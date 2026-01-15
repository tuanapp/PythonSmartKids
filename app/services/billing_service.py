"""
Google Play Billing Service
Handles purchase verification, subscription management, and credit allocation
"""
import json
import logging
import base64
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.config import GOOGLE_PLAY_SERVICE_ACCOUNT_JSON, GOOGLE_PLAY_PACKAGE_NAME
from app.db.db_factory import DatabaseFactory

logger = logging.getLogger(__name__)

# Product SKU to subscription level mapping
SKU_TO_SUBSCRIPTION_LEVEL = {
    'monthly_premium': 2,
    # 'yearly_premium': 2,
    # 'yearly_family': 3,
}

# Credits granted with subscription purchase/renewal
SUBSCRIPTION_CREDIT_BONUS = {
    'monthly_premium': 500,   # 500 credits per month
    # 'yearly_premium': 1200,   # 1200 credits per year (100/month * 12)
    # 'yearly_family': 2000,    # 2000 credits per year for family plan
}

# Credit expiry period (in days) for each subscription type
SUBSCRIPTION_CREDIT_EXPIRY_DAYS = {
    'monthly_premium': 30,    # Monthly credits expire in 30 days
    # 'yearly_premium': 365,    # Yearly credits expire in 1 year
    # 'yearly_family': 365,     # Family credits expire in 1 year
}

# Product SKU to credit amount mapping (one-time purchases - NO EXPIRY)
SKU_TO_CREDIT_AMOUNT = {
    'credits_1': 1,
    'credits_25': 25,
    # 'credits_50': 50,
    # 'credits_100': 100,
    # 'credits_500': 500,
}


