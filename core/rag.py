from dataclasses import dataclass
import logging
import math
import re

from core.llm import call_llm, embed_texts

CHUNK_WORD_COUNT = 200
CHUNK_OVERLAP = 50
TOP_K_CHUNKS = 5
MIN_CHUNK_WORDS = 40
MAX_INDEX_CACHE_SIZE = 8

LOGGER = logging.getLogger(__name__)
_EMBEDDING_INDEX_CACHE: dict[str, tuple[list["TranscriptChunk"], list[list[float]]]] = {}
PROMPT_ECHO_MARKERS = (
    "user question",
    "question:",
    "constraints",
    "constraint 1",
    "source 1",
    "draft:",
    "retrieved transcript excerpts",
)
PROMPT_ECHO_LINE_PATTERN = re.compile(
    r"^(?:[\*\-\u2022]\s*)?(?:"
    r"user question:|question:|context:|constraints?:|constraint \d+:|"
    r"source \d+:|draft:|definition:|features:|additional use:"
    r")",
    re.IGNORECASE,
)
RAG_SYSTEM_INSTRUCTION = """You answer questions using only provided transcript excerpts.
Return only the final answer text.
Do not restate the question.
Do not list constraints, source labels, notes, drafts, or your reasoning.
If the excerpts are insufficient, return exactly: I don't have that information in the transcripts.
Keep the answer concise and cite the relevant video title inline when you use information from it."""


@dataclass(frozen=True)
class TranscriptChunk:
    video_id: str
    title: str
    chunk_id: int
    text: str


def _chunk_text(text: str) -> list[str]:
    words = text.split()
    if not words:
        return []

    if len(words) <= CHUNK_WORD_COUNT:
        return [" ".join(words)]

    chunks = []
    step = max(CHUNK_WORD_COUNT - CHUNK_OVERLAP, 1)

    for start in range(0, len(words), step):
        chunk_words = words[start:start + CHUNK_WORD_COUNT]
        if not chunk_words:
            continue
        if len(chunk_words) < MIN_CHUNK_WORDS and chunks:
            chunks[-1] = f"{chunks[-1]} {' '.join(chunk_words)}".strip()
            break
        chunks.append(" ".join(chunk_words))

        if start + CHUNK_WORD_COUNT >= len(words):
            break

    return chunks


def _build_chunks(transcripts: dict, video_titles: dict) -> list[TranscriptChunk]:
    chunks = []

    for video_id, transcript in transcripts.items():
        if not transcript or transcript.startswith("Error:"):
            continue

        title = video_titles.get(video_id, video_id)
        for chunk_id, chunk_text in enumerate(_chunk_text(transcript), start=1):
            chunks.append(
                TranscriptChunk(
                    video_id=video_id,
                    title=title,
                    chunk_id=chunk_id,
                    text=chunk_text,
                )
            )

    return chunks


def _build_cache_key(transcripts: dict) -> str:
    ids = sorted(
        vid for vid, t in transcripts.items()
        if t and not t.startswith("Error:")
    )
    return ",".join(ids)


def _remember_embedding_index(
    cache_key: str,
    chunks: list[TranscriptChunk],
    embeddings: list[list[float]],
) -> None:
    if cache_key in _EMBEDDING_INDEX_CACHE:
        _EMBEDDING_INDEX_CACHE.pop(cache_key)

    _EMBEDDING_INDEX_CACHE[cache_key] = (chunks, embeddings)
    while len(_EMBEDDING_INDEX_CACHE) > MAX_INDEX_CACHE_SIZE:
        oldest_key = next(iter(_EMBEDDING_INDEX_CACHE))
        _EMBEDDING_INDEX_CACHE.pop(oldest_key)


def _get_embedding_index(
    transcripts: dict,
    video_titles: dict,
) -> tuple[list[TranscriptChunk], list[list[float]]]:
    cache_key = _build_cache_key(transcripts)
    cached_index = _EMBEDDING_INDEX_CACHE.get(cache_key)
    if cached_index:
        return cached_index

    chunks = _build_chunks(transcripts, video_titles)
    if not chunks:
        return [], []

    embeddings = embed_texts(
        [chunk.text for chunk in chunks],
        task_type="retrieval_document",
    )
    _remember_embedding_index(cache_key, chunks, embeddings)
    return chunks, embeddings


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0

    dot_product = sum(left_value * right_value for left_value, right_value in zip(left, right))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if not left_norm or not right_norm:
        return 0.0

    return dot_product / (left_norm * right_norm)


