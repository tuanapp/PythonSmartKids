import logging
from app.config import DATABASE_PROVIDER, DATABASE_URL, NEON_DBNAME, NEON_USER, NEON_PASSWORD, NEON_HOST, NEON_SSLMODE
from app.db.db_interface import DatabaseProvider
from app.db.sqlite_provider import SQLiteProvider
from app.db.neon_provider import NeonProvider

logger = logging.getLogger(__name__)

class DatabaseFactory:
    """Factory class to create database provider instances."""
    
    _instance = None
    
    @staticmethod
    def get_provider() -> DatabaseProvider:
        """
        Get or create a database provider instance based on the configuration.
        
        Returns:
            DatabaseProvider: An instance of the configured database provider
        """
        if DatabaseFactory._instance is None:
            if DATABASE_PROVIDER.lower() == "sqlite":
                # Extract the file path from the sqlite URL
                db_path = DATABASE_URL.replace("sqlite:///", "")
                logger.info(f"Using SQLite database at {db_path}")
                DatabaseFactory._instance = SQLiteProvider(db_path)
            elif DATABASE_PROVIDER.lower() == "neon":
                logger.info(f"Using Neon PostgreSQL database at {NEON_HOST}")
                DatabaseFactory._instance = NeonProvider(
                    dbname=NEON_DBNAME,
                    user=NEON_USER,
                    password=NEON_PASSWORD,
                    host=NEON_HOST,
                    sslmode=NEON_SSLMODE
                )
            else:
                logger.error(f"Unknown database provider: {DATABASE_PROVIDER}")
                raise ValueError(f"Unsupported database provider: {DATABASE_PROVIDER}")
            
            # Initialize the database
            DatabaseFactory._instance.init_db()
            
        return DatabaseFactory._instance