class GooglePlayBillingService:
    """Service for Google Play billing operations"""
    
    def __init__(self):
        self.db_provider = DatabaseFactory.get_provider()
        self.package_name = GOOGLE_PLAY_PACKAGE_NAME
        self.publisher_api = None
        self._init_attempted = False
        self._initialize_api()
    
    def _ensure_initialized(self):
        """Ensure API is initialized (lazy initialization for serverless environments)"""
        if not self._init_attempted or (not self.publisher_api and GOOGLE_PLAY_SERVICE_ACCOUNT_JSON):
            self._initialize_api()
    
    def _initialize_api(self):
        """Initialize Google Play Developer API client"""
        self._init_attempted = True
        try:
            if not GOOGLE_PLAY_SERVICE_ACCOUNT_JSON:
                logger.warning("GOOGLE_PLAY_SERVICE_ACCOUNT_JSON not configured")
                return
            
            # Decode base64 service account JSON with automatic padding correction
            # Add padding if missing (common issue when copying base64 strings)
            encoded = GOOGLE_PLAY_SERVICE_ACCOUNT_JSON.strip()
            padding_needed = len(encoded) % 4
            if padding_needed:
                encoded += '=' * (4 - padding_needed)
            
            service_account_json = base64.b64decode(encoded).decode('utf-8')
            service_account_info = json.loads(service_account_json)
            
            # Create credentials
            credentials = service_account.Credentials.from_service_account_info(
                service_account_info,
                scopes=['https://www.googleapis.com/auth/androidpublisher']
            )
            
            # Build the API client
            self.publisher_api = build('androidpublisher', 'v3', credentials=credentials)
            logger.info("Google Play Developer API initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Google Play API: {e}", exc_info=True)
            self.publisher_api = None
    
    def verify_subscription_purchase(
        self,
        product_id: str,
        purchase_token: str
    ) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Verify a subscription purchase with Google Play
        
        Returns:
            (is_valid, purchase_data, error_message)
        """
        self._ensure_initialized()
        if not self.publisher_api:
            return False, None, "Google Play API not initialized"
        
        try:
            result = self.publisher_api.purchases().subscriptions().get(
                packageName=self.package_name,
                subscriptionId=product_id,
                token=purchase_token
            ).execute()
            
            # Check if subscription is valid and active
            expiry_time_millis = int(result.get('expiryTimeMillis', 0))
            is_active = expiry_time_millis > int(datetime.now().timestamp() * 1000)
            
            purchase_data = {
                'order_id': result.get('orderId'),
                'purchase_time': int(result.get('startTimeMillis', 0)),
                'expiry_time': expiry_time_millis,
                'auto_renewing': result.get('autoRenewing', False),
                'payment_state': result.get('paymentState', 0),
                'purchase_type': result.get('purchaseType', 0),
                'acknowledgement_state': result.get('acknowledgementState', 0),
                'raw_data': result
            }
            
            return is_active, purchase_data, None
            
        except HttpError as e:
            logger.error(f"Google Play API error verifying subscription: {e}")
            return False, None, f"API error: {e.resp.status}"
        except Exception as e:
            logger.error(f"Error verifying subscription purchase: {e}")
            return False, None, str(e)
    
    def verify_product_purchase(
        self,
        product_id: str,
        purchase_token: str
    ) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Verify a one-time product purchase with Google Play
        
        Returns:
            (is_valid, purchase_data, error_message)
        """
        self._ensure_initialized()
        if not self.publisher_api:
            return False, None, "Google Play API not initialized"
        
        try:
            result = self.publisher_api.purchases().products().get(
                packageName=self.package_name,
                productId=product_id,
                token=purchase_token
            ).execute()
            
            # Check purchase state (0 = purchased, 1 = cancelled, 2 = pending)
            purchase_state = result.get('purchaseState', 2)
            is_valid = purchase_state == 0
            
            purchase_data = {
                'order_id': result.get('orderId'),
                'purchase_time': int(result.get('purchaseTimeMillis', 0)),
                'purchase_state': purchase_state,
                'consumption_state': result.get('consumptionState', 0),
                'acknowledgement_state': result.get('acknowledgementState', 0),
                'raw_data': result
            }
            
            return is_valid, purchase_data, None
            
        except HttpError as e:
            logger.error(f"Google Play API error verifying product: {e}")
            return False, None, f"API error: {e.resp.status}"
        except Exception as e:
            logger.error(f"Error verifying product purchase: {e}")
            return False, None, str(e)
    
    def save_purchase_record(
        self,
        uid: str,
        product_id: str,
        purchase_token: str,
        purchase_data: Dict[str, Any],
        auto_renewing: Optional[bool] = None
    ) -> int:
        """
        Save or update purchase record in database
        
        Returns:
            purchase_id
        """
        conn = self.db_provider._get_connection()
        cursor = conn.cursor()
        
        try:
            # Check if purchase already exists
            cursor.execute("""
                SELECT id FROM google_play_purchases 
                WHERE purchase_token = %s
            """, (purchase_token,))
            
            existing = cursor.fetchone()
            
            purchase_time = datetime.fromtimestamp(purchase_data['purchase_time'] / 1000)
            purchase_state = purchase_data.get('purchase_state', 0)
            acknowledged = purchase_data.get('acknowledgement_state', 0) == 1
            
            if existing:
                # Update existing record
                purchase_id = existing[0]
                cursor.execute("""
                    UPDATE google_play_purchases 
                    SET purchase_state = %s,
                        acknowledged = %s,
                        auto_renewing = %s,
                        raw_receipt = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                """, (
                    purchase_state,
                    acknowledged,
                    auto_renewing,
                    json.dumps(purchase_data['raw_data']),
                    purchase_id
                ))
                logger.info(f"Updated purchase record {purchase_id}")
            else:
                # Insert new record
                cursor.execute("""
                    INSERT INTO google_play_purchases 
                    (uid, purchase_token, product_id, order_id, purchase_time, 
                     purchase_state, acknowledged, auto_renewing, raw_receipt)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    uid,
                    purchase_token,
                    product_id,
                    purchase_data['order_id'],
                    purchase_time,
                    purchase_state,
                    acknowledged,
                    auto_renewing,
                    json.dumps(purchase_data['raw_data'])
                ))
                purchase_id = cursor.fetchone()[0]
                logger.info(f"Created purchase record {purchase_id}")
            
            conn.commit()
            return purchase_id
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Error saving purchase record: {e}")
            raise
        finally:
            cursor.close()
            conn.close()
    
    def process_subscription_purchase(
        self,
        uid: str,
        product_id: str,
        purchase_id: int
    ) -> Dict[str, Any]:
        """
        Process a subscription purchase - update user subscription level and grant credits with expiry
        
        Returns:
            Processing result
        """
        subscription_level = SKU_TO_SUBSCRIPTION_LEVEL.get(product_id)
        if subscription_level is None:
            raise ValueError(f"Unknown subscription product: {product_id}")
        
        # Get credit bonus and expiry period for this subscription
        credit_bonus = SUBSCRIPTION_CREDIT_BONUS.get(product_id, 0)
        expiry_days = SUBSCRIPTION_CREDIT_EXPIRY_DAYS.get(product_id, 30)
        
        conn = self.db_provider._get_connection()
        cursor = conn.cursor()
        
        try:
            # Get current subscription level and credits
            cursor.execute("SELECT subscription, credits FROM users WHERE uid = %s", (uid,))
            result = cursor.fetchone()
            if not result:
                raise ValueError(f"User not found: {uid}")
            
            old_subscription = result[0]
            old_credits = result[1] or 0
            new_credits = old_credits + credit_bonus
            
            # Calculate expiry date for credits
            from datetime import datetime, timedelta
            credits_expire_at = datetime.now() + timedelta(days=expiry_days)
            
            # Update user subscription level, add credits, and set expiry
            cursor.execute("""
                UPDATE users 
                SET subscription = %s, 
                    credits = %s,
                    credits_expire_at = %s
                WHERE uid = %s
            """, (subscription_level, new_credits, credits_expire_at, uid))
            
            # Log subscription history with credit grant and expiry
            cursor.execute("""
                INSERT INTO subscription_history 
                (uid, purchase_id, event, old_subscription, new_subscription, credits_granted, expiry_date, notes)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                uid,
                purchase_id,
                'STARTED',
                old_subscription,
                subscription_level,
                credit_bonus,
                credits_expire_at,
                f'Activated {product_id} - granted {credit_bonus} credits (expires in {expiry_days} days)'
            ))
            
            conn.commit()
            
            logger.info(f"Updated user {uid} subscription from {old_subscription} to {subscription_level}, granted {credit_bonus} credits (expires {credits_expire_at})")
            
            return {
                'success': True,
                'old_subscription': old_subscription,
                'new_subscription': subscription_level,
                'old_credits': old_credits,
                'new_credits': new_credits,
                'credits_granted': credit_bonus
            }
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Error processing subscription purchase: {e}")
            raise
        finally:
            cursor.close()
            conn.close()
    
    def process_credit_pack_purchase(
        self,
        uid: str,
        product_id: str,
        purchase_id: int
    ) -> Dict[str, Any]:
        """
        Process a credit pack purchase - add credits to user account
        
        Returns:
            Processing result
        """
        credit_amount = SKU_TO_CREDIT_AMOUNT.get(product_id)
        if credit_amount is None:
            raise ValueError(f"Unknown credit pack product: {product_id}")
        
        conn = self.db_provider._get_connection()
        cursor = conn.cursor()
        
        try:
            # Get current credits
            cursor.execute("SELECT credits FROM users WHERE uid = %s", (uid,))
            result = cursor.fetchone()
            if not result:
                raise ValueError(f"User not found: {uid}")
            
            old_credits = result[0]
            new_credits = old_credits + credit_amount
            
            # Update user credits
            cursor.execute("""
                UPDATE users 
                SET credits = %s 
                WHERE uid = %s
            """, (new_credits, uid))
            
            # Log subscription history (for credit purchases too)
            cursor.execute("""
                INSERT INTO subscription_history 
                (uid, purchase_id, event, old_subscription, new_subscription, credits_granted, notes)
                VALUES (%s, %s, %s, NULL, NULL, %s, %s)
            """, (
                uid,
                purchase_id,
                'CREDIT_PURCHASE',
                credit_amount,
                f'Purchased {product_id}'
            ))
            
            conn.commit()
            
            logger.info(f"Added {credit_amount} credits to user {uid} (old: {old_credits}, new: {new_credits})")
            
            return {
                'success': True,
                'old_credits': old_credits,
                'new_credits': new_credits,
                'credits_granted': credit_amount
            }
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Error processing credit pack purchase: {e}")
            raise
        finally:
            cursor.close()
            conn.close()
    
    def get_user_purchases(self, uid: str, limit: int = 50) -> list:
        """Get user's purchase history"""
        conn = self.db_provider._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT id, product_id, order_id, purchase_time, purchase_state, 
                       acknowledged, auto_renewing, created_at
                FROM google_play_purchases 
                WHERE uid = %s 
                ORDER BY purchase_time DESC 
                LIMIT %s
            """, (uid, limit))
            
            purchases = []
            for row in cursor.fetchall():
                purchases.append({
                    'id': row[0],
                    'product_id': row[1],
                    'order_id': row[2],
                    'purchase_time': row[3].isoformat() if row[3] else None,
                    'purchase_state': row[4],
                    'acknowledged': row[5],
                    'auto_renewing': row[6],
                    'created_at': row[7].isoformat() if row[7] else None,
                })
            
            return purchases
            
        finally:
            cursor.close()
            conn.close()
    
    def cancel_subscription(
        self,
        uid: str,
        purchase_id: int,
        reason: str = "User cancelled"
    ) -> Dict[str, Any]:
        """
        Handle subscription cancellation
        Downgrade user to free tier
        """
        conn = self.db_provider._get_connection()
        cursor = conn.cursor()
        
        try:
            # Get current subscription
            cursor.execute("SELECT subscription FROM users WHERE uid = %s", (uid,))
            result = cursor.fetchone()
            if not result:
                raise ValueError(f"User not found: {uid}")
            
            old_subscription = result[0]
            
            # Downgrade to free tier (0)
            cursor.execute("""
                UPDATE users 
                SET subscription = 0 
                WHERE uid = %s
            """, (uid,))
            
            # Log subscription history
            cursor.execute("""
                INSERT INTO subscription_history 
                (uid, purchase_id, event, old_subscription, new_subscription, credits_granted, notes)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                uid,
                purchase_id,
                'CANCELLED',
                old_subscription,
                0,
                0,
                reason
            ))
            
            conn.commit()
            
            logger.info(f"Cancelled subscription for user {uid}: {old_subscription} -> 0")
            
            return {
                'success': True,
                'old_subscription': old_subscription,
                'new_subscription': 0
            }
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Error cancelling subscription: {e}")
            raise
        finally:
            cursor.close()
            conn.close()


# Global instance
billing_service = GooglePlayBillingService()
