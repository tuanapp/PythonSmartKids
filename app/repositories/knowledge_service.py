"""
Knowledge Service - Manages subjects and knowledge documents for knowledge-based questions
"""

from typing import List, Optional, Tuple
from datetime import datetime
from app.db.db_factory import DatabaseFactory
# TODO: evaluate & decide later
# from app.services.performance_report_service import performance_report_service
import logging

logger = logging.getLogger(__name__)

# Get the configured database provider instance
db_provider = DatabaseFactory.get_provider()


class KnowledgeService:
    """Service for managing subjects and knowledge documents"""

    @staticmethod
    def _match_subject_from_query(query_text: str) -> Optional[dict]:
        try:
            subjects = KnowledgeService.get_all_subjects()
        except Exception:
            return None

        query_lower = query_text.lower()
        for subject in subjects:
            name = (subject.get("name") or "").lower()
            display_name = (subject.get("display_name") or "").lower()
            if name and name in query_lower:
                return subject
            if display_name and display_name in query_lower:
                return subject
        return None

    @staticmethod
    def _extract_topic_filter(query_text: str) -> Tuple[Optional[str], List[str]]:
        topic_keywords = {
            "grammar": ["grammar", "tenses", "parts of speech", "sentence structure"],
            "vocabulary": ["vocabulary", "vocab", "word meaning", "synonym", "antonym"],
            "reading comprehension": ["reading comprehension", "comprehension", "reading", "passage"],
            "spelling": ["spelling", "spell"],
            "punctuation": ["punctuation", "comma", "period", "apostrophe"],
            "writing": ["writing", "essay", "paragraph", "story"],
        }

        query_lower = query_text.lower()
        for topic, keywords in topic_keywords.items():
            for keyword in keywords:
                if keyword in query_lower:
                    return topic, keywords

        return None, []
    
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
            conn = db_provider._get_connection()
            cursor = conn.cursor()
            
            # Note: grade_level filtering would require knowledge_documents join
            # For now, return all active subjects
            query = """
                SELECT id, name, display_name, description, icon, color, is_active,
                       visual_json_max, visual_svg_max
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
    def answer_performance_query(
        uid: str,
        query_text: str,
        subject_id: Optional[int] = None,
        limit: int = 5
    ) -> dict:
        """
        Answer user questions about performance details using knowledge attempts data.

        Args:
            uid: Firebase User UID
            query_text: User question text
            subject_id: Optional subject ID to filter
            limit: Max number of items to return in top_missed
        """
        cleaned_query = (query_text or "").strip()
        if len(cleaned_query) < 3:
            return {
                "success": False,
                "error": "query_too_short",
                "message": "Please provide a more specific question."
            }

        subject = None
        if subject_id:
            subject = KnowledgeService.get_subject_by_id(subject_id)
        else:
            subject = KnowledgeService._match_subject_from_query(cleaned_query)

        topic_label, topic_keywords = KnowledgeService._extract_topic_filter(cleaned_query)

        try:
            conn = db_provider._get_connection()
            cursor = conn.cursor()

            query = """
                SELECT question, topic, evaluation_status, created_at, subject_id
                FROM knowledge_question_attempts
                WHERE uid = %s
            """
            params = [uid]

            if subject:
                query += " AND subject_id = %s"
                params.append(subject["id"])

            query += " ORDER BY created_at DESC"

            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()

            cursor.close()
            conn.close()
        except Exception as e:
            logger.error(f"Error answering performance query: {e}")
            raise

        attempts = [
            {
                "question": row[0],
                "topic": row[1],
                "evaluation_status": row[2],
                "created_at": row[3],
                "subject_id": row[4]
            }
            for row in rows
        ]

        if topic_keywords:
            filtered = []
            for attempt in attempts:
                topic_text = (attempt.get("topic") or "").lower()
                question_text = (attempt.get("question") or "").lower()
                if any(keyword in topic_text or keyword in question_text for keyword in topic_keywords):
                    filtered.append(attempt)
            attempts = filtered

        total = len(attempts)
        correct = sum(1 for a in attempts if (a.get("evaluation_status") or "").lower() == "correct")
        incorrect = total - correct
        accuracy = round((correct / total) * 100, 1) if total > 0 else 0.0

        missed_groups = {}
        for attempt in attempts:
            status = (attempt.get("evaluation_status") or "").lower()
            if status == "correct":
                continue
            question = attempt.get("question") or ""
            topic = attempt.get("topic")
            key = (question, topic)
            if key not in missed_groups:
                missed_groups[key] = {
                    "question": question,
                    "topic": topic,
                    "incorrect_count": 0,
                    "last_attempted": None
                }
            missed_groups[key]["incorrect_count"] += 1
            created_at = attempt.get("created_at")
            last_attempted = missed_groups[key]["last_attempted"]
            if created_at and (last_attempted is None or created_at > last_attempted):
                missed_groups[key]["last_attempted"] = created_at

        def sort_key(item: dict) -> Tuple[int, float]:
            last_attempted = item.get("last_attempted")
            last_ts = last_attempted.timestamp() if last_attempted else 0.0
            return (-item["incorrect_count"], -last_ts)

        top_missed = sorted(missed_groups.values(), key=sort_key)[:max(1, min(limit, 20))]

        for item in top_missed:
            if item["last_attempted"]:
                item["last_attempted"] = item["last_attempted"].isoformat()

        subject_label = None
        if subject:
            subject_label = subject.get("display_name") or subject.get("name")

        if total == 0:
            return {
                "success": True,
                "student_uid": uid,
                "query": cleaned_query,
                "subject": subject,
                "topic_filter": topic_label,
                "stats": {
                    "total": 0,
                    "correct": 0,
                    "incorrect": 0,
                    "accuracy": 0.0
                },
                "top_missed": [],
                "answer": "No matching attempts were found for this question.",
                "message": "No matching attempts were found for this question."
            }

        subject_part = f" for {subject_label}" if subject_label else ""
        topic_part = f" in {topic_label}" if topic_label else ""
        answer = (
            f"Found {incorrect} incorrect out of {total} attempts{subject_part}{topic_part}. "
            f"Accuracy is {accuracy}%."
        )

        return {
            "success": True,
            "student_uid": uid,
            "query": cleaned_query,
            "subject": subject,
            "topic_filter": topic_label,
            "stats": {
                "total": total,
                "correct": correct,
                "incorrect": incorrect,
                "accuracy": accuracy
            },
            "top_missed": top_missed,
            "answer": answer,
            "message": "Performance query answered successfully."
        }
    
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
            conn = db_provider._get_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                """
                SELECT id, name, display_name, description, icon, color, is_active, 
                       visual_json_max, visual_svg_max
                FROM subjects 
                WHERE id = %s AND is_active = true
                """,
                (subject_id,)
            )
            
            row = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if row:
                columns = ['id', 'name', 'display_name', 'description', 'icon', 'color', 'is_active', 
                           'visual_json_max', 'visual_svg_max']
                return dict(zip(columns, row))
            return None
            
        except Exception as e:
            logger.error(f"Error fetching subject by id {subject_id}: {e}")
            raise
    
    @staticmethod
    def get_knowledge_documents(
        subject_id: int,
        grade_level: Optional[int] = None,
        level: Optional[int] = None
    ) -> List[dict]:
        """
        Get knowledge documents for a subject.
        
        Args:
            subject_id: ID of the subject
            grade_level: Optional grade level filter
            level: Optional question level (unused in DB, for compatibility)
            
        Returns:
            List of knowledge document dictionaries
        """
        try:
            conn = db_provider._get_connection()
            cursor = conn.cursor()
            
            query = """
                SELECT id, subject_id, title, content, grade_level, source, is_active
                FROM knowledge_documents
                WHERE subject_id = %s AND is_active = true
            """
            params = [subject_id]
            
            if grade_level:
                query += " AND (grade_level = %s OR grade_level IS NULL)"
                params.append(grade_level)
            
            query += " ORDER BY grade_level ASC NULLS FIRST, created_at DESC"
            
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
        question_count: int,
        request_text: Optional[str] = None,
        response_text: Optional[str] = None,
        response_time_ms: Optional[int] = None,
        model_name: Optional[str] = None,
        used_fallback: Optional[bool] = None,
        failed_models: Optional[str] = None,
        knowledge_document_ids: Optional[str] = None,
        past_incorrect_attempts_count: Optional[int] = None,
        is_llm_only: Optional[bool] = None,
        level: Optional[int] = None,
        focus_weak_areas: Optional[bool] = None,
        log_type: str = 'knowledge'
    ):
        """
        Log knowledge document usage for analytics.
        
        Args:
            uid: Firebase User UID
            knowledge_doc_id: ID of the knowledge document used (optional)
            subject_id: ID of the subject
            question_count: Number of questions generated
            request_text: The AI prompt sent
            response_text: The AI response received
            response_time_ms: Generation time in milliseconds
            model_name: AI model used
            used_fallback: Whether fallback model was used
            failed_models: Comma-separated list of models that failed before success
            knowledge_document_ids: Comma-separated document IDs used
            past_incorrect_attempts_count: Number of weak areas targeted
            is_llm_only: Whether generation was LLM-only
            level: Requested difficulty level (1-6)
            focus_weak_areas: Whether weak areas mode was enabled
            log_type: Type of log entry (defaults to 'knowledge')
        """
        try:
            conn = db_provider._get_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                """
                INSERT INTO knowledge_usage_log 
                (uid, knowledge_doc_id, subject_id, question_count, request_text, response_text, 
                 response_time_ms, model_name, used_fallback, failed_models, knowledge_document_ids,
                 past_incorrect_attempts_count, is_llm_only, level, focus_weak_areas, log_type)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (uid, knowledge_doc_id, subject_id, question_count, request_text, response_text,
                 response_time_ms, model_name, used_fallback, failed_models, knowledge_document_ids,
                 past_incorrect_attempts_count, is_llm_only, level, focus_weak_areas, log_type)
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
            conn = db_provider._get_connection()
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
            
            # TODO: evaluate & decide later
            # Invalidate performance report cache when new attempts are added
            # performance_report_service.invalidate_cache()
            
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
            conn = db_provider._get_connection()
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
            
            logger.debug(f"Retrieved {len(results)} knowledge attempts for user {uid}, subject_id={subject_id}")
            if results:
                # Log first attempt for debugging
                first = results[0]
                logger.debug(f"Sample attempt: subject_id={first.get('subject_id')} (type: {type(first.get('subject_id'))}), eval_status='{first.get('evaluation_status')}'")
            return results
            
        except Exception as e:
            logger.error(f"Error fetching knowledge attempts: {e}")
            raise
    
    @staticmethod
    def create_knowledge_document(
        subject_id: int,
        title: str,
        content: str,
        grade_level: Optional[int] = None,
        source: Optional[str] = None
    ) -> int:
        """
        Create a new knowledge document.
        
        Args:
            subject_id: ID of the subject
            title: Document title
            content: Document content
            grade_level: Optional grade level (4-7)
            source: Optional source/creator identifier
            
        Returns:
            ID of the created document
        """
        try:
            conn = db_provider._get_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                """
                INSERT INTO knowledge_documents 
                (subject_id, title, content, grade_level, source)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
                """,
                (subject_id, title, content, grade_level, source)
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
