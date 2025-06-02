import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.api.routes import router
from app.models.schemas import MathAttempt
import datetime

# Create a test FastAPI app
app = FastAPI()
app.include_router(router)

# Test client fixture
@pytest.fixture
def client():
    return TestClient(app)

# Integration Tests
@pytest.mark.integration
def test_submit_and_generate(client):
    """
    Integration test that tests submitting an attempt and then generating questions.
    This test uses more realistic mocks that preserve the interaction between components.
    """
    with patch("app.repositories.db_service.save_attempt") as mock_save_attempt, \
         patch("app.repositories.db_service.get_attempts") as mock_get_attempts, \
         patch("app.repositories.db_service.get_question_patterns") as mock_get_patterns, \
         patch("app.services.ai_service.generate_practice_questions") as mock_generate_questions:
          # First submit an attempt
        attempt_data = {
            "student_id": 1,
            "uid": "test-firebase-integration-uid",
            "question": "2+2",
            "is_answer_correct": True,
            "incorrect_answer": "",
            "correct_answer": "4",
            "datetime": "2023-01-01T12:00:00"
        }
        submit_response = client.post("/submit_attempt", json=attempt_data)
        assert submit_response.status_code == 200
        
        # Then generate questions
        mock_get_attempts.return_value = [
            {
                "question": "2+2",
                "is_correct": True,
                "incorrect_answer": "",
                "correct_answer": "4", 
                "datetime": "2023-01-01T12:00:00"
            }
        ]
        mock_patterns = [
            {
                "id": "123",
                "type": "addition",
                "pattern_text": "a + b = _",
                "created_at": "2023-01-01T12:00:00"
            }
        ]
        mock_get_patterns.return_value = mock_patterns
        mock_generate_questions.return_value = {
            "questions": {
                "Addition": "3+3",
                "Subtraction": "5-2"
            },
            "timestamp": None
        }
        
        generate_response = client.post("/generate-questions/1")
        assert generate_response.status_code == 200
        
        # Verify the response contains questions
        questions = generate_response.json()["questions"]
        assert isinstance(questions, dict)
        assert len(questions) > 0
        
        # Verify the mock calls include patterns
        mock_generate_questions.assert_called_with(mock_get_attempts.return_value, mock_patterns)

@pytest.mark.integration
def test_full_api_flow(client):
    """
    A more comprehensive integration test that tests the entire API flow.
    """
    # This would typically use more extensive mocks or actual test databases
    with patch("app.repositories.db_service.save_attempt") as mock_save_attempt, \
         patch("app.repositories.db_service.get_attempts") as mock_get_attempts, \
         patch("app.repositories.db_service.get_question_patterns") as mock_get_patterns, \
         patch("app.services.ai_service.generate_practice_questions") as mock_generate_questions, \
         patch("app.services.ai_service.get_analysis") as mock_get_analysis:
          # Submit an attempt
        attempt_data = {
            "student_id": 1,
            "uid": "test-firebase-uid-integration-2",
            "question": "2+2",
            "is_answer_correct": True,
            "incorrect_answer": "",
            "correct_answer": "4",
            "datetime": "2023-01-01T12:00:00"
        }
        client.post("/submit_attempt", json=attempt_data)
          # Mock attempt retrieval
        mock_get_attempts.return_value = [
            {
                "question": "2+2",
                "is_correct": True,
                "incorrect_answer": "",
                "correct_answer": "4", 
                "datetime": "2023-01-01T12:00:00",
                "uid": "test-firebase-uid-mock-integration"
            }
        ]
        
        # Mock patterns
        mock_patterns = [
            {
                "id": "123",
                "type": "addition",
                "pattern_text": "a + b = _",
                "created_at": "2023-01-01T12:00:00"
            }
        ]
        mock_get_patterns.return_value = mock_patterns
        
        # Mock analysis generation
        mock_get_analysis.return_value = {
            "strengths": ["addition"],
            "weaknesses": [],
            "recommendations": ["Try more complex addition"]
        }
        
        # Test analyze endpoint
        analyze_response = client.get("/analyze_student/1")
        assert analyze_response.status_code == 200
        analysis = analyze_response.json()
        assert "strengths" in analysis
        
        # Mock generated questions
        mock_generate_questions.return_value = {
            "questions": {
                "Addition": "3+3",
                "AdditionX": "__ + 2 = 5",
                "Multiplication": "4×5",
                "Division": "10÷2"
            },
            "timestamp": None
        }
        
        # Generate new questions
        generate_response = client.post("/generate-questions/1")
        assert generate_response.status_code == 200
        questions = generate_response.json()
        assert "questions" in questions
        # Just check that we have some questions, don't check the exact number
        assert len(questions["questions"]) >= 1
        
        # Verify patterns were used
        mock_generate_questions.assert_called_with(mock_get_attempts.return_value, mock_patterns)

