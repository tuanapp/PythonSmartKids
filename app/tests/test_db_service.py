import pytest
import sqlite3
from unittest.mock import patch, MagicMock, mock_open
from app.repositories.db_service import get_attempts, save_attempt
from app.models.schemas import MathAttempt
import datetime

class TestDBService:
    """
    Test suite for database service operations.
    """
    
    @patch('app.repositories.db_service.sqlite3.connect')
    def test_get_attempts(self, mock_connect):
        """
        Test retrieving attempts for a student from the database
        """
        # Setup mock connection and cursor
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Configure mock to return some attempts
        mock_cursor.fetchall.return_value = [
            ("2+2", 1, "5", "4", "2023-01-01T12:00:00"),
            ("3+3", 1, "", "6", "2023-01-01T12:05:00")
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
        # Verify database was queried correctly
        mock_cursor.execute.assert_called_once()
        # Check that the query filters by student_id
        call_args = mock_cursor.execute.call_args[0]
        assert "WHERE student_id = ?" in call_args[0]
        assert call_args[1][0] == student_id
    
    @patch('app.repositories.db_service.sqlite3.connect')
    def test_get_attempts_empty(self, mock_connect):
        """
        Test retrieving attempts when there are none for a student
        """
        # Setup mock connection and cursor
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Configure mock to return no attempts
        mock_cursor.fetchall.return_value = []
        
        # Call the function
        student_id = 99  # Presumably doesn't exist
        results = get_attempts(student_id)
        
        # Assertions
        assert isinstance(results, list)
        assert len(results) == 0
    
    @patch('app.repositories.db_service.sqlite3.connect')
    def test_save_attempt(self, mock_connect):
        """
        Test saving an attempt to the database
        """
        # Setup mock connection and cursor
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
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
        mock_cursor.execute.assert_called_once()
        # Check that all fields are included in the INSERT
        call_args = mock_cursor.execute.call_args[0]
        assert "INSERT INTO attempts" in call_args[0]
        assert "student_id" in call_args[0]
        assert "datetime" in call_args[0]
        assert "question" in call_args[0]
        assert "is_answer_correct" in call_args[0]
        assert "incorrect_answer" in call_args[0]
        assert "correct_answer" in call_args[0]
        # Verify the commit was called
        mock_conn.commit.assert_called_once()
        
    @patch('app.repositories.db_service.sqlite3.connect')
    def test_save_attempt_handles_error(self, mock_connect):
        """
        Test error handling when saving an attempt fails
        """
        # Setup mock to raise an exception
        mock_connect.side_effect = sqlite3.Error("Database error")
        
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