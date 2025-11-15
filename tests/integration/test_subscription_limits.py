"""
Comprehensive Integration Tests for Subscription-Based Question Generation

Tests all three subscription levels:
- Free (subscription=0): 2 questions/day
- Trial (subscription=1): 2 questions/day
- Premium (subscription=2+): Unlimited questions/day

Tests ensure:
1. All local PC calls have is_live=False
2. Daily limits enforced correctly for each tier
3. Premium users get unlimited access
4. Proper tracking in prompts table
"""

import pytest
import os
from datetime import datetime, timezone, date
from fastapi.testclient import TestClient
import psycopg2
from psycopg2.extras import RealDictCursor

# Set test environment before importing app modules
os.environ['ENVIRONMENT'] = 'development'

from app.main import app
from app.db.db_factory import DatabaseFactory

class TestSubscriptionBasedQuestionGeneration:
    """Integration tests for subscription-based question generation with daily limits."""
    
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
    def test_users(self):
        """Test user UIDs for different subscription levels."""
        return {
            'free': "TestFreeUser123456789012345",      # 28 chars
            'trial': "TestTrialUser12345678901234",     # 28 chars
            'premium': "TestPremiumUser1234567890123"   # 28 chars
        }
    
    def cleanup_test_data(self, db_connection, test_users):
        """Clean up test users and their data from database."""
        cursor = db_connection.cursor()
        
        # Delete prompts for all test users
        for uid in test_users.values():
            cursor.execute("DELETE FROM prompts WHERE uid = %s", (uid,))
            cursor.execute("DELETE FROM attempts WHERE uid = %s", (uid,))
            cursor.execute("DELETE FROM users WHERE uid = %s", (uid,))
        
        db_connection.commit()
        cursor.close()
    
    def create_test_user(self, db_connection, uid, email, subscription_level):
        """Create a test user with specified subscription level."""
        cursor = db_connection.cursor()
        
        # Insert or update user with subscription level
        cursor.execute("""
            INSERT INTO users (uid, email, name, display_name, grade_level, registration_date, subscription)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (uid) 
            DO UPDATE SET subscription = EXCLUDED.subscription
        """, (
            uid,
            email,
            f"Test User {subscription_level}",
            f"TestUser{subscription_level}",
            3,
            datetime.now(timezone.utc),
            subscription_level
        ))
        
        db_connection.commit()
        cursor.close()
    
    def get_today_question_count(self, db_connection, uid):
        """Get today's question generation count for a user."""
        cursor = db_connection.cursor()
        cursor.execute("""
            SELECT COUNT(*) 
            FROM prompts
            WHERE uid = %s 
              AND request_type = 'question_generation'
              AND DATE(created_at) = CURRENT_DATE
        """, (uid,))
        count = cursor.fetchone()[0]
        cursor.close()
        return count
    
    def get_prompts_from_db(self, db_connection, uid):
        """Retrieve prompts from database for verification."""
        cursor = db_connection.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT id, uid, request_type, is_live, level, source, created_at
            FROM prompts
            WHERE uid = %s
            ORDER BY created_at DESC
        """, (uid,))
        prompts = cursor.fetchall()
        cursor.close()
        return [dict(p) for p in prompts]
    
    # ============================================================================
    # FREE SUBSCRIPTION TESTS (subscription=0)
    # ============================================================================
    
    @pytest.mark.integration
    @pytest.mark.neon
    def test_01_free_user_first_generation_success(self, client, db_connection, test_users):
        """Free user (subscription=0) can generate first question set."""
        uid = test_users['free']
        
        # Clean up and create free user
        self.cleanup_test_data(db_connection, {'free': uid})
        self.create_test_user(db_connection, uid, "free@test.com", subscription_level=0)
        
        # Verify starting count is 0
        assert self.get_today_question_count(db_connection, uid) == 0
        
        # Make request with is_live=False (local PC test)
        request_data = {
            "uid": uid,
            "level": 1,
            "is_live": False  # Local PC call
        }
        response = client.post("/generate-questions", json=request_data)
        
        # Verify success
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        response_data = response.json()
        assert "questions" in response_data
        assert response_data.get("daily_count") == 1
        assert response_data.get("daily_limit") == 2
        assert response_data.get("is_premium") == False
        
        # Verify prompt saved with correct attributes
        prompts = self.get_prompts_from_db(db_connection, uid)
        assert len(prompts) == 1
        assert prompts[0]['is_live'] == 0  # Local PC call
        assert prompts[0]['level'] == 1
        assert prompts[0]['source'] in ['api', 'fallback']
        assert prompts[0]['request_type'] == 'question_generation'
        
        # Verify count incremented
        assert self.get_today_question_count(db_connection, uid) == 1
    
    @pytest.mark.integration
    @pytest.mark.neon
    def test_02_free_user_second_generation_success(self, client, db_connection, test_users):
        """Free user can generate second question set (at limit)."""
        uid = test_users['free']
        
        # User already has 1 generation from previous test
        current_count = self.get_today_question_count(db_connection, uid)
        assert current_count == 1
        
        # Make second request
        request_data = {
            "uid": uid,
            "level": 2,
            "is_live": False  # Local PC call
        }
        response = client.post("/generate-questions", json=request_data)
        
        # Verify success
        assert response.status_code == 200
        response_data = response.json()
        assert response_data.get("daily_count") == 2  # At limit now
        assert response_data.get("daily_limit") == 2
        assert response_data.get("is_premium") == False
        
        # Verify count is now 2
        assert self.get_today_question_count(db_connection, uid) == 2
    
    @pytest.mark.integration
    @pytest.mark.neon
    def test_03_free_user_third_generation_blocked(self, client, db_connection, test_users):
        """Free user blocked after reaching daily limit of 2."""
        uid = test_users['free']
        
        # User already has 2 generations
        current_count = self.get_today_question_count(db_connection, uid)
        assert current_count == 2
        
        # Make third request (should be blocked)
        request_data = {
            "uid": uid,
            "level": 1,
            "is_live": False  # Local PC call
        }
        response = client.post("/generate-questions", json=request_data)
        
        # Verify blocked with 403
        assert response.status_code == 403
        response_data = response.json()
        assert "daily_limit_exceeded" in response_data["detail"]["error"]
        assert response_data["detail"]["current_count"] == 2
        assert response_data["detail"]["max_count"] == 2
        assert response_data["detail"]["is_premium"] == False
        
        # Verify count still 2 (no new prompt saved)
        assert self.get_today_question_count(db_connection, uid) == 2
    
    # ============================================================================
    # TRIAL SUBSCRIPTION TESTS (subscription=1)
    # ============================================================================
    
    @pytest.mark.integration
    @pytest.mark.neon
    def test_04_trial_user_first_generation_success(self, client, db_connection, test_users):
        """Trial user (subscription=1) can generate first question set."""
        uid = test_users['trial']
        
        # Clean up and create trial user
        self.cleanup_test_data(db_connection, {'trial': uid})
        self.create_test_user(db_connection, uid, "trial@test.com", subscription_level=1)
        
        # Make request with is_live=False
        request_data = {
            "uid": uid,
            "level": 3,
            "is_live": False  # Local PC call
        }
        response = client.post("/generate-questions", json=request_data)
        
        # Verify success
        assert response.status_code == 200
        response_data = response.json()
        assert response_data.get("daily_count") == 1
        assert response_data.get("daily_limit") == 2  # Trial same as free
        assert response_data.get("is_premium") == False
        
        # Verify prompt attributes
        prompts = self.get_prompts_from_db(db_connection, uid)
        assert len(prompts) == 1
        assert prompts[0]['is_live'] == 0  # Local PC
        assert prompts[0]['level'] == 3
    
    @pytest.mark.integration
    @pytest.mark.neon
    def test_05_trial_user_second_generation_success(self, client, db_connection, test_users):
        """Trial user can generate second question set (at limit)."""
        uid = test_users['trial']
        
        # Make second request
        request_data = {
            "uid": uid,
            "level": 2,
            "is_live": False
        }
        response = client.post("/generate-questions", json=request_data)
        
        # Verify success
        assert response.status_code == 200
        assert self.get_today_question_count(db_connection, uid) == 2
    
    @pytest.mark.integration
    @pytest.mark.neon
    def test_06_trial_user_third_generation_blocked(self, client, db_connection, test_users):
        """Trial user blocked after reaching daily limit of 2."""
        uid = test_users['trial']
        
        # Make third request (should be blocked)
        request_data = {
            "uid": uid,
            "level": 1,
            "is_live": False
        }
        response = client.post("/generate-questions", json=request_data)
        
        # Verify blocked
        assert response.status_code == 403
        response_data = response.json()
        assert "daily_limit_exceeded" in response_data["detail"]["error"]
        assert response_data["detail"]["max_count"] == 2
    
    # ============================================================================
    # PREMIUM SUBSCRIPTION TESTS (subscription=2+)
    # ============================================================================
    
    @pytest.mark.integration
    @pytest.mark.neon
    def test_07_premium_user_multiple_generations_unlimited(self, client, db_connection, test_users):
        """Premium user (subscription=2+) has unlimited generations."""
        uid = test_users['premium']
        
        # Clean up and create premium user
        self.cleanup_test_data(db_connection, {'premium': uid})
        self.create_test_user(db_connection, uid, "premium@test.com", subscription_level=2)
        
        # Generate 5 question sets (more than free/trial limit)
        for i in range(5):
            request_data = {
                "uid": uid,
                "level": (i % 6) + 1,  # Rotate through levels 1-6
                "is_live": False  # Local PC call
            }
            response = client.post("/generate-questions", json=request_data)
            
            # All should succeed
            assert response.status_code == 200, f"Generation {i+1} failed: {response.text}"
            response_data = response.json()
            assert response_data.get("is_premium") == True
            assert "daily_count" in response_data  # Should still track count
        
        # Verify all 5 prompts saved
        assert self.get_today_question_count(db_connection, uid) == 5
        
        # Verify all prompts have correct attributes
        prompts = self.get_prompts_from_db(db_connection, uid)
        assert len(prompts) == 5
        for prompt in prompts:
            assert prompt['is_live'] == 0  # All local PC calls
            assert prompt['request_type'] == 'question_generation'
    
    @pytest.mark.integration
    @pytest.mark.neon
    def test_08_premium_user_no_daily_limit(self, client, db_connection, test_users):
        """Premium user can continue generating beyond normal limits."""
        uid = test_users['premium']
        
        # Clean up and ensure premium user exists with correct subscription level
        self.cleanup_test_data(db_connection, {'premium': uid})
        self.create_test_user(db_connection, uid, "premium@test.com", subscription_level=2)
        
        # Generate 5 question sets first (to establish baseline)
        for i in range(5):
            request_data = {
                "uid": uid,
                "level": (i % 6) + 1,
                "is_live": False
            }
            response = client.post("/generate-questions", json=request_data)
            assert response.status_code == 200, f"Setup generation {i+1} failed: {response.text}"
        
        # Verify user now has 5 generations
        current_count = self.get_today_question_count(db_connection, uid)
        assert current_count == 5
        
        # Make 6th request (should still work - premium users have unlimited)
        request_data = {
            "uid": uid,
            "level": 4,
            "is_live": False
        }
        response = client.post("/generate-questions", json=request_data)
        
        # Verify success
        assert response.status_code == 200
        response_data = response.json()
        assert response_data.get("is_premium") == True
        
        # Verify DB count incremented to 6 (most important check)
        final_count = self.get_today_question_count(db_connection, uid)
        assert final_count == 6
    
    # ============================================================================
    # LIVE vs TEST CALL TESTS
    # ============================================================================
    
    @pytest.mark.integration
    @pytest.mark.neon
    def test_09_is_live_false_for_local_calls(self, client, db_connection, test_users):
        """Verify all local PC test calls have is_live=False."""
        uid = test_users['premium']  # Use premium to avoid limit issues
        
        # Make request explicitly with is_live=False
        request_data = {
            "uid": uid,
            "level": 1,
            "is_live": False  # Explicitly set for local testing
        }
        response = client.post("/generate-questions", json=request_data)
        
        assert response.status_code == 200
        
        # Verify prompt saved with is_live=0
        prompts = self.get_prompts_from_db(db_connection, uid)
        latest_prompt = prompts[0]  # Most recent
        assert latest_prompt['is_live'] == 0, "Local PC calls must have is_live=0"
    
    @pytest.mark.integration
    @pytest.mark.neon
    def test_10_is_live_true_for_production_calls(self, client, db_connection, test_users):
        """Simulate production app call with is_live=True."""
        uid = test_users['premium']
        
        # Make request with is_live=True (simulating production app)
        request_data = {
            "uid": uid,
            "level": 2,
            "is_live": True  # Production app call
        }
        response = client.post("/generate-questions", json=request_data)
        
        assert response.status_code == 200
        
        # Verify prompt saved with is_live=1
        prompts = self.get_prompts_from_db(db_connection, uid)
        latest_prompt = prompts[0]
        assert latest_prompt['is_live'] == 1, "Production calls should have is_live=1"
    
    # ============================================================================
    # LEVEL FILTERING TESTS
    # ============================================================================
    
    @pytest.mark.integration
    @pytest.mark.neon
    def test_11_level_stored_in_prompts(self, client, db_connection, test_users):
        """Verify difficulty level is stored in prompts table."""
        uid = test_users['premium']
        
        # Test different levels
        for level in [1, 3, 6]:
            request_data = {
                "uid": uid,
                "level": level,
                "is_live": False
            }
            response = client.post("/generate-questions", json=request_data)
            assert response.status_code == 200
            
            # Verify level stored
            prompts = self.get_prompts_from_db(db_connection, uid)
            latest_prompt = prompts[0]
            assert latest_prompt['level'] == level, f"Level {level} not stored correctly"
    
    @pytest.mark.integration
    @pytest.mark.neon
    def test_12_source_tracked_in_prompts(self, client, db_connection, test_users):
        """Verify source (api/cached/fallback) is tracked in prompts."""
        uid = test_users['premium']
        
        request_data = {
            "uid": uid,
            "level": 2,
            "is_live": False
        }
        response = client.post("/generate-questions", json=request_data)
        assert response.status_code == 200
        
        # Verify source is tracked
        prompts = self.get_prompts_from_db(db_connection, uid)
        latest_prompt = prompts[0]
        assert latest_prompt['source'] in ['api', 'cached', 'fallback'], \
            f"Source should be api/cached/fallback, got: {latest_prompt['source']}"
    
    # ============================================================================
    # ERROR HANDLING TESTS
    # ============================================================================
    
    @pytest.mark.integration
    @pytest.mark.neon
    def test_13_missing_uid_returns_error(self, client):
        """Request without UID should fail validation."""
        request_data = {
            "level": 1,
            "is_live": False
        }
        response = client.post("/generate-questions", json=request_data)
        
        # Should return validation error
        assert response.status_code == 422  # Validation error
    
    @pytest.mark.integration
    @pytest.mark.neon
    def test_14_invalid_level_handled(self, client, test_users):
        """Invalid level should be handled gracefully."""
        uid = test_users['premium']
        
        request_data = {
            "uid": uid,
            "level": 99,  # Invalid level
            "is_live": False
        }
        response = client.post("/generate-questions", json=request_data)
        
        # Should still work (returns empty patterns or defaults)
        assert response.status_code in [200, 400]
    
    # ============================================================================
    # CLEANUP
    # ============================================================================
    
    @pytest.mark.integration
    @pytest.mark.neon
    def test_99_cleanup(self, db_connection, test_users):
        """Clean up all test data after tests complete."""
        self.cleanup_test_data(db_connection, test_users)
        
        # Verify cleanup
        for uid in test_users.values():
            assert self.get_today_question_count(db_connection, uid) == 0
            assert len(self.get_prompts_from_db(db_connection, uid)) == 0
