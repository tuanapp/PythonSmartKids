"""
Hotfix migration to add missing columns to prompts table and fix question_generations.

This migration fixes the production database to match our consolidated architecture.
"""

import psycopg2
from app.config import NEON_DBNAME, NEON_USER, NEON_PASSWORD, NEON_HOST, NEON_SSLMODE

def apply_hotfix_migration():
    """Apply hotfix migration to production database."""
    
    conn = psycopg2.connect(
        dbname=NEON_DBNAME,
        user=NEON_USER,
        password=NEON_PASSWORD,
        host=NEON_HOST,
        sslmode=NEON_SSLMODE
    )
    cursor = conn.cursor()
    
    try:
        print("\n" + "="*70)
        print("HOTFIX MIGRATION: Enhance Prompts Table & Fix Question Generations")
        print("="*70 + "\n")
        
        # Step 1: Add missing columns to prompts table
        print("Step 1: Adding missing columns to prompts table...")
        
        columns_to_add = [
            ("request_type", "VARCHAR(50)", "DEFAULT 'question_generation'"),
            ("model_name", "VARCHAR(100)", "DEFAULT NULL"),
            ("response_time_ms", "INTEGER", "DEFAULT NULL"),
            ("prompt_tokens", "INTEGER", "DEFAULT NULL"),
            ("completion_tokens", "INTEGER", "DEFAULT NULL"),
            ("total_tokens", "INTEGER", "DEFAULT NULL"),
            ("estimated_cost_usd", "FLOAT", "DEFAULT NULL"),
            ("status", "VARCHAR(50)", "DEFAULT 'success'"),
            ("error_message", "TEXT", "DEFAULT NULL"),
        ]
        
        for col_name, col_type, col_default in columns_to_add:
            try:
                cursor.execute(f"""
                    ALTER TABLE prompts 
                    ADD COLUMN IF NOT EXISTS {col_name} {col_type} {col_default}
                """)
                print(f"   ✅ Added column: {col_name}")
            except Exception as e:
                print(f"   ⚠️  Column {col_name}: {e}")
        
        # Step 2: Check if question_generations has llm_interaction_id or prompt_id
        print("\nStep 2: Checking question_generations structure...")
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'question_generations'
            AND column_name IN ('llm_interaction_id', 'prompt_id')
        """)
        existing_cols = [row[0] for row in cursor.fetchall()]
        
        has_llm_id = 'llm_interaction_id' in existing_cols
        has_prompt_id = 'prompt_id' in existing_cols
        
        print(f"   Current state: llm_interaction_id={has_llm_id}, prompt_id={has_prompt_id}")
        
        if has_llm_id and not has_prompt_id:
            print("\n   Need to rename llm_interaction_id to prompt_id...")
            
            # Drop foreign key constraint if exists
            cursor.execute("""
                SELECT constraint_name 
                FROM information_schema.table_constraints 
                WHERE table_name = 'question_generations' 
                AND constraint_type = 'FOREIGN KEY'
                AND constraint_name LIKE '%llm_interaction%'
            """)
            fk_constraints = cursor.fetchall()
            
            for (constraint_name,) in fk_constraints:
                cursor.execute(f"""
                    ALTER TABLE question_generations 
                    DROP CONSTRAINT IF EXISTS {constraint_name}
                """)
                print(f"   ✅ Dropped constraint: {constraint_name}")
            
            # Rename column
            cursor.execute("""
                ALTER TABLE question_generations 
                RENAME COLUMN llm_interaction_id TO prompt_id
            """)
            print("   ✅ Renamed llm_interaction_id to prompt_id")
            
            # Add new foreign key to prompts
            cursor.execute("""
                ALTER TABLE question_generations 
                ADD CONSTRAINT fk_question_gen_prompt 
                FOREIGN KEY (prompt_id) REFERENCES prompts(id) ON DELETE SET NULL
            """)
            print("   ✅ Added foreign key to prompts table")
            
        elif has_prompt_id:
            print("   ✅ Already has prompt_id column")
        else:
            print("   ⚠️  Neither column exists, adding prompt_id...")
            cursor.execute("""
                ALTER TABLE question_generations 
                ADD COLUMN prompt_id INTEGER REFERENCES prompts(id) ON DELETE SET NULL
            """)
            print("   ✅ Added prompt_id column")
        
        # Commit all changes
        conn.commit()
        
        print("\n" + "="*70)
        print("✅ HOTFIX MIGRATION COMPLETED SUCCESSFULLY!")
        print("="*70)
        print("\nChanges applied:")
        print("  ✅ Enhanced prompts table with 9 new columns")
        print("  ✅ Updated question_generations to reference prompts")
        print("\nThe application should now work correctly!")
        print("="*70 + "\n")
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ ERROR: {e}")
        print("Migration rolled back.")
        raise
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    import sys
    
    print("\n⚠️  WARNING: This will modify the production database!")
    print("This migration will:")
    print("  1. Add 9 new columns to the prompts table")
    print("  2. Rename llm_interaction_id to prompt_id in question_generations")
    print("  3. Update foreign key relationships")
    
    response = input("\nDo you want to proceed? (yes/no): ")
    
    if response.lower() == 'yes':
        apply_hotfix_migration()
    else:
        print("Migration cancelled.")
        sys.exit(0)
