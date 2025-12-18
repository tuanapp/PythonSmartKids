import logging
from app.db.models import QuestionPattern
from app.models.schemas import MathAttempt, UserRegistration
from app.db.db_factory import DatabaseFactory

logger = logging.getLogger(__name__)

# Get the configured database provider instance
db_provider = DatabaseFactory.get_provider()

def init_db():
    """Initialize the configured database."""
    db_provider.init_db()

def save_user_registration(user: UserRegistration):
    """Save a user registration using the configured database provider."""
    try:
        db_provider.save_user_registration(user)
        logger.debug(f"User registration saved for uid: {user.uid}")
        return {"success": True, "uid": user.uid}
    except Exception as e:
        logger.error(f"Error saving user registration: {e}")
        raise

def save_attempt(attempt: MathAttempt):
    """Save an attempt using the configured database provider."""
    try:
        db_provider.save_attempt(attempt)
        logger.debug(f"Attempt saved for student {attempt.student_id}")
    except Exception as e:
        logger.error(f"Error saving attempt: {e}")
        raise

def get_attempts(student_id: int):
    """Get attempts for a student using the configured database provider."""
    try:
        attempts = db_provider.get_attempts(student_id)
        logger.debug(f"Retrieved {len(attempts)} attempts for student {student_id}")
        logger.debug(f"Sample attempt data: {attempts[0] if attempts else 'No attempts'}")
        return attempts
    except Exception as e:
        logger.error(f"Error retrieving attempts: {e}")
        raise

def get_attempts_by_uid(uid: str):
    """Get attempts for a user by UID using the configured database provider."""
    try:
        attempts = db_provider.get_attempts_by_uid(uid)
        logger.debug(f"Retrieved {len(attempts)} attempts for user with UID {uid}")
        logger.debug(f"Sample attempt data: {attempts[0] if attempts else 'No attempts'}")
        return attempts
    except Exception as e:
        logger.error(f"Error retrieving attempts by UID: {e}")
        raise

def get_question_patterns():
    """Retrieve all question patterns using the configured database provider."""
    try:
        patterns = db_provider.get_question_patterns()
        logger.debug(f"Retrieved {len(patterns)} question patterns")
        return patterns
    except Exception as e:
        logger.error(f"Error retrieving question patterns: {e}")
        raise

def get_question_patterns_by_level(level: int = None):
    """Retrieve question patterns filtered by level using the configured database provider."""
    try:
        patterns = db_provider.get_question_patterns_by_level(level)
        logger.debug(f"Retrieved {len(patterns)} question patterns for level {level}")
        return patterns
    except Exception as e:
        logger.error(f"Error retrieving question patterns by level: {e}")
        raise

def get_user_by_uid(uid: str):
    """Retrieve a user by UID using the configured database provider."""
    try:
        user = db_provider.get_user_by_uid(uid)
        logger.debug(f"Retrieved user data for uid: {uid}")
        return user
    except Exception as e:
        logger.error(f"Error retrieving user by uid: {e}")
        raise

def get_user_by_email(email: str):
    """Retrieve a user by email using the configured database provider."""
    try:
        user = db_provider.get_user_by_email(email)
        logger.debug(f"Retrieved user data for email: {email}")
        return user
    except Exception as e:
        logger.error(f"Error retrieving user by email: {e}")
        raise

def update_user_profile(uid: str, name: str = None, display_name: str = None, grade_level: int = None):
    """Update user profile fields using the configured database provider."""
    try:
        db_provider.update_user_profile(uid, name, display_name, grade_level)
        logger.debug(f"Updated profile for user {uid}")
    except Exception as e:
        logger.error(f"Error updating user profile: {e}")
        raise

def save_prompt(uid: str, request_text: str, response_text: str, is_live: int = 1):
    """Save AI prompt request and response using the configured database provider."""
    try:
        db_provider.save_prompt(uid, request_text, response_text, is_live)
        logger.debug(f"Prompt saved for user {uid} (is_live={is_live})")
    except Exception as e:
        logger.error(f"Error saving prompt: {e}")
        raise


# ============================================================================
# User Credits Management Functions
# ============================================================================

def get_user_credits(uid: str) -> int:
    """Get the current credits for a user."""
    try:
        conn = db_provider._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT credits FROM users WHERE uid = %s", (uid,))
        result = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if result:
            return result[0]
        return 0
    except Exception as e:
        logger.error(f"Error getting user credits: {e}")
        return 0


