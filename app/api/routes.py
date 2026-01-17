from fastapi import APIRouter, HTTPException, Header
from app.models.schemas import MathAttempt, GenerateQuestionsRequest, UserRegistration, UserProfileUpdate, AdjustCreditsRequest
from app.services import ai_service
from app.services.ai_service import generate_practice_questions
from app.services.prompt_service import PromptService
from app.services.user_blocking_service import UserBlockingService
from app.services.billing_service import billing_service
from app.services.fcm_service import fcm_service
from app.validators.billing_validators import (
    VerifyPurchaseRequest, VerifyPurchaseResponse,
    ProcessPurchaseRequest, ProcessPurchaseResponse,
    GooglePlayWebhookRequest,
    UpdateSubscriptionRequest, UpdateSubscriptionResponse,
    GetPurchaseHistoryResponse,
    RefundPurchaseRequest, RefundPurchaseResponse
)
from app.repositories import db_service
from app.db.vercel_migrations import migration_manager
from app.db.models import get_session
from app.config import GOOGLE_PLAY_SERVICE_ACCOUNT_JSON
import uuid
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
        credits_expire_at = user_data.get("credits_expire_at")
        
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
            "credits_expire_at": credits_expire_at.isoformat() if credits_expire_at else None,
            "registrationDate": user_data["registration_date"],
            "daily_count": daily_count,
            "daily_limit": max_daily,
            "is_premium": is_premium,
            "is_blocked": user_data.get("is_blocked", False),
            "blocked_reason": user_data.get("blocked_reason"),
            "is_debug": user_data.get("is_debug", False),
            "help_tone_preference": user_data.get("help_tone_preference")
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving user: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve user: {str(e)}")

@router.patch("/users/{uid}/profile")
async def update_user_profile(uid: str, update: UserProfileUpdate):
    """Update user profile (name, displayName, gradeLevel, helpTonePreference)"""
    try:
        # Verify user exists
        user_data = db_service.get_user_by_uid(uid)
        if not user_data:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Check if any field is provided
        if update.name is None and update.displayName is None and update.gradeLevel is None and update.helpTonePreference is None:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        # Update profile
        db_service.update_user_profile(
            uid,
            name=update.name,
            display_name=update.displayName,
            grade_level=update.gradeLevel,
            help_tone_preference=update.helpTonePreference
        )
        
        updated_fields = []
        if update.name is not None:
            updated_fields.append(f"name={update.name}")
        if update.displayName is not None:
            updated_fields.append(f"displayName={update.displayName}")
        if update.gradeLevel is not None:
            updated_fields.append(f"gradeLevel={update.gradeLevel}")
        if update.helpTonePreference is not None:
            updated_fields.append(f"helpTonePreference={update.helpTonePreference}")
        
        logger.info(f"Updated profile for user {uid}: {', '.join(updated_fields)}")
        
        return {
            "success": True,
            "uid": uid,
            "name": update.name,
            "displayName": update.displayName,
            "gradeLevel": update.gradeLevel,
            "helpTonePreference": update.helpTonePreference,
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
            "blocked_reason": None
        }


@router.post("/users/{user_uid}/device-token")
async def register_device_token(
    user_uid: str,
    device_id: str = Header(..., alias="X-Device-Id"),
    fcm_token: str = Header(..., alias="X-FCM-Token"),
    platform: str = Header(default="android", alias="X-Platform")
):
    """
    Register or update FCM device token for push notifications.
    
    Args:
        user_uid: Firebase User UID
        device_id: Stable device identifier (from X-Device-Id header)
        fcm_token: FCM registration token (from X-FCM-Token header)
        platform: Device platform - 'android', 'ios', 'web' (from X-Platform header)
    
    Returns:
        Registration result
    """
    try:
        # Validate user exists
        user_data = db_service.get_user_by_uid(user_uid)
        if not user_data:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Register device token
        result = fcm_service.register_device_token(
            uid=user_uid,
            device_id=device_id,
            fcm_token=fcm_token,
            platform=platform
        )
        
        if result['success']:
            logger.info(f"Registered device token for user {user_uid}, device {device_id}")
            return {
                "success": True,
                "message": result['message']
            }
        else:
            logger.error(f"Failed to register device token: {result.get('error')}")
            raise HTTPException(status_code=500, detail=result.get('error', 'Unknown error'))
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error registering device token for {user_uid}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to register device token: {str(e)}")


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
        
        # Send FCM notification to user's devices (non-blocking, with retries)
        try:
            is_upgrade = request.amount > 0
            fcm_result = await fcm_service.send_credit_notification(
                uid=user_uid,
                old_credits=result['old_credits'],
                new_credits=result['new_credits'],
                is_upgrade=is_upgrade,
                max_retries=2
            )
            if fcm_result['success']:
                logger.info(f"FCM notification sent to {fcm_result['sent_count']} device(s) for user {user_uid}")
            else:
                logger.warning(f"FCM notification failed for user {user_uid}: {fcm_result.get('error')}")
        except Exception as fcm_error:
            # Log but don't fail the request if FCM fails
            logger.error(f"Error sending FCM notification for credit adjustment: {fcm_error}")
        
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
# Google Play Billing Endpoints
# ============================================================================

