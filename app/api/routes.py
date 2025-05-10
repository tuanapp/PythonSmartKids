from fastapi import APIRouter, HTTPException
from app.models.schemas import MathAttempt
from app.services import ai_service
from app.services.ai_service import generate_practice_questions
from app.repositories import db_service
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/submit_attempt")
async def submit_attempt(attempt: MathAttempt):
    db_service.save_attempt(attempt)
    return {"message": attempt.question + " Attempt saved successfully - xx " +  datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

@router.get("/analyze_student/{student_id}")
async def analyze_student(student_id: int):
    data = db_service.get_attempts(student_id)
    analysis = ai_service.get_analysis(data)
    return analysis

@router.post("/generate-questions/{student_id}")
async def generate_questions(student_id: int):
    """
    Generate a new set of practice questions based on the student's previous performance.
    """
    logger.debug(f"Received generate-questions request for student_id: {student_id}")
    try:
        # Get student's previous attempts
        attempts = db_service.get_attempts(student_id)
        logger.debug(f"Retrieved {len(attempts)} previous attempts")
        questions = generate_practice_questions(attempts)
        logger.debug("Generated new questions successfully")
        return questions
    except Exception as e:
        logger.error(f"Error generating questions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
