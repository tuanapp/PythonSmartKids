# Pytest configuration and shared fixtures
import pytest
import sys
import os
from pathlib import Path

# Add the project root to Python path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

@pytest.fixture(scope="session")
def project_root_path():
    """Provide the project root path."""
    return project_root

@pytest.fixture(scope="session") 
def test_fixtures_path():
    """Provide the test fixtures directory path."""
    return Path(__file__).parent / "fixtures"

@pytest.fixture
def sample_uid():
    """Provide a sample UID for testing."""
    return "test-uid-12345"

@pytest.fixture
def sample_question_data():
    """Provide sample question data for testing."""
    return [
        {
            "number": 1,
            "topic": "addition",
            "pattern": "a + b = _",
            "question": "5 + 3 = _",
            "answer": 8
        },
        {
            "number": 2,
            "topic": "subtraction", 
            "pattern": "a - b = _",
            "question": "10 - 4 = _",
            "answer": 6
        }
    ]

@pytest.fixture
def sample_math_attempt():
    """Provide sample math attempt data for testing."""
    from app.models.schemas import MathAttempt
    from datetime import datetime
    
    return MathAttempt(
        student_id=1,
        uid="test-uid-12345",
        question="5 + 3 = _",
        is_answer_correct=True,
        correct_answer="8",
        incorrect_answer="",
        datetime=datetime.now()
    )
