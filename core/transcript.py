from youtube_transcript_api import YouTubeTranscriptApi
from urllib.parse import urlparse, parse_qs
import os

COOKIE_FILE_PATH = "../youtube_cookies.txt"

def get_video_id(youtube_url: str) -> str:
    parsed = urlparse(youtube_url)

    if parsed.hostname in ["www.youtube.com", "youtube.com"]:
        return parse_qs(parsed.query)["v"][0]

    if parsed.hostname == "youtu.be":
        return parsed.path[1:]

    raise ValueError("Invalid YouTube URL")


def extract_transcript_from_id(video_id: str) -> str:
    try:
        # Check if we have the cookies file from our Railway environment variable
        if os.path.exists(COOKIE_FILE_PATH):
            # Use the static method which accepts a file path for cookies
            transcript = YouTubeTranscriptApi.get_transcript(
                video_id, 
                cookies=COOKIE_FILE_PATH
            )
        else:
            # Fallback for local development
            transcript = YouTubeTranscriptApi.get_transcript(video_id)
            
        return " ".join(chunk['text'] for chunk in transcript)
        
    except Exception as e:
        # This will catch the error and show it in your Streamlit UI
        return f"Error: {e}"
