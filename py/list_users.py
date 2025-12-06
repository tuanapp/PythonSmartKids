"""Check all users in database and test registration."""

import psycopg2
from app.config import NEON_DBNAME, NEON_USER, NEON_PASSWORD, NEON_HOST, NEON_SSLMODE

def list_all_users():
    """List all users in the database."""
    
    conn = psycopg2.connect(
        dbname=NEON_DBNAME,
        user=NEON_USER,
        password=NEON_PASSWORD,
        host=NEON_HOST,
        sslmode=NEON_SSLMODE
    )
    cursor = conn.cursor()
    
    print("\n=== All Users in Database ===")
    cursor.execute("""
        SELECT uid, email, subscription, is_blocked, registration_date
        FROM users
        ORDER BY registration_date DESC
        LIMIT 10
    """)
    
    results = cursor.fetchall()
    if results:
        print(f"Found {len(results)} users:")
        for uid, email, sub, blocked, reg_date in results:
            status = "🔒 BLOCKED" if blocked else "✅ Active"
            sub_label = {0: "Free", 1: "Trial", 2: "Premium"}.get(sub, f"Tier {sub}")
            print(f"   {status} | {email} | {sub_label} | UID: {uid[:10]}... | Registered: {reg_date}")
    else:
        print("No users found in database")
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    list_all_users()
