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

def save_prompt(uid: str, request_text: str, response_text: str, is_live: int = 1):
    """Save AI prompt request and response using the configured database provider."""
    try:
        db_provider.save_prompt(uid, request_text, response_text, is_live)
        logger.debug(f"Prompt saved for user {uid} (is_live={is_live})")
    except Exception as e:
        logger.error(f"Error saving prompt: {e}")
        raise


# ============================================================================
# Game Score / Leaderboard Functions
# ============================================================================

def save_game_score(uid: str, user_name: str, game_type: str, score: int, time_seconds: int = None, total_questions: int = None):
    """Save a game score for the leaderboard."""
    try:
        conn = db_provider._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO game_scores (uid, user_name, game_type, score, time_seconds, total_questions)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (uid, user_name, game_type, score, time_seconds, total_questions))
        
        result = cursor.fetchone()
        score_id = result[0] if result else None
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"Game score saved: {game_type} for user {uid} - score: {score}, time: {time_seconds}")
        return {"id": score_id}
    except Exception as e:
        logger.error(f"Error saving game score: {e}")
        raise


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
                "user_name": row[2],
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
