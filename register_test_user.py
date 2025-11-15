"""
Manually register a user in the database for testing.
This simulates what happens when a user registers via the frontend.
"""

import psycopg2
from datetime import datetime, UTC
from app.config import NEON_DBNAME, NEON_USER, NEON_PASSWORD, NEON_HOST, NEON_SSLMODE

def register_test_user(uid, email, name, display_name, grade_level, subscription=0):
    """Manually register a user in the database."""
    
    conn = psycopg2.connect(
        dbname=NEON_DBNAME,
        user=NEON_USER,
        password=NEON_PASSWORD,
        host=NEON_HOST,
        sslmode=NEON_SSLMODE
    )
    cursor = conn.cursor()
    
    try:
        # Check if user already exists
        cursor.execute("SELECT uid, email FROM users WHERE email = %s", (email,))
        existing = cursor.fetchone()
        
        if existing:
            print(f"❌ User already exists: {existing[1]} (UID: {existing[0]})")
            return False
        
        # Insert new user
        now = datetime.now(UTC)
        cursor.execute("""
            INSERT INTO users 
            (uid, email, name, display_name, grade_level, subscription, registration_date, is_blocked)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, uid, email
        """, (uid, email, name, display_name, grade_level, subscription, now, False))
        
        result = cursor.fetchone()
        conn.commit()
        
        print(f"\n✅ User registered successfully!")
        print(f"   ID: {result[0]}")
        print(f"   UID: {result[1]}")
        print(f"   Email: {result[2]}")
        print(f"   Name: {name}")
        print(f"   Grade Level: {grade_level}")
        print(f"   Subscription: {subscription} (0=Free, 1=Trial, 2+=Premium)")
        print(f"   Registration Date: {now}")
        
        return True
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Error registering user: {e}")
        return False
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    import sys
    
    print("\n=== Manual User Registration ===\n")
    print("This will register a test user in the database.")
    print("Note: The user must already exist in Firebase Auth!\n")
    
    # Test user credentials
    # For testing, we'll use a Firebase-like UID (28 characters)
    test_uid = "kdxpics5test1234567890abcd"  # Firebase UIDs are 28 chars
    test_email = "kdxpics5@gmail.com"
    test_name = "Test User"
    test_display_name = "Test User"
    test_grade = 5
    test_subscription = 0  # Free tier
    
    print(f"User to register:")
    print(f"  Email: {test_email}")
    print(f"  Name: {test_name}")
    print(f"  Grade Level: {test_grade}")
    print(f"  Subscription: {test_subscription} (Free)")
    print(f"  UID: {test_uid}")
    
    response = input("\nProceed with registration? (yes/no): ")
    
    if response.lower() == 'yes':
        register_test_user(test_uid, test_email, test_name, test_display_name, test_grade, test_subscription)
    else:
        print("Registration cancelled.")