@router.get("/billing/health")
async def billing_health():
    """
    Check if Google Play API is properly initialized and ready to process purchases.
    
    Returns:
        Health status of the billing system including:
        - google_play_api_initialized: Whether the Google Play API client is ready
        - package_name: The configured package name
        - service_account_configured: Whether the service account JSON is set
        - status: Overall health status (healthy/degraded)
    """
    # Ensure initialization is attempted (lazy init for serverless)
    billing_service._ensure_initialized()
    
    is_initialized = billing_service.publisher_api is not None
    has_service_account = bool(GOOGLE_PLAY_SERVICE_ACCOUNT_JSON)
    
    # Try to get more diagnostic info
    diagnostic_info = {}
    if has_service_account and not is_initialized:
        try:
            import base64
            import json as json_lib
            # Test if we can decode the service account JSON
            decoded = base64.b64decode(GOOGLE_PLAY_SERVICE_ACCOUNT_JSON).decode('utf-8')
            parsed = json_lib.loads(decoded)
            diagnostic_info['can_decode_json'] = True
            diagnostic_info['has_project_id'] = 'project_id' in parsed
            diagnostic_info['has_private_key'] = 'private_key' in parsed
        except Exception as e:
            diagnostic_info['decode_error'] = str(e)
    
    return {
        "google_play_api_initialized": is_initialized,
        "service_account_configured": has_service_account,
        "package_name": billing_service.package_name,
        "status": "healthy" if is_initialized else "degraded",
        "message": "Billing system ready" if is_initialized else "Google Play API not initialized - check GOOGLE_PLAY_SERVICE_ACCOUNT_JSON environment variable",
        "diagnostics": diagnostic_info if diagnostic_info else None
    }


@router.post("/billing/verify-purchase", response_model=VerifyPurchaseResponse)
async def verify_purchase(
    request: VerifyPurchaseRequest,
    uid: str = Header(..., description="Firebase User UID")
):
    """
    Verify a Google Play purchase with Google's servers
    
    Args:
        request: Purchase verification request with product_id, purchase_token, product_type
        uid: Firebase User UID from header
    
    Returns:
        Verification result with purchase_id if successful
    """
    try:
        logger.info(f"[PURCHASE] Starting verification for user {uid}: product_id={request.product_id}, type={request.product_type}")
        
        # Verify with Google Play
        if request.product_type == 'subscription':
            is_valid, purchase_data, error = billing_service.verify_subscription_purchase(
                request.product_id,
                request.purchase_token
            )
        else:  # product
            is_valid, purchase_data, error = billing_service.verify_product_purchase(
                request.product_id,
                request.purchase_token
            )
        
        if not is_valid:
            logger.warning(f"[PURCHASE] Verification failed for user {uid}: {error}")
            return VerifyPurchaseResponse(
                success=False,
                is_valid=False,
                error=error or "Purchase verification failed",
                message="Invalid purchase"
            )
        
        # Save purchase record
        logger.info(f"[PURCHASE] Verification successful, saving to database...")
        auto_renewing = purchase_data.get('auto_renewing') if request.product_type == 'subscription' else None
        purchase_id = billing_service.save_purchase_record(
            uid=uid,
            product_id=request.product_id,
            purchase_token=request.purchase_token,
            purchase_data=purchase_data,
            auto_renewing=auto_renewing
        )
        
        logger.info(f"[PURCHASE] ✅ Purchase verified and saved to DB for user {uid}: product={request.product_id}, purchase_id={purchase_id}, table=google_play_purchases")
        
        return VerifyPurchaseResponse(
            success=True,
            is_valid=True,
            purchase_id=purchase_id,
            message="Purchase verified successfully"
        )
        
    except Exception as e:
        logger.error(f"Error verifying purchase: {e}")
        return VerifyPurchaseResponse(
            success=False,
            is_valid=False,
            error=str(e),
            message="Failed to verify purchase"
        )


