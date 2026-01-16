"""Service for tracking AI prompts and calculating costs."""

import logging
import time
from datetime import datetime, UTC
from typing import Optional, Dict, Any
import psycopg2
from psycopg2.extras import RealDictCursor

from app.config import NEON_DBNAME, NEON_USER, NEON_PASSWORD, NEON_HOST, NEON_SSLMODE
from app.utils.grade_tone_loader import GradeToneConfig

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
        credits: int,
        max_daily_questions: int = 2
    ) -> Dict[str, Any]:
        """
        Check if a user can generate more questions based on credits, subscription and daily limit.
        
        Credits and daily limits work together:
        - Credits: Overall cap on total AI generations (across all time)
        - Daily limit: Cap on generations per day (resets daily)
        - Both must allow generation for request to proceed
        
        Args:
            uid: Firebase User UID
            subscription: User's subscription level (0=free, 1=trial, 2+=premium)
            credits: User's remaining AI generation credits
            max_daily_questions: Maximum allowed generations per day for free/trial users
            
        Returns:
            Dictionary with:
                - can_generate: bool - Whether user can generate questions
                - reason: str - Explanation
                - current_count: int - Current daily count
                - max_count: int or None - Max allowed (None for premium)
                - is_premium: bool - Whether user has premium
                - credits_remaining: int - Credits remaining after this check
        """
        is_premium = subscription >= 2
        
        # First check credits (applies to all users)
        if credits <= 0:
            return {
                'can_generate': False,
                'reason': 'No credits remaining',
                'current_count': 0,
                'max_count': None,
                'is_premium': is_premium,
                'credits_remaining': 0
            }
        
        # Premium users bypass daily limits but still use credits
        if is_premium:
            return {
                'can_generate': True,
                'reason': 'Premium user - unlimited daily access',
                'current_count': 0,  # Don't count for premium
                'max_count': None,
                'is_premium': True,
                'credits_remaining': credits
            }
        
        # For free/trial users, also check daily limit
        current_count = self.get_daily_question_generation_count(uid)
        
        if current_count >= max_daily_questions:
            return {
                'can_generate': False,
                'reason': f'Daily limit reached ({current_count}/{max_daily_questions})',
                'current_count': current_count,
                'max_count': max_daily_questions,
                'is_premium': False,
                'credits_remaining': credits
            }
        
        return {
            'can_generate': True,
            'reason': f'Within daily limit ({current_count}/{max_daily_questions})',
            'current_count': current_count,
            'max_count': max_daily_questions,
            'is_premium': False,
            'credits_remaining': credits
        }

    def get_daily_help_count(
        self,
        uid: str,
        date: Optional[datetime] = None
    ) -> int:
        """
        Get the count of help requests for a specific day from knowledge_usage_log table.
        
        Args:
            uid: Firebase User UID
            date: Date to check (defaults to today)
            
        Returns:
            Count of help requests for the day
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Use today if no date provided
            if date is None:
                date = datetime.now(UTC)
            
            # Query for help requests in knowledge_usage_log on the specified date
            cursor.execute("""
                SELECT COUNT(*) 
                FROM knowledge_usage_log
                WHERE uid = %s 
                  AND log_type IN ('knowledge_question_help', 'knowledge_answer_help')
                  AND DATE(generated_at AT TIME ZONE 'UTC') = DATE(%s AT TIME ZONE 'UTC')
            """, (uid, date))
            
            count = cursor.fetchone()[0]
            
            cursor.close()
            conn.close()
            
            return count
            
        except Exception as e:
            logger.error(f"Error fetching daily help count for uid={uid}: {e}")
            return 0

    def can_request_help(
        self,
        uid: str,
        subscription: int,
        credits: int,
        max_daily_help: int = 2
    ) -> Dict[str, Any]:
        """
        Check if a user can request help based on credits, subscription and daily limit.
        
        Credits and daily limits work together:
        - Credits: Overall cap on total AI generations (across all time)
        - Daily limit: Cap on help requests per day (resets daily)
        - Both must allow help request to proceed
        
        Args:
            uid: Firebase User UID
            subscription: User's subscription level (0=free, 1=trial, 2+=premium)
            credits: User's remaining AI generation credits
            max_daily_help: Maximum allowed help requests per day for free/trial users
            
        Returns:
            Dictionary with:
                - can_request: bool - Whether user can request help
                - reason: str - Explanation
                - current_count: int - Current daily help count
                - max_count: int or None - Max allowed (None for premium)
                - is_premium: bool - Whether user has premium
                - credits_remaining: int - Credits remaining after this check
        """
        is_premium = subscription >= 2
        
        # First check credits (applies to all users)
        if credits <= 0:
            return {
                'can_request': False,
                'reason': 'No credits remaining',
                'current_count': 0,
                'max_count': None,
                'is_premium': is_premium,
                'credits_remaining': 0
            }
        
        # Premium users bypass daily limits but still use credits
        if is_premium:
            return {
                'can_request': True,
                'reason': 'Premium user - unlimited daily help',
                'current_count': 0,  # Don't count for premium
                'max_count': None,
                'is_premium': True,
                'credits_remaining': credits
            }
        
        # For free/trial users, also check daily help limit
        current_count = self.get_daily_help_count(uid)
        
        if current_count >= max_daily_help:
            return {
                'can_request': False,
                'reason': f'Daily help limit reached ({current_count}/{max_daily_help})',
                'current_count': current_count,
                'max_count': max_daily_help,
                'is_premium': False,
                'credits_remaining': credits
            }
        
        return {
            'can_request': True,
            'reason': f'Within daily help limit ({current_count}/{max_daily_help})',
            'current_count': current_count,
            'max_count': max_daily_help,
            'is_premium': False,
            'credits_remaining': credits
        }

    def deduct_user_credit(
        self,
        uid: str,
        amount: int = 1
    ) -> bool:
        """
        Deduct credits from user's account.
        
        Args:
            uid: Firebase User UID
            amount: Number of credits to deduct (default: 1)
            
        Returns:
            True if deduction successful, False otherwise
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Update credits, ensuring it doesn't go negative
            cursor.execute("""
                UPDATE users 
                SET credits = GREATEST(0, credits - %s)
                WHERE uid = %s
                RETURNING credits
            """, (amount, uid))
            
            result = cursor.fetchone()
            conn.commit()
            
            cursor.close()
            conn.close()
            
            if result:
                logger.info(f"Deducted {amount} credit(s) from user {uid}, remaining: {result[0]}")
                return True
            else:
                logger.warning(f"User {uid} not found for credit deduction")
                return False
            
        except Exception as e:
            logger.error(f"Error deducting credits for uid={uid}: {e}")
            return False

    def generate_question_help(
        self,
        uid: str,
        question: str,
        correct_answer: str,
        subject_id: int,
        subject_name: str,
        user_answer: Optional[str] = None,
        has_answered: bool = False,
        visual_preference: str = 'text',
        student_grade_level: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generate AI-powered step-by-step help for a knowledge question.
        
        Behavior depends on whether user has answered:
        - Before answering (has_answered=False): Generate explanation for a SIMILAR question
        - After answering (has_answered=True): Generate explanation for the EXACT question
        
        Visual aids (shapes/diagrams) are controlled by:
        1. Global feature flags in config.py (FF_HELP_VISUAL_*)
        2. Subject-level limits in subjects table (visual_json_max, visual_svg_max)
        3. Environment variables override subject settings
        4. User preference (visual_preference parameter)
        
        Args:
            uid: Firebase User UID
            question: The actual question text
            correct_answer: The correct answer for context
            subject_id: Subject ID for visual limit lookup
            subject_name: Subject name for prompt context
            user_answer: User's submitted answer (only when has_answered=True)
            has_answered: Whether user has already submitted an answer
            visual_preference: 'text' (no visuals), 'json' (force JSON shapes), 'svg' (force AI SVG)
            
        Returns:
            Dictionary with:
                - help_steps: List[HelpStep] - Markdown steps with optional visuals
                - question_variant: str - The question being explained (different if not answered)
                - has_answered: bool - Echo of input flag
                - visual_count: int - Number of JSON visual aids included
                - svg_count: int - Number of AI-generated SVG aids included
        """
        from openai import OpenAI
        from app.config import (
            AI_BRIDGE_BASE_URL,
            AI_BRIDGE_API_KEY,
            HTTP_REFERER,
            APP_TITLE,
            FF_HELP_VISUAL_JSON_ENABLED,
            FF_HELP_VISUAL_JSON_MAX,
            FF_HELP_VISUAL_SVG_FROM_AI_ENABLED,
            FF_HELP_VISUAL_SVG_FROM_AI_MAX
        )
        from app.services.ai_service import get_models_to_try
        import json
        
        try:
            # Fetch subject visual limits from database
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT visual_json_max, visual_svg_max
                FROM subjects
                WHERE id = %s
            """, (subject_id,))
            
            subject_limits = cursor.fetchone()
            cursor.close()
            conn.close()
            
            # Default to 0 if subject not found
            subject_json_max = subject_limits[0] if subject_limits else 0
            subject_svg_max = subject_limits[1] if subject_limits else 0
            
            # Determine effective visual limits (global env overrides subject)
            effective_json_max = FF_HELP_VISUAL_JSON_MAX if FF_HELP_VISUAL_JSON_ENABLED else 0
            effective_svg_max = FF_HELP_VISUAL_SVG_FROM_AI_MAX if FF_HELP_VISUAL_SVG_FROM_AI_ENABLED else 0
            
            # Take minimum of subject and global limits (subject can be MORE restrictive)
            final_json_max = min(effective_json_max, subject_json_max) if subject_json_max > 0 else effective_json_max
            final_svg_max = min(effective_svg_max, subject_svg_max) if subject_svg_max > 0 else effective_svg_max
            
            # Override based on user's visual preference
            if visual_preference == 'text':
                # User wants text only - disable all visuals
                final_json_max = 0
                final_svg_max = 0
            elif visual_preference == 'json':
                # User wants JSON shapes - force at least 1, disable SVG
                final_json_max = max(final_json_max, 5)  # Ensure minimum 5 for multiple shapes
                final_svg_max = 0
            elif visual_preference == 'svg':
                # User wants AI-generated SVG - force at least 1, disable JSON
                final_json_max = 0
                final_svg_max = max(final_svg_max, 2)  # Ensure minimum 2 SVGs
            
            logger.info(f"Help visual limits for subject {subject_name} (preference={visual_preference}): JSON={final_json_max}, SVG={final_svg_max}")
            
            # Determine if visuals are required or optional
            visual_required = visual_preference in ['json', 'svg']
            visual_requirement_text = "**REQUIRED**" if visual_required else "OPTIONAL - use sparingly when they genuinely help understanding"
            
            # Build visual instructions for AI
            visual_instructions = ""
            if final_json_max > 0 or final_svg_max > 0:
                visual_instructions = f"""
**Visual Aids** ({visual_requirement_text}):
You {"MUST" if visual_required else "may"} include up to {final_json_max} JSON-based visual aids and {final_svg_max} AI-generated SVG aids across ALL steps.
{"At least ONE visual aid is MANDATORY for this help request." if visual_required else ""}

For JSON visuals (frontend renders these):
- Shape primitives: {{\"type\": \"circle\", \"data\": {{\"radius\": 50, \"fill\": \"#4CAF50\", \"label\": \"Area\"}}}}
- Available shapes: circle, rectangle, triangle, line, arrow, grid
- Each shape supports: fill, stroke, strokeWidth, label, position (x, y)

**IMPORTANT for quantities/ratios:**
- To show "2 apples", create an ARRAY of 2 rectangle shapes, NOT one shape with label "2 Apples"
- To show ratio 3:2, create 3 shapes + 2 shapes (5 total shapes in the array)
- Each visual can contain MULTIPLE shapes as an array
- Example for 2 items:
  {{
    "type": "json_shapes",  // Note: plural "shapes"
    "data": [
      {{\"type\": \"rectangle\", \"position\": {{\"x\": 50, \"y\": 50}}, \"width\": 40, \"height\": 40, \"fill\": \"#F44336\", \"label\": \"Apple 1\"}},
      {{\"type\": \"rectangle\", \"position\": {{\"x\": 100, \"y\": 50}}, \"width\": 40, \"height\": 40, \"fill\": \"#F44336\", \"label\": \"Apple 2\"}}
    ]
  }}

For AI-generated SVG (experimental, use ONLY if JSON shapes insufficient):
- Provide complete <svg> element with viewBox, dimensions
- Use clean, minimal styling
- Include descriptive title/aria-label

**When to use visuals:**
- Math: Geometry (shapes), fractions (pie charts), ratios (multiple shapes), graphs
- Science: Diagrams (atoms, cells, processes)
- Geography: Maps, region highlights
- {"Use visuals for ANY concept that benefits from visual representation" if visual_required else "NOT needed for: Pure text concepts, definitions, simple calculations"}

**Visual Response Format:**
Add "visual" field to relevant steps:
{{
  "step_number": 2,
  "explanation": "markdown text...",
  "visual": {{
    "type": "json_shapes",  // or "json_shape" (single), or "svg_code"
    "data": [...],           // Array of shapes OR single shape object
    "svg": "<svg>...</svg>"  // or complete SVG string
  }}
}}
"""
            
            # Build prompt based on whether user has answered
            if has_answered:
                # Post-answer: Explain the EXACT question
                answer_context = f"\nUser's submitted answer: {user_answer}" if user_answer else ""
                prompt_mode = "POST-ANSWER MODE"
                question_instruction = f"Explain the following {subject_name} question step-by-step:{answer_context}"
                question_target = question
            else:
                # Pre-answer: Explain a SIMILAR question
                prompt_mode = "PRE-ANSWER MODE"
                question_instruction = f"""Generate a SIMILAR but DIFFERENT {subject_name} question to help the student learn the concept, then explain it step-by-step.

**Original Question (DO NOT explain this directly):**
{question}

**Your Task:**
1. Create a similar question that teaches the SAME concept/skill
2. Make it slightly easier or use different numbers/scenario
3. Provide step-by-step explanation for YOUR new question
4. The new question should have the same educational value"""
                question_target = "[AI will generate similar question]"
            
            prompt = f"""You are an expert {subject_name} tutor helping a student understand a question.

**{prompt_mode}**
{question_instruction}

**Question:** {question}
**Correct Answer:** {correct_answer}

{visual_instructions}

**Response Format (valid JSON only):**
{{
  "question_variant": "{question if has_answered else 'your newly generated similar question'}",  // If post-answer: copy the question text exactly as provided. If pre-answer: write your new similar question here
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
1. {GradeToneConfig.get_prompt_instruction(student_grade_level)}
2. Break down into 3-5 logical steps
3. Include markdown formatting: **bold**, *italic*, bullet points, numbered lists
4. Highlight key concepts and common mistakes
5. End with a summary/takeaway
6. Visuals: ONLY use when they genuinely aid understanding (not decorative)
7. Avoid overwhelming the student - keep it focused and concise
8. {"CRITICAL: In 'question_variant' field, generate a SIMILAR question with different numbers/scenario. DO NOT copy the original question!" if not has_answered else "CRITICAL: In 'question_variant' field, copy the exact question text provided above word-for-word. Do NOT write 'EXACT' or any placeholder."}

Return ONLY the JSON object, no additional text.
"""
            
            # Get models from database (cached) with fallback - same as knowledge questions
            models_to_try = get_models_to_try()
            
            if not models_to_try:
                logger.error("No AI models available for help generation")
                raise ValueError("No AI models available")
            
            # Initialize OpenAI client
            openai_client = OpenAI(
                base_url=AI_BRIDGE_BASE_URL,
                api_key=AI_BRIDGE_API_KEY,
                default_headers={
                    "HTTP-Referer": HTTP_REFERER,
                    "X-Title": APP_TITLE
                }
            )
            
            last_error = None
            last_error_model = None
            response_text = None
            failed_models = []
            
            # Try models in order with fallback
            for attempt_index, model_name in enumerate(models_to_try):
                is_fallback_attempt = attempt_index > 0
                
                if is_fallback_attempt:
                    logger.info(f"Primary model failed, trying fallback model: {model_name}")
                
                try:
                    start_time = time.time()
                    
                    completion = openai_client.chat.completions.create(
                        model=model_name,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.7,
                        max_tokens=2000
                    )
                    
                    response_time_ms = int((time.time() - start_time) * 1000)
                    response_text = completion.choices[0].message.content.strip()
                    
                    # Parse JSON response
                    try:
                        # Remove markdown code blocks if present
                        if response_text.startswith("```"):
                            response_text = response_text.split("```")[1]
                            if response_text.startswith("json"):
                                response_text = response_text[4:].strip()
                        
                        help_data = json.loads(response_text)
                        
                        # Validate response structure
                        if "help_steps" not in help_data or not isinstance(help_data["help_steps"], list):
                            raise ValueError("Response missing 'help_steps' array")
                        
                        if "question_variant" not in help_data:
                            help_data["question_variant"] = question  # Fallback to original
                        
                        # Count visual aids
                        visual_count = 0
                        svg_count = 0
                        
                        for step in help_data["help_steps"]:
                            if "visual" in step and step["visual"]:
                                visual_type = step["visual"].get("type", "")
                                if visual_type == "json_shape":
                                    visual_count += 1
                                elif visual_type == "svg_code":
                                    svg_count += 1
                        
                        # Enforce visual limits (truncate if AI exceeded)
                        if visual_count > final_json_max or svg_count > final_svg_max:
                            logger.warning(f"AI exceeded visual limits: JSON={visual_count}/{final_json_max}, SVG={svg_count}/{final_svg_max}")
                            
                            json_used = 0
                            svg_used = 0
                            
                            for step in help_data["help_steps"]:
                                if "visual" in step and step["visual"]:
                                    visual_type = step["visual"].get("type", "")
                                    
                                    if visual_type == "json_shape":
                                        if json_used >= final_json_max:
                                            del step["visual"]  # Remove excess
                                        else:
                                            json_used += 1
                                            
                                    elif visual_type == "svg_code":
                                        if svg_used >= final_svg_max:
                                            del step["visual"]  # Remove excess
                                        else:
                                            svg_used += 1
                            
                            visual_count = json_used
                            svg_count = svg_used
                        
                        logger.info(f"Help generated successfully with {model_name} for uid={uid}, subject={subject_name}, visuals: JSON={visual_count}, SVG={svg_count}")
                        
                        # Return successful result with full AI request/response for logging
                        return {
                            "help_steps": help_data["help_steps"],
                            "question_variant": help_data["question_variant"],
                            "has_answered": has_answered,
                            "visual_count": visual_count,
                            "svg_count": svg_count,
                            "ai_model": model_name,
                            "used_fallback": is_fallback_attempt,
                            "response_time_ms": response_time_ms,
                            "ai_request": prompt,  # Full prompt sent to AI
                            "ai_response": response_text  # Full response from AI
                        }
                        
                    except json.JSONDecodeError as e:
                        last_error = f"AI returned invalid JSON: {e}"
                        last_error_model = model_name
                        failed_models.append(model_name)
                        logger.error(f"Error parsing help response as JSON from {model_name}: {e}")
                        logger.error(f"Response was: {response_text if response_text else 'N/A'}")
                        
                        # If this was the last model, raise the error
                        if attempt_index == len(models_to_try) - 1:
                            raise ValueError(last_error)
                        # Otherwise continue to next model
                        continue
                        
                except Exception as e:
                    last_error = str(e)
                    last_error_model = model_name
                    failed_models.append(model_name)
                    logger.error(f"Error generating help with {model_name}: {e}")
                    
                    # If this was the last model, raise the error
                    if attempt_index == len(models_to_try) - 1:
                        raise
                    # Otherwise continue to next model
                    continue
            
            # If we get here, all models failed
            raise ValueError(f"All models failed. Last error from {last_error_model}: {last_error}")
                

        except Exception as e:
            logger.error(f"Error generating help for uid={uid}, question='{question[:50]}...': {e}")
            raise


