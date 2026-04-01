from .llm import call_llm


def summarize_transcript(transcript: str) -> str:
    if not transcript or transcript.startswith("Error:"):
        return "Cannot generate notes because transcript extraction failed."

    prompt = f"""
You are given a YouTube lecture transcript.

Create chapter-wise study notes.
Use headings, sub-headings, and bullet points.
Do NOT add information not present in the transcript.

Transcript:
{transcript}
"""
    return call_llm(prompt)
