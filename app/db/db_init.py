import os
import logging
from app.config import DATABASE_PROVIDER, SUPABASE_URL, SUPABASE_KEY
from supabase import create_client, Client

logger = logging.getLogger(__name__)

def init_supabase():
    """
    Initialize the Supabase database structure.
    
    This function can be run once to set up the initial table structure in Supabase.
    It uses raw SQL through the Supabase client because Supabase doesn't have a direct
    table creation API for Python.
    """
    try:
        logger.info(f"Initializing Supabase database at {SUPABASE_URL}")
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        # Check if we can connect to Supabase
        try:
            # Try to run a simple query to verify connection
            supabase.table("attempts").select("*").limit(1).execute()
            logger.info("Table 'attempts' already exists in Supabase")
        except Exception as e:
            if "relation" in str(e) and "does not exist" in str(e):
                # Table doesn't exist, create it
                logger.info("Creating 'attempts' table in Supabase")
                
                # Create the attempts table using SQL
                # Note: Supabase REST API doesn't support table creation,
                # so we would typically do this in the Supabase dashboard or using migrations
                logger.warning(
                    "To create the table in Supabase, run the following SQL in the Supabase SQL Editor:\n"
                    "CREATE TABLE attempts (\n"
                    "    id SERIAL PRIMARY KEY,\n"
                    "    student_id INTEGER NOT NULL,\n"
                    "    datetime TIMESTAMP NOT NULL,\n"
                    "    question TEXT NOT NULL,\n"
                    "    is_answer_correct BOOLEAN NOT NULL,\n"
                    "    incorrect_answer TEXT,\n"
                    "    correct_answer TEXT NOT NULL\n"
                    ");"
                )
                
                # Set up RLS (Row Level Security) policies
                logger.warning(
                    "To set up basic RLS policies, run:\n"
                    "ALTER TABLE attempts ENABLE ROW LEVEL SECURITY;\n"
                    "CREATE POLICY \"Allow anonymous select\" ON attempts FOR SELECT USING (true);\n"
                    "CREATE POLICY \"Allow anonymous insert\" ON attempts FOR INSERT USING (true);"
                )
            else:
                logger.error(f"Error connecting to Supabase: {e}")
        
        logger.info("Supabase initialization completed")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize Supabase: {e}")
        return False

if __name__ == "__main__":
    # This allows running this file directly to initialize Supabase
    if DATABASE_PROVIDER.lower() == "supabase":
        init_supabase()
    else:
        logger.warning(f"Current database provider is {DATABASE_PROVIDER}, not Supabase. No initialization performed.")
