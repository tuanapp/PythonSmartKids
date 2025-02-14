from pydantic import BaseModel
from datetime import datetime

class MathAttempt(BaseModel):
    student_id: int
    datetime: datetime
    question: str
    is_answer_correct: bool
    incorrect_answer: str = None
    correct_answer: str
