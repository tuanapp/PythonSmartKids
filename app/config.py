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
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
