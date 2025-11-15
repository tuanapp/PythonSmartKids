#!/usr/bin/env python3
"""
Check prompts in database for specific UID
"""
from app.db.db_factory import DatabaseFactory

def check_prompts(uid):
    db = DatabaseFactory.get_provider()
    conn = db._get_connection()
    cursor = conn.cursor()
    
    # Check total prompts
    cursor.execute("""
        SELECT COUNT(*), MAX(created_at) 
        FROM prompts 
        WHERE uid=%s AND request_type='question_generation'
    """, (uid,))
    count, max_date = cursor.fetchone()
    print(f"Total prompts for {uid}: {count}")
    print(f"Latest prompt date: {max_date}")
    
    # Check today's prompts
    cursor.execute("""
        SELECT COUNT(*), DATE(created_at AT TIME ZONE 'UTC') as date
        FROM prompts 
        WHERE uid=%s AND request_type='question_generation'
        GROUP BY DATE(created_at AT TIME ZONE 'UTC')
        ORDER BY date DESC
        LIMIT 5
    """, (uid,))
    
    print("\nPrompts by date:")
    for count, date in cursor.fetchall():
        print(f"  {date}: {count} prompts")
    
    # Check recent prompts details
    cursor.execute("""
        SELECT id, created_at, status, is_live, level, source
        FROM prompts 
        WHERE uid=%s AND request_type='question_generation'
        ORDER BY created_at DESC
        LIMIT 10
    """, (uid,))
    
    print("\nRecent prompts:")
    for row in cursor.fetchall():
        print(f"  ID: {row[0]}, Created: {row[1]}, Status: {row[2]}, Live: {row[3]}, Level: {row[4]}, Source: {row[5]}")
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    uid = "5NZJhogMvocs6cmwq8IfBupiHtw1"
    check_prompts(uid)
