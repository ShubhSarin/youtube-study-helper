import os
import logging
import time
from openai import OpenAI
import google.generativeai as genai
from google.api_core import exceptions as google_api_exceptions
from core.env_utils import ENV_PATH, read_env_value

# ---------------------------------------------------------------------------
# Model defaults
# ---------------------------------------------------------------------------
DEFAULT_GENERATION_MODEL_NAME = "xiaomi/mimo-v2.5"
DEFAULT_EMBEDDING_MODEL_NAME = "openai/text-embedding-3-small"
GENERATION_MODEL_NAME = read_env_value("GENERATION_MODEL_NAME") or DEFAULT_GENERATION_MODEL_NAME
EMBEDDING_MODEL_NAME = read_env_value("EMBEDDING_MODEL_NAME") or DEFAULT_EMBEDDING_MODEL_NAME

# ---------------------------------------------------------------------------
# Generation / retry knobs
# ---------------------------------------------------------------------------
EMBEDDING_BATCH_SIZE = 16
GENERATION_TEMPERATURE = 0.2
GENERATION_MAX_ATTEMPTS = 3
GENERATION_RETRY_DELAY_SECONDS = 1.0
LLM_UNAVAILABLE_MESSAGE = "The model is temporarily unavailable right now. Please try your request again in a moment."

LOGGER = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Detect which provider to use
# ---------------------------------------------------------------------------
_openrouter_api_key = os.getenv("OPENROUTER_API_KEY") or read_env_value("OPENROUTER_API_KEY")
_openrouter_base_url = (
    os.getenv("OPENROUTER_BASE_URL")
    or read_env_value("OPENROUTER_BASE_URL")
    or "https://openrouter.ai/api/v1"
)
_openrouter_model_name = (
    os.getenv("OPENROUTER_MODEL_NAME")
    or read_env_value("OPENROUTER_MODEL_NAME")
    or "xiaomi/mimo-v2.5"
)
_openrouter_embedding_model_name = (
    os.getenv("OPENROUTER_EMBEDDING_MODEL_NAME")
    or read_env_value("OPENROUTER_EMBEDDING_MODEL_NAME")
    or "openai/text-embedding-3-small"
)

USE_OPENROUTER = bool(_openrouter_api_key)

# ---------------------------------------------------------------------------
# Initialise the chosen client
# ---------------------------------------------------------------------------
if USE_OPENROUTER:
    LOGGER.info("Using OpenRouter provider (base_url=%s, model=%s)", _openrouter_base_url, _openrouter_model_name)
    _openai_client = OpenAI(
        base_url=_openrouter_base_url,
        api_key=_openrouter_api_key,
    )
else:
    google_api_key = os.getenv("GOOGLE_API_KEY") or read_env_value("GOOGLE_API_KEY")
    if not google_api_key:
        raise RuntimeError(f"Neither OPENROUTER_API_KEY nor GOOGLE_API_KEY found. Checked: {ENV_PATH}")
    genai.configure(api_key=google_api_key)
    _gemini_model = genai.GenerativeModel(GENERATION_MODEL_NAME)
    LOGGER.info("Using Google Gemini provider (model=%s)", GENERATION_MODEL_NAME)


# ===================================================================
#  Helper utilities
# ===================================================================


def _batched_texts(texts: list[str], batch_size: int) -> list[list[str]]:
    return [texts[index : index + batch_size] for index in range(0, len(texts), batch_size)]


def _normalize_embedding_vector(item: object) -> list[float]:
    if isinstance(item, dict):
        values = item.get("values")
        if isinstance(values, list):
            return [float(value) for value in values]

    if isinstance(item, list):
        return [float(value) for value in item]

    raise RuntimeError(f"Unsupported embedding vector format: {type(item).__name__}")


def _is_retryable_generation_error(exc: Exception) -> bool:
    return isinstance(
        exc,
        (
            google_api_exceptions.InternalServerError,
            google_api_exceptions.ServiceUnavailable,
            google_api_exceptions.TooManyRequests,
            google_api_exceptions.DeadlineExceeded,
        ),
    )


# ===================================================================
#  Embeddings
# ===================================================================


def _extract_embedding_vectors_gemini(response: object) -> list[list[float]]:
    payload = response.to_dict() if hasattr(response, "to_dict") else response

    if not isinstance(payload, dict) or "embedding" not in payload:
        raise RuntimeError(f"Unexpected embedding response type: {type(payload).__name__}")

    embedding_payload = payload["embedding"]

    if isinstance(embedding_payload, dict):
        return [_normalize_embedding_vector(embedding_payload)]

    if isinstance(embedding_payload, list):
        return [_normalize_embedding_vector(item) for item in embedding_payload]

    raise RuntimeError(f"Unexpected embedding payload type: {type(embedding_payload).__name__}")


