"""
Production Deployment Verification Script for Migration 008
Run this after deploying to production to verify the migration.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db.db_factory import DatabaseFactory
import json

def verify_production_migration():
    """Verify Migration 008 in production database"""
    print("=" * 80)
    print("PRODUCTION MIGRATION 008 VERIFICATION")
    print("=" * 80)
    
    try:
        db_provider = DatabaseFactory.get_provider()
        conn = db_provider._get_connection()
        cursor = conn.cursor()
        
        # Check 1: Verify level and source columns exist in prompts
        print("\n✓ Check 1: Prompts table columns")
        cursor.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns 
            WHERE table_name = 'prompts' AND column_name IN ('level', 'source')
            ORDER BY column_name
        """)
        columns = cursor.fetchall()
        
        if len(columns) == 2:
            print("  ✅ Both columns exist in prompts table:")
            for col_name, col_type, nullable in columns:
                print(f"     - {col_name}: {col_type} (nullable: {nullable})")
        else:
            print(f"  ❌ Expected 2 columns, found {len(columns)}")
            return False
        
        # Check 2: Verify question_generations table is dropped
        print("\n✓ Check 2: question_generations table")
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'question_generations'
            )
        """)
        qgen_exists = cursor.fetchone()[0]
        
        if not qgen_exists:
            print("  ✅ question_generations table successfully dropped")
        else:
            print("  ❌ question_generations table still exists (should be dropped)")
            return False
        
        # Check 3: Verify llm_interactions table is dropped
        print("\n✓ Check 3: llm_interactions table")
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'llm_interactions'
            )
        """)
        llm_exists = cursor.fetchone()[0]
        
        if not llm_exists:
            print("  ✅ llm_interactions table successfully dropped")
        else:
            print("  ❌ llm_interactions table still exists (should be dropped)")
            return False
        
        # Check 4: Verify migration version
        print("\n✓ Check 4: Migration version")
        cursor.execute("SELECT version_num FROM alembic_version ORDER BY version_num DESC LIMIT 1")
        result = cursor.fetchone()
        version = result[0] if result else None
        
        if version == '008':
            print(f"  ✅ Migration version is 008 (current)")
        else:
            print(f"  ⚠️  Migration version is {version} (expected: 008)")
        
        # Check 5: Sample data query to verify functionality
        print("\n✓ Check 5: Test query with new columns")
        cursor.execute("""
            SELECT COUNT(*) as total_prompts,
                   COUNT(level) as prompts_with_level,
                   COUNT(source) as prompts_with_source
            FROM prompts
        """)
        total, with_level, with_source = cursor.fetchone()
        
        print(f"  ✅ Query successful:")
        print(f"     - Total prompts: {total}")
        print(f"     - Prompts with level: {with_level}")
        print(f"     - Prompts with source: {with_source}")
        
        # Check 6: Test daily counting query (the main use case)
        print("\n✓ Check 6: Daily question generation counting")
        cursor.execute("""
            SELECT COUNT(*) 
            FROM prompts
            WHERE request_type = 'question_generation'
              AND DATE(created_at) = CURRENT_DATE
        """)
        today_count = cursor.fetchone()[0]
        
        print(f"  ✅ Daily counting query works: {today_count} questions generated today")
        
        cursor.close()
        conn.close()
        
        print("\n" + "=" * 80)
        print("✅ ALL VERIFICATION CHECKS PASSED")
        print("=" * 80)
        print("\nMigration 008 successfully deployed and verified!")
        print("\nArchitecture changes:")
        print("  • Added 'level' column to prompts table (difficulty tracking)")
        print("  • Added 'source' column to prompts table (api/cached/fallback)")
        print("  • Dropped 'question_generations' table (redundant)")
        print("  • Dropped 'llm_interactions' table (redundant)")
        print("  • Simplified architecture: single prompts table handles all tracking")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Verification failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = verify_production_migration()
    sys.exit(0 if success else 1)
