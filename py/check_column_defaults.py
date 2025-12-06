import psycopg2

conn = psycopg2.connect('postgresql://tuanapp:HdzrNIKh5mM1@ep-sparkling-butterfly-33773987.ap-southeast-1.aws.neon.tech/smartboydb?sslmode=require')
cur = conn.cursor()
cur.execute("""
    SELECT column_name, column_default, is_nullable 
    FROM information_schema.columns 
    WHERE table_name = 'users' AND column_name IN ('created_at', 'updated_at')
""")
for row in cur.fetchall():
    print(f"{row[0]}: default={row[1]}, nullable={row[2]}")
conn.close()
