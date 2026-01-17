from youtube_transcript_api import YouTubeTranscriptApi
from urllib.parse import urlparse, parse_qs


def get_video_id(youtube_url: str) -> str:
    parsed = urlparse(youtube_url)

    if parsed.hostname in ["www.youtube.com", "youtube.com"]:
        return parse_qs(parsed.query)["v"][0]

    if parsed.hostname == "youtu.be":
        return parsed.path[1:]

    raise ValueError("Invalid YouTube URL")


def extract_transcript(youtube_url: str) -> str:
    video_id = get_video_id(youtube_url)

    api = YouTubeTranscriptApi()      # ✅ instantiate
    transcript = api.fetch(video_id)  # ✅ instance method

    full_text = " ".join(chunk.text for chunk in transcript)
    return full_text
