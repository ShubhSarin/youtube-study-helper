from youtube_transcript_api import YouTubeTranscriptApi
from urllib.parse import urlparse, parse_qs
from pathlib import Path
import re
import requests
import yt_dlp

PROJECT_ROOT = Path(__file__).resolve().parent.parent
COOKIE_FILE_PATH = PROJECT_ROOT / "youtube_cookies.txt"


def _extract_text_from_json3(payload: dict) -> str:
    parts = []
    for event in payload.get("events", []):
        for seg in event.get("segs", []):
            text = seg.get("utf8", "")
            if text:
                parts.append(text)
    return " ".join(parts).replace("\n", " ").strip()


def _extract_text_from_vtt(vtt_text: str) -> str:
    lines = []
    for raw_line in vtt_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line == "WEBVTT":
            continue
        if "-->" in line:
            continue
        if line.isdigit():
            continue
        lines.append(line)

    cleaned = " ".join(lines)
    cleaned = re.sub(r"<[^>]+>", "", cleaned)
    return cleaned.strip()


def _fetch_transcript_via_ytdlp(video_id: str) -> str:
    url = f"https://www.youtube.com/watch?v={video_id}"
    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "ignoreconfig": True,
        "noplaylist": True,
    }
    if COOKIE_FILE_PATH.exists():
        opts["cookiefile"] = str(COOKIE_FILE_PATH)

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)

    subtitle_map = info.get("subtitles") or {}
    auto_map = info.get("automatic_captions") or {}

    # Prefer manual subtitles, then auto captions.
    candidates = subtitle_map if subtitle_map else auto_map
    if not candidates:
        return ""

    preferred_langs = ["en", "en-US"]
    lang_key = next((l for l in preferred_langs if l in candidates), None)
    if not lang_key:
        lang_key = next(iter(candidates.keys()))

    tracks = candidates.get(lang_key, [])
    if not tracks:
        return ""

    json3_track = next((t for t in tracks if t.get("ext") == "json3" and t.get("url")), None)
    if json3_track:
        resp = requests.get(json3_track["url"], timeout=20)
        resp.raise_for_status()
        text = _extract_text_from_json3(resp.json())
        if text:
            return text

    # Fallback to VTT/SRV subtitle formats.
    any_track = next((t for t in tracks if t.get("url")), None)
    if not any_track:
        return ""

    resp = requests.get(any_track["url"], timeout=20)
    resp.raise_for_status()
    return _extract_text_from_vtt(resp.text)

def get_video_id(youtube_url: str) -> str:
    parsed = urlparse(youtube_url)

    if parsed.hostname in ["www.youtube.com", "youtube.com"]:
        return parse_qs(parsed.query)["v"][0]

    if parsed.hostname == "youtu.be":
        return parsed.path[1:]

    raise ValueError("Invalid YouTube URL")


def extract_transcript_from_id(video_id: str) -> str:
    try:
        api = YouTubeTranscriptApi()
        if COOKIE_FILE_PATH.exists():
            try:
                api = YouTubeTranscriptApi(cookie_path=str(COOKIE_FILE_PATH))
            except Exception:
                # Fall back to cookie-less mode when cookie parsing/loading fails.
                api = YouTubeTranscriptApi()

        # Try English first, then fall back to any available transcript language.
        try:
            transcript = api.fetch(video_id, languages=["en", "en-US"])
        except Exception:
            transcript_list = api.list(video_id)
            transcript = next(iter(transcript_list)).fetch()

        full_text = " ".join(chunk.text for chunk in transcript).strip()
        if not full_text:
            return "Error: Transcript is empty"
        return full_text
        
    except Exception as e:
        try:
            fallback_text = _fetch_transcript_via_ytdlp(video_id)
            if fallback_text:
                return fallback_text
        except Exception:
            pass

        # This will catch the error and show it in your Streamlit UI
        return f"Error: {e}"
