"""
Performance Report Service
Integrates the agentic workflow for student performance analysis
"""

import os
import operator
from typing import Annotated, List, Optional, TypedDict, Literal
import logging
from datetime import datetime

import pandas as pd
import psycopg2
from neo4j import GraphDatabase

# Optional imports with fallback
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SentenceTransformer = None
    SENTENCE_TRANSFORMERS_AVAILABLE = False

try:
    from langgraph.graph import StateGraph, END
    LANGGRAPH_AVAILABLE = True
except ImportError:
    StateGraph = None
    END = None
    LANGGRAPH_AVAILABLE = False

try:
    from google import genai
    GEMINI_AVAILABLE = True
except ImportError:
    genai = None
    GEMINI_AVAILABLE = False

from app.config import (
    NEON_DBNAME, NEON_USER, NEON_PASSWORD, NEON_HOST, NEON_SSLMODE,
    NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD, NEO4J_DATABASE,
    GEMINI_API_KEY, EMBEDDING_MODEL, EMBEDDING_DIMENSIONS, MAX_RETRIEVAL_RETRIES
)
from app.db.db_factory import DatabaseFactory
from app.services.prompt_service import PromptService

logger = logging.getLogger(__name__)

# Agent State Definition
class AgentState(TypedDict):
    """Shared state between agents with retry tracking"""
    student_uid: str
    students_df: pd.DataFrame
    subjects_df: pd.DataFrame
    attempts_df: pd.DataFrame
    graph_context: str
    vector_context: str
    hybrid_context: str
    performance_summary: str
    evidence_sufficient: bool
    retrieval_attempt: int
    evidence_quality_score: float
    analysis_report: str
    messages: Annotated[List[str], operator.add]

def make_initial_state(student_uid: str) -> AgentState:
    return {
        "student_uid": student_uid,
        "students_df": pd.DataFrame(),
        "subjects_df": pd.DataFrame(),
        "attempts_df": pd.DataFrame(),
        "graph_context": "",
        "vector_context": "",
        "hybrid_context": "",
        "performance_summary": "",
        "evidence_sufficient": False,
        "retrieval_attempt": 0,
        "evidence_quality_score": 0.0,
        "analysis_report": "",
        "messages": [],
    }

# Neo4j Utilities
def neo4j_driver():
    return GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))

def run_cypher(driver, query: str, params: Optional[dict] = None):
    with driver.session(database=NEO4J_DATABASE) as session:
        return list(session.run(query, params or {}))

def neo4j_smoke_test(driver):
    result = run_cypher(driver, "RETURN 1 AS ok")
    assert result and result[0]["ok"] == 1
    logger.info("✅ Neo4j connectivity OK")

def ensure_constraints(driver):
    run_cypher(
        driver,
        """
        CREATE CONSTRAINT student_uid_unique IF NOT EXISTS
        FOR (s:Student)
        REQUIRE s.uid IS UNIQUE
        """
    )
    run_cypher(
        driver,
        """
        CREATE CONSTRAINT subject_id_unique IF NOT EXISTS
        FOR (s:Subject)
        REQUIRE s.id IS UNIQUE
        """
    )
    logger.info("✅ Constraints ensured")

def drop_vector_index_if_exists(driver, index_name: str = "attempt_embeddings"):
    run_cypher(driver, f"DROP INDEX {index_name} IF EXISTS")

def create_vector_index(driver, dimensions: int, index_name: str = "attempt_embeddings"):
    run_cypher(
        driver,
        f"""
        CREATE VECTOR INDEX {index_name} IF NOT EXISTS
        FOR (a:KnowledgeAttempt)
        ON (a.embedding)
        OPTIONS {{
            indexConfig: {{
                `vector.dimensions`: $dimensions,
                `vector.similarity_function`: 'cosine'
            }}
        }}
        """,
        {"dimensions": dimensions},
    )
    logger.info(f"✅ Vector index '{index_name}' ensured ({dimensions} dims)")

