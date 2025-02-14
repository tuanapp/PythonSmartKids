import sqlite3
from app.models.schemas import MathAttempt
from app.config import DATABASE_URL

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
    cursor.execute("SELECT question, is_answer_correct FROM attempts WHERE student_id = ?", (student_id,))
    data = cursor.fetchall()
    conn.close()
    return [{"question": row[0], "is_correct": row[1]} for row in data]

init_db()