def _retrieve_relevant_chunks(
    question: str,
    transcripts: dict,
    video_titles: dict,
    top_k: int = TOP_K_CHUNKS,
) -> list[TranscriptChunk]:
    chunks, chunk_embeddings = _get_embedding_index(transcripts, video_titles)
    if not chunks:
        return []

    if not question.strip() or not chunk_embeddings:
        return chunks[:top_k]

    try:
        query_embedding = embed_texts([question], task_type="retrieval_query")[0]
    except Exception as exc:
        LOGGER.error("Failed to embed retrieval query: %s", exc)
        return chunks[:top_k]

    scored_chunks = [
        (_cosine_similarity(query_embedding, chunk_embedding), chunk)
        for chunk, chunk_embedding in zip(chunks, chunk_embeddings)
    ]

    scored_chunks.sort(key=lambda item: item[0], reverse=True)
    relevant = [chunk for score, chunk in scored_chunks if score > 0]
    if relevant:
        return relevant[:top_k]

    return chunks[:top_k]


def _build_context(question: str, transcripts: dict, video_titles: dict) -> str:
    relevant_chunks = _retrieve_relevant_chunks(question, transcripts, video_titles)
    if not relevant_chunks:
        return ""

    context_parts = []
    for idx, chunk in enumerate(relevant_chunks, start=1):
        context_parts.append(
            f"[Source {idx}] Video: {chunk.title} | Excerpt {chunk.chunk_id}\n{chunk.text}"
        )

    return "\n\n".join(context_parts)


def _is_prompt_echo_line(line: str) -> bool:
    normalized = line.lstrip("*-• ").strip()
    if PROMPT_ECHO_LINE_PATTERN.match(normalized):
        return True

    lower = normalized.lower()
    if re.match(r"^\d+\.\s", normalized) and any(
        phrase in lower
        for phrase in (
            "use only",
            "cite the video title",
            "if the excerpts",
            "if information is missing",
            "synthesize",
        )
    ):
        return True

    return False


def _sanitize_answer_text(answer: str) -> str:
    stripped = answer.strip()
    if not stripped:
        return "I don't have that information in the transcripts."

    lower = stripped.lower()
    if not any(marker in lower for marker in PROMPT_ECHO_MARKERS):
        return stripped

    paragraphs = [paragraph.strip() for paragraph in re.split(r"\n\s*\n", stripped) if paragraph.strip()]
    for paragraph in reversed(paragraphs):
        lines = [line.strip() for line in paragraph.splitlines() if line.strip()]
        cleaned_lines = [line.lstrip("*-• ").strip() for line in lines if not _is_prompt_echo_line(line)]
        cleaned_paragraph = " ".join(cleaned_lines).strip()
        if cleaned_paragraph:
            return cleaned_paragraph

    cleaned_lines = [
        line.lstrip("*-• ").strip()
        for line in stripped.splitlines()
        if line.strip() and not _is_prompt_echo_line(line)
    ]
    if cleaned_lines:
        return " ".join(cleaned_lines).strip()

    return stripped


def _sentence_tokens(text: str) -> set[str]:
    return set(re.findall(r"\b[a-z0-9]+\b", text.lower()))


def _is_similar_sentence(left: str, right: str) -> bool:
    left_tokens = _sentence_tokens(left)
    right_tokens = _sentence_tokens(right)
    if not left_tokens or not right_tokens:
        return left.strip().lower() == right.strip().lower()

    overlap = len(left_tokens & right_tokens)
    union = len(left_tokens | right_tokens)
    if not union:
        return False

    return (overlap / union) >= 0.8


def _finalize_answer_text(answer: str) -> str:
    sanitized = _sanitize_answer_text(answer)
    sentences = [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+", sanitized)
        if sentence.strip()
    ]

    unique_sentences: list[str] = []
    for sentence in sentences:
        if any(_is_similar_sentence(sentence, existing) for existing in unique_sentences):
            continue
        unique_sentences.append(sentence)

    if unique_sentences:
        return " ".join(unique_sentences[:3]).strip()

    return sanitized


def answer_question(question: str, transcripts: dict, video_titles: dict) -> str:
    """Answer a question by retrieving the most relevant transcript chunks first."""
    context = _build_context(question, transcripts, video_titles)
    if not context:
        return "I don't have that information in the transcripts."

    prompt = f"""<question>
{question}
</question>

<transcript_excerpts>
{context}
</transcript_excerpts>

Write a direct answer in 1-3 sentences.
Return only the final answer text.
Do not repeat the question.
Do not mention constraints, source numbers, transcript excerpts, or drafts.
Respond in English only. Never use Chinese.
If the excerpts are insufficient, return exactly: I don't have that information in the transcripts."""

    answer = call_llm(prompt, system_instruction=RAG_SYSTEM_INSTRUCTION)
    return _finalize_answer_text(answer)
