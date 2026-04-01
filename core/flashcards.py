from .llm import call_llm


def generate_flashcards(transcript: str) -> str:
    if not transcript or transcript.startswith("Error:"):
        return "Cannot generate flashcards because transcript extraction failed."

    prompt = f"""
Generate flashcards (question–answer pairs) from the transcript.
Keep them concise and factual.

Transcript:
{transcript}
"""
    return call_llm(prompt)
