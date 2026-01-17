"""
Firebase Cloud Messaging (FCM) Service
Handles push notifications for credit updates and other real-time events
"""
import logging
import os
import json
import base64
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import time

try:
    import firebase_admin
    from firebase_admin import credentials, messaging
    FCM_AVAILABLE = True
except ImportError:
    FCM_AVAILABLE = False

from app.db.db_factory import DatabaseFactory

logger = logging.getLogger(__name__)


class FCMService:
    """Service for sending Firebase Cloud Messaging push notifications"""
    
    def __init__(self):
        self.db_provider = DatabaseFactory.get_provider()
        self._initialized = False
        self._init_error = None
        
        # Initialize Firebase Admin SDK
        if FCM_AVAILABLE:
            try:
                self._initialize_firebase()
            except Exception as e:
                logger.error(f"Failed to initialize Firebase Admin SDK: {e}")
                self._init_error = str(e)
        else:
            logger.warning("firebase-admin package not installed - FCM notifications disabled")
            self._init_error = "firebase-admin not installed"
    
    def _initialize_firebase(self):
        """Initialize Firebase Admin SDK with service account credentials"""
        try:
            # Check if already initialized
            if firebase_admin._apps:
                self._initialized = True
                logger.info("Firebase Admin SDK already initialized")
                return
            
            # Get service account JSON from environment (base64 encoded)
            service_account_b64 = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON", "")
            
            if not service_account_b64:
                raise ValueError("FIREBASE_SERVICE_ACCOUNT_JSON environment variable not set")
            
            # Decode base64 service account JSON
            service_account_json = base64.b64decode(service_account_b64).decode('utf-8')
            service_account_dict = json.loads(service_account_json)
            
            # Initialize Firebase Admin SDK
            cred = credentials.Certificate(service_account_dict)
            firebase_admin.initialize_app(cred)
            
            self._initialized = True
            logger.info("Firebase Admin SDK initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing Firebase Admin SDK: {e}")
            self._initialized = False
            self._init_error = str(e)
            raise
    
    def is_available(self) -> bool:
        """Check if FCM service is available"""
        return FCM_AVAILABLE and self._initialized
    
    async def send_credit_notification(
        self,
        uid: str,
        old_credits: int,
        new_credits: int,
        is_upgrade: bool = True,
        max_retries: int = 2
    ) -> Dict[str, Any]:
        """
        Send credit update notification to all user's active devices
        
        Args:
            uid: User UID
            old_credits: Credits before update
            new_credits: Credits after update
            is_upgrade: True if credits increased (admin addition), False if decreased
            max_retries: Maximum retry attempts (default: 2)
        
        Returns:
            Dictionary with success status and results
        """
        if not self.is_available():
            return {
                'success': False,
                'error': f'FCM service not available: {self._init_error}',
                'sent_count': 0
            }
        
        try:
            # Get active devices for user (last seen within 60 days)
            devices = self._get_active_devices(uid, days=60)
            
            if not devices:
                logger.info(f"No active devices found for user {uid}")
                return {
                    'success': True,
                    'sent_count': 0,
                    'message': 'No active devices'
                }
            
            # Prepare notification data
            data_payload = {
                'type': 'credit_update',
                'old_credits': str(old_credits),
                'new_credits': str(new_credits),
                'is_upgrade': str(is_upgrade),
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # Send to all devices with retry logic
            results = []
            for device in devices:
                result = await self._send_to_device(
                    device['fcm_token'],
                    data_payload,
                    device['device_id'],
                    max_retries
                )
                results.append(result)
                
                # Clean up invalid tokens
                if not result['success'] and result.get('invalid_token'):
                    self._mark_token_invalid(device['id'])
            
            success_count = sum(1 for r in results if r['success'])
            
            logger.info(f"Sent credit notification to {success_count}/{len(devices)} devices for user {uid}")
            
            return {
                'success': True,
                'sent_count': success_count,
                'total_devices': len(devices),
                'results': results
            }
            
        except Exception as e:
            logger.error(f"Error sending credit notification: {e}")
            return {
                'success': False,
                'error': str(e),
                'sent_count': 0
            }
    
    async def _send_to_device(
        self,
        fcm_token: str,
        data: Dict[str, str],
        device_id: str,
        max_retries: int
    ) -> Dict[str, Any]:
        """
        Send notification to a single device with retry logic
        
        Args:
            fcm_token: FCM device token
            data: Data payload
            device_id: Device identifier (for logging)
            max_retries: Maximum retry attempts
        
        Returns:
            Result dictionary with success status
        """
        retry_count = 0
        last_error = None
        
        while retry_count <= max_retries:
            try:
                # Create silent data message (no notification UI)
                message = messaging.Message(
                    data=data,
                    token=fcm_token,
                    android=messaging.AndroidConfig(
                        priority='high',
                        # Silent notification - app handles in background
                        data=data
                    )
                )
                
                # Send message
                response = messaging.send(message)
                
                logger.info(f"FCM notification sent to device {device_id}: {response}")
                
                return {
                    'success': True,
                    'device_id': device_id,
                    'message_id': response
                }
                
            except messaging.UnregisteredError:
                # Token is invalid - don't retry
                logger.warning(f"Invalid FCM token for device {device_id}")
                return {
                    'success': False,
                    'device_id': device_id,
                    'error': 'Invalid token',
                    'invalid_token': True
                }
                
            except Exception as e:
                last_error = str(e)
                retry_count += 1
                
                if retry_count <= max_retries:
                    # Exponential backoff: 1s, 2s
                    wait_time = retry_count
                    logger.warning(f"FCM send failed for device {device_id}, retry {retry_count}/{max_retries} in {wait_time}s: {e}")
                    time.sleep(wait_time)
                else:
                    logger.error(f"FCM send failed for device {device_id} after {max_retries} retries: {e}")
        
        return {
            'success': False,
            'device_id': device_id,
            'error': last_error,
            'retries': retry_count - 1
        }
    
    def _get_active_devices(self, uid: str, days: int = 60) -> List[Dict[str, Any]]:
        """
        Get active devices for a user
        
        Args:
            uid: User UID
            days: Number of days to consider as "active"
        
        Returns:
            List of device records
        """
        try:
            conn = self.db_provider._get_connection()
            cursor = conn.cursor()
            
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            cursor.execute("""
                SELECT id, device_id, fcm_token, last_seen_at
                FROM user_devices
                WHERE user_id = %s
                  AND is_enabled = TRUE
                  AND fcm_token IS NOT NULL
                  AND last_seen_at > %s
                ORDER BY last_seen_at DESC
            """, (uid, cutoff_date))
            
            rows = cursor.fetchall()
            cursor.close()
            conn.close()
            
            return [
                {
                    'id': row[0],
                    'device_id': row[1],
                    'fcm_token': row[2],
                    'last_seen_at': row[3]
                }
                for row in rows
            ]
            
        except Exception as e:
            logger.error(f"Error getting active devices: {e}")
            return []
    
    def _mark_token_invalid(self, device_id: int):
        """Mark a device token as invalid"""
        try:
            conn = self.db_provider._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE user_devices
                SET is_enabled = FALSE,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (device_id,))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info(f"Marked device {device_id} token as invalid")
            
        except Exception as e:
            logger.error(f"Error marking token invalid: {e}")
    
    def register_device_token(
        self,
        uid: str,
        device_id: str,
        fcm_token: str,
        platform: str = 'android'
    ) -> Dict[str, Any]:
        """
        Register or update FCM token for a device
        
        Args:
            uid: User UID
            device_id: Stable device identifier
            fcm_token: FCM registration token
            platform: Device platform (default: 'android')
        
        Returns:
            Result dictionary
        """
        try:
            conn = self.db_provider._get_connection()
            cursor = conn.cursor()
            
            # Upsert device record
            cursor.execute("""
                INSERT INTO user_devices 
                (user_id, device_id, platform, fcm_token, last_seen_at, last_token_sync_at, is_enabled)
                VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, TRUE)
                ON CONFLICT (user_id, device_id)
                DO UPDATE SET
                    fcm_token = EXCLUDED.fcm_token,
                    platform = EXCLUDED.platform,
                    last_seen_at = CURRENT_TIMESTAMP,
                    last_token_sync_at = CURRENT_TIMESTAMP,
                    is_enabled = TRUE,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING id
            """, (uid, device_id, platform, fcm_token))
            
            device_record_id = cursor.fetchone()[0]
            
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info(f"Registered FCM token for user {uid}, device {device_id}")
            
            return {
                'success': True,
                'device_id': device_record_id,
                'message': 'Token registered successfully'
            }
            
        except Exception as e:
            logger.error(f"Error registering device token: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def update_device_last_seen(self, uid: str, device_id: str):
        """Update last_seen_at for a device"""
        try:
            conn = self.db_provider._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE user_devices
                SET last_seen_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = %s AND device_id = %s
            """, (uid, device_id))
            
            conn.commit()
            cursor.close()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error updating device last seen: {e}")


# Global instance
fcm_service = FCMService()
