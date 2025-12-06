"""Quick script to check users table schema"""
from app.db.db_factory import DatabaseFactory

db = DatabaseFactory.get_provider()
conn = db._get_connection()
cursor = conn.cursor()

cursor.execute("""
    SELECT column_name, data_type 
    FROM information_schema.columns 
    WHERE table_name='users' 
    ORDER BY ordinal_position
""")

print("Users table columns:")
for col_name, col_type in cursor.fetchall():
    print(f"  - {col_name}: {col_type}")

cursor.close()
conn.close()