@router.post("/billing/process-purchase", response_model=ProcessPurchaseResponse)
async def process_purchase(
    request: ProcessPurchaseRequest,
    uid: str = Header(..., description="Firebase User UID")
):
    """
    Process a verified purchase - grant subscription or credits
    
    Args:
        request: Process request with purchase_id
        uid: Firebase User UID from header
    
    Returns:
        Processing result with updated subscription/credits
    """
    try:
        logger.info(f"[PURCHASE] Processing purchase_id={request.purchase_id} for user {uid}")
        
        # Get purchase details from database
        conn = DatabaseFactory.get_provider()._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT product_id, uid FROM google_play_purchases WHERE id = %s
        """, (request.purchase_id,))
        
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not result:
            logger.error(f"[PURCHASE] Purchase not found in DB: purchase_id={request.purchase_id}")
            raise HTTPException(status_code=404, detail="Purchase not found")
        
        product_id, purchase_uid = result
        logger.info(f"[PURCHASE] Retrieved purchase from DB: product_id={product_id}, owner_uid={purchase_uid[:8]}...")
        
        # Verify purchase belongs to requesting user
        if purchase_uid != uid:
            raise HTTPException(status_code=403, detail="Purchase does not belong to this user")
        
        # Determine if it's a subscription or credit pack
        from app.services.billing_service import SKU_TO_SUBSCRIPTION_LEVEL, SKU_TO_CREDIT_AMOUNT
        
        if product_id in SKU_TO_SUBSCRIPTION_LEVEL:
            # Process subscription
            logger.info(f"[PURCHASE] Processing as SUBSCRIPTION: {product_id}")
            process_result = billing_service.process_subscription_purchase(
                uid=uid,
                product_id=product_id,
                purchase_id=request.purchase_id
            )
            
            logger.info(f"[PURCHASE] ✅ Subscription activated for user {uid}: {product_id}, level {process_result['old_subscription']} → {process_result['new_subscription']}")
            
            return ProcessPurchaseResponse(
                success=True,
                old_subscription=process_result['old_subscription'],
                new_subscription=process_result['new_subscription'],
                credits_granted=0,
                message=f"Subscription activated: {product_id}"
            )
            
        elif product_id in SKU_TO_CREDIT_AMOUNT:
            # Process credit pack
            logger.info(f"[PURCHASE] Processing as CREDIT PACK: {product_id}")
            process_result = billing_service.process_credit_pack_purchase(
                uid=uid,
                product_id=product_id,
                purchase_id=request.purchase_id
            )
            
            logger.info(f"[PURCHASE] ✅ Credits granted for user {uid}: {product_id}, credits {process_result['old_credits']} → {process_result['new_credits']} (+{process_result['credits_granted']})")
            
            return ProcessPurchaseResponse(
                success=True,
                old_credits=process_result['old_credits'],
                new_credits=process_result['new_credits'],
                credits_granted=process_result['credits_granted'],
                message=f"Credits added: {product_id}"
            )
        else:
            raise HTTPException(status_code=400, detail=f"Unknown product: {product_id}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing purchase: {e}")
        return ProcessPurchaseResponse(
            success=False,
            credits_granted=0,
            error=str(e),
            message="Failed to process purchase"
        )


@router.post("/billing/google-play-webhook")
async def google_play_webhook(request: GooglePlayWebhookRequest):
    """
    Handle Google Play Real-time Developer Notifications
    
    Processes subscription renewals, cancellations, and other events
    """
    try:
        logger.info(f"Received Google Play webhook: {request.dict()}")
        
        # Handle subscription notifications
        if request.subscriptionNotification:
            notification = request.subscriptionNotification
            notification_type = notification.get('notificationType')
            purchase_token = notification.get('purchaseToken')
            
            # Find purchase in database
            conn = DatabaseFactory.get_provider()._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, uid, product_id FROM google_play_purchases 
                WHERE purchase_token = %s
            """, (purchase_token,))
            
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if not result:
                logger.warning(f"Purchase not found for webhook token: {purchase_token}")
                return {"status": "ok", "message": "Purchase not found"}
            
            purchase_id, uid, product_id = result
            
            # Handle different notification types
            # 1 = SUBSCRIPTION_RECOVERED
            # 2 = SUBSCRIPTION_RENEWED
            # 3 = SUBSCRIPTION_CANCELED
            # 4 = SUBSCRIPTION_PURCHASED
            # 5 = SUBSCRIPTION_ON_HOLD
            # 6 = SUBSCRIPTION_IN_GRACE_PERIOD
            # 7 = SUBSCRIPTION_RESTARTED
            # 8 = SUBSCRIPTION_PRICE_CHANGE_CONFIRMED
            # 9 = SUBSCRIPTION_DEFERRED
            # 10 = SUBSCRIPTION_PAUSED
            # 11 = SUBSCRIPTION_PAUSE_SCHEDULE_CHANGED
            # 12 = SUBSCRIPTION_REVOKED
            # 13 = SUBSCRIPTION_EXPIRED
            
            if notification_type in [3, 12, 13]:  # Cancelled, Revoked, or Expired
                # For revoked subscriptions, also refund credits
                if notification_type == 12:  # SUBSCRIPTION_REVOKED
                    try:
                        refund_result = billing_service.handle_webhook_refund(
                            purchase_token=purchase_token,
                            notification_type=notification_type
                        )
                        logger.info(f"Webhook refund processed for user {uid}: {refund_result}")
                    except Exception as e:
                        logger.error(f"Error processing webhook refund: {e}")
                
                # Cancel subscription for all cancellation types
                billing_service.cancel_subscription(
                    uid=uid,
                    purchase_id=purchase_id,
                    reason=f"Google Play notification type {notification_type}"
                )
                logger.info(f"Subscription cancelled for user {uid}")
            
            elif notification_type in [1, 2, 4, 7]:  # Recovered, Renewed, Purchased, or Restarted
                # Re-activate subscription if needed
                from app.services.billing_service import SKU_TO_SUBSCRIPTION_LEVEL
                subscription_level = SKU_TO_SUBSCRIPTION_LEVEL.get(product_id)
                
                if subscription_level:
                    # Update subscription level
                    conn = DatabaseFactory.get_provider()._get_connection()
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE users SET subscription = %s WHERE uid = %s
                    """, (subscription_level, uid))
                    
                    # Log history
                    cursor.execute("""
                        INSERT INTO subscription_history 
                        (uid, purchase_id, event, new_subscription, credits_granted, notes)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (uid, purchase_id, 'RENEWED', subscription_level, 0, 
                          f"Google Play notification type {notification_type}"))
                    
                    conn.commit()
                    cursor.close()
                    conn.close()
                    
                    logger.info(f"Subscription renewed for user {uid}")
        
        # Handle one-time product notifications (credit pack refunds)
        elif request.oneTimeProductNotification:
            notification = request.oneTimeProductNotification
            notification_type = notification.get('notificationType')
            purchase_token = notification.get('purchaseToken')
            
            # Notification types for one-time products:
            # 1 = ONE_TIME_PRODUCT_PURCHASED
            # 2 = ONE_TIME_PRODUCT_CANCELED
            
            if notification_type == 2:  # ONE_TIME_PRODUCT_CANCELED (refund)
                try:
                    refund_result = billing_service.handle_webhook_refund(
                        purchase_token=purchase_token,
                        notification_type=notification_type
                    )
                    logger.info(f"Credit pack refund processed: {refund_result}")
                except Exception as e:
                    logger.error(f"Error processing credit pack refund: {e}")
            else:
                logger.info(f"One-time product notification type {notification_type}: {notification}")
        
        return {"status": "ok", "message": "Webhook processed"}
        
    except Exception as e:
        logger.error(f"Error processing Google Play webhook: {e}")
        return {"status": "error", "message": str(e)}


