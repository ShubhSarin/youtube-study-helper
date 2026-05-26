import os
import logging
import time
import google.generativeai as genai
from google.api_core import exceptions as google_api_exceptions
from core.env_utils import ENV_PATH, read_env_value

DEFAULT_GENERATION_MODEL_NAME = "gemma-4-31b-it"
DEFAULT_EMBEDDING_MODEL_NAME = "models/gemini-embedding-001"
GENERATION_MODEL_NAME = read_env_value("GENERATION_MODEL_NAME") or DEFAULT_GENERATION_MODEL_NAME
EMBEDDING_MODEL_NAME = read_env_value("EMBEDDING_MODEL_NAME") or DEFAULT_EMBEDDING_MODEL_NAME
EMBEDDING_BATCH_SIZE = 16
GENERATION_TEMPERATURE = 0.2
GENERATION_MAX_ATTEMPTS = 3
GENERATION_RETRY_DELAY_SECONDS = 1.0
LLM_UNAVAILABLE_MESSAGE = "The model is temporarily unavailable right now. Please try your request again in a moment."

api_key = os.getenv("GOOGLE_API_KEY") or read_env_value("GOOGLE_API_KEY")
LOGGER = logging.getLogger(__name__)

if not api_key:
    raise RuntimeError(f"GOOGLE_API_KEY not found. Checked: {ENV_PATH}")

genai.configure(api_key=api_key)

model = genai.GenerativeModel(GENERATION_MODEL_NAME)


def _batched_texts(texts: list[str], batch_size: int) -> list[list[str]]:
    return [texts[index:index + batch_size] for index in range(0, len(texts), batch_size)]


def _normalize_embedding_vector(item: object) -> list[float]:
    if isinstance(item, dict):
        values = item.get("values")
        if isinstance(values, list):
            return [float(value) for value in values]

    if isinstance(item, list):
        return [float(value) for value in item]

    raise RuntimeError(f"Unsupported embedding vector format: {type(item).__name__}")


def _extract_embedding_vectors(response: object) -> list[list[float]]:
    payload = response.to_dict() if hasattr(response, "to_dict") else response

    if not isinstance(payload, dict) or "embedding" not in payload:
        raise RuntimeError(f"Unexpected embedding response type: {type(payload).__name__}")

    embedding_payload = payload["embedding"]

    if isinstance(embedding_payload, dict):
        return [_normalize_embedding_vector(embedding_payload)]

    if isinstance(embedding_payload, list):
        return [_normalize_embedding_vector(item) for item in embedding_payload]

    raise RuntimeError(f"Unexpected embedding payload type: {type(embedding_payload).__name__}")


def embed_texts(texts: list[str], task_type: str) -> list[list[float]]:
    if not texts:
        return []

    embeddings: list[list[float]] = []
    for batch in _batched_texts(texts, EMBEDDING_BATCH_SIZE):
        response = genai.embed_content(
            model=EMBEDDING_MODEL_NAME,
            content=batch,
            task_type=task_type,
        )
        batch_embeddings = _extract_embedding_vectors(response)
        if len(batch_embeddings) != len(batch):
            raise RuntimeError(
                f"Embedding count mismatch. Expected {len(batch)}, received {len(batch_embeddings)}."
            )
        embeddings.extend(batch_embeddings)

    return embeddings


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


def _generate_text(llm_model: object, prompt: str) -> str:
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

def call_llm(prompt: str, system_instruction: str | None = None) -> str:
    if system_instruction:
        try:
            llm_model = genai.GenerativeModel(
                GENERATION_MODEL_NAME,
                system_instruction=system_instruction,
            )
            return _generate_text(llm_model, prompt)
        except Exception as exc:
            LOGGER.warning("Falling back to prompt-only generation after system-instruction failure: %s", exc)

    try:
        return _generate_text(model, prompt)
    except google_api_exceptions.GoogleAPICallError as exc:
        LOGGER.error("Prompt-only generation failed after retries: %s", exc)
        return LLM_UNAVAILABLE_MESSAGE
