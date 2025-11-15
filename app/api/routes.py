from fastapi import APIRouter, HTTPException
from app.models.schemas import MathAttempt, GenerateQuestionsRequest, UserRegistration
from app.services import ai_service
from app.services.ai_service import generate_practice_questions
from app.services.prompt_service import PromptService
from app.services.user_blocking_service import UserBlockingService
from app.repositories import db_service
from app.db.vercel_migrations import migration_manager
from app.db.models import get_session
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

@router.get("/users/{uid}")
async def get_user(uid: str):
    """Get user information including subscription level"""
    try:
        user_data = db_service.get_user_by_uid(uid)
        if not user_data:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {
            "uid": user_data["uid"],
            "email": user_data["email"],
            "name": user_data["name"],
            "displayName": user_data["display_name"],
            "gradeLevel": user_data["grade_level"],
            "subscription": user_data.get("subscription", 0),  # Default to 0 if not set
            "registrationDate": user_data["registration_date"]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving user: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve user: {str(e)}")

@router.post("/users/{user_uid}/block")
async def block_user(
    user_uid: str,
    reason: str,
    blocked_by: str,
    notes: str = None,
    admin_key: str = ""
):
    """
    Block a user with specified reason.
    Requires admin authentication.
    """
    # Verify admin access
    expected_key = os.getenv('ADMIN_KEY', 'dev-admin-key')
    if admin_key != expected_key:
        raise HTTPException(status_code=401, detail="Invalid admin key")
    
    try:
        db = get_session()
        user = UserBlockingService.block_user(
            db=db,
            user_uid=user_uid,
            reason=reason,
            blocked_by=blocked_by,
            notes=notes
        )
        db.close()
        
        logger.info(f"User {user_uid} blocked by {blocked_by}. Reason: {reason}")
        
        return {
            "success": True,
            "message": "User blocked successfully",
            "user_uid": user.uid,
            "blocked_at": user.blocked_at.isoformat() if user.blocked_at else None
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error blocking user {user_uid}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to block user: {str(e)}")

@router.post("/users/{user_uid}/unblock")
async def unblock_user(
    user_uid: str,
    unblocked_by: str,
    notes: str = None,
    admin_key: str = ""
):
    """
    Unblock a user.
    Requires admin authentication.
    """
    # Verify admin access
    expected_key = os.getenv('ADMIN_KEY', 'dev-admin-key')
    if admin_key != expected_key:
        raise HTTPException(status_code=401, detail="Invalid admin key")
    
    try:
        db = get_session()
        user = UserBlockingService.unblock_user(
            db=db,
            user_uid=user_uid,
            unblocked_by=unblocked_by,
            notes=notes
        )
        db.close()
        
        logger.info(f"User {user_uid} unblocked by {unblocked_by}")
        
        return {
            "success": True,
            "message": "User unblocked successfully",
            "user_uid": user.uid
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error unblocking user {user_uid}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to unblock user: {str(e)}")

@router.get("/users/{user_uid}/status")
async def check_user_status(user_uid: str):
    """
    Check if user is blocked and return blocking status.
    This endpoint is public (no admin key required) for client-side checks.
    """
    try:
        db = get_session()
        is_blocked, reason = UserBlockingService.is_user_blocked(db, user_uid)
        db.close()
        
        return {
            "user_uid": user_uid,
            "is_blocked": is_blocked,
            "blocked_reason": reason
        }
    except Exception as e:
        logger.error(f"Error checking user status for {user_uid}: {e}")
        # Fail open - allow access if check fails
        return {
            "user_uid": user_uid,
            "is_blocked": False,
            "blocked_reason": ""
        }

@router.get("/users/{user_uid}/blocking-history")
async def get_blocking_history(
    user_uid: str,
    limit: int = 10,
    admin_key: str = ""
):
    """
    Get blocking history for a user.
    Requires admin authentication.
    """
    # Verify admin access
    expected_key = os.getenv('ADMIN_KEY', 'dev-admin-key')
    if admin_key != expected_key:
        raise HTTPException(status_code=401, detail="Invalid admin key")
    
    try:
        db = get_session()
        history = UserBlockingService.get_blocking_history(db, user_uid, limit)
        db.close()
        
        return [
            {
                "id": record.id,
                "user_uid": record.user_uid,
                "action": record.action,
                "reason": record.reason,
                "blocked_at": record.blocked_at.isoformat() if record.blocked_at else None,
                "blocked_by": record.blocked_by,
                "unblocked_at": record.unblocked_at.isoformat() if record.unblocked_at else None,
                "notes": record.notes
            }
            for record in history
        ]
    except Exception as e:
        logger.error(f"Error fetching blocking history for {user_uid}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch blocking history: {str(e)}")

@router.get("/admin/blocked-users")
async def get_blocked_users(
    limit: int = 100,
    admin_key: str = ""
):
    """
    Get all currently blocked users.
    Requires admin authentication.
    """
    # Verify admin access
    expected_key = os.getenv('ADMIN_KEY', 'dev-admin-key')
    if admin_key != expected_key:
        raise HTTPException(status_code=401, detail="Invalid admin key")
    
    try:
        db = get_session()
        blocked_users = UserBlockingService.get_all_blocked_users(db, limit)
        db.close()
        
        return [
            {
                "uid": user.uid,
                "email": user.email,
                "name": user.name,
                "is_blocked": user.is_blocked,
                "blocked_reason": user.blocked_reason,
                "blocked_at": user.blocked_at.isoformat() if user.blocked_at else None,
                "blocked_by": user.blocked_by
            }
            for user in blocked_users
        ]
    except Exception as e:
        logger.error(f"Error fetching blocked users: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch blocked users: {str(e)}")

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
    Enforces subscription-based daily limits: free/trial users = 2/day, premium = unlimited.
    Tracks all question generations in the prompts table.
    Optionally filter patterns by difficulty level.
    """
    logger.debug(f"Received generate-questions request for uid: {request.uid}, level: {request.level}, is_live: {request.is_live}")
    
    # Initialize prompt service for daily limit checking
    prompt_service = PromptService()
    
    try:
        # Get user data to check subscription level
        user_data = db_service.get_user_by_uid(request.uid)
        
        # Default to free subscription (0) if user not found (should not happen with auth middleware)
        subscription = user_data.get("subscription", 0) if user_data else 0
        
        logger.info(f"User {request.uid} subscription level: {subscription}")
        
        # Check if user can generate questions based on subscription and daily limit
        limit_check = prompt_service.can_generate_questions(
            uid=request.uid,
            subscription=subscription,
            max_daily_questions=2  # Free and trial users limited to 2/day
        )
        
        if not limit_check['can_generate']:
            logger.warning(f"User {request.uid} exceeded daily limit: {limit_check['reason']}")
            raise HTTPException(
                status_code=403,  # Forbidden
                detail={
                    'error': 'daily_limit_exceeded',
                    'message': limit_check['reason'],
                    'current_count': limit_check['current_count'],
                    'max_count': limit_check['max_count'],
                    'is_premium': limit_check['is_premium']
                }
            )
        
        logger.info(f"Limit check passed: {limit_check['reason']}")
        
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

        # Generate questions with LLM tracking (uid is now passed)
        questions_response = generate_practice_questions(
            uid=request.uid,  # Pass uid for LLM logging
            attempts=attempts, 
            patterns=patterns, 
            ai_bridge_base_url=request.ai_bridge_base_url,
            ai_bridge_api_key=request.ai_bridge_api_key,
            ai_bridge_model=request.ai_bridge_model,
            level=request.level
        )
        logger.debug("Generated new questions successfully")
        
        # The prompt is already recorded in the prompts table by ai_service
        # No need for separate question_generations table
        prompt_id = questions_response.get('prompt_id')
        
        # Add tracking info to response (updated count after this generation)
        questions_response['daily_count'] = limit_check['current_count'] + 1  # After this generation
        questions_response['daily_limit'] = limit_check['max_count']
        questions_response['is_premium'] = limit_check['is_premium']
        
        # Save the prompt and response to database (legacy prompts table) - SKIP, already done
        try:
            prompt_request = questions_response.get('ai_request', '')
            prompt_response = questions_response.get('ai_response', '')
            
            logger.debug(f"Prompt storage check - ai_request exists: {bool(prompt_request)}, ai_response exists: {bool(prompt_response)}")
            logger.debug(f"Response keys: {list(questions_response.keys())}")
            
            if prompt_request and prompt_response:
                # Skip saving - already saved by PromptService in ai_service
                logger.debug("Prompt already saved by PromptService, skipping legacy save")
                # db_service.save_prompt(
                #     uid=request.uid,
                #     request_text=prompt_request,
                #     response_text=prompt_response,
                #     is_live=request.is_live
                # )
                logger.debug(f"Saved prompt to database for uid: {request.uid}, is_live: {request.is_live}")
            else:
                logger.warning(f"Could not save prompt: missing request or response text (request={len(prompt_request) if prompt_request else 0} chars, response={len(prompt_response) if prompt_response else 0} chars)")
        except Exception as prompt_error:
            # Don't fail the entire request if prompt saving fails
            logger.error(f"Error saving prompt to database: {prompt_error}")

        return questions_response
    except HTTPException:
        # Re-raise HTTP exceptions (like 403 for limit exceeded)
        raise
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

