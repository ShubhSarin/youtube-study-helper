"""FastAPI backend exposing the core YouTube Study Helper pipeline as REST endpoints.

All heavy lifting (transcripts, summarization, flashcards, quiz, RAG) stays in core/.
This layer only translates HTTP requests into core/ calls and keeps per-session state.

Abuse protection: exactly one active session per client IP (bindings expire after
inactivity). Client-supplied session ids are never trusted — the server binds and
resolves the session itself, so a visitor cannot mint extra sessions or adopt
someone else's.
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from core.env_utils import read_env_value
from core.playlist import get_video_ids_from_playlist
from core.rag import answer_question
from core.summarizer import summarize_transcript
from core.flashcards import generate_flashcards
from core.quiz import generate_quiz
from core.transcript import extract_transcripts_from_ids
from core.youtube_utils import is_playlist, extract_video_id, get_video_title

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger("api")

app = FastAPI(title="YouTube Study Helper", version="2.1.0")

# CORS for local dev (Vite dev server on 5173); prod serves the built SPA from the same origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Session state (per session id, thread-safe)
# ---------------------------------------------------------------------------
SESSION_TTL_SECONDS = 60 * 60  # one hour of inactivity releases the IP's slot


class SessionState:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.video_ids: list[str] = []
        self.video_titles: dict[str, str] = {}
        self.transcripts: dict[str, str] = {}
        self.transcript_errors: dict[str, str] = {}
        self.summaries: dict[str, str] = {}
        self.flashcards: dict[str, str] = {}
        self.quizzes: dict[str, str] = {}
        self.chat_history: list[dict[str, str]] = []


SESSIONS: dict[str, SessionState] = {}
# ip -> (session_id, last_seen_epoch). One live binding per IP enforces the
# one-active-chat-per-IP limit and keeps Supadata spend bounded per visitor.
IP_BINDINGS: dict[str, tuple[str, float]] = {}


def _purge_expired() -> None:
    now = time.time()
    expired_ips = [ip for ip, (_, seen) in IP_BINDINGS.items() if now - seen > SESSION_TTL_SECONDS]
    for ip in expired_ips:
        sid, _ = IP_BINDINGS.pop(ip)
        SESSIONS.pop(sid, None)


def _client_ip(request: Request) -> str:
    # Azure Container Apps / reverse proxies put the real client in X-Forwarded-For.
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _resolve_session(request: Request) -> str:
    """Return the session id bound to this client IP, creating one if needed.

    Client-supplied session ids are ignored entirely: the server is authoritative.
    """
    ip = _client_ip(request)
    with threading.Lock():
        _purge_expired()
        binding = IP_BINDINGS.get(ip)
        now = time.time()
        if binding is not None:
            sid, _ = binding
            IP_BINDINGS[ip] = (sid, now)
            SESSIONS.setdefault(sid, SessionState())
            return sid
        sid = str(uuid.uuid4())
        IP_BINDINGS[ip] = (sid, now)
        SESSIONS[sid] = SessionState()
        LOGGER.info("Bound new session %s to IP %s (%d active)", sid, ip, len(IP_BINDINGS))
        return sid


def _require_session(request: Request) -> tuple[str, SessionState]:
    sid = _resolve_session(request)
    state = SESSIONS.get(sid)
    if state is None:  # pragma: no cover - _resolve_session always ensures it
        raise HTTPException(status_code=401, detail="Session expired. Reload the page.")
    return sid, state


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class ProcessRequest(BaseModel):
    session_id: str | None = None  # accepted for compat; ignored — server binds by IP
    url: str


class GenerateRequest(BaseModel):
    session_id: str | None = None
    video_id: str
    action: str  # "summary" | "flashcards" | "quiz"


class QuestionRequest(BaseModel):
    session_id: str | None = None
    question: str


# ---------------------------------------------------------------------------
# Cookie sync (for yt-dlp authenticated requests)
# ---------------------------------------------------------------------------
COOKIE_FILE_PATH = Path(__file__).resolve().parent.parent / "youtube_cookies.txt"


def sync_cookie_file() -> None:
    cookies_content = read_env_value("YOUTUBE_COOKIES_CONTENT")
    if not cookies_content:
        return
    if COOKIE_FILE_PATH.exists():
        existing = COOKIE_FILE_PATH.read_text(encoding="utf-8")
        if existing == cookies_content:
            return
    COOKIE_FILE_PATH.write_text(cookies_content, encoding="utf-8")


sync_cookie_file()


# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------
@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/session")
def get_session(request: Request) -> dict:
    """Resolve (or create) the IP-bound session and return its full state.

    Lets the SPA hydrate after a refresh without losing loaded transcripts
    or generated content, and without creating a second session.
    """
    sid, state = _require_session(request)
    with state.lock:
        return _session_payload(sid, state)


@app.post("/api/release")
def release_session(request: Request) -> dict:
    """Explicitly drop this IP's session (the UI's 'Clear session' button)."""
    ip = _client_ip(request)
    with threading.Lock():
        binding = IP_BINDINGS.pop(ip, None)
    if binding is not None:
        SESSIONS.pop(binding[0], None)
    return {"released": binding is not None}


@app.post("/api/process")
def process_url(req: ProcessRequest, request: Request) -> dict:
    sid, state = _require_session(request)

    with state.lock:
        try:
            if is_playlist(req.url):
                video_ids = get_video_ids_from_playlist(req.url)
            else:
                video_ids = [extract_video_id(req.url)]
        except Exception as exc:
            LOGGER.error("Failed to parse URL %s: %s", req.url, exc)
            raise HTTPException(status_code=400, detail=f"Could not parse YouTube URL: {exc}")

        if not video_ids:
            raise HTTPException(status_code=400, detail="No videos found in URL.")

        transcripts, transcript_errors = extract_transcripts_from_ids(video_ids)

        state.video_ids = video_ids
        state.video_titles = {vid: get_video_title(vid) for vid in video_ids}
        state.transcripts = transcripts
        state.transcript_errors = transcript_errors
        state.summaries = {}
        state.flashcards = {}
        state.quizzes = {}
        state.chat_history = []

    return {
        "session_id": sid,
        "videos": [
            {
                "video_id": vid,
                "title": state.video_titles.get(vid, vid),
                "error": transcript_errors.get(vid),
            }
            for vid in video_ids
        ],
    }


@app.post("/api/generate")
def generate(req: GenerateRequest, request: Request) -> dict:
    sid, state = _require_session(request)

    with state.lock:
        transcript = state.transcripts.get(req.video_id)
        if not transcript:
            raise HTTPException(
                status_code=404,
                detail=f"No transcript available for video {req.video_id}. Process the URL first.",
            )

        action_map = {
            "summary": ("summaries", summarize_transcript),
            "flashcards": ("flashcards", generate_flashcards),
            "quiz": ("quizzes", generate_quiz),
        }
        if req.action not in action_map:
            raise HTTPException(status_code=400, detail=f"Unknown action '{req.action}'.")

        state_key, func = action_map[req.action]
        generated = func(transcript)
        getattr(state, state_key)[req.video_id] = generated

    return {"session_id": sid, "video_id": req.video_id, "action": req.action, "content": generated}


@app.post("/api/ask")
def ask(req: QuestionRequest, request: Request) -> dict:
    sid, state = _require_session(request)

    with state.lock:
        if not state.transcripts:
            raise HTTPException(status_code=400, detail="No transcripts loaded. Process a URL first.")

        answer = answer_question(req.question, state.transcripts, state.video_titles)
        state.chat_history.append({"question": req.question, "answer": answer})

    return {"session_id": sid, "question": req.question, "answer": answer}


def _session_payload(sid: str, state: SessionState) -> dict:
    return {
        "session_id": sid,
        "videos": [
            {
                "video_id": vid,
                "title": state.video_titles.get(vid, vid),
                "error": state.transcript_errors.get(vid),
                "summary": state.summaries.get(vid),
                "flashcards": state.flashcards.get(vid),
                "quiz": state.quizzes.get(vid),
            }
            for vid in state.video_ids
        ],
        "chat": list(state.chat_history),
    }


# ---------------------------------------------------------------------------
# Static SPA serving (production) — must come after API routes
# ---------------------------------------------------------------------------
WEB_DIST = Path(__file__).resolve().parent.parent / "web" / "dist"

if WEB_DIST.exists():
    app.mount("/assets", StaticFiles(directory=WEB_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}")
    def spa(full_path: str) -> FileResponse:
        file_path = WEB_DIST / full_path
        if full_path and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(WEB_DIST / "index.html")
