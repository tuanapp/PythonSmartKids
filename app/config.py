import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///math_attempts.db")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "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")