@router.post("/admin/users/{user_uid}/subscription", response_model=UpdateSubscriptionResponse)
async def update_user_subscription(
    user_uid: str,
    request: UpdateSubscriptionRequest,
    admin_key: str = ""
):
    """
    Manually update a user's subscription level (admin only)
    
    Args:
        user_uid: Firebase User UID
        request: Subscription update request
        admin_key: Admin authentication key
    
    Returns:
        Subscription update result
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
        
        old_subscription = user_data.get('subscription', 0)
        
        # Update subscription
        conn = DatabaseFactory.get_provider()._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE users 
            SET subscription = %s 
            WHERE uid = %s
        """, (request.subscription_level, user_uid))
        
        # Log subscription history
        cursor.execute("""
            INSERT INTO subscription_history 
            (uid, purchase_id, event, old_subscription, new_subscription, credits_granted, notes)
            VALUES (%s, NULL, %s, %s, %s, %s, %s)
        """, (
            user_uid,
            'MANUAL',
            old_subscription,
            request.subscription_level,
            0,
            request.reason or 'Manual admin update'
        ))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"Admin updated subscription for {user_uid}: {old_subscription} -> {request.subscription_level}")
        
        return UpdateSubscriptionResponse(
            success=True,
            uid=user_uid,
            old_subscription=old_subscription,
            new_subscription=request.subscription_level,
            message=f"Subscription updated from {old_subscription} to {request.subscription_level}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating subscription for {user_uid}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update subscription: {str(e)}")


@router.post("/admin/expire-credits")
async def expire_credits_admin(
    admin_key: str = Header(..., description="Admin API key")
):
    """
    Admin endpoint to manually trigger credit expiry cleanup
    Expires credits for all users whose credits_expire_at has passed
    """
    try:
        # Verify admin key
        expected_key = os.getenv("ADMIN_API_KEY", "dev-admin-key")
        if admin_key != expected_key:
            raise HTTPException(status_code=403, detail="Invalid admin key")
        
        from app.services.credit_expiry_service import credit_expiry_service
        
        # Expire credits
        result = credit_expiry_service.expire_credits()
        
        if result['success']:
            return {
                "success": True,
                "expired_count": result['expired_count'],
                "message": result['message']
            }
        else:
            raise HTTPException(status_code=500, detail=result.get('error', 'Failed to expire credits'))
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in expire credits admin endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to expire credits: {str(e)}")


@router.post("/admin/billing/refund", response_model=RefundPurchaseResponse)
async def refund_purchase_admin(request: RefundPurchaseRequest):
    """
    Admin endpoint to refund a purchase
    Deducts credits from user and marks purchase as cancelled
    
    Args:
        request: Refund request with purchase_id, reason, and admin_key
    
    Returns:
        Refund result with credits deducted
    """
    try:
        # Verify admin key
        expected_key = os.getenv('ADMIN_KEY', 'dev-admin-key')
        if request.admin_key != expected_key:
            raise HTTPException(status_code=401, detail="Invalid admin key")
        
        # Process refund
        result = billing_service.refund_purchase(
            purchase_id=request.purchase_id,
            refund_reason=request.refund_reason
        )
        
        return RefundPurchaseResponse(
            success=True,
            purchase_id=result['purchase_id'],
            product_id=result['product_id'],
            credits_deducted=result['credits_deducted'],
            old_credits=result['old_credits'],
            new_credits=result['new_credits'],
            message=f"Refunded {result['product_id']}: deducted {result['credits_deducted']} credits"
        )
        
    except HTTPException:
        raise
    except ValueError as e:
        return RefundPurchaseResponse(
            success=False,
            purchase_id=request.purchase_id,
            product_id="",
            credits_deducted=0,
            old_credits=0,
            new_credits=0,
            message="Refund failed",
            error=str(e)
        )
    except Exception as e:
        logger.error(f"Error refunding purchase {request.purchase_id}: {e}")
        return RefundPurchaseResponse(
            success=False,
            purchase_id=request.purchase_id,
            product_id="",
            credits_deducted=0,
            old_credits=0,
            new_credits=0,
            message="Refund failed",
            error=str(e)
        )


