"""
Performance Report Service
Integrates the agentic workflow for student performance analysis
"""

import os
import operator
import json
from typing import Annotated, List, Optional, TypedDict, Literal, Dict, Any
import logging
from datetime import datetime

import pandas as pd
import psycopg2
from neo4j import GraphDatabase

# Optional imports with fallback
try:
    import sentence_transformers
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    sentence_transformers = None
    SENTENCE_TRANSFORMERS_AVAILABLE = False

try:
    from langgraph.graph import StateGraph, END
    LANGGRAPH_AVAILABLE = True
except ImportError:
    StateGraph = None
    END = None
    LANGGRAPH_AVAILABLE = False

try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    genai = None
    GENAI_AVAILABLE = False

try:
    from langsmith import Client as LangSmithClient
    from langsmith.run_helpers import traceable
    LANGSMITH_AVAILABLE = True
except ImportError:
    LangSmithClient = None
    traceable = None
    LANGSMITH_AVAILABLE = False

from app.config import (
    NEON_DBNAME, NEON_USER, NEON_PASSWORD, NEON_HOST, NEON_SSLMODE,
    NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD, NEO4J_DATABASE,
    GEMINI_API_KEY, EMBEDDING_MODEL, EMBEDDING_DIMENSIONS, MAX_RETRIEVAL_RETRIES,
    LANGSMITH_API_KEY, LANGSMITH_PROJECT, LANGSMITH_TRACING, AI_BRIDGE_MODEL
)
from app.db.db_factory import DatabaseFactory
from app.services.prompt_service import PromptService

logger = logging.getLogger(__name__)

# Minimum attempts for a subject to be considered sufficient evidence
MIN_ATTEMPTS_PER_SUBJECT = 10

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
    # Enhanced error tracking and agent status
    agent_statuses: Dict[str, Any]
    workflow_progress: List[str]
    errors: List[Dict[str, Any]]
    processing_time_ms: int
    model_used: str
    trace_id: Optional[str]

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
        # Enhanced error tracking and agent status
        "agent_statuses": {},
        "workflow_progress": [],
        "errors": [],
        "processing_time_ms": 0,
        "model_used": "",
        "trace_id": None
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
                from sentence_transformers import SentenceTransformer
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
        conn = self.neon_conn
        created_conn = False
        if conn is None:
            try:
                db = DatabaseFactory.get_provider()
                conn = db._get_connection()
                created_conn = True
            except Exception as e:
                logger.error(f"No Postgres connection available: {e}")
                return None

        try:
            with conn.cursor() as cursor:
                cursor.execute(query)
                if cursor.description:
                    columns = [desc[0] for desc in cursor.description]
                    rows = cursor.fetchall()
                    return pd.DataFrame(rows, columns=columns)
        finally:
            if created_conn and conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass

        return None

    def run_neo4j_query(self, query: str, params: Optional[dict] = None):
        driver = self.neo4j_driver
        created_driver = False
        if driver is None:
            try:
                driver = neo4j_driver()
                created_driver = True
            except Exception as e:
                logger.error(f"No Neo4j driver available: {e}")
                return []

        try:
            with driver.session(database=NEO4J_DATABASE) as session:
                return list(session.run(query, params or {}))
        finally:
            if created_driver and driver is not None:
                try:
                    driver.close()
                except Exception:
                    pass

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

