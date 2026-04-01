from core.youtube_utils import is_playlist, extract_video_id
from core.playlist import get_video_ids_from_playlist
from core.transcript import extract_transcript_from_id
from core.summarizer import summarize_transcript
from core.flashcards import generate_flashcards
from core.quiz import generate_quiz


def process_youtube_url(url: str) -> dict:
    """
    Returns:
    {
      video_id: {
        transcript,
        summary,
        flashcards,
        quiz
      },
      ...
    }
    """

    results = {}

    if is_playlist(url):
        video_ids = get_video_ids_from_playlist(url)
    else:
        video_ids = [extract_video_id(url)]

    for vid in video_ids:
        transcript = extract_transcript_from_id(vid)

        if not transcript or transcript.startswith("Error:"):
            results[vid] = {
                "transcript": transcript,
                "summary": "Cannot generate notes because transcript extraction failed.",
                "flashcards": "Cannot generate flashcards because transcript extraction failed.",
                "quiz": "Cannot generate quiz because transcript extraction failed.",
            }
            continue

        results[vid] = {
            "transcript": transcript,
            "summary": summarize_transcript(transcript),
            "flashcards": generate_flashcards(transcript),
            "quiz": generate_quiz(transcript),
        }

    return results
