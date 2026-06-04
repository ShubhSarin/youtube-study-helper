import streamlit as st
from core.env_utils import read_env_value
from core.transcript import extract_transcripts_from_ids
from core.youtube_utils import is_playlist, extract_video_id, get_video_title
from core.playlist import get_video_ids_from_playlist
from core.summarizer import summarize_transcript
from core.flashcards import generate_flashcards
from core.quiz import generate_quiz
from core.rag import answer_question
from pathlib import Path

# ---------------------------------------------------------------------------
# Page configuration
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="YouTube Study Helper",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Custom CSS
# ---------------------------------------------------------------------------
st.markdown(
    """
<style>
    .main-header {
        font-size: 2.4rem;
        font-weight: 700;
        margin-bottom: 0.2rem;
    }
    .main-subheader {
        font-size: 1.05rem;
        color: #6b7280;
        margin-bottom: 1.5rem;
    }
    .video-title {
        font-size: 2.3rem;
        font-weight: 600;
        margin-bottom: 0.75rem;
    }
    .stButton > button {
        border-radius: 8px;
        font-weight: 500;
        transition: all 0.15s ease;
        width: 100%;
    }
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    }
    .chat-container {
        border-radius: 12px;
        padding: 1rem 0;
        margin-top: 0.5rem;
    }
    .stChatMessage {
        border-radius: 10px;
    }
    footer {visibility: hidden;}
</style>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Cookie sync (for yt-dlp authenticated requests)
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent
COOKIE_FILE_PATH = PROJECT_ROOT / "youtube_cookies.txt"


def sync_cookie_file() -> None:
    cookies_content = read_env_value("YOUTUBE_COOKIES_CONTENT")
    if not cookies_content:
        return
    if COOKIE_FILE_PATH.exists():
        existing_content = COOKIE_FILE_PATH.read_text(encoding="utf-8")
        if existing_content == cookies_content:
            return
    COOKIE_FILE_PATH.write_text(cookies_content, encoding="utf-8")


sync_cookie_file()

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
DEFAULTS: dict[str, object] = {
    "video_ids": [],
    "video_titles": {},
    "transcripts": {},
    "transcript_errors": {},
    "summaries": {},
    "flashcards": {},
    "quizzes": {},
    "chat_history": [],
    "pending_generation": None,
    "processing": False,
    "processing_result": None,
}
for key, default in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = default


def reset_session() -> None:
    for key, default in DEFAULTS.items():
        st.session_state[key] = default


# ---------------------------------------------------------------------------
# Generation helpers
# ---------------------------------------------------------------------------
def queue_generation(video_id: str, action: str) -> None:
    if st.session_state.get("pending_generation") is not None:
        return
    st.session_state["pending_generation"] = {"video_id": video_id, "action": action}
    st.rerun()


def run_generation_action(video_id: str, action: str) -> None:
    transcript = st.session_state["transcripts"][video_id]

    action_map = {
        "summary": ("Generating notes...", "summaries", summarize_transcript),
        "flashcards": ("Generating flashcards...", "flashcards", generate_flashcards),
        "quiz": ("Generating quiz...", "quizzes", generate_quiz),
    }
    spinner_text, state_key, func = action_map[action]

    with st.spinner(spinner_text):
        st.session_state[state_key][video_id] = func(transcript)


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### 🎓 Study Helper")
    st.caption("Turn YouTube videos into study material with AI.")

    st.divider()

    if st.session_state["video_ids"]:
        st.metric("Videos loaded", len(st.session_state["video_ids"]))
        notes_count = len(st.session_state["summaries"])
        cards_count = len(st.session_state["flashcards"])
        quiz_count = len(st.session_state["quizzes"])
        st.caption(f"📘 {notes_count} notes  ·  🧠 {cards_count} flashcards  ·  📝 {quiz_count} quizzes")

    st.divider()

    if st.button("🗑️ Clear session", use_container_width=True):
        reset_session()
        st.rerun()

    st.divider()
    st.caption("Built with Streamlit  •  Powered by AI")

# ---------------------------------------------------------------------------
# Main content
# ---------------------------------------------------------------------------
st.markdown('<p class="main-header">🎓 YouTube Study Helper</p>', unsafe_allow_html=True)
st.markdown(
    '<p class="main-subheader">Paste a YouTube video or playlist URL to generate notes, flashcards, and quizzes — then ask questions about the content.</p>',
    unsafe_allow_html=True,
)

# URL input
col_url, col_btn = st.columns([5, 1])
with col_url:
    url = st.text_input(
        "YouTube URL",
        placeholder="https://www.youtube.com/watch?v=... or playlist URL",
        label_visibility="collapsed",
    )
is_busy = st.session_state.get("processing", False) or st.session_state.get("pending_generation") is not None
with col_btn:
    if is_busy:
        st.caption("⏳ Working...")
        process_clicked = False
    else:
        process_clicked = st.button("🚀 Process", use_container_width=True)

if process_clicked and url and not st.session_state.get("processing") and not st.session_state.get("pending_generation"):
    st.session_state["processing"] = True
    st.rerun()

if st.session_state.get("processing"):
    with st.spinner("Extracting transcripts..."):
        try:
            if is_playlist(url):
                video_ids = get_video_ids_from_playlist(url)
            else:
                video_ids = [extract_video_id(url)]

            st.session_state["video_ids"] = video_ids
            st.session_state["video_titles"] = {vid: get_video_title(vid) for vid in video_ids}
            st.session_state["transcripts"], st.session_state["transcript_errors"] = extract_transcripts_from_ids(video_ids)
            st.session_state["summaries"] = {}
            st.session_state["flashcards"] = {}
            st.session_state["quizzes"] = {}
            if st.session_state["transcript_errors"]:
                st.session_state["processing_result"] = ("warning", f"⚠️ Could not extract transcript for {len(st.session_state['transcript_errors'])} video(s).")
            else:
                st.session_state["processing_result"] = ("success", f"✅ Processed {len(video_ids)} video(s) successfully!")
        finally:
            st.session_state["processing"] = False
        st.rerun()

if st.session_state.get("processing_result"):
    level, message = st.session_state["processing_result"]
    if level == "success":
        st.success(message)
    else:
        st.warning(message)
    st.session_state["processing_result"] = None

# ---------------------------------------------------------------------------
# Video cards (only render when not busy with processing)
# ---------------------------------------------------------------------------
if st.session_state["video_ids"] and not st.session_state.get("processing"):
    is_busy = st.session_state.get("pending_generation") is not None

    for vid in st.session_state["video_ids"]:
        title = st.session_state["video_titles"].get(vid, vid)

        st.markdown(f'<p class="video-title">🎬 {title}</p>', unsafe_allow_html=True)

        transcript_error = st.session_state["transcript_errors"].get(vid)
        if transcript_error:
            st.error(transcript_error)
            continue

        # Action buttons (hidden entirely when busy to prevent click races)
        if is_busy:
            st.caption("⏳ Generating...")
        else:
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("📘 Notes", key=f"summary_{vid}", use_container_width=True):
                    queue_generation(vid, "summary")
            with col2:
                if st.button("🧠 Flashcards", key=f"flashcards_{vid}", use_container_width=True):
                    queue_generation(vid, "flashcards")
            with col3:
                if st.button("📝 Quiz", key=f"quiz_{vid}", use_container_width=True):
                    queue_generation(vid, "quiz")

        # Display generated content in tabs
        has_notes = vid in st.session_state["summaries"]
        has_flashcards = vid in st.session_state["flashcards"]
        has_quiz = vid in st.session_state["quizzes"]

        if has_notes or has_flashcards or has_quiz:
            tab_labels = []
            if has_notes:
                tab_labels.append("📘 Notes")
            if has_flashcards:
                tab_labels.append("🧠 Flashcards")
            if has_quiz:
                tab_labels.append("📝 Quiz")
            tabs = st.tabs(tab_labels)
            tab_idx = 0
            if has_notes:
                with tabs[tab_idx]:
                    st.markdown(st.session_state["summaries"][vid])
                tab_idx += 1
            if has_flashcards:
                with tabs[tab_idx]:
                    st.markdown(st.session_state["flashcards"][vid])
                tab_idx += 1
            if has_quiz:
                with tabs[tab_idx]:
                    st.markdown(st.session_state["quizzes"][vid])

# ---------------------------------------------------------------------------
# Handle pending generation (after cards render so buttons are hidden)
# ---------------------------------------------------------------------------
pending_generation = st.session_state.get("pending_generation")
if pending_generation:
    vid = pending_generation["video_id"]
    action = pending_generation["action"]
    try:
        run_generation_action(vid, action)
    finally:
        st.session_state["pending_generation"] = None
    st.rerun()

# ---------------------------------------------------------------------------
# Q&A section
# ---------------------------------------------------------------------------
if st.session_state["video_ids"] and st.session_state["transcripts"]:
    st.divider()
    st.markdown("### 💬 Ask Questions About the Videos")

    with st.container():
        st.markdown('<div class="chat-container">', unsafe_allow_html=True)

        # Chat history
        for chat in st.session_state["chat_history"]:
            with st.chat_message("user"):
                st.write(chat["question"])
            with st.chat_message("assistant"):
                st.write(chat["answer"])

        # Input
        question = st.chat_input("Ask a question about the video content...")
        if question:
            with st.chat_message("user"):
                st.write(question)
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    answer = answer_question(
                        question,
                        st.session_state["transcripts"],
                        st.session_state["video_titles"],
                    )
                    st.write(answer)
            st.session_state["chat_history"].append({"question": question, "answer": answer})
            st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

