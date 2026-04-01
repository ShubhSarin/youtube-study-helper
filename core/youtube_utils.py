from urllib.parse import urlparse, parse_qs
import yt_dlp
import requests
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
COOKIE_FILE_PATH = PROJECT_ROOT / "youtube_cookies.txt"

def is_playlist(url: str) -> bool:
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    return "list" in qs


def extract_video_id(url: str) -> str:
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)

    if "v" in qs:
        return qs["v"][0]

    if parsed.hostname == "youtu.be":
        return parsed.path[1:]

    raise ValueError("Invalid YouTube video URL")


def extract_playlist_id(url: str) -> str:
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)

    if "list" in qs:
        return qs["list"][0]

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
