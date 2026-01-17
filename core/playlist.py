import yt_dlp
from core.youtube_utils import extract_playlist_id


def get_video_ids_from_playlist(playlist_url: str) -> list[str]:
    """Extract video IDs from a YouTube playlist"""
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'skip_download': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(playlist_url, download=False)
            if 'entries' in info:
                return [entry['id'] for entry in info['entries'] if entry]
            return []
    except Exception as e:
        print(f"Error extracting playlist: {e}")
        return []
