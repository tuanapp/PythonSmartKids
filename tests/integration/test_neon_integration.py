"""
Integration tests for directly interacting with the Neon PostgreSQL database.
These tests perform real operations against the database without mocks.
"""
import pytest
import datetime
import uuid
import os
import psycopg2
from dotenv import load_dotenv
from app.db.neon_provider import NeonProvider
from app.models.schemas import MathAttempt

# Load environment variables from .env file
load_dotenv()

# Get Neon credentials from environment variables or use defaults
NEON_DBNAME = os.getenv("NEON_DBNAME", "smartboydb")
NEON_USER = os.getenv("NEON_USER", "tuanapp")
NEON_PASSWORD = os.getenv("NEON_PASSWORD", "HdzrNIKh5mM1")
NEON_HOST = os.getenv("NEON_HOST", "ep-sparkling-butterfly-33773987-pooler.ap-southeast-1.aws.neon.tech")
NEON_SSLMODE = os.getenv("NEON_SSLMODE", "require")

# Define a fixed student ID for testing insert and delete operations
FIXED_STUDENT_ID = 9999999
FIXED_UID = "test-fixed-firebase-uid"

@pytest.fixture
def neon_provider():
    """Fixture to provide a configured Neon PostgreSQL provider."""
    provider = NeonProvider(
        dbname=NEON_DBNAME,
        user=NEON_USER,
        password=NEON_PASSWORD,
        host=NEON_HOST,
        sslmode=NEON_SSLMODE
    )
    return provider

@pytest.fixture
def unique_student_id():
    """Generate a unique student ID for test isolation."""
    return int(uuid.uuid4().int % 100000000)  # Ensure it's a reasonable-sized integer

@pytest.fixture
def unique_uid():
    """Generate a unique UID for test isolation."""
    return f"test-uid-{uuid.uuid4()}"

@pytest.fixture
def neon_connection():
    """Create a direct connection to the Neon PostgreSQL database."""
    conn = psycopg2.connect(
        dbname=NEON_DBNAME,
        user=NEON_USER,
        password=NEON_PASSWORD,
        host=NEON_HOST,
        sslmode=NEON_SSLMODE
    )
    conn.autocommit = True  # Set autocommit for this connection
    yield conn
    conn.close()

@pytest.mark.integration
@pytest.mark.neon
def test_insert_attempt_to_neon(neon_provider, unique_student_id):
    """Test directly inserting a record into the Neon PostgreSQL attempts table."""    # Create a test attempt with a timestamp that will be easily identifiable
    test_attempt = MathAttempt(
        student_id=unique_student_id,
        uid="test-firebase-uid-integration",
        question="5+7",
        is_answer_correct=True,
        incorrect_answer=None,
        correct_answer="12",
        datetime=datetime.datetime.now()
    )
    
    # Save the attempt to Neon
    neon_provider.save_attempt(test_attempt)
    
    # Verify by retrieving and checking if at least one attempt exists
    attempts = neon_provider.get_attempts(unique_student_id)
    assert len(attempts) > 0, "No attempts were saved to Neon PostgreSQL"
    
    # Verify the content of the saved attempt
    latest_attempt = attempts[0]  # Should be the most recent one
    assert latest_attempt["question"] == "5+7"
    assert latest_attempt["is_correct"] is True
    assert latest_attempt["correct_answer"] == "12"

@pytest.mark.integration
@pytest.mark.neon
def test_read_attempt_from_neon(neon_provider, unique_student_id):
    """Test reading records from the Neon PostgreSQL attempts table."""
    # Create a few test attempts with different data
    for i, (question, answer, is_correct) in enumerate([
        ("2+2", "4", True),
        ("3+5", "8", True),
        ("7-3", "4", False)
    ]):
        attempt = MathAttempt(
            student_id=unique_student_id,
            uid=f"test-firebase-uid-{i}",
            question=question,
            is_answer_correct=is_correct,
            incorrect_answer="5" if not is_correct else None,
            correct_answer=answer,
            datetime=datetime.datetime.now() + datetime.timedelta(minutes=i)
        )
        neon_provider.save_attempt(attempt)
    
    # Read all attempts for this student
    attempts = neon_provider.get_attempts(unique_student_id)
    
    # Verify the number of attempts retrieved
    assert len(attempts) >= 3, "Not all test attempts were retrieved"
    
    # Due to ordering by datetime desc, the attempts should be in reverse order
    assert attempts[0]["question"] == "7-3"
    assert attempts[0]["is_correct"] is False
    
    # Check a specific field in the second attempt
    assert attempts[1]["question"] == "3+5"
    assert attempts[1]["correct_answer"] == "8"

