from fastapi import APIRouter, HTTPException
from app.models.schemas import MathAttempt, GenerateQuestionsRequest, UserRegistration
from app.services import ai_service
from app.services.ai_service import generate_practice_questions
from app.services.prompt_service import PromptService
from app.services.user_blocking_service import UserBlockingService
from app.repositories import db_service
from app.db.vercel_migrations import migration_manager
from app.db.models import get_session
from app.db.db_factory import DatabaseFactory
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
    """Get user information including subscription level and daily usage"""
    try:
        user_data = db_service.get_user_by_uid(uid)
        if not user_data:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get subscription level
        subscription = user_data.get("subscription", 0)
        
        # Initialize prompt service to get daily usage
        prompt_service = PromptService()
        daily_count = prompt_service.get_daily_question_generation_count(uid)
        
        # Determine daily limit based on subscription
        # Premium users (subscription >= 2) have unlimited access
        is_premium = subscription >= 2
        max_daily = None if is_premium else 2  # Free/trial users get 2 per day
        
        return {
            "uid": user_data["uid"],
            "email": user_data["email"],
            "name": user_data["name"],
            "displayName": user_data["display_name"],
            "gradeLevel": user_data["grade_level"],
            "subscription": subscription,
            "registrationDate": user_data["registration_date"],
            "daily_count": daily_count,
            "daily_limit": max_daily,
            "is_premium": is_premium
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

        # Generate questions with LLM tracking (uid and is_live are passed)
        questions_response = generate_practice_questions(
            uid=request.uid,  # Pass uid for LLM logging
            attempts=attempts, 
            patterns=patterns, 
            ai_bridge_base_url=request.ai_bridge_base_url,
            ai_bridge_api_key=request.ai_bridge_api_key,
            ai_bridge_model=request.ai_bridge_model,
            level=request.level,
            is_live=request.is_live  # Pass is_live to track production vs test calls
        )
        logger.debug("Generated new questions successfully")
        
        # The prompt is already recorded in the prompts table by ai_service
        # No need for separate question_generations table
        prompt_id = questions_response.get('prompt_id')
        
        # Query actual current count AFTER generation is saved (more accurate than pre-query + 1)
        actual_count = prompt_service.get_daily_question_generation_count(request.uid)
        
        # Add tracking info to response (actual count after this generation)
        questions_response['daily_count'] = actual_count
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

@router.get("/debug/daily-count/{uid}")
async def debug_daily_count(uid: str):
    """Debug endpoint to check daily question count and prompts table schema"""
    try:
        prompt_service = PromptService()
        
        # Get the database connection
        db = DatabaseFactory.get_provider()
        conn = db._get_connection()
        cursor = conn.cursor()
        
        # First, check what columns exist in the prompts table
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'prompts'
            ORDER BY ordinal_position
        """)
        columns = [{'name': row[0], 'type': row[1]} for row in cursor.fetchall()]
        column_names = [col['name'] for col in columns]
        
        # Check if question_generations table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'question_generations'
            )
        """)
        question_generations_exists = cursor.fetchone()[0]
        
        # Count total prompts for this UID
        cursor.execute("SELECT COUNT(*) FROM prompts WHERE uid = %s", (uid,))
        total_count = cursor.fetchone()[0]
        
        # Get recent prompts with only columns that exist
        select_fields = ['id', 'created_at']
        if 'status' in column_names:
            select_fields.append('status')
        if 'is_live' in column_names:
            select_fields.append('is_live')
        if 'request_type' in column_names:
            select_fields.append('request_type')
        if 'level' in column_names:
            select_fields.append('level')
        if 'source' in column_names:
            select_fields.append('source')
            
        query = f"""
            SELECT {', '.join(select_fields)}
            FROM prompts
            WHERE uid = %s
            ORDER BY created_at DESC
            LIMIT 10
        """
        cursor.execute(query, (uid,))
        
        recent_prompts = []
        for row in cursor.fetchall():
            prompt_data = {}
            for i, field in enumerate(select_fields):
                prompt_data[field] = str(row[i]) if row[i] is not None else None
            recent_prompts.append(prompt_data)
        
        # Try to get daily count using the service
        try:
            daily_count = prompt_service.get_daily_question_generation_count(uid)
        except Exception as e:
            daily_count = f"Error: {str(e)}"
        
        cursor.close()
        conn.close()
        
        return {
            'uid': uid,
            'migration_status': {
                'question_generations_table_exists': question_generations_exists,
                'prompts_columns': columns,
                'migration_008_applied': not question_generations_exists and 'request_type' in column_names
            },
            'counts': {
                'total_prompts': total_count,
                'daily_count': daily_count
            },
            'recent_prompts': recent_prompts
        }
    except Exception as e:
        logger.error(f"Error in debug endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/debug/subjects-schema")
