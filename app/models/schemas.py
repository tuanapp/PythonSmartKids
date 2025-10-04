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
    qorder: Optional[int] = None

class QuestionPattern(BaseModel):
    id: str
    type: str
    pattern_text: str
    created_at: datetime

class GenerateQuestionsRequest(BaseModel):
    uid: str
    level: Optional[int] = None  # Filter patterns by difficulty level
    ai_bridge_base_url: Optional[str] = None
    ai_bridge_api_key: Optional[str] = None
    ai_bridge_model: Optional[str] = None

class UserRegistration(BaseModel):
    uid: str  # Firebase User UID (28 character alphanumeric string, e.g., "FrhUjcQpTDVKK14K4y3thVcPgQd2")
    email: str
    name: str
    displayName: str
    gradeLevel: int  # Grade level (4, 5, 6, 7)
    registrationDate: str  # ISO format datetime string