@pytest.mark.integration
def test_analyze_and_generate_cycle(client):
    """
    Integration test that simulates a typical usage pattern:
    1. Submit an attempt
    2. Analyze the student performance 
    3. Generate new questions based on analysis
    """
    with patch("app.repositories.db_service.save_attempt") as mock_save_attempt, \
         patch("app.repositories.db_service.get_attempts") as mock_get_attempts, \
         patch("app.repositories.db_service.get_question_patterns") as mock_get_patterns, \
         patch("app.services.ai_service.get_analysis") as mock_get_analysis, \
         patch("app.services.ai_service.generate_practice_questions") as mock_generate_questions:
        
        # Submit multiple attempts
        for question, correct_answer, is_answer_correct, incorrect_answer in [
            ("2+2", "4", True, ""),            ("3+5", "8", True, ""),
            ("7-3", "4", False, "5")
        ]:
            attempt_data = {
                "student_id": 1,
                "uid": f"test-firebase-uid-integration-loop-{question}",
                "question": question,
                "is_answer_correct": is_answer_correct,
                "correct_answer": correct_answer,
                "incorrect_answer": incorrect_answer,
                "datetime": "2023-01-01T12:00:00"
            }
            submit_response = client.post("/submit_attempt", json=attempt_data)
            assert submit_response.status_code == 200
            assert question in submit_response.json()["message"]
        
        # Set up data for analysis and generation
        attempts = [
            {
                "question": q,
                "is_correct": c,
                "incorrect_answer": i,
                "correct_answer": a,
                "datetime": "2023-01-01T12:00:00",
                "uid": f"test-firebase-uid-analysis-{q.replace('+', 'plus').replace('-', 'minus')}"
            }
            for q, a, c, i in [
                ("2+2", "4", True, ""),
                ("3+5", "8", True, ""),
                ("7-3", "4", False, "5")
            ]
        ]
        mock_get_attempts.return_value = attempts

        patterns = [
            {
                "id": "123",
                "type": "addition",
                "pattern_text": "a + b = _",
                "created_at": "2023-01-01T12:00:00"
            },
            {
                "id": "124",
                "type": "subtraction",
                "pattern_text": "a - b = _",
                "created_at": "2023-01-01T12:00:00"
            }
        ]
        mock_get_patterns.return_value = patterns
        
        # Mock analysis
        analysis_result = {
            "strengths": ["addition"],
            "weaknesses": ["subtraction"],
            "recommendations": ["Practice more subtraction"]
        }
        mock_get_analysis.return_value = analysis_result
        
        # Get analysis
        analyze_response = client.get("/analyze_student/1")
        assert analyze_response.status_code == 200
        analysis = analyze_response.json()
        assert analysis["weaknesses"] == ["subtraction"]
        
        # Mock generated questions focusing on weaknesses - match the actual structure
        mock_generate_questions.return_value = {
            "questions": {
                "Subtraction": "9-4",
                "SubtractionX": "10-7",
                "Addition": "5+3"
            },
            "timestamp": None
        }
        
        # Generate new questions
        generate_response = client.post("/generate-questions/1")
        assert generate_response.status_code == 200
        questions = generate_response.json()["questions"]
        assert "Subtraction" in questions  # Verify focus on weak area
        assert "Addition" in questions     # Verify including some strong area questions
        
        # Verify the flow of data
        mock_get_attempts.assert_called()
        mock_get_patterns.assert_called()
        mock_generate_questions.assert_called_with(attempts, patterns)

@pytest.mark.integration
def test_question_patterns_endpoint(client):
    """
    Integration test for the question patterns endpoint
    """
    with patch("app.repositories.db_service.get_question_patterns") as mock_get_patterns:
        # Mock patterns
        mock_patterns = [
            {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "type": "algebra",
                "pattern_text": "a + b = _",
                "created_at": "2023-01-01T12:00:00"
            },
            {
                "id": "223e4567-e89b-12d3-a456-426614174001",
                "type": "fraction",
                "pattern_text": "_ / _ = 1",
                "created_at": "2023-01-01T12:00:00"
            }
        ]
        mock_get_patterns.return_value = mock_patterns
        
        # Test the endpoint
        response = client.get("/question-patterns")
        assert response.status_code == 200
        
        # Verify response structure
        patterns = response.json()
        assert len(patterns) == 2
        assert all(key in patterns[0] for key in ["id", "type", "pattern_text", "created_at"])
        assert patterns[0]["type"] == "algebra"
        assert patterns[1]["type"] == "fraction"

@pytest.mark.integration
def test_question_patterns_endpoint_empty(client):
    """
    Integration test for the question patterns endpoint when no patterns exist
    """
    with patch("app.repositories.db_service.get_question_patterns") as mock_get_patterns:
        # Mock empty patterns list
        mock_get_patterns.return_value = []
        
        # Test the endpoint
        response = client.get("/question-patterns")
        assert response.status_code == 200
        
        # Verify empty response
        patterns = response.json()
        assert isinstance(patterns, list)
        assert len(patterns) == 0

@pytest.mark.integration
def test_question_patterns_endpoint_error(client):
    """
    Integration test for the question patterns endpoint error handling
    """
    with patch("app.repositories.db_service.get_question_patterns") as mock_get_patterns:
        # Mock database error
        mock_get_patterns.side_effect = Exception("Database error")
        
        # Test the endpoint
        response = client.get("/question-patterns")
        assert response.status_code == 500
        assert "Failed to retrieve question patterns" in response.json()["detail"]