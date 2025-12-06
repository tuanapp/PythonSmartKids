"""
Test script for user blocking system
Tests blocking/unblocking operations
"""
import psycopg2
from datetime import datetime, timezone

# Database connection string
DATABASE_URL = "postgresql://tuanapp:HdzrNIKh5mM1@ep-sparkling-butterfly-33773987.ap-southeast-1.aws.neon.tech/tuandb?sslmode=require"

def test_blocking_system():
    """Test the user blocking functionality"""
    
    print("=" * 60)
    print("Testing User Blocking System")
    print("=" * 60)
    print()
    
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # Test 1: Create a test user
        print("Test 1: Creating test user...")
        test_uid = "TEST_USER_12345678901234567890"
        test_email = "test@example.com"
        
        cursor.execute("""
            INSERT INTO users (uid, email, name, display_name, grade_level, subscription, registration_date)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (uid) DO UPDATE 
            SET is_blocked = FALSE, blocked_reason = NULL, blocked_at = NULL, blocked_by = NULL
            RETURNING id;
        """, (test_uid, test_email, "Test User", "TestUser", 5, 0, datetime.now(timezone.utc)))
        
        user_id = cursor.fetchone()[0]
        conn.commit()
        print(f"✓ Created test user with ID: {user_id}")
        print()
        
        # Test 2: Block the user
        print("Test 2: Blocking user...")
        block_reason = "Testing blocking functionality"
        blocked_by = "test_admin"
        
        cursor.execute("""
            UPDATE users 
            SET is_blocked = TRUE, 
                blocked_reason = %s, 
                blocked_at = %s, 
                blocked_by = %s
            WHERE uid = %s;
        """, (block_reason, datetime.now(timezone.utc), blocked_by, test_uid))
        
        cursor.execute("""
            INSERT INTO user_blocking_history (user_uid, action, reason, blocked_at, blocked_by)
            VALUES (%s, %s, %s, %s, %s);
        """, (test_uid, "BLOCKED", block_reason, datetime.now(timezone.utc), blocked_by))
        
        conn.commit()
        print(f"✓ User blocked successfully")
        print()
        
        # Test 3: Check blocking status
        print("Test 3: Checking blocking status...")
        cursor.execute("""
            SELECT is_blocked, blocked_reason, blocked_by 
            FROM users 
            WHERE uid = %s;
        """, (test_uid,))
        
        is_blocked, reason, by_who = cursor.fetchone()
        if is_blocked:
            print(f"✓ User is blocked")
            print(f"  Reason: {reason}")
            print(f"  Blocked by: {by_who}")
        else:
            print("✗ User is not blocked (unexpected!)")
        print()
        
        # Test 4: Get blocking history
        print("Test 4: Checking blocking history...")
        cursor.execute("""
            SELECT action, reason, blocked_by, blocked_at 
            FROM user_blocking_history 
            WHERE user_uid = %s
            ORDER BY blocked_at DESC;
        """, (test_uid,))
        
        history = cursor.fetchall()
        print(f"✓ Found {len(history)} history record(s):")
        for action, reason, by_who, when in history:
            print(f"  - {action} by {by_who}: {reason}")
        print()
        
        # Test 5: Unblock the user
        print("Test 5: Unblocking user...")
        cursor.execute("""
            UPDATE users 
            SET is_blocked = FALSE, 
                blocked_reason = NULL, 
                blocked_at = NULL, 
                blocked_by = NULL
            WHERE uid = %s;
        """, (test_uid,))
        
        cursor.execute("""
            INSERT INTO user_blocking_history (user_uid, action, unblocked_at, blocked_by, notes)
            VALUES (%s, %s, %s, %s, %s);
        """, (test_uid, "UNBLOCKED", datetime.now(timezone.utc), "test_admin", "Test completed"))
        
        conn.commit()
        print(f"✓ User unblocked successfully")
        print()
        
        # Test 6: Verify unblocked
        print("Test 6: Verifying user is unblocked...")
        cursor.execute("""
            SELECT is_blocked 
            FROM users 
            WHERE uid = %s;
        """, (test_uid,))
        
        is_blocked = cursor.fetchone()[0]
        if not is_blocked:
            print(f"✓ User is now unblocked")
        else:
            print("✗ User is still blocked (unexpected!)")
        print()
        
        # Cleanup
        print("Cleanup: Removing test user...")
        cursor.execute("DELETE FROM user_blocking_history WHERE user_uid = %s;", (test_uid,))
        cursor.execute("DELETE FROM users WHERE uid = %s;", (test_uid,))
        conn.commit()
        print("✓ Test user removed")
        print()
        
        cursor.close()
        conn.close()
        
        print("=" * 60)
        print("✅ All tests passed!")
        print("=" * 60)
        print()
        print("The user blocking system is working correctly!")
        print()
        
        return True
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        if conn:
            conn.rollback()
            conn.close()
        return False

if __name__ == "__main__":
    test_blocking_system()
