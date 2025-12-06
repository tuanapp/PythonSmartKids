"""
Test script to check and apply Migration 008 locally before production deployment.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db.vercel_migrations import migration_manager
import json

def check_status():
    """Check current migration status"""
    print("=" * 60)
    print("CHECKING MIGRATION STATUS")
    print("=" * 60)
    
    result = migration_manager.check_migration_status()
    print(json.dumps(result, indent=2, default=str))
    
    return result

def check_columns():
    """Check if level and source columns exist in prompts table"""
    print("\n" + "=" * 60)
    print("CHECKING PROMPTS TABLE COLUMNS")
    print("=" * 60)
    
    from app.db.db_factory import DatabaseFactory
    db_provider = DatabaseFactory.get_provider()
    conn = db_provider._get_connection()
    cursor = conn.cursor()
    
    # Check for level column
    cursor.execute("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'prompts' 
        ORDER BY ordinal_position
    """)
    columns = cursor.fetchall()
    
    print("\nPrompts table columns:")
    for col_name, col_type in columns:
        print(f"  - {col_name}: {col_type}")
    
    # Check if level and source exist
    level_exists = any(col[0] == 'level' for col in columns)
    source_exists = any(col[0] == 'source' for col in columns)
    
    print(f"\n✓ Level column exists: {level_exists}")
    print(f"✓ Source column exists: {source_exists}")
    
    # Check if question_generations table exists
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = 'question_generations'
        )
    """)
    qgen_exists = cursor.fetchone()[0]
    print(f"✓ question_generations table exists: {qgen_exists}")
    
    cursor.close()
    conn.close()
    
    return level_exists, source_exists, qgen_exists

def apply_migration():
    """Apply Migration 008"""
    print("\n" + "=" * 60)
    print("APPLYING MIGRATION 008")
    print("=" * 60)
    
    result = migration_manager.add_question_generation_tracking_migration()
    print(json.dumps(result, indent=2, default=str))
    
    return result

if __name__ == "__main__":
    # Step 1: Check status
    status = check_status()
    
    # Step 2: Check current columns
    level_exists, source_exists, qgen_exists = check_columns()
    
    # Step 3: Apply migration if needed
    if not level_exists or not source_exists or qgen_exists:
        print("\n⚠️  Migration 008 needs to be applied")
        response = input("\nApply Migration 008 now? (y/n): ")
        
        if response.lower() == 'y':
            result = apply_migration()
            
            if result.get('success'):
                print("\n✅ Migration 008 applied successfully!")
                
                # Verify
                print("\n" + "=" * 60)
                print("VERIFYING MIGRATION")
                print("=" * 60)
                level_exists, source_exists, qgen_exists = check_columns()
                
                if level_exists and source_exists and not qgen_exists:
                    print("\n✅ Migration verified successfully!")
                    print("   - level column added to prompts ✓")
                    print("   - source column added to prompts ✓")
                    print("   - question_generations table removed ✓")
                else:
                    print("\n⚠️  Migration verification failed")
            else:
                print(f"\n❌ Migration failed: {result.get('error')}")
        else:
            print("\nMigration skipped")
    else:
        print("\n✅ Migration 008 already applied")
        print("   - level column exists ✓")
        print("   - source column exists ✓")
        print("   - question_generations table removed ✓")
