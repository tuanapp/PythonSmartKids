import logging
import os
from urllib.parse import urlparse

from app.config import (
    DATABASE_URL,
    NEON_DBNAME,
    NEON_HOST,
    NEON_PASSWORD,
    NEON_SSLMODE,
    NEON_USER,
)
from app.db.db_interface import DatabaseProvider
from app.db.neon_provider import NeonProvider

logger = logging.getLogger(__name__)

class DatabaseFactory:
    """Factory for creating database providers."""
    
    _instance = None
    
    @staticmethod
    def get_provider() -> DatabaseProvider:
        """
        Get or create a PostgreSQL database provider instance.
        
        Returns:
            DatabaseProvider: An instance of the PostgreSQL database provider (NeonProvider)
        """
        if DatabaseFactory._instance is None:
            logger.info("Using PostgreSQL database (NeonProvider)")
            
            # Prefer explicit env vars (Cloud Run), then fall back to app.config defaults
            # (which may come from dotenv files in local/dev environments).
            dbname = os.getenv("NEON_DBNAME") or NEON_DBNAME
            user = os.getenv("NEON_USER") or NEON_USER
            password = os.getenv("NEON_PASSWORD") or NEON_PASSWORD
            host = os.getenv("NEON_HOST") or NEON_HOST

            # As a last resort, try parsing DATABASE_URL if NEON_* are incomplete.
            if not all([dbname, user, password, host]) and DATABASE_URL:
                try:
                    parsed = urlparse(DATABASE_URL)
                    if parsed.hostname and parsed.username and parsed.path:
                        host = host or parsed.hostname
                        user = user or parsed.username
                        password = password or (parsed.password or "")
                        dbname = dbname or parsed.path.lstrip("/")
                except Exception:
                    # Keep the original missing-vars error below.
                    pass
            
            # Validate required environment variables
            if not all([dbname, user, password, host]):
                missing_vars = [var for var, val in {
                    "NEON_DBNAME": dbname,
                    "NEON_USER": user,
                    "NEON_PASSWORD": password,
                    "NEON_HOST": host
                }.items() if not val]
                raise Exception(f"Missing required PostgreSQL environment variables: {', '.join(missing_vars)}")
            
            DatabaseFactory._instance = NeonProvider(
                dbname=dbname,
                user=user,
                password=password,
                host=host,
                sslmode=NEON_SSLMODE
            )
            
            # Initialize the database
            DatabaseFactory._instance.init_db()
            
        return DatabaseFactory._instance