async def debug_subjects_schema():
    """Debug endpoint to check subjects table schema and data"""
    try:
        db = DatabaseFactory.get_provider()
        conn = db._get_connection()
        cursor = conn.cursor()
        
        # Check subjects table columns
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'subjects'
            ORDER BY ordinal_position
        """)
        columns = [{'name': row[0], 'type': row[1]} for row in cursor.fetchall()]
        column_names = [col['name'] for col in columns]
        
        # Try to get subjects data with only existing columns
        if columns:
            cursor.execute(f"SELECT * FROM subjects LIMIT 5")
            rows = cursor.fetchall()
            sample_data = []
            for row in rows:
                sample_data.append(dict(zip(column_names, [str(v) if v is not None else None for v in row])))
        else:
            sample_data = []
        
        cursor.close()
        conn.close()
        
        return {
            'table_exists': len(columns) > 0,
            'columns': columns,
            'column_names': column_names,
            'sample_data': sample_data
        }
    except Exception as e:
        logger.error(f"Error in subjects debug endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Knowledge-Based Question Game Routes
# ============================================================================

@router.get("/subjects")
async def get_subjects(grade_level: int = None):
    """Get all available subjects, optionally filtered by grade level."""
    from app.repositories.knowledge_service import KnowledgeService
    
    try:
        subjects = KnowledgeService.get_all_subjects(grade_level)
        return {"subjects": subjects}
    except Exception as e:
        logger.error(f"Error fetching subjects: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch subjects")


@router.get("/subjects/{subject_id}")
async def get_subject(subject_id: int):
    """Get a single subject by ID."""
    from app.repositories.knowledge_service import KnowledgeService
    
    try:
        subject = KnowledgeService.get_subject_by_id(subject_id)
        if not subject:
            raise HTTPException(status_code=404, detail="Subject not found")
        return subject
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching subject {subject_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch subject")


@router.get("/subjects/{subject_id}/knowledge")
async def get_subject_knowledge(
    subject_id: int,
    grade_level: int = None,
    difficulty_level: int = None
):
    """Get knowledge documents for a subject."""
    from app.repositories.knowledge_service import KnowledgeService
    
    try:
        # First verify subject exists
        subject = KnowledgeService.get_subject_by_id(subject_id)
        if not subject:
            raise HTTPException(status_code=404, detail="Subject not found")
        
        documents = KnowledgeService.get_knowledge_documents(
            subject_id, grade_level, difficulty_level
        )
        return {"knowledge_documents": documents, "subject": subject}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching knowledge documents: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch knowledge documents")


@router.post("/generate-knowledge-questions")
async def generate_knowledge_questions(request: dict):
    """
    Generate questions based on knowledge documents.
    
    Request body:
    - uid: str (required) - Firebase User UID
    - subject_id: int (required) - Subject ID
    - count: int (optional, default=10) - Number of questions to generate (1-50)
    - level: int (optional) - Difficulty level filter (1-6)
    - is_live: int (optional, default=1) - 1=live, 0=test
    """
    from app.repositories.knowledge_service import KnowledgeService
    from app.services.ai_service import generate_knowledge_based_questions
    
    # Extract and validate parameters
    uid = request.get('uid')
    subject_id = request.get('subject_id')
    count = request.get('count', 10)
    level = request.get('level')
    is_live = request.get('is_live', 1)
    
    if not uid:
        raise HTTPException(status_code=400, detail="uid is required")
    if not subject_id:
        raise HTTPException(status_code=400, detail="subject_id is required")
    if count < 1 or count > 50:
        raise HTTPException(status_code=400, detail="count must be between 1 and 50")
    
    try:
        # Check user exists and get subscription info
        user_data = db_service.get_user_by_uid(uid)
        if not user_data:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Initialize prompt service for daily limit checking
        prompt_service = PromptService()
        daily_count = prompt_service.get_daily_question_generation_count(uid)
        subscription = user_data.get("subscription", 0)
        is_premium = subscription >= 2
        max_daily = None if is_premium else 2
        
        # Check daily limit for non-premium users
        if not is_premium and daily_count >= max_daily:
            raise HTTPException(
                status_code=429,
                detail={
                    "message": "Daily limit reached",
                    "current_count": daily_count,
                    "max_count": max_daily,
                    "is_premium": is_premium
                }
            )
        
        # Get subject info
        subject = KnowledgeService.get_subject_by_id(subject_id)
        if not subject:
            raise HTTPException(status_code=404, detail="Subject not found")
        
        # Get knowledge documents
        user_grade = user_data.get("grade_level")
        knowledge_docs = KnowledgeService.get_knowledge_documents(
            subject_id,
            user_grade,
            level
        )
        
        if not knowledge_docs:
            raise HTTPException(
                status_code=404,
                detail=f"No knowledge documents found for subject '{subject['display_name']}'"
            )
        
        # Combine knowledge content (use first document or combine multiple)
        knowledge_content = knowledge_docs[0]['content']
        if len(knowledge_docs) > 1:
            # Combine summaries or first portions of multiple documents
            summaries = [doc.get('summary') or doc['content'][:500] for doc in knowledge_docs[:3]]
            knowledge_content = "\n\n---\n\n".join(summaries)
        
        # Get user's attempt history for personalization
        user_history = KnowledgeService.get_user_knowledge_attempts(uid, subject_id, limit=20)
        
        # Generate questions using AI
        result = generate_knowledge_based_questions(
            uid=uid,
            subject_id=subject_id,
            subject_name=subject['display_name'],
            knowledge_content=knowledge_content,
            count=count,
            level=level,
            user_history=user_history,
            is_live=is_live
        )
        
        # Log usage
        KnowledgeService.log_knowledge_usage(
            uid,
            knowledge_docs[0]['id'] if knowledge_docs else None,
            subject_id,
            count
        )
        
        # Update daily count (increment in prompts table was already done in AI service)
        
        return {
            "message": "Questions generated successfully",
            "questions": result['questions'],
            "validation_result": {
                "ai_model": result['ai_model'],
                "generation_time_ms": result['generation_time_ms']
            },
            "daily_count": daily_count + 1,
            "daily_limit": max_daily,
            "is_premium": is_premium,
            "subject": subject
        }
        
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error generating knowledge questions: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error generating knowledge questions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate questions: {str(e)}")


@router.post("/evaluate-answers")
async def evaluate_answers(request: dict):
    """
    Evaluate user answers using AI.
    
    Request body:
    - uid: str (required) - Firebase User UID
    - subject_id: int (required) - Subject ID
    - evaluations: List[dict] (required) - List of {question, user_answer, correct_answer}
    - is_live: int (optional, default=1) - 1=live, 0=test
    """
    from app.repositories.knowledge_service import KnowledgeService
    from app.services.ai_service import evaluate_answers_with_ai
    
    # Extract and validate parameters
    uid = request.get('uid')
    subject_id = request.get('subject_id')
    evaluations = request.get('evaluations', [])
    is_live = request.get('is_live', 1)
    
    if not uid:
        raise HTTPException(status_code=400, detail="uid is required")
    if not subject_id:
        raise HTTPException(status_code=400, detail="subject_id is required")
    if not evaluations:
        raise HTTPException(status_code=400, detail="evaluations list is required")
    
    try:
        # Get subject info
        subject = KnowledgeService.get_subject_by_id(subject_id)
        if not subject:
            raise HTTPException(status_code=404, detail="Subject not found")
        
        # Prepare answers for evaluation
        answers = [
            {
                'question': e.get('question', ''),
                'user_answer': e.get('user_answer', ''),
                'correct_answer': e.get('correct_answer', '')
            }
            for e in evaluations
        ]
        
        # Evaluate answers using AI
        results = evaluate_answers_with_ai(
            answers=answers,
            subject_name=subject['display_name'],
            uid=uid,
            is_live=is_live
        )
        
        # Save attempts to database
        for i, result in enumerate(results):
            try:
                # Get additional info from original evaluation request
                original = evaluations[i] if i < len(evaluations) else {}
                
                KnowledgeService.save_knowledge_attempt(
                    uid=uid,
                    subject_id=subject_id,
                    question=result.get('question', ''),
                    user_answer=result.get('user_answer', ''),
                    correct_answer=result.get('correct_answer', ''),
                    evaluation_status=result.get('status', 'unknown'),
                    ai_feedback=result.get('ai_feedback'),
                    best_answer=result.get('best_answer'),
                    improvement_tips=result.get('improvement_tips'),
                    score=result.get('score'),
                    difficulty_level=original.get('difficulty'),
                    topic=original.get('topic')
                )
            except Exception as save_error:
                logger.warning(f"Failed to save attempt: {save_error}")
        
        # Calculate summary stats
        correct_count = sum(1 for r in results if r.get('status') == 'correct')
        partial_count = sum(1 for r in results if r.get('status') == 'partial')
        incorrect_count = sum(1 for r in results if r.get('status') == 'incorrect')
        total_score = sum(r.get('score', 0) for r in results) / len(results) if results else 0
        
        return {
            "message": "Answers evaluated successfully",
            "evaluations": results,
            "summary": {
                "total": len(results),
                "correct": correct_count,
                "partial": partial_count,
                "incorrect": incorrect_count,
                "average_score": round(total_score, 2)
            },
            "subject": subject
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error evaluating answers: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to evaluate answers: {str(e)}")


@router.post("/admin/knowledge-documents")
async def create_knowledge_document(request: dict, admin_key: str = ""):
    """
    Create a new knowledge document (admin only).
    
    Request body:
    - subject_id: int (required)
    - title: str (required)
    - content: str (required)
    - summary: str (optional)
    - metadata: dict (optional)
    - grade_level: int (optional, 4-7)
    - difficulty_level: int (optional, 1-6)
    """
    from app.repositories.knowledge_service import KnowledgeService
    
    # Verify admin access
    expected_key = os.getenv('ADMIN_KEY', 'dev-admin-key')
    if admin_key != expected_key:
        raise HTTPException(status_code=401, detail="Invalid admin key")
    
    # Extract parameters
    subject_id = request.get('subject_id')
    title = request.get('title')
    content = request.get('content')
    
    if not subject_id:
        raise HTTPException(status_code=400, detail="subject_id is required")
    if not title:
        raise HTTPException(status_code=400, detail="title is required")
    if not content:
        raise HTTPException(status_code=400, detail="content is required")
    
    try:
        doc_id = KnowledgeService.create_knowledge_document(
            subject_id=subject_id,
            title=title,
            content=content,
            summary=request.get('summary'),
            metadata=request.get('metadata'),
            grade_level=request.get('grade_level'),
            difficulty_level=request.get('difficulty_level'),
            created_by=request.get('created_by', 'admin')
        )
        
        return {
            "message": "Knowledge document created successfully",
            "id": doc_id
        }
        
    except Exception as e:
        logger.error(f"Error creating knowledge document: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create knowledge document: {str(e)}")


