"""Test script to check user access and question generation ability."""

import psycopg2
from app.config import NEON_DBNAME, NEON_USER, NEON_PASSWORD, NEON_HOST, NEON_SSLMODE
from datetime import date

def check_user_access(email):
    """Check if user can generate questions."""
    
    conn = psycopg2.connect(
        dbname=NEON_DBNAME,
        user=NEON_USER,
        password=NEON_PASSWORD,
        host=NEON_HOST,
        sslmode=NEON_SSLMODE
    )
    cursor = conn.cursor()
    
    # Check user details
    print(f"\n=== Checking User: {email} ===")
    cursor.execute("""
        SELECT uid, email, subscription, is_blocked, blocked_reason, registration_date
        FROM users
        WHERE email = %s
    """, (email,))
    
    result = cursor.fetchone()
    if not result:
        print(f"❌ User not found in database")
        cursor.close()
        conn.close()
        return
    
    uid, email, subscription, is_blocked, blocked_reason, reg_date = result
    print(f"✅ User found:")
    print(f"   UID: {uid}")
    print(f"   Email: {email}")
    print(f"   Subscription: {subscription} (0=free, 1=trial, 2+=premium)")
    print(f"   Is Blocked: {is_blocked}")
    if blocked_reason:
        print(f"   Blocked Reason: {blocked_reason}")
    print(f"   Registration Date: {reg_date}")
    
    # Check if blocked
    if is_blocked:
        print(f"\n❌ User is BLOCKED - Cannot generate questions")
        print(f"   Reason: {blocked_reason}")
        cursor.close()
        conn.close()
        return
    
    # Check today's generation count
    today = date.today()
    cursor.execute("""
        SELECT COUNT(*) 
        FROM question_generations
        WHERE uid = %s AND generation_date = %s
    """, (uid, today))
    
    count = cursor.fetchone()[0]
    print(f"\n📊 Generation Stats:")
    print(f"   Today's Generations: {count}")
    
    # Check limits
    max_daily = 2  # Default for free/trial users
    if subscription >= 2:
        print(f"   User is PREMIUM - Unlimited generations ✅")
        can_generate = True
    else:
        print(f"   User is FREE/TRIAL - Limited to {max_daily} generations per day")
        can_generate = count < max_daily
        if can_generate:
            print(f"   ✅ Can generate questions ({count}/{max_daily})")
        else:
            print(f"   ❌ Daily limit reached ({count}/{max_daily})")
    
    # Check if question_generations table exists and has correct structure
    print(f"\n🔧 Table Structure Check:")
    cursor.execute("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'question_generations'
        ORDER BY ordinal_position
    """)
    columns = cursor.fetchall()
    if columns:
        print(f"   question_generations table exists with columns:")
        for col_name, col_type in columns:
            print(f"      - {col_name} ({col_type})")
    else:
        print(f"   ❌ question_generations table NOT FOUND!")
        print(f"   This could be why generation fails!")
    
    # Check prompts table structure
    cursor.execute("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'prompts'
        ORDER BY ordinal_position
    """)
    columns = cursor.fetchall()
    if columns:
        print(f"\n   prompts table exists with columns:")
        for col_name, col_type in columns:
            print(f"      - {col_name} ({col_type})")
    else:
        print(f"   ❌ prompts table NOT FOUND!")
    
    cursor.close()
    conn.close()
    
    print(f"\n{'='*50}")
    if can_generate and not is_blocked:
        print(f"✅ USER CAN GENERATE QUESTIONS")
    else:
        print(f"❌ USER CANNOT GENERATE QUESTIONS")
        if is_blocked:
            print(f"   Reason: Account is blocked")
        elif not can_generate:
            print(f"   Reason: Daily limit reached")
    print(f"{'='*50}\n")

if __name__ == "__main__":
    check_user_access("kdxpics5@gmail.com")
