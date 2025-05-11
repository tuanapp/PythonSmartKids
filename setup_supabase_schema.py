"""
This script provides instructions for setting up the required database schema in Supabase.
"""
import sys
import os
import logging
from supabase import create_client
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def setup_supabase_schema():
    """
    Attempt to connect to Supabase and set up the required schema.
    """
    load_dotenv()
    
    # Get Supabase connection details from environment variables
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    
    if not supabase_url or not supabase_key:
        logger.error("Supabase URL or key not found. Please check your .env file.")
        sys.exit(1)
    
    logger.info(f"Connecting to Supabase at {supabase_url}")
    
    try:
        # Create a Supabase client
        supabase = create_client(supabase_url, supabase_key)
        logger.info("Successfully connected to Supabase!")
        
        # Check if the attempts table exists by querying it
        try:
            response = supabase.table("attempts").select("count()", count='exact').execute()
            logger.info("Attempts table already exists in Supabase.")
            count = response.count if hasattr(response, 'count') else 0
            logger.info(f"Current record count: {count}")
            return True
        except Exception as e:
            if "relation" in str(e) and "does not exist" in str(e):
                logger.info("Attempts table not found. Creating it automatically...")
                create_attempts_table(supabase)
            else:
                logger.error(f"Error checking table: {e}")
                show_manual_instructions()
    except Exception as e:
        logger.error(f"Failed to connect to Supabase: {e}")
        show_manual_instructions()
        return False

def create_attempts_table(supabase):
    """
    Create the attempts table in Supabase.
    """
    try:
        # Execute SQL to create the table and set up RLS
        sql = """
        CREATE TABLE attempts (
            id SERIAL PRIMARY KEY,
            student_id INTEGER NOT NULL,
            datetime TIMESTAMP NOT NULL,
            question TEXT NOT NULL,
            is_answer_correct BOOLEAN NOT NULL,
            incorrect_answer TEXT,
            correct_answer TEXT NOT NULL
        );
        
        -- Set up basic Row Level Security (RLS) policies
        ALTER TABLE attempts ENABLE ROW LEVEL SECURITY;
        CREATE POLICY "Allow anonymous select" ON attempts FOR SELECT USING (true);
        CREATE POLICY "Allow anonymous insert" ON attempts FOR INSERT USING (true);
        """
        
        # Execute SQL query using REST API since PostgreSQL SQL execution is not directly
        # supported in the Python client
        response = supabase.rpc('exec_sql', {'sql': sql}).execute()
        
        logger.info("Successfully created attempts table and set up RLS policies!")
        return True
    except Exception as e:
        logger.error(f"Failed to create attempts table: {e}")
        show_manual_instructions()
        return False

def show_manual_instructions():
    """
    Show instructions for manually creating the schema in Supabase.
    """
    print("\n" + "=" * 80)
    print("SUPABASE SCHEMA SETUP INSTRUCTIONS")
    print("=" * 80)
    print("To set up the database schema in Supabase, please follow these steps:")
    print("1. Go to https://app.supabase.com/ and log in")
    print("2. Select your project (https://apifyzsbctxzfwrqkcqb.supabase.co)")
    print("3. Go to the SQL Editor")
    print("4. Create a new query and paste the following SQL:")
    print()
    print("```sql")
    print("CREATE TABLE attempts (")
    print("    id SERIAL PRIMARY KEY,")
    print("    student_id INTEGER NOT NULL,")
    print("    datetime TIMESTAMP NOT NULL,")
    print("    question TEXT NOT NULL,")
    print("    is_answer_correct BOOLEAN NOT NULL,")
    print("    incorrect_answer TEXT,")
    print("    correct_answer TEXT NOT NULL")
    print(");")
    print()
    print("-- Set up basic Row Level Security (RLS) policies")
    print("ALTER TABLE attempts ENABLE ROW LEVEL SECURITY;")
    print("CREATE POLICY \"Allow anonymous select\" ON attempts FOR SELECT USING (true);")
    print("CREATE POLICY \"Allow anonymous insert\" ON attempts FOR INSERT USING (true);")
    print("```")
    print()
    print("5. Click 'Run' to execute the SQL")
    print("=" * 80 + "\n")

if __name__ == "__main__":
    setup_supabase_schema()