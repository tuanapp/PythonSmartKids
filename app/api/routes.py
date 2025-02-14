from fastapi import APIRouter
from app.models.schemas import MathAttempt
from app.services import ai_service
from app.repositories import db_service

router = APIRouter()

@router.post("/submit_attempt")
async def submit_attempt(attempt: MathAttempt):
    db_service.save_attempt(attempt)
    return {"message": "Attempt saved successfully"}

@router.get("/analyze_student/{student_id}")
async def analyze_student(student_id: int):
    data = db_service.get_attempts(student_id)
    analysis = ai_service.get_analysis(data)
    return analysis