def decrement_user_credits(uid: str) -> int:
    """
    Decrement user credits by 1 after successful AI generation.
    Returns the new credit balance.
    """
    try:
        conn = db_provider._get_connection()
        cursor = conn.cursor()
        
        # Decrement credits but don't go below 0
        cursor.execute("""
            UPDATE users 
            SET credits = GREATEST(credits - 1, 0),
                updated_at = CURRENT_TIMESTAMP
            WHERE uid = %s
            RETURNING credits
        """, (uid,))
        
        result = cursor.fetchone()
        new_credits = result[0] if result else 0
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"Decremented credits for user {uid}, new balance: {new_credits}")
        return new_credits
    except Exception as e:
        logger.error(f"Error decrementing user credits: {e}")
        raise


def adjust_user_credits(uid: str, amount: int, reason: str = None) -> dict:
    """
    Adjust user credits by a given amount (positive to add, negative to subtract).
    Used by admin endpoint to manage user credits.
    
    Args:
        uid: Firebase User UID
        amount: Credits to add (positive) or remove (negative)
        reason: Optional reason for the adjustment
        
    Returns:
        Dictionary with old_credits, new_credits, and adjustment details
    """
    try:
        conn = db_provider._get_connection()
        cursor = conn.cursor()
        
        # Get current credits first
        cursor.execute("SELECT credits FROM users WHERE uid = %s", (uid,))
        result = cursor.fetchone()
        
        if not result:
            cursor.close()
            conn.close()
            raise ValueError(f"User not found: {uid}")
        
        old_credits = result[0]
        
        # Calculate new credits (don't go below 0)
        new_credits = max(old_credits + amount, 0)
        
        # Update credits
        cursor.execute("""
            UPDATE users 
            SET credits = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE uid = %s
        """, (new_credits, uid))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"Adjusted credits for user {uid}: {old_credits} -> {new_credits} (amount: {amount}, reason: {reason})")
        
        return {
            "uid": uid,
            "old_credits": old_credits,
            "new_credits": new_credits,
            "adjustment": amount,
            "reason": reason
        }
    except Exception as e:
        logger.error(f"Error adjusting user credits: {e}")
        raise


# ============================================================================
# Credit Usage Tracking Functions
# ============================================================================

def record_credit_usage(uid: str, game_type: str, subject: str = None, sub_section: str = None, credits_used: int = 1, model_name: str = None) -> dict:
    """
    Record or update credit usage for a user on a specific game/subject for today.
    Uses upsert logic: if record exists for today, increment; otherwise create new.
    
    Args:
        uid: Firebase User UID
        game_type: Type of game ('math', 'dictation', 'knowledge', etc.)
        subject: Subject within game (e.g., 'addition', 'multiplication')
        sub_section: Future: sub-section within subject
        credits_used: Number of credits used (default 1)
        model_name: Optional AI model name used for generation (resolves to model_id FK)
        
    Returns:
        Dictionary with usage record details
    """
    # Resolve model_name to model_id if provided
    model_id = None
    if model_name:
        try:
            from app.services.llm_service import llm_service
            model_id = llm_service.get_model_id_by_name(model_name)
            if model_id:
                logger.debug(f"Resolved model '{model_name}' to model_id={model_id}")
        except Exception as e:
            logger.warning(f"Could not resolve model name '{model_name}': {e}")
    
    try:
        conn = db_provider._get_connection()
        cursor = conn.cursor()
        
        # Use upsert to either create or update the record
        cursor.execute("""
            INSERT INTO credit_usage (uid, usage_date, game_type, subject, sub_section, credits_used, generation_count, model_id)
            VALUES (%s, CURRENT_DATE, %s, %s, %s, %s, 1, %s)
            ON CONFLICT (uid, usage_date, game_type, subject) 
            DO UPDATE SET 
                credits_used = credit_usage.credits_used + EXCLUDED.credits_used,
                generation_count = credit_usage.generation_count + 1,
                model_id = COALESCE(EXCLUDED.model_id, credit_usage.model_id),
                updated_at = CURRENT_TIMESTAMP
            RETURNING id, usage_date, credits_used, generation_count, model_id
        """, (uid, game_type, subject, sub_section, credits_used, model_id))
        
        result = cursor.fetchone()
        
        conn.commit()
        cursor.close()
        conn.close()
        
        if result:
            logger.info(f"Recorded credit usage for user {uid}: game={game_type}, subject={subject}, credits={result[2]}, count={result[3]}, model_id={result[4]}")
            return {
                "id": result[0],
                "usage_date": str(result[1]),
                "credits_used": result[2],
                "generation_count": result[3],
                "model_id": result[4]
            }
        return None
    except Exception as e:
        # If unique constraint doesn't exist yet, fall back to simple insert/update
        logger.warning(f"Upsert failed, falling back to simple insert: {e}")
        try:
            conn = db_provider._get_connection()
            cursor = conn.cursor()
            
            # Check if record exists
            cursor.execute("""
                SELECT id, credits_used, generation_count FROM credit_usage 
                WHERE uid = %s AND usage_date = CURRENT_DATE AND game_type = %s 
                AND (subject = %s OR (subject IS NULL AND %s IS NULL))
            """, (uid, game_type, subject, subject))
            
            existing = cursor.fetchone()
            
            if existing:
                # Update existing record
                cursor.execute("""
                    UPDATE credit_usage 
                    SET credits_used = credits_used + %s,
                        generation_count = generation_count + 1,
                        model_id = COALESCE(%s, model_id),
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    RETURNING id, credits_used, generation_count, model_id
                """, (credits_used, model_id, existing[0]))
            else:
                # Insert new record
                cursor.execute("""
                    INSERT INTO credit_usage (uid, usage_date, game_type, subject, sub_section, credits_used, generation_count, model_id)
                    VALUES (%s, CURRENT_DATE, %s, %s, %s, %s, 1, %s)
                    RETURNING id, credits_used, generation_count, model_id
                """, (uid, game_type, subject, sub_section, credits_used, model_id))
            
            result = cursor.fetchone()
            conn.commit()
            cursor.close()
            conn.close()
            
            if result:
                logger.info(f"Recorded credit usage for user {uid}: game={game_type}, subject={subject}, model_id={result[3]}")
                return {
                    "id": result[0],
                    "credits_used": result[1],
                    "generation_count": result[2],
                    "model_id": result[3]
                }
            return None
        except Exception as e2:
            logger.error(f"Error recording credit usage: {e2}")
            raise


