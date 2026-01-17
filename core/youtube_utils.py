from urllib.parse import urlparse, parse_qs
import yt_dlp


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
    try:
        url = f"https://www.youtube.com/watch?v={video_id}"
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return info.get('title', f"Video {video_id}")
    except Exception as e:
        print(f"Error fetching title for {video_id}: {e}")
        return f"Video {video_id}"  # Fallback to video ID if title fetch fails
