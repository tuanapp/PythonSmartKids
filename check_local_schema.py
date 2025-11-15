"""Check local prompts table schema"""
from app.db.db_factory import DatabaseFactory

db = DatabaseFactory.get_provider()
conn = db._get_connection()
cursor = conn.cursor()

cursor.execute("""
    SELECT column_name, data_type 
    FROM information_schema.columns 
    WHERE table_name = 'prompts'
    ORDER BY ordinal_position
""")

print("Local prompts table columns:")
for row in cursor.fetchall():
    print(f"  {row[0]}: {row[1]}")

cursor.close()
conn.close()
