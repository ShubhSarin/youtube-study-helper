from core.transcript import extract_transcript_from_id
from core.youtube_utils import extract_video_id


def get_video_id(youtube_url: str) -> str:
    return extract_video_id(youtube_url)


def extract_transcript(youtube_url: str) -> str:
    video_id = get_video_id(youtube_url)
    return extract_transcript_from_id(video_id)
