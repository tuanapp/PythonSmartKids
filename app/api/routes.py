from fastapi import APIRouter, HTTPException, Header
from app.models.schemas import MathAttempt, GenerateQuestionsRequest, UserRegistration, UserProfileUpdate, AdjustCreditsRequest, PerformanceReportQueryRequest
from app.services import ai_service
from app.services.ai_service import generate_practice_questions
from app.services.prompt_service import PromptService
from app.services.user_blocking_service import UserBlockingService
from app.services.performance_report_service import performance_report_service
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
    """Get user information including subscription level, credits, and daily usage"""
    try:
        user_data = db_service.get_user_by_uid(uid)
        if not user_data:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get subscription level and credits
        subscription = user_data.get("subscription", 0)
        credits = user_data.get("credits", 0)
        
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
            "credits": credits,
            "registrationDate": user_data["registration_date"],
            "daily_count": daily_count,
            "daily_limit": max_daily,
            "is_premium": is_premium,
            "is_blocked": user_data.get("is_blocked", False),
            "blocked_reason": user_data.get("blocked_reason"),
            "is_debug": user_data.get("is_debug", False)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving user: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve user: {str(e)}")

@router.patch("/users/{uid}/profile")
async def update_user_profile(uid: str, update: UserProfileUpdate):
    """Update user profile (name, displayName, gradeLevel)"""
    try:
        # Verify user exists
        user_data = db_service.get_user_by_uid(uid)
        if not user_data:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Check if any field is provided
        if update.name is None and update.displayName is None and update.gradeLevel is None:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        # Update profile
        db_service.update_user_profile(
            uid,
            name=update.name,
            display_name=update.displayName,
            grade_level=update.gradeLevel
        )
        
        updated_fields = []
        if update.name is not None:
            updated_fields.append(f"name={update.name}")
        if update.displayName is not None:
            updated_fields.append(f"displayName={update.displayName}")
        if update.gradeLevel is not None:
            updated_fields.append(f"gradeLevel={update.gradeLevel}")
        
        logger.info(f"Updated profile for user {uid}: {', '.join(updated_fields)}")
        
        return {
            "success": True,
            "uid": uid,
            "name": update.name,
            "displayName": update.displayName,
            "gradeLevel": update.gradeLevel,
            "message": "Profile updated successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user profile: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update profile: {str(e)}")

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


