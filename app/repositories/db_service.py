import logging
from app.models.schemas import MathAttempt
from app.db.db_factory import DatabaseFactory

logger = logging.getLogger(__name__)

# Get the configured database provider instance
db_provider = DatabaseFactory.get_provider()

def init_db():
    """Initialize the configured database."""
    db_provider.init_db()

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

# Initialize the database when this module is imported
init_db()