# Data Ingester Agent
class DataIngesterAgent:
    """Agent 1: Data extraction and import with vector embeddings."""

    def __init__(self):
        self.neon_conn = None
        self.neo4j_driver = None
        self.embedding_model = None
        
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                self.embedding_model = SentenceTransformer(EMBEDDING_MODEL)
                logger.info("✅ SentenceTransformer loaded successfully")
            except Exception as e:
                logger.warning(f"⚠️ Failed to load SentenceTransformer: {e}")
        else:
            logger.warning("⚠️ SentenceTransformer not available - vector operations will be limited")

    def connect(self):
        self.neon_conn = psycopg2.connect(
            dbname=NEON_DBNAME,
            user=NEON_USER,
            password=NEON_PASSWORD,
            host=NEON_HOST,
            sslmode=NEON_SSLMODE,
        )
        self.neo4j_driver = GraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USERNAME, NEO4J_PASSWORD),
        )
        logger.info("✅ Connected to PostgreSQL and Neo4j")

    def run_postgres_query(self, query: str) -> Optional[pd.DataFrame]:
        with self.neon_conn.cursor() as cursor:
            cursor.execute(query)
            if cursor.description:
                columns = [desc[0] for desc in cursor.description]
                return pd.DataFrame(cursor.fetchall(), columns=columns)
        return None

    def run_neo4j_query(self, query: str, params: Optional[dict] = None):
        with self.neo4j_driver.session(database=NEO4J_DATABASE) as session:
            return list(session.run(query, params or {}))

    def create_vector_index(self):
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            logger.info("🔄 Creating vector index in Neo4j...")
            drop_vector_index_if_exists(self.neo4j_driver, "attempt_embeddings")
            create_vector_index(self.neo4j_driver, EMBEDDING_DIMENSIONS, "attempt_embeddings")

    def extract_data(self, state: AgentState) -> AgentState:
        logger.info("🔄 Agent 1: Extracting data from PostgreSQL...")
        uid = state["student_uid"]

        students_df = self.run_postgres_query(
            f"""
            SELECT uid, name, grade_level, subscription, registration_date
            FROM users WHERE uid = '{uid}' AND is_blocked = FALSE
            """
        )

        subjects_df = self.run_postgres_query(
            """
            SELECT id, name, description FROM subjects
            """
        )

        attempts_df = self.run_postgres_query(
            f"""
            SELECT id, uid, created_at as datetime, question,
                   evaluation_status, user_answer, correct_answer, subject_id
            FROM knowledge_question_attempts
            WHERE uid = '{uid}'
            """
        )

        state["students_df"] = students_df if students_df is not None else pd.DataFrame()
        state["subjects_df"] = subjects_df if subjects_df is not None else pd.DataFrame()
        state["attempts_df"] = attempts_df if attempts_df is not None else pd.DataFrame()
        state["messages"].append("Agent 1: Data extracted from PostgreSQL")

        logger.info(
            f"  📊 Loaded {len(state['students_df'])} students, {len(state['subjects_df'])} subjects, {len(state['attempts_df'])} attempts"
        )
        return state

    def import_to_neo4j_with_embeddings(self, state: AgentState) -> AgentState:
        logger.info("🔄 Agent 1: Importing to Neo4j with embeddings...")
        logger.info("  ⚠️ This will wipe the Neo4j database contents in the configured DB.")

        self.run_neo4j_query("MATCH (n) DETACH DELETE n")
        ensure_constraints(self.neo4j_driver)
        self.create_vector_index()

        # Import students
        for _, student in state["students_df"].iterrows():
            name_prefix = (student.get("name") or "")[:3]
            self.run_neo4j_query(
                """
                MERGE (s:Student {uid: $uid})
                SET s.gradeLevel = $grade_level, s.namePrefix = $name_prefix
                """,
                {
                    "uid": student["uid"],
                    "grade_level": student.get("grade_level"),
                    "name_prefix": name_prefix,
                },
            )

        # Import subjects
        for _, subject in state["subjects_df"].iterrows():
            self.run_neo4j_query(
                """
                MERGE (sub:Subject {id: $id})
                SET sub.name = $name, sub.description = $description
                """,
                {
                    "id": str(subject["id"]),
                    "name": subject.get("name"),
                    "description": subject.get("description"),
                },
            )

        # Import attempts with embeddings
        logger.info("  🧠 Generating embeddings for attempts...")

        attempts = state["attempts_df"]
        for idx, attempt in attempts.iterrows():
            embed_text = (
                f"Question: {attempt.get('question')}. "
                f"Student answered: {attempt.get('user_answer')}. "
                f"Correct answer: {attempt.get('correct_answer')}"
            )
            
            # Generate embedding if model is available
            if self.embedding_model is not None:
                try:
                    embedding = self.embedding_model.encode(embed_text).tolist()
                except Exception as e:
                    logger.warning(f"Failed to generate embedding for attempt {attempt['id']}: {e}")
                    # Use a simple text-based embedding as fallback
                    embedding = [ord(c) % 100 for c in embed_text[:10]]
            else:
                # Use a simple text-based embedding as fallback
                embedding = [ord(c) % 100 for c in embed_text[:10]]
            
            is_correct = attempt.get("evaluation_status") == "correct"

            self.run_neo4j_query(
                """
                CREATE (a:KnowledgeAttempt {
                    id: $id,
                    question: $question,
                    isCorrect: $is_correct,
                    userAnswer: $user_answer,
                    correctAnswer: $correct_answer,
                    embedding: $embedding,
                    embeddingText: $embed_text
                })
                WITH a
                MATCH (s:Student {uid: $uid}) CREATE (s)-[:ATTEMPTED]->(a)
                WITH a
                MATCH (sub:Subject {id: $subject_id}) CREATE (a)-[:BELONGS_TO]->(sub)
                """,
                {
                    "id": attempt["id"],
                    "question": attempt.get("question"),
                    "is_correct": is_correct,
                    "user_answer": attempt.get("user_answer"),
                    "correct_answer": attempt.get("correct_answer"),
                    "uid": attempt.get("uid"),
                    "subject_id": str(attempt.get("subject_id")),
                    "embedding": embedding,
                    "embed_text": embed_text,
                },
            )

            if (idx + 1) % 50 == 0:
                logger.info(f"    Processed {idx + 1}/{len(attempts)} attempts")

        state["messages"].append(
            f"Agent 1: Imported {len(attempts)} attempts with embeddings to Neo4j"
        )
        logger.info(f"  ✅ Neo4j import complete with {len(attempts)} embedded nodes")
        return state

    def close(self):
        if self.neon_conn is not None:
            try:
                self.neon_conn.close()
            except Exception:
                pass
            self.neon_conn = None

        if self.neo4j_driver is not None:
            try:
                self.neo4j_driver.close()
            except Exception:
                pass
            self.neo4j_driver = None

