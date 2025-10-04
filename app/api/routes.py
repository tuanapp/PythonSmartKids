from fastapi import APIRouter, HTTPException
from app.models.schemas import MathAttempt, GenerateQuestionsRequest, UserRegistration
from app.services import ai_service
from app.services.ai_service import generate_practice_questions
from app.repositories import db_service
from app.db.vercel_migrations import migration_manager
from datetime import datetime, UTC
import logging
import os

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/users/register")
async def register_user(user: UserRegistration):
    """Register a new user in the backend database"""
    try:
        # Generate registration date on backend if not provided
        if not user.registrationDate:
            user.registrationDate = datetime.now(UTC).isoformat()
        
        # Save user registration to database
        result = db_service.save_user_registration(user)
        logger.debug(f"User registration saved for uid: {user.uid}")
        return {
            "message": "User registered successfully",
            "uid": user.uid,
            "email": user.email,
            "name": user.name,
            "registrationDate": user.registrationDate
        }
    except Exception as e:
        logger.error(f"Error registering user: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to register user: {str(e)}")

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
    Optionally filter patterns by difficulty level.
    """
    logger.debug(f"Received generate-questions request for uid: {request.uid}, level: {request.level}")
    try:
        # Get student's previous attempts
        attempts = db_service.get_attempts_by_uid(request.uid)
        logger.debug(f"Retrieved {len(attempts)} previous attempts")

        # Get patterns filtered by level if specified
        if request.level is not None:
            patterns = db_service.get_question_patterns_by_level(request.level)
            logger.debug(f"Retrieved {len(patterns)} patterns for level {request.level}")
        else:
            patterns = db_service.get_question_patterns()
            logger.debug(f"Retrieved {len(patterns)} patterns (all levels)")

        questions_response = generate_practice_questions(
            attempts, 
            patterns, 
            request.ai_bridge_base_url,
            request.ai_bridge_api_key,
            request.ai_bridge_model,
            request.level
        )
        logger.debug("Generated new questions successfully")        

        return questions_response
    except Exception as e:
        logger.error(f"Error generating questions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/question-patterns")
async def get_question_patterns(level: int = None):
    """API endpoint to retrieve question patterns, optionally filtered by level."""
    try:
        if level is not None:
            patterns = db_service.get_question_patterns_by_level(level)
            logger.debug(f"Retrieved patterns for level {level}")
        else:
            patterns = db_service.get_question_patterns()
            logger.debug("Retrieved all patterns")
            
        return [
            {
                "id": pattern["id"],
                "type": pattern["type"],
                "pattern_text": pattern["pattern_text"],
                "notes": pattern.get("notes"),
                "level": pattern.get("level"),
                "created_at": pattern["created_at"]
            }
            for pattern in patterns
        ]
    except Exception as e:
        logger.error(f"Error retrieving question patterns: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve question patterns")

# Migration endpoints for Vercel deployment
@router.get("/admin/migration-status")
async def get_migration_status(admin_key: str = ""):
    """Check the current migration status"""
    # Simple admin verification - in production, use proper authentication
    expected_key = os.getenv('ADMIN_KEY', 'dev-admin-key')
    if admin_key != expected_key:
        raise HTTPException(status_code=401, detail="Invalid admin key")
    
    try:
        status = migration_manager.check_migration_status()
        return status
    except Exception as e:
        logger.error(f"Error checking migration status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/admin/apply-migrations")
async def apply_migrations(admin_key: str = ""):
    """Apply all pending migrations"""
    # Simple admin verification - in production, use proper authentication
    expected_key = os.getenv('ADMIN_KEY', 'dev-admin-key')
    if admin_key != expected_key:
        raise HTTPException(status_code=401, detail="Invalid admin key")
    
    try:
        result = migration_manager.apply_all_migrations()
        if result['success']:
            return result
        else:
            raise HTTPException(status_code=500, detail=result.get('error', 'Migration failed'))
    except Exception as e:
        logger.error(f"Error applying migrations: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/admin/add-notes-column")
async def add_notes_column(admin_key: str = ""):
    """Specifically add the notes column to question_patterns table"""
    # Simple admin verification - in production, use proper authentication
    expected_key = os.getenv('ADMIN_KEY', 'dev-admin-key')
    if admin_key != expected_key:
        raise HTTPException(status_code=401, detail="Invalid admin key")
    
    try:
        result = migration_manager.add_notes_column_migration()
        if result['success']:
            return result
        else:
            raise HTTPException(status_code=500, detail=result.get('error', 'Migration failed'))
    except Exception as e:
        logger.error(f"Error adding notes column: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/admin/add-level-column")
async def add_level_column(admin_key: str = ""):
    """Specifically add the level column to question_patterns table"""
    # Simple admin verification - in production, use proper authentication
    expected_key = os.getenv('ADMIN_KEY', 'dev-admin-key')
    if admin_key != expected_key:
        raise HTTPException(status_code=401, detail="Invalid admin key")
    
    try:
        result = migration_manager.add_level_column_migration()
        if result['success']:
            return result
        else:
            raise HTTPException(status_code=500, detail=result.get('error', 'Migration failed'))
    except Exception as e:
        logger.error(f"Error adding level column: {e}")
        raise HTTPException(status_code=500, detail=str(e))