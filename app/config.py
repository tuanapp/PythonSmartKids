import os
from dotenv import load_dotenv

load_dotenv()

# Database settings
DATABASE_PROVIDER = os.getenv("DATABASE_PROVIDER", "neon")  # Only 'neon' is supported now

# Neon PostgreSQL specific settings
DATABASE_URL = os.getenv("DATABASE_URL", "")
NEON_DBNAME = os.getenv("NEON_DBNAME", "smartboydb")
NEON_USER = os.getenv("NEON_USER", "tuanapp")
NEON_PASSWORD = os.getenv("NEON_PASSWORD", "HdzrNIKh5mM1")
NEON_HOST = os.getenv("NEON_HOST", "ep-sparkling-butterfly-33773987-pooler.ap-southeast-1.aws.neon.tech")
NEON_SSLMODE = os.getenv("NEON_SSLMODE", "require")

# OpenAI settings
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1/")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "")

# AI Bridge settings
AI_BRIDGE_BASE_URL = os.getenv("FORGE_BASE_URL", "https://api.forge.tensorblock.co/v1")
AI_BRIDGE_API_KEY = os.getenv("FORGE_API_KEY", "")
AI_BRIDGE_MODEL = os.getenv("FORGE_AI_MODEL", "Gemini/models/gemini-2.0-flash") #OpenRouter/qwen/qwen3-4b:free

HTTP_REFERER = os.getenv("HTTP_REFERER", "https://github.com/tuanna0308/PythonSmartKids")
APP_TITLE = os.getenv("APP_TITLE", "PythonSmartKids")

# Testing settings
RUN_REAL_API_TESTS = os.getenv("RUN_REAL_API_TESTS", "False").lower() == "true"
