import logging
import os
from app.config import NEON_SSLMODE
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
            
            # Get PostgreSQL connection details from environment variables
            dbname = os.getenv("NEON_DBNAME")
            user = os.getenv("NEON_USER")
            password = os.getenv("NEON_PASSWORD")
            host = os.getenv("NEON_HOST")
            
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