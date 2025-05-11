import os
from dotenv import load_dotenv

load_dotenv()

# Database settings
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///math_attempts.db")
DATABASE_PROVIDER = os.getenv("DATABASE_PROVIDER", "sqlite")  # Options: sqlite, supabase

# Supabase specific settings
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://apifyzsbctxzfwrqkcqb.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFwaWZ5enNiY3R4emZ3cnFrY3FiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDY4NzMyNTEsImV4cCI6MjA2MjQ0OTI1MX0.teB3iEL-cAozLxZOyPVMOB7JHOIba7eMTRbUMXAeL0A")

# OpenAI settings
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
