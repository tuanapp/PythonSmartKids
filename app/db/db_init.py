import os
import logging
import psycopg2
from app.config import DATABASE_PROVIDER, NEON_DBNAME, NEON_USER, NEON_PASSWORD, NEON_HOST, NEON_SSLMODE

logger = logging.getLogger(__name__)

def init_neon():
    """
    Initialize the Neon PostgreSQL database structure.
    
    This function can be run once to set up the initial table structure in Neon PostgreSQL.
    """
    try:
        logger.info(f"Initializing Neon PostgreSQL database at {NEON_HOST}")
        
        # Connect to Neon PostgreSQL
        conn = psycopg2.connect(
            dbname=NEON_DBNAME,
            user=NEON_USER,
            password=NEON_PASSWORD,
            host=NEON_HOST,
            sslmode=NEON_SSLMODE
        )
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Check if the attempts table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'attempts'
            )
        """)
        table_exists = cursor.fetchone()[0]
        
        if table_exists:
            logger.info("Table 'attempts' already exists in Neon PostgreSQL")
            cursor.execute("SELECT COUNT(*) FROM attempts")
            count = cursor.fetchone()[0]
            logger.info(f"Current record count: {count}")
        else:
            # Create the attempts table
            logger.info("Creating 'attempts' table in Neon PostgreSQL")
            cursor.execute("""
                CREATE TABLE attempts (
                    id SERIAL PRIMARY KEY,
                    student_id INTEGER NOT NULL,
                    datetime TIMESTAMP NOT NULL,
                    question TEXT NOT NULL,
                    is_answer_correct BOOLEAN NOT NULL,
                    incorrect_answer TEXT,
                    correct_answer TEXT NOT NULL
                )
            """)
            logger.info("Table 'attempts' created successfully")
        
        cursor.close()
        conn.close()
        
        logger.info("Neon PostgreSQL initialization completed")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize Neon PostgreSQL: {e}")
        return False

if __name__ == "__main__":
    # This allows running this file directly to initialize the database
    if DATABASE_PROVIDER.lower() == "neon":
        init_neon()
    else:
        logger.warning(f"Current database provider is {DATABASE_PROVIDER}, not Neon. No initialization performed.")
