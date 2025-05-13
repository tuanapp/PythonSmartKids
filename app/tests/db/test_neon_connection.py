# """
# Simple script to test the connection to Neon PostgreSQL.
# """
# import os
# import logging
# import psycopg2
# from dotenv import load_dotenv

# # Configure logging
# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
# )
# logger = logging.getLogger(__name__)

# def test_neon_connection():
#     """
#     Test the connection to Neon PostgreSQL database.
#     """
#     load_dotenv()
    
#     # Get Neon connection details from environment variables or use defaults
#     dbname = os.getenv("NEON_DBNAME", "smartboydb")
#     user = os.getenv("NEON_USER", "tuanapp")
#     password = os.getenv("NEON_PASSWORD", "HdzrNIKh5mM1")
#     host = os.getenv("NEON_HOST", "ep-sparkling-butterfly-33773987-pooler.ap-southeast-1.aws.neon.tech")
#     sslmode = os.getenv("NEON_SSLMODE", "require")
    
#     logger.info(f"Testing connection to Neon PostgreSQL at {host}")
    
#     try:
#         # Connect to Neon PostgreSQL
#         conn = psycopg2.connect(
#             dbname=dbname,
#             user=user,
#             password=password,
#             host=host,
#             sslmode=sslmode
#         )
        
#         # Test by creating a cursor and executing a simple query
#         cursor = conn.cursor()
#         cursor.execute("SELECT version();")
#         version = cursor.fetchone()
        
#         logger.info("✅ Connection successful!")
#         logger.info(f"PostgreSQL version: {version[0]}")
        
#         # Check if the attempts table exists
#         cursor.execute("""
#             SELECT EXISTS (
#                 SELECT FROM information_schema.tables 
#                 WHERE table_schema = 'public' 
#                 AND table_name = 'attempts'
#             )
#         """)
#         table_exists = cursor.fetchone()[0]
        
#         if table_exists:
#             logger.info("✅ Attempts table exists")
#             cursor.execute("SELECT COUNT(*) FROM attempts")
#             count = cursor.fetchone()[0]
#             logger.info(f"Current record count: {count}")
#         else:
#             logger.warning("⚠️ Attempts table does not exist yet. Run setup_neon_schema.py to create it.")
            
#         cursor.close()
#         conn.close()
        
#         return True
        
#     except Exception as e:
#         logger.error(f"❌ Connection failed: {e}")
#         return False

# if __name__ == "__main__":
#     test_neon_connection()