# Agent 2: Retriever (Hybrid Graph + Vector Retrieval with Retry)
class RetrieverAgent:
    """Agent 2: Hybrid retrieval using Neo4j's unified graph + vector capabilities with evidence quality assessment."""

    def __init__(self, neo4j_driver, embedding_model):
        self.neo4j_driver = neo4j_driver
        self.embedding_model = embedding_model

    def run_neo4j_query(self, query: str, params: Optional[dict] = None):
        driver = self.neo4j_driver
        created_driver = False
        if driver is None:
            try:
                driver = neo4j_driver()
                created_driver = True
            except Exception as e:
                logger.error(f"RetrieverAgent: No Neo4j driver available: {e}")
                return []

        try:
            with driver.session(database=NEO4J_DATABASE) as session:
                return list(session.run(query, params or {}))
        finally:
            if created_driver and driver is not None:
                try:
                    driver.close()
                except Exception:
                    pass

    def assess_evidence_quality(self, state: AgentState) -> float:
        """Calculate evidence quality score (0-1) based on retrieved data."""
        score = 0.0

        # Check if we have performance summary
        if state.get("performance_summary") and len(state.get("performance_summary", "")) > 50:
            score += 0.3

        # Check if we have vector context (more robust: non-empty and reasonably long)
        if state.get("vector_context") and len(state.get("vector_context", "").strip()) > 20:
            score += 0.4

        # Check if we have hybrid context
        if state.get("hybrid_context") and len(state.get("hybrid_context", "")) > 100:
            score += 0.3

        # Grant evidence credit if at least one subject has enough attempts
        try:
            perf_df = state.get("performance_df")
            if perf_df is not None and not perf_df.empty:
                logger.debug(f"assess_evidence_quality: performance_df head:\n{perf_df.head().to_string()}\ncolumns={list(perf_df.columns)}")
                # look for at least one subject with total attempts >= MIN_ATTEMPTS_PER_SUBJECT
                if (perf_df["total"] >= MIN_ATTEMPTS_PER_SUBJECT).any():
                    # grant additional credit for strong per-subject evidence (cap at 1.0)
                    score = min(score + 0.3, 1.0)
        except Exception:
            # silently ignore malformed df
            pass

        return min(score, 1.0)

    def retrieve_graph_context(self, state: AgentState) -> AgentState:
        attempt_num = state["retrieval_attempt"] + 1
        logger.info(f"🔄 Agent 2: Retrieving graph context (attempt {attempt_num}/{MAX_RETRIEVAL_RETRIES + 1})...")
        uid = state["student_uid"]

        result = self.run_neo4j_query(
            """
            MATCH (s:Student {uid: $uid})-[:ATTEMPTED]->(ka:KnowledgeAttempt)-[:BELONGS_TO]->(sub:Subject)
            RETURN sub.name AS subject,
                   count(CASE WHEN ka.isCorrect = true THEN 1 END) AS correct,
                   count(CASE WHEN ka.isCorrect = false THEN 1 END) AS incorrect
            ORDER BY incorrect DESC
            """,
            {"uid": uid},
        )

        performance_data = []
        for record in result:
            performance_data.append({
                "subject": record["subject"],
                "correct": record["correct"],
                "incorrect": record["incorrect"],
                "total": record["correct"] + record["incorrect"],
                "accuracy": (record["correct"] / (record["correct"] + record["incorrect"]) * 100) if (record["correct"] + record["incorrect"]) > 0 else 0
            })
        performance_df = pd.DataFrame(performance_data)
        # Save the DataFrame to state so evidence scoring can inspect per-subject counts
        state["performance_df"] = performance_df
        state["performance_summary"] = performance_df.to_string(index=False)
        state["graph_context"] = f"Graph-based performance analysis:\n{state['performance_summary']}"
        state["messages"].append(f"Agent 2: Retrieved graph context (attempt {attempt_num})")

        logger.info(f"  ✅ Retrieved performance for {len(performance_data)} subjects")
        return state

    def retrieve_vector_context(self, state: AgentState) -> AgentState:
        attempt_num = state["retrieval_attempt"] + 1
        logger.info(f"🔄 Agent 2: Performing vector similarity search (attempt {attempt_num}/{MAX_RETRIEVAL_RETRIES + 1})...")
        uid = state["student_uid"]

        # Adjust query based on retrieval attempt
        if attempt_num == 1:
            query_text = "repeated mistakes and learning gaps"
        else:
            query_text = "common incorrect answers and patterns"

        # Encode query to embedding; fall back to deterministic simple embedding if model missing
        query_embedding = None
        if self.embedding_model is not None:
            try:
                query_embedding = self.embedding_model.encode(query_text).tolist()
            except Exception as e:
                logger.warning(f"RetrieverAgent: embedding_model.encode failed, using fallback embedding: {e}")

        if query_embedding is None:
            # deterministic fallback: map chars to small ints and repeat/truncate to EMBEDDING_DIMENSIONS
            chars = [ord(c) % 100 for c in query_text]
            if not chars:
                chars = [0]
            # expand/repeat to required length
            dims = EMBEDDING_DIMENSIONS if EMBEDDING_DIMENSIONS and isinstance(EMBEDDING_DIMENSIONS, int) else 10
            query_embedding = (chars * ((dims // len(chars)) + 1))[:dims]

        result = self.run_neo4j_query(
            """
            CALL db.index.vector.queryNodes('attempt_embeddings', 5, $query_embedding)
            YIELD node, score
            WHERE node.uid = $uid
            RETURN node.question AS question, node.isCorrect AS isCorrect,
                   node.userAnswer AS userAnswer, node.correctAnswer AS correctAnswer, score
            ORDER BY score DESC LIMIT 5
            """,
            {"query_embedding": query_embedding, "uid": uid},
        )

        vector_context = []
        for record in result:
            vector_context.append({
                "question": record["question"],
                "is_correct": record["isCorrect"],
                "user_answer": record["userAnswer"],
                "correct_answer": record["correctAnswer"],
                "similarity_score": record["score"]
            })

        state["vector_context"] = "\n".join([
            f"- Question: {item['question'][:100]}..."
            f"\n  Student answered: {item['user_answer']}"
            f"\n  Correct: {item['correct_answer']}"
            f"\n  Similarity: {item['similarity_score']:.3f}"
            for item in vector_context
        ])
        state["messages"].append(f"Agent 2: Retrieved vector context (attempt {attempt_num})")

        logger.info(f"  ✅ Retrieved {len(vector_context)} similar attempts")
        return state

    def retrieve_hybrid_context(self, state: AgentState) -> AgentState:
        attempt_num = state["retrieval_attempt"] + 1
        logger.info(f"🔄 Agent 2: Performing hybrid context retrieval (attempt {attempt_num}/{MAX_RETRIEVAL_RETRIES + 1})...")

        # Combine graph and vector context
        state["hybrid_context"] = f"""
Graph Analysis:
{state['graph_context']}

Vector Similarity Analysis:
{state['vector_context']}
        """.strip()

        state["messages"].append(f"Agent 2: Combined hybrid context (attempt {attempt_num})")
        logger.info("  ✅ Combined hybrid context")
        return state

    def perform_retrieval(self, state: AgentState) -> AgentState:
        """Main retrieval orchestration with quality assessment."""
        state["retrieval_attempt"] += 1

        # Retrieve different types of context
        state = self.retrieve_graph_context(state)
        state = self.retrieve_vector_context(state)
        state = self.retrieve_hybrid_context(state)

        # Assess evidence quality
        state["evidence_quality_score"] = self.assess_evidence_quality(state)
        # Primary threshold check
        state["evidence_sufficient"] = state["evidence_quality_score"] >= 0.7

        # Secondary check: if any subject has MIN_ATTEMPTS_PER_SUBJECT, force sufficiency
        try:
            perf_df = state.get("performance_df")
            if perf_df is not None and not perf_df.empty:
                if (perf_df["total"] >= MIN_ATTEMPTS_PER_SUBJECT).any():
                    state["evidence_sufficient"] = True
                    # ensure score reflects that
                    state["evidence_quality_score"] = max(state["evidence_quality_score"], 0.8)
        except Exception:
            pass

        state["messages"].append(f"Agent 2: Evidence quality score: {state['evidence_quality_score']:.2f}")
        logger.info(f"  📊 Evidence quality: {state['evidence_quality_score']:.2f} (sufficient: {state['evidence_sufficient']})")

        return state

# Agent 3: Analyst (LLM-powered Report Generation)
class AnalystAgent:
    """Agent 3: LLM-powered analysis using retrieved context with evidence sufficiency checking."""

    def __init__(self):
        self.model = None
        if GENAI_AVAILABLE:
            logger.info("✅ Google GenAI library available")
        if GEMINI_API_KEY:
            logger.info("⚠️ Google GEMINI_API_KEY available")
        if GENAI_AVAILABLE and GEMINI_API_KEY:
            try:
                genai.configure(api_key=GEMINI_API_KEY)
                self.model = genai.GenerativeModel("gemini-2.5-flash")
                logger.info("✅ Gemini model initialized")
            except Exception as e:
                logger.warning(f"⚠️ Failed to initialize Gemini: {e}")
                self.model = None
        else:
            logger.warning("⚠️ Gemini AI not available")

    def generate_report(self, state: AgentState) -> AgentState:
        logger.info("🔄 Agent 3: Generating performance analysis report...")

        if not self.model:
            state["analysis_report"] = (
                """
## ⚠️ AI Analysis Unavailable

The AI analysis service is currently unavailable. Please check the system configuration.
                """
            ).strip()
            state["messages"].append("Agent 3: AI model not available")
            return state

        if not state.get("evidence_sufficient", False):
            state["analysis_report"] = (
                f"""
## 📊 Basic Performance Report

**Evidence Quality Score:** {state['evidence_quality_score']:.2f}
**Retrieval Attempts:** {state['retrieval_attempt']}

### Limited Analysis Available
The available data was insufficient for comprehensive AI analysis. Here's what we found:

{state['performance_summary']}

### Recommendations:
- Complete more practice questions to enable detailed analysis
- Focus on subjects with higher incorrect answer rates
                """
            ).strip()
            state["messages"].append(
                "Agent 3: Generated basic report due to insufficient evidence"
            )
            return state

        # Generate comprehensive report using LLM
        prompt = (
            f"""
You are an expert educational analyst. Analyze this student's performance data and provide a comprehensive report.

Student Performance Data:
{state['hybrid_context']}

Evidence Quality Score: {state['evidence_quality_score']:.2f}
Retrieval Attempts: {state['retrieval_attempt']}

Please provide a detailed analysis including:
1. Overall performance assessment
2. Subject-wise strengths and weaknesses
3. Learning patterns and common mistakes
4. Specific recommendations for improvement
5. Study strategies tailored to this student

Format the report in clear, engaging markdown with sections and bullet points.
Keep it encouraging and actionable for a student.
            """
        )

        try:
            response = self.model.generate_content(prompt)
            state["analysis_report"] = response.text
            state["model_used"] = "gemini-2.5-flash"
            state["messages"].append(
                "Agent 3: Generated comprehensive AI analysis report"
            )
            logger.info("  ✅ AI analysis report generated successfully")
        except Exception as e:
            logger.error(f"  ❌ AI analysis failed: {e}")
            state["analysis_report"] = (
                f"""
## ⚠️ Analysis Error

An error occurred during AI analysis: {str(e)}

### Fallback Analysis
{state['performance_summary']}
                """
            ).strip()
            state["model_used"] = "error-fallback"
            state["messages"].append(
                f"Agent 3: AI analysis failed: {str(e)}"
            )

        return state

# Main Service Class
class PerformanceReportService:
    """Main service class for generating student performance reports."""

    def __init__(self):
        self.app = None
        self.data_agent = None
        self.langsmith_client = None
        self.cache_last_invalidation = None
        self.cache_ttl_hours = 24

        # Initialize LangSmith client if available
        if LANGSMITH_AVAILABLE and LANGSMITH_API_KEY and LANGSMITH_TRACING:
            try:
                self.langsmith_client = LangSmithClient(
                    api_key=LANGSMITH_API_KEY,
                    project=LANGSMITH_PROJECT
                )
                logger.info("✅ LangSmith client initialized")
            except Exception as e:
                logger.warning(f"⚠️ Failed to initialize LangSmith client: {e}")
                self.langsmith_client = None
        else:
            logger.info("ℹ️ LangSmith tracing not configured or disabled")

    def invalidate_cache(self):
        """Invalidate the cache by updating the last invalidation timestamp."""
        from datetime import datetime
        self.cache_last_invalidation = datetime.now()
        logger.info("Cache invalidated due to new attempt submission")

    def is_cache_valid(self) -> bool:
        """Check if the cache is still valid (within TTL)."""
        if self.cache_last_invalidation is None:
            return True
        from datetime import datetime, timedelta
        return datetime.now() - self.cache_last_invalidation < timedelta(hours=self.cache_ttl_hours)

    def save_performance_report(self, student_uid: str, report_data: dict) -> bool:
        """Save a performance report to the database."""
        try:
            db = DatabaseFactory.get_provider()
            conn = db._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO performance_reports (
                    uid, report_content, report_format, agent_statuses, execution_log,
                    traces, evidence_sufficient, evidence_quality_score, retrieval_attempts,
                    errors, success, processing_time_ms, model_used, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            """, (
                student_uid,
                report_data.get('analysis_report', ''),
                report_data.get('report_format', 'markdown'),
                json.dumps(report_data.get('agent_statuses', {})),
                json.dumps(report_data.get('execution_log', [])),
                report_data.get('trace_id'),
                report_data.get('evidence_sufficient', False),
                report_data.get('evidence_quality_score', 0.0),
                report_data.get('retrieval_attempts', 1),
                json.dumps(report_data.get('errors', [])),
                report_data.get('success', True),
                report_data.get('processing_time_ms', 0),
                report_data.get('model_used', '')
            ))

            conn.commit()
            cursor.close()
            conn.close()
            logger.info(f"Performance report saved for student {student_uid}")
            return True

        except Exception as e:
            logger.error(f"Error saving performance report: {str(e)}")
            return False

    def get_performance_reports(self, student_uid: str) -> list:
        """Retrieve performance reports for a student."""
        try:
            db = DatabaseFactory.get_provider()
            conn = db._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT id, report_content, report_format, agent_statuses, execution_log,
                       traces, evidence_sufficient, evidence_quality_score, retrieval_attempts,
                       errors, success, processing_time_ms, model_used, created_at, updated_at
                FROM performance_reports
                WHERE uid = %s
                ORDER BY created_at DESC
            """, (student_uid,))

            reports = []
            for row in cursor.fetchall():
                reports.append({
                    'id': row[0],
                    'report_content': row[1],
                    'report_format': row[2],
                    'agent_statuses': json.loads(row[3]) if row[3] else {},
                    'execution_log': json.loads(row[4]) if row[4] else [],
                    'trace_id': row[5],
                    'evidence_sufficient': row[6],
                    'evidence_quality_score': row[7],
                    'retrieval_attempts': row[8],
                    'errors': json.loads(row[9]) if row[9] else [],
                    'success': row[10],
                    'processing_time_ms': row[11],
                    'model_used': row[12],
                    'created_at': row[13].isoformat() if row[13] else None,
                    'updated_at': row[14].isoformat() if row[14] else None
                })

            cursor.close()
            conn.close()
            return reports

        except Exception as e:
            logger.error(f"Error retrieving performance reports: {str(e)}")
            return []

    def check_cooldown(self, student_uid: str, admin_key: str = None) -> dict:
        """Check if the user is within the 24-hour cooldown period."""
        try:
            # Check admin bypass
            expected_admin_key = os.getenv('ADMIN_KEY', 'dev-admin-key')
            if admin_key == expected_admin_key:
                return {'can_generate': True, 'cooldown_remaining': 0, 'admin_bypass': True}

            db = DatabaseFactory.get_provider()
            conn = db._get_connection()
            cursor = conn.cursor()

            # Get the most recent report creation time
            cursor.execute("""
                SELECT created_at FROM performance_reports
                WHERE uid = %s
                ORDER BY created_at DESC
                LIMIT 1
            """, (student_uid,))

            result = cursor.fetchone()
            cursor.close()
            conn.close()

            if not result:
                return {'can_generate': True, 'cooldown_remaining': 0, 'admin_bypass': False}

            last_generation = result[0]
            from datetime import datetime, timedelta, timezone
            now = datetime.now(timezone.utc)
            cooldown_end = last_generation + timedelta(hours=24)

            if now >= cooldown_end:
                return {'can_generate': True, 'cooldown_remaining': 0, 'admin_bypass': False}
            else:
                remaining_seconds = int((cooldown_end - now).total_seconds())
                return {
                    'can_generate': False,
                    'cooldown_remaining': remaining_seconds,
                    'cooldown_end': cooldown_end.isoformat(),
                    'admin_bypass': False,
                    'error': 'daily_limit_exceeded'
                }

        except Exception as e:
            logger.error(f"Error checking cooldown: {str(e)}")
            return {'can_generate': False, 'error': str(e)}

    def initialize_workflow(self):
        """Initialize the agentic workflow."""
        if self.app is None:
            self.app, self.data_agent = self.create_workflow()
        return self.app, self.data_agent

    def create_workflow(self):
        """Create LangGraph workflow for multi-agent orchestration with retry loop.
           When PERFORMANCE_REPORT_ISOLATE_ANALYST=true, use a minimal app to run only AnalystAgent for testing.
        """
        isolate_flag = os.getenv("PERFORMANCE_REPORT_ISOLATE_ANALYST", "false").lower() == "true"

        try:
            analyst_agent = AnalystAgent()
        except Exception as e:
            logger.error(f"Failed to initialize AnalystAgent: {e}")
            # Return a minimal no-op app and no data_agent
            class NoOpApp:
                def invoke(self, state):
                    state.setdefault("messages", []).append("AnalystAgent initialization failed")
                    state["analysis_report"] = "## ⚠️ Analyst initialization failed"
                    state["evidence_sufficient"] = False
                    return state
            return NoOpApp(), None

        if isolate_flag:
            # Minimal app that exposes an `invoke(state)` method expected by _execute_workflow_steps
            class SimpleAnalystApp:
                def invoke(self, state):
                    # Ensure state has required fields for analysis to run
                    state.setdefault("messages", [])
                    try:
                        # Directly call the analyst to generate the report using existing state
                        new_state = analyst_agent.generate_report(state)
                        return new_state
                    except Exception as e:
                        logger.error(f"SimpleAnalystApp.invoke failed: {e}")
                        state.setdefault("errors", []).append({
                            "step": "analyze",
                            "message": str(e),
                            "timestamp": datetime.now().isoformat()
                        })
                        state["analysis_report"] = f"## ⚠️ Analysis Error\n\nAn error occurred: {str(e)}"
                        state["evidence_sufficient"] = False
                        return state

            app = SimpleAnalystApp()
            logger.info("✅ Simple workflow created: AnalystAgent only (isolation enabled via env var)")
            return app, None

        # Normal workflow (LangGraph) creation
        if not LANGGRAPH_AVAILABLE:
            logger.warning("⚠️ LangGraph not available, falling back to simplified workflow")
            data_agent = DataIngesterAgent()
            data_agent.connect()
            return "workflow", data_agent

        data_agent = DataIngesterAgent()
        data_agent.connect()

        retriever_agent = RetrieverAgent(data_agent.neo4j_driver, data_agent.embedding_model)
        # analyst_agent already initialized above

        workflow = StateGraph(AgentState)

        # Add nodes
        workflow.add_node("extract_data", data_agent.extract_data)
        workflow.add_node("import_with_embeddings", data_agent.import_to_neo4j_with_embeddings)
        workflow.add_node("retrieve", retriever_agent.perform_retrieval)
        workflow.add_node("analyze", analyst_agent.generate_report)

        def should_retry_retrieval(state: AgentState) -> Literal["retrieve", "analyze"]:
            """Decide whether to retry retrieval or proceed to analysis."""
            if state["evidence_sufficient"] or state["retrieval_attempt"] >= MAX_RETRIEVAL_RETRIES:
                return "analyze"
            else:
                logger.info(f"🔄 Retrying retrieval (attempt {state['retrieval_attempt'] + 1}/{MAX_RETRIEVAL_RETRIES})")
                return "retrieve"

        # Set up the workflow edges
        workflow.set_entry_point("extract_data")
        workflow.add_edge("extract_data", "import_with_embeddings")
        workflow.add_edge("import_with_embeddings", "retrieve")
        workflow.add_edge("analyze", END)

        # Conditional edge from retrieve to either retry or analyze
        workflow.add_conditional_edges(
            "retrieve",
            should_retry_retrieval,
            {
                "retrieve": "retrieve",
                "analyze": "analyze"
            }
        )

        app = workflow.compile()
        logger.info("✅ LangGraph workflow created with retry mechanism")
        return app, data_agent

    def generate_performance_report(self, student_uid: str, admin_key: str = None) -> dict:
        """
        Generate a performance report for a student with enhanced error tracking and persistence.

        Args:
            student_uid: Firebase User UID
            admin_key: Admin key for bypassing cooldown

        Returns:
            Dictionary containing the analysis report and metadata
        """
        start_time = datetime.now()
        trace_id = None

        try:
            # Check cooldown first
            cooldown_check = self.check_cooldown(student_uid, admin_key)
            if not cooldown_check.get('can_generate', False):
                return {
                    "success": False,
                    "student_uid": student_uid,
                    "error": cooldown_check.get('error', 'cooldown_active'),
                    "cooldown_remaining": cooldown_check.get('cooldown_remaining', 0),
                    "cooldown_end": cooldown_check.get('cooldown_end'),
                    "timestamp": datetime.now().isoformat()
                }

            # Initialize workflow (but may skip later if running only analyst)
            app, data_agent = self.initialize_workflow()

            # Create initial state
            state = make_initial_state(student_uid)
            # Allow running only Agent 3 (Analyst) when toggle present in admin_key param
            # Use admin_key='run_only_analyst' or pass via a proper parameter in API later
            run_only_analyst = False
            # if isinstance(admin_key, str) and admin_key.strip().lower() == 'run_only_analyst':
            #     run_only_analyst = True
            state["agent_statuses"] = {}
            state["workflow_progress"] = []
            state["errors"] = []
            state["processing_time_ms"] = 0
            state["model_used"] = "gemini-2.5-flash" # "basic-analysis"  # Default model

            logger.info(f"\n🚀 Starting Performance Analysis for student {student_uid}...\n")

            # If requested, run only the Analyst agent using a minimal state
            if run_only_analyst:
                logger.info("ℹ️ Running only Agent 3 (Analyst) as requested")
                analyst = AnalystAgent()
                # Build minimal state: fetch performance summary from Postgres
                try:
                    db = DatabaseFactory.get_provider()
                    conn = db._get_connection()
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT id, question, user_answer, correct_answer, evaluation_status FROM knowledge_question_attempts WHERE uid = %s ORDER BY created_at DESC LIMIT 50",
                        (student_uid,)
                    )
                    rows = cursor.fetchall()
                    cursor.close()
                    conn.close()

                    # Create a small performance summary
                    perf_lines = []
                    for r in rows:
                        q = (r[1] or '')
                        ua = r[2]
                        ca = r[3]
                        status = r[4]
                        perf_lines.append(f"Q: {q[:120]} | Ans: {ua} | Correct: {ca} | Status: {status}")

                    state['performance_summary'] = '\n'.join(perf_lines)
                    state['hybrid_context'] = state['performance_summary']
                    state['evidence_sufficient'] = len(rows) >= 5
                    state['evidence_quality_score'] = 0.8 if state['evidence_sufficient'] else 0.4

                except Exception as e:
                    logger.error(f"Failed to build minimal state for analyst-only run: {e}")
                    state['performance_summary'] = ''
                    state['hybrid_context'] = ''
                    state['evidence_sufficient'] = False
                    state['evidence_quality_score'] = 0.0

                final_state = analyst.generate_report(state)
                # Build response similar to full workflow
                end_time = datetime.now()
                processing_time_ms = int((end_time - start_time).total_seconds() * 1000)
                response = {
                    'success': True,
                    'student_uid': student_uid,
                    'analysis_report': final_state.get('analysis_report', ''),
                    'evidence_sufficient': final_state.get('evidence_sufficient', False),
                    'evidence_quality_score': final_state.get('evidence_quality_score', 0.0),
                    'retrieval_attempts': final_state.get('retrieval_attempt', 0),
                    'execution_log': final_state.get('messages', []),
                    'agent_statuses': final_state.get('agent_statuses', {}),
                    'workflow_progress': final_state.get('workflow_progress', []),
                    'errors': final_state.get('errors', []),
                    'processing_time_ms': processing_time_ms,
                    'model_used': final_state.get('model_used', ''),
                    'trace_id': final_state.get('trace_id'),
                    'timestamp': end_time.isoformat()
                }

                # Save report
                if response['success']:
                    save_success = self.save_performance_report(student_uid, response)
                    if not save_success:
                        logger.warning('Failed to save analyst-only performance report to database')

                return response

            # Wrap execution with LangSmith tracing if available
                if self.langsmith_client and traceable:
                    try:
                        # Start an explicit LangSmith run so events/records are sent
                        run = self.langsmith_client.runs.create(
                            name=f"performance_report_{student_uid}_{int(start_time.timestamp())}",
                            project=LANGSMITH_PROJECT,
                            metadata={"student_uid": student_uid}
                        )
                        run_id = getattr(run, "id", None) or run.get("id") if isinstance(run, dict) else None
                        # Attach traceable wrapper if available to capture nested traces
                        @traceable(client=self.langsmith_client, project_name=LANGSMITH_PROJECT)
                        def execute_workflow():
                            return self._execute_workflow_steps(state, app, data_agent)

                        workflow_result = execute_workflow()

                        # Close/run finalize if client supports it
                        try:
                            # some LangSmith clients expose runs.finish or similar
                            if hasattr(self.langsmith_client.runs, 'update') and run_id:
                                self.langsmith_client.runs.update(run_id, status="succeeded")
                        except Exception:
                            pass

                        trace_id = run_id or f"trace_{student_uid}_{int(start_time.timestamp())}"
                    except Exception as e:
                        logger.warning(f"LangSmith tracing failed to start run: {e}")
                        workflow_result = self._execute_workflow_steps(state, app, data_agent)
                        trace_id = f"trace_{student_uid}_{int(start_time.timestamp())}"
            else:
                workflow_result = self._execute_workflow_steps(state, app, data_agent)

            # Calculate processing time
            end_time = datetime.now()
            processing_time_ms = int((end_time - start_time).total_seconds() * 1000)
            state["processing_time_ms"] = processing_time_ms

            # Prepare response
            response = {
                "success": workflow_result["success"],
                "student_uid": student_uid,
                "analysis_report": workflow_result["analysis_report"],
                "evidence_sufficient": workflow_result["evidence_sufficient"],
                "evidence_quality_score": workflow_result["evidence_quality_score"],
                "retrieval_attempts": workflow_result["retrieval_attempts"],
                "execution_log": workflow_result["execution_log"],
                "agent_statuses": workflow_result.get("agent_statuses", state.get("agent_statuses", {})),
                "workflow_progress": workflow_result.get("workflow_progress", state.get("workflow_progress", [])),
                "errors": state.get("errors", []),
                "processing_time_ms": processing_time_ms,
                "model_used": workflow_result.get("model_used", state.get("model_used", "")),
                "trace_id": workflow_result.get("trace_id", trace_id),
                "timestamp": end_time.isoformat()
            }

            # Save to database if successful
            if response["success"]:
                save_success = self.save_performance_report(student_uid, response)
                if not save_success:
                    logger.warning("Failed to save performance report to database")

            return response

        except Exception as e:
            end_time = datetime.now()
            processing_time_ms = int((end_time - start_time).total_seconds() * 1000)

            error_details = {
                "message": str(e),
                "code": "report_generation_failed",
                "stack_snippet": str(e)[:200]  # Limited stack trace
            }

            logger.error(f"Error generating performance report: {str(e)}")
            return {
                "success": False,
                "student_uid": student_uid,
                "error": str(e),
                "errors": [error_details],
                "processing_time_ms": processing_time_ms,
                "trace_id": trace_id,
                "timestamp": end_time.isoformat()
            }

        finally:
            # Clean up connections
            if self.data_agent:
                self.data_agent.close()

    def _execute_workflow_steps(self, state: AgentState, app, data_agent) -> dict:
        """Execute the full LangGraph workflow with enhanced error tracking."""
        try:
            # Initialize workflow progress
            state["workflow_progress"].append("Starting multi-agent workflow")
            state["agent_statuses"]["workflow"] = {"status": "in_progress", "start_time": datetime.now().isoformat()}

            # Execute the LangGraph workflow
            logger.info("🚀 Executing LangGraph multi-agent workflow...")
            final_state = app.invoke(state)

            # Update completion status
            state["agent_statuses"]["workflow"]["status"] = "completed"
            state["agent_statuses"]["workflow"]["end_time"] = datetime.now().isoformat()
            state["workflow_progress"].append("Multi-agent workflow completed")

            return {
                "success": True,
                "analysis_report": final_state["analysis_report"],
                "evidence_sufficient": final_state["evidence_sufficient"],
                "evidence_quality_score": final_state["evidence_quality_score"],
                "retrieval_attempts": final_state["retrieval_attempt"],
                "execution_log": final_state["messages"],
                "agent_statuses": final_state["agent_statuses"],
                "workflow_progress": final_state["workflow_progress"],
                "model_used": final_state["model_used"],
                "trace_id": final_state.get("trace_id")
            }

        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            # Record error in state
            error_info = {
                "step": "workflow_execution",
                "message": str(e),
                "code": "workflow_error",
                "timestamp": datetime.now().isoformat()
            }
            state["errors"].append(error_info)

            # Update agent statuses for failed workflow
            state["agent_statuses"]["workflow"] = {
                "status": "failed",
                "error": str(e),
                "end_time": datetime.now().isoformat()
            }
            state["workflow_progress"].append(f"Workflow failed: {str(e)}")

            return {
                "success": False,
                "analysis_report": f"## ⚠️ Workflow Error\n\nAn error occurred during analysis: {str(e)}\n\nPlease try again later.",
                "evidence_sufficient": False,
                "evidence_quality_score": 0.0,
                "retrieval_attempts": state.get("retrieval_attempt", 0),
                "execution_log": state["messages"],
                "agent_statuses": state["agent_statuses"],
                "workflow_progress": state["workflow_progress"],
                "model_used": "error-fallback",
                "trace_id": None
            }

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