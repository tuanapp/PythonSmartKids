import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///math_attempts.db")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