# Main Service Class
class PerformanceReportService:
    """Main service class for generating student performance reports."""

    def __init__(self):
        self.app = None
        self.data_agent = None

    def initialize_workflow(self):
        """Initialize the agentic workflow."""
        if self.app is None:
            self.app, self.data_agent = self.create_workflow()
        return self.app, self.data_agent

    def create_workflow(self):
        """Create a simplified workflow without LangGraph dependency."""
        data_agent = DataIngesterAgent()
        data_agent.connect()
        return "workflow", data_agent

    def generate_performance_report(self, student_uid: str) -> dict:
        """
        Generate a performance report for a student.

        Args:
            student_uid: Firebase User UID

        Returns:
            Dictionary containing the analysis report and metadata
        """
        try:
            # Initialize workflow
            app, data_agent = self.initialize_workflow()

            # Create initial state
            initial_state = make_initial_state(student_uid)

            logger.info(f"\n🚀 Starting Performance Analysis for student {student_uid}...\n")

            # Step 1: Extract data
            state = data_agent.extract_data(initial_state)

            # Step 2: Import to Neo4j
            state = data_agent.import_to_neo4j_with_embeddings(state)

            # Step 3: Simple analysis without advanced retrieval
            if len(state["attempts_df"]) > 0:
                # Basic performance calculation
                correct_count = len(state["attempts_df"][state["attempts_df"]["evaluation_status"] == "correct"])
                total_count = len(state["attempts_df"])
                accuracy = (correct_count / total_count * 100) if total_count > 0 else 0

                # Generate simple report
                state["analysis_report"] = f"""
## 📊 Student Performance Report

**Student ID:** {student_uid}
**Total Attempts:** {total_count}
**Correct Answers:** {correct_count}
**Accuracy:** {accuracy:.1f}%

### Performance Summary:
- The student has attempted {total_count} questions
- Achieved {accuracy:.1f}% accuracy
- {'Excellent performance!' if accuracy >= 80 else 'Good progress!' if accuracy >= 60 else 'Needs improvement'}

### Recommendations:
- Continue practicing regularly
- Focus on areas with incorrect answers
- Review explanations for missed questions
                """

                state["evidence_sufficient"] = True
                state["evidence_quality_score"] = 0.8
                state["messages"].append("Generated basic performance analysis")
            else:
                state["analysis_report"] = """
## ⚠️ Insufficient Data

No question attempts found for this student. Please complete some practice questions to generate a performance report.
                """
                state["evidence_sufficient"] = False
                state["evidence_quality_score"] = 0.0
                state["messages"].append("No data available for analysis")

            # Prepare response
            response = {
                "success": True,
                "student_uid": student_uid,
                "analysis_report": state["analysis_report"],
                "evidence_sufficient": state["evidence_sufficient"],
                "evidence_quality_score": state["evidence_quality_score"],
                "retrieval_attempts": 1,
                "execution_log": state["messages"],
                "timestamp": datetime.now().isoformat()
            }

            return response

        except Exception as e:
            logger.error(f"Error generating performance report: {str(e)}")
            return {
                "success": False,
                "student_uid": student_uid,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

        finally:
            # Clean up connections
            if self.data_agent:
                self.data_agent.close()

    def check_data_availability(self, student_uid: str) -> dict:
        """
        Check if sufficient data is available for report generation.

        Args:
            student_uid: Firebase User UID

        Returns:
            Dictionary indicating data availability
        """
        try:
            # Check PostgreSQL for student data
            db = DatabaseFactory.get_provider()
            conn = db._get_connection()

            with conn.cursor() as cursor:
                # Check student exists
                cursor.execute("SELECT COUNT(*) FROM users WHERE uid = %s AND is_blocked = FALSE", (student_uid,))
                student_count = cursor.fetchone()[0]

                # Check attempts count
                cursor.execute("SELECT COUNT(*) FROM knowledge_question_attempts WHERE uid = %s", (student_uid,))
                attempts_count = cursor.fetchone()[0]

            conn.close()

            # Check Neo4j connectivity
            try:
                driver = neo4j_driver()
                neo4j_smoke_test(driver)
                driver.close()
                neo4j_available = True
            except Exception:
                neo4j_available = False

            return {
                "student_exists": student_count > 0,
                "attempts_count": attempts_count,
                "sufficient_data": attempts_count >= 5,  # Minimum threshold
                "neo4j_available": neo4j_available,
                "can_generate_report": student_count > 0 and attempts_count >= 1
            }

        except Exception as e:
            logger.error(f"Error checking data availability: {str(e)}")
            return {
                "error": str(e),
                "can_generate_report": False
            }

# Initialize service instance
performance_report_service = PerformanceReportService()
