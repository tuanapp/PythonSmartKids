import pytest
import sqlite3
import os
import tempfile
from unittest.mock import patch, MagicMock
from datetime import datetime

from app.db.sqlite_provider import SQLiteProvider
from app.db.neon_provider import NeonProvider
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


class TestNeonProvider:
    """Tests for the Neon PostgreSQL database provider."""
    
    @patch('app.db.neon_provider.psycopg2.connect')
    def test_init_db(self, mock_connect):
        """Test database initialization with Neon PostgreSQL."""
        # Setup mock connection and cursor
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        provider = NeonProvider(
            dbname="test_db",
            user="test_user",
            password="test_password",
            host="test_host",
            sslmode="require"
        )
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
        
        # Create provider
        provider = NeonProvider(
            dbname="test_db",
            user="test_user",
            password="test_password",
            host="test_host",
            sslmode="require"
        )
        
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
        
        # Verify the database connection was made
        mock_connect.assert_called_once()
        
        # Verify cursor.execute was called to insert data
        mock_cursor.execute.assert_called_once()
        
        # Get the parameters that were passed to execute
        call_args = mock_cursor.execute.call_args[0]
        # First argument is SQL query, second is parameters
        params = call_args[1]
        assert params[0] == 1  # student_id
        assert params[1] == test_datetime  # datetime
        assert params[2] == "1+1"  # question
        assert params[3] == True  # is_answer_correct
        assert params[4] == ""  # incorrect_answer
        assert params[5] == "2"  # correct_answer
        
        # Verify commit was called
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
        
        # Create provider
        provider = NeonProvider(
            dbname="test_db",
            user="test_user",
            password="test_password",
            host="test_host",
            sslmode="require"
        )
        
        # Get attempts
        attempts = provider.get_attempts(1)
        
        # Verify the connection was made
        mock_connect.assert_called_once()
        
        # Verify cursor was created with the right factory
        mock_conn.cursor.assert_called_once()
        
        # Verify query execution
        mock_cursor.execute.assert_called_once()
        
        # Check that the student_id parameter was used in the query
        call_args = mock_cursor.execute.call_args[0]
        params = call_args[1]
        assert params[0] == 1  # student_id
        
        # Verify the returned data structure
        assert len(attempts) == 2
        assert attempts[0]['question'] == '2+2'
        assert attempts[0]['is_correct'] == True
        assert attempts[1]['question'] == '3+3'
        assert attempts[1]['is_correct'] == False
        assert attempts[1]['incorrect_answer'] == '7'