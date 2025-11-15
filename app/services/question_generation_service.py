"""Service for tracking question generation events and enforcing limits."""

import logging
from datetime import datetime, date, UTC
from typing import Optional, Dict, Any
import psycopg2
from psycopg2.extras import RealDictCursor

from app.config import NEON_DBNAME, NEON_USER, NEON_PASSWORD, NEON_HOST, NEON_SSLMODE

logger = logging.getLogger(__name__)


class QuestionGenerationService:
    """Service for managing question generation tracking and subscription limits."""
    
    def __init__(self):
        """Initialize the service with database connection parameters."""
        self.connection_params = {
            'dbname': NEON_DBNAME,
            'user': NEON_USER,
            'password': NEON_PASSWORD,
            'host': NEON_HOST,
            'sslmode': NEON_SSLMODE
        }
    
    def _get_connection(self):
        """Create and return a database connection."""
        return psycopg2.connect(**self.connection_params)
    
    def get_daily_generation_count(self, uid: str, generation_date: Optional[date] = None) -> int:
        """
        Get the number of question generations for a user on a specific date.
        
        Args:
            uid: Firebase User UID
            generation_date: Date to check (defaults to today)
            
        Returns:
            Number of question generations for that date
        """
        if generation_date is None:
            generation_date = date.today()
        
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM question_generations
                WHERE uid = %s AND generation_date = %s
            """, (uid, generation_date))
            
            result = cursor.fetchone()
            count = result[0] if result else 0
            
            cursor.close()
            conn.close()
            
            logger.info(f"Daily generation count for uid={uid}, date={generation_date}: {count}")
            return count
            
        except Exception as e:
            logger.error(f"Error getting daily generation count for uid={uid}: {e}")
            return 0
    
    def can_generate_questions(self, uid: str, subscription: int, max_daily_questions: int = 2) -> Dict[str, Any]:
        """
        Check if a user can generate questions based on their subscription and daily limit.
        
        Args:
            uid: Firebase User UID
            subscription: User's subscription level (0=free, 1=trial, 2+=premium)
            max_daily_questions: Maximum daily questions for non-premium users
            
        Returns:
            Dictionary with:
                - can_generate: Boolean indicating if user can generate questions
                - reason: String explaining why if can_generate is False
                - current_count: Current number of generations today
                - max_count: Maximum allowed (None for unlimited)
                - is_premium: Boolean indicating if user has premium subscription
        """
        # Premium users (subscription >= 2) have unlimited access
        is_premium = subscription >= 2
        
        if is_premium:
            return {
                'can_generate': True,
                'reason': 'Premium subscription - unlimited access',
                'current_count': None,
                'max_count': None,
                'is_premium': True
            }
        
        # Free and trial users have daily limits
        current_count = self.get_daily_generation_count(uid)
        
        if current_count >= max_daily_questions:
            return {
                'can_generate': False,
                'reason': f'Daily limit of {max_daily_questions} questions reached',
                'current_count': current_count,
                'max_count': max_daily_questions,
                'is_premium': False
            }
        
        return {
            'can_generate': True,
            'reason': f'Within daily limit ({current_count}/{max_daily_questions})',
            'current_count': current_count,
            'max_count': max_daily_questions,
            'is_premium': False
        }
    
    def record_generation(
        self,
        uid: str,
        level: Optional[int] = None,
        source: str = 'api',
        llm_interaction_id: Optional[int] = None
    ) -> Optional[int]:
        """
        Record a question generation event.
        
        Args:
            uid: Firebase User UID
            level: Difficulty level requested (1-6)
            source: Source of questions ('api', 'cached', 'fallback')
            llm_interaction_id: ID of associated LLM interaction (if applicable)
            
        Returns:
            ID of the created question_generation record, or None on error
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            now = datetime.now(UTC)
            today = date.today()
            
            cursor.execute("""
                INSERT INTO question_generations 
                (uid, generation_date, generation_datetime, level, source, llm_interaction_id)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (uid, today, now, level, source, llm_interaction_id))
            
            generation_id = cursor.fetchone()[0]
            conn.commit()
            
            cursor.close()
            conn.close()
            
            logger.info(f"Recorded generation event: id={generation_id}, uid={uid}, level={level}, source={source}")
            return generation_id
            
        except Exception as e:
            logger.error(f"Error recording generation for uid={uid}: {e}")
            return None
    
    def get_user_generations(
        self,
        uid: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 100
    ) -> list:
        """
        Get question generation history for a user.
        
        Args:
            uid: Firebase User UID
            start_date: Optional start date filter
            end_date: Optional end date filter
            limit: Maximum number of records to return
            
        Returns:
            List of generation records
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            query = """
                SELECT id, uid, generation_date, generation_datetime, 
                       level, source, llm_interaction_id
                FROM question_generations
                WHERE uid = %s
            """
            params = [uid]
            
            if start_date:
                query += " AND generation_date >= %s"
                params.append(start_date)
            
            if end_date:
                query += " AND generation_date <= %s"
                params.append(end_date)
            
            query += " ORDER BY generation_datetime DESC LIMIT %s"
            params.append(limit)
            
            cursor.execute(query, params)
            results = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            return [dict(row) for row in results]
            
        except Exception as e:
            logger.error(f"Error getting user generations for uid={uid}: {e}")
            return []
