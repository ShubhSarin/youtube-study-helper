from urllib.parse import urlparse, parse_qs
import re
import yt_dlp
import requests
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
COOKIE_FILE_PATH = PROJECT_ROOT / "youtube_cookies.txt"

VIDEO_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{11}")
PLAYLIST_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+")
URL_PATTERN = re.compile(r"https?://[^\s\"'<>]+", re.IGNORECASE)


def _normalize_url_input(url: str) -> str:
    cleaned_url = (url or "").strip()
    if not cleaned_url:
        return ""

    cleaned_url = cleaned_url.strip('"\'<>[]{}()')
    url_match = URL_PATTERN.search(cleaned_url)
    if url_match:
        cleaned_url = url_match.group(0).rstrip('"\').,;')

    if "://" not in cleaned_url and cleaned_url.startswith(("www.youtube.com", "youtube.com", "m.youtube.com", "music.youtube.com", "youtu.be")):
        cleaned_url = f"https://{cleaned_url}"

    return cleaned_url


def _parse_youtube_url(url: str):
    normalized_url = _normalize_url_input(url)
    return urlparse(normalized_url), parse_qs(urlparse(normalized_url).query)


def _normalize_hostname(hostname: str | None) -> str:
    if not hostname:
        return ""

    return hostname.lower().removeprefix("www.")


def _coerce_video_id(value: str | None) -> str | None:
    if not value:
        return None

    match = VIDEO_ID_PATTERN.match(value.strip())
    if match:
        return match.group(0)
    return None


def _coerce_playlist_id(value: str | None) -> str | None:
    if not value:
        return None

    match = PLAYLIST_ID_PATTERN.match(value.strip())
    if match:
        return match.group(0)
    return None


def _extract_video_id_from_parts(parsed, qs) -> str | None:
    if "v" in qs:
        video_id = _coerce_video_id(qs["v"][0])
        if video_id:
            return video_id

    hostname = _normalize_hostname(parsed.hostname)
    path_parts = [part for part in parsed.path.split("/") if part]

    if hostname == "youtu.be" and path_parts:
        return _coerce_video_id(path_parts[0])

    if hostname in {"youtube.com", "m.youtube.com", "music.youtube.com"} and len(path_parts) >= 2 and path_parts[0] in {"shorts", "embed", "live", "v"}:
        return _coerce_video_id(path_parts[1])

    return None

def is_playlist(url: str) -> bool:
    parsed, qs = _parse_youtube_url(url)
    if "list" not in qs:
        return False

    normalized_path = parsed.path.rstrip("/").lower()
    if normalized_path == "/playlist":
        return True

    return _extract_video_id_from_parts(parsed, qs) is None


def extract_video_id(url: str) -> str:
    parsed, qs = _parse_youtube_url(url)
    video_id = _extract_video_id_from_parts(parsed, qs)
    if video_id:
        return video_id

    raise ValueError("Invalid YouTube video URL")


def extract_playlist_id(url: str) -> str:
    parsed, qs = _parse_youtube_url(url)

    if "list" in qs:
        playlist_id = _coerce_playlist_id(qs["list"][0])
        if playlist_id:
            return playlist_id

    raise ValueError("Invalid playlist URL")


def get_video_title(video_id: str) -> str:
    """Get the title of a YouTube video from its ID"""
    url = f"https://www.youtube.com/watch?v={video_id}"

    # First try oEmbed, which returns metadata without any media format negotiation.
    try:
        oembed_url = "https://www.youtube.com/oembed"
        response = requests.get(
            oembed_url,
            params={"url": url, "format": "json"},
            timeout=10,
        )
        if response.ok:
            title = response.json().get("title")
            if title:
                return title
    except Exception:
        pass

    # Fallback to yt-dlp metadata extraction.
    try:
        base_opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
            'ignoreconfig': True,
            'extract_flat': True,
            'noplaylist': True,
        }

        ydl_opts = dict(base_opts)
        if COOKIE_FILE_PATH.exists():
            ydl_opts['cookiefile'] = str(COOKIE_FILE_PATH)

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return info.get('title', f"Video {video_id}")
        except Exception:
            # Retry once without cookies in case cookie auth causes extraction issues.
            with yt_dlp.YoutubeDL(base_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return info.get('title', f"Video {video_id}")
    except Exception as e:
        print(f"Error fetching title for {video_id}: {e}")
        return f"Video {video_id}"  # Fallback to video ID if title fetch fails
