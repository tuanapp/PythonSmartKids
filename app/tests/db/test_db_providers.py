import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

from app.db.neon_provider import NeonProvider
from app.models.schemas import MathAttempt

class TestNeonProvider:
    """Tests for the Neon PostgreSQL database provider."""
    
    def _create_provider(self):
        """Helper method to create a test NeonProvider instance."""
        return NeonProvider(
            dbname="test_db",
            user="test_user",
            password="test_password",
            host="test_host",
            sslmode="require"
        )
    
    @patch('app.db.neon_provider.psycopg2.connect')
    def test_init_db(self, mock_connect):
        """Test database initialization with Neon PostgreSQL."""
        # Setup mock connection and cursor
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        provider = self._create_provider()
        provider.init_db()
        
        # Verify connection was made with correct parameters
        mock_connect.assert_called_once_with(
            dbname="test_db",
            user="test_user",
            password="test_password",
            host="test_host",
            sslmode="require"
        )
        
        # Verify the table creation was attempted
        mock_cursor.execute.assert_called()
        mock_conn.commit.assert_called_once()
    
    @patch('app.db.neon_provider.psycopg2.connect')
    def test_save_attempt(self, mock_connect):
        """Test saving an attempt to Neon PostgreSQL."""
        # Setup mock connection and cursor
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        # Create provider and test attempt
        provider = self._create_provider()
        test_datetime = datetime(2023, 1, 1, 12, 0, 0)
        attempt = MathAttempt(
            student_id=1,
            question="1+1",
            is_answer_correct=True,
            correct_answer="2",
            incorrect_answer="",
            datetime=test_datetime
        )
        
        # Save the attempt
        provider.save_attempt(attempt)
        
        # Verify the correct parameters were used
        call_args = mock_cursor.execute.call_args[0]
        params = call_args[1]
        assert params[0] == 1  # student_id
        assert params[1] == test_datetime  # datetime
        assert params[2] == "1+1"  # question
        assert params[3] == True  # is_answer_correct
        assert params[4] == ""  # incorrect_answer
        assert params[5] == "2"  # correct_answer
        
        mock_conn.commit.assert_called_once()
    
    @patch('app.db.neon_provider.psycopg2.connect')
    def test_get_attempts(self, mock_connect):
        """Test retrieving attempts from Neon PostgreSQL."""
        # Setup mock cursor with test data
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {
                'question': '2+2',
                'is_answer_correct': True,
                'incorrect_answer': '',
                'correct_answer': '4',
                'datetime': datetime(2023, 1, 1, 12, 0, 0)
            },
            {
                'question': '3+3',
                'is_answer_correct': False,
                'incorrect_answer': '7',
                'correct_answer': '6',
                'datetime': datetime(2023, 1, 1, 12, 5, 0)
            }
        ]
        
        # Setup mock connection
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        # Get attempts
        provider = self._create_provider()
        attempts = provider.get_attempts(1)
        
        # Verify query parameters
        call_args = mock_cursor.execute.call_args[0]
        params = call_args[1]
        assert params[0] == 1  # student_id
        
        # Verify the returned data
        assert len(attempts) == 2
        assert attempts[0]['question'] == '2+2'
        assert attempts[0]['is_correct'] == True
        assert attempts[1]['question'] == '3+3'
        assert attempts[1]['is_correct'] == False
        assert attempts[1]['incorrect_answer'] == '7'
    
    def test_get_question_patterns(self):
        """Test retrieving question patterns from Neon database"""
        provider = self._create_provider()
        
        # Mock the connection and cursor
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock the query result
        mock_patterns = [
            {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "type": "algebra",
                "pattern_text": "a + b = _",
                "created_at": "2023-01-01T12:00:00"
            }
        ]
        mock_cursor.fetchall.return_value = mock_patterns
        
        with patch.object(provider, '_get_connection', return_value=mock_conn):
            patterns = provider.get_question_patterns()
            
            # Verify the correct SQL was executed
            mock_cursor.execute.assert_called_once_with("""
                SELECT id, type, pattern_text, created_at
                FROM question_patterns
            """)
            
            # Verify the result
            assert patterns == mock_patterns
            assert len(patterns) == 1
            assert patterns[0]["type"] == "algebra"
            
        mock_cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()
    
    def test_get_question_patterns_handles_error(self):
        """Test error handling when retrieving question patterns fails"""
        provider = self._create_provider()
        
        mock_conn = MagicMock()
        mock_conn.cursor.side_effect = Exception("Database error")
        
        with patch.object(provider, '_get_connection', return_value=mock_conn):
            with pytest.raises(Exception) as exc_info:
                provider.get_question_patterns()
            
            assert "Database error" in str(exc_info.value)