from youtube_transcript_api import YouTubeTranscriptApi
from urllib.parse import urlparse, parse_qs


def get_video_id(youtube_url: str) -> str:
    parsed = urlparse(youtube_url)

    if parsed.hostname in ["www.youtube.com", "youtube.com"]:
        return parse_qs(parsed.query)["v"][0]

    if parsed.hostname == "youtu.be":
        return parsed.path[1:]

    raise ValueError("Invalid YouTube URL")


def extract_transcript_from_id(video_id: str) -> str:
    api = YouTubeTranscriptApi()
    transcript = api.fetch(video_id)
    return " ".join(chunk.text for chunk in transcript)
