"""Fix alembic version in database"""
import psycopg2
from app.config import NEON_DBNAME, NEON_USER, NEON_PASSWORD, NEON_HOST, NEON_SSLMODE

conn = psycopg2.connect(
    dbname=NEON_DBNAME,
    user=NEON_USER,
    password=NEON_PASSWORD,
    host=NEON_HOST,
    sslmode=NEON_SSLMODE
)

cursor = conn.cursor()
cursor.execute('SELECT * FROM alembic_version')
print('Current versions:', cursor.fetchall())

# Delete the invalid '008' version
cursor.execute("DELETE FROM alembic_version WHERE version_num = '008'")
conn.commit()

cursor.execute('SELECT * FROM alembic_version')
print('Updated versions:', cursor.fetchall())

conn.close()
print('Alembic version successfully cleaned up')
