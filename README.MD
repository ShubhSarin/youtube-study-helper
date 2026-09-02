# 🎓 YouTube Study Helper

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![React](https://img.shields.io/badge/React-19-61DAFB.svg)](https://react.dev/)
[![FastAPI](https://img.shields.io/badge/FastAPI-latest-009688.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

Turn YouTube videos and playlists into study material with AI. Paste a URL, get **notes**, **flashcards**, and **quizzes** — then ask questions with retrieval-augmented generation (RAG) over the full transcript.

## ✨ Features

- 🖥️ **Real UI** — React + Vite + Tailwind SPA served by FastAPI (no Streamlit)
- 📺 **Single video or playlist** — process one lecture or an entire course
- 📘 **Study notes** — chapter-wise notes generated from the transcript
- 🧠 **Flashcards** — concise Q&A pairs for active recall
- 📝 **Quizzes** — 5-question multiple-choice quiz per video
- 💬 **RAG-powered Q&A** — ask questions across all processed videos; answers are grounded in transcript excerpts, not summaries
- ☁️ **Supadata transcripts** — reliable transcript retrieval that works in cloud deployments
- 🔀 **Multi-provider LLM** — switch between Google Gemini and OpenRouter (OpenAI-compatible) by setting env vars
- 🐳 **Docker-ready** — multi-stage build (Node build → FastAPI serves static SPA) for Azure Container Apps or any container host

## 🚀 Quick Start

```bash
# Clone
git clone https://github.com/ShubhSarin/youtube-study-helper.git
cd youtube-study-helper

# Backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Frontend (Node 18+)
cd web && npm install && npm run build && cd ..

# Configure (copy and edit)
cp .env.example .env
# Fill in your API keys in .env

# Run — serves the API and the built UI on http://localhost:8000
uvicorn api.main:app --reload --port 8000
```

### Development mode (hot reload)

```bash
# Terminal 1 — API
uvicorn api.main:app --reload --port 8000

# Terminal 2 — Vite dev server with /api proxied to :8000
cd web && npm run dev
```


## ⚙️ Environment Variables

Copy `.env.example` to `.env` and fill in your keys:

| Variable | Description | Required |
|---|---|---|
| `SUPADATA_API_KEY` | [Supadata](https://supadata.ai) API key for transcript extraction | ✅ |
| `OPENROUTER_API_KEY` | [OpenRouter](https://openrouter.ai) API key (uses this if set) | *(one of these)* |
| `OPENROUTER_BASE_URL` | OpenRouter base URL (default: `https://openrouter.ai/api/v1`) | |
| `OPENROUTER_MODEL_NAME` | Chat model (default: `xiaomi/mimo-v2.5`) | |
| `OPENROUTER_EMBEDDING_MODEL_NAME` | Embedding model (default: `openai/text-embedding-3-small`) | |
| `GOOGLE_API_KEY` | Google Gemini API key (used when `OPENROUTER_API_KEY` is empty) | *(one of these)* |
| `GENERATION_MODEL_NAME` | Gemini generation model (default: `xiaomi/mimo-v2.5`) | |
| `EMBEDDING_MODEL_NAME` | Gemini embedding model (default: `openai/text-embedding-3-small`) | |

> **How it works:** If `OPENROUTER_API_KEY` is set → uses OpenRouter with OpenAI-compatible client. Otherwise → falls back to Google Gemini SDK.

## 🧠 How It Works

```mermaid
flowchart LR
    A[YouTube URL] --> B{Playlist?}
    B -->|Yes| C[Fetch all video IDs]
    B -->|No| D[Extract single video ID]
    C --> E[Supadata transcript API]
    D --> E
    E --> F[Chunk transcripts]
    F --> G[Embed chunks]
    G --> H[In-memory index]
    H --> I[Notes / Flashcards / Quiz]
    H --> J[RAG Q&A]
    J --> K[Cosine similarity retrieval]
    K --> L[LLM generates answer]
```

## 🐳 Docker Deployment

```bash
docker build -t youtube-study-helper .
docker run -p 8000:8000 --env-file .env youtube-study-helper
# UI + API at http://localhost:8000
```

For Azure Container App deployment, see [DEPLOY.md](DEPLOY.md).

## 📁 Project Structure

```
.
├── api/
│   ├── __init__.py
│   └── main.py               # FastAPI backend: REST endpoints + SPA serving
├── web/                      # React (Vite + TypeScript + Tailwind) frontend
│   ├── src/
│   │   ├── App.tsx           # UI: URL input, video cards, tabs, chat
│   │   ├── api.ts            # Typed fetch client for the backend
│   │   └── main.tsx
│   └── vite.config.ts        # Dev proxy: /api → :8000
├── core/
│   ├── llm.py                # LLM client (Gemini / OpenRouter)
│   ├── transcript.py         # Supadata transcript retrieval
│   ├── summarizer.py         # Study notes generation
│   ├── flashcards.py         # Flashcard generation
│   ├── quiz.py               # Quiz generation
│   ├── rag.py                # RAG retrieval + Q&A
│   ├── youtube_utils.py      # YouTube URL parsing
│   ├── playlist.py           # Playlist video ID extraction
│   └── env_utils.py          # .env file reader (no python-dotenv)
├── agents/                   # (experimental)
├── Dockerfile                # Multi-stage: node build → fastapi serve
├── DEPLOY.md                 # Azure deployment guide
├── .env.example              # Environment variable template
└── requirements.txt
```

## 📄 License

MIT — use it, modify it, share it.

## 🚀 Getting Started

### Prerequisites

- Python 3.8 or higher
- Google API key for Google Generative AI
- Supadata API key for transcript retrieval

### Installation

```bash
git clone https://github.com/ShubhSarin/youtube-study-helper.git
cd youtube-study-helper
pip install -r requirements.txt
```

### Environment Variables

Create a `.env` file in the project root or provide these values through your deployment environment:

```bash
GOOGLE_API_KEY=your_google_api_key_here
SUPADATA_API_KEY=your_supadata_api_key_here
GENERATION_MODEL_NAME=gemma-4-31b-it
EMBEDDING_MODEL_NAME=models/gemini-embedding-001
```

Optional:

```bash
YOUTUBE_COOKIES_CONTENT="multiline_cookie_text_if_needed"
```

Notes:

- `GOOGLE_API_KEY` is used for both generation and embeddings.
- `SUPADATA_API_KEY` is required at startup for transcript retrieval.
- `GENERATION_MODEL_NAME` is optional and overrides the default generation model.
- `EMBEDDING_MODEL_NAME` is optional and overrides the default embedding model.
- `YOUTUBE_COOKIES_CONTENT` is optional and only matters for metadata-related flows that still rely on `yt-dlp`.

### Running the App

```bash
uvicorn api.main:app --port 8000
```

The API and the built React UI are served at `http://localhost:8000`.

## 📖 Usage

1. Paste a YouTube video or playlist URL.
2. Click `Process`.
3. Wait for transcript ingestion to finish.
4. Generate notes, flashcards, or quizzes for any processed video.
5. Ask questions in the chat section to query all available transcripts.

If transcript extraction fails for some videos, the app keeps the successful videos and surfaces errors for the failed ones.

## 🏗️ Project Structure

```text
youtube-study-helper/
├── api/
│   └── main.py               # FastAPI entrypoint: REST endpoints + SPA serving
├── web/                      # React (Vite + TypeScript + Tailwind) SPA
├── transcript_extractor.py   # Compatibility shim around the new transcript backend
├── requirements.txt          # Python dependencies
├── core/
│   ├── env_utils.py          # Repo-local environment loader with multiline .env support
│   ├── transcript.py         # Supadata transcript retrieval and batch transcript ingestion
│   ├── process.py            # Non-UI processing flow for video and playlist URLs
│   ├── summarizer.py         # Notes generation
│   ├── flashcards.py         # Flashcard generation
│   ├── quiz.py               # Quiz generation
│   ├── rag.py                # Embedding-based transcript retrieval and answer cleanup
│   ├── llm.py                # Generation and embedding helpers
│   ├── youtube_utils.py      # URL parsing and video metadata helpers
│   └── playlist.py           # Playlist expansion
└── agents/
    └── agent.py              # ADK agent definitions kept for consistency, not the live app path
```

## 🛠️ Technology Stack

- [React 19](https://react.dev/) + [Vite](https://vite.dev/) + [Tailwind CSS](https://tailwindcss.com/) for the SPA frontend
- [FastAPI](https://fastapi.tiangolo.com/) for the REST backend and static SPA serving
- [Google Generative AI](https://ai.google.dev/) for generation and embeddings
- `GENERATION_MODEL_NAME` with a default of `gemma-4-31b-it` for notes, flashcards, quizzes, and RAG answers
- `EMBEDDING_MODEL_NAME` with a default of `models/gemini-embedding-001` for transcript and query embeddings
- [Supadata Transcript API](https://api.supadata.ai/v1/transcript) for transcript retrieval
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) for playlist expansion and video metadata helpers
- `requests` for API calls

## 🔑 Key Modules

- [api/main.py](api/main.py): FastAPI app — REST endpoints for process/generate/ask, per-session state, SPA serving
- [web/src/App.tsx](web/src/App.tsx): React UI — URL processing, per-video generation tabs, RAG chat
- [core/transcript.py](core/transcript.py): fetches transcripts from Supadata and reports failures cleanly
- [core/llm.py](core/llm.py): wraps model generation, embedding calls, and safe fallback behavior
- [core/rag.py](core/rag.py): performs transcript chunking, embedding retrieval, answer generation, and answer sanitization
- [core/env_utils.py](core/env_utils.py): reads environment variables and local `.env` values without `python-dotenv`
- [core/process.py](core/process.py): keeps the non-UI processing path aligned with the app behavior

## 🧪 Operational Notes

- The app fails fast if `SUPADATA_API_KEY` is missing.
- Generation and embedding model selection can be overridden with `GENERATION_MODEL_NAME` and `EMBEDDING_MODEL_NAME`.
- Transcript retrieval errors are handled per video so a bad item does not stop a full playlist.
- The RAG layer caches transcript-chunk embeddings by transcript snapshot to avoid rebuilding the index on every question.
- ADK agents in [agents/agent.py](agents/agent.py) were updated to use the same model, but the live application path is FastAPI plus the `core` modules.

## 🎯 Use Cases

- 📚 Turn lecture videos into study material
- 👨‍🏫 Create quizzes and flashcards from teaching content
- 📖 Build notes from multi-video tutorial playlists
- 🧪 Search across technical talk transcripts with question answering
- 📝 Review long-form video content faster

## 🙏 Acknowledgments

- Google Generative AI for generation and embeddings
- Supadata for hosted-friendly transcript retrieval
- React, Vite, Tailwind CSS, and FastAPI for the app framework
