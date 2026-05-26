import logging

import requests
from core.env_utils import ENV_PATH, read_env_value

SUPADATA_TRANSCRIPT_URL = "https://api.supadata.ai/v1/transcript"
SUPADATA_TIMEOUT_SECONDS = 20

LOGGER = logging.getLogger(__name__)


SUPADATA_API_KEY = read_env_value("SUPADATA_API_KEY")
if not SUPADATA_API_KEY:
    raise RuntimeError(
        f"SUPADATA_API_KEY not found. Set it in the environment or {ENV_PATH} before starting the server."
    )


def _build_watch_url(video_id: str) -> str:
    return f"https://www.youtube.com/watch?v={video_id}"


def _normalize_transcript_payload(payload: dict) -> str | None:
    content = payload.get("content")
    if not isinstance(content, list) or not content:
        return None

    parts = []
    for item in content:
        if not isinstance(item, dict):
            continue
        text = item.get("text", "")
        if isinstance(text, str) and text.strip():
            parts.append(text.strip())

    transcript = " ".join(parts).strip()
    return transcript or None


def _fetch_transcript_from_supadata(video_url: str) -> str | None:
    try:
        response = requests.get(
            SUPADATA_TRANSCRIPT_URL,
            headers={"x-api-key": SUPADATA_API_KEY},
            params={"url": video_url},
            timeout=SUPADATA_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = response.json()
    except requests.Timeout as exc:
        LOGGER.error("Timed out fetching transcript for %s via Supadata: %s", video_url, exc)
        return None
    except requests.ConnectionError as exc:
        LOGGER.error("Connection error fetching transcript for %s via Supadata: %s", video_url, exc)
        return None
    except requests.HTTPError as exc:
        status_code = exc.response.status_code if exc.response is not None else "unknown"
        response_body = exc.response.text[:200].replace("\n", " ") if exc.response is not None else ""
        LOGGER.error(
            "Supadata returned HTTP %s for %s. Response: %s",
            status_code,
            video_url,
            response_body,
        )
        return None
    except requests.RequestException as exc:
        LOGGER.error("Unexpected request error fetching transcript for %s via Supadata: %s", video_url, exc)
        return None
    except ValueError as exc:
        LOGGER.error("Supadata returned invalid JSON for %s: %s", video_url, exc)
        return None

    transcript = _normalize_transcript_payload(payload)
    if transcript:
        return transcript

    LOGGER.error("Supadata returned no transcript content for %s", video_url)
    return None


def _format_transcript_error(video_id: str) -> str:
    return f"Error: Could not fetch transcript for video {video_id} from Supadata."


def extract_transcripts_from_ids(video_ids: list[str]) -> tuple[dict[str, str], dict[str, str]]:
    transcripts: dict[str, str] = {}
    transcript_errors: dict[str, str] = {}

    for video_id in video_ids:
        transcript = _fetch_transcript_from_supadata(_build_watch_url(video_id))
        if transcript:
            transcripts[video_id] = transcript
            continue

        error_message = _format_transcript_error(video_id)
        LOGGER.warning("%s Skipping this video.", error_message)
        transcript_errors[video_id] = error_message

    return transcripts, transcript_errors


def extract_transcript_from_id(video_id: str) -> str:
    transcript = _fetch_transcript_from_supadata(_build_watch_url(video_id))
    if transcript:
        return transcript

    return _format_transcript_error(video_id)
