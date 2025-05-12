"""
A simple script to test the connection to Neon PostgreSQL database.
"""
import os
import sys
import time
import psycopg2
from dotenv import load_dotenv

def test_postgres_connection():
    """Test the Neon PostgreSQL connection using the connection parameters."""
    load_dotenv()
    
    # Get Neon connection details from environment variables or use defaults
    dbname = os.getenv("NEON_DBNAME", "smartboydb")
    user = os.getenv("NEON_USER", "tuanapp")
    password = os.getenv("NEON_PASSWORD", "HdzrNIKh5mM1")
    host = os.getenv("NEON_HOST", "ep-sparkling-butterfly-33773987-pooler.ap-southeast-1.aws.neon.tech")
    sslmode = os.getenv("NEON_SSLMODE", "require")
    
    print(f"Attempting to connect to Neon PostgreSQL database...")
    print(f"Host: {host}, Database: {dbname}, User: {user}")
    
    start_time = time.time()
    
    try:
        # Attempt to connect
        conn = psycopg2.connect(
            dbname=dbname,
            user=user,
            password=password,
            host=host,
            sslmode=sslmode
        )
        
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
            print("❌ The 'attempts' table does not exist! Run setup_neon_schema.py to create it.")
        
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
    print("Testing Neon PostgreSQL Connection")
    print("-" * 40)
    test_postgres_connection()