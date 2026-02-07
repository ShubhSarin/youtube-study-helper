# 🎓 YouTube Study Helper

A powerful AI-powered study assistant that helps you learn from YouTube videos and playlists by automatically generating summaries, flashcards, quizzes, and answering your questions about the content.

## ✨ Features

- 📺 **Video & Playlist Support**: Process individual YouTube videos or entire playlists
- 📝 **AI-Generated Notes**: Automatically create structured, chapter-wise study notes from video transcripts
- 🧠 **Smart Flashcards**: Generate question-answer flashcard pairs for effective learning and memorization
- 📊 **Interactive Quizzes**: Create multiple-choice quizzes with 4 options to test your knowledge
- 💬 **RAG-Powered Q&A**: Ask questions about video content and get accurate answers based on transcripts
- 🎯 **Multi-Video Context**: Process multiple videos and ask questions across all content
- ⚡ **Real-time Processing**: Fast transcript extraction and AI-powered content generation

## 🚀 Getting Started

### Prerequisites

- Python 3.8 or higher
- Google API Key (for Gemini AI model)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/ShubhSarin/youtube-study-helper.git
cd youtube-study-helper
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up your Google API Key:
   - Create a `.env` file in the project root
   - Add your Google API key:
```bash
GOOGLE_API_KEY=your_api_key_here
```
   - Get your API key from [Google AI Studio](https://aistudio.google.com/app/apikey)

### Running the Application

Launch the Streamlit app:
```bash
streamlit run streamlit_app.py
```

The app will open in your default web browser at `http://localhost:8501`

## 📖 Usage Guide

1. **Enter YouTube URL**: Paste a YouTube video or playlist URL into the input field
2. **Process Content**: Click the "Process" button to extract transcripts from the video(s)
3. **Generate Study Materials**:
   - Click "📘 Generate Notes" for structured study notes
   - Click "🧠 Generate Flashcards" for flashcard learning pairs
   - Click "📝 Generate Quiz" for multiple-choice questions
4. **Ask Questions**: Use the chat interface at the bottom to ask questions about the video content
5. **Interactive Learning**: Expand sections to view your generated content

## 🏗️ Project Structure

```
youtube-study-helper/
├── streamlit_app.py          # Main Streamlit application
├── requirements.txt          # Python dependencies
├── transcript_extractor.py   # Legacy transcript extraction
├── core/                     # Core functionality modules
│   ├── transcript.py         # YouTube transcript extraction
│   ├── summarizer.py         # AI-powered note generation
│   ├── flashcards.py         # Flashcard generation
│   ├── quiz.py               # Quiz generation
│   ├── rag.py                # RAG-based question answering
│   ├── llm.py                # Google Gemini AI integration
│   ├── youtube_utils.py      # YouTube URL parsing utilities
│   └── playlist.py           # Playlist handling
└── agents/                   # AI agent definitions
    └── agent.py              # Specialized AI agents for different tasks
```

## 🛠️ Technology Stack

- **Frontend**: [Streamlit](https://streamlit.io/) - Interactive web interface
- **AI Model**: [Google Gemini 2.5 Flash](https://ai.google.dev/) - Content generation and Q&A
- **YouTube API**: 
  - [youtube-transcript-api](https://github.com/jdepoix/youtube-transcript-api) - Transcript extraction
  - [yt-dlp](https://github.com/yt-dlp/yt-dlp) - Video metadata and playlist handling
- **AI Framework**: [Google ADK](https://github.com/google/adk) - Agent-based AI architecture

## 🔑 Key Components

### Core Modules

- **`transcript.py`**: Extracts transcripts from YouTube videos using video IDs
- **`summarizer.py`**: Creates structured study notes with headings and bullet points
- **`flashcards.py`**: Generates concise question-answer pairs for memorization
- **`quiz.py`**: Creates multiple-choice questions for knowledge assessment
- **`rag.py`**: Implements RAG (Retrieval-Augmented Generation) for answering questions
- **`llm.py`**: Manages Google Gemini AI model integration
- **`playlist.py`**: Handles YouTube playlist processing
- **`youtube_utils.py`**: Utility functions for URL parsing and video metadata

### AI Agents

The project uses specialized AI agents for different tasks:
- **Summary Agent**: Optimized for creating structured notes
- **Flashcard Agent**: Specialized in generating learning pairs
- **Quiz Agent**: Focused on creating assessment questions
- **RAG Agent**: Expert in answering questions based on transcripts

## 🎯 Use Cases

- 📚 **Students**: Create study materials from educational YouTube videos
- 👨‍🏫 **Educators**: Generate quizzes and flashcards for teaching
- 📖 **Lifelong Learners**: Build comprehensive notes from tutorial playlists
- 🧪 **Researchers**: Extract and query information from technical talks
- 📝 **Content Reviewers**: Quickly understand video content through summaries

## 🔒 Environment Variables

Create a `.env` file with the following:

```bash
GOOGLE_API_KEY=your_google_api_key_here
```

## 📋 Requirements

See `requirements.txt` for full dependency list:
- streamlit >= 1.32.0
- google-adk >= 0.1.0
- google-generativeai >= 0.8.0
- youtube-transcript-api >= 0.6.0
- yt-dlp >= 2024.0.0
- python-dotenv >= 1.0.0

## 🤝 Contributing

Contributions are welcome! Feel free to:
- Report bugs
- Suggest new features
- Submit pull requests

## 📄 License

This project is open source. Please check the repository for license details.

## 🙏 Acknowledgments

- Google Gemini AI for powerful content generation
- YouTube Transcript API for reliable transcript extraction
- Streamlit for the intuitive web framework
