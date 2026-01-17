import os
from dotenv import load_dotenv
from pathlib import Path
import google.generativeai as genai

# 🔒 Explicit path to project root .env
ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(dotenv_path=ENV_PATH)

api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    raise RuntimeError(f"GOOGLE_API_KEY not found. Checked: {ENV_PATH}")

genai.configure(api_key=api_key)

model = genai.GenerativeModel("gemini-2.5-flash")

def call_llm(prompt: str) -> str:
    return model.generate_content(prompt).text