def _embed_texts_gemini(texts: list[str], task_type: str) -> list[list[float]]:
    embeddings: list[list[float]] = []
    for batch in _batched_texts(texts, EMBEDDING_BATCH_SIZE):
        response = genai.embed_content(
            model=EMBEDDING_MODEL_NAME,
            content=batch,
            task_type=task_type,
        )
        batch_embeddings = _extract_embedding_vectors_gemini(response)
        if len(batch_embeddings) != len(batch):
            raise RuntimeError(
                f"Embedding count mismatch. Expected {len(batch)}, received {len(batch_embeddings)}."
            )
        embeddings.extend(batch_embeddings)
    return embeddings


def _embed_texts_openrouter(texts: list[str], task_type: str) -> list[list[float]]:
    """Embed texts via OpenRouter's OpenAI-compatible embeddings endpoint.

    ``task_type`` is accepted for API compatibility with the Gemini codepath but
    is not forwarded (OpenAI-compatible endpoints do not support it).
    """
    _ = task_type  # unused – kept for signature parity
    embeddings: list[list[float]] = []
    for batch in _batched_texts(texts, EMBEDDING_BATCH_SIZE):
        response = _openai_client.embeddings.create(
            model=_openrouter_embedding_model_name,
            input=batch,
        )
        batch_embeddings = [data.embedding for data in response.data]
        embeddings.extend(batch_embeddings)
    return embeddings


def embed_texts(texts: list[str], task_type: str) -> list[list[float]]:
    if not texts:
        return []
    if USE_OPENROUTER:
        return _embed_texts_openrouter(texts, task_type)
    return _embed_texts_gemini(texts, task_type)


# ===================================================================
#  Text generation
# ===================================================================


def _generate_text_gemini(llm_model: object, prompt: str) -> str:
    for attempt in range(1, GENERATION_MAX_ATTEMPTS + 1):
        try:
            response = llm_model.generate_content(
                prompt,
                generation_config={"temperature": GENERATION_TEMPERATURE},
            )
            return response.text
        except Exception as exc:
            if not _is_retryable_generation_error(exc) or attempt == GENERATION_MAX_ATTEMPTS:
                raise
            LOGGER.warning(
                "Retrying generation after transient API failure (%s/%s): %s",
                attempt,
                GENERATION_MAX_ATTEMPTS,
                exc,
            )
            time.sleep(GENERATION_RETRY_DELAY_SECONDS * attempt)
    # Should never reach here, but satisfy the type-checker
    raise RuntimeError("Unreachable – generation exhausted all retries")


def _generate_text_openrouter(prompt: str, system_instruction: str | None = None) -> str:
    messages: list[dict] = []
    if system_instruction:
        messages.append({"role": "system", "content": system_instruction})
    messages.append({"role": "user", "content": prompt})

    for attempt in range(1, GENERATION_MAX_ATTEMPTS + 1):
        try:
            response = _openai_client.chat.completions.create(
                model=_openrouter_model_name,
                messages=messages,
                temperature=GENERATION_TEMPERATURE,
            )
            choice = response.choices[0]
            content = choice.message.content
            if content is None:
                raise RuntimeError("OpenRouter returned an empty response.")
            return content
        except Exception as exc:
            if attempt == GENERATION_MAX_ATTEMPTS:
                raise
            LOGGER.warning(
                "Retrying OpenRouter generation after transient failure (%s/%s): %s",
                attempt,
                GENERATION_MAX_ATTEMPTS,
                exc,
            )
            time.sleep(GENERATION_RETRY_DELAY_SECONDS * attempt)
    raise RuntimeError("Unreachable – generation exhausted all retries")


def call_llm(prompt: str, system_instruction: str | None = None) -> str:
    # ── OpenRouter path ────────────────────────────────────────────
    if USE_OPENROUTER:
        try:
            return _generate_text_openrouter(prompt, system_instruction)
        except Exception as exc:
            LOGGER.error("OpenRouter generation failed: %s", exc)
            return LLM_UNAVAILABLE_MESSAGE

    # ── Google Gemini path ─────────────────────────────────────────
    if system_instruction:
        try:
            llm_model = genai.GenerativeModel(
                GENERATION_MODEL_NAME,
                system_instruction=system_instruction,
            )
            return _generate_text_gemini(llm_model, prompt)
        except Exception as exc:
            LOGGER.warning(
                "Falling back to prompt-only generation after system-instruction failure: %s", exc
            )

    try:
        return _generate_text_gemini(_gemini_model, prompt)
    except google_api_exceptions.GoogleAPICallError as exc:
        LOGGER.error("Prompt-only generation failed after retries: %s", exc)
        return LLM_UNAVAILABLE_MESSAGE