def get_user_credit_usage(uid: str, usage_date: str = None, game_type: str = None) -> list:
    """
    Get credit usage records for a user.
    
    Args:
        uid: Firebase User UID
        usage_date: Optional date filter (YYYY-MM-DD format, defaults to today)
        game_type: Optional game type filter
        
    Returns:
        List of credit usage records
    """
    try:
        conn = db_provider._get_connection()
        cursor = conn.cursor()
        
        query = """
            SELECT id, uid, usage_date, game_type, subject, sub_section, credits_used, generation_count, created_at
            FROM credit_usage 
            WHERE uid = %s
        """
        params = [uid]
        
        if usage_date:
            query += " AND usage_date = %s"
            params.append(usage_date)
        else:
            query += " AND usage_date = CURRENT_DATE"
        
        if game_type:
            query += " AND game_type = %s"
            params.append(game_type)
        
        query += " ORDER BY game_type, subject"
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return [
            {
                "id": row[0],
                "uid": row[1],
                "usage_date": str(row[2]),
                "game_type": row[3],
                "subject": row[4],
                "sub_section": row[5],
                "credits_used": row[6],
                "generation_count": row[7],
                "created_at": row[8].isoformat() if row[8] else None
            }
            for row in results
        ]
    except Exception as e:
        logger.error(f"Error getting user credit usage: {e}")
        raise


def get_user_daily_credit_summary(uid: str, usage_date: str = None) -> dict:
    """
    Get a summary of credit usage for a user on a specific date.
    
    Args:
        uid: Firebase User UID
        usage_date: Optional date (YYYY-MM-DD format, defaults to today)
        
    Returns:
        Summary dictionary with totals per game type
    """
    try:
        conn = db_provider._get_connection()
        cursor = conn.cursor()
        
        date_condition = "usage_date = %s" if usage_date else "usage_date = CURRENT_DATE"
        params = [uid, usage_date] if usage_date else [uid]
        
        cursor.execute(f"""
            SELECT 
                game_type,
                SUM(credits_used) as total_credits,
                SUM(generation_count) as total_generations
            FROM credit_usage 
            WHERE uid = %s AND {date_condition}
            GROUP BY game_type
        """, params)
        
        results = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        by_game = {row[0]: {"credits_used": row[1], "generation_count": row[2]} for row in results}
        total_credits = sum(row[1] for row in results)
        total_generations = sum(row[2] for row in results)
        
        return {
            "uid": uid,
            "usage_date": usage_date or "today",
            "total_credits_used": total_credits,
            "total_generations": total_generations,
            "by_game_type": by_game
        }
    except Exception as e:
        logger.error(f"Error getting user daily credit summary: {e}")
        raise


# ============================================================================
# Game Score / Leaderboard Functions
# ============================================================================

