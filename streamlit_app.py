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

# Initialize session state
if "video_ids" not in st.session_state:
    st.session_state["video_ids"] = []
if "video_titles" not in st.session_state:
    st.session_state["video_titles"] = {}
if "transcripts" not in st.session_state:
    st.session_state["transcripts"] = {}
if "transcript_errors" not in st.session_state:
    st.session_state["transcript_errors"] = {}
if "summaries" not in st.session_state:
    st.session_state["summaries"] = {}
if "flashcards" not in st.session_state:
    st.session_state["flashcards"] = {}
if "quizzes" not in st.session_state:
    st.session_state["quizzes"] = {}
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []
if "pending_generation" not in st.session_state:
    st.session_state["pending_generation"] = None


def queue_generation(video_id: str, action: str) -> None:
    st.session_state["pending_generation"] = {
        "video_id": video_id,
        "action": action,
    }
    st.rerun()


def run_generation_action(video_id: str, action: str) -> None:
    transcript = st.session_state["transcripts"][video_id]

    if action == "summary":
        with st.spinner("Generating notes..."):
            st.session_state["summaries"][video_id] = summarize_transcript(transcript)
        return

    if action == "flashcards":
        with st.spinner("Generating flashcards..."):
            st.session_state["flashcards"][video_id] = generate_flashcards(transcript)
        return

    if action == "quiz":
        with st.spinner("Generating quiz..."):
            st.session_state["quizzes"][video_id] = generate_quiz(transcript)
        return

    raise ValueError(f"Unknown generation action: {action}")

st.title("YouTube Study Assistant")

url = st.text_input("Paste YouTube video or playlist URL")

if st.button("Process") and url:
    with st.spinner("Extracting transcripts..."):
        # Extract video IDs
        if is_playlist(url):
            video_ids = get_video_ids_from_playlist(url)
        else:
            video_ids = [extract_video_id(url)]
        
        # Store video IDs and extract transcripts
        st.session_state["video_ids"] = video_ids
        st.session_state["video_titles"] = {}
        st.session_state["transcripts"] = {}
        st.session_state["transcript_errors"] = {}
        st.session_state["summaries"] = {}
        st.session_state["flashcards"] = {}
        st.session_state["quizzes"] = {}
        
        for vid in video_ids:
            st.session_state["video_titles"][vid] = get_video_title(vid)

        transcripts, transcript_errors = extract_transcripts_from_ids(video_ids)
        st.session_state["transcripts"] = transcripts
        st.session_state["transcript_errors"] = transcript_errors
    
    st.success(f"✅ Processed {len(video_ids)} video(s)")
    if st.session_state["transcript_errors"]:
        st.warning(
            f"⚠️ Could not extract transcript for {len(st.session_state['transcript_errors'])} video(s)."
        )

# Display videos and interactive buttons
if st.session_state["video_ids"]:
    pending_generation = st.session_state["pending_generation"]
    is_generation_running = pending_generation is not None

    for vid in st.session_state["video_ids"]:
        title = st.session_state["video_titles"].get(vid, vid)
        st.header(f"🎬 {title}")

        transcript_error = st.session_state["transcript_errors"].get(vid)
        if transcript_error:
            st.error(transcript_error)
            st.divider()
            continue
        
        action_area = st.empty()
        with action_area.container():
            col1, col2, col3 = st.columns(3)
            if col1.button(
                "📘 Generate Notes",
                key=f"summary_{vid}",
                disabled=is_generation_running,
            ):
                queue_generation(vid, "summary")

            if col2.button(
                "🧠 Generate Flashcards",
                key=f"flashcards_{vid}",
                disabled=is_generation_running,
            ):
                queue_generation(vid, "flashcards")

            if col3.button(
                "📝 Generate Quiz",
                key=f"quiz_{vid}",
                disabled=is_generation_running,
            ):
                queue_generation(vid, "quiz")

            if pending_generation and pending_generation["video_id"] == vid:
                try:
                    run_generation_action(vid, pending_generation["action"])
                finally:
                    st.session_state["pending_generation"] = None
                st.rerun()
        
        # Display generated content
        if vid in st.session_state["summaries"]:
            with st.expander("📘 Notes", expanded=True):
                st.write(st.session_state["summaries"][vid])
        
        if vid in st.session_state["flashcards"]:
            with st.expander("🧠 Flashcards", expanded=True):
                st.write(st.session_state["flashcards"][vid])
        
        if vid in st.session_state["quizzes"]:
            with st.expander("📝 Quiz", expanded=True):
                st.write(st.session_state["quizzes"][vid])
        
        st.divider()

# RAG Q&A Section - Ask questions about all videos
if st.session_state["video_ids"] and st.session_state["transcripts"]:
    st.header("💬 Ask Questions About the Videos")
    st.write("Ask any question about the content from the processed videos.")
    
    # Display chat history
    for chat in st.session_state["chat_history"]:
        with st.chat_message("user"):
            st.write(chat["question"])
        with st.chat_message("assistant"):
            st.write(chat["answer"])
    
    # Question input
    question = st.chat_input("Ask a question about the video content...")
    
    if question:
        # Add user question to chat
        with st.chat_message("user"):
            st.write(question)
        
        # Generate answer
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                answer = answer_question(
                    question, 
                    st.session_state["transcripts"],
                    st.session_state["video_titles"]
                )
                st.write(answer)
        
        # Save to chat history
        st.session_state["chat_history"].append({
            "question": question,
            "answer": answer
        })
        st.rerun()