@pytest.mark.integration
@pytest.mark.neon
def test_database_connection(neon_provider):
    """Test basic database connection and initialization."""
    try:
        # Initialize the database (this should create the table if it doesn't exist)
        neon_provider.init_db()
        
        # Get a connection to verify it works
        conn = neon_provider._get_connection()
        cursor = conn.cursor()
        
        # Run a simple query to check connection
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        assert result[0] == 1, "Database connection test failed"
    except Exception as e:
        pytest.fail(f"Database connection failed with error: {e}")

@pytest.mark.integration
@pytest.mark.neon
def test_insert_fixed_record(neon_provider):
    """Test inserting a record with a fixed student ID."""
    # First, clean up any existing records with this student ID
    conn = psycopg2.connect(
        dbname=NEON_DBNAME,
        user=NEON_USER,
        password=NEON_PASSWORD,
        host=NEON_HOST,
        sslmode=NEON_SSLMODE
    )
    conn.autocommit = True
    cursor = conn.cursor()
    cursor.execute("DELETE FROM attempts WHERE student_id = %s", (FIXED_STUDENT_ID,))
    cursor.close()
    conn.close()
      # Create a test attempt with the fixed student ID
    test_attempt = MathAttempt(
        student_id=FIXED_STUDENT_ID,
        uid="test-firebase-uid-fixed",
        question="10+15",
        is_answer_correct=True,
        incorrect_answer=None,
        correct_answer="25",
        datetime=datetime.datetime.now()
    )
    
    # Save the attempt to Neon
    neon_provider.save_attempt(test_attempt)
    
    # Verify by retrieving the record
    attempts = neon_provider.get_attempts(FIXED_STUDENT_ID)
    assert len(attempts) > 0, "No attempt was saved with the fixed student ID"
    
    # Verify the content of the saved attempt
    latest_attempt = attempts[0]
    assert latest_attempt["question"] == "10+15"
    assert latest_attempt["is_correct"] is True
    assert latest_attempt["correct_answer"] == "25"
    print(f"Successfully inserted record with fixed student ID: {FIXED_STUDENT_ID}")

@pytest.mark.integration
@pytest.mark.neon
def test_get_attempts_by_uid(neon_provider, unique_uid):
    """Test retrieving records by UID from the Neon PostgreSQL attempts table."""
    # Create a test attempt with a unique UID
    unique_student_id = int(uuid.uuid4().int % 100000000)
    
    # Create a few test attempts with the same UID but different data
    for i, (question, answer, is_correct) in enumerate([
        ("2+2", "4", True),
        ("3+5", "8", True),
        ("7-3", "4", False)
    ]):
        attempt = MathAttempt(
            student_id=unique_student_id + i,  # Different student IDs
            uid=unique_uid,  # Same UID for all attempts
            question=question,
            is_answer_correct=is_correct,
            incorrect_answer="5" if not is_correct else None,
            correct_answer=answer,
            datetime=datetime.datetime.now() + datetime.timedelta(minutes=i)
        )
        neon_provider.save_attempt(attempt)
    
    # Retrieve attempts by UID
    attempts = neon_provider.get_attempts_by_uid(unique_uid)
    
    # Verify the number of attempts retrieved
    assert len(attempts) >= 3, "Not all test attempts were retrieved by UID"
    
    # Due to ordering by datetime desc, the attempts should be in reverse order
    assert attempts[0]["question"] == "7-3"
    assert attempts[0]["is_correct"] is False
    assert attempts[0]["uid"] == unique_uid
    
    # Check a specific field in the second attempt
    assert attempts[1]["question"] == "3+5"
    assert attempts[1]["correct_answer"] == "8"
    assert attempts[1]["uid"] == unique_uid
    
    # Additional check for the first attempt
    assert attempts[2]["question"] == "2+2"
    assert attempts[2]["uid"] == unique_uid

@pytest.mark.integration
@pytest.mark.neon
def test_delete_fixed_record(neon_connection):
    """Test deleting a record with a fixed student ID."""
    cursor = neon_connection.cursor()
    
    # First verify that the record exists
    cursor.execute("SELECT COUNT(*) FROM attempts WHERE student_id = %s", (FIXED_STUDENT_ID,))
    count_before = cursor.fetchone()[0]
    assert count_before > 0, f"No records found with student ID {FIXED_STUDENT_ID} to delete"
    
    # Delete the record(s)
    cursor.execute("DELETE FROM attempts WHERE student_id = %s", (FIXED_STUDENT_ID,))
    
    # Verify deletion
    cursor.execute("SELECT COUNT(*) FROM attempts WHERE student_id = %s", (FIXED_STUDENT_ID,))
    count_after = cursor.fetchone()[0]
    cursor.close()
    
    assert count_after == 0, f"Failed to delete all records with student ID {FIXED_STUDENT_ID}"
    print(f"Successfully deleted records with fixed student ID: {FIXED_STUDENT_ID}")