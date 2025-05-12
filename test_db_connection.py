"""
A simple script to test the PostgreSQL connection to Supabase.
"""
import os
import sys
import time
import psycopg2
from dotenv import load_dotenv

def test_postgres_connection():
    """Test the Supabase PostgreSQL connection using the connection string."""
    load_dotenv()
    
    # Get connection string from environment variable
    postgres_conn_string = os.getenv("POSTGRES_CONNECTION_STRING")
    supabase_db_password = os.getenv("SUPABASE_DB_PASSWORD")
    
    if not postgres_conn_string:
        print("Error: POSTGRES_CONNECTION_STRING not found in environment variables.")
        print("Please ensure it's set in your .env file.")
        sys.exit(1)
        
    # If the connection string contains ${SUPABASE_DB_PASSWORD}, replace it
    if "${SUPABASE_DB_PASSWORD}" in postgres_conn_string and supabase_db_password:
        postgres_conn_string = postgres_conn_string.replace("${SUPABASE_DB_PASSWORD}", supabase_db_password)
    
    print(f"Attempting to connect to PostgreSQL database...")
    print(f"Connection string: {postgres_conn_string.replace(supabase_db_password, '******')}")
    
    start_time = time.time()
    
    try:
        # Attempt to connect
        conn = psycopg2.connect(postgres_conn_string)
        
        # Calculate connection time
        connection_time = time.time() - start_time
        
        print(f"\n✅ Connection successful! ({connection_time:.2f} seconds)")
        print(f"Server info: {conn.get_parameter_status('server_version')}")
        
        # Test a simple query
        cursor = conn.cursor()
        cursor.execute("SELECT current_timestamp, current_database()")
        timestamp, database = cursor.fetchone()
        
        print(f"Current time on server: {timestamp}")
        print(f"Connected to database: {database}")
        
        # Check if the attempts table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM pg_tables 
                WHERE schemaname = 'public' 
                AND tablename = 'attempts'
            )
        """)
        table_exists = cursor.fetchone()[0]
        
        if table_exists:
            print("✅ The 'attempts' table exists.")
            
            # Count records in attempts table
            cursor.execute("SELECT COUNT(*) FROM attempts")
            count = cursor.fetchone()[0]
            print(f"Number of records in attempts table: {count}")
        else:
            print("❌ The 'attempts' table does not exist!")
        
        # Close the connection
        cursor.close()
        conn.close()
        return True
        
    except psycopg2.OperationalError as e:
        # Calculate failure time
        failure_time = time.time() - start_time
        print(f"\n❌ Connection failed after {failure_time:.2f} seconds!")
        print(f"Error: {e}")
        return False
    except Exception as e:
        print(f"\n❌ An error occurred: {e}")
        return False

if __name__ == "__main__":
    print("Testing Supabase PostgreSQL Connection")
    print("-" * 40)
    test_postgres_connection()