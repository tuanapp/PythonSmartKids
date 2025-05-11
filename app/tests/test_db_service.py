import pytest
from unittest.mock import patch, MagicMock
from app.repositories.db_service import get_attempts, save_attempt
from app.models.schemas import MathAttempt
import datetime

class TestDBService:
    """
    Test suite for database service operations.
    """
    
    @patch('app.repositories.db_service.db_provider')
    def test_get_attempts(self, mock_db_provider):
        """
        Test retrieving attempts for a student from the database
        """
        # Configure mock to return some attempts
        mock_db_provider.get_attempts.return_value = [
            {
                "question": "2+2",
                "is_correct": True,
                "incorrect_answer": "5",
                "correct_answer": "4",
                "datetime": "2023-01-01T12:00:00"
            },
            {
                "question": "3+3",
                "is_correct": True,
                "incorrect_answer": "",
                "correct_answer": "6",
                "datetime": "2023-01-01T12:05:00"
            }
        ]
        
        # Call the function
        student_id = 1
        results = get_attempts(student_id)
        
        # Assertions
        assert len(results) == 2
        assert results[0]["question"] == "2+2"
        assert results[0]["is_correct"] == True
        assert results[0]["correct_answer"] == "4"
        assert results[0]["incorrect_answer"] == "5"
        assert results[1]["question"] == "3+3"
        
        # Verify database provider was called correctly
        mock_db_provider.get_attempts.assert_called_once_with(student_id)
    
    @patch('app.repositories.db_service.db_provider')
    def test_get_attempts_empty(self, mock_db_provider):
        """
        Test retrieving attempts when there are none for a student
        """
        # Configure mock to return no attempts
        mock_db_provider.get_attempts.return_value = []
        
        # Call the function
        student_id = 99  # Presumably doesn't exist
        results = get_attempts(student_id)
        
        # Assertions
        assert isinstance(results, list)
        assert len(results) == 0
        mock_db_provider.get_attempts.assert_called_once_with(student_id)
    
    @patch('app.repositories.db_service.db_provider')
    def test_save_attempt(self, mock_db_provider):
        """
        Test saving an attempt to the database
        """
        # Create a test attempt
        attempt = MathAttempt(
            student_id=1,
            question="5+5",
            is_answer_correct=False,
            correct_answer="10",
            incorrect_answer="11",
            datetime=datetime.datetime.now()
        )
        
        # Call the function
        save_attempt(attempt)
        
        # Assertions
        mock_db_provider.save_attempt.assert_called_once_with(attempt)
        
    @patch('app.repositories.db_service.db_provider')
    def test_save_attempt_handles_error(self, mock_db_provider):
        """
        Test error handling when saving an attempt fails
        """
        # Setup mock to raise an exception
        mock_db_provider.save_attempt.side_effect = Exception("Database error")
        
        # Create a test attempt
        attempt = MathAttempt(
            student_id=1,
            question="5+5",
            is_answer_correct=False,
            correct_answer="10",
            incorrect_answer="11",
            datetime=datetime.datetime.now()
        )
        
        # Call the function and check it handles the exception
        with pytest.raises(Exception):
            save_attempt(attempt)