import logging
from typing import List, Dict, Any
import sqlite3
from datetime import datetime
import os

from app.models.schemas import MathAttempt, UserRegistration
from app.db.db_interface import DatabaseProvider
from app.db.models import QuestionPattern
from app.config import MAX_ATTEMPTS_HISTORY_LIMIT

logger = logging.getLogger(__name__)

class SQLiteProvider(DatabaseProvider):
    """SQLite implementation of the database provider for local development."""
    
    def __init__(self, db_path: str = "./local_dev.db"):
        """
        Initialize the SQLite provider with database path.
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        logger.info(f"Initializing SQLite provider with database at: {db_path}")
    
    def _get_connection(self):
        """Create and return a new database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable dict-like access to rows
        return conn
    
    def init_db(self) -> None:
        """Initialize the SQLite database by creating all required tables if they don't exist."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            logger.info(f"Connected to SQLite database at {self.db_path}")
            
            # Create attempts table if it doesn't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id INTEGER NOT NULL,
                    uid TEXT NOT NULL,
                    datetime TEXT NOT NULL,
                    question TEXT NOT NULL,
                    is_answer_correct BOOLEAN NOT NULL,
                    incorrect_answer TEXT,
                    correct_answer TEXT NOT NULL,
                    qorder INTEGER
                )
            """)
            
            # Create question_patterns table if it doesn't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS question_patterns (
                    id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    pattern_text TEXT NOT NULL,
                    notes TEXT,
                    level INTEGER,
                    created_at TEXT NOT NULL
                )
            """)
            
            # Create users table if it doesn't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    uid TEXT UNIQUE NOT NULL,
                    email TEXT NOT NULL,
                    name TEXT NOT NULL,
                    display_name TEXT NOT NULL,
                    grade_level INTEGER NOT NULL,
                    registration_date TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
            logger.info("Successfully initialized SQLite database with all tables")
            cursor.close()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to initialize SQLite database: {e}")
            raise Exception(f"Database initialization error: {e}")
    
    def save_user_registration(self, user: UserRegistration) -> None:
        """Save a user registration to the SQLite database."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Convert ISO string to datetime object for consistency
            registration_date = user.registrationDate
            
            # Insert or update the user registration
            cursor.execute("""
                INSERT OR REPLACE INTO users 
                (uid, email, name, display_name, grade_level, registration_date, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                user.uid,
                user.email,
                user.name,
                user.displayName,
                user.gradeLevel,
                registration_date,
                datetime.now().isoformat()
            ))
            
            conn.commit()
            logger.debug(f"User registration saved for uid: {user.uid}")
            cursor.close()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error saving user registration to SQLite: {e}")
            raise Exception(f"Database error: {e}")
    
    def save_attempt(self, attempt: MathAttempt) -> None:
        """Save a math attempt to the SQLite database."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Insert the attempt
            cursor.execute("""
                INSERT INTO attempts 
                (student_id, uid, datetime, question, is_answer_correct, incorrect_answer, correct_answer, qorder)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                attempt.student_id,
                attempt.uid,
                attempt.datetime.isoformat(),
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
            logger.error(f"Error saving attempt to SQLite: {e}")
            raise Exception(f"Database error: {e}")
    
    def get_attempts(self, student_id: int) -> List[Dict[str, Any]]:
        """Retrieve attempts for a specific student from the SQLite database."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT question, is_answer_correct, incorrect_answer, correct_answer, datetime, uid, qorder
                FROM attempts
                WHERE student_id = ?
                ORDER BY datetime DESC, qorder ASC
                LIMIT ?
            """, (student_id, MAX_ATTEMPTS_HISTORY_LIMIT))
            
            rows = cursor.fetchall()
            cursor.close()
            conn.close()
            
            # Format the data to match the expected schema
            attempts = [{
                "question": row['question'],
                "is_correct": bool(row['is_answer_correct']),
                "incorrect_answer": row['incorrect_answer'] if row['incorrect_answer'] else "",
                "correct_answer": str(row['correct_answer']) if row['correct_answer'] else "",
                "datetime": row['datetime'],
                "uid": row['uid']
            } for row in rows]
            
            logger.debug(f"Retrieved {len(attempts)} out of {MAX_ATTEMPTS_HISTORY_LIMIT} max attempts for student {student_id}")
            return attempts
            
        except Exception as e:
            logger.error(f"Error retrieving attempts from SQLite: {e}")
            raise Exception(f"Database error: {e}")

    def get_attempts_by_uid(self, uid: str) -> List[Dict[str, Any]]:
        """Retrieve attempts for a specific user by UID from the SQLite database."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT question, is_answer_correct, incorrect_answer, correct_answer, datetime, uid, qorder
                FROM attempts
                WHERE uid = ?
                ORDER BY datetime DESC, qorder ASC
                LIMIT ?
            """, (uid, MAX_ATTEMPTS_HISTORY_LIMIT))
            
            rows = cursor.fetchall()
            cursor.close()
            conn.close()
            
            # Format the data to match the expected schema
            attempts = [{
                "question": row['question'],
                "is_correct": bool(row['is_answer_correct']),
                "incorrect_answer": row['incorrect_answer'] if row['incorrect_answer'] else "",
                "correct_answer": str(row['correct_answer']) if row['correct_answer'] else "",
                "datetime": row['datetime'],
                "uid": row['uid']
            } for row in rows]
            
            logger.debug(f"Retrieved {len(attempts)} attempts for user with UID {uid}")
            return attempts
            
        except Exception as e:
            logger.error(f"Error retrieving attempts by UID from SQLite: {e}")
            raise Exception(f"Database error: {e}")

    def get_question_patterns(self) -> List[Dict[str, Any]]:
        """Retrieve all question patterns from the SQLite database."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, type, pattern_text, notes, level, created_at
                FROM question_patterns
                ORDER BY created_at DESC
            """)
            
            rows = cursor.fetchall()
            cursor.close()
            conn.close()
            
            patterns = [{
                "id": row['id'],
                "type": row['type'],
                "pattern_text": row['pattern_text'],
                "notes": row['notes'],
                "level": row['level'],
                "created_at": row['created_at']
            } for row in rows]
            
            logger.debug(f"Retrieved {len(patterns)} question patterns")
            return patterns
            
        except Exception as e:
            logger.error(f"Error retrieving question patterns from SQLite: {e}")
            raise Exception(f"Database error: {e}")

    def get_question_patterns_by_level(self, level: int = None) -> List[Dict[str, Any]]:
        """Retrieve question patterns filtered by level from the SQLite database."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            if level is not None:
                cursor.execute("""
                    SELECT id, type, pattern_text, notes, level, created_at
                    FROM question_patterns
                    WHERE level = ?
                    ORDER BY created_at DESC
                """, (level,))
            else:
                return self.get_question_patterns()
            
            rows = cursor.fetchall()
            cursor.close()
            conn.close()
            
            patterns = [{
                "id": row['id'],
                "type": row['type'],
                "pattern_text": row['pattern_text'],
                "notes": row['notes'],
                "level": row['level'],
                "created_at": row['created_at']
            } for row in rows]
            
            logger.debug(f"Retrieved {len(patterns)} question patterns for level {level}")
            return patterns
            
        except Exception as e:
            logger.error(f"Error retrieving question patterns by level from SQLite: {e}")
            raise Exception(f"Database error: {e}")

    def get_user_by_uid(self, uid: str) -> Dict[str, Any]:
        """Retrieve user registration data by UID."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.row_factory = sqlite3.Row
            
            cursor.execute("""
                SELECT uid, email, name, display_name, grade_level, registration_date, updated_at
                FROM users
                WHERE uid = ?
            """, (uid,))
            
            row = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if row:
                user = {
                    "uid": row['uid'],
                    "email": row['email'],
                    "name": row['name'],
                    "display_name": row['display_name'],
                    "grade_level": row['grade_level'],
                    "registration_date": row['registration_date'],
                    "updated_at": row['updated_at']
                }
                logger.debug(f"Retrieved user data for uid: {uid}")
                return user
            else:
                logger.debug(f"No user found for uid: {uid}")
                return {}
                
        except Exception as e:
            logger.error(f"Error retrieving user by uid from SQLite: {e}")
            raise Exception(f"Database error: {e}")

    def get_user_by_email(self, email: str) -> Dict[str, Any]:
        """Retrieve user registration data by email."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.row_factory = sqlite3.Row
            
            cursor.execute("""
                SELECT uid, email, name, display_name, grade_level, registration_date, updated_at
                FROM users
                WHERE email = ?
            """, (email,))
            
            row = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if row:
                user = {
                    "uid": row['uid'],
                    "email": row['email'],
                    "name": row['name'],
                    "display_name": row['display_name'],
                    "grade_level": row['grade_level'],
                    "registration_date": row['registration_date'],
                    "updated_at": row['updated_at']
                }
                logger.debug(f"Retrieved user data for email: {email}")
                return user
            else:
                logger.debug(f"No user found for email: {email}")
                return {}
                
        except Exception as e:
            logger.error(f"Error retrieving user by email from SQLite: {e}")
            raise Exception(f"Database error: {e}")