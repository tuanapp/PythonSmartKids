import pytest
import json
from datetime import datetime
from app.services.ai_service import generate_practice_questions, get_analysis
from app.config import RUN_REAL_API_TESTS

class TestAIServiceReal:
    """
    Integration tests for the AI service that make actual calls to the OpenAI API.
    These tests are designed to verify real API behavior and response formats.
    
    IMPORTANT: These tests will consume API credits and should be run sparingly.
    Set the environment variable RUN_REAL_API_TESTS=True in .env file to run these tests.
    """
    
    def setup_method(self):
        """Check if real API tests should run"""
        if not RUN_REAL_API_TESTS:
            pytest.skip("Skipping real API tests. Set RUN_REAL_API_TESTS=True in .env file to run these tests.")
    
    # @pytest.mark.real
    # def test_get_analysis_real_api_call(self):
    #     """
    #     Test that sends a real request to the AI service and verifies the response format
    #     for the get_analysis function.
    #     """
    #     # Set up test data
    #     student_data = [
    #         {
    #             "question": "2+2", 
    #             "is_correct": True, 
    #             "incorrect_answer": "",
    #             "correct_answer": "4",
    #             "datetime": datetime.now().isoformat()
    #         },
    #         {
    #             "question": "7-3", 
    #             "is_correct": False,
    #             "incorrect_answer": "5",
    #             "correct_answer": "4",
    #             "datetime": datetime.now().isoformat()
    #         },
    #         {
    #             "question": "10+15", 
    #             "is_correct": True, 
    #             "incorrect_answer": "",
    #             "correct_answer": "25",
    #             "datetime": datetime.now().isoformat()
    #         },
    #         {
    #             "question": "8×4", 
    #             "is_correct": True, 
    #             "incorrect_answer": "",
    #             "correct_answer": "32",
    #             "datetime": datetime.now().isoformat()
    #         },
    #         {
    #             "question": "20÷5", 
    #             "is_correct": False,
    #             "incorrect_answer": "3",
    #             "correct_answer": "4",
    #             "datetime": datetime.now().isoformat()
    #         }
    #     ]
        
    #     # Make the actual API call
    #     result = get_analysis(student_data)
        
    #     # Log the result for debugging
    #     print(f"\nAPI Response for get_analysis: {json.dumps(result, indent=2)}")
        
    #     # Assertions to verify the response format
    #     assert isinstance(result, dict), "Response should be a dictionary"
    #     assert "analysis" in result, "Response should have an 'analysis' key"
    #     assert "questions" in result, "Response should have a 'questions' key"
    #     assert isinstance(result["analysis"], str), "Analysis should be a string"
    #     assert isinstance(result["questions"], list), "Questions should be a list"
        
    #     # Detailed validation of the questions
    #     for question in result["questions"]:
    #         assert "question" in question, "Each question should have a 'question' field"
    #         assert "answer" in question, "Each question should have an 'answer' field"
    #         assert isinstance(question["question"], str), "Question field should be a string"
    
    @pytest.mark.real
    def test_generate_practice_questions_real_api_call(self):
        """
        Test that sends a real request to the AI service and verifies the response format
        for the generate_practice_questions function.
        """
        # Set up test data with diverse question types
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
            },
            {
                "question": "9×6", 
                "is_correct": False,
                "incorrect_answer": "52",
                "correct_answer": "54",
                "datetime": datetime.now().isoformat()
            },
            {
                "question": "25÷5", 
                "is_correct": True,
                "incorrect_answer": "",
                "correct_answer": "5",
                "datetime": datetime.now().isoformat()
            }
        ]
        
        patterns = [
            {
                "id": "123",
                "type": "addition",
                "pattern_text": "a + b = _",
                "created_at": datetime.now().isoformat()
            },
            {
                "id": "124",
                "type": "subtraction",
                "pattern_text": "a - b = _",
                "created_at": datetime.now().isoformat()
            },
            {
                "id": "125",
                "type": "multiplication",
                "pattern_text": "a × b = _",
                "created_at": datetime.now().isoformat()
            },
            {
                "id": "126",
                "type": "division",
                "pattern_text": "a ÷ b = _",
                "created_at": datetime.now().isoformat()
            },
            {
                "id": "127",
                "type": "algebra",
                "pattern_text": "a + _ = b",
                "created_at": datetime.now().isoformat()
            }
        ]
        
        # Make the actual API call
        result = generate_practice_questions(attempts, patterns)
        
        # Log the result for debugging
        # Convert datetime objects to strings for JSON serialization
        result_serializable = {
            key: (value.isoformat() if isinstance(value, datetime) else value)
            for key, value in result.items()
        }
        print(f"\nAPI Response for generate_practice_questions: {json.dumps(result_serializable, indent=2)}")
        
        # Assertions to verify the response format
        assert isinstance(result, dict), "Response should be a dictionary"
        assert "questions" in result, "Response should have a 'questions' key"
        assert "timestamp" in result, "Response should have a 'timestamp' key"
        
        # Check that the timestamp is a datetime object or None
        assert isinstance(result["timestamp"], (datetime, type(None))), "Timestamp should be a datetime object or None"
        
        # Validate the questions structure
        questions = result["questions"]
        assert isinstance(questions, dict), "Questions should be a dictionary"
        
        if "questions" in questions and isinstance(questions["questions"], list):
            # If the response has the expected structure with a questions list
            for question in questions["questions"]:
                assert isinstance(question, dict), "Each question should be a dictionary"
                # Check for required fields based on the expected format
                assert "question" in question or "pattern" in question, "Each question should have a question or pattern"
                assert "answer" in question or "number" in question, "Each question should have an answer or number field"
        else:
            # Alternative format sometimes returned by the AI
            # Check if we have at least one question category
            assert len(questions) > 0, "Should have at least one question category"
            
            # Sample one category and check its format
            sample_key = list(questions.keys())[0]
            sample_question = questions[sample_key]
            assert isinstance(sample_question, str), "Question value should be a string"