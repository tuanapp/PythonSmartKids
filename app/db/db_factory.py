import logging
import os
from app.config import DATABASE_PROVIDER, NEON_SSLMODE
from app.db.db_interface import DatabaseProvider
from app.db.neon_provider import NeonProvider

logger = logging.getLogger(__name__)

class DatabaseFactory:
    """Factory for creating database providers."""
    
    _instance = None
    
    @staticmethod
    def get_provider() -> DatabaseProvider:
        """
        Get or create a database provider instance based on the configuration.
        
        Returns:
            DatabaseProvider: An instance of the configured database provider
        """
        if DatabaseFactory._instance is None:
            if DATABASE_PROVIDER.lower() == "neon":
                logger.info("Using Neon PostgreSQL database")
                
                # Get Neon connection details from environment variables
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
                    raise Exception(f"Missing required environment variables: {', '.join(missing_vars)}")
                
                DatabaseFactory._instance = NeonProvider(
                    dbname=dbname,
                    user=user,
                    password=password,
                    host=host,
                    sslmode=NEON_SSLMODE
                )
            else:
                logger.error(f"Unknown database provider: {DATABASE_PROVIDER}")
                raise ValueError(f"Unsupported database provider: {DATABASE_PROVIDER}")
            
            # Initialize the database
            DatabaseFactory._instance.init_db()
            
        return DatabaseFactory._instance