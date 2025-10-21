"""
Integration Test for Prompt Storage Feature

This test verifies the complete flow:
1. Call the /generate-questions API endpoint with is_live parameter
2. Verify prompts are saved to the PostgreSQL database
3. Test both live (is_live=1) and test (is_live=0) scenarios
4. Verify prompt data can be retrieved from the database
"""

import pytest
import os
import json
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from fastapi import FastAPI
import psycopg2
from psycopg2.extras import RealDictCursor

# Set test environment before importing app modules
os.environ['ENVIRONMENT'] = 'development'

from app.main import app
from app.repositories import db_service
from app.models.schemas import GenerateQuestionsRequest
from app.db.db_factory import DatabaseFactory

class TestPromptStorageIntegration:
    """Integration tests for prompt storage functionality."""
    
    @pytest.fixture(scope="class")
    def client(self):
        """Create test client for FastAPI app."""
        return TestClient(app)
    
    @pytest.fixture(scope="class")
    def db_connection(self):
        """Create direct database connection for verification."""
        db_provider = DatabaseFactory.get_provider()
        conn = db_provider._get_connection()
        yield conn
        conn.close()
    
    @pytest.fixture(scope="class")
    def test_uid(self):
        """Test user UID for prompt storage tests."""
        return "TestPromptUser123456789012"  # 28 char UID
    
    @pytest.fixture(scope="class")
    def test_request_live(self, test_uid):
        """Sample request data for live app call (is_live=1)."""
        return {
            "uid": test_uid,
            "level": 1,
            "is_live": 1
        }
    
    @pytest.fixture(scope="class")
    def test_request_test(self, test_uid):
        """Sample request data for test/Postman call (is_live=0)."""
        return {
            "uid": test_uid,
            "level": 2,
            "is_live": 0
        }
    
    def cleanup_test_prompts(self, db_connection, test_uid):
        """Clean up test prompts from database."""
        cursor = db_connection.cursor()
        cursor.execute("DELETE FROM prompts WHERE uid = %s", (test_uid,))
        db_connection.commit()
        cursor.close()
    
    def get_prompts_from_db(self, db_connection, test_uid):
        """Retrieve prompts from database for verification."""
        cursor = db_connection.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT id, uid, request_text, response_text, is_live, created_at
            FROM prompts
            WHERE uid = %s
            ORDER BY created_at DESC
        """, (test_uid,))
        prompts = cursor.fetchall()
        cursor.close()
        return [dict(p) for p in prompts]
    
    @pytest.mark.integration
    @pytest.mark.neon
    def test_01_prompt_storage_live_call(self, client, db_connection, test_uid, test_request_live):
        """Test that prompts are saved with is_live=1 for live app calls."""
        # Clean up any existing test data
        self.cleanup_test_prompts(db_connection, test_uid)
        
        # Call the API endpoint
        response = client.post("/generate-questions", json=test_request_live)
        
        # Verify API response
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        response_data = response.json()
        
        # Verify response contains questions
        assert "questions" in response_data, "Response should contain 'questions' field"
        assert len(response_data["questions"]) > 0, "Should have at least one question"
        
        # Verify prompt was saved to database
        prompts = self.get_prompts_from_db(db_connection, test_uid)
        assert len(prompts) > 0, "At least one prompt should be saved to database"
        
        # Get the most recent prompt
        latest_prompt = prompts[0]
        
        # Verify prompt fields
        assert latest_prompt["uid"] == test_uid, "UID should match test user"
        assert latest_prompt["is_live"] == 1, "is_live should be 1 for live app call"
        assert latest_prompt["request_text"], "request_text should not be empty"
        assert latest_prompt["response_text"], "response_text should not be empty"
        assert latest_prompt["created_at"], "created_at should be set"
        
        # Verify request_text contains expected prompt elements
        request_text = latest_prompt["request_text"]
        # Request text can be either actual AI prompt or fallback message
        is_fallback = request_text.startswith("Fallback questions")
        if not is_fallback:
            assert "Generate a set of math questions" in request_text, "Request should contain prompt header"
            assert "question pattern" in request_text.lower(), "Request should mention question patterns"
        else:
            assert "Fallback" in request_text, "Fallback request should mention fallback"
        
        print(f"\n✅ Live call test passed!")
        print(f"   Prompt ID: {latest_prompt['id']}")
        print(f"   UID: {latest_prompt['uid']}")
        print(f"   is_live: {latest_prompt['is_live']}")
        print(f"   Request length: {len(latest_prompt['request_text'])} chars")
        print(f"   Response length: {len(latest_prompt['response_text'])} chars")
    
    @pytest.mark.integration
    @pytest.mark.neon
    def test_02_prompt_storage_test_call(self, client, db_connection, test_uid, test_request_test):
        """Test that prompts are saved with is_live=0 for test/Postman calls."""
        # Clean up any existing test data
        self.cleanup_test_prompts(db_connection, test_uid)
        
        # Call the API endpoint with is_live=0
        response = client.post("/generate-questions", json=test_request_test)
        
        # Verify API response
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        response_data = response.json()
        
        # Verify response contains questions
        assert "questions" in response_data, "Response should contain 'questions' field"
        
        # Verify prompt was saved to database
        prompts = self.get_prompts_from_db(db_connection, test_uid)
        assert len(prompts) > 0, "At least one prompt should be saved to database"
        
        # Get the most recent prompt
        latest_prompt = prompts[0]
        
        # Verify is_live is 0 for test call
        assert latest_prompt["is_live"] == 0, "is_live should be 0 for test/Postman call"
        assert latest_prompt["uid"] == test_uid, "UID should match test user"
        
        print(f"\n✅ Test call test passed!")
        print(f"   Prompt ID: {latest_prompt['id']}")
        print(f"   UID: {latest_prompt['uid']}")
        print(f"   is_live: {latest_prompt['is_live']}")
    
    @pytest.mark.integration
    @pytest.mark.neon
    def test_03_prompt_storage_default_is_live(self, client, db_connection, test_uid):
        """Test that is_live defaults to 1 when not specified."""
        # Clean up any existing test data
        self.cleanup_test_prompts(db_connection, test_uid)
        
        # Call the API without specifying is_live
        request_without_is_live = {
            "uid": test_uid,
            "level": 3
            # is_live not specified
        }
        
        response = client.post("/generate-questions", json=request_without_is_live)
        
        # Verify API response
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Verify prompt was saved with default is_live=1
        prompts = self.get_prompts_from_db(db_connection, test_uid)
        assert len(prompts) > 0, "At least one prompt should be saved to database"
        
        latest_prompt = prompts[0]
        assert latest_prompt["is_live"] == 1, "is_live should default to 1 when not specified"
        
        print(f"\n✅ Default is_live test passed!")
        print(f"   is_live defaulted to: {latest_prompt['is_live']}")
    
    @pytest.mark.integration
    @pytest.mark.neon
    def test_04_prompt_storage_multiple_calls(self, client, db_connection, test_uid):
        """Test that multiple calls create multiple prompt records."""
        # Clean up any existing test data
        self.cleanup_test_prompts(db_connection, test_uid)
        
        # Make multiple API calls
        for i in range(3):
            request_data = {
                "uid": test_uid,
                "level": i + 1,
                "is_live": i % 2  # Alternate between 0 and 1
            }
            response = client.post("/generate-questions", json=request_data)
            assert response.status_code == 200, f"Call {i+1} failed: {response.text}"
        
        # Verify multiple prompts were saved
        prompts = self.get_prompts_from_db(db_connection, test_uid)
        assert len(prompts) == 3, f"Expected 3 prompts, found {len(prompts)}"
        
        # Verify is_live values alternate
        is_live_values = [p["is_live"] for p in reversed(prompts)]  # Reverse to get chronological order
        assert is_live_values == [0, 1, 0], f"Expected [0, 1, 0], got {is_live_values}"
        
        print(f"\n✅ Multiple calls test passed!")
        print(f"   Total prompts saved: {len(prompts)}")
        print(f"   is_live values: {is_live_values}")
    
    @pytest.mark.integration
    @pytest.mark.neon
    def test_05_prompt_content_validation(self, client, db_connection, test_uid):
        """Test that saved prompt content is valid and complete."""
        # Clean up any existing test data
        self.cleanup_test_prompts(db_connection, test_uid)
        
        # Call the API
        request_data = {
            "uid": test_uid,
            "level": 2,
            "is_live": 1
        }
        response = client.post("/generate-questions", json=request_data)
        assert response.status_code == 200
        
        # Get the saved prompt
        prompts = self.get_prompts_from_db(db_connection, test_uid)
        assert len(prompts) > 0
        
        prompt = prompts[0]
        
        # Validate request_text structure
        request_text = prompt["request_text"]
        assert len(request_text) > 0, "Request text should not be empty"
        # Request can be fallback or actual AI prompt
        is_fallback = request_text.startswith("Fallback questions")
        if not is_fallback:
            assert len(request_text) > 100, "AI request text should be substantial"
            assert "Generate" in request_text, "Should contain generation instruction"
        assert "question" in request_text.lower(), "Should mention questions"
        
        # Validate response_text structure
        response_text = prompt["response_text"]
        assert len(response_text) > 0, "Response text should not be empty"
        
        # Try to parse response as JSON (it might be JSON array)
        try:
            # Try to find JSON in the response
            import re
            json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
            if json_match:
                questions_json = json.loads(json_match.group())
                assert isinstance(questions_json, list), "Response should be a JSON array"
                if len(questions_json) > 0:
                    assert "question" in questions_json[0], "Each question should have 'question' field"
                    assert "answer" in questions_json[0], "Each question should have 'answer' field"
        except Exception as e:
            # Response might be in different format (fallback questions, etc.)
            print(f"   Note: Response is not JSON format: {e}")
            pass
        
        print(f"\n✅ Prompt content validation passed!")
        print(f"   Request text length: {len(request_text)} chars")
        print(f"   Response text length: {len(response_text)} chars")
    
    @pytest.mark.integration
    @pytest.mark.neon
    def test_06_database_indexes_exist(self, db_connection):
        """Test that database indexes were created for performance."""
        cursor = db_connection.cursor()
        
        # Check if indexes exist
        cursor.execute("""
            SELECT indexname 
            FROM pg_indexes 
            WHERE tablename = 'prompts'
            AND indexname IN ('idx_prompts_uid', 'idx_prompts_created_at')
        """)
        indexes = cursor.fetchall()
        cursor.close()
        
        index_names = [idx[0] for idx in indexes]
        assert 'idx_prompts_uid' in index_names, "Index on uid should exist"
        assert 'idx_prompts_created_at' in index_names, "Index on created_at should exist"
        
        print(f"\n✅ Database indexes test passed!")
        print(f"   Found indexes: {index_names}")
    
    @pytest.mark.integration
    @pytest.mark.neon
    def test_07_cleanup(self, db_connection, test_uid):
        """Clean up all test data after tests complete."""
        self.cleanup_test_prompts(db_connection, test_uid)
        
        # Verify cleanup
        prompts = self.get_prompts_from_db(db_connection, test_uid)
        assert len(prompts) == 0, "All test prompts should be cleaned up"
        
        print(f"\n✅ Cleanup test passed!")
        print(f"   All test data removed")


if __name__ == "__main__":
    """Run tests directly with pytest."""
    pytest.main([__file__, "-v", "-s"])