@router.post("/admin/users/{user_uid}/credits")
async def adjust_user_credits(
    user_uid: str,
    request: AdjustCreditsRequest,
    admin_key: str = ""
):
    """
    Adjust user credits by a given amount.
    Positive amount adds credits, negative amount removes credits.
    Requires admin authentication.
    
    Args:
        user_uid: Firebase User UID
        request.amount: Credits to add (positive) or remove (negative)
        request.reason: Optional reason for the adjustment
        admin_key: Admin authentication key
    """
    # Verify admin access
    expected_key = os.getenv('ADMIN_KEY', 'dev-admin-key')
    if admin_key != expected_key:
        raise HTTPException(status_code=401, detail="Invalid admin key")
    
    try:
        # Check if user exists
        user_data = db_service.get_user_by_uid(user_uid)
        if not user_data:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Adjust credits
        result = db_service.adjust_user_credits(
            uid=user_uid,
            amount=request.amount,
            reason=request.reason
        )
        
        logger.info(f"Admin adjusted credits for {user_uid}: {result['old_credits']} -> {result['new_credits']} (reason: {request.reason})")
        
        return {
            "success": True,
            "uid": result["uid"],
            "old_credits": result["old_credits"],
            "new_credits": result["new_credits"],
            "adjustment": result["adjustment"],
            "reason": result["reason"],
            "message": f"Credits adjusted from {result['old_credits']} to {result['new_credits']}"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adjusting credits for {user_uid}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to adjust credits: {str(e)}")


@router.get("/users/{user_uid}/credit-usage")
async def get_user_credit_usage(
    user_uid: str,
    date: str = None,
    game_type: str = None
):
    """
    Get credit usage for a user.
    
    Args:
        user_uid: Firebase User UID
        date: Optional date filter (YYYY-MM-DD format, defaults to today)
        game_type: Optional game type filter ('math', 'knowledge', 'dictation', etc.)
    
    Returns:
        Credit usage summary and detailed records
    """
    try:
        # Check if user exists
        user_data = db_service.get_user_by_uid(user_uid)
        if not user_data:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get detailed usage records
        usage_records = db_service.get_user_credit_usage(
            uid=user_uid,
            usage_date=date,
            game_type=game_type
        )
        
        # Get summary
        summary = db_service.get_user_daily_credit_summary(
            uid=user_uid,
            usage_date=date
        )
        
        return {
            "success": True,
            "uid": user_uid,
            "user_name": user_data.get("display_name"),
            "credits_remaining": user_data.get("credits", 0),
            "summary": summary,
            "records": usage_records
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting credit usage for {user_uid}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get credit usage: {str(e)}")


# ============================================================================
# LLM Models Endpoints
# ============================================================================

@router.get("/llm-models")
async def get_llm_models(provider: str = None):
    """
    Get all active LLM models.
    
    Args:
        provider: Optional provider filter ('google', 'groq', 'anthropic', etc.)
    
    Returns:
        List of active models ordered by order_number
    """
    try:
        from app.services.llm_service import llm_service
        models = llm_service.get_active_models(provider=provider)
        return {
            "success": True,
            "models": models,
            "count": len(models)
        }
    except Exception as e:
        logger.error(f"Error getting LLM models: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get LLM models: {str(e)}")


@router.get("/admin/llm-models")
async def get_all_llm_models(admin_key: str = "", include_inactive: bool = True):
    """
    Get all LLM models including inactive/deprecated ones (admin endpoint).
    
    Args:
        admin_key: Admin authentication key
        include_inactive: Whether to include inactive models (default True)
    
    Returns:
        List of all models
    """
    expected_key = os.getenv('ADMIN_KEY', 'dev-admin-key')
    if admin_key != expected_key:
        raise HTTPException(status_code=401, detail="Invalid admin key")
    
    try:
        from app.services.llm_service import llm_service
        models = llm_service.get_all_models(include_inactive=include_inactive)
        return {
            "success": True,
            "models": models,
            "count": len(models)
        }
    except Exception as e:
        logger.error(f"Error getting all LLM models: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get LLM models: {str(e)}")


@router.post("/admin/llm-models/sync")
async def sync_llm_models(
    admin_key: str = "",
    provider: str = "google",
    api_key: str = None
):
    """
    Sync LLM models from a provider's API.
    
    Logic:
    - Fetch current models from provider API
    - Skip models with manual=true
    - Update/insert models with manual=false
    - Mark missing models as deprecated and inactive
    
    Args:
        admin_key: Admin authentication key
        provider: Provider to sync from ('google', 'groq', 'anthropic', 'openai')
        api_key: Optional API key (uses env var if not provided)
    
    Returns:
        Sync result with counts of added/updated/deprecated models
    """
    expected_key = os.getenv('ADMIN_KEY', 'dev-admin-key')
    if admin_key != expected_key:
        raise HTTPException(status_code=401, detail="Invalid admin key")
    
    try:
        from app.services.llm_service import llm_service, SUPPORTED_PROVIDERS
        
        if provider not in SUPPORTED_PROVIDERS:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported provider: {provider}. Supported: {list(SUPPORTED_PROVIDERS.keys())}"
            )
        
        result = llm_service.sync_models_from_provider(provider, api_key)
        
        logger.info(f"LLM models sync result for {provider}: {result['message']}")
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error syncing LLM models from {provider}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to sync LLM models: {str(e)}")


@router.patch("/admin/llm-models/{model_name:path}")
async def update_llm_model(
    model_name: str,
    admin_key: str = "",
    order_number: int = None,
    active: bool = None,
    manual: bool = None,
    display_name: str = None
):
    """
    Update an LLM model's properties.
    
    Args:
        model_name: The model_name to update (URL-encoded, e.g., 'models%2Fgemini-2.0-flash')
        admin_key: Admin authentication key
        order_number: New display order
        active: Whether the model is active
        manual: Whether the model is manually managed (won't be auto-updated)
        display_name: Human-readable name
    
    Returns:
        Updated model
    """
    expected_key = os.getenv('ADMIN_KEY', 'dev-admin-key')
    if admin_key != expected_key:
        raise HTTPException(status_code=401, detail="Invalid admin key")
    
    try:
        from app.services.llm_service import llm_service
        
        updates = {}
        if order_number is not None:
            updates['order_number'] = order_number
        if active is not None:
            updates['active'] = active
        if manual is not None:
            updates['manual'] = manual
        if display_name is not None:
            updates['display_name'] = display_name
        
        if not updates:
            raise HTTPException(status_code=400, detail="No valid update fields provided")
        
        result = llm_service.update_model(model_name, updates)
        
        if result['success']:
            logger.info(f"Updated LLM model '{model_name}': {updates}")
            return result
        else:
            raise HTTPException(status_code=404, detail=result.get('error', 'Model not found'))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating LLM model '{model_name}': {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update LLM model: {str(e)}")


@router.post("/submit_attempt")
async def submit_attempt(attempt: MathAttempt):
    db_service.save_attempt(attempt)
    # Invalidate performance report cache when new attempts are added
    performance_report_service.invalidate_cache()
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
    Enforces credit-based and subscription-based limits:
    - Credits: Overall cap on total AI generations
    - Daily limits: Free/trial users = 2/day, premium = unlimited
    Tracks all question generations in the prompts table.
    Optionally filter patterns by difficulty level.
    """
    logger.debug(f"Received generate-questions request for uid: {request.uid}, level: {request.level}, is_live: {request.is_live}")
    
    # Initialize prompt service for daily limit checking
    prompt_service = PromptService()
    
    try:
        # Get user data to check subscription level and credits
        user_data = db_service.get_user_by_uid(request.uid)
        
        # Default values if user not found (should not happen with auth middleware)
        subscription = user_data.get("subscription", 0) if user_data else 0
        credits = user_data.get("credits", 0) if user_data else 0
        
        logger.info(f"User {request.uid} subscription level: {subscription}, credits: {credits}")
        
        # Check if user can generate questions based on credits, subscription and daily limit
        limit_check = prompt_service.can_generate_questions(
            uid=request.uid,
            subscription=subscription,
            credits=credits,
            max_daily_questions=2  # Free and trial users limited to 2/day
        )
        
        if not limit_check['can_generate']:
            # Determine error type based on reason
            error_type = 'no_credits' if 'credit' in limit_check['reason'].lower() else 'daily_limit_exceeded'
            logger.warning(f"User {request.uid} cannot generate: {limit_check['reason']}")
            raise HTTPException(
                status_code=403,  # Forbidden
                detail={
                    'error': error_type,
                    'message': limit_check['reason'],
                    'current_count': limit_check['current_count'],
                    'max_count': limit_check['max_count'],
                    'is_premium': limit_check['is_premium'],
                    'credits_remaining': limit_check['credits_remaining']
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
        
        # Decrement user credits after successful generation
        new_credits = db_service.decrement_user_credits(request.uid)
        logger.info(f"Decremented credits for user {request.uid}, new balance: {new_credits}")
        
        # Record credit usage for analytics (with model tracking)
        try:
            subject = f"level_{request.level}" if request.level else "general"
            # Get model name from ai_summary for FK tracking
            ai_summary = questions_response.get('ai_summary', {})
            model_name = ai_summary.get('ai_model') if ai_summary else None
            db_service.record_credit_usage(
                uid=request.uid,
                game_type="math",
                subject=subject,
                credits_used=1,
                model_name=model_name
            )
        except Exception as usage_error:
            logger.warning(f"Failed to record credit usage (non-critical): {usage_error}")
        
        # Query actual current count AFTER generation is saved (more accurate than pre-query + 1)
        actual_count = prompt_service.get_daily_question_generation_count(request.uid)
        
        # Add tracking info to response (actual count after this generation)
        questions_response['daily_count'] = actual_count
        questions_response['daily_limit'] = limit_check['max_count']
        questions_response['is_premium'] = limit_check['is_premium']
        questions_response['credits_remaining'] = new_credits
        
        # Save the prompt and response to database (legacy prompts table) - SKIP, already done
        try:
            ai_summary = questions_response.get('ai_summary', {})
            prompt_request = ai_summary.get('ai_request', '') if ai_summary else ''
            prompt_response = ai_summary.get('ai_response', '') if ai_summary else ''
            
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
    import traceback
    
    try:
        subjects = KnowledgeService.get_all_subjects(grade_level)
        return {"subjects": subjects}
    except Exception as e:
        error_details = {
            "error": str(e),
            "type": type(e).__name__,
            "traceback": traceback.format_exc()
        }
        logger.error(f"Error fetching subjects: {error_details}")
        raise HTTPException(status_code=500, detail=error_details)


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


@router.get("/subjects/{subject_id}/visual-limits")
async def get_subject_visual_limits(subject_id: int):
    """
    Get visual aid limits for a specific subject.
    
    Returns subject-level visual configuration for help feature:
    - visual_json_max: Max JSON-based visual aids allowed
    - visual_svg_max: Max AI-generated SVG aids allowed
    
    These limits work together with global feature flags:
    - Global flags (FF_HELP_VISUAL_*) override subject settings
    - Subject limits can be MORE restrictive than global
    - Final limit = min(global, subject) for each type
    """
    from app.repositories.knowledge_service import KnowledgeService
    
    try:
        subject = KnowledgeService.get_subject_by_id(subject_id)
        if not subject:
            raise HTTPException(status_code=404, detail="Subject not found")
        
        # Extract visual limits (default to 0 if not set)
        visual_json_max = subject.get('visual_json_max', 0)
        visual_svg_max = subject.get('visual_svg_max', 0)
        
        return {
            "subject_id": subject_id,
            "subject_name": subject['display_name'],
            "visual_json_max": visual_json_max,
            "visual_svg_max": visual_svg_max
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching visual limits for subject {subject_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch visual limits")


@router.get("/app/features/help")
async def get_help_feature_flags():
    """
    Get global feature flags for help system.
    
    Returns:
    - visual_json_enabled: Whether JSON-based visual aids are enabled globally
    - visual_json_max: Global max JSON visual aids per help request
    - visual_svg_enabled: Whether AI-generated SVG aids are enabled globally
    - visual_svg_max: Global max SVG visual aids per help request
    
    Frontend should cache these flags and combine with subject-level limits.
    """
    from app.config import (
        FF_HELP_VISUAL_JSON_ENABLED,
        FF_HELP_VISUAL_JSON_MAX,
        FF_HELP_VISUAL_SVG_FROM_AI_ENABLED,
        FF_HELP_VISUAL_SVG_FROM_AI_MAX
    )
    
    return {
        "visual_json_enabled": FF_HELP_VISUAL_JSON_ENABLED,
        "visual_json_max": FF_HELP_VISUAL_JSON_MAX,
        "visual_svg_enabled": FF_HELP_VISUAL_SVG_FROM_AI_ENABLED,
        "visual_svg_max": FF_HELP_VISUAL_SVG_FROM_AI_MAX
    }


@router.get("/subjects/{subject_id}/knowledge")
async def get_subject_knowledge(
    subject_id: int,
    grade_level: int = None,
    level: int = None
):
    """Get knowledge documents for a subject."""
    from app.repositories.knowledge_service import KnowledgeService
    
    try:
        # First verify subject exists
        subject = KnowledgeService.get_subject_by_id(subject_id)
        if not subject:
            raise HTTPException(status_code=404, detail="Subject not found")
        
        documents = KnowledgeService.get_knowledge_documents(
            subject_id, grade_level, level
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
    - count: int (optional, default=5) - Number of questions to generate (1-50)
    - level: int (optional) - Difficulty level filter (1-6)
    - is_live: int (optional, default=1) - 1=live, 0=test
    - focus_weak_areas: bool (optional, default=False) - If True, focus on previous wrong answers; if False, generate fresh questions only
    """
    from app.repositories.knowledge_service import KnowledgeService
    from app.services.ai_service import generate_knowledge_based_questions
    
    # Extract and validate parameters
    uid = request.get('uid')
    subject_id = request.get('subject_id')
    count = request.get('count', 5)  # Default to 5 questions
    level = request.get('level')
    is_live = request.get('is_live', 1)
    focus_weak_areas = request.get('focus_weak_areas', False)  # Default to fresh questions
    
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
        subscription = user_data.get("subscription", 0)
        credits = user_data.get("credits", 0)
        
        logger.info(f"User {uid} subscription level: {subscription}, credits: {credits}")
        
        # Check if user can generate questions based on credits, subscription and daily limit
        limit_check = prompt_service.can_generate_questions(
            uid=uid,
            subscription=subscription,
            credits=credits,
            max_daily_questions=2  # Free and trial users limited to 2/day
        )
        
        if not limit_check['can_generate']:
            # Determine error type based on reason
            error_type = 'no_credits' if 'credit' in limit_check['reason'].lower() else 'daily_limit_exceeded'
            logger.warning(f"User {uid} cannot generate knowledge questions: {limit_check['reason']}")
            raise HTTPException(
                status_code=403,
                detail={
                    'error': error_type,
                    'message': limit_check['reason'],
                    'current_count': limit_check['current_count'],
                    'max_count': limit_check['max_count'],
                    'is_premium': limit_check['is_premium'],
                    'credits_remaining': limit_check['credits_remaining']
                }
            )
        
        logger.info(f"Limit check passed: {limit_check['reason']}")
        is_premium = limit_check['is_premium']
        max_daily = limit_check['max_count']
        daily_count = limit_check['current_count']
        
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
            # No knowledge documents found - use LLM-only generation
            logger.info(f"No knowledge documents found for subject {subject_id}, using LLM-only generation")
            
            # Get user's attempt history for personalization
            user_history = KnowledgeService.get_user_knowledge_attempts(uid, subject_id, limit=20)
            
            # Import the LLM-only generator
            from app.services.ai_service import generate_llm_only_questions
            
            result = generate_llm_only_questions(
                uid=uid,
                subject_id=subject_id,
                subject_name=subject['display_name'],
                grade_level=user_grade,
                count=count,
                level=level,
                user_history=user_history,
                is_live=is_live,
                focus_weak_areas=focus_weak_areas
            )
            
            # Decrement user credits after successful generation
            new_credits = db_service.decrement_user_credits(uid)
            logger.info(f"Decremented credits for user {uid}, new balance: {new_credits}")
            
            # Log usage with analytics data
            ai_summary = result.get('ai_summary', {})
            KnowledgeService.log_knowledge_usage(
                uid=uid,
                knowledge_doc_id=None,
                subject_id=subject_id,
                question_count=count,
                request_text=ai_summary.get('ai_request'),
                response_text=ai_summary.get('ai_response'),
                response_time_ms=ai_summary.get('generation_time_ms'),
                model_name=ai_summary.get('ai_model'),
                used_fallback=ai_summary.get('used_fallback'),
                failed_models=ai_summary.get('failed_models'),
                knowledge_document_ids=ai_summary.get('knowledge_document_ids'),
                past_incorrect_attempts_count=ai_summary.get('past_incorrect_attempts_count'),
                is_llm_only=ai_summary.get('is_llm_only'),
                level=level,
                focus_weak_areas=focus_weak_areas
            )
            
            # Record credit usage
            try:
                db_service.record_credit_usage(
                    uid=uid,
                    game_type="knowledge",
                    subject=subject['display_name'],
                    credits_used=1
                )
            except Exception as usage_error:
                logger.warning(f"Failed to record credit usage: {usage_error}")
            
            actual_count = prompt_service.get_daily_question_generation_count(uid)
            
            return {
                "message": "Questions generated successfully (LLM-only mode)",
                "questions": result['questions'],
                "ai_summary": result.get('ai_summary'),
                "daily_count": actual_count,
                "daily_limit": max_daily,
                "is_premium": is_premium,
                "credits_remaining": new_credits,
                "subject": subject
            }
        
        # Build knowledge_document_ids as comma-separated string
        knowledge_document_ids = ",".join(str(doc['id']) for doc in knowledge_docs) if knowledge_docs else None
        
        # Combine knowledge content (use first document or combine multiple)
        knowledge_content = knowledge_docs[0]['content']
        if len(knowledge_docs) > 1:
            # Combine first portions of multiple documents (no summary field in production)
            content_excerpts = [doc['content'][:500] for doc in knowledge_docs[:3]]
            knowledge_content = "\n\n---\n\n".join(content_excerpts)
        
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
            is_live=is_live,
            focus_weak_areas=focus_weak_areas,
            knowledge_document_ids=knowledge_document_ids
        )
        
        # Decrement user credits after successful generation
        new_credits = db_service.decrement_user_credits(uid)
        logger.info(f"Decremented credits for user {uid}, new balance: {new_credits}")
        
        # Log usage with analytics data
        ai_summary = result.get('ai_summary', {})
        KnowledgeService.log_knowledge_usage(
            uid=uid,
            knowledge_doc_id=knowledge_docs[0]['id'] if knowledge_docs else None,
            subject_id=subject_id,
            question_count=count,
            request_text=ai_summary.get('ai_request'),
            response_text=ai_summary.get('ai_response'),
            response_time_ms=ai_summary.get('generation_time_ms'),
            model_name=ai_summary.get('ai_model'),
            used_fallback=ai_summary.get('used_fallback'),
            failed_models=ai_summary.get('failed_models'),
            knowledge_document_ids=ai_summary.get('knowledge_document_ids'),
            past_incorrect_attempts_count=ai_summary.get('past_incorrect_attempts_count'),
            is_llm_only=ai_summary.get('is_llm_only'),
            level=level,
            focus_weak_areas=focus_weak_areas
        )
        
        # Record credit usage for analytics (with model tracking)
        try:
            # Get model name from ai_summary for FK tracking
            ai_summary = result.get('ai_summary', {})
            model_name = ai_summary.get('ai_model') if ai_summary else None
            db_service.record_credit_usage(
                uid=uid,
                game_type="knowledge",
                subject=subject['display_name'] if subject else None,
                credits_used=1,
                model_name=model_name
            )
        except Exception as usage_error:
            logger.warning(f"Failed to record credit usage (non-critical): {usage_error}")
        
        # Query actual current count AFTER generation is saved
        actual_count = prompt_service.get_daily_question_generation_count(uid)
        
        return {
            "message": "Questions generated successfully",
            "questions": result['questions'],
            "ai_summary": result.get('ai_summary'),
            "daily_count": actual_count,
            "daily_limit": max_daily,
            "is_premium": is_premium,
            "credits_remaining": new_credits,
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
        ai_result = evaluate_answers_with_ai(
            answers=answers,
            subject_name=subject['display_name'],
            uid=uid,
            is_live=is_live
        )
        
        # Extract evaluations and ai_summary from AI response
        results = ai_result.get('evaluations', [])
        ai_summary = ai_result.get('ai_summary', {})
        
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
            "subject": subject,
            "ai_summary": ai_summary
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error evaluating answers: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to evaluate answers: {str(e)}")


@router.post("/generate-question-help")
async def generate_question_help(request: dict):
    """
    Generate AI-powered step-by-step help for a knowledge question.
    
    Behavior:
    - Before answering: Generates explanation for a SIMILAR question
    - After answering: Generates explanation for the EXACT question
    
    Request body:
    - uid: str (required) - Firebase User UID
    - question: str (required) - The question text
    - correct_answer: str (required) - Correct answer for context
    - subject_id: int (required) - Subject ID
    - subject_name: str (required) - Subject display name
    - user_answer: str (optional) - User's answer (when has_answered=true)
    - has_answered: bool (optional, default=false) - Whether user answered
    - is_live: int (optional, default=1) - 1=live, 0=test
    
    Returns:
    - help_steps: List[HelpStep] - Markdown-formatted explanation steps
    - question_variant: str - The question being explained
    - has_answered: bool - Echo of input flag
    - visual_count: int - Number of JSON visual aids
    - svg_count: int - Number of SVG aids
    - credits_remaining: int - User's remaining credits
    - daily_help_count: int - Today's help request count
    
    Rate Limits:
    - Credits: All users must have credits > 0 (deducts 1 credit per request)
    - Daily limit: Free/trial users limited to 2 help requests per day
    - Premium users: Unlimited daily help (but still uses credits)
    
    HTTP Errors:
    - 400: Missing required fields
    - 403: No credits remaining or daily limit exceeded
    - 404: Subject not found
    - 500: AI generation failed
    """
    from app.repositories.db_service import get_user_by_uid
    from app.repositories.knowledge_service import KnowledgeService
    from app.services.prompt_service import PromptService
    
    # Extract and validate parameters
    uid = request.get('uid')
    question = request.get('question')
    correct_answer = request.get('correct_answer')
    subject_id = request.get('subject_id')
    subject_name = request.get('subject_name')
    user_answer = request.get('user_answer')
    has_answered = request.get('has_answered', False)
    is_live = request.get('is_live', 1)
    visual_preference = request.get('visual_preference', 'text')  # 'text', 'json', or 'svg'
    
    if not uid:
        raise HTTPException(status_code=400, detail="uid is required")
    if not question:
        raise HTTPException(status_code=400, detail="question is required")
    if not correct_answer:
        raise HTTPException(status_code=400, detail="correct_answer is required")
    if not subject_id:
        raise HTTPException(status_code=400, detail="subject_id is required")
    if not subject_name:
        raise HTTPException(status_code=400, detail="subject_name is required")
    
    try:
        # Verify subject exists
        subject = KnowledgeService.get_subject_by_id(subject_id)
        if not subject:
            raise HTTPException(status_code=404, detail="Subject not found")
        
        # Get user data for subscription and credits
        user = get_user_by_uid(uid)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        subscription = user.get('subscription', 0)
        credits = user.get('credits', 0)
        
        # Initialize prompt service
        prompt_service = PromptService()
        
        # Check if user can request help (credits + daily limit)
        limit_check = prompt_service.can_request_help(
            uid=uid,
            subscription=subscription,
            credits=credits,
            max_daily_help=2  # Free/trial users limited to 2 per day
        )
        
        if not limit_check['can_request']:
            error_type = 'no_credits' if credits <= 0 else 'daily_limit_exceeded'
            raise HTTPException(
                status_code=403,
                detail={
                    "error": error_type,
                    "message": limit_check['reason'],
                    "current_count": limit_check['current_count'],
                    "max_count": limit_check['max_count'],
                    "is_premium": limit_check['is_premium'],
                    "credits_remaining": credits
                }
            )
        
        # Generate help using AI
        help_result = prompt_service.generate_question_help(
            uid=uid,
            question=question,
            correct_answer=correct_answer,
            subject_id=subject_id,
            subject_name=subject_name,
            user_answer=user_answer,
            has_answered=has_answered,
            visual_preference=visual_preference
        )
        
        # Extract model info from help result
        ai_model = help_result.get("ai_model", "unknown")
        response_time_ms = help_result.get("response_time_ms")
        used_fallback = help_result.get("used_fallback", False)
        
        # Deduct 1 credit
        deduction_success = prompt_service.deduct_user_credit(uid=uid, amount=1)
        if not deduction_success:
            logger.warning(f"Failed to deduct credit for uid={uid} after help generation")
        
        # Calculate new credits remaining
        new_credits = max(0, credits - 1)
        
        # Log help request to knowledge_usage_log
        try:
            log_type = 'knowledge_answer_help' if has_answered else 'knowledge_question_help'
            
            KnowledgeService.log_knowledge_usage(
                uid=uid,
                knowledge_doc_id=None,  # Help requests don't use knowledge documents
                subject_id=subject_id,
                question_count=0,  # Not a question generation
                request_text=help_result.get('ai_request'),  # Full AI prompt
                response_text=help_result.get('ai_response'),  # Full AI response
                model_name=ai_model,
                response_time_ms=response_time_ms,
                log_type=log_type,
                is_live=is_live,
                used_fallback=used_fallback
            )
        except Exception as log_error:
            logger.warning(f"Failed to log help usage: {log_error}")
        
        # Get updated daily count
        daily_count = prompt_service.get_daily_help_count(uid)
        
        return {
            "message": "Help generated successfully",
            "help_steps": help_result["help_steps"],
            "question_variant": help_result["question_variant"],
            "has_answered": help_result["has_answered"],
            "visual_count": help_result["visual_count"],
            "svg_count": help_result["svg_count"],
            "credits_remaining": new_credits,
            "daily_help_count": daily_count,
            "subject": subject,
            "ai_summary": {
                "ai_model": ai_model,
                "generation_time_ms": response_time_ms,
                "used_fallback": used_fallback
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating question help: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate help: {str(e)}")


@router.post("/admin/knowledge-documents")
async def create_knowledge_document(request: dict, admin_key: str = ""):
    """
    Create a new knowledge document (admin only).
    
    Request body:
    - subject_id: int (required)
    - title: str (required)
    - content: str (required)
    - source: str (optional)
    - grade_level: int (optional, 4-7)
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
            source=request.get('source'),
            grade_level=request.get('grade_level')
        )
        
        return {
            "message": "Knowledge document created successfully",
            "id": doc_id
        }
        
    except Exception as e:
        logger.error(f"Error creating knowledge document: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create knowledge document: {str(e)}")


@router.get("/admin/seed-knowledge-documents")
async def seed_knowledge_documents(admin_key: str = ""):
    """
    Seed the knowledge_documents table with sample content for testing.
    """
    from app.repositories.knowledge_service import KnowledgeService
    
    # Verify admin access
    expected_key = os.getenv('ADMIN_KEY', 'dev-admin-key')
    if admin_key != expected_key:
        raise HTTPException(status_code=401, detail="Invalid admin key")
    
    # Sample knowledge documents for each subject
    sample_docs = [
        # Science (subject_id=1)
        {
            "subject_id": 1,
            "title": "The Solar System",
            "content": """The Solar System consists of the Sun and the celestial objects that are bound to it by gravity. The eight planets in order from the Sun are: Mercury, Venus, Earth, Mars, Jupiter, Saturn, Uranus, and Neptune. 

Mercury is the smallest planet and closest to the Sun. Venus is the hottest planet due to its thick atmosphere. Earth is the only planet known to support life. Mars is called the Red Planet because of iron oxide on its surface.

Jupiter is the largest planet with a Great Red Spot storm. Saturn is famous for its beautiful rings made of ice and rock. Uranus rotates on its side. Neptune is the windiest planet with speeds reaching 1,200 mph.

The asteroid belt lies between Mars and Jupiter. Beyond Neptune is the Kuiper Belt, home to dwarf planets like Pluto.""",
            "grade_level": 5,
            "source": "seed-data"
        },
        {
            "subject_id": 1,
            "title": "States of Matter",
            "content": """Matter exists in three main states: solid, liquid, and gas. Each state has unique properties.

Solids have a fixed shape and volume. The particles are tightly packed and vibrate in place. Examples include ice, wood, and metal.

Liquids have a fixed volume but take the shape of their container. Particles are close together but can move around. Examples include water, milk, and oil.

Gases have no fixed shape or volume. Particles are far apart and move freely. Examples include air, oxygen, and steam.

Matter can change states through heating or cooling. Melting changes solid to liquid. Freezing changes liquid to solid. Evaporation changes liquid to gas. Condensation changes gas to liquid.""",
            "grade_level": 4,
            "source": "seed-data"
        },
        # History (subject_id=2)
        {
            "subject_id": 2,
            "title": "Ancient Egypt",
            "content": """Ancient Egypt was one of the world's first great civilizations, lasting over 3,000 years. It developed along the Nile River in northeastern Africa.

The Egyptians built massive pyramids as tombs for their pharaohs. The Great Pyramid of Giza is one of the Seven Wonders of the Ancient World. It was built around 2560 BCE for Pharaoh Khufu.

Egyptians developed hieroglyphics, a writing system using pictures and symbols. They wrote on papyrus, an early form of paper made from reeds.

The Egyptians believed in many gods and an afterlife. They mummified bodies to preserve them for the afterlife. King Tutankhamun's tomb was discovered in 1922 with amazing treasures.

Egyptian achievements include the calendar, medicine, mathematics, and engineering. Cleopatra was the last pharaoh before Egypt became part of the Roman Empire.""",
            "grade_level": 5,
            "source": "seed-data"
        },
        # Geography (subject_id=3)
        {
            "subject_id": 3,
            "title": "Continents and Oceans",
            "content": """Earth has seven continents and five oceans. The continents are Asia, Africa, North America, South America, Antarctica, Europe, and Australia/Oceania.

Asia is the largest continent, home to China and India. Africa has the Sahara Desert and the Nile River. North America includes the United States, Canada, and Mexico. South America contains the Amazon Rainforest. Antarctica is the coldest continent with no permanent population. Europe has many countries despite being smaller. Australia is both a continent and a country.

The five oceans are the Pacific, Atlantic, Indian, Southern, and Arctic. The Pacific is the largest and deepest ocean. The Atlantic separates the Americas from Europe and Africa. The Indian Ocean is the warmest. The Southern Ocean surrounds Antarctica. The Arctic Ocean is the smallest and coldest.

About 71% of Earth's surface is covered by water.""",
            "grade_level": 4,
            "source": "seed-data"
        },
        # Nature (subject_id=4)  
        {
            "subject_id": 4,
            "title": "Animal Classifications",
            "content": """Animals are classified into groups based on their characteristics. The main groups are mammals, birds, reptiles, amphibians, fish, and invertebrates.

Mammals are warm-blooded, have hair or fur, and feed their babies milk. Examples include dogs, cats, elephants, and humans.

Birds are warm-blooded with feathers and lay eggs. They have beaks and most can fly. Examples include eagles, penguins, and sparrows.

Reptiles are cold-blooded with scales. They lay eggs on land. Examples include snakes, lizards, and crocodiles.

Amphibians live both in water and on land. They start life in water with gills, then develop lungs. Examples include frogs, toads, and salamanders.

Fish are cold-blooded and live in water. They breathe through gills and have fins. Examples include salmon, sharks, and goldfish.

Invertebrates have no backbone. They make up 97% of all animals. Examples include insects, spiders, and jellyfish.""",
            "grade_level": 4,
            "source": "seed-data"
        },
        # Space (subject_id=5)
        {
            "subject_id": 5,
            "title": "Stars and Galaxies",
            "content": """Stars are giant balls of hot gas that produce light and heat through nuclear fusion. Our Sun is a medium-sized star.

Stars have different colors based on their temperature. Blue stars are the hottest, followed by white, yellow, orange, and red (coolest).

Stars are born in nebulae, clouds of gas and dust. They go through life cycles: main sequence, red giant, and then become white dwarfs, neutron stars, or black holes depending on their size.

A galaxy is a collection of billions of stars, gas, and dust held together by gravity. Our galaxy is the Milky Way, containing about 200 billion stars.

There are three main types of galaxies: spiral (like the Milky Way), elliptical, and irregular. The nearest major galaxy is Andromeda, 2.5 million light-years away.

The universe contains billions of galaxies, each with billions of stars.""",
            "grade_level": 5,
            "source": "seed-data"
        },
        # Technology (subject_id=6)
        {
            "subject_id": 6,
            "title": "How Computers Work",
            "content": """Computers are electronic devices that process information. They have hardware (physical parts) and software (programs).

The main hardware components are:
- CPU (Central Processing Unit): The brain that does calculations
- RAM (Random Access Memory): Short-term memory for active tasks
- Storage (Hard drive or SSD): Long-term memory for files
- Input devices: Keyboard, mouse, microphone
- Output devices: Monitor, speakers, printer

Software includes the operating system (like Windows or macOS) and applications (like games and word processors).

Computers use binary code - only 0s and 1s. Everything you see on screen is converted to binary for the computer to understand.

The internet connects millions of computers worldwide. Data travels through cables, Wi-Fi, and satellites. A website is hosted on a server - a powerful computer that's always on.

Programming is writing instructions for computers using languages like Python or JavaScript.""",
            "grade_level": 5,
            "source": "seed-data"
        }
    ]
    
    created = []
    errors = []
    
    for doc in sample_docs:
        try:
            doc_id = KnowledgeService.create_knowledge_document(
                subject_id=doc["subject_id"],
                title=doc["title"],
                content=doc["content"],
                grade_level=doc.get("grade_level"),
                source=doc.get("source")
            )
            created.append({"id": doc_id, "title": doc["title"], "subject_id": doc["subject_id"]})
        except Exception as e:
            errors.append({"title": doc["title"], "error": str(e)})
    
    return {
        "message": f"Seeded {len(created)} knowledge documents",
        "created": created,
        "errors": errors
    }


@router.get("/debug/knowledge-documents")
async def debug_knowledge_documents():
    """Debug endpoint to check knowledge documents."""
    from app.repositories.knowledge_service import KnowledgeService
    
    try:
        subjects = KnowledgeService.get_all_subjects()
        result = {
            "subjects_count": len(subjects),
            "subjects": subjects,
            "documents_by_subject": {}
        }
        
        for subject in subjects:
            docs = KnowledgeService.get_knowledge_documents(subject["id"])
            result["documents_by_subject"][subject["name"]] = {
                "count": len(docs),
                "documents": [{"id": d["id"], "title": d["title"], "grade_level": d.get("grade_level")} for d in docs]
            }
        
        return result
        
    except Exception as e:
        import traceback
        return {
            "error": str(e),
            "traceback": traceback.format_exc()
        }


# ============================================================================
# Game Leaderboard Endpoints
# ============================================================================

@router.post("/game-scores")
async def submit_game_score(score_data: dict):
    """
    Submit a game score for the leaderboard.
    
    For multiplication_time: higher score (correct answers) is better
    For multiplication_range: lower time_seconds is better
    """
    from app.models.schemas import GameScoreSubmit
    from app.repositories import db_service
    
    logger.info(f"[/game-scores POST] Received score_data: {score_data}")
    
    try:
        # Validate input
        logger.info(f"[/game-scores POST] Validating input with GameScoreSubmit...")
        score = GameScoreSubmit(**score_data)
        logger.info(f"[/game-scores POST] Validated: uid={score.uid}, game_type={score.game_type}, score={score.score}")
        
        if score.game_type not in ['multiplication_time', 'multiplication_range']:
            raise HTTPException(status_code=400, detail="Invalid game_type. Must be 'multiplication_time' or 'multiplication_range'")
        
        logger.info(f"[/game-scores POST] Calling db_service.save_game_score...")
        result = db_service.save_game_score(
            uid=score.uid,
            user_name=score.user_name,
            game_type=score.game_type,
            score=score.score,
            time_seconds=score.time_seconds,
            total_questions=score.total_questions
        )
        logger.info(f"[/game-scores POST] db_service.save_game_score returned: {result}")
        
        if result:
            logger.info(f"[/game-scores POST] SUCCESS - score_id: {result.get('id')}")
            return {
                "success": True,
                "message": "Score saved successfully",
                "score_id": result.get("id")
            }
        else:
            logger.error(f"[/game-scores POST] FAILED - result was None or falsy")
            raise HTTPException(status_code=500, detail="Failed to save score")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[/game-scores POST] Exception: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save score: {str(e)}")


@router.get("/game-scores/leaderboard/{game_type}")
async def get_leaderboard(game_type: str, limit: int = 3):
    """
    Get top scores for a specific game type.
    
    For multiplication_time: returns top scores by highest correct answers
    For multiplication_range: returns top scores by lowest completion time
    
    Args:
        game_type: 'multiplication_time' or 'multiplication_range'
        limit: Number of top scores to return (default: 3)
    """
    from app.repositories import db_service
    
    if game_type not in ['multiplication_time', 'multiplication_range']:
        raise HTTPException(status_code=400, detail="Invalid game_type. Must be 'multiplication_time' or 'multiplication_range'")
    
    try:
        result = db_service.get_leaderboard(game_type=game_type, limit=limit)
        return result
            
    except Exception as e:
        logger.error(f"Error fetching leaderboard: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch leaderboard: {str(e)}")


@router.get("/game-scores/user/{uid}")
async def get_user_scores(uid: str, game_type: str = None, limit: int = 10):
    """
    Get a specific user's game scores.
    
    Args:
        uid: User's Firebase UID
        game_type: Optional filter by game type
        limit: Number of scores to return (default: 10)
    """
    from app.repositories import db_service
    
    try:
        if game_type and game_type not in ['multiplication_time', 'multiplication_range']:
            raise HTTPException(status_code=400, detail="Invalid game_type")
        
        # Use the best scores function with optional game_type filter
        # For general user scores, we just return recent scores
        result = db_service.get_user_best_scores(uid=uid, game_type=game_type, limit=limit)
        return result
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching user scores: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch user scores: {str(e)}")


@router.get("/game-scores/user/{uid}/best")
async def get_user_best_scores_endpoint(uid: str, game_type: str, limit: int = 3):
    """
    Get a user's best scores for a specific game type.

    For multiplication_time: returns top scores by highest correct answers
    For multiplication_range: returns top scores by lowest completion time

    Args:
        uid: User's Firebase UID
        game_type: 'multiplication_time' or 'multiplication_range'
        limit: Number of best scores to return (default: 3)
    """
    from app.repositories import db_service

    if game_type not in ['multiplication_time', 'multiplication_range']:
        raise HTTPException(status_code=400, detail="Invalid game_type. Must be 'multiplication_time' or 'multiplication_range'")

    try:
        result = db_service.get_user_best_scores(uid=uid, game_type=game_type, limit=limit)
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching user best scores: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch user best scores: {str(e)}")

# ============================================================================
# Performance Report Endpoints
# ============================================================================

@router.get("/performance-report/{student_uid}/check-availability")
async def check_performance_report_availability(student_uid: str):
    """
    Check if sufficient data is available to generate a performance report for a student.

    Args:
        student_uid: Firebase User UID

    Returns:
        Dictionary indicating data availability and readiness for report generation
    """
    try:
        result = performance_report_service.check_data_availability(student_uid)
        return {
            "success": True,
            "student_uid": student_uid,
            "can_generate_report": result.get("can_generate_report", False),
            "student_exists": result.get("student_exists", False),
            "attempts_count": result.get("attempts_count", 0),
            "sufficient_data": result.get("sufficient_data", False),
            "neo4j_available": result.get("neo4j_available", False),
            "message": "Report generation available" if result.get("can_generate_report") else "Insufficient data for report generation",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error checking performance report availability: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to check report availability: {str(e)}")

@router.get("/performance-report/{student_uid}")
async def generate_performance_report(student_uid: str, admin_key: str = Header(None)):
    """
    Generate a comprehensive performance report for a student using the agentic workflow.

    Args:
        student_uid: Firebase User UID
        admin_key: Optional admin key header for bypassing cooldown

    Returns:
        Dictionary containing the analysis report and metadata
    """
    try:
        # Check if report generation is possible
        availability = performance_report_service.check_data_availability(student_uid)
        if not availability.get("can_generate_report", False):
            error_msg = f"Cannot generate report: {availability.get('error', 'Insufficient data or Neo4j unavailable')}"
            logger.warning(error_msg)
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "insufficient_data",
                    "message": error_msg,
                    "student_exists": availability.get("student_exists", False),
                    "attempts_count": availability.get("attempts_count", 0),
                    "neo4j_available": availability.get("neo4j_available", False)
                }
            )

        # Generate the performance report (pass admin_key for cooldown bypass)
        result = performance_report_service.generate_performance_report(student_uid, admin_key)

        if result["success"]:
            return {
                "success": True,
                "student_uid": student_uid,
                "analysis_report": result["analysis_report"],
                "evidence_sufficient": result["evidence_sufficient"],
                "evidence_quality_score": result["evidence_quality_score"],
                "retrieval_attempts": result["retrieval_attempts"],
                "execution_log": result["execution_log"],
                "agent_statuses": result.get("agent_statuses", {}),
                "workflow_progress": result.get("workflow_progress", []),
                "errors": result.get("errors", []),
                "processing_time_ms": result.get("processing_time_ms", 0),
                "model_used": result.get("model_used", ""),
                "trace_id": result.get("trace_id"),
                "timestamp": result["timestamp"],
                "message": "Performance report generated successfully"
            }
        else:
            # Handle cooldown errors specifically
            if result.get("error") == "daily_limit_exceeded":
                raise HTTPException(
                    status_code=429,  # Too Many Requests
                    detail={
                        "error": "daily_limit_exceeded",
                        "message": "SmartBoy Limit: Performance report can only be generated once every 24 hours",
                        "cooldown_remaining": result.get("cooldown_remaining", 0),
                        "cooldown_end": result.get("cooldown_end"),
                        "student_uid": student_uid
                    }
                )
            else:
                raise HTTPException(
                    status_code=500,
                    detail={
                        "error": "report_generation_failed",
                        "message": result.get("error", "Unknown error during report generation"),
                        "errors": result.get("errors", []),
                        "student_uid": student_uid
                    }
                )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating performance report: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate performance report: {str(e)}")

@router.post("/performance-report/{student_uid}/query")
async def query_performance_report(student_uid: str, request: PerformanceReportQueryRequest):
    """
    Answer user questions about a student's performance report details.

    Args:
        student_uid: Firebase User UID
        request: Query payload with optional subject filter
    """
    try:
        result = performance_report_service.handle_performance_request(
            student_uid=student_uid,
            query_text=request.query,
            intent=None
        )

        if not result.get("success", False):
            if result.get("error") == "daily_limit_exceeded":
                raise HTTPException(
                    status_code=429,
                    detail={
                        "error": "daily_limit_exceeded",
                        "message": result.get(
                            "message",
                            "SmartBoy Limit: Performance report can only be generated once every 24 hours"
                        ),
                        "cooldown_remaining": result.get("cooldown_remaining", 0),
                        "cooldown_end": result.get("cooldown_end"),
                        "model_used": result.get("model_used", ""),
                        "model_configured": result.get("model_configured", ""),
                        "model_invoked": result.get("model_invoked", False),
                        "api_key_used": result.get("api_key_used", ""),
                        "intent": result.get("intent"),
                        "student_uid": student_uid
                    }
                )
            raise HTTPException(
                status_code=500,
                detail={
                    "error": result.get("error", "query_failed"),
                    "message": result.get("message", "Failed to answer performance query"),
                    "model_used": result.get("model_used", ""),
                    "model_configured": result.get("model_configured", ""),
                    "api_key_used": result.get("api_key_used", ""),
                    "intent": result.get("intent"),
                    "student_uid": student_uid
                }
            )

        return {
            "success": True,
            "student_uid": student_uid,
            "query": result.get("query", request.query),
            "answer": result.get("answer"),
            "message": result.get("message"),
            "evidence_sufficient": result.get("evidence_sufficient"),
            "evidence_quality_score": result.get("evidence_quality_score"),
            "retrieval_attempts": result.get("retrieval_attempts"),
            "execution_log": result.get("execution_log", []),
            "guardrails": result.get("guardrails", {}),
            "processing_time_ms": result.get("processing_time_ms", 0),
            "model_used": result.get("model_used", ""),
            "model_configured": result.get("model_configured", ""),
            "api_key_used": result.get("api_key_used", "")
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error answering performance report query: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to answer performance query: {str(e)}")

@router.get("/performance-report-history/{student_uid}")
async def get_performance_reports_history(student_uid: str):
    """
    Retrieve the history of performance reports for a student.

    Args:
        student_uid: Firebase User UID

    Returns:
        List of performance reports
    """
    try:
        reports = performance_report_service.get_performance_reports(student_uid)
        return {
            "success": True,
            "student_uid": student_uid,
            "reports": reports,
            "count": len(reports),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error retrieving performance reports: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve performance reports: {str(e)}")

@router.post("/admin/analytics/reports")
async def get_performance_reports_analytics(admin_key: str = ""):
    """Get analytics for performance reports (admin only)"""
    # Simple admin verification
    expected_key = os.getenv('ADMIN_KEY', 'dev-admin-key')
    if admin_key != expected_key:
        raise HTTPException(status_code=401, detail="Invalid admin key")

    try:
        db = DatabaseFactory.get_provider()
        conn = db._get_connection()
        cursor = conn.cursor()

        # Get total reports count
        cursor.execute("SELECT COUNT(*) FROM performance_reports")
        total_reports = cursor.fetchone()[0]

        # Get success rate
        cursor.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN success THEN 1 ELSE 0 END) as successful
            FROM performance_reports
        """)
        result = cursor.fetchone()
        success_rate = (result[1] / result[0] * 100) if result[0] > 0 else 0

        # Get reports by date (last 30 days)
        cursor.execute("""
            SELECT
                DATE(created_at) as report_date,
                COUNT(*) as count,
                SUM(CASE WHEN success THEN 1 ELSE 0 END) as successful
            FROM performance_reports
            WHERE created_at >= NOW() - INTERVAL '30 days'
            GROUP BY DATE(created_at)
            ORDER BY report_date DESC
        """)
        daily_stats = [
            {
                "date": str(row[0]),
                "total": row[1],
                "successful": row[2],
                "success_rate": (row[2] / row[1] * 100) if row[1] > 0 else 0
            }
            for row in cursor.fetchall()
        ]

        # Get average processing time
        cursor.execute("""
            SELECT AVG(processing_time_ms)
            FROM performance_reports
            WHERE processing_time_ms IS NOT NULL
        """)
        avg_processing_time = cursor.fetchone()[0] or 0

        conn.close()

        return {
            "success": True,
            "analytics": {
                "total_reports": total_reports,
                "success_rate": round(success_rate, 2),
                "average_processing_time_ms": round(avg_processing_time, 2),
                "daily_stats": daily_stats
            },
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting analytics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get analytics: {str(e)}")

@router.post("/admin/reports/bulk-regenerate")
async def bulk_regenerate_reports(admin_key: str = "", limit: int = 10):
    """Bulk regenerate performance reports for users who don't have recent reports (admin only)"""
    # Simple admin verification
    expected_key = os.getenv('ADMIN_KEY', 'dev-admin-key')
    if admin_key != expected_key:
        raise HTTPException(status_code=401, detail="Invalid admin key")

    try:
        db = DatabaseFactory.get_provider()
        conn = db._get_connection()
        cursor = conn.cursor()

        # Find users who haven't had reports in the last 24 hours and have attempts
        cursor.execute("""
            SELECT DISTINCT u.uid, u.name
            FROM users u
            LEFT JOIN performance_reports pr ON u.uid = pr.uid AND pr.created_at >= NOW() - INTERVAL '24 hours'
            JOIN knowledge_question_attempts kqa ON u.uid = kqa.uid
            WHERE pr.id IS NULL
            AND u.is_blocked = FALSE
            LIMIT %s
        """, (limit,))

        users_to_process = cursor.fetchall()
        conn.close()

        results = []
        for uid, name in users_to_process:
            try:
                # Generate report without cooldown check (admin override)
                result = performance_report_service.generate_performance_report(uid, admin_key)
                results.append({
                    "uid": uid,
                    "name": name,
                    "success": result["success"],
                    "message": "Report generated successfully" if result["success"] else result.get("error", "Unknown error")
                })
            except Exception as e:
                results.append({
                    "uid": uid,
                    "name": name,
                    "success": False,
                    "message": str(e)
                })

        return {
            "success": True,
            "processed": len(results),
            "results": results,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error in bulk regeneration: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to bulk regenerate reports: {str(e)}")

@router.get("/performance-reports/{student_uid}")
async def get_performance_reports(student_uid: str):
    """
    Retrieve all performance reports for a student.

    Args:
        student_uid: Firebase User UID

    Returns:
        List of performance reports
    """
    try:
        reports = performance_report_service.get_performance_reports(student_uid)
        return {
            "success": True,
            "student_uid": student_uid,
            "reports": reports,
            "count": len(reports),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error retrieving performance reports: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve performance reports: {str(e)}")


@router.get("/performance-reports/{student_uid}/latest")
async def get_latest_performance_report(student_uid: str):
    """
    Retrieve the latest performance report for a student.

    Returns the most recent report or a 404 if none exist.
    """
    try:
        reports = performance_report_service.get_performance_reports(student_uid)
        if not reports:
            raise HTTPException(status_code=404, detail="No performance reports found for this student")

        latest = reports[0]
        return {
            "success": True,
            "student_uid": student_uid,
            "report": latest,
            "timestamp": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving latest performance report: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve latest report: {str(e)}")

@router.post("/admin/performance-reports/analytics")
async def get_performance_reports_analytics(admin_key: str = Header(None)):
    """
    Get analytics for performance reports (admin only).

    Args:
        admin_key: Admin authentication key

    Returns:
        Analytics data for performance reports
    """
    # Simple admin verification
    expected_key = os.getenv('ADMIN_KEY', 'dev-admin-key')
    if admin_key != expected_key:
        raise HTTPException(status_code=401, detail="Invalid admin key")

    try:
        db = DatabaseFactory.get_provider()
        conn = db._get_connection()
        cursor = conn.cursor()

        # Get total reports count
        cursor.execute("SELECT COUNT(*) FROM performance_reports")
        total_reports = cursor.fetchone()[0]

        # Get success rate
        cursor.execute("SELECT COUNT(*) FROM performance_reports WHERE success = TRUE")
        successful_reports = cursor.fetchone()[0]

        # Get reports by date (last 30 days)
        cursor.execute("""
            SELECT DATE(created_at), COUNT(*)
            FROM performance_reports
            WHERE created_at >= NOW() - INTERVAL '30 days'
            GROUP BY DATE(created_at)
            ORDER BY DATE(created_at)
        """)
        daily_stats = [{"date": str(row[0]), "count": row[1]} for row in cursor.fetchall()]

        # Get average processing time
        cursor.execute("SELECT AVG(processing_time_ms) FROM performance_reports WHERE processing_time_ms > 0")
        avg_processing_time = cursor.fetchone()[0] or 0

        # Get top users by report count
        cursor.execute("""
            SELECT uid, COUNT(*) as report_count
            FROM performance_reports
            GROUP BY uid
            ORDER BY report_count DESC
            LIMIT 10
        """)
        top_users = [{"uid": row[0], "report_count": row[1]} for row in cursor.fetchall()]

        cursor.close()
        conn.close()

        success_rate = (successful_reports / total_reports * 100) if total_reports > 0 else 0

        return {
            "success": True,
            "analytics": {
                "total_reports": total_reports,
                "successful_reports": successful_reports,
                "success_rate": round(success_rate, 2),
                "average_processing_time_ms": round(avg_processing_time, 2),
                "daily_stats": daily_stats,
                "top_users": top_users
            },
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting performance reports analytics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get analytics: {str(e)}")

@router.post("/admin/performance-reports/bulk-regenerate")
async def bulk_regenerate_reports(admin_key: str = Header(None), days_back: int = 7):
    """
    Bulk regenerate performance reports for users who had reports in the last N days (admin only).

    Args:
        admin_key: Admin authentication key
        days_back: Number of days to look back for users with reports

    Returns:
        Status of bulk regeneration job
    """
    # Simple admin verification
    expected_key = os.getenv('ADMIN_KEY', 'dev-admin-key')
    if admin_key != expected_key:
        raise HTTPException(status_code=401, detail="Invalid admin key")

    try:
        db = DatabaseFactory.get_provider()
        conn = db._get_connection()
        cursor = conn.cursor()

        # Get distinct UIDs who had reports in the last N days
        cursor.execute("""
            SELECT DISTINCT uid
            FROM performance_reports
            WHERE created_at >= NOW() - INTERVAL '%s days'
        """, (days_back,))

        uids = [row[0] for row in cursor.fetchall()]
        cursor.close()
        conn.close()

        # Start background regeneration (simplified - in production use a job queue)
        regenerated_count = 0
        failed_count = 0
        results = []

        for uid in uids:
            try:
                # Force regeneration by passing admin key
                result = performance_report_service.generate_performance_report(uid, admin_key)
                if result["success"]:
                    regenerated_count += 1
                    results.append({"uid": uid, "status": "success"})
                else:
                    failed_count += 1
                    results.append({"uid": uid, "status": "failed", "error": result.get("error")})
            except Exception as e:
                failed_count += 1
                results.append({"uid": uid, "status": "error", "error": str(e)})

        return {
            "success": True,
            "message": f"Bulk regeneration completed. {regenerated_count} successful, {failed_count} failed.",
            "total_users": len(uids),
            "regenerated_count": regenerated_count,
            "failed_count": failed_count,
            "results": results,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error in bulk regeneration: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start bulk regeneration: {str(e)}")
