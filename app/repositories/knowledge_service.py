"""
Knowledge Service - Manages subjects and knowledge documents for knowledge-based questions
"""

from typing import List, Optional
from app.db.db_factory import DatabaseFactory
import logging

logger = logging.getLogger(__name__)

# Get the configured database provider instance
db_provider = DatabaseFactory.get_provider()


class KnowledgeService:
    """Service for managing subjects and knowledge documents"""
    
    @staticmethod
    def get_all_subjects(grade_level: Optional[int] = None) -> List[dict]:
        """
        Get all active subjects, optionally filtered by grade level.
        
        Args:
            grade_level: Optional grade level to filter subjects (4-7)
            
        Returns:
            List of subject dictionaries
        """
        try:
            conn = db_provider.get_connection()
            cursor = conn.cursor()
            
            # Note: grade_level filtering would require knowledge_documents join
            # For now, return all active subjects
            query = """
                SELECT id, name, display_name, description, icon, color, is_active
                FROM subjects
                WHERE is_active = true
                ORDER BY name
            """
            cursor.execute(query)
            
            columns = [desc[0] for desc in cursor.description]
            results = []
            for row in cursor.fetchall():
                results.append(dict(zip(columns, row)))
            
            cursor.close()
            conn.close()
            
            logger.debug(f"Retrieved {len(results)} subjects")
            return results
            
        except Exception as e:
            logger.error(f"Error fetching subjects: {e}")
            raise
    
    @staticmethod
    def get_subject_by_id(subject_id: int) -> Optional[dict]:
        """
        Get subject by ID.
        
        Args:
            subject_id: ID of the subject
            
        Returns:
            Subject dictionary or None if not found
        """
        try:
            conn = db_provider.get_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                """
                SELECT id, name, display_name, description, icon, color, is_active
                FROM subjects 
                WHERE id = %s AND is_active = true
                """,
                (subject_id,)
            )
            
            row = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if row:
                columns = ['id', 'name', 'display_name', 'description', 'icon', 'color', 'is_active']
                return dict(zip(columns, row))
            return None
            
        except Exception as e:
            logger.error(f"Error fetching subject by id {subject_id}: {e}")
            raise
    
    @staticmethod
    def get_knowledge_documents(
        subject_id: int,
        grade_level: Optional[int] = None,
        difficulty_level: Optional[int] = None
    ) -> List[dict]:
        """
        Get knowledge documents for a subject.
        
        Args:
            subject_id: ID of the subject
            grade_level: Optional grade level filter
            difficulty_level: Optional difficulty level filter (1-6)
            
        Returns:
            List of knowledge document dictionaries
        """
        try:
            conn = db_provider.get_connection()
            cursor = conn.cursor()
            
            query = """
                SELECT id, subject_id, title, content, summary, metadata,
                       grade_level, difficulty_level, is_active
                FROM knowledge_documents
                WHERE subject_id = %s AND is_active = true
            """
            params = [subject_id]
            
            if grade_level:
                query += " AND (grade_level = %s OR grade_level IS NULL)"
                params.append(grade_level)
            
            if difficulty_level:
                query += " AND (difficulty_level = %s OR difficulty_level IS NULL)"
                params.append(difficulty_level)
            
            query += " ORDER BY difficulty_level ASC NULLS FIRST, created_at DESC"
            
            cursor.execute(query, tuple(params))
            
            columns = [desc[0] for desc in cursor.description]
            results = []
            for row in cursor.fetchall():
                results.append(dict(zip(columns, row)))
            
            cursor.close()
            conn.close()
            
            logger.debug(f"Retrieved {len(results)} knowledge documents for subject {subject_id}")
            return results
            
        except Exception as e:
            logger.error(f"Error fetching knowledge documents: {e}")
            raise
    
    @staticmethod
    def log_knowledge_usage(
        uid: str,
        knowledge_doc_id: Optional[int],
        subject_id: int,
        question_count: int
    ):
        """
        Log knowledge document usage for analytics.
        
        Args:
            uid: Firebase User UID
            knowledge_doc_id: ID of the knowledge document used (optional)
            subject_id: ID of the subject
            question_count: Number of questions generated
        """
        try:
            conn = db_provider.get_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                """
                INSERT INTO knowledge_usage_log 
                (uid, knowledge_doc_id, subject_id, question_count)
                VALUES (%s, %s, %s, %s)
                """,
                (uid, knowledge_doc_id, subject_id, question_count)
            )
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.debug(f"Logged knowledge usage for user {uid}")
            
        except Exception as e:
            logger.error(f"Error logging knowledge usage: {e}")
            # Don't raise - logging should not break the main flow
    
    @staticmethod
    def save_knowledge_attempt(
        uid: str,
        subject_id: int,
        question: str,
        user_answer: str,
        correct_answer: str,
        evaluation_status: str,
        ai_feedback: Optional[str] = None,
        best_answer: Optional[str] = None,
        improvement_tips: Optional[str] = None,
        score: Optional[float] = None,
        difficulty_level: Optional[int] = None,
        topic: Optional[str] = None
    ):
        """
        Save a knowledge question attempt with evaluation results.
        
        Args:
            uid: Firebase User UID
            subject_id: ID of the subject
            question: The question text
            user_answer: User's answer
            correct_answer: The correct answer
            evaluation_status: 'correct', 'incorrect', or 'partial'
            ai_feedback: AI-generated feedback
            best_answer: AI-suggested best answer
            improvement_tips: Tips for improvement
            score: Score from 0.0 to 1.0
            difficulty_level: Difficulty level (1-6)
            topic: Topic of the question
        """
        try:
            conn = db_provider.get_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                """
                INSERT INTO knowledge_question_attempts 
                (uid, subject_id, question, user_answer, correct_answer, 
                 evaluation_status, ai_feedback, best_answer, improvement_tips, 
                 score, difficulty_level, topic)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (uid, subject_id, question, user_answer, correct_answer,
                 evaluation_status, ai_feedback, best_answer, improvement_tips,
                 score, difficulty_level, topic)
            )
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.debug(f"Saved knowledge attempt for user {uid}")
            
        except Exception as e:
            logger.error(f"Error saving knowledge attempt: {e}")
            raise
    
    @staticmethod
    def get_user_knowledge_attempts(
        uid: str,
        subject_id: Optional[int] = None,
        limit: int = 20
    ) -> List[dict]:
        """
        Get a user's knowledge question attempt history.
        
        Args:
            uid: Firebase User UID
            subject_id: Optional subject ID to filter
            limit: Maximum number of attempts to return
            
        Returns:
            List of attempt dictionaries
        """
        try:
            conn = db_provider.get_connection()
            cursor = conn.cursor()
            
            query = """
                SELECT id, uid, subject_id, question, user_answer, correct_answer,
                       evaluation_status, ai_feedback, score, difficulty_level, topic,
                       created_at
                FROM knowledge_question_attempts
                WHERE uid = %s
            """
            params = [uid]
            
            if subject_id:
                query += " AND subject_id = %s"
                params.append(subject_id)
            
            query += " ORDER BY created_at DESC LIMIT %s"
            params.append(limit)
            
            cursor.execute(query, tuple(params))
            
            columns = [desc[0] for desc in cursor.description]
            results = []
            for row in cursor.fetchall():
                results.append(dict(zip(columns, row)))
            
            cursor.close()
            conn.close()
            
            logger.debug(f"Retrieved {len(results)} knowledge attempts for user {uid}")
            return results
            
        except Exception as e:
            logger.error(f"Error fetching knowledge attempts: {e}")
            raise
    
    @staticmethod
    def create_knowledge_document(
        subject_id: int,
        title: str,
        content: str,
        summary: Optional[str] = None,
        metadata: Optional[dict] = None,
        grade_level: Optional[int] = None,
        difficulty_level: Optional[int] = None,
        created_by: Optional[str] = None
    ) -> int:
        """
        Create a new knowledge document.
        
        Args:
            subject_id: ID of the subject
            title: Document title
            content: Document content
            summary: Optional summary
            metadata: Optional metadata dict
            grade_level: Optional grade level (4-7)
            difficulty_level: Optional difficulty level (1-6)
            created_by: Optional creator identifier
            
        Returns:
            ID of the created document
        """
        try:
            conn = db_provider.get_connection()
            cursor = conn.cursor()
            
            import json
            metadata_json = json.dumps(metadata) if metadata else None
            
            cursor.execute(
                """
                INSERT INTO knowledge_documents 
                (subject_id, title, content, summary, metadata, 
                 grade_level, difficulty_level, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (subject_id, title, content, summary, metadata_json,
                 grade_level, difficulty_level, created_by)
            )
            
            doc_id = cursor.fetchone()[0]
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info(f"Created knowledge document with id {doc_id}")
            return doc_id
            
        except Exception as e:
            logger.error(f"Error creating knowledge document: {e}")
            raise
