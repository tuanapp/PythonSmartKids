import os
import psycopg2
from dotenv import load_dotenv

def execute_sql_file():
    load_dotenv()
    
    # Get the connection string from environment variables
    connection_string = os.getenv('POSTGRES_CONNECTION_STRING')
    
    if not connection_string:
        print("Error: POSTGRES_CONNECTION_STRING not found in environment variables")
        return
    
    try:
        # Connect to the database
        conn = psycopg2.connect(connection_string)
        cur = conn.cursor()
        
        # Read and execute the SQL file
        with open('create_api_table.sql', 'r') as file:
            sql = file.read()
            cur.execute(sql)
        
        # Commit the changes
        conn.commit()
        
        # Verify the table was created
        cur.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'api' AND table_name = 'attempts')")
        table_exists = cur.fetchone()[0]
        
        if table_exists:
            print("✅ Table 'api.attempts' was successfully created!")
        else:
            print("❌ Table creation failed!")
            
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    execute_sql_file()