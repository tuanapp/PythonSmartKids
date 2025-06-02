from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class MathAttempt(BaseModel):
    student_id: int
    uid: str #from Firbase Users table (User UID)
    datetime: datetime
    question: str
    is_answer_correct: bool
    incorrect_answer: Optional[str] = None
    correct_answer: str

class QuestionPattern(BaseModel):
    id: str
    type: str
    pattern_text: str
    created_at: datetime
