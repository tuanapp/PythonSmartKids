import pytest
import json
from unittest.mock import patch, MagicMock
from app.services.ai_service import generate_practice_questions, get_analysis
from datetime import datetime

class TestAIServiceIntegration:
    """
    Integration tests for the AI service that verify actual API calls and response formats.
    Tests run against the actual AI service with mocked requests/responses.
    """
    
    @pytest.mark.integration
    def test_get_analysis_response_format(self):
        """
        Integration test to verify the format of the response from the AI service's get_analysis function.
        """
        # Set up test data
        student_data = [
            {
                "question": "2+2", 
                "is_correct": True, 
                "incorrect_answer": "",
                "correct_answer": "4",
                "datetime": "2023-01-01T12:00:00"
            },
            {
                "question": "7-3", 
                "is_correct": False,
                "incorrect_answer": "5",
                "correct_answer": "4",
                "datetime": "2023-01-01T12:00:00"
            }
        ]
        
        # Mock the OpenAI API call
        with patch("app.services.ai_service.client.chat.completions.create") as mock_openai:
            # Configure the mock to return a valid JSON response
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = '''
            {
                "analysis": "The student shows competence in addition but struggles with subtraction.",
                "questions": [
                    {"question": "5 - 2 = ?", "answer": "3"},
                    {"question": "10 - 7 = ?", "answer": "3"}
                ]
            }
            '''
            mock_openai.return_value = mock_response
            
            # Call the function
            result = get_analysis(student_data)
            
            # Assertions to verify the response format
            assert isinstance(result, dict), "Response should be a dictionary"
            assert "analysis" in result, "Response should have an 'analysis' key"
            assert "questions" in result, "Response should have a 'questions' key"
            assert isinstance(result["analysis"], str), "Analysis should be a string"
            assert isinstance(result["questions"], list), "Questions should be a list"
            
            for question in result["questions"]:
                assert "question" in question, "Each question should have a 'question' field"
                assert "answer" in question, "Each question should have an 'answer' field"
    
    @pytest.mark.integration
    def test_generate_practice_questions_response_format(self):
        """
        Integration test to verify the format of the response from the AI service's 
        generate_practice_questions function.
        """
        # Set up test data
        attempts = [
            {
                "question": "2+2", 
                "is_correct": True, 
                "incorrect_answer": "",
                "correct_answer": "4",
                "datetime": "2023-01-01T12:00:00"
            },
            {
                "question": "7-3", 
                "is_correct": False,
                "incorrect_answer": "5",
                "correct_answer": "4",
                "datetime": "2023-01-01T12:00:00"
            }
        ]
        
        patterns = [
            {
                "id": "123",
                "type": "algebra",
                "pattern_text": "a + _ = b",
                "created_at": "2023-01-01T12:00:00"
            },
            {
                "id": "124",
                "type": "algebra",
                "pattern_text": "a - _ = b",
                "created_at": "2023-01-01T12:00:00"
            }
        ]
        
        # Mock the OpenAI API call
        with patch("app.services.ai_service.client.chat.completions.create") as mock_openai:
            # Configure the mock to return a valid JSON response
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = '''
            {
              "questions": [
                {
                  "number": 1,
                  "topic": "algebra",
                  "pattern": "a + _ = b",
                  "question": "500 + _ = 700",
                  "answer": 200
                },
                {
                  "number": 2,
                  "topic": "algebra",
                  "pattern": "a - _ = b",
                  "question": "300 - _ = -500",
                  "answer": 800
                },
                {
                  "number": 3,
                  "topic": "algebra",
                  "pattern": "a + b = _",
                  "question": "999 + (-999)",
                  "answer": 0
                }
              ]
            }
            '''
            mock_openai.return_value = mock_response
            
            # Call the function
            result = generate_practice_questions(attempts, patterns)
            
            # Assertions to verify the response format
            assert isinstance(result, dict), "Response should be a dictionary"
            assert "questions" in result, "Response should have a 'questions' key"
            assert "timestamp" in result, "Response should have a 'timestamp' key"
            assert isinstance(result["questions"], dict), "Questions should be a dictionary in the result"
            assert isinstance(result["timestamp"], (datetime, type(None))), "Timestamp should be a datetime or None"
            
            # Validate the questions format in the response
            questions = result["questions"]
            assert "questions" in questions, "The questions object should have a 'questions' key"
            assert isinstance(questions["questions"], list), "questions['questions'] should be a list"
            
            for question in questions["questions"]:
                assert "number" in question, "Each question should have a 'number' field"
                assert "topic" in question, "Each question should have a 'topic' field"
                assert "pattern" in question, "Each question should have a 'pattern' field"
                assert "question" in question, "Each question should have a 'question' field"
                assert "answer" in question, "Each question should have an 'answer' field"
    
    @pytest.mark.integration
    def test_get_analysis_actual_format(self):
        """
        Integration test to verify the actual format of the response from the AI service without mocking.
        This test will be skipped if the environment variable SKIP_ACTUAL_AI_CALLS is set to True.
        """
        import os
        if os.environ.get("SKIP_ACTUAL_AI_CALLS", "True").lower() == "true":
            pytest.skip("Skipping test that makes actual AI API calls")
        
        # Set up test data
        student_data = [
            {
                "question": "2+2", 
                "is_correct": True, 
                "incorrect_answer": "",
                "correct_answer": "4",
                "datetime": datetime.now().isoformat()
            },
            {
                "question": "7-3", 
                "is_correct": False,
                "incorrect_answer": "5",
                "correct_answer": "4",
                "datetime": datetime.now().isoformat()
            }
        ]
        
        # Call the function with actual API
        result = get_analysis(student_data)
        
        # Assertions to verify the response format
        assert isinstance(result, dict), "Response should be a dictionary"
        assert "analysis" in result, "Response should have an 'analysis' key"
        assert "questions" in result, "Response should have a 'questions' key"
        assert isinstance(result["analysis"], str), "Analysis should be a string"
        assert isinstance(result["questions"], list), "Questions should be a list"
        
        for question in result["questions"]:
            assert "question" in question, "Each question should have a 'question' field"
            assert "answer" in question, "Each question should have an 'answer' field"
    
    @pytest.mark.integration
    def test_generate_practice_questions_actual_format(self):
        """
        Integration test to verify the actual format of the response from the AI service without mocking.
        This test will be skipped if the environment variable SKIP_ACTUAL_AI_CALLS is set to True.
        """
        import os
        if os.environ.get("SKIP_ACTUAL_AI_CALLS", "True").lower() == "true":
            pytest.skip("Skipping test that makes actual AI API calls")
        
        # Set up test data
        attempts = [
            {
                "question": "2+2", 
                "is_correct": True, 
                "incorrect_answer": "",
                "correct_answer": "4",
                "datetime": datetime.now().isoformat()
            },
            {
                "question": "7-3", 
                "is_correct": False,
                "incorrect_answer": "5",
                "correct_answer": "4",
                "datetime": datetime.now().isoformat()
            }
        ]
        
        patterns = [
            {
                "id": "123",
                "type": "algebra",
                "pattern_text": "a + _ = b",
                "created_at": datetime.now().isoformat()
            },
            {
                "id": "124",
                "type": "algebra",
                "pattern_text": "a - _ = b",
                "created_at": datetime.now().isoformat()
            }
        ]
        
        # Call the function with actual API
        result = generate_practice_questions(attempts, patterns)
        
        # Assertions to verify the response format
        assert isinstance(result, dict), "Response should be a dictionary"
        assert "questions" in result, "Response should have a 'questions' key"
        assert "timestamp" in result, "Response should have a 'timestamp' key"
        assert isinstance(result["questions"], dict), "Questions should be a dictionary"
        assert isinstance(result["timestamp"], (datetime, type(None))), "Timestamp should be a datetime or None"