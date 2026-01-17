import os
from pathlib import Path
from dotenv import load_dotenv

ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=ENV_PATH)

print("CWD:", os.getcwd())
print("ENV PATH:", ENV_PATH)
print("KEY FOUND:", bool(os.getenv("GOOGLE_API_KEY")))
print("KEY VALUE:", os.getenv("GOOGLE_API_KEY"))
