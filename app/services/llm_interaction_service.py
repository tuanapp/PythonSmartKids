"""Service for tracking LLM interactions and calculating costs."""

import logging
from datetime import datetime, UTC
from typing import Optional, Dict, Any
import psycopg2
from psycopg2.extras import RealDictCursor

from app.config import NEON_DBNAME, NEON_USER, NEON_PASSWORD, NEON_HOST, NEON_SSLMODE

logger = logging.getLogger(__name__)


class LLMInteractionService:
    """Service for managing LLM interaction logging and cost tracking."""
    
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
        Calculate the estimated cost of an LLM interaction.
        
        Args:
            model_name: Name of the model used
            prompt_tokens: Number of tokens in the prompt
            completion_tokens: Number of tokens in the completion
            
        Returns:
            Estimated cost in USD, or None if tokens not provided
        """
        if prompt_tokens is None or completion_tokens is None:
            return None
        
        # Find matching cost structure (case-insensitive partial match)
        model_costs = None
        model_lower = model_name.lower() if model_name else ''
        
        for key, costs in self.TOKEN_COSTS.items():
            if key.lower() in model_lower:
                model_costs = costs
                break
        
        # Use default if no match found
        if model_costs is None:
            model_costs = self.TOKEN_COSTS['default']
            logger.warning(f"Unknown model '{model_name}', using default pricing")
        
        # Calculate cost: (tokens / 1,000,000) * cost_per_million
        prompt_cost = (prompt_tokens / 1_000_000) * model_costs['prompt']
        completion_cost = (completion_tokens / 1_000_000) * model_costs['completion']
        total_cost = prompt_cost + completion_cost
        
        return round(total_cost, 6)  # Round to 6 decimal places for accuracy
    
    def record_interaction(
        self,
        uid: str,
        prompt_text: str,
        response_text: Optional[str] = None,
        model_name: Optional[str] = None,
        prompt_tokens: Optional[int] = None,
        completion_tokens: Optional[int] = None,
        total_tokens: Optional[int] = None,
        response_time_ms: Optional[int] = None,
        status: str = 'success',
        error_message: Optional[str] = None
    ) -> Optional[int]:
        """
        Record an LLM interaction event with full details.
        
        Args:
            uid: Firebase User UID
            prompt_text: The full prompt sent to LLM
            response_text: The full response from LLM (nullable for errors)
            model_name: Name of the model used
            prompt_tokens: Token count for prompt
            completion_tokens: Token count for response
            total_tokens: Total tokens used
            response_time_ms: Response time in milliseconds
            status: Status of the interaction ('success', 'error', 'timeout')
            error_message: Error details if status != 'success'
            
        Returns:
            ID of the created llm_interaction record, or None on error
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            now = datetime.now(UTC)
            
            # Calculate cost if tokens are provided
            estimated_cost = self.calculate_cost(model_name, prompt_tokens, completion_tokens)
            
            cursor.execute("""
                INSERT INTO llm_interactions 
                (uid, request_datetime, prompt_text, response_text, model_name,
                 prompt_tokens, completion_tokens, total_tokens, estimated_cost_usd,
                 response_time_ms, status, error_message)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                uid, now, prompt_text, response_text, model_name,
                prompt_tokens, completion_tokens, total_tokens, estimated_cost,
                response_time_ms, status, error_message
            ))
            
            interaction_id = cursor.fetchone()[0]
            conn.commit()
            
            cursor.close()
            conn.close()
            
            logger.info(f"Recorded LLM interaction: id={interaction_id}, uid={uid}, model={model_name}, status={status}, cost=${estimated_cost or 0:.6f}")
            return interaction_id
            
        except Exception as e:
            logger.error(f"Error recording LLM interaction for uid={uid}: {e}")
            return None
    
    def get_user_interactions(
        self,
        uid: str,
        limit: int = 100,
        status_filter: Optional[str] = None
    ) -> list:
        """
        Get LLM interaction history for a user.
        
        Args:
            uid: Firebase User UID
            limit: Maximum number of records to return
            status_filter: Optional status filter ('success', 'error', 'timeout')
            
        Returns:
            List of LLM interaction records
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            query = """
                SELECT id, uid, request_datetime, prompt_text, response_text,
                       model_name, prompt_tokens, completion_tokens, total_tokens,
                       estimated_cost_usd, response_time_ms, status, error_message
                FROM llm_interactions
                WHERE uid = %s
            """
            params = [uid]
            
            if status_filter:
                query += " AND status = %s"
                params.append(status_filter)
            
            query += " ORDER BY request_datetime DESC LIMIT %s"
            params.append(limit)
            
            cursor.execute(query, params)
            results = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            return [dict(row) for row in results]
            
        except Exception as e:
            logger.error(f"Error getting user interactions for uid={uid}: {e}")
            return []
    
    def get_user_cost_summary(
        self,
        uid: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get cost summary for a user's LLM usage.
        
        Args:
            uid: Firebase User UID
            start_date: Optional start date filter
            end_date: Optional end date filter
            
        Returns:
            Dictionary with cost statistics
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            query = """
                SELECT 
                    COUNT(*) as total_interactions,
                    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful_interactions,
                    SUM(prompt_tokens) as total_prompt_tokens,
                    SUM(completion_tokens) as total_completion_tokens,
                    SUM(total_tokens) as total_tokens,
                    SUM(estimated_cost_usd) as total_cost_usd,
                    AVG(response_time_ms) as avg_response_time_ms
                FROM llm_interactions
                WHERE uid = %s
            """
            params = [uid]
            
            if start_date:
                query += " AND request_datetime >= %s"
                params.append(start_date)
            
            if end_date:
                query += " AND request_datetime <= %s"
                params.append(end_date)
            
            cursor.execute(query, params)
            result = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            if result:
                return dict(result)
            return {}
            
        except Exception as e:
            logger.error(f"Error getting cost summary for uid={uid}: {e}")
            return {}
