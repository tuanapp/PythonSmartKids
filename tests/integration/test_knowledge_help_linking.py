"""
Integration Test for Knowledge Help Linking

This test verifies that help records are correctly linked to attempts using quiz_session_id.
"""

import pytest
import os
import uuid
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env'))

# Set test environment
os.environ['ENVIRONMENT'] = 'development'

from app.repositories.knowledge_service import KnowledgeService
from app.db.db_factory import DatabaseFactory

class TestKnowledgeHelpLinking:
    """Integration tests for help linking functionality."""
    
    @pytest.fixture(scope="class")
    def db_connection(self):
        """Get database connection."""
        provider = DatabaseFactory.get_provider()
        return provider._get_connection()
    
    @pytest.fixture(scope="function")
    def test_data(self):
        """Generate unique test data."""
        unique_id = str(uuid.uuid4())[:8]
        return {
            "uid": f"test_user_{unique_id}",
            "quiz_session_id": f"session_{unique_id}",
            "subject_id": 1,  # Assuming subject ID 1 exists (Math usually)
            "question": f"What is 10 + {unique_id}?",
            "request_text": f"Help me with: What is 10 + {unique_id}?"
        }

    def test_link_help_records_by_session(self, test_data):
        """
        Test that help records are linked to attempts by session ID.
        
        Flow:
        1. Create a help record with quiz_session_id (attempt_id=None)
        2. Create an attempt
        3. Call link_help_records_by_session
        4. Verify help record is updated with attempt_id
        """
        uid = test_data["uid"]
        quiz_session_id = test_data["quiz_session_id"]
        subject_id = test_data["subject_id"]
        question = test_data["question"]
        request_text = test_data["request_text"]
        
        print(f"\nTesting with UID: {uid}, Session: {quiz_session_id}")
        
        # 1. Log help usage (pre-answer, so attempt_id is None)
        KnowledgeService.log_knowledge_usage(
            uid=uid,
            subject_id=subject_id,
            request_text=request_text,
            response_text="Here is some help...",
            log_type='knowledge_question_help',
            quiz_session_id=quiz_session_id,
            attempt_id=None
        )
        
        # Verify help record exists and is unlinked
        conn = DatabaseFactory.get_provider()._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, attempt_id FROM knowledge_usage_log WHERE quiz_session_id = %s",
            (quiz_session_id,)
        )
        help_record = cursor.fetchone()
        assert help_record is not None, "Help record should be created"
        help_id = help_record[0]
        assert help_record[1] is None, "Help record should initially have NULL attempt_id"
        
        print(f"Created help record ID: {help_id}")
        
        # 2. Save an attempt
        attempt_id, _ = KnowledgeService.save_knowledge_attempt(
            uid=uid,
            subject_id=subject_id,
            question=question,
            user_answer="15",
            correct_answer="15",
            evaluation_status="correct",
            score=1.0
        )
        
        print(f"Created attempt ID: {attempt_id}")
        
        # 3. Link records
        # Note: The linking logic matches if question[:50] is in request_text
        # Our test data: question="What is...", request_text="Help me with: What is..."
        # So question is IN request_text.
        
        KnowledgeService.link_help_records_by_session(
            quiz_session_id=quiz_session_id,
            attempt_ids=[attempt_id],
            questions=[question]
        )
        
        # 4. Verify linking
        cursor.execute(
            "SELECT attempt_id FROM knowledge_usage_log WHERE id = %s",
            (help_id,)
        )
        updated_record = cursor.fetchone()
        cursor.close()
        conn.close()
        
        assert updated_record is not None
        linked_attempt_id = updated_record[0]
        
        print(f"Linked attempt ID: {linked_attempt_id}")
        
        assert linked_attempt_id == attempt_id, f"Help record should be linked to attempt {attempt_id}, but got {linked_attempt_id}"

    def test_link_help_records_multiple_questions(self, test_data):
        """Test linking with multiple questions in the same session."""
        uid = test_data["uid"] + "_multi"
        quiz_session_id = test_data["quiz_session_id"] + "_multi"
        subject_id = test_data["subject_id"]
        
        questions = [f"Question {i}" for i in range(3)]
        
        # Create help records for Q0 and Q2 only
        for i in [0, 2]:
            KnowledgeService.log_knowledge_usage(
                uid=uid,
                subject_id=subject_id,
                request_text=f"Help for {questions[i]}",
                response_text="Help...",
                log_type='knowledge_question_help',
                quiz_session_id=quiz_session_id,
                attempt_id=None
            )
            
        # Create attempts for all 3
        attempt_ids = []
        for q in questions:
            aid, _ = KnowledgeService.save_knowledge_attempt(
                uid=uid,
                subject_id=subject_id,
                question=q,
                user_answer="Ans",
                correct_answer="Ans",
                evaluation_status="correct"
            )
            attempt_ids.append(aid)
            
        # Link
        KnowledgeService.link_help_records_by_session(
            quiz_session_id=quiz_session_id,
            attempt_ids=attempt_ids,
            questions=questions
        )
        
        # Verify
        conn = DatabaseFactory.get_provider()._get_connection()
        cursor = conn.cursor()
        
        # Check Q0 help
        cursor.execute(
            "SELECT attempt_id FROM knowledge_usage_log WHERE quiz_session_id = %s AND request_text LIKE %s",
            (quiz_session_id, f"%{questions[0]}%")
        )
        res0 = cursor.fetchone()
        assert res0[0] == attempt_ids[0], "Q0 help should be linked to Q0 attempt"
        
        # Check Q2 help
        cursor.execute(
            "SELECT attempt_id FROM knowledge_usage_log WHERE quiz_session_id = %s AND request_text LIKE %s",
            (quiz_session_id, f"%{questions[2]}%")
        )
        res2 = cursor.fetchone()
        assert res2[0] == attempt_ids[2], "Q2 help should be linked to Q2 attempt"
        
        cursor.close()
        conn.close()
