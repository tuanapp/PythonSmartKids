from fastapi import APIRouter, HTTPException
from app.models.schemas import MathAttempt, GenerateQuestionsRequest
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

@router.get("/analyze_student/{uid}")
async def analyze_student(uid: str):
    data = db_service.get_attempts_by_uid(uid)
    analysis = ai_service.get_analysis(data)
    return analysis

@router.post("/generate-questions")
async def generate_questions(request: GenerateQuestionsRequest):
    """
    Generate a new set of practice questions based on the student's previous performance.
    """
    logger.debug(f"Received generate-questions request for uid: {request.uid}")
    try:
        # Get student's previous attempts
        attempts = db_service.get_attempts_by_uid(request.uid)
        logger.debug(f"Retrieved {len(attempts)} previous attempts")

        patterns = db_service.get_question_patterns()
        logger.debug(f"Retrieved {len(patterns)} patterns")        

        questions_response = generate_practice_questions(
            attempts, 
            patterns, 
            request.openai_base_url,
            request.openai_api_key,
            request.openai_model
        )
        logger.debug("Generated new questions successfully")        

        return questions_response
    except Exception as e:
        logger.error(f"Error generating questions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/question-patterns")
async def get_question_patterns():
    """API endpoint to retrieve all question patterns."""
    try:
        patterns = db_service.get_question_patterns()
        return [
            {
                "id": pattern["id"],
                "type": pattern["type"],
                "pattern_text": pattern["pattern_text"],
                "created_at": pattern["created_at"]
            }
            for pattern in patterns
        ]
    except Exception as e:
        logger.error(f"Error retrieving question patterns: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve question patterns")
