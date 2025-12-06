"""
Script to check existing database schema
"""
import psycopg2

# Database connection string
DATABASE_URL = "postgresql://tuanapp:HdzrNIKh5mM1@ep-sparkling-butterfly-33773987.ap-southeast-1.aws.neon.tech/tuandb?sslmode=require"

def check_schema():
    """Check existing database schema"""
    
    print("Connecting to database...")
    print(f"Host: ep-sparkling-butterfly-33773987.ap-southeast-1.aws.neon.tech")
    print(f"Database: tuandb")
    print()
    
    try:
        # Connect to database
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        print("=" * 60)
        print("EXISTING TABLES")
        print("=" * 60)
        
        # List all tables
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        
        tables = cursor.fetchall()
        if tables:
            print(f"\nFound {len(tables)} table(s):")
            for table in tables:
                print(f"  - {table[0]}")
                
                # Get columns for each table
                cursor.execute("""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns 
                    WHERE table_name = %s
                    ORDER BY ordinal_position;
                """, (table[0],))
                
                columns = cursor.fetchall()
                if columns:
                    print(f"    Columns ({len(columns)}):")
                    for col_name, col_type, nullable in columns:
                        null_str = "NULL" if nullable == "YES" else "NOT NULL"
                        print(f"      - {col_name} ({col_type}, {null_str})")
                print()
        else:
            print("\n⚠ No tables found in the database!")
        
        print("=" * 60)
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        if conn:
            conn.close()

if __name__ == "__main__":
    check_schema()
