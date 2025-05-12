import logging
from typing import List, Dict, Any
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime

from app.models.schemas import MathAttempt
from app.db.db_interface import DatabaseProvider
from app.db.models import QuestionPattern

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
        Initialize the Neon database by creating the attempts table if it doesn't exist.
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
                    datetime TIMESTAMP NOT NULL,
                    question TEXT NOT NULL,
                    is_answer_correct BOOLEAN NOT NULL,
                    incorrect_answer TEXT,
                    correct_answer TEXT NOT NULL
                )
            """)
            
            conn.commit()
            logger.info("Successfully initialized Neon database")
            cursor.close()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to initialize Neon database: {e}")
            raise Exception(f"Database initialization error: {e}")
    
    def save_attempt(self, attempt: MathAttempt) -> None:
        """Save a math attempt to the Neon database."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Insert the attempt
            cursor.execute("""
                INSERT INTO attempts 
                (student_id, datetime, question, is_answer_correct, incorrect_answer, correct_answer)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                attempt.student_id,
                attempt.datetime,
                attempt.question,
                attempt.is_answer_correct,
                attempt.incorrect_answer or "",
                attempt.correct_answer
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
                SELECT question, is_answer_correct, incorrect_answer, correct_answer, datetime
                FROM attempts
                WHERE student_id = %s
                ORDER BY datetime DESC
                LIMIT 50
            """, (student_id,))
            
            data = cursor.fetchall()
            cursor.close()
            conn.close()
            
            # Format the data to match the expected schema
            attempts = [{
                "question": item['question'],
                "is_correct": bool(item['is_answer_correct']),
                "incorrect_answer": item['incorrect_answer'] if item['incorrect_answer'] else "",
                "correct_answer": str(item['correct_answer']) if item['correct_answer'] else "",
                "datetime": item['datetime'].isoformat() if isinstance(item['datetime'], datetime) else item['datetime']
            } for item in data]
            
            logger.debug(f"Retrieved {len(attempts)} attempts for student {student_id}")
            return attempts
            
        except Exception as e:
            logger.error(f"Error retrieving attempts from Neon: {e}")
            raise Exception(f"Database error: {e}")

    def get_question_patterns(self):
        """Retrieve all question patterns from the database."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # Query to fetch all question patterns
            cursor.execute("""
                SELECT id, type, pattern_text, created_at
                FROM question_patterns
            """)

            patterns = cursor.fetchall()
            cursor.close()
            conn.close()

            return patterns
        except Exception as e:
            logger.error(f"Error retrieving question patterns: {e}")
            raise Exception(f"Database error: {e}")