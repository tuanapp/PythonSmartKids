"""
Script to run the user blocking migration on Neon PostgreSQL database
"""
import psycopg2
import sys
from pathlib import Path

# Database connection string
DATABASE_URL = "postgresql://tuanapp:HdzrNIKh5mM1@ep-sparkling-butterfly-33773987.ap-southeast-1.aws.neon.tech/tuandb?sslmode=require"

def run_migration():
    """Run the user blocking migration SQL script"""
    
    # Read the migration SQL file
    migration_file = Path(__file__).parent / "migrations" / "add_user_blocking.sql"
    
    if not migration_file.exists():
        print(f"Error: Migration file not found at {migration_file}")
        return False
    
    with open(migration_file, 'r', encoding='utf-8') as f:
        migration_sql = f.read()
    
    print("Connecting to database...")
    print(f"Host: ep-sparkling-butterfly-33773987.ap-southeast-1.aws.neon.tech")
    print(f"Database: tuandb")
    print()
    
    try:
        # Connect to database
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = False
        cursor = conn.cursor()
        
        print("Executing migration SQL...")
        print("=" * 60)
        
        # Execute the migration
        cursor.execute(migration_sql)
        
        # Commit the transaction
        conn.commit()
        
        print("✓ Migration executed successfully!")
        print()
        
        # Verify the changes
        print("Verifying database changes...")
        print("-" * 60)
        
        # Check if blocking fields exist in users table
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'users' 
            AND column_name IN ('is_blocked', 'blocked_reason', 'blocked_at', 'blocked_by')
            ORDER BY column_name;
        """)
        
        user_columns = cursor.fetchall()
        if user_columns:
            print("\n✓ Blocking fields added to 'users' table:")
            for col_name, col_type in user_columns:
                print(f"  - {col_name} ({col_type})")
        else:
            print("⚠ Warning: Blocking fields not found in users table")
        
        # Check if user_blocking_history table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'user_blocking_history'
            );
        """)
        
        table_exists = cursor.fetchone()[0]
        if table_exists:
            print("\n✓ 'user_blocking_history' table created")
            
            # Get column info
            cursor.execute("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'user_blocking_history'
                ORDER BY ordinal_position;
            """)
            
            columns = cursor.fetchall()
            print("  Columns:")
            for col_name, col_type in columns:
                print(f"    - {col_name} ({col_type})")
        else:
            print("⚠ Warning: user_blocking_history table not found")
        
        # Check indexes
        cursor.execute("""
            SELECT indexname 
            FROM pg_indexes 
            WHERE tablename IN ('users', 'user_blocking_history')
            AND indexname LIKE '%block%'
            ORDER BY indexname;
        """)
        
        indexes = cursor.fetchall()
        if indexes:
            print("\n✓ Indexes created:")
            for idx in indexes:
                print(f"  - {idx[0]}")
        
        print("\n" + "=" * 60)
        print("✓ Migration completed successfully!")
        print()
        
        cursor.close()
        conn.close()
        
        return True
        
    except psycopg2.Error as e:
        print(f"\n✗ Database error: {e}")
        print(f"Error code: {e.pgcode}")
        if conn:
            conn.rollback()
            conn.close()
        return False
        
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        if conn:
            conn.rollback()
            conn.close()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("User Blocking System - Database Migration")
    print("=" * 60)
    print()
    
    success = run_migration()
    
    if success:
        print("\n🎉 You can now use the user blocking system!")
        print()
        print("Next steps:")
        print("1. Set ADMIN_KEY environment variable")
        print("2. Deploy backend changes")
        print("3. Test the blocking endpoints")
        sys.exit(0)
    else:
        print("\n⚠ Migration failed. Please check the errors above.")
        sys.exit(1)
