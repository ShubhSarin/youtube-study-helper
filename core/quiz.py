from .llm import call_llm


def generate_quiz(transcript: str) -> str:
    prompt = f"""
Generate 5 multiple-choice questions from the transcript.
Each question should have 4 options and one correct answer.

Transcript:
{transcript}
"""
    return call_llm(prompt)
