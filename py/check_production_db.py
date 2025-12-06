"""Check production database structure and identify issues."""

import psycopg2
from app.config import NEON_DBNAME, NEON_USER, NEON_PASSWORD, NEON_HOST, NEON_SSLMODE

def check_production_db():
    """Check production database structure."""
    
    conn = psycopg2.connect(
        dbname=NEON_DBNAME,
        user=NEON_USER,
        password=NEON_PASSWORD,
        host=NEON_HOST,
        sslmode=NEON_SSLMODE
    )
    cursor = conn.cursor()
    
    print("\n=== Production Database Status ===\n")
    
    # Check all tables
    print("📋 Tables:")
    cursor.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema='public'
        ORDER BY table_name
    """)
    tables = [row[0] for row in cursor.fetchall()]
    for table in tables:
        print(f"   ✅ {table}")
    
    # Check if new tables exist
    print("\n🔍 New Tracking Tables:")
    if 'question_generations' in tables:
        print("   ✅ question_generations exists")
        cursor.execute("SELECT COUNT(*) FROM question_generations")
        count = cursor.fetchone()[0]
        print(f"      Records: {count}")
    else:
        print("   ❌ question_generations NOT FOUND")
        print("      → Migration hasn't been applied yet!")
    
    # Check prompts table structure
    print("\n📝 Prompts Table Structure:")
    cursor.execute("""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns 
        WHERE table_name = 'prompts'
        ORDER BY ordinal_position
    """)
    columns = cursor.fetchall()
    
    # Check for new columns we added
    column_names = [col[0] for col in columns]
    new_columns = ['request_type', 'model_name', 'response_time_ms', 'prompt_tokens', 
                   'completion_tokens', 'total_tokens', 'estimated_cost_usd', 'status', 'error_message']
    
    missing_columns = [col for col in new_columns if col not in column_names]
    
    if missing_columns:
        print("   ⚠️  Missing enhanced tracking columns:")
        for col in missing_columns:
            print(f"      ❌ {col}")
        print("\n   → Prompts table hasn't been enhanced yet!")
    else:
        print("   ✅ All enhanced tracking columns present")
    
    # Check users count
    print("\n👥 Users:")
    cursor.execute("SELECT COUNT(*) FROM users")
    user_count = cursor.fetchone()[0]
    print(f"   Total users: {user_count}")
    
    # Check if there are blocked users
    cursor.execute("SELECT COUNT(*) FROM users WHERE is_blocked = TRUE")
    blocked_count = cursor.fetchone()[0]
    if blocked_count > 0:
        print(f"   ⚠️  Blocked users: {blocked_count}")
    
    # Check alembic version
    if 'alembic_version' in tables:
        print("\n🔧 Alembic Migration Status:")
        cursor.execute("SELECT version_num FROM alembic_version")
        version = cursor.fetchone()
        if version:
            print(f"   Current version: {version[0]}")
        else:
            print("   No version recorded")
    
    # Summary
    print("\n" + "="*50)
    print("SUMMARY:")
    print("="*50)
    
    if 'question_generations' not in tables:
        print("❌ ISSUE: New tracking tables not created")
        print("   Solution: Need to apply migration to production")
    elif missing_columns:
        print("❌ ISSUE: Prompts table not enhanced")
        print("   Solution: Need to apply migration to add new columns")
    else:
        print("✅ Database structure looks good!")
    
    print("\n💡 To fix, run:")
    print("   curl 'https://python-smart-kids.vercel.app/admin/apply-migrations?admin_key=dev-admin-key'")
    print("="*50 + "\n")
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    check_production_db()