@router.get("/billing/purchases/{user_uid}", response_model=GetPurchaseHistoryResponse)
async def get_purchase_history(
    user_uid: str,
    limit: int = 50
):
    """
    Get user's purchase history
    
    Args:
        user_uid: Firebase User UID
        limit: Maximum number of purchases to return
    
    Returns:
        List of user's purchases
    """
    try:
        purchases = billing_service.get_user_purchases(user_uid, limit)
        
        return GetPurchaseHistoryResponse(
            purchases=purchases,
            count=len(purchases)
        )
        
    except Exception as e:
        logger.error(f"Error getting purchase history for {user_uid}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get purchase history: {str(e)}")


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
        
        # Reject if user not found in database
        if not user_data:
            logger.error(f"User {request.uid} not found in database")
            raise HTTPException(
                status_code=404,
                detail="User not found. Please register first."
            )
        
        subscription = user_data.get("subscription", 0)
        credits = user_data.get("credits", 0)
        
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
    
    # Generate quiz_session_id on server
    quiz_session_id = str(uuid.uuid4())
    
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
                focus_weak_areas=focus_weak_areas,
                quiz_session_id=quiz_session_id
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
                "subject": subject,
                "quiz_session_id": quiz_session_id
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
            focus_weak_areas=focus_weak_areas,
            quiz_session_id=quiz_session_id,
            question_number=None
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
            "subject": subject,
            "quiz_session_id": quiz_session_id
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
    quiz_session_id = request.get('quiz_session_id')  # NEW: Session ID for linking help records
    
    if not uid:
        raise HTTPException(status_code=400, detail="uid is required")
    if not subject_id:
        raise HTTPException(status_code=400, detail="subject_id is required")
    if not evaluations:
        raise HTTPException(status_code=400, detail="evaluations list is required")
    
    try:
        # Check user exists
        user_data = db_service.get_user_by_uid(uid)
        if not user_data:
            raise HTTPException(status_code=404, detail="User not found. Please register first.")
        
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
        
        # Save attempts to database and collect attempt IDs
        attempt_ids = []
        for i, result in enumerate(results):
            try:
                # Get additional info from original evaluation request
                original = evaluations[i] if i < len(evaluations) else {}
                
                attempt_id, created_at = KnowledgeService.save_knowledge_attempt(
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
                    topic=original.get('topic'),
                    quiz_session_id=quiz_session_id
                )
                attempt_ids.append(attempt_id)
                
            except Exception as save_error:
                logger.warning(f"Failed to save attempt: {save_error}")
                attempt_ids.append(None)  # Keep array length consistent
        
        # NEW: Link pre-answer help records using quiz_session_id
        if quiz_session_id:
            try:
                questions = [r.get('question', '') for r in results]
                KnowledgeService.link_help_records_by_session(
                    quiz_session_id=quiz_session_id,
                    attempt_ids=attempt_ids,
                    questions=questions
                )
            except Exception as link_error:
                logger.warning(f"Failed to link help records for session {quiz_session_id}: {link_error}")
        
        # Calculate summary stats
        correct_count = sum(1 for r in results if r.get('status') == 'correct')
        partial_count = sum(1 for r in results if r.get('status') == 'partial')
        incorrect_count = sum(1 for r in results if r.get('status') == 'incorrect')
        total_score = sum(r.get('score', 0) for r in results) / len(results) if results else 0
        
        return {
            "message": "Answers evaluated successfully",
            "evaluations": results,
            "attempt_ids": attempt_ids,  # NEW: Return attempt IDs for frontend
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
    from app.config import HELP_GRADE_REDUCTION
    
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
    attempt_id = request.get('attempt_id')  # Optional: ID of the attempt this help is for
    quiz_session_id = request.get('quiz_session_id')  # NEW: Session ID for linking
    question_number = request.get('question_number')  # NEW: Question number in quiz (1-based)
    requested_help_grade = request.get('help_grade_level')  # NEW: Override grade level for help
    
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
        
        # Get grade level for tone adjustment (user already fetched above)
        student_grade_level = user.get('grade_level') if user else None
        user_help_preference = user.get('help_tone_preference') if user else None
        
        # Calculate help grade level
        # Priority: 1) Explicit request override, 2) User saved preference, 3) Apply reduction, 4) Use student grade
        if requested_help_grade is not None:
            # User explicitly requested a specific grade level
            help_grade_level = max(1, requested_help_grade)  # Ensure minimum grade 1
        elif user_help_preference:
            # User has saved preference - interpret it
            if user_help_preference == 'auto' and student_grade_level:
                # Auto means one grade simpler
                help_grade_level = max(1, student_grade_level - 1)
            elif user_help_preference == 'kid':
                help_grade_level = 'kid'
            elif user_help_preference.isdigit():
                help_grade_level = int(user_help_preference)
            else:
                # Fallback to default if invalid preference
                help_grade_level = student_grade_level
        elif student_grade_level is not None and HELP_GRADE_REDUCTION > 0:
            # Apply grade reduction (e.g., Grade 6 - 1 = Grade 5 explanation)
            help_grade_level = max(1, student_grade_level - HELP_GRADE_REDUCTION)
        else:
            # No reduction, use student's actual grade (or NULL defaults to 'kid')
            help_grade_level = student_grade_level if student_grade_level else 'kid'
        
        # Generate help using AI
        help_result = prompt_service.generate_question_help(
            uid=uid,
            question=question,
            correct_answer=correct_answer,
            subject_id=subject_id,
            subject_name=subject_name,
            user_answer=user_answer,
            has_answered=has_answered,
            visual_preference=visual_preference,
            student_grade_level=help_grade_level  # Use calculated help grade level
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
                used_fallback=used_fallback,
                attempt_id=attempt_id,  # Link help to specific attempt
                quiz_session_id=quiz_session_id,  # NEW: Session ID for grouping
                question_number=question_number  # NEW: Question number in quiz
            )
        except Exception as log_error:
            logger.warning(f"Failed to log help usage: {log_error}")
        
        # Get updated daily count
        daily_count = prompt_service.get_daily_help_count(uid)
        
        # Get human-readable tone description
        if help_grade_level == 'kid':
            help_tone_description = "Simplest (Kid-friendly)"
        elif isinstance(help_grade_level, int):
            help_tone_description = f"Grade {help_grade_level} level"
        else:
            help_tone_description = "Default"
        
        return {
            "message": "Help generated successfully",
            "help_steps": help_result["help_steps"],
            "question_variant": help_result["question_variant"],
            "has_answered": help_result["has_answered"],
            "visual_count": help_result["visual_count"],
            "svg_count": help_result["svg_count"],
            "complexity_assessment": help_result.get("complexity_assessment"),  # NEW: AI-assessed complexity
            "step_count": help_result.get("step_count", len(help_result["help_steps"])),  # NEW: Explicit step count
            "help_tone": help_tone_description,  # NEW: Human-readable tone description
            "credits_remaining": new_credits,
            "daily_help_count": daily_count,
            "student_grade_level": student_grade_level,
            "help_grade_level": help_grade_level,
            "user_help_preference": user_help_preference,
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


@router.post("/generate-question-help/preview")
async def preview_question_help_prompt(request: dict):
    """
    Preview the AI prompt that will be used for help generation WITHOUT calling AI.
    This endpoint is for testing and debugging prompt construction based on grade level.
    
    Does NOT:
    - Call the AI model
    - Consume credits
    - Check subscription limits
    - Log usage
    
    Request body (same as /generate-question-help):
    - uid: str (required) - Firebase User UID (to fetch grade level)
    - question: str (required) - The question text
    - correct_answer: str (required) - Correct answer for context
    - subject_id: int (required) - Subject ID
    - subject_name: str (required) - Subject display name
    - user_answer: str (optional) - User's answer (when has_answered=true)
    - has_answered: bool (optional, default=false) - Whether user answered
    - visual_preference: str (optional, default='text') - 'text', 'json', or 'svg'
    
    Returns:
    - prompt: str - The complete prompt that would be sent to AI
    - grade_level: int - Student's grade level (or None if missing)
    - tone_config: dict - The grade-specific tone configuration used
    - metadata: dict - Additional context about prompt construction
    """
    try:
        from app.repositories.db_service import get_user_by_uid
        from app.repositories.knowledge_service import KnowledgeService
        from app.utils.grade_tone_loader import GradeToneConfig
        from app.config import (
            FF_HELP_VISUAL_JSON_ENABLED,
            FF_HELP_VISUAL_JSON_MAX,
            FF_HELP_VISUAL_SVG_FROM_AI_ENABLED,
            FF_HELP_VISUAL_SVG_FROM_AI_MAX,
            HELP_GRADE_REDUCTION
        )
        
        # Extract request data
        uid = request.get("uid")
        question = request.get("question")
        correct_answer = request.get("correct_answer")
        subject_id = request.get("subject_id")
        subject_name = request.get("subject_name")
        user_answer = request.get("user_answer")
        has_answered = request.get("has_answered", False)
        visual_preference = request.get("visual_preference", "text")
        requested_help_grade = request.get("help_grade_level")  # NEW: Override grade level
        
        # Validation
        if not all([uid, question, correct_answer, subject_id, subject_name]):
            raise HTTPException(
                status_code=400,
                detail="Missing required fields: uid, question, correct_answer, subject_id, subject_name"
            )
        
        # Fetch user to get grade level
        user = get_user_by_uid(uid)
        student_grade_level = user.get('grade_level') if user else None
        user_help_preference = user.get('help_tone_preference') if user else None
        
        # Calculate help grade level (same logic as main endpoint)
        # Priority: 1) Explicit request override, 2) User saved preference, 3) Apply reduction, 4) Use student grade
        if requested_help_grade is not None:
            # User explicitly requested a specific grade level
            help_grade_level = max(1, requested_help_grade)  # Ensure minimum grade 1
        elif user_help_preference:
            # User has saved preference - interpret it
            if user_help_preference == 'auto' and student_grade_level:
                # Auto means one grade simpler
                help_grade_level = max(1, student_grade_level - 1)
            elif user_help_preference == 'kid':
                help_grade_level = 'kid'
            elif user_help_preference.isdigit():
                help_grade_level = int(user_help_preference)
            else:
                # Fallback to default if invalid preference
                help_grade_level = student_grade_level
        elif student_grade_level is not None and HELP_GRADE_REDUCTION > 0:
            # Apply grade reduction (e.g., Grade 6 - 1 = Grade 5 explanation)
            help_grade_level = max(1, student_grade_level - HELP_GRADE_REDUCTION)
        else:
            # No reduction, use student's actual grade (or NULL defaults to 'kid')
            help_grade_level = student_grade_level if student_grade_level else 'kid'
        
        # Get subject for visual limits
        subject = KnowledgeService.get_subject_by_id(subject_id)
        
        if not subject:
            raise HTTPException(status_code=404, detail=f"Subject {subject_id} not found")
        
        # Determine visual limits (same logic as generate_question_help)
        subject_json_max = subject.get('visual_json_max', 3)
        subject_svg_max = subject.get('visual_svg_max', 1)
        
        # Apply global overrides
        final_json_max = min(FF_HELP_VISUAL_JSON_MAX, subject_json_max)
        final_svg_max = min(FF_HELP_VISUAL_SVG_FROM_AI_MAX, subject_svg_max)
        
        # Determine visual requirements based on preference
        if visual_preference == 'text' or not FF_HELP_VISUAL_JSON_ENABLED:
            final_json_max = 0
            final_svg_max = 0
            visual_required = False
            visual_requirement_text = "NOT ALLOWED"
        elif visual_preference == 'json':
            final_svg_max = 0
            visual_required = True
            visual_requirement_text = "JSON REQUIRED"
        elif visual_preference == 'svg':
            if FF_HELP_VISUAL_SVG_FROM_AI_ENABLED:
                final_json_max = 0
                visual_required = True
                visual_requirement_text = "SVG REQUIRED"
            else:
                final_json_max = 0
                final_svg_max = 0
                visual_required = False
                visual_requirement_text = "SVG DISABLED"
        else:
            visual_required = False
            visual_requirement_text = "OPTIONAL"
        
        # Build visual instructions (same as in prompt_service.py)
        if final_json_max == 0 and final_svg_max == 0:
            visual_instructions = """
**Visual Aids** (NOT ALLOWED):
Do NOT include any visual aids. Provide text-only explanations.
"""
        else:
            visual_instructions = f"""
**Visual Aids** ({visual_requirement_text}):
You {"MUST" if visual_required else "may"} include up to {final_json_max} JSON-based visual aids and up to {final_svg_max} AI-generated SVG aids.

For JSON visuals (frontend renders these):
- Shape primitives: {{"type": "circle", "data": {{"cx": 50, "cy": 50, "r": 30, "fill": "blue"}}}}
- Available types: circle, rectangle, line, polygon, text, path
- Use simple, clear visuals that genuinely aid understanding
- Each visual should be attached to the step where it's most helpful

{"For AI-generated SVG:" if final_svg_max > 0 else ""}
{"- Include complete SVG element with viewBox, proper dimensions" if final_svg_max > 0 else ""}
{"- Keep it simple and educational (diagrams, charts, simple illustrations)" if final_svg_max > 0 else ""}
{"- Use clear colors and labels" if final_svg_max > 0 else ""}

**CRITICAL**: Only use visuals when they genuinely help understanding. Do NOT use them as decoration.
"""
        
        # Determine prompt mode
        if has_answered and user_answer:
            prompt_mode = "POST-ANSWER MODE: Student answered INCORRECTLY"
            question_instruction = f"The student's incorrect answer was: {user_answer}. Focus on why this is wrong and how to get the correct answer."
        else:
            prompt_mode = "PRE-ANSWER MODE: Student needs help BEFORE answering"
            question_instruction = "Generate a SIMILAR question (different numbers/scenario) and explain how to solve it. This helps them learn without giving away the exact answer."
        
        # Get grade-specific tone instruction
        tone_config = GradeToneConfig.get_tone_for_grade(help_grade_level)
        tone_instruction = tone_config.get('tone_instruction', '')
        
        # Build the complete prompt (same as in prompt_service.py lines 769-809)
        prompt = f"""You are an expert {subject_name} tutor helping a student understand a question.

**{prompt_mode}**
{question_instruction}

**Question:** {question}
**Correct Answer:** {correct_answer}

{visual_instructions}

**Response Format (valid JSON only):**
{{
  "question_variant": "{question if has_answered else 'your newly generated similar question'}",
  "help_steps": [
    {{
      "step_number": 1,
      "explanation": "**Step 1: Understanding the Problem**\\n\\nMarkdown-formatted explanation..."
    }},
    {{
      "step_number": 2,
      "explanation": "**Step 2: Key Concept**\\n\\nMore markdown...",
      "visual": {{  // OPTIONAL - only if genuinely helpful
        "type": "json_shape",
        "data": {{...}}
      }}
    }}
  ]
}}

**Quality Guidelines:**
1. {tone_instruction}
2. Break down into 3-5 logical steps
3. Include markdown formatting: **bold**, *italic*, bullet points, numbered lists
4. Highlight key concepts and common mistakes
5. End with a summary/takeaway
6. Visuals: ONLY use when they genuinely aid understanding (not decorative)
7. Avoid overwhelming the student - keep it focused and concise
8. {"CRITICAL: In 'question_variant' field, generate a SIMILAR question with different numbers/scenario. DO NOT copy the original question!" if not has_answered else "CRITICAL: In 'question_variant' field, copy the exact question text provided above word-for-word. Do NOT write 'EXACT' or any placeholder."}

Return ONLY the JSON object, no additional text.
"""
        
        # Return preview data
        return {
            "prompt": prompt,
            "student_grade_level": student_grade_level,
            "help_grade_level": help_grade_level,
            "user_help_preference": user_help_preference,
            "tone_config": tone_config,
            "metadata": {
                "subject_id": subject_id,
                "subject_name": subject_name,
                "has_answered": has_answered,
                "visual_preference": visual_preference,
                "grade_reduction_applied": HELP_GRADE_REDUCTION if requested_help_grade is None and not user_help_preference else 0,
                "requested_help_grade": requested_help_grade,
                "visual_limits": {
                    "json_max": final_json_max,
                    "svg_max": final_svg_max,
                    "subject_json_max": subject_json_max,
                    "subject_svg_max": subject_svg_max,
                    "global_json_max": FF_HELP_VISUAL_JSON_MAX,
                    "global_svg_max": FF_HELP_VISUAL_SVG_FROM_AI_MAX
                },
                "mode": prompt_mode,
                "tone_instruction": tone_instruction,
                "default_grade_fallback": student_grade_level is None
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error previewing help prompt: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to preview prompt: {str(e)}")


@router.get("/knowledge/sessions")
async def get_knowledge_sessions(
    uid: str,
    subject_id: int = None,
    limit: int = 50
):
    """
    Get a list of unique knowledge quiz sessions for a user.
    Sessions are grouped by timestamp (within ±10 seconds).
    
    Query parameters:
    - uid: str (required) - Firebase User UID
    - subject_id: int (optional) - Filter by subject
    - limit: int (optional, default=50) - Max sessions to return
    
    Returns:
    - sessions: List of session metadata objects with:
        - session_id: int - Representative ID
        - session_timestamp: datetime - Session start time
        - subject_id: int
        - subject_name: str
        - subject_display_name: str
        - subject_icon: str
        - subject_color: str
        - total_questions: int
        - correct_count: int
        - partial_count: int
        - incorrect_count: int
        - average_score: float
    """
    from app.repositories.knowledge_service import KnowledgeService
    
    if not uid:
        raise HTTPException(status_code=400, detail="uid is required")
    
    try:
        sessions = KnowledgeService.get_user_attempt_sessions(
            uid=uid,
            subject_id=subject_id,
            limit=limit
        )
        
        return {
            "message": "Sessions retrieved successfully",
            "sessions": sessions
        }
        
    except Exception as e:
        logger.error(f"Error retrieving knowledge sessions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve sessions: {str(e)}")


@router.get("/knowledge/attempts")
async def get_knowledge_attempts(
    uid: str,
    quiz_session_id: str = None,
    subject_id: int = None
):
    """
    Get knowledge quiz attempts for a user.
    Can retrieve attempts from a specific session or all attempts.
    
    Query parameters:
    - uid: str (required) - Firebase User UID
    - quiz_session_id: str (optional) - Session ID to get specific session
    - subject_id: int (optional) - Filter by subject
    
    Returns:
    - attempts: List of attempt objects with help data included
    """
    from app.repositories.knowledge_service import KnowledgeService
    
    if not uid:
        raise HTTPException(status_code=400, detail="uid is required")
    
    try:
        if quiz_session_id:
            # Get specific session attempts
            attempts = KnowledgeService.get_attempts_by_session(
                uid=uid,
                quiz_session_id=quiz_session_id,
                subject_id=subject_id
            )
        else:
            # Get all attempts (legacy method, limited to 20)
            attempts = KnowledgeService.get_user_knowledge_attempts(
                uid=uid,
                subject_id=subject_id,
                limit=20
            )
        
        return {
            "message": "Attempts retrieved successfully",
            "attempts": attempts
        }
        
    except Exception as e:
        logger.error(f"Error retrieving knowledge attempts: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve attempts: {str(e)}")


@router.get("/knowledge/attempts/{attempt_id}")
async def get_knowledge_attempt(
    attempt_id: int,
    uid: str
):
    """
    Get a single knowledge attempt by ID with help data.
    
    Path parameters:
    - attempt_id: int - ID of the attempt
    
    Query parameters:
    - uid: str (required) - Firebase User UID (for security)
    
    Returns:
    - attempt: Full attempt object with:
        - All attempt fields (question, answers, evaluation, etc.)
        - help_response: str - Saved help response JSON
        - help_request: str - Help request prompt
        - help_model: str - AI model used for help
        - help_generation_time: int - Help generation time in ms
    """
    from app.repositories.knowledge_service import KnowledgeService
    
    if not uid:
        raise HTTPException(status_code=400, detail="uid is required")
    
    try:
        attempt = KnowledgeService.get_attempt_by_id(
            attempt_id=attempt_id,
            uid=uid
        )
        
        if not attempt:
            raise HTTPException(status_code=404, detail="Attempt not found")
        
        return {
            "message": "Attempt retrieved successfully",
            "attempt": attempt
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving attempt {attempt_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve attempt: {str(e)}")


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
        
        # Check user exists
        user_data = db_service.get_user_by_uid(score.uid)
        if not user_data:
            raise HTTPException(status_code=404, detail="User not found. Please register first.")
        
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
# Performance Reports Endpoints
# ============================================================================

@router.get("/performance-report-history/{uid}")
async def get_performance_reports(uid: str):
    """
    Get all performance reports for a student
    Returns list of reports ordered by creation date (newest first)
    """
    try:
        reports = db_service.get_performance_reports(uid)
        return {
            "success": True,
            "student_uid": uid,
            "reports": reports,
            "count": len(reports)
        }
    except Exception as e:
        logger.error(f"Error fetching performance reports: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch performance reports: {str(e)}")


@router.get("/performance-reports/{uid}/latest")
async def get_latest_performance_report(uid: str):
    """
    Get the most recent performance report for a student
    """
    try:
        report = db_service.get_latest_performance_report(uid)
        if not report:
            raise HTTPException(status_code=404, detail="No performance reports found for this user")
        
        return {
            "success": True,
            "student_uid": uid,
            "report": report
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching latest performance report: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch latest performance report: {str(e)}")


@router.get("/performance-report/{uid}/check-availability")
async def check_performance_report_availability(uid: str):
    """
    Check if a performance report can be generated for a student
    Verifies:
    - Student exists
    - Has sufficient learning data (attempts)
    - Neo4j is available (if needed)
    """
    try:
        # Check if user exists
        user_data = db_service.get_user_by_uid(uid)
        if not user_data:
            return {
                "success": True,
                "student_uid": uid,
                "can_generate_report": False,
                "student_exists": False,
                "attempts_count": 0,
                "sufficient_data": False,
                "neo4j_available": False,
                "message": "Student not found",
                "timestamp": datetime.now(UTC).isoformat()
            }
        
        # Count student's attempts across all question types
        conn = db_service.db_factory.get_provider()._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT COUNT(*) FROM attempts WHERE uid = %s
        """, (uid,))
        attempts_count = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        
        # Require minimum 10 attempts for meaningful analysis
        sufficient_data = attempts_count >= 10
        
        # For now, assume Neo4j availability = True (agentic service handles this)
        neo4j_available = True
        
        can_generate = sufficient_data and neo4j_available
        
        message = "Report generation available"
        if not sufficient_data:
            message = f"Insufficient data: {attempts_count} attempts (minimum 10 required)"
        elif not neo4j_available:
            message = "Analysis service temporarily unavailable"
        
        return {
            "success": True,
            "student_uid": uid,
            "can_generate_report": can_generate,
            "student_exists": True,
            "attempts_count": attempts_count,
            "sufficient_data": sufficient_data,
            "neo4j_available": neo4j_available,
            "message": message,
            "timestamp": datetime.now(UTC).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error checking report availability: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to check report availability: {str(e)}")
