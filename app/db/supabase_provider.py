import logging
from typing import List, Dict, Any
from supabase import create_client, Client
from app.models.schemas import MathAttempt
from app.db.db_interface import DatabaseProvider

logger = logging.getLogger(__name__)

class SupabaseProvider(DatabaseProvider):
    """Supabase implementation of the database provider."""
    
    def __init__(self, url: str, key: str):
        self.url = url
        self.key = key
        self.client = create_client(url, key)
        
    def init_db(self) -> None:
        """
        Initialize the Supabase database.
        
        Note: Actual table creation in Supabase is typically done through migrations
        or directly in the Supabase dashboard. This method is primarily a placeholder
        to conform to the interface.
        """
        logger.info("Connected to Supabase at %s", self.url)
        # Check if we can connect to Supabase
        try:
            # Just query to check connection
            self.client.table('attempts').select('*').limit(1).execute()
            logger.info("Successfully connected to Supabase table 'attempts'")
        except Exception as e:
            logger.error(f"Failed to connect to Supabase: {e}")
            logger.warning("You may need to create the 'attempts' table in your Supabase dashboard")
            logger.info("Table schema: id (serial primary key), student_id, datetime, question, is_answer_correct, incorrect_answer, correct_answer")
    
    def save_attempt(self, attempt: MathAttempt) -> None:
        """Save a math attempt to the Supabase database."""
        try:
            # Convert attempt to dict, ensuring proper datetime handling
            attempt_data = {
                "student_id": attempt.student_id,
                "datetime": attempt.datetime.isoformat(),
                "question": attempt.question,
                "is_answer_correct": attempt.is_answer_correct,
                "incorrect_answer": attempt.incorrect_answer or "",
                "correct_answer": attempt.correct_answer
            }
            
            # Insert the data into Supabase
            result = self.client.table('attempts').insert(attempt_data).execute()
            
            if hasattr(result, 'error') and result.error:
                raise Exception(f"Supabase error: {result.error}")
                
            logger.debug(f"Attempt saved for student {attempt.student_id}")
        except Exception as e:
            logger.error(f"Error saving attempt to Supabase: {e}")
            raise Exception(f"Database error: {e}")
    
    def get_attempts(self, student_id: int) -> List[Dict[str, Any]]:
        """Retrieve attempts for a specific student from the Supabase database."""
        try:
            # Query Supabase for attempts by student_id
            response = self.client.table('attempts') \
                .select('question', 'is_answer_correct', 'incorrect_answer', 'correct_answer', 'datetime') \
                .eq('student_id', student_id) \
                .order('datetime', desc=True) \
                .limit(50) \
                .execute()
            
            if hasattr(response, 'error') and response.error:
                raise Exception(f"Supabase error: {response.error}")
            
            data = response.data
            
            # Format the data to match the expected schema
            attempts = [{
                "question": item['question'],
                "is_correct": bool(item['is_answer_correct']),
                "incorrect_answer": item['incorrect_answer'] if item['incorrect_answer'] else "",
                "correct_answer": str(item['correct_answer']) if item['correct_answer'] else "",
                "datetime": item['datetime']
            } for item in data]
            
            logger.debug(f"Retrieved {len(attempts)} attempts for student {student_id}")
            return attempts
        except Exception as e:
            logger.error(f"Error retrieving attempts from Supabase: {e}")
            raise Exception(f"Database error: {e}")