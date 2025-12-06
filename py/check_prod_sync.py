"""
Script to check production DB schema vs expected model schema
"""
import psycopg2

DATABASE_URL = "postgresql://tuanapp:HdzrNIKh5mM1@ep-sparkling-butterfly-33773987.ap-southeast-1.aws.neon.tech/smartboydb?sslmode=require"

# Expected tables and columns from models.py
EXPECTED_SCHEMA = {
    "attempts": {
        "id": "integer",
        "student_id": "integer",
        "uid": "character varying",
        "datetime": "timestamp",
        "question": "text",
        "is_answer_correct": "boolean",
        "incorrect_answer": "text",
        "correct_answer": "text",
        "qorder": "integer",
    },
    "question_patterns": {
        "id": "uuid",
        "type": "character varying",
        "pattern_text": "text",
        "notes": "text",
        "level": "integer",
        "created_at": "timestamp",
    },
    "prompts": {
        "id": "integer",
        "uid": "character varying",
        "request_type": "character varying",
        "request_text": "text",
        "model_name": "character varying",
        "level": "integer",
        "source": "character varying",
        "response_text": "text",
        "response_time_ms": "integer",
        "prompt_tokens": "integer",
        "completion_tokens": "integer",
        "total_tokens": "integer",
        "estimated_cost_usd": "double precision",
        "status": "character varying",
        "error_message": "text",
        "is_live": "integer",
        "created_at": "timestamp",
    },
    "users": {
        "id": "integer",
        "uid": "character varying",
        "email": "character varying",
        "name": "character varying",
        "display_name": "character varying",
        "grade_level": "integer",
        "subscription": "integer",
        "registration_date": "timestamp",
        "is_blocked": "boolean",
        "blocked_reason": "text",
        "blocked_at": "timestamp",
        "blocked_by": "character varying",
        "created_at": "timestamp",
        "updated_at": "timestamp",
    },
    "user_blocking_history": {
        "id": "integer",
        "user_uid": "character varying",
        "action": "character varying",
        "reason": "text",
        "blocked_at": "timestamp",
        "blocked_by": "character varying",
        "unblocked_at": "timestamp",
        "notes": "text",
    },
}

def check_sync():
    print("=" * 70)
    print("PRODUCTION DB SCHEMA SYNC CHECK")
    print("=" * 70)
    
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    # Get all tables
    cursor.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
        ORDER BY table_name;
    """)
    prod_tables = {row[0] for row in cursor.fetchall()}
    
    # Check alembic_version
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_name = 'alembic_version'
        );
    """)
    has_alembic = cursor.fetchone()[0]
    
    if has_alembic:
        cursor.execute("SELECT version_num FROM alembic_version;")
        versions = cursor.fetchall()
        print(f"\nAlembic version(s): {[v[0] for v in versions]}")
    else:
        print("\n⚠ No alembic_version table found (migrations not tracked)")
    
    print("\n" + "-" * 70)
    print("TABLE COMPARISON")
    print("-" * 70)
    
    expected_tables = set(EXPECTED_SCHEMA.keys())
    
    missing_tables = expected_tables - prod_tables
    extra_tables = prod_tables - expected_tables - {"alembic_version", "playing_with_neon"}
    
    print(f"\nExpected tables: {sorted(expected_tables)}")
    print(f"Production tables: {sorted(prod_tables)}")
    
    if missing_tables:
        print(f"\n❌ MISSING TABLES in production: {sorted(missing_tables)}")
    else:
        print(f"\n✓ All expected tables exist")
    
    if extra_tables:
        print(f"\n⚠ EXTRA TABLES in production (not in models): {sorted(extra_tables)}")
    
    print("\n" + "-" * 70)
    print("COLUMN COMPARISON")
    print("-" * 70)
    
    for table_name, expected_cols in EXPECTED_SCHEMA.items():
        print(f"\n[{table_name}]")
        
        if table_name not in prod_tables:
            print(f"  ❌ TABLE MISSING - cannot check columns")
            continue
        
        cursor.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns 
            WHERE table_name = %s
            ORDER BY ordinal_position;
        """, (table_name,))
        
        prod_cols = {row[0]: row[1] for row in cursor.fetchall()}
        
        missing_cols = set(expected_cols.keys()) - set(prod_cols.keys())
        extra_cols = set(prod_cols.keys()) - set(expected_cols.keys())
        
        if missing_cols:
            print(f"  ❌ MISSING columns: {sorted(missing_cols)}")
        
        if extra_cols:
            print(f"  ⚠ EXTRA columns: {sorted(extra_cols)}")
        
        if not missing_cols and not extra_cols:
            print(f"  ✓ All columns present")
        
        # Check column types (loose match)
        for col_name in set(expected_cols.keys()) & set(prod_cols.keys()):
            expected_type = expected_cols[col_name]
            actual_type = prod_cols[col_name]
            if expected_type not in actual_type and actual_type not in expected_type:
                print(f"  ⚠ Type mismatch: {col_name} expected '{expected_type}', got '{actual_type}'")
    
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    total_missing = len(missing_tables)
    if total_missing > 0:
        print(f"\n❌ {total_missing} table(s) MISSING from production")
        print("   These need to be created via migrations or manual SQL")
    else:
        print("\n✓ All expected tables exist in production")
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    check_sync()
