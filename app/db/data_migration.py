import logging
import sqlite3
from datetime import datetime
import os

from app.config import DATABASE_URL, SUPABASE_URL, SUPABASE_KEY
from app.db.sqlite_provider import SQLiteProvider
from app.db.supabase_provider import SupabaseProvider
from app.models.schemas import MathAttempt

logger = logging.getLogger(__name__)

def migrate_sqlite_to_supabase():
    """
    Migrate data from SQLite database to Supabase.
    
    This function reads all data from the SQLite database
    and writes it to the Supabase database.
    """
    try:
        # Initialize providers
        sqlite_path = DATABASE_URL.replace("sqlite:///", "")
        sqlite_provider = SQLiteProvider(sqlite_path)
        supabase_provider = SupabaseProvider(SUPABASE_URL, SUPABASE_KEY)
        
        # Check if the SQLite file exists
        if not os.path.exists(sqlite_path):
            logger.error(f"SQLite database file not found: {sqlite_path}")
            return False
        
        logger.info(f"Starting migration from SQLite ({sqlite_path}) to Supabase ({SUPABASE_URL})")
        
        # Connect to SQLite and fetch all attempts
        conn = sqlite3.connect(sqlite_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT student_id, datetime, question, is_answer_correct, incorrect_answer, correct_answer
            FROM attempts
        """)
        rows = cursor.fetchall()
        conn.close()
        
        logger.info(f"Found {len(rows)} records to migrate")
        
        # Insert each record into Supabase
        for i, row in enumerate(rows):
            try:
                # Parse the datetime string to a datetime object
                dt_str = row['datetime']
                try:
                    # Try ISO format first
                    dt = datetime.fromisoformat(dt_str)
                except ValueError:
                    # Fall back to other formats
                    dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
                
                # Create attempt object
                attempt = MathAttempt(
                    student_id=row['student_id'],
                    datetime=dt,
                    question=row['question'],
                    is_answer_correct=bool(row['is_answer_correct']),
                    incorrect_answer=row['incorrect_answer'] if row['incorrect_answer'] else "",
                    correct_answer=row['correct_answer']
                )
                
                # Save to Supabase
                supabase_provider.save_attempt(attempt)
                
                if (i + 1) % 10 == 0:
                    logger.info(f"Migrated {i + 1}/{len(rows)} records")
                    
            except Exception as e:
                logger.error(f"Error migrating record {i}: {e}")
        
        logger.info(f"Migration completed. {len(rows)} records transferred to Supabase.")
        return True
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return False

def migrate_supabase_to_sqlite():
    """
    Migrate data from Supabase database to SQLite.
    
    This function reads all data from the Supabase database
    and writes it to the SQLite database.
    """
    try:
        # Initialize providers
        sqlite_path = DATABASE_URL.replace("sqlite:///", "")
        sqlite_provider = SQLiteProvider(sqlite_path)
        supabase_provider = SupabaseProvider(SUPABASE_URL, SUPABASE_KEY)
        
        logger.info(f"Starting migration from Supabase ({SUPABASE_URL}) to SQLite ({sqlite_path})")
        
        # Ensure SQLite database is initialized
        sqlite_provider.init_db()
        
        # Fetch all students to migrate
        from supabase import create_client
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        # Get list of unique student IDs
        response = supabase.table('attempts').select('student_id').execute()
        if hasattr(response, 'error') and response.error:
            raise Exception(f"Supabase error: {response.error}")
        
        student_ids = set(item['student_id'] for item in response.data)
        logger.info(f"Found {len(student_ids)} students to migrate")
        
        total_records = 0
        
        # Migrate data for each student
        for student_id in student_ids:
            try:
                # Get attempts for this student
                attempts = supabase_provider.get_attempts(student_id)
                
                for attempt_data in attempts:
                    try:
                        # Parse the datetime string
                        dt_str = attempt_data['datetime']
                        try:
                            # Try ISO format first
                            dt = datetime.fromisoformat(dt_str)
                        except ValueError:
                            # Fall back to other formats
                            dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
                        
                        # Create attempt object
                        attempt = MathAttempt(
                            student_id=student_id,
                            datetime=dt,
                            question=attempt_data['question'],
                            is_answer_correct=attempt_data['is_correct'],
                            incorrect_answer=attempt_data['incorrect_answer'],
                            correct_answer=attempt_data['correct_answer']
                        )
                        
                        # Save to SQLite
                        sqlite_provider.save_attempt(attempt)
                        total_records += 1
                        
                    except Exception as e:
                        logger.error(f"Error migrating record for student {student_id}: {e}")
                
                logger.info(f"Migrated {len(attempts)} records for student {student_id}")
                
            except Exception as e:
                logger.error(f"Error processing student {student_id}: {e}")
        
        logger.info(f"Migration completed. {total_records} records transferred to SQLite.")
        return True
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return False

if __name__ == "__main__":
    import sys
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    if len(sys.argv) < 2:
        print("Usage: python -m app.db.data_migration [to_supabase|to_sqlite]")
        sys.exit(1)
        
    direction = sys.argv[1].lower()
    
    if direction == "to_supabase":
        success = migrate_sqlite_to_supabase()
    elif direction == "to_sqlite":
        success = migrate_supabase_to_sqlite()
    else:
        print(f"Unknown direction: {direction}")
        print("Usage: python -m app.db.data_migration [to_supabase|to_sqlite]")
        sys.exit(1)
        
    if success:
        print("Migration completed successfully!")
        sys.exit(0)
    else:
        print("Migration failed. See logs for details.")
        sys.exit(1)