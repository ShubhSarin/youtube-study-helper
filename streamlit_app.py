import streamlit as st
from core.transcript import extract_transcript_from_id
from core.youtube_utils import is_playlist, extract_video_id, get_video_title
from core.playlist import get_video_ids_from_playlist
from core.summarizer import summarize_transcript
from core.flashcards import generate_flashcards
from core.quiz import generate_quiz
from core.rag import answer_question
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
COOKIE_FILE_PATH = PROJECT_ROOT / "youtube_cookies.txt"

cookies_content = os.getenv("YOUTUBE_COOKIES_CONTENT")

if cookies_content:
    # Write the content to a file on the server's disk
    with open(COOKIE_FILE_PATH, "w") as f:
        f.write(cookies_content)
    print("YouTube cookies file created successfully.")
else:
    print("YOUTUBE_COOKIES_CONTENT variable not found.")

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
            transcript = extract_transcript_from_id(vid)
            if transcript.startswith("Error:"):
                st.session_state["transcript_errors"][vid] = transcript
            else:
                st.session_state["transcripts"][vid] = transcript
    
    st.success(f"✅ Processed {len(video_ids)} video(s)")
    if st.session_state["transcript_errors"]:
        st.warning(
            f"⚠️ Could not extract transcript for {len(st.session_state['transcript_errors'])} video(s)."
        )

# Display videos and interactive buttons
if st.session_state["video_ids"]:
    for vid in st.session_state["video_ids"]:
        title = st.session_state["video_titles"].get(vid, vid)
        st.header(f"🎬 {title}")

        transcript_error = st.session_state["transcript_errors"].get(vid)
        if transcript_error:
            st.error(transcript_error)
            st.divider()
            continue
        
        col1, col2, col3 = st.columns(3)
        
        # Generate Summary Button
        with col1:
            if st.button(f"📘 Generate Notes", key=f"summary_{vid}"):
                with st.spinner("Generating notes..."):
                    transcript = st.session_state["transcripts"][vid]
                    st.session_state["summaries"][vid] = summarize_transcript(transcript)
        
        # Generate Flashcards Button
        with col2:
            if st.button(f"🧠 Generate Flashcards", key=f"flashcards_{vid}"):
                with st.spinner("Generating flashcards..."):
                    transcript = st.session_state["transcripts"][vid]
                    st.session_state["flashcards"][vid] = generate_flashcards(transcript)
        
        # Generate Quiz Button
        with col3:
            if st.button(f"📝 Generate Quiz", key=f"quiz_{vid}"):
                with st.spinner("Generating quiz..."):
                    transcript = st.session_state["transcripts"][vid]
                    st.session_state["quizzes"][vid] = generate_quiz(transcript)
        
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