def save_game_score(uid: str, user_name: str, game_type: str, score: int, time_seconds: int = None, total_questions: int = None):
    """Save a game score for the leaderboard."""
    logger.info(f"[save_game_score] START - uid: {uid}, game_type: {game_type}, score: {score}, time: {time_seconds}")
    try:
        logger.info(f"[save_game_score] Getting connection from db_provider...")
        conn = db_provider._get_connection()
        logger.info(f"[save_game_score] Connection obtained successfully")
        cursor = conn.cursor()
        
        logger.info(f"[save_game_score] Executing INSERT query...")
        cursor.execute("""
            INSERT INTO game_scores (uid, user_name, game_type, score, time_seconds, total_questions)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (uid, user_name, game_type, score, time_seconds, total_questions))
        
        result = cursor.fetchone()
        score_id = result[0] if result else None
        logger.info(f"[save_game_score] INSERT complete, score_id: {score_id}")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"[save_game_score] SUCCESS - Game score saved: {game_type} for user {uid} - score: {score}, time: {time_seconds}, id: {score_id}")
        return {"id": score_id}
    except Exception as e:
        logger.error(f"Error saving game score: {e}")
        raise


def _mask_user_name(name: str) -> str:
    """
    Mask user name for PII protection.
    Format: First name (last letter replaced with *) + first letter of last name.
    Examples:
        "John Smith" -> "Joh* S"
        "Alice" -> "Alic*"
        "john.doe@email.com" -> "joh* d" (treats email username as name)
    """
    if not name:
        return "Player"
    
    # If it looks like an email, extract username part
    if '@' in name:
        name = name.split('@')[0]
        # Replace dots/underscores with spaces for parsing
        name = name.replace('.', ' ').replace('_', ' ')
    
    parts = name.strip().split()
    
    if len(parts) == 0:
        return "Player"
    
    first_name = parts[0]
    
    # Mask last letter of first name
    if len(first_name) > 1:
        masked_first = first_name[:-1] + '*'
    else:
        masked_first = '*'
    
    # Add first letter of last name if exists
    if len(parts) > 1:
        last_initial = parts[-1][0].upper() if parts[-1] else ''
        return f"{masked_first} {last_initial}"
    
    return masked_first


def get_leaderboard(game_type: str, limit: int = 3):
    """Get top scores for a specific game type."""
    try:
        conn = db_provider._get_connection()
        cursor = conn.cursor()
        
        if game_type == 'multiplication_time':
            # For time game: highest score (correct answers) is best
            cursor.execute("""
                SELECT id, uid, user_name, game_type, score, time_seconds, total_questions, created_at
                FROM game_scores
                WHERE game_type = %s
                ORDER BY score DESC, created_at ASC
                LIMIT %s
            """, (game_type, limit))
        else:
            # For range game: lowest time is best
            cursor.execute("""
                SELECT id, uid, user_name, game_type, score, time_seconds, total_questions, created_at
                FROM game_scores
                WHERE game_type = %s AND time_seconds IS NOT NULL
                ORDER BY time_seconds ASC, created_at ASC
                LIMIT %s
            """, (game_type, limit))
        
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        
        scores = []
        for rank, row in enumerate(rows, 1):
            scores.append({
                "id": row[0],
                "uid": row[1],
                "user_name": _mask_user_name(row[2]),  # Mask for PII protection
                "game_type": row[3],
                "score": row[4],
                "time_seconds": row[5],
                "total_questions": row[6],
                "created_at": row[7].isoformat() if row[7] else None,
                "rank": rank
            })
        
        return {
            "game_type": game_type,
            "scores": scores
        }
    except Exception as e:
        logger.error(f"Error fetching leaderboard: {e}")
        raise


def get_user_best_scores(uid: str, game_type: str, limit: int = 3):
    """Get a user's best scores for a specific game type."""
    try:
        conn = db_provider._get_connection()
        cursor = conn.cursor()
        
        if game_type == 'multiplication_time':
            # For time game: highest score is best
            cursor.execute("""
                SELECT id, uid, user_name, game_type, score, time_seconds, total_questions, created_at
                FROM game_scores
                WHERE uid = %s AND game_type = %s
                ORDER BY score DESC, created_at ASC
                LIMIT %s
            """, (uid, game_type, limit))
        else:
            # For range game: lowest time is best
            cursor.execute("""
                SELECT id, uid, user_name, game_type, score, time_seconds, total_questions, created_at
                FROM game_scores
                WHERE uid = %s AND game_type = %s AND time_seconds IS NOT NULL
                ORDER BY time_seconds ASC, created_at ASC
                LIMIT %s
            """, (uid, game_type, limit))
        
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        
        scores = []
        for row in rows:
            scores.append({
                "id": row[0],
                "uid": row[1],
                "user_name": row[2],
                "game_type": row[3],
                "score": row[4],
                "time_seconds": row[5],
                "total_questions": row[6],
                "created_at": row[7].isoformat() if row[7] else None
            })
        
        return {
            "uid": uid,
            "scores": scores
        }
    except Exception as e:
        logger.error(f"Error fetching user best scores: {e}")
        raise


# Initialize the database when this module is imported
init_db()
