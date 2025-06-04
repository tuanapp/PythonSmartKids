import pytest
from unittest.mock import patch, MagicMock
from app.services.ai_service import generate_practice_questions, get_analysis

class TestAIService:
    """
    Test suite for the AI service which handles generating questions and analysis.
    """
    
    def test_generate_practice_questions_with_attempts(self):
        """
        Test that generate_practice_questions produces appropriate questions 
        when there are previous attempts.
        """
        # Mock attempts that show proficiency in addition but weakness in subtraction
        attempts = [
            {
                "question": "2+2", 
                "answer": "4", 
                "is_correct": False, 
                "incorrect_answer": "5",
                "correct_answer": "4",
                "datetime": "2023-01-01T12:00:00"
            },
            {
                "question": "3+5", 
                "answer": "8", 
                "is_correct": True,
                "incorrect_answer": "",
                "correct_answer": "8",
                "datetime": "2023-01-01T12:00:00"
            },
            {
                "question": "7-3", 
                "answer": "5", 
                "is_correct": False,
                "incorrect_answer": "5",
                "correct_answer": "4",
                "datetime": "2023-01-01T12:00:00"
            }
        ]

        # Mock patterns
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
        
        # Test with mock OpenAI client
        with patch("app.services.ai_service.client.chat.completions.create") as mock_openai_create:
            # Configure the mock
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = '''{
                "Addition": "9-4",
                "Subtraction": "10-7"
            }'''
            mock_openai_create.return_value = mock_response
            
            # Call the function
            result = generate_practice_questions(attempts, patterns)
            
            # Assertions
            assert isinstance(result, dict)
            assert "questions" in result
            questions = result["questions"]
            assert "Addition" in questions
            assert "Subtraction" in questions
            # Verify OpenAI was called with appropriate context
            mock_openai_create.assert_called_once()
            call_args = mock_openai_create.call_args[1]
            assert "role" in call_args["messages"][0]
            assert "content" in call_args["messages"][0]
    
    def test_generate_practice_questions_no_attempts(self):
        """
        Test that generate_practice_questions produces beginner-level questions
        when there are no previous attempts.
        """
        # No need to mock OpenAI for empty attempts since it uses generate_fallback_questions
        result = generate_practice_questions([])
        
        # Assertions
        assert isinstance(result, dict)
        assert "questions" in result
        questions = result["questions"]
        # Check that it contains basic operation types
        assert any(key.startswith("Addition") for key in questions.keys())
        assert any(key.startswith("Multiplication") for key in questions.keys())
        assert any(key.startswith("Division") for key in questions.keys())
        assert any(key.startswith("SubtractionX") for key in questions.keys())
    
    def test_get_analysis(self):
        """
        Test that get_analysis produces a meaningful analysis of student performance.
        """
        # Mock attempts with mixed performance
        attempts = [
            {"question": "2+2", "answer": "4", "is_correct": True},
            {"question": "3+5", "answer": "8", "is_correct": True},
            {"question": "4*3", "answer": "12", "is_correct": True},
            {"question": "7-3", "answer": "5", "is_correct": False},
            {"question": "10-7", "answer": "2", "is_correct": False}
        ]
        
        with patch("app.services.ai_service.client.chat.completions.create") as mock_openai_create:
            # Configure the mock
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = '''{
                "strengths": ["addition", "multiplication"],
                "weaknesses": ["subtraction"],
                "recommendations": ["Practice more subtraction"]
            }'''
            mock_openai_create.return_value = mock_response
            
            # Call the function
            result = get_analysis(attempts)
            
            # Assertions
            assert isinstance(result, dict)
            # Verify OpenAI was called
            mock_openai_create.assert_called_once()

            #test