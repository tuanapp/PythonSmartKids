import sqlite3
from app.models.schemas import MathAttempt
from app.config import DATABASE_URL
import logging

logger = logging.getLogger(__name__)
DB_FILE = DATABASE_URL.replace("sqlite:///", "")

def init_db():
    conn = sqlite3.connect(DB_FILE)
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

def save_attempt(attempt: MathAttempt):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO attempts (student_id, datetime, question, is_answer_correct, incorrect_answer, correct_answer)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (attempt.student_id, attempt.datetime, attempt.question, attempt.is_answer_correct, attempt.incorrect_answer, attempt.correct_answer))
    conn.commit()
    conn.close()

def get_attempts(student_id: int):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT question, is_answer_correct, incorrect_answer, correct_answer, datetime 
        FROM attempts 
        WHERE student_id = ? 
        ORDER BY datetime DESC 
        LIMIT 50""", (student_id,))
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
    logger.debug(f"Sample attempt data: {attempts[0] if attempts else 'No attempts'}")
    
    return attempts

init_db()
