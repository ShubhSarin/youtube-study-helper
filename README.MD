# 🎓 YouTube Study Helper

YouTube Study Helper is a Streamlit app that turns YouTube videos and playlists into study material. It fetches transcripts, generates notes, flashcards, and quizzes on demand, and answers follow-up questions with retrieval over transcript excerpts instead of relying on coarse summaries.

## ✨ Current Features

- 📺 Process a single YouTube video or an entire playlist
- 📝 Generate study notes from the transcript of each processed video
- 🧠 Generate flashcards on demand for each video
- 📊 Generate quizzes on demand for each video
- 💬 Ask questions across all processed videos with embedding-based RAG
- 🎯 Work across multiple videos in one session
- ☁️ Use Supadata transcript retrieval so hosted deployments are not blocked by transcript scraping limitations
- 🧷 Keep the UI stable during long-running generation by disabling the full action row while work is in progress

## 🧠 Current Implementation Logic

The live app is driven by [streamlit_app.py](streamlit_app.py) and the [core](core) modules.

1. The user pastes a video or playlist URL into the Streamlit app.
2. The app decides whether the URL is a single video or a playlist.
3. Playlist expansion and video-title lookup are handled through [core/playlist.py](core/playlist.py) and [core/youtube_utils.py](core/youtube_utils.py), with `yt-dlp` still used for metadata-related work.
4. Transcript retrieval is handled by [core/transcript.py](core/transcript.py), which calls the Supadata transcript API using `SUPADATA_API_KEY`.
5. The app stores successful transcripts and transcript failures separately in Streamlit session state.
6. Notes, flashcards, and quizzes are generated only when the user clicks the corresponding button for a video.
7. While one generation task is running, all three buttons for the current UI state are disabled so the layout does not duplicate or shift during reruns.
8. For chat, [core/rag.py](core/rag.py) chunks the available transcripts, embeds those chunks, embeds the user question, ranks chunks by cosine similarity, and builds a focused context window from the most relevant excerpts.
9. The final answer is generated with the model configured by `GENERATION_MODEL_NAME` through [core/llm.py](core/llm.py), which defaults to `gemma-4-31b-it`, then sanitized to remove prompt-echo artifacts and repeated sentences before being shown in the UI.

## 🔎 RAG Logic

The question-answering flow is no longer summary-based. It now works like this:

1. Transcript text is split into overlapping chunks.
2. Each chunk is embedded with the model configured by `EMBEDDING_MODEL_NAME`, which defaults to `models/gemini-embedding-001`, using the `retrieval_document` task type.
3. The user question is embedded with the `retrieval_query` task type.
4. Chunks are ranked by cosine similarity against the query embedding.
5. The top transcript excerpts are passed to the generation model.
6. The answer is cleaned so internal prompt structure such as `Question:`, `Constraint:`, `Source:`, and `Draft:` does not leak into the final response.

This makes the app answer from the transcript evidence itself instead of pushing the full transcript into one prompt or relying on pre-generated summaries.

## ⚙️ Environment Loading

The project does not depend on `python-dotenv` at runtime anymore.

- [core/env_utils.py](core/env_utils.py) reads values from the real environment first.
- If a variable is not present in the runtime environment, it falls back to reading the local `.env` file directly.
- The custom loader supports multiline quoted values, which is important for `YOUTUBE_COOKIES_CONTENT`.
- If `YOUTUBE_COOKIES_CONTENT` is present, [streamlit_app.py](streamlit_app.py) syncs it into `youtube_cookies.txt` only when the contents change.

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
streamlit run streamlit_app.py
```

By default, Streamlit opens the app in your browser on a local port such as `8501`.

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
├── streamlit_app.py          # Active Streamlit entrypoint and session-state UI flow
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

- [Streamlit](https://streamlit.io/) for the UI
- [Google Generative AI](https://ai.google.dev/) for generation and embeddings
- `GENERATION_MODEL_NAME` with a default of `gemma-4-31b-it` for notes, flashcards, quizzes, and RAG answers
- `EMBEDDING_MODEL_NAME` with a default of `models/gemini-embedding-001` for transcript and query embeddings
- [Supadata Transcript API](https://api.supadata.ai/v1/transcript) for transcript retrieval
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) for playlist expansion and video metadata helpers
- `requests` for API calls

## 🔑 Key Modules

- [streamlit_app.py](streamlit_app.py): orchestrates the app, session state, per-video actions, and chat flow
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
- ADK agents in [agents/agent.py](agents/agent.py) were updated to use the same model, but the live application path is still Streamlit plus the `core` modules.

## 🎯 Use Cases

- 📚 Turn lecture videos into study material
- 👨‍🏫 Create quizzes and flashcards from teaching content
- 📖 Build notes from multi-video tutorial playlists
- 🧪 Search across technical talk transcripts with question answering
- 📝 Review long-form video content faster

## 🙏 Acknowledgments

- Google Generative AI for generation and embeddings
- Supadata for hosted-friendly transcript retrieval
- Streamlit for the web app framework
