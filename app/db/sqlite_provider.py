import sqlite3
import logging
from typing import List, Dict, Any
from app.models.schemas import MathAttempt
from app.db.db_interface import DatabaseProvider

logger = logging.getLogger(__name__)

class SQLiteProvider(DatabaseProvider):
    """SQLite implementation of the database provider."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        
    def init_db(self) -> None:
        """Initialize the SQLite database and create the attempts table if it doesn't exist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER,
                datetime TEXT,
                question TEXT,
                is_answer_correct BOOLEAN,
                incorrect_answer TEXT,
                correct_answer TEXT
            )
        ''')
        conn.commit()
        conn.close()
        logger.info(f"SQLite database initialized at {self.db_path}")
        
    def save_attempt(self, attempt: MathAttempt) -> None:
        """Save a math attempt to the SQLite database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO attempts (student_id, datetime, question, is_answer_correct, incorrect_answer, correct_answer)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                attempt.student_id, 
                attempt.datetime.isoformat() if hasattr(attempt.datetime, 'isoformat') else attempt.datetime, 
                attempt.question, 
                attempt.is_answer_correct, 
                attempt.incorrect_answer, 
                attempt.correct_answer
            ))
            conn.commit()
            conn.close()
            logger.debug(f"Attempt saved for student {attempt.student_id}")
        except sqlite3.Error as e:
            logger.error(f"Error saving attempt to SQLite: {e}")
            raise Exception(f"Database error: {e}")
    
    def get_attempts(self, student_id: int) -> List[Dict[str, Any]]:
        """Retrieve attempts for a specific student from the SQLite database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT question, is_answer_correct, incorrect_answer, correct_answer, datetime 
                FROM attempts 
                WHERE student_id = ? 
                ORDER BY datetime DESC 
                LIMIT 50
            """, (student_id,))
            data = cursor.fetchall()
            conn.close()
            
            attempts = [{
                "question": row[0],
                "is_correct": bool(row[1]),  # Ensure boolean conversion
                "incorrect_answer": row[2] if row[2] is not None else "",  # Handle NULL values
                "correct_answer": str(row[3]) if row[3] is not None else "",  # Ensure string conversion
                "datetime": row[4]
            } for row in data]
            
            logger.debug(f"Retrieved {len(attempts)} attempts for student {student_id}")
            return attempts
        except sqlite3.Error as e:
            logger.error(f"Error retrieving attempts from SQLite: {e}")
            raise Exception(f"Database error: {e}")