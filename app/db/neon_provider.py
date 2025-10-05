import logging
from typing import List, Dict, Any
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime

from app.models.schemas import MathAttempt, UserRegistration
from app.db.db_interface import DatabaseProvider
from app.db.models import QuestionPattern
from app.db.db_initializer import DatabaseInitializer
from app.config import MAX_ATTEMPTS_HISTORY_LIMIT

logger = logging.getLogger(__name__)

class NeonProvider(DatabaseProvider):
    """Neon PostgreSQL implementation of the database provider."""
    
    def __init__(self, dbname: str, user: str, password: str, host: str, sslmode: str = "require"):
        """
        Initialize the Neon provider with connection parameters.
        
        Args:
            dbname: The database name
            user: Database username
            password: Database password
            host: Database host
            sslmode: SSL mode (default: require)
        """
        self.dbname = dbname
        self.user = user
        self.password = password
        self.host = host
        self.sslmode = sslmode
        self.table_name = 'attempts'
        
        # For local PostgreSQL (localhost), try to ensure database exists
        if host == 'localhost':
            connection_params = {
                'dbname': dbname,
                'user': user,
                'password': password,
                'host': host,
                'sslmode': sslmode
            }
            
            try:
                success = DatabaseInitializer.ensure_postgres_database_exists(connection_params)
                if success:
                    logger.info(f"Database '{dbname}' is ready for use")
                else:
                    logger.warning(f"Could not auto-create database '{dbname}'. Manual setup may be required.")
            except Exception as e:
                logger.warning(f"Database auto-creation failed: {e}. Will attempt to connect anyway.")
    
    def _get_connection(self):
        """Create and return a new database connection."""
        return psycopg2.connect(
            dbname=self.dbname,
            user=self.user,
            password=self.password,
            host=self.host,
            sslmode=self.sslmode
        )
    
    def init_db(self) -> None:
        """
        Initialize the Neon database by creating all required tables if they don't exist.
        This method creates the complete schema including all migration changes.
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            logger.info(f"Connected to Neon PostgreSQL at {self.host}")
            
            # Create attempts table if it doesn't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS attempts (
                    id SERIAL PRIMARY KEY,
                    student_id INTEGER NOT NULL,
                    uid TEXT NOT NULL,
                    datetime TIMESTAMP NOT NULL,
                    question TEXT NOT NULL,
                    is_answer_correct BOOLEAN NOT NULL,
                    incorrect_answer TEXT,
                    correct_answer TEXT NOT NULL,
                    qorder INTEGER
                )
            """)
            
            # Create question_patterns table if it doesn't exist (includes notes and level columns)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS question_patterns (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    type TEXT NOT NULL,
                    pattern_text TEXT NOT NULL,
                    notes TEXT,
                    level INTEGER,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """)
            
            # Create users table if it doesn't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    uid TEXT UNIQUE NOT NULL,
                    email TEXT NOT NULL,
                    name TEXT NOT NULL,
                    display_name TEXT NOT NULL,
                    grade_level INTEGER NOT NULL,
                    subscription INTEGER DEFAULT 0,
                    registration_date TIMESTAMPTZ NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """)
            
            # Create alembic_version table for migration tracking
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS alembic_version (
                    version_num VARCHAR(32) NOT NULL,
                    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
                )
            """)
            
            # Check if this is a fresh installation or needs migration updates
            cursor.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'question_patterns'")
            patterns_table_existed = cursor.fetchone()[0] > 0
            
            if not patterns_table_existed:
                # Fresh installation - set the migration version to latest
                cursor.execute("DELETE FROM alembic_version")
                cursor.execute("INSERT INTO alembic_version (version_num) VALUES ('006')")
                logger.info("Fresh installation: Set migration version to 006")
            else:
                # Existing installation - check if notes and level columns exist
                cursor.execute("""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_name = 'question_patterns' AND column_name IN ('notes', 'level')
                """)
                existing_columns = [row[0] for row in cursor.fetchall()]
                
                if 'notes' not in existing_columns:
                    # Add notes column if it doesn't exist
                    cursor.execute("ALTER TABLE question_patterns ADD COLUMN notes TEXT")
                    logger.info("Added notes column to existing question_patterns table")
                
                if 'level' not in existing_columns:
                    # Add level column if it doesn't exist
                    cursor.execute("ALTER TABLE question_patterns ADD COLUMN level INTEGER")
                    logger.info("Added level column to existing question_patterns table")
                
                # Update migration version if needed
                cursor.execute("SELECT version_num FROM alembic_version ORDER BY version_num DESC LIMIT 1")
                current_version = cursor.fetchone()
                if not current_version or current_version[0] < '006':
                    cursor.execute("DELETE FROM alembic_version")
                    cursor.execute("INSERT INTO alembic_version (version_num) VALUES ('007')")
                    logger.info("Updated migration version to 007")
            
            # Check and add subscription column to users table if needed (Migration 007)
            cursor.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'users' AND column_name = 'subscription'
            """)
            subscription_column_exists = cursor.fetchall()
            
            if not subscription_column_exists:
                # Add subscription column with default value 0 (free users)
                cursor.execute("ALTER TABLE users ADD COLUMN subscription INTEGER DEFAULT 0")
                logger.info("Added subscription column to existing users table with default value 0 (free users)")
            
            conn.commit()
            logger.info("Successfully initialized Neon database with all tables and migrations")
            cursor.close()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to initialize Neon database: {e}")
            raise Exception(f"Database initialization error: {e}")
    
    def save_user_registration(self, user: UserRegistration) -> None:
        """Save a user registration to the Neon database."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Convert ISO string to datetime object
            registration_date = datetime.fromisoformat(user.registrationDate.replace('Z', '+00:00'))
            
            # Insert or update the user registration
            cursor.execute("""
                INSERT INTO users (uid, email, name, display_name, grade_level, subscription, registration_date, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (uid) 
                DO UPDATE SET 
                    email = EXCLUDED.email,
                    name = EXCLUDED.name,
                    display_name = EXCLUDED.display_name,
                    grade_level = EXCLUDED.grade_level,
                    subscription = EXCLUDED.subscription,
                    updated_at = NOW()
            """, (
                user.uid,
                user.email,
                user.name,
                user.displayName,
                user.gradeLevel,
                user.subscription,
                registration_date
            ))
            
            conn.commit()
            logger.debug(f"User registration saved for uid: {user.uid}")
            cursor.close()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error saving user registration to Neon: {e}")
            raise Exception(f"Database error: {e}")
        
    def save_attempt(self, attempt: MathAttempt) -> None:
        """Save a math attempt to the Neon database."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Insert the attempt
            cursor.execute("""
                INSERT INTO attempts 
                (student_id, uid, datetime, question, is_answer_correct, incorrect_answer, correct_answer, qorder)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                attempt.student_id,
                attempt.uid,
                attempt.datetime,
                attempt.question,
                attempt.is_answer_correct,
                attempt.incorrect_answer or "",
                attempt.correct_answer,
                attempt.qorder
            ))
            
            conn.commit()
            logger.debug(f"Attempt saved for student {attempt.student_id}")
            cursor.close()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error saving attempt to Neon: {e}")
            raise Exception(f"Database error: {e}")
    
    def get_attempts(self, student_id: int) -> List[Dict[str, Any]]:
        """Retrieve attempts for a specific student from the Neon database."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
              # Query for attempts by student_id
            cursor.execute("""
                SELECT question, is_answer_correct, incorrect_answer, correct_answer, datetime, uid, qorder
                FROM attempts
                WHERE student_id = %s
                ORDER BY datetime DESC, qorder ASC
                LIMIT %s
            """, (student_id, MAX_ATTEMPTS_HISTORY_LIMIT))
            
            data = cursor.fetchall()
            cursor.close()
            conn.close()
              # Format the data to match the expected schema
            attempts = [{
                "question": item['question'],
                "is_correct": bool(item['is_answer_correct']),
                "incorrect_answer": item['incorrect_answer'] if item['incorrect_answer'] else "",
                "correct_answer": str(item['correct_answer']) if item['correct_answer'] else "",
                "datetime": item['datetime'].isoformat() if isinstance(item['datetime'], datetime) else item['datetime'],
                "uid": item['uid']
            } for item in data]
            
            logger.debug(f"Retrieved {len(attempts)} out of {MAX_ATTEMPTS_HISTORY_LIMIT} max attempts for student {student_id}")
            return attempts
            
        except Exception as e:
            logger.error(f"Error retrieving attempts from Neon: {e}")
            raise Exception(f"Database error: {e}")

    def get_attempts_by_uid(self, uid: str) -> List[Dict[str, Any]]:
        """Retrieve attempts for a specific user by UID from the Neon database."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Query for attempts by uid
            cursor.execute("""
                SELECT question, is_answer_correct, incorrect_answer, correct_answer, datetime, uid, student_id, qorder
                FROM attempts
                WHERE uid = %s
                ORDER BY datetime DESC, qorder ASC
                LIMIT %s
            """, (uid, MAX_ATTEMPTS_HISTORY_LIMIT))
            
            data = cursor.fetchall()
            cursor.close()
            conn.close()
            
            # Format the data to match the expected schema
            attempts = [{
                "question": item['question'],
                "is_correct": bool(item['is_answer_correct']),
                "incorrect_answer": item['incorrect_answer'] if item['incorrect_answer'] else "",
                "correct_answer": str(item['correct_answer']) if item['correct_answer'] else "",
                "datetime": item['datetime'].isoformat() if isinstance(item['datetime'], datetime) else item['datetime'],
                "uid": item['uid'],
                "student_id": item['student_id']
            } for item in data]
            
            logger.debug(f"Retrieved {len(attempts)} out of {MAX_ATTEMPTS_HISTORY_LIMIT} max attempts for user with UID {uid}")
            return attempts
            
        except Exception as e:
            logger.error(f"Error retrieving attempts by UID from Neon: {e}")
            raise Exception(f"Database error: {e}")

    def get_question_patterns(self):
        """Retrieve all question patterns from the database."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # Query to fetch all question patterns
            cursor.execute("""
                SELECT id, type, pattern_text, notes, level, created_at
                FROM question_patterns
            """)

            patterns = cursor.fetchall()
            cursor.close()
            conn.close()

            return patterns
        except Exception as e:
            logger.error(f"Error retrieving question patterns: {e}")
            raise Exception(f"Database error: {e}")

    def get_question_patterns_by_level(self, level: int = None):
        """Retrieve question patterns filtered by level."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            if level is not None:
                # Query to fetch patterns with specific level or null level
                cursor.execute("""
                    SELECT id, type, pattern_text, notes, level, created_at
                    FROM question_patterns
                    WHERE level = %s OR level IS NULL
                    ORDER BY level ASC
                """, (level,))
            else:
                # Query to fetch all question patterns
                cursor.execute("""
                    SELECT id, type, pattern_text, notes, level, created_at
                    FROM question_patterns
                    ORDER BY level ASC
                """)

            patterns = cursor.fetchall()
            cursor.close()
            conn.close()

            logger.debug(f"Retrieved {len(patterns)} patterns for level {level}")
            return patterns
        except Exception as e:
            logger.error(f"Error retrieving question patterns by level: {e}")
            raise Exception(f"Database error: {e}")

    def get_user_by_uid(self, uid: str) -> Dict[str, Any]:
        """Retrieve user registration data by UID."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("""
                SELECT uid, email, name, display_name, grade_level, subscription, registration_date, updated_at
                FROM users
                WHERE uid = %s
            """, (uid,))
            
            user = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if user:
                logger.debug(f"Retrieved user data for uid: {uid}")
                return dict(user)
            else:
                logger.debug(f"No user found for uid: {uid}")
                return {}
                
        except Exception as e:
            logger.error(f"Error retrieving user by uid: {e}")
            raise Exception(f"Database error: {e}")

    def get_user_by_email(self, email: str) -> Dict[str, Any]:
        """Retrieve user registration data by email."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("""
                SELECT uid, email, name, display_name, grade_level, subscription, registration_date, updated_at
                FROM users
                WHERE email = %s
            """, (email,))
            
            user = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if user:
                logger.debug(f"Retrieved user data for email: {email}")
                return dict(user)
            else:
                logger.debug(f"No user found for email: {email}")
                return {}
                
        except Exception as e:
            logger.error(f"Error retrieving user by email: {e}")
            raise Exception(f"Database error: {e}")