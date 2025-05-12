"""
This script provides functionality for setting up the required database schema in Neon PostgreSQL.
"""
import sys
import os
import logging
import psycopg2
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def setup_neon_schema():
    """
    Connect to Neon and set up the required schema.
    """
    load_dotenv()
    
    # Get Neon connection details from environment variables or use defaults
    dbname = os.getenv("NEON_DBNAME", "smartboydb")
    user = os.getenv("NEON_USER", "tuanapp")
    password = os.getenv("NEON_PASSWORD", "HdzrNIKh5mM1")
    host = os.getenv("NEON_HOST", "ep-sparkling-butterfly-33773987-pooler.ap-southeast-1.aws.neon.tech")
    sslmode = os.getenv("NEON_SSLMODE", "require")
    
    logger.info(f"Connecting to Neon PostgreSQL at {host}")
    
    try:
        # Connect to Neon PostgreSQL
        conn = psycopg2.connect(
            dbname=dbname,
            user=user,
            password=password,
            host=host,
            sslmode=sslmode
        )
        conn.autocommit = True
        cursor = conn.cursor()
        
        logger.info("Successfully connected to Neon PostgreSQL!")
        
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
            logger.info("Attempts table already exists in Neon PostgreSQL.")
            cursor.execute("SELECT COUNT(*) FROM attempts")
            count = cursor.fetchone()[0]
            logger.info(f"Current record count: {count}")
        else:
            logger.info("Attempts table not found. Creating it...")
            create_attempts_table(cursor)
            
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Failed to connect to Neon PostgreSQL: {e}")
        show_manual_instructions()
        return False

def create_attempts_table(cursor):
    """
    Create the attempts table in Neon PostgreSQL.
    """
    try:
        # Create the table
        cursor.execute("""
            CREATE TABLE public.attempts (
                id SERIAL PRIMARY KEY,
                student_id INTEGER NOT NULL,
                datetime TIMESTAMP NOT NULL,
                question TEXT NOT NULL,
                is_answer_correct BOOLEAN NOT NULL,
                incorrect_answer TEXT,
                correct_answer TEXT NOT NULL
            )
        """)
        
        logger.info("Successfully created attempts table!")
        return True
        
    except Exception as e:
        logger.error(f"Failed to create attempts table: {e}")
        show_manual_instructions()
        return False

def show_manual_instructions():
    """
    Show instructions for manually creating the schema in Neon PostgreSQL.
    """
    print("\n" + "=" * 80)
    print("NEON POSTGRESQL SCHEMA SETUP INSTRUCTIONS")
    print("=" * 80)
    print("To set up the database schema in Neon PostgreSQL manually, follow these steps:")
    print("1. Connect to your Neon database using a PostgreSQL client or the Neon console")
    print("2. Execute the following SQL:")
    print()
    print("```sql")
    print("CREATE TABLE public.attempts (")
    print("    id SERIAL PRIMARY KEY,")
    print("    student_id INTEGER NOT NULL,")
    print("    datetime TIMESTAMP NOT NULL,")
    print("    question TEXT NOT NULL,")
    print("    is_answer_correct BOOLEAN NOT NULL,")
    print("    incorrect_answer TEXT,")
    print("    correct_answer TEXT NOT NULL")
    print(");")
    print("```")
    print()
    print("=" * 80 + "\n")

if __name__ == "__main__":
    setup_neon_schema()