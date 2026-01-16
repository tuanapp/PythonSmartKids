import os
from dotenv import load_dotenv

# Load environment-specific configuration
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

if ENVIRONMENT == "development":
    load_dotenv(".env.development")
elif ENVIRONMENT == "production":
    load_dotenv(".env.production")
else:
    load_dotenv()  # Fallback to default .env

# Database settings - PostgreSQL only
DATABASE_URL = os.getenv("DATABASE_URL", "")
# DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://smartboy_dev:smartboy_dev@localhost:5432/smartboy_dev")

# Neon PostgreSQL specific settings
NEON_DBNAME = os.getenv("NEON_DBNAME", "smartboydb")
NEON_USER = os.getenv("NEON_USER", "tuanapp")
NEON_PASSWORD = os.getenv("NEON_PASSWORD", "")
NEON_HOST = os.getenv("NEON_HOST", "")
NEON_SSLMODE = os.getenv("NEON_SSLMODE", "require")

# OpenAI settings
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1/")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "")

# AI Bridge settings (Primary Model)
AI_BRIDGE_BASE_URL = os.getenv("FORGE_BASE_URL", "https://api.forge.tensorblock.co/v1")
AI_BRIDGE_API_KEY = os.getenv("FORGE_API_KEY", "")
AI_BRIDGE_MODEL = os.getenv("FORGE_AI_MODEL", "Gemini/models/gemini-2.5-flash") #OpenRouter/qwen/qwen3-4b:free

# Fallback AI Model settings (used when primary model fails)
AI_FALLBACK_MODEL_1 = os.getenv("FORGE_FALLBACK_MODEL_1", "Groq/llama-3.3-70b-versatile")

HTTP_REFERER = os.getenv("HTTP_REFERER", "https://github.com/tuanna0308/PythonSmartKids")
APP_TITLE = os.getenv("APP_TITLE", "PythonSmartKids")

# Database query settings
MAX_ATTEMPTS_HISTORY_LIMIT = int(os.getenv("MAX_ATTEMPTS_HISTORY_LIMIT", "20"))

# Testing settings
RUN_REAL_API_TESTS = os.getenv("RUN_REAL_API_TESTS", "False").lower() == "true"

# Debug settings
DEBUG_MODE = os.getenv("DebugMode", "0") == "1"

# Below are Phase B - Reporting/Analytics configurations

# Neo4j settings for performance reports
NEO4J_URI = os.getenv("NEO4J_URI", "neo4j+s://969d50b9.databases.neo4j.io")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

# Gemini AI settings
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Embedding model settings
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
EMBEDDING_DIMENSIONS = int(os.getenv("EMBEDDING_DIMENSIONS", "384"))

# Retry configuration for agentic workflow
MAX_RETRIEVAL_RETRIES = int(os.getenv("MAX_RETRIEVAL_RETRIES", "2"))

# LangSmith tracing settings (optional)
LANGSMITH_API_KEY = os.getenv('LANGSMITH_API_KEY', '')
LANGSMITH_PROJECT = os.getenv('LANGSMITH_PROJECT', 'pr-internal-mesenchyme-70')
LANGSMITH_TRACING = os.getenv('LANGSMITH_TRACING', 'false').lower() == 'true'

# === Help Feature - Visual Aids Configuration ===
# Controls global limits for visual aids in help responses
# Subject-level limits in subjects table can be MORE restrictive

# JSON-based visual aids (frontend renders SVG from shape parameters)
FF_HELP_VISUAL_JSON_ENABLED = os.getenv("FF_HELP_VISUAL_JSON_ENABLED", "true").lower() == "true"
FF_HELP_VISUAL_JSON_MAX = int(os.getenv("FF_HELP_VISUAL_JSON_MAX", "3"))

# AI-generated SVG (complete SVG element from AI, experimental)
FF_HELP_VISUAL_SVG_FROM_AI_ENABLED = os.getenv("FF_HELP_VISUAL_SVG_FROM_AI_ENABLED", "false").lower() == "true"
FF_HELP_VISUAL_SVG_FROM_AI_MAX = int(os.getenv("FF_HELP_VISUAL_SVG_FROM_AI_MAX", "1"))

# Help Grade Reduction - How many grades to reduce for simpler explanations
# E.g., if set to 1, Grade 6 student gets Grade 5 level explanation
# Set to 0 to disable reduction (explain at student's actual grade)
HELP_GRADE_REDUCTION = int(os.getenv("HELP_GRADE_REDUCTION", "0"))

# === Google Play Billing Configuration ===
# Service account JSON for verifying Google Play purchases (base64 encoded)
GOOGLE_PLAY_SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_PLAY_SERVICE_ACCOUNT_JSON", "")
GOOGLE_PLAY_PACKAGE_NAME = os.getenv("GOOGLE_PLAY_PACKAGE_NAME", "tuanorg.smartboy")

# Admin key for administrative endpoints
ADMIN_KEY = os.getenv("ADMIN_KEY", "dev-admin-key")
