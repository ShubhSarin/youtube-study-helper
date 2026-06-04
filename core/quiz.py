from .llm import call_llm


def generate_quiz(transcript: str) -> str:
    if not transcript or transcript.startswith("Error:"):
        return "Cannot generate quiz because transcript extraction failed."

    prompt = f"""
Generate 5 multiple-choice questions from the transcript.
Each question should have 4 options and one correct answer.
Respond in English only. Never use Chinese.

Transcript:
{transcript}
"""
    return call_llm(prompt)
