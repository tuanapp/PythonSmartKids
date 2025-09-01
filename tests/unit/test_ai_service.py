import pytest
from unittest.mock import patch, MagicMock
from app.services.ai_service import generate_practice_questions, get_analysis


class TestAIService:
    """Test suite for the AI service which handles generating questions and analysis."""
    
    def test_generate_practice_questions_with_attempts(self):
        """Test that generate_practice_questions produces appropriate questions when there are previous attempts."""
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

        # Mock patterns with level information
        patterns = [
            {
                "id": "123",
                "type": "addition",
                "pattern_text": "a + b = _",
                "created_at": "2023-01-01T12:00:00",
                "level": 2
            },
            {
                "id": "124",
                "type": "subtraction",
                "pattern_text": "a - b = _",
                "created_at": "2023-01-01T12:00:00",
                "level": 2
            }
        ]
        
        # Mock the OpenAI response to match expected format (array of questions)
        mock_ai_response = [
            {
                "number": 1,
                "topic": "addition",
                "pattern": "a + b = _",
                "question": "9 + 4 = _",
                "answer": "13"
            },
            {
                "number": 2,
                "topic": "subtraction", 
                "pattern": "a - b = _",
                "question": "10 - 7 = _",
                "answer": "3"
            }
        ]        # Test with mock OpenAI client and validator
        with patch("app.services.ai_service.OpenAI") as mock_openai_class, \
             patch("app.services.ai_service.OpenAIResponseValidator") as mock_validator_class:
            
            # Configure the OpenAI client mock
            mock_client = MagicMock()
            mock_openai_class.return_value = mock_client
            
            # Configure the completion mock
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = str(mock_ai_response).replace("'", '"')
            mock_client.chat.completions.create.return_value = mock_response
            
            # Configure the validator mock
            mock_validator = MagicMock()
            mock_validator_class.return_value = mock_validator
            mock_validator.validate_partial_response.return_value = {
                'is_valid': True,
                'questions': mock_ai_response,
                'errors': [],
                'warnings': []
            }
            mock_validator.get_validation_summary.return_value = "Validation successful"
            
            # Call the function with level parameter
            result = generate_practice_questions(attempts, patterns, level=2)
            
            # Assertions
            assert isinstance(result, dict)
            assert "questions" in result
            questions = result["questions"]
            assert isinstance(questions, list)
            assert len(questions) > 0
            
            # Check that questions have the expected structure
            for question in questions:
                assert "number" in question
                assert "topic" in question
                assert "question" in question
                assert "answer" in question
            
            # Check that validation_result includes level information
            assert "validation_result" in result
            assert result["validation_result"]["level"] == 2
            
            # Verify OpenAI client was created and called
            mock_openai_class.assert_called_once()
            mock_client.chat.completions.create.assert_called_once()
    
    def test_generate_practice_questions_no_attempts(self):
        """Test that generate_practice_questions produces beginner-level questions when there are no previous attempts."""
        # Empty patterns list for testing
        patterns = []
        
        # Call the function with empty attempts and patterns, no level specified
        result = generate_practice_questions([], patterns, level=None)
        
        # Assertions - when no valid attempts, the function should still return fallback questions
        assert isinstance(result, dict)
        assert "questions" in result
        questions = result["questions"]
        assert isinstance(questions, list)
        assert len(questions) > 0
        
        # Check that questions have the expected structure
        for question in questions:
            assert "number" in question
            assert "topic" in question
            assert "question" in question
            assert "answer" in question
            
        # Verify topics include basic math operations
        topics = [q["topic"] for q in questions]
        # Should have basic math topics from fallback questions
        assert any("addition" in topic.lower() for topic in topics)
        
        # Check that validation_result includes level information (should be None)
        assert "validation_result" in result
        assert result["validation_result"]["level"] is None
    
    def test_generate_practice_questions_with_level_filtering(self):
        """Test that generate_practice_questions correctly handles level filtering."""
        # Mock attempts
        attempts = [
            {
                "question": "2+2", 
                "answer": "4", 
                "is_correct": True, 
                "incorrect_answer": "",
                "correct_answer": "4",
                "datetime": "2023-01-01T12:00:00"
            }
        ]

        # Mock patterns with different levels
        patterns = [
            {
                "id": "123",
                "type": "addition",
                "pattern_text": "a + b = _",
                "created_at": "2023-01-01T12:00:00",
                "level": 3
            }
        ]
        
        # Mock the OpenAI response
        mock_ai_response = [
            {
                "number": 1,
                "topic": "addition",
                "pattern": "a + b = _",
                "question": "15 + 27 = _",
                "answer": "42"
            }
        ]
        
        # Test with mock OpenAI client and validator for level 3
        with patch("app.services.ai_service.OpenAI") as mock_openai_class, \
             patch("app.services.ai_service.OpenAIResponseValidator") as mock_validator_class:
            
            # Configure the OpenAI client mock
            mock_client = MagicMock()
            mock_openai_class.return_value = mock_client
            
            # Configure the completion mock
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = str(mock_ai_response).replace("'", '"')
            mock_client.chat.completions.create.return_value = mock_response
            
            # Configure the validator mock
            mock_validator = MagicMock()
            mock_validator_class.return_value = mock_validator
            mock_validator.validate_partial_response.return_value = {
                'is_valid': True,
                'questions': mock_ai_response,
                'errors': [],
                'warnings': []
            }
            mock_validator.get_validation_summary.return_value = "Validation successful"
            
            # Call the function with specific level
            result = generate_practice_questions(attempts, patterns, level=3)
            
            # Assertions
            assert isinstance(result, dict)
            assert "questions" in result
            assert "validation_result" in result
            assert result["validation_result"]["level"] == 3
            
            # Verify OpenAI client was created and called
            mock_openai_class.assert_called_once()
            mock_client.chat.completions.create.assert_called_once()
    
    def test_generate_practice_questions_fallback_with_level(self):
        """Test that fallback questions include level information."""
        # Empty patterns and attempts to trigger fallback
        patterns = []
        attempts = []
        
        # Call function with level specified
        result = generate_practice_questions(attempts, patterns, level=4)
        
        # Should get fallback questions
        assert isinstance(result, dict)
        assert "questions" in result
        assert len(result["questions"]) > 0
        
        # Check that level is preserved in fallback
        assert "validation_result" in result
        assert result["validation_result"]["level"] == 4
    
    def test_get_analysis(self):
        """Test that get_analysis produces a meaningful analysis of student performance."""
        # Mock attempts with mixed performance
        attempts = [
            {"question": "2+2", "answer": "4", "is_correct": True},
            {"question": "3+5", "answer": "8", "is_correct": True},
            {"question": "4*3", "answer": "12", "is_correct": True},
            {"question": "7-3", "answer": "5", "is_correct": False},
            {"question": "10-7", "answer": "2", "is_correct": False}        ]
        with patch("app.services.ai_service.client.chat.completions.create") as mock_openai_create:
            # Configure the mock
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = '{"strengths": ["addition", "multiplication"], "weaknesses": ["subtraction"], "recommendations": ["Practice more subtraction"]}'
            mock_openai_create.return_value = mock_response
            
            # Call the function
            result = get_analysis(attempts)
            
            # Assertions
            assert isinstance(result, dict)
            # Verify OpenAI was called
            mock_openai_create.assert_called_once()