"""Show actual prompts table structure."""

import psycopg2
from app.config import NEON_DBNAME, NEON_USER, NEON_PASSWORD, NEON_HOST, NEON_SSLMODE

def show_prompts_structure():
    """Show current prompts table structure."""
    
    conn = psycopg2.connect(
        dbname=NEON_DBNAME,
        user=NEON_USER,
        password=NEON_PASSWORD,
        host=NEON_HOST,
        sslmode=NEON_SSLMODE
    )
    cursor = conn.cursor()
    
    print("\n=== Current Prompts Table Structure ===\n")
    cursor.execute("""
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns 
        WHERE table_name = 'prompts'
        ORDER BY ordinal_position
    """)
    
    columns = cursor.fetchall()
    print("Columns:")
    for col_name, data_type, nullable, default in columns:
        null_str = "NULL" if nullable == 'YES' else "NOT NULL"
        default_str = f" DEFAULT {default}" if default else ""
        print(f"   {col_name:20} {data_type:20} {null_str:10} {default_str}")
    
    print("\n" + "="*70)
    print("Code expects these ADDITIONAL columns:")
    print("="*70)
    expected = [
        ("request_type", "VARCHAR(50)", "NOT NULL", "DEFAULT 'question_generation'"),
        ("model_name", "VARCHAR(100)", "NULL", ""),
        ("response_time_ms", "INTEGER", "NULL", ""),
        ("prompt_tokens", "INTEGER", "NULL", ""),
        ("completion_tokens", "INTEGER", "NULL", ""),
        ("total_tokens", "INTEGER", "NULL", ""),
        ("estimated_cost_usd", "FLOAT", "NULL", ""),
        ("status", "VARCHAR(50)", "NOT NULL", "DEFAULT 'success'"),
        ("error_message", "TEXT", "NULL", ""),
    ]
    
    existing_columns = [col[0] for col in columns]
    
    for col_name, data_type, nullable, default in expected:
        if col_name not in existing_columns:
            print(f"❌ {col_name:20} {data_type:20} {nullable:10} {default}")
    
    print("\n💡 These columns must be added for the code to work!")
    print("="*70 + "\n")
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    show_prompts_structure()
