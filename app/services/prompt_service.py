"""Service for tracking AI prompts and calculating costs."""

import logging
from datetime import datetime, UTC
from typing import Optional, Dict, Any
import psycopg2
from psycopg2.extras import RealDictCursor

from app.config import NEON_DBNAME, NEON_USER, NEON_PASSWORD, NEON_HOST, NEON_SSLMODE

logger = logging.getLogger(__name__)


class PromptService:
    """Service for managing AI prompt logging and cost tracking."""
    
    # Token costs per 1M tokens (USD) - update these based on actual pricing
    TOKEN_COSTS = {
        'gpt-4': {'prompt': 30.0, 'completion': 60.0},
        'gpt-4-turbo': {'prompt': 10.0, 'completion': 30.0},
        'gpt-3.5-turbo': {'prompt': 0.5, 'completion': 1.5},
        'gemini-2.0-flash': {'prompt': 0.1, 'completion': 0.4},  # Estimated
        'default': {'prompt': 1.0, 'completion': 2.0}  # Fallback pricing
    }
    
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
    
    def calculate_cost(
        self,
        model_name: str,
        prompt_tokens: Optional[int],
        completion_tokens: Optional[int]
    ) -> Optional[float]:
        """
        Calculate the estimated cost of an AI prompt interaction.
        
        Args:
            model_name: Name of the model used
            prompt_tokens: Number of tokens in the prompt
            completion_tokens: Number of tokens in the completion
            
        Returns:
            Estimated cost in USD, or None if tokens are missing
        """
        if prompt_tokens is None or completion_tokens is None:
            return None
        
        # Get model-specific costs or use default
        model_costs = self.TOKEN_COSTS.get(model_name)
        if model_costs is None:
            model_costs = self.TOKEN_COSTS['default']
            logger.warning(f"Unknown model '{model_name}', using default pricing")
        
        # Calculate cost: (tokens / 1,000,000) * cost_per_million
        prompt_cost = (prompt_tokens / 1_000_000) * model_costs['prompt']
        completion_cost = (completion_tokens / 1_000_000) * model_costs['completion']
        total_cost = prompt_cost + completion_cost
        
        return round(total_cost, 6)  # Round to 6 decimal places for accuracy
    
    def record_prompt(
        self,
        uid: str,
        request_type: str,
        request_text: str,
        response_text: Optional[str] = None,
        model_name: Optional[str] = None,
        prompt_tokens: Optional[int] = None,
        completion_tokens: Optional[int] = None,
        total_tokens: Optional[int] = None,
        response_time_ms: Optional[int] = None,
        status: str = 'success',
        error_message: Optional[str] = None,
        is_live: int = 1,
        level: Optional[int] = None,
        source: Optional[str] = None
    ) -> Optional[int]:
        """
        Record an AI prompt interaction event with full details.
        
        Args:
            uid: Firebase User UID
            request_type: Type of request (e.g., 'question_generation')
            request_text: The full prompt sent to AI
            response_text: The full response from AI (nullable for errors)
            model_name: Name of the model used
            prompt_tokens: Token count for prompt
            completion_tokens: Token count for response
            total_tokens: Total tokens used
            response_time_ms: Response time in milliseconds
            status: Status of the interaction ('success', 'error', 'timeout')
            error_message: Error details if status != 'success'
            is_live: 1=live from app, 0=test call
            level: Difficulty level for question generation (1-6)
            source: Source of questions ('api', 'cached', 'fallback')
            
        Returns:
            ID of the created prompt record, or None on error
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            now = datetime.now(UTC)
            
            # Calculate cost if tokens are provided
            estimated_cost = self.calculate_cost(model_name, prompt_tokens, completion_tokens)
            
            cursor.execute("""
                INSERT INTO prompts 
                (uid, request_type, request_text, response_text, model_name,
                 prompt_tokens, completion_tokens, total_tokens, estimated_cost_usd,
                 response_time_ms, status, error_message, is_live, created_at,
                 level, source)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                uid, request_type, request_text, response_text, model_name,
                prompt_tokens, completion_tokens, total_tokens, estimated_cost,
                response_time_ms, status, error_message, is_live, now,
                level, source
            ))
            
            prompt_id = cursor.fetchone()[0]
            conn.commit()
            
            cursor.close()
            conn.close()
            
            logger.info(f"Recorded AI prompt: id={prompt_id}, uid={uid}, type={request_type}, model={model_name}, status={status}, cost=${estimated_cost or 0:.6f}")
            return prompt_id
            
        except Exception as e:
            logger.error(f"Error recording AI prompt for uid={uid}: {e}")
            return None
    
    def get_user_prompts(
        self,
        uid: str,
        limit: int = 100,
        offset: int = 0,
        request_type: Optional[str] = None
    ) -> list[Dict[str, Any]]:
        """
        Get AI prompt interaction history for a user.
        
        Args:
            uid: Firebase User UID
            limit: Maximum number of records to return
            offset: Number of records to skip
            request_type: Filter by specific request type (optional)
            
        Returns:
            List of prompt interaction records as dictionaries
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            if request_type:
                cursor.execute("""
                    SELECT * FROM prompts
                    WHERE uid = %s AND request_type = %s
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s
                """, (uid, request_type, limit, offset))
            else:
                cursor.execute("""
                    SELECT * FROM prompts
                    WHERE uid = %s
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s
                """, (uid, limit, offset))
            
            results = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            return [dict(row) for row in results]
            
        except Exception as e:
            logger.error(f"Error fetching prompts for uid={uid}: {e}")
            return []
    
    def get_user_cost_summary(
        self,
        uid: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get cost summary for a user's AI prompt usage.
        
        Args:
            uid: Firebase User UID
            start_date: Start of date range (optional)
            end_date: End of date range (optional)
            
        Returns:
            Dictionary with cost summary statistics
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Build query with optional date filtering
            query = """
                SELECT 
                    COUNT(*) as total_prompts,
                    SUM(prompt_tokens) as total_prompt_tokens,
                    SUM(completion_tokens) as total_completion_tokens,
                    SUM(total_tokens) as total_tokens,
                    SUM(estimated_cost_usd) as total_cost_usd,
                    AVG(response_time_ms) as avg_response_time_ms,
                    COUNT(CASE WHEN status = 'success' THEN 1 END) as successful_prompts,
                    COUNT(CASE WHEN status = 'error' THEN 1 END) as failed_prompts
                FROM prompts
                WHERE uid = %s
            """
            params = [uid]
            
            if start_date:
                query += " AND created_at >= %s"
                params.append(start_date)
            
            if end_date:
                query += " AND created_at <= %s"
                params.append(end_date)
            
            cursor.execute(query, params)
            result = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            return dict(result) if result else {}
            
        except Exception as e:
            logger.error(f"Error fetching cost summary for uid={uid}: {e}")
            return {}
    
    def get_model_usage_stats(
        self,
        uid: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> list[Dict[str, Any]]:
        """
        Get usage statistics broken down by model.
        
        Args:
            uid: Firebase User UID
            start_date: Start of date range (optional)
            end_date: End of date range (optional)
            
        Returns:
            List of model usage statistics
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            query = """
                SELECT 
                    model_name,
                    COUNT(*) as prompt_count,
                    SUM(total_tokens) as total_tokens,
                    SUM(estimated_cost_usd) as total_cost_usd,
                    AVG(response_time_ms) as avg_response_time_ms
                FROM prompts
                WHERE uid = %s
            """
            params = [uid]
            
            if start_date:
                query += " AND created_at >= %s"
                params.append(start_date)
            
            if end_date:
                query += " AND created_at <= %s"
                params.append(end_date)
            
            query += " GROUP BY model_name ORDER BY total_cost_usd DESC"
            
            cursor.execute(query, params)
            results = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            return [dict(row) for row in results]
            
        except Exception as e:
            logger.error(f"Error fetching model usage stats for uid={uid}: {e}")
            return []
    
    def get_daily_question_generation_count(
        self,
        uid: str,
        date: Optional[datetime] = None
    ) -> int:
        """
        Get the count of question generations for a specific day.
        
        Args:
            uid: Firebase User UID
            date: Date to check (defaults to today)
            
        Returns:
            Count of question generations for the day
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Use today if no date provided
            if date is None:
                date = datetime.now(UTC)
            
            # Query for prompts of type 'question_generation' on the specified date
            # Use AT TIME ZONE to ensure consistent timezone comparison
            cursor.execute("""
                SELECT COUNT(*) 
                FROM prompts
                WHERE uid = %s 
                  AND request_type = 'question_generation'
                  AND DATE(created_at AT TIME ZONE 'UTC') = DATE(%s AT TIME ZONE 'UTC')
            """, (uid, date))
            
            count = cursor.fetchone()[0]
            
            cursor.close()
            conn.close()
            
            return count
            
        except Exception as e:
            logger.error(f"Error fetching daily question count for uid={uid}: {e}")
            return 0
    
    def can_generate_questions(
        self,
        uid: str,
        subscription: int,
        max_daily_questions: int = 2
    ) -> Dict[str, Any]:
        """
        Check if a user can generate more questions based on subscription and daily limit.
        
        Args:
            uid: Firebase User UID
            subscription: User's subscription level (0=free, 1=trial, 2+=premium)
            max_daily_questions: Maximum allowed generations per day for free/trial users
            
        Returns:
            Dictionary with:
                - can_generate: bool - Whether user can generate questions
                - reason: str - Explanation
                - current_count: int - Current daily count
                - max_count: int or None - Max allowed (None for premium)
                - is_premium: bool - Whether user has premium
        """
        # Premium users (subscription >= 2) have unlimited access
        is_premium = subscription >= 2
        
        if is_premium:
            return {
                'can_generate': True,
                'reason': 'Premium user - unlimited access',
                'current_count': 0,  # Don't count for premium
                'max_count': None,
                'is_premium': True
            }
        
        # For free/trial users, check daily limit
        current_count = self.get_daily_question_generation_count(uid)
        
        if current_count >= max_daily_questions:
            return {
                'can_generate': False,
                'reason': f'Daily limit reached ({current_count}/{max_daily_questions})',
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

