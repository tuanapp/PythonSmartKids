"""
Credit Expiry Service
Handles automatic expiration of premium subscription credits
"""
import logging
from datetime import datetime
from typing import Dict, Any, List
from app.db.db_factory import DatabaseFactory

logger = logging.getLogger(__name__)


class CreditExpiryService:
    """Service for managing credit expiry and cleanup"""
    
    def __init__(self):
        self.db_provider = DatabaseFactory.get_provider()
    
    def expire_credits(self) -> Dict[str, Any]:
        """
        Expire credits for users whose credits_expire_at has passed
        
        Returns:
            Dictionary with results of expiry operation
        """
        try:
            conn = self.db_provider._get_connection()
            cursor = conn.cursor()
            
            # Find users with expired credits
            cursor.execute("""
                SELECT uid, credits, credits_expire_at 
                FROM users 
                WHERE credits_expire_at < NOW() 
                AND credits > 0
            """)
            
            expired_users = cursor.fetchall()
            expired_count = len(expired_users)
            
            if expired_count == 0:
                logger.info("No expired credits found")
                cursor.close()
                conn.close()
                return {
                    'success': True,
                    'expired_count': 0,
                    'message': 'No expired credits found'
                }
            
            # Log each user's credit expiration to subscription_history
            for uid, credits, expire_at in expired_users:
                cursor.execute("""
                    INSERT INTO subscription_history 
                    (uid, purchase_id, event, old_subscription, new_subscription, credits_granted, notes)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    uid,
                    None,
                    'CREDITS_EXPIRED',
                    None,
                    None,
                    -credits,  # Negative to indicate removal
                    f'Expired {credits} credits (expire date: {expire_at})'
                ))
                logger.info(f"Logged credit expiration for user {uid}: {credits} credits")
            
            # Reset credits to 0 for all expired users
            cursor.execute("""
                UPDATE users 
                SET credits = 0, 
                    credits_expire_at = NULL 
                WHERE credits_expire_at < NOW() 
                AND credits > 0
            """)
            
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info(f"Expired credits for {expired_count} users")
            
            return {
                'success': True,
                'expired_count': expired_count,
                'message': f'Expired credits for {expired_count} users'
            }
            
        except Exception as e:
            logger.error(f"Error expiring credits: {e}")
            return {
                'success': False,
                'error': str(e),
                'expired_count': 0
            }
    
    def get_expiring_soon(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        Get users whose credits will expire within the specified number of days
        
        Args:
            days: Number of days to look ahead (default: 7)
            
        Returns:
            List of users with expiring credits
        """
        try:
            conn = self.db_provider._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT uid, email, credits, credits_expire_at 
                FROM users 
                WHERE credits_expire_at IS NOT NULL 
                AND credits > 0
                AND credits_expire_at > NOW()
                AND credits_expire_at <= NOW() + INTERVAL '%s days'
                ORDER BY credits_expire_at ASC
            """, (days,))
            
            results = cursor.fetchall()
            cursor.close()
            conn.close()
            
            users = []
            for row in results:
                users.append({
                    'uid': row[0],
                    'email': row[1],
                    'credits': row[2],
                    'credits_expire_at': row[3].isoformat() if row[3] else None
                })
            
            return users
            
        except Exception as e:
            logger.error(f"Error getting expiring credits: {e}")
            return []


# Global instance
credit_expiry_service = CreditExpiryService()
