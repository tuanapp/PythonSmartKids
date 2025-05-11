import pytest
import sqlite3
import os
import tempfile
from unittest.mock import patch, MagicMock
from datetime import datetime

from app.db.sqlite_provider import SQLiteProvider
from app.db.supabase_provider import SupabaseProvider
from app.models.schemas import MathAttempt

class TestSQLiteProvider:
    """Tests for the SQLite database provider."""
    
    @pytest.fixture
    def temp_db(self):
        """Create a temporary database file for testing."""
        fd, path = tempfile.mkstemp()
        os.close(fd)
        yield path
        os.unlink(path)
    
    def test_init_db(self, temp_db):
        """Test database initialization."""
        provider = SQLiteProvider(temp_db)
        provider.init_db()
        
        # Verify the table was created
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='attempts'")
        tables = cursor.fetchall()
        conn.close()
        
        assert len(tables) == 1
        assert tables[0][0] == 'attempts'
    
    def test_save_attempt(self, temp_db):
        """Test saving an attempt."""
        provider = SQLiteProvider(temp_db)
        provider.init_db()
        
        # Create a test attempt
        attempt = MathAttempt(
            student_id=1,
            question="1+1",
            is_answer_correct=True,
            correct_answer="2",
            incorrect_answer="",
            datetime=datetime.now()
        )
        
        # Save the attempt
        provider.save_attempt(attempt)
        
        # Verify it was saved
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM attempts")
        rows = cursor.fetchall()
        conn.close()
        
        assert len(rows) == 1
        assert rows[0][1] == 1  # student_id
        assert rows[0][3] == "1+1"  # question
        assert rows[0][4] == 1  # is_answer_correct
        assert rows[0][5] == ""  # incorrect_answer
        assert rows[0][6] == "2"  # correct_answer
    
    def test_get_attempts(self, temp_db):
        """Test retrieving attempts."""
        provider = SQLiteProvider(temp_db)
        provider.init_db()
        
        # Add some test data - Note that we're inserting them in chronological order
        # but expecting them to be returned in reverse order (most recent first)
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        # First entry - older date
        cursor.execute('''
            INSERT INTO attempts (student_id, datetime, question, is_answer_correct, incorrect_answer, correct_answer)
            VALUES (1, '2023-01-01T12:00:00', '2+2', 1, '', '4')
        ''')
        # Second entry - more recent date
        cursor.execute('''
            INSERT INTO attempts (student_id, datetime, question, is_answer_correct, incorrect_answer, correct_answer)
            VALUES (1, '2023-01-01T12:05:00', '3+3', 0, '7', '6')
        ''')
        # Third entry - for a different student
        cursor.execute('''
            INSERT INTO attempts (student_id, datetime, question, is_answer_correct, incorrect_answer, correct_answer)
            VALUES (2, '2023-01-01T12:10:00', '4+4', 1, '', '8')
        ''')
        conn.commit()
        conn.close()
        
        # Retrieve attempts for student 1
        attempts = provider.get_attempts(1)
        
        # Verify results - should be ordered by datetime DESC
        assert len(attempts) == 2
        # The most recent one (3+3) should be first
        assert attempts[0]['question'] == '3+3'
        assert attempts[0]['is_correct'] == False
        assert attempts[0]['incorrect_answer'] == '7'
        # The older one (2+2) should be second
        assert attempts[1]['question'] == '2+2'
        assert attempts[1]['is_correct'] == True
        
        # Retrieve attempts for student 2
        attempts = provider.get_attempts(2)
        assert len(attempts) == 1
        assert attempts[0]['question'] == '4+4'


class TestSupabaseProvider:
    """Tests for the Supabase database provider."""
    
    @patch('app.db.supabase_provider.create_client')
    def test_init_db(self, mock_create_client):
        """Test database initialization with Supabase."""
        mock_client = MagicMock()
        # Configure the mock to not have an error attribute
        mock_response = MagicMock()
        mock_response.error = None
        mock_client.table.return_value.select.return_value.limit.return_value.execute.return_value = mock_response
        mock_create_client.return_value = mock_client
        
        provider = SupabaseProvider('fake_url', 'fake_key')
        provider.init_db()
        
        # Verify Supabase client was created
        mock_create_client.assert_called_once_with('fake_url', 'fake_key')
        # Verify the connection check was performed
        mock_client.table.assert_called_with('attempts')
    
    @patch('app.db.supabase_provider.create_client')
    def test_save_attempt(self, mock_create_client):
        """Test saving an attempt to Supabase."""
        # Setup mock client
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.error = None  # Ensure error is explicitly None
        mock_client.table.return_value.insert.return_value.execute.return_value = mock_response
        mock_create_client.return_value = mock_client
        
        # Create provider
        provider = SupabaseProvider('fake_url', 'fake_key')
        
        # Create test attempt
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
        
        # Verify Supabase client was called correctly
        mock_client.table.assert_called_with('attempts')
        mock_client.table().insert.assert_called_once()
        
        # Get the data that was passed to insert
        call_args = mock_client.table().insert.call_args[0][0]
        assert call_args['student_id'] == 1
        assert call_args['question'] == "1+1"
        assert call_args['is_answer_correct'] == True
        assert call_args['correct_answer'] == "2"
        assert call_args['incorrect_answer'] == ""
        assert call_args['datetime'] == test_datetime.isoformat()
    
    @patch('app.db.supabase_provider.create_client')
    def test_get_attempts(self, mock_create_client):
        """Test retrieving attempts from Supabase."""
        # Setup mock client and response
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.error = None  # Ensure error is explicitly None
        mock_response.data = [
            {
                'question': '2+2',
                'is_answer_correct': True,
                'incorrect_answer': '',
                'correct_answer': '4',
                'datetime': '2023-01-01T12:00:00'
            },
            {
                'question': '3+3',
                'is_answer_correct': False,
                'incorrect_answer': '7',
                'correct_answer': '6',
                'datetime': '2023-01-01T12:05:00'
            }
        ]
        mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = mock_response
        mock_create_client.return_value = mock_client
        
        # Create provider
        provider = SupabaseProvider('fake_url', 'fake_key')
        
        # Get attempts
        attempts = provider.get_attempts(1)
        
        # Verify Supabase client was called correctly
        mock_client.table.assert_called_with('attempts')
        mock_client.table().select.assert_called_once()
        
        # Verify the returned data
        assert len(attempts) == 2
        assert attempts[0]['question'] == '2+2'
        assert attempts[0]['is_correct'] == True
        assert attempts[1]['question'] == '3+3'
        assert attempts[1]['is_correct'] == False
        assert attempts[1]['incorrect_answer'] == '7'