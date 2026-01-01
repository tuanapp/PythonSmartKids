"""
Performance Report Service
Integrates the agentic workflow for student performance analysis
"""

import os
import re
import operator
import json
from typing import Annotated, List, Optional, TypedDict, Literal, Dict, Any, Tuple
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

from app.services.subject_taxonomy import SUBJECT_TAXONOMY

from app.config import (
    NEON_DBNAME, NEON_USER, NEON_PASSWORD, NEON_HOST, NEON_SSLMODE,
    NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD, NEO4J_DATABASE,
    GEMINI_API_KEY, EMBEDDING_MODEL, EMBEDDING_DIMENSIONS, MAX_RETRIEVAL_RETRIES,
    LANGSMITH_API_KEY, LANGSMITH_PROJECT, LANGSMITH_TRACING, AI_BRIDGE_MODEL
)
from app.db.db_factory import DatabaseFactory
from app.services.prompt_service import PromptService

# Helper to conditionally apply traceable decorator
def maybe_traceable(func):
    """Apply @traceable decorator if LangSmith is available and enabled."""
    if LANGSMITH_AVAILABLE and traceable and LANGSMITH_TRACING:
        return traceable(name=f"{func.__qualname__}")(func)
    return func

logger = logging.getLogger(__name__)

# Minimum attempts for a subject to be considered sufficient evidence
MIN_ATTEMPTS_PER_SUBJECT = 10
DEFAULT_MODEL_NAME = "gemini-2.5-flash"

EMAIL_RE = re.compile(r"(?i)\\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\\.[A-Z]{2,}\\b")
PHONE_RE = re.compile(r"(?<!\\d)(?:\\+?\\d[\\d\\s().-]{7,}\\d)")
CARD_RE = re.compile(r"\\b(?:\\d[ -]*?){13,19}\\b")

PROMPT_INJECTION_MARKERS = [
    "ignore previous",
    "system prompt",
    "developer message",
    "act as",
    "jailbreak",
    "bypass",
    "do anything now",
    "reveal hidden",
]

DISALLOWED_CONTENT_MARKERS = [
    "porn",
    "sexual",
    "nude",
    "explicit",
    "drug",
    "violence",
    "hate",
]

SUBJECT_ALIASES = {
    "math": "Math",
    "maths": "Math",
    "mathematics": "Math",
    "english": "English",
    "french": "French",
    "science": "Science",
    "physics": "Physics",
    "chemistry": "Chemistry",
    "biology": "Biology",
    "history": "History",
    "geography": "Geography",
}

TOPIC_PHRASES = [
    "reflexive verbs",
    "subject-verb agreement",
    "subject verb agreement",
    "object pronoun",
]

def _mask_api_key(api_key: Optional[str]) -> str:
    if not api_key:
        return ""
    if len(api_key) <= 8:
        return "*" * len(api_key)
    return f"{api_key[:4]}...{api_key[-4:]}"

def _get_api_key_hint() -> str:
    return _mask_api_key(GEMINI_API_KEY)

def _extract_subject_topic(query_text: str) -> tuple[Optional[str], Optional[str]]:
    lowered = (query_text or "").lower()
    subject = None
    topic = None

    for alias, canonical in SUBJECT_ALIASES.items():
        if re.search(rf"\\b{re.escape(alias)}\\b", lowered):
            subject = canonical
            break

    for phrase in TOPIC_PHRASES:
        if phrase in lowered:
            topic = phrase
            break

    if not topic:
        keywords = _extract_query_keywords(query_text)
        if keywords:
            topic = keywords[0]

    if not subject:
        if any(token in lowered for token in ["fraction", "fractions", "algebra", "geometry", "decimal", "ratio"]):
            subject = "Math"
        elif any(token in lowered for token in ["verb", "pronoun", "tense", "interjection"]):
            subject = "English"
        elif "french" in lowered:
            subject = "French"

    return subject, topic

def _extract_fallback_missed_questions(fallback_text: str) -> List[str]:
    lines = (fallback_text or "").splitlines()
    try:
        start = lines.index("Most missed questions:") + 1
    except ValueError:
        return []
    questions = []
    for line in lines[start:]:
        line = line.strip()
        if not line.startswith("- "):
            continue
        question = line[2:].split(" - missed", 1)[0].strip()
        if question:
            questions.append(question)
    return questions
def _mask_pii(text: str) -> tuple[str, Dict[str, Any]]:
    flags: Dict[str, Any] = {"masked": False, "types": []}
    if not text:
        return text, flags

    masked = text
    if EMAIL_RE.search(masked):
        masked = EMAIL_RE.sub("[redacted_email]", masked)
        flags["types"].append("email")
    if PHONE_RE.search(masked):
        masked = PHONE_RE.sub("[redacted_phone]", masked)
        flags["types"].append("phone")
    if CARD_RE.search(masked):
        masked = CARD_RE.sub("[redacted_card]", masked)
        flags["types"].append("card")

    if flags["types"]:
        flags["masked"] = True
    return masked, flags

def _contains_markers(text: str, markers: List[str]) -> List[str]:
    lowered = (text or "").lower()
    return [marker for marker in markers if marker in lowered]

def _apply_input_guardrails(query_text: str) -> tuple[str, Dict[str, Any], bool, Optional[str]]:
    masked_text, pii_flags = _mask_pii(query_text or "")
    prompt_hits = _contains_markers(masked_text, PROMPT_INJECTION_MARKERS)
    content_hits = _contains_markers(masked_text, DISALLOWED_CONTENT_MARKERS)

    guardrails = {
        "pii": pii_flags,
        "prompt_injection": prompt_hits,
        "disallowed_content": content_hits,
    }

    if prompt_hits:
        return masked_text, guardrails, True, "prompt_injection_detected"
    if content_hits:
        return masked_text, guardrails, True, "disallowed_content"

    return masked_text, guardrails, False, None

def _apply_output_guardrails(text: str) -> tuple[str, Dict[str, Any]]:
    content_hits = _contains_markers(text or "", DISALLOWED_CONTENT_MARKERS)
    guardrails = {"disallowed_content": content_hits}
    if content_hits:
        return "Content filtered due to safety policy.", guardrails
    return text, guardrails

def _extract_query_keywords(query_text: str) -> List[str]:
    keywords_map = {
        "fraction": ["fraction", "fractions", "decimal", "ratio", "proportion", "percentage"],
        "algebra": ["algebra", "equation", "expression", "variable"],
        "geometry": ["geometry", "area", "perimeter", "triangle", "rectangle", "square"],
        "verb": ["verb", "verbs", "tense", "tenses", "modal"],
        "pronoun": ["pronoun", "pronouns", "object pronoun"],
        "subject-verb": ["subject-verb", "agreement"],
        "interjection": ["interjection", "interjections"],
        "french": ["french", "conjugation", "reflexive", "article", "demonstrative", "vocabulary"],
    }

    lowered = (query_text or "").lower()
    hits = []
    for _, values in keywords_map.items():
        for value in values:
            if value in lowered:
                hits.append(value)
    return list(dict.fromkeys(hits))

def _build_qa_fallback_answer(student_uid: str, query_text: str) -> str:
    keywords = _extract_query_keywords(query_text)

    db = DatabaseFactory.get_provider()
    conn = db._get_connection()
    cursor = conn.cursor()

    base_query = """
        SELECT question, topic, evaluation_status, created_at
        FROM knowledge_question_attempts
        WHERE uid = %s
    """
    params: List[Any] = [student_uid]

    if keywords:
        like_clauses = []
        for kw in keywords:
            like_clauses.append("topic ILIKE %s")
            like_clauses.append("question ILIKE %s")
            params.extend([f"%{kw}%", f"%{kw}%"])
        base_query += " AND (" + " OR ".join(like_clauses) + ")"

    base_query += " ORDER BY created_at DESC"

    cursor.execute(base_query, tuple(params))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    if not rows:
        return "I couldn't find matching attempts for this question."

    attempts = [
        {
            "question": row[0],
            "topic": row[1],
            "status": row[2],
            "created_at": row[3],
        }
        for row in rows
    ]

    total = len(attempts)
    incorrect = sum(1 for a in attempts if (a.get("status") or "").lower() != "correct")

    missed_groups: Dict[Tuple[str, Optional[str]], Dict[str, Any]] = {}
    for attempt in attempts:
        status = (attempt.get("status") or "").lower()
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
            }
        missed_groups[key]["incorrect_count"] += 1

    top_missed = sorted(
        missed_groups.values(),
        key=lambda item: (-item["incorrect_count"], item["question"])
    )[:5]

    lines = [
        f"Found {incorrect} incorrect out of {total} attempts matching your question.",
    ]
    if top_missed:
        lines.append("Most missed questions:")
        for item in top_missed:
            topic = f" ({item['topic']})" if item.get("topic") else ""
            lines.append(f"- {item['question']}{topic} - missed {item['incorrect_count']}x")

    return "\n".join(lines)

class IntentRouterAgent:
    def __init__(self):
        self.model = None
        if GENAI_AVAILABLE and GEMINI_API_KEY:
            try:
                genai.configure(api_key=GEMINI_API_KEY)
                self.model = genai.GenerativeModel("gemini-2.5-flash")
            except Exception as e:
                logger.warning(f"IntentRouterAgent init failed: {e}")
                self.model = None

    def _heuristic_intent(self, query_text: str, subject: Optional[str] = None, topic: Optional[str] = None) -> str:
        lowered = (query_text or "").lower()
        
        # Strong report indicators - MUST be checked first for exact matches
        report_indicators = [
            "generate report", "full report", "complete report",
            "performance report", "full analysis", "complete analysis",
            "overall performance", "generate analysis"
        ]
        if any(indicator in lowered for indicator in report_indicators):
            return "report"
        
        # Strong QA indicators - specific questions about performance
        qa_indicators = [
            "what", "which", "how many", "how often", "why", "where",
            "questions did i", "type of", "kinds of", "categories",
            "most often", "most common", "frequently", "repeated",
            "got wrong", "missed", "incorrect", "weak", "struggle"
        ]
        if any(indicator in lowered for indicator in qa_indicators):
            return "qa"
        
        # If a specific subject or topic is mentioned, treat as QA
        if subject or topic:
            return "qa"
        
        # Default to QA for most queries
        return "qa"

    def classify_intent(self, query_text: str) -> Dict[str, Optional[str]]:
        cleaned = (query_text or "").strip()
        if not cleaned:
            return {"intent": "report", "subject": None, "topic": None}

        subject, topic = _extract_subject_topic(cleaned)
        intent = self._heuristic_intent(cleaned, subject, topic)

        if self.model:
            prompt = (
                "Classify the user request into one of: report, qa.\n\n"
                "- 'qa' = Specific question about performance (e.g., 'What questions did I get wrong?', "
                "'Which topics do I struggle with?', 'Types of questions I missed most often', "
                "'Show me my weak areas in Math', 'What are my most common mistakes?')\n"
                "- 'report' = Generic request for complete analysis (e.g., 'Generate full report', "
                "'Complete performance analysis', 'Overall performance report')\n\n"
                "Key: If the user asks about SPECIFIC aspects (wrong answers, types, topics, mistakes, weak areas), "
                "classify as 'qa' even if they use words like 'summary' or 'provide'.\n\n"
                "Return only the single word 'report' or 'qa'.\n\n"
                f"User request: {cleaned}"
            )
            try:
                response = self.model.generate_content(prompt)
                text = (response.text or "").strip().lower()
                token = text.split()[0] if text else ""
                if token in ("report", "qa"):
                    intent = token
            except Exception as e:
                logger.warning(f"IntentRouterAgent classify failed: {e}")

        return {"intent": intent, "subject": subject, "topic": topic}

# Agent State Definition
class AgentState(TypedDict):
    """Shared state between agents with retry tracking"""
    student_uid: str
    students_df: pd.DataFrame
    subjects_df: pd.DataFrame
    attempts_df: pd.DataFrame
    performance_df: pd.DataFrame
    graph_context: str
    vector_context: str
    hybrid_context: str
    performance_summary: str
    query_text: str
    intent: str
    subject: Optional[str]
    topic: Optional[str]
    fallback_context: str
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
    guardrails: Dict[str, Any]

def make_initial_state(student_uid: str) -> AgentState:
    return {
        "student_uid": student_uid,
        "students_df": pd.DataFrame(),
        "subjects_df": pd.DataFrame(),
        "attempts_df": pd.DataFrame(),
        "performance_df": pd.DataFrame(),
        "graph_context": "",
        "vector_context": "",
        "hybrid_context": "",
        "performance_summary": "",
        "query_text": "",
        "intent": "",
        "subject": None,
        "topic": None,
        "fallback_context": "",
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
        "trace_id": None,
        "guardrails": {}
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

def _categorize_questions_hierarchical(questions_data: List[Dict[str, Any]], subject_name: str) -> List[Dict[str, Any]]:
    """
    Use AI to categorize questions with full hierarchical taxonomy.
    
    Args:
        questions_data: List of dicts with 'question' and 'id' keys
        subject_name: Name of the subject (e.g., 'Math', 'Science')
    
    Returns:
        List of category dicts with topic, subtopic, concept, difficulty, blooms_level
    """
    if not GENAI_AVAILABLE or not GEMINI_API_KEY:
        logger.warning("Gemini AI not available for question categorization")
        default_cat = {
            "topic": "General",
            "subtopic": "Uncategorized",
            "concept": "General concept",
            "difficulty": 2,
            "blooms_level": "understand"
        }
        return [default_cat] * len(questions_data)
    
    if not questions_data:
        return []
    
    # Normalize subject name to match taxonomy keys
    # Database subjects come in various cases: "Maths", "english", "french", "Sinhala", "IT technology"
    subject_name_normalized = subject_name.strip().title()
    
    # Handle common variations and map database subjects to taxonomy keys (case-insensitive)
    subject_mapping = {
        # Math variations
        "Maths": "Math",
        "Math": "Math",
        "Mathematics": "Math",
        # English
        "English": "English",
        # Science
        "Science": "Science",
        # History
        "History": "History",
        # Geography  
        "Geography": "Geography",
        # Nature
        "Nature": "Nature",
        # Space
        "Space": "Space",
        # Technology and IT variations
        "Technology": "Technology",
        "It Technology": "Technology",  # "IT technology" from DB
        "It": "IT",
        "Information Technology": "IT",
        "Computer": "IT",
        # French
        "French": "French",
        "French-T1": "French",
        # Sinhala
        "Sinhala": "Sinhala",
        # General Knowledge
        "General Knowledge": "General Knowledge",
        "Gk": "General Knowledge"
    }
    subject_key = subject_mapping.get(subject_name_normalized, subject_name_normalized)
    
    # Get taxonomy for this subject
    taxonomy = SUBJECT_TAXONOMY.get(subject_key, {})
    if not taxonomy:
        logger.warning(f"No taxonomy found for subject: {subject_name} (normalized: {subject_key})")
        logger.info(f"Available subjects in taxonomy: {list(SUBJECT_TAXONOMY.keys())}")
        default_cat = {
            "topic": "General",
            "subtopic": "Uncategorized",
            "concept": "General concept",
            "difficulty": 2,
            "blooms_level": "understand"
        }
        return [default_cat] * len(questions_data)
    
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel(DEFAULT_MODEL_NAME)
        
        # Build FULL taxonomy reference with all levels: Topic → SubTopic → Concepts
        taxonomy_lines = []
        for topic, subtopics in taxonomy.items():
            taxonomy_lines.append(f"\n**{topic}**")
            for subtopic, concepts in subtopics.items():
                concepts_str = ", ".join(concepts[:8])  # Show first 8 concepts
                if len(concepts) > 8:
                    concepts_str += f" ... (+{len(concepts) - 8} more)"
                taxonomy_lines.append(f"  • {subtopic}: {concepts_str}")
        taxonomy_str = "\n".join(taxonomy_lines)
        
        # Build questions list
        questions_list = "\n".join([
            f"{i+1}. {q['question'][:200]}..." if len(q.get('question', '')) > 200 else f"{i+1}. {q.get('question', '')}" 
            for i, q in enumerate(questions_data)
        ])
        
        prompt = f"""You are an expert {subject_key} educator categorizing questions using a detailed hierarchical taxonomy.

📚 COMPLETE TAXONOMY FOR {subject_key.upper()}:
{taxonomy_str}

⚠️ CRITICAL RULES:
1. NEVER use generic labels like "General", "Uncategorized", or "General concept"
2. ALWAYS match to the MOST SPECIFIC topic, subtopic, and concept from the taxonomy above
3. If a question doesn't fit perfectly, choose the CLOSEST match
4. Read the question carefully and identify the exact skill/concept being tested

📝 EXAMPLES:
- Question: "What is 12 × 8?" → {{"topic": "Number Operations", "subtopic": "Basic Arithmetic", "concept": "Multiplication tables", "difficulty": 2, "blooms_level": "remember"}}
- Question: "Find the area of a rectangle with length 5cm and width 3cm" → {{"topic": "Geometry", "subtopic": "2D Shapes", "concept": "Area calculations", "difficulty": 3, "blooms_level": "apply"}}
- Question: "Simplify: 3x + 5x" → {{"topic": "Algebra", "subtopic": "Expressions", "concept": "Simplifying expressions", "difficulty": 3, "blooms_level": "apply"}}

BLOOM'S TAXONOMY GUIDE:
- remember: Recall facts, definitions, formulas (e.g., "What is 7+5?", "Define noun")
- understand: Explain concepts, interpret (e.g., "Explain why 1/2 = 0.5")
- apply: Use knowledge to solve problems (e.g., "Calculate the area of...")
- analyze: Break down, identify patterns (e.g., "Which operation should be done first?")
- evaluate: Make judgments, critique (e.g., "Which method is more efficient?")
- create: Design, produce original work (e.g., "Write a word problem for...")

QUESTIONS TO CATEGORIZE:
{questions_list}

🎯 OUTPUT FORMAT - Return ONLY a valid JSON array:
[
  {{
    "topic": "Exact Topic Name from Taxonomy",
    "subtopic": "Exact SubTopic Name from Taxonomy",
    "concept": "Specific concept from list OR similar concept (2-6 words)",
    "difficulty": 2,
    "blooms_level": "apply"
  }},
  ...
]

JSON array:"""
        
        response = model.generate_content(prompt)
        response_text = response.text.strip()
        
        # Extract JSON array from response
        json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
        if json_match:
            categories = json.loads(json_match.group())
            if len(categories) == len(questions_data):
                logger.info(f"✅ Hierarchically categorized {len(categories)} {subject_name} questions")
                return categories
            else:
                logger.warning(f"Category count mismatch: got {len(categories)}, expected {len(questions_data)}")
        
        logger.warning("Failed to parse AI categorization response, using defaults")
        default_cat = {
            "topic": "General",
            "subtopic": "Uncategorized",
            "concept": "General concept",
            "difficulty": 2,
            "blooms_level": "understand"
        }
        return [default_cat] * len(questions_data)
        
    except Exception as e:
        logger.error(f"Error categorizing questions: {e}")
        default_cat = {
            "topic": "General",
            "subtopic": "Uncategorized",
            "concept": "General concept",
            "difficulty": 2,
            "blooms_level": "understand"
        }
        return [default_cat] * len(questions_data)

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

        # Import attempts with embeddings and AI-categorization
        logger.info("  🧠 Generating embeddings and categorizing questions...")

        attempts = state["attempts_df"]
        subjects_df = state["subjects_df"]
        
        # Group attempts by subject for batch categorization
        subject_id_to_name = {str(row["id"]): row.get("name", "Unknown") for _, row in subjects_df.iterrows()}
        attempts_by_subject = {}
        for idx, attempt in attempts.iterrows():
            subject_id = str(attempt.get("subject_id"))
            if subject_id not in attempts_by_subject:
                attempts_by_subject[subject_id] = []
            attempts_by_subject[subject_id].append({
                "index": idx,
                "id": attempt["id"],
                "question": attempt.get("question"),
                "attempt_data": attempt
            })
        
        # Categorize questions by subject in batches with hierarchical taxonomy
        question_categories = {}
        for subject_id, subject_attempts in attempts_by_subject.items():
            subject_name = subject_id_to_name.get(subject_id, "Unknown")
            logger.info(f"  🏷️ Hierarchically categorizing {len(subject_attempts)} {subject_name} questions...")
            
            questions_data = [{"id": a["id"], "question": a["question"]} for a in subject_attempts]
            categories = _categorize_questions_hierarchical(questions_data, subject_name)
            
            for i, attempt_info in enumerate(subject_attempts):
                question_categories[attempt_info["id"]] = categories[i] if i < len(categories) else {
                    "topic": "General",
                    "subtopic": "Uncategorized",
                    "concept": "General concept",
                    "difficulty": 2,
                    "blooms_level": "understand"
                }
        
        # Now import with embeddings and hierarchical categories
        logger.info("  🔗 Creating hierarchical graph structure...")
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
            category_info = question_categories.get(attempt["id"], {
                "topic": "General",
                "subtopic": "Uncategorized",
                "concept": "General concept",
                "difficulty": 2,
                "blooms_level": "understand"
            })
            
            subject_id = str(attempt.get("subject_id"))
            subject_name = subject_id_to_name.get(subject_id, "Unknown")

            # Create hierarchical structure: Subject -> Topic -> SubTopic -> Concept -> Question -> KnowledgeAttempt
            self.run_neo4j_query(
                """
                // Get or create Subject
                MATCH (sub:Subject {id: $subject_id})
                
                // Create or merge Topic under Subject
                MERGE (topic:Topic {name: $topic, subjectId: $subject_id})
                ON CREATE SET topic.subjectName = $subject_name
                MERGE (sub)-[:HAS_TOPIC]->(topic)
                
                // Create or merge SubTopic under Topic
                MERGE (subtopic:SubTopic {name: $subtopic, topicName: $topic, subjectId: $subject_id})
                ON CREATE SET subtopic.subjectName = $subject_name
                MERGE (topic)-[:HAS_SUBTOPIC]->(subtopic)
                
                // Create or merge Concept under SubTopic
                MERGE (concept:Concept {
                    name: $concept,
                    subtopicName: $subtopic,
                    topicName: $topic,
                    subjectId: $subject_id
                })
                ON CREATE SET concept.subjectName = $subject_name
                MERGE (subtopic)-[:HAS_CONCEPT]->(concept)
                
                // Create Question node
                CREATE (q:Question {
                    id: $attempt_id,
                    text: $question,
                    difficulty: $difficulty,
                    bloomsLevel: $blooms_level,
                    subjectId: $subject_id
                })
                
                // Link Question to hierarchy
                MERGE (concept)-[:HAS_QUESTION]->(q)
                MERGE (q)-[:TESTS_CONCEPT]->(concept)
                MERGE (q)-[:TESTS_SUBTOPIC]->(subtopic)
                MERGE (q)-[:TESTS_TOPIC]->(topic)
                
                // Create KnowledgeAttempt (student's answer)
                CREATE (ka:KnowledgeAttempt {
                    id: $attempt_id,
                    question: $question,
                    isCorrect: $is_correct,
                    userAnswer: $user_answer,
                    correctAnswer: $correct_answer,
                    questionType: $old_question_type,
                    topic: $topic,
                    subtopic: $subtopic,
                    concept: $concept,
                    difficulty: $difficulty,
                    bloomsLevel: $blooms_level,
                    embedding: $embedding,
                    embeddingText: $embed_text
                })
                
                // Link attempt to student, subject, and question
                WITH ka, q, sub
                MATCH (s:Student {uid: $uid})
                CREATE (s)-[:ATTEMPTED]->(ka)
                CREATE (ka)-[:BELONGS_TO]->(sub)
                CREATE (ka)-[:ANSWERED]->(q)
                """,
                {
                    "attempt_id": attempt["id"],
                    "question": attempt.get("question"),
                    "is_correct": is_correct,
                    "user_answer": attempt.get("user_answer"),
                    "correct_answer": attempt.get("correct_answer"),
                    "old_question_type": f"{category_info.get('topic', 'General')} - {category_info.get('subtopic', 'Uncategorized')}",
                    "topic": category_info.get("topic", "General"),
                    "subtopic": category_info.get("subtopic", "Uncategorized"),
                    "concept": category_info.get("concept", "General concept"),
                    "difficulty": category_info.get("difficulty", 2),
                    "blooms_level": category_info.get("blooms_level", "understand"),
                    "uid": attempt.get("uid"),
                    "subject_id": subject_id,
                    "subject_name": subject_name,
                    "embedding": embedding,
                    "embed_text": embed_text,
                },
            )

            if (idx + 1) % 50 == 0:
                logger.info(f"    Processed {idx + 1}/{len(attempts)} attempts with hierarchical structure")

        state["messages"].append(
            f"Agent 1: Imported {len(attempts)} attempts with hierarchical categorization to Neo4j"
        )
        logger.info(f"  ✅ Neo4j import complete with hierarchical graph structure and {len(attempts)} embedded nodes")
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
        logger.info(f"🔄 Agent 2: Retrieving hierarchical graph context (attempt {attempt_num}/{MAX_RETRIEVAL_RETRIES + 1})...")
        uid = state["student_uid"]
        subject = state.get("subject")
        topic = state.get("topic")
        
        # Expand topic to include singular/plural variations
        topic_variations = []
        if topic:
            topic_lower = topic.lower()
            # Create variations: singular, plural, and the original
            variations = [topic_lower]
            # Add plural form (simple s-addition)
            if not topic_lower.endswith('s'):
                variations.append(topic_lower + 's')
            else:
                # Remove trailing 's' for singular form
                variations.append(topic_lower.rstrip('s'))
            topic_variations = variations

        # Get subject-level performance
        # Navigate through relationships: Student -> KnowledgeAttempt -> Question -> Topic
        subject_result = self.run_neo4j_query(
            """
            MATCH (s:Student {uid: $uid})-[:ATTEMPTED]->(ka:KnowledgeAttempt)-[:BELONGS_TO]->(sub:Subject)
            OPTIONAL MATCH (ka)-[:ANSWERED]->(q:Question)-[:TESTS_TOPIC]->(t:Topic)
            WHERE ($subject IS NULL OR toLower(sub.name) = toLower($subject))
              AND (size($topicVariations) = 0 OR 
                   ANY(variant IN $topicVariations WHERE 
                       toLower(t.name) CONTAINS variant))
            RETURN sub.name AS subject,
                   count(CASE WHEN ka.isCorrect = true THEN 1 END) AS correct,
                   count(CASE WHEN ka.isCorrect = false THEN 1 END) AS incorrect
            ORDER BY incorrect DESC
            """,
            {"uid": uid, "subject": subject, "topicVariations": topic_variations},
        )

        performance_data = []
        for record in subject_result:
            performance_data.append({
                "subject": record["subject"],
                "correct": record["correct"],
                "incorrect": record["incorrect"],
                "total": record["correct"] + record["incorrect"],
                "accuracy": (record["correct"] / (record["correct"] + record["incorrect"]) * 100) if (record["correct"] + record["incorrect"]) > 0 else 0
            })
        performance_df = pd.DataFrame(performance_data)
        state["performance_df"] = performance_df
        state["performance_summary"] = performance_df.to_string(index=False)
        
        # Get hierarchical breakdown: Topic -> SubTopic -> Concept
        # Note: topic, subtopic, concept are properties on KnowledgeAttempt node (set during data ingestion)
        hierarchical_result = self.run_neo4j_query(
            """
            MATCH (s:Student {uid: $uid})-[:ATTEMPTED]->(ka:KnowledgeAttempt)-[:BELONGS_TO]->(sub:Subject)
            WHERE ($subject IS NULL OR toLower(sub.name) = toLower($subject))
              AND ka.topic IS NOT NULL
              AND (size($topicVariations) = 0 OR 
                   ANY(variant IN $topicVariations WHERE 
                       toLower(ka.topic) CONTAINS variant))
            WITH sub.name AS subject, ka.topic AS topic, ka.subtopic AS subtopic, ka.concept AS concept,
                 ka.difficulty AS difficulty, ka.bloomsLevel AS bloomsLevel,
                 count(CASE WHEN ka.isCorrect = false THEN 1 END) AS incorrect_count,
                 count(CASE WHEN ka.isCorrect = true THEN 1 END) AS correct_count
            WHERE incorrect_count > 0 OR correct_count > 0
            RETURN subject, topic, subtopic, concept, difficulty, bloomsLevel,
                   correct_count AS correct,
                   incorrect_count AS incorrect,
                   (correct_count + incorrect_count) AS total,
                   CASE WHEN (correct_count + incorrect_count) > 0
                        THEN toFloat(correct_count) / (correct_count + incorrect_count) * 100
                        ELSE 0 END AS accuracy
            ORDER BY subject, incorrect DESC, total DESC
            LIMIT 20
            """,
            {"uid": uid, "subject": subject, "topicVariations": topic_variations},
        )
        
        # Build hierarchical context
        hierarchical_lines = ["\n**Hierarchical Performance Breakdown:**"]
        current_subject = None
        current_topic = None
        
        for record in hierarchical_result:
            subj = record["subject"]
            top = record["topic"]
            subtop = record["subtopic"]
            conc = record["concept"]
            diff = record.get("difficulty", "N/A")
            blooms = record.get("bloomsLevel", "N/A")
            correct = record["correct"]
            incorrect = record["incorrect"]
            total = record["total"]
            accuracy = record["accuracy"]
            
            if subj != current_subject:
                if current_subject is not None:
                    hierarchical_lines.append("")
                hierarchical_lines.append(f"\n📚 {subj}:")
                current_subject = subj
                current_topic = None
            
            if top != current_topic:
                hierarchical_lines.append(f"  📖 {top}:")
                current_topic = top
            
            hierarchical_lines.append(
                f"    • {subtop} → {conc}: {incorrect}/{total} wrong ({accuracy:.1f}% accuracy) "
                f"[Difficulty: {diff}, Bloom's: {blooms}]"
            )
        
        hierarchical_text = "\n".join(hierarchical_lines) if hierarchical_result else ""
        
        filter_note = ""
        if subject or topic_variations:
            topic_display = f"{topic} (variants: {', '.join(topic_variations)})" if topic_variations else "any"
            filter_note = f" (filtered by subject={subject or 'any'}, topic={topic_display})"
        
        state["graph_context"] = f"""Graph-based performance analysis{filter_note}:
{state['performance_summary']}
{hierarchical_text}""".strip()
        
        state["messages"].append(f"Agent 2: Retrieved hierarchical graph context (attempt {attempt_num})")
        logger.info(f"  ✅ Retrieved performance for {len(performance_data)} subjects with {len(hierarchical_result)} hierarchical insights")
        return state

    def retrieve_question_type_breakdown(self, state: AgentState) -> str:
        """Retrieve hierarchical breakdown by Topic -> SubTopic -> Concept."""
        uid = state["student_uid"]
        subject = state.get("subject")
        topic = state.get("topic")
        
        # Expand topic to include singular/plural variations
        topic_variations = []
        if topic:
            topic_lower = topic.lower()
            variations = [topic_lower]
            if not topic_lower.endswith('s'):
                variations.append(topic_lower + 's')
            else:
                variations.append(topic_lower.rstrip('s'))
            topic_variations = variations
        
        logger.info(f"  🏷️ Retrieving hierarchical concept breakdown for subject={subject}...")
        
        # Query to get hierarchical concept statistics with difficulty and Bloom's level
        result = self.run_neo4j_query(
            """
            MATCH (s:Student {uid: $uid})-[:ATTEMPTED]->(ka:KnowledgeAttempt)-[:BELONGS_TO]->(sub:Subject)
            WHERE ($subject IS NULL OR toLower(sub.name) = toLower($subject))
              AND (size($topicVariations) = 0 OR 
                   ANY(variant IN $topicVariations WHERE 
                       toLower(ka.topic) CONTAINS variant))
              AND ka.topic IS NOT NULL
            WITH sub.name AS subject, ka.topic AS topic, ka.subtopic AS subtopic, 
                 ka.concept AS concept, ka.difficulty AS difficulty, ka.bloomsLevel AS bloomsLevel,
                 count(CASE WHEN ka.isCorrect = false THEN 1 END) AS incorrect_count,
                 count(CASE WHEN ka.isCorrect = true THEN 1 END) AS correct_count
            WHERE incorrect_count > 0 OR correct_count > 0
            RETURN subject, topic, subtopic, concept, difficulty, bloomsLevel,
                   correct_count AS correct,
                   incorrect_count AS incorrect,
                   (correct_count + incorrect_count) AS total,
                   CASE WHEN (correct_count + incorrect_count) > 0
                        THEN toFloat(correct_count) / (correct_count + incorrect_count) * 100
                        ELSE 0 END AS accuracy
            ORDER BY subject, topic, incorrect DESC, total DESC
            """,
            {"uid": uid, "subject": subject, "topicVariations": topic_variations},
        )
        
        if not result:
            return ""
        
        # Build hierarchical breakdown text
        breakdown_lines = ["\n**📊 Hierarchical Concept Analysis:**"]
        current_subject = None
        current_topic = None
        
        for record in result:
            subj = record["subject"]
            top = record["topic"]
            subtop = record["subtopic"]
            conc = record["concept"]
            diff = record.get("difficulty", "?")
            blooms = record.get("bloomsLevel", "?")
            correct = record["correct"]
            incorrect = record["incorrect"]
            total = record["total"]
            accuracy = record["accuracy"]
            
            if subj != current_subject:
                if current_subject is not None:
                    breakdown_lines.append("")  # Empty line between subjects
                breakdown_lines.append(f"\n📚 **{subj}:**")
                current_subject = subj
                current_topic = None
            
            if top != current_topic:
                breakdown_lines.append(f"\n  📖 {top}:")
                current_topic = top
            
            # Show SubTopic -> Concept with detailed stats
            bloom_emoji = {
                "remember": "🧠", "understand": "💡", "apply": "🔧",
                "analyze": "🔬", "evaluate": "⚖️", "create": "🎨"
            }.get(blooms, "📝")
            
            diff_stars = "⭐" * int(diff) if isinstance(diff, (int, float)) and 1 <= diff <= 5 else "⭐" * 2
            
            breakdown_lines.append(
                f"    • **{subtop}** → {conc}\n"
                f"      ❌ {incorrect}/{total} wrong ({accuracy:.1f}% accuracy) | "
                f"Difficulty: {diff_stars} | Bloom's: {bloom_emoji} {blooms}"
            )
        
        breakdown_text = "\n".join(breakdown_lines)
        logger.info(f"  ✅ Retrieved hierarchical breakdown for {len(result)} concepts across topics")
        return breakdown_text

    def retrieve_vector_context(self, state: AgentState) -> AgentState:
        attempt_num = state["retrieval_attempt"] + 1
        logger.info(f"🔄 Agent 2: Performing vector similarity search (attempt {attempt_num}/{MAX_RETRIEVAL_RETRIES + 1})...")
        uid = state["student_uid"]
        subject = state.get("subject")
        topic = state.get("topic")

        query_override = (state.get("query_text") or "").strip()
        if query_override:
            query_text = query_override[:200]
        else:
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
            CALL db.index.vector.queryNodes('attempt_embeddings', 10, $query_embedding)
            YIELD node, score
            MATCH (node)-[:BELONGS_TO]->(sub:Subject)
            WHERE node.uid = $uid
              AND ($subject IS NULL OR toLower(sub.name) = toLower($subject))
              AND ($topic IS NULL OR toLower(node.topic) CONTAINS toLower($topic) OR toLower(node.question) CONTAINS toLower($topic))
            RETURN node.question AS question, node.isCorrect AS isCorrect,
                   node.userAnswer AS userAnswer, node.correctAnswer AS correctAnswer,
                   node.topic AS topic, node.subtopic AS subtopic, node.concept AS concept,
                   node.difficulty AS difficulty, node.bloomsLevel AS bloomsLevel,
                   sub.name AS subject, score
            ORDER BY score DESC LIMIT 8
            """,
            {"query_embedding": query_embedding, "uid": uid, "subject": subject, "topic": topic},
        )

        vector_context = []
        for record in result:
            vector_context.append({
                "question": record["question"],
                "is_correct": record["isCorrect"],
                "user_answer": record["userAnswer"],
                "correct_answer": record["correctAnswer"],
                "topic": record.get("topic", "N/A"),
                "subtopic": record.get("subtopic", "N/A"),
                "concept": record.get("concept", "N/A"),
                "difficulty": record.get("difficulty", "?"),
                "blooms_level": record.get("bloomsLevel", "?"),
                "subject": record.get("subject", "N/A"),
                "similarity_score": record["score"]
            })

        state["vector_context"] = "\n".join([
            f"- **{item['subject']}** → {item['topic']} → {item['subtopic']} → {item['concept']}\n"
            f"  Q: {item['question'][:100]}...\n"
            f"  Student: {item['user_answer']} | Correct: {item['correct_answer']} | "
            f"Difficulty: {'⭐' * int(item['difficulty']) if isinstance(item['difficulty'], (int, float)) and 1 <= item['difficulty'] <= 5 else '⭐⭐'} | "
            f"Bloom's: {item['blooms_level']} | Similarity: {item['similarity_score']:.3f}"
            for item in vector_context
        ])
        state["messages"].append(f"Agent 2: Retrieved vector context (attempt {attempt_num})")

        logger.info(f"  ✅ Retrieved {len(vector_context)} similar attempts")
        return state

    def retrieve_hybrid_context(self, state: AgentState) -> AgentState:
        attempt_num = state["retrieval_attempt"] + 1
        logger.info(f"🔄 Agent 2: Performing hybrid context retrieval (attempt {attempt_num}/{MAX_RETRIEVAL_RETRIES + 1})...")

        fallback_block = ""
        if state.get("intent") == "qa" and state.get("fallback_context"):
            fallback_block = f"\n**Fallback Summary:**\n{state['fallback_context']}\n"
        
        # Get question type breakdown (additional hierarchical analysis)
        question_type_breakdown = self.retrieve_question_type_breakdown(state)

        # Combine all contexts without duplicating graph_context
        # graph_context already contains performance summary and hierarchical breakdown
        context_parts = [state['graph_context']]
        
        # Add question type breakdown only if it provides additional insights
        if question_type_breakdown and question_type_breakdown.strip():
            context_parts.append(question_type_breakdown)
        
        # Add vector context if available
        vector_ctx = state.get('vector_context', '').strip()
        if vector_ctx:
            context_parts.append(f"\n**Vector Similarity Analysis:**\n{vector_ctx}")
        
        # Add fallback context if available (for Q&A only)
        if fallback_block:
            context_parts.append(fallback_block)
        
        state["hybrid_context"] = "\n\n".join(context_parts).strip()

        state["messages"].append(f"Agent 2: Combined hybrid context (attempt {attempt_num})")
        logger.info("  ✅ Combined hybrid context with question type analysis")
        return state

    @maybe_traceable
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
You are an expert educational analyst. Analyze this student's performance using the hierarchical data structure.

Student Performance Data (Hierarchical):
{state['hybrid_context']}

Evidence Quality Score: {state['evidence_quality_score']:.2f}
Retrieval Attempts: {state['retrieval_attempt']}

The data includes hierarchical categorization:
- **Topics**: Major subject areas (e.g., "Geometry", "Grammar", "Forces & Motion")
- **SubTopics**: Specific areas within topics (e.g., "2D Shapes", "Tenses", "Friction")
- **Concepts**: Atomic skills being tested (e.g., "Area calculations", "Simple present tense", "Gravity")
- **Difficulty**: 1-5 scale (⭐ to ⭐⭐⭐⭐⭐)
- **Bloom's Level**: Cognitive complexity (remember, understand, apply, analyze, evaluate, create)

Please provide a detailed analysis including:

1. **Overall Performance Summary**
   - Highlight subjects with strongest/weakest performance

2. **Hierarchical Weakness Analysis**
   - Identify weak **Topics** (e.g., "Fractions & Decimals")
   - Drill down to problematic **SubTopics** (e.g., "Fractions operations")
   - Pinpoint specific **Concepts** needing practice (e.g., "Dividing fractions")

3. **Difficulty & Cognitive Level Patterns**
   - What difficulty levels (⭐-⭐⭐⭐⭐⭐) have most errors?
   - Which Bloom's levels (remember/understand/apply/analyze/evaluate/create) are challenging?

4. **Learning Patterns & Common Mistakes**
   - Identify recurring error patterns
   - Note if mistakes are in higher-order thinking (analyze/evaluate) vs basic recall

5. **Targeted Recommendations**
   - Prioritize specific concepts to practice (most granular level)
   - Suggest progression: master foundational concepts before advancing
   - Recommend difficulty progression strategy

6. **Study Strategies**
   - Tailor strategies based on Bloom's levels where student struggles
   - Suggest concept-specific practice approaches

Format in clear, engaging markdown with emojis, sections, and bullet points.
Keep it encouraging, specific, and actionable for a student.
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

    @maybe_traceable
    def generate_answer(self, state: AgentState) -> AgentState:
        logger.info("🔄 Agent 3: Generating performance Q&A response...")

        if not self.model:
            state["analysis_report"] = (
                "AI service unavailable. Please try again later."
            )
            state["messages"].append("Agent 3: AI model not available for Q&A")
            return state

        if not state.get("evidence_sufficient", False):
            state["analysis_report"] = (
                "Insufficient evidence to answer this question. "
                "Please ask about areas with more attempts."
            )
            state["messages"].append("Agent 3: Q&A insufficient evidence")
            return state

        question = state.get("query_text", "").strip()
        subject = state.get("subject") or "all subjects"
        topic = state.get("topic") or "all topics"
        context = state.get("hybrid_context") or state.get("performance_summary", "")
        prompt = (
            "You are an academic tutor analyzing student performance using hierarchical categorization.\n\n"
            "The data includes:\n"
            "- **Topics**: Major subject areas\n"
            "- **SubTopics**: Specific areas within topics\n"
            "- **Concepts**: Atomic skills being tested\n"
            "- **Difficulty**: 1-5 scale (⭐ to ⭐⭐⭐⭐⭐)\n"
            "- **Bloom's Level**: remember/understand/apply/analyze/evaluate/create\n\n"
            f"User question:\n{question}\n\n"
            f"Scope:\nSubject: {subject}\nTopic: {topic}\n\n"
            "Context:\n"
            f"{context}\n\n"
            "Answer requirements:\n"
            "1) Use the hierarchical structure to identify specific weak concepts (Topic → SubTopic → Concept)\n"
            "2) If available, reference difficulty levels and Bloom's levels in your analysis\n"
            "3) Provide specific accuracy for topics/subtopics/concepts (if available)\n"
            "4) Include concrete examples of missed questions when available\n"
            "5) Give targeted improvement tips: practice specific concepts at appropriate difficulty\n"
            "6) If user asks about 'types' of questions, interpret this as the hierarchical breakdown\n\n"
            "Keep it concise, data-driven, specific to the question, and avoid mentioning unrelated subjects."
        )

        try:
            response = self.model.generate_content(prompt)
            generated = (response.text or "").strip()
            if not generated:
                generated = (
                    "I couldn't find a specific answer in the context. "
                    "Here is a summary of the available performance data:\n\n"
                    f"{state.get('performance_summary', '').strip()}"
                ).strip()
                state["messages"].append("Agent 3: Empty Q&A response, used summary fallback")
            state["analysis_report"] = generated
            state["model_used"] = "gemini-2.5-flash"
            state["messages"].append("Agent 3: Generated Q&A response")
            logger.info("  ✅ Q&A response generated successfully")
        except Exception as e:
            logger.error(f"  ❌ Q&A analysis failed: {e}")
            state["analysis_report"] = (
                "Unable to answer the question due to an analysis error."
            )
            state["model_used"] = "error-fallback"
            state["messages"].append(f"Agent 3: Q&A analysis failed: {str(e)}")

        return state

# Main Service Class
class PerformanceReportService:
    """Main service class for generating student performance reports."""

    def __init__(self):
        self.app = None
        self.data_agent = None
        self.langsmith_client = None
        self.intent_router = IntentRouterAgent()
        self.cache_last_invalidation = None
        self.cache_ttl_hours = 24

        # Initialize LangSmith client if available
        if LANGSMITH_AVAILABLE and LANGSMITH_API_KEY and LANGSMITH_TRACING:
            try:
                self.langsmith_client = LangSmithClient(
                    api_key=LANGSMITH_API_KEY
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
            def _safe_load(val, default=None):
                if val is None:
                    return default
                # If DB driver already returned parsed JSON (dict/list), return as-is
                if isinstance(val, (dict, list)):
                    return val
                # If it's bytes, decode
                if isinstance(val, (bytes, bytearray)):
                    try:
                        val = val.decode('utf-8')
                    except Exception:
                        return default
                # Finally try to parse JSON string
                try:
                    return json.loads(val)
                except Exception:
                    return default

            for row in cursor.fetchall():
                reports.append({
                    'id': row[0],
                    'report_content': row[1],
                    'report_format': row[2],
                    'agent_statuses': _safe_load(row[3], {}),
                    'execution_log': _safe_load(row[4], []),
                    'trace_id': row[5],
                    'evidence_sufficient': row[6],
                    'evidence_quality_score': row[7],
                    'retrieval_attempts': row[8],
                    'errors': _safe_load(row[9], []),
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

    def _initialize_agents(self):
        data_agent = DataIngesterAgent()
        data_agent.connect()
        retriever_agent = RetrieverAgent(data_agent.neo4j_driver, data_agent.embedding_model)
        analyst_agent = AnalystAgent()
        return data_agent, retriever_agent, analyst_agent

    @maybe_traceable
    def _run_retrieval_loop(self, state: AgentState, retriever_agent: RetrieverAgent) -> AgentState:
        while True:
            state = retriever_agent.perform_retrieval(state)
            if state.get("evidence_sufficient") or state.get("retrieval_attempt", 0) >= MAX_RETRIEVAL_RETRIES:
                break
        return state

    def handle_performance_request(
        self,
        student_uid: str,
        query_text: Optional[str] = None,
        intent: Optional[str] = None,
        admin_key: Optional[str] = None
    ) -> dict:
        subject = None
        topic = None
        intent_payload = intent or self.intent_router.classify_intent(query_text or "")
        if isinstance(intent_payload, dict):
            resolved_intent = intent_payload.get("intent") or "qa"
            subject = intent_payload.get("subject")
            topic = intent_payload.get("topic")
        else:
            resolved_intent = intent_payload

        if resolved_intent == "report":
            result = self.generate_performance_report(student_uid, admin_key)
        else:
            result = self.generate_performance_answer(
                student_uid,
                query_text or "",
                admin_key,
                subject=subject,
                topic=topic
            )
        if isinstance(result, dict):
            result.setdefault("intent", resolved_intent)
            result.setdefault("subject", subject)
            result.setdefault("topic", topic)
        return result

    def generate_performance_answer(
        self,
        student_uid: str,
        query_text: str,
        admin_key: str = None,
        subject: Optional[str] = None,
        topic: Optional[str] = None
    ) -> dict:
        start_time = datetime.now()
        state = make_initial_state(student_uid)
        state["query_text"] = query_text or ""
        state["intent"] = "qa"
        state["subject"] = subject
        state["topic"] = topic

        cleaned_query, guardrails, blocked, block_reason = _apply_input_guardrails(query_text or "")
        state["query_text"] = cleaned_query
        state["guardrails"] = guardrails
        if not state.get("subject") and not state.get("topic"):
            inferred_subject, inferred_topic = _extract_subject_topic(cleaned_query)
            state["subject"] = inferred_subject
            state["topic"] = inferred_topic

        if blocked:
            response = {
                "success": True,
                "student_uid": student_uid,
                "intent": "qa",
                "subject": subject,
                "topic": topic,
                "query": cleaned_query,
                "answer": "Request blocked by safety guardrails.",
                "message": f"Blocked: {block_reason}",
                "agents_executed": ["IntentRouter", "InputGuardrails"],
                "execution_path": "guardrail_blocked",
                "is_fallback": False,
                "response_source": "safety_guardrails",
                "guardrails": guardrails,
                "timestamp": datetime.now().isoformat()
            }
            report_body = (
                "## Performance Q&A\n\n"
                f"**Question:** {cleaned_query}\n\n"
                "**Answer:** Request blocked by safety guardrails.\n"
            )
            response["analysis_report"] = report_body
            self.save_performance_report(student_uid, {
                "analysis_report": report_body,
                "report_format": "qa",
                "agent_statuses": {},
                "execution_log": [],
                "trace_id": None,
                "evidence_sufficient": False,
                "evidence_quality_score": 0.0,
                "retrieval_attempts": 0,
                "errors": [],
                "success": True,
                "processing_time_ms": 0,
                "model_used": ""
            })
            return response

        try:
            fallback_text = _build_qa_fallback_answer(student_uid, cleaned_query)
            missed_questions = _extract_fallback_missed_questions(fallback_text)
            if missed_questions:
                state["fallback_context"] = "Most missed questions:\n" + "\n".join(
                    f"- {q}" for q in missed_questions
                )
            else:
                state["fallback_context"] = fallback_text
        except Exception as e:
            logger.warning(f"Failed to build fallback context: {e}")
            state["fallback_context"] = ""

        data_agent = None
        trace_id = None
        try:
            # Skip data ingestion for Q&A queries - use existing Neo4j data
            # Data is already in Neo4j from previous report generations or manual imports
            skip_data_ingester = True
            
            if skip_data_ingester:
                logger.info("ℹ️ Q&A: Skipping DataIngesterAgent - using existing Neo4j data")
                # Initialize agents without data ingestion
                data_agent = DataIngesterAgent()
                data_agent.connect()  # Connect but don't extract/import
                retriever_agent = RetrieverAgent(data_agent.neo4j_driver, data_agent.embedding_model)
                analyst_agent = AnalystAgent()
            else:
                # Full initialization with data ingestion (legacy path)
                data_agent, retriever_agent, analyst_agent = self._initialize_agents()
            
            state["agent_statuses"] = {}
            state["workflow_progress"] = []
            state["errors"] = []
            state["model_used"] = "gemini-2.5-flash"

            # Set LangSmith environment context for Q&A tracing
            import os
            trace_id = f"qa_{student_uid}_{int(start_time.timestamp())}"
            if LANGSMITH_TRACING and LANGSMITH_API_KEY:
                os.environ["LANGCHAIN_TRACING_V2"] = "true"
                os.environ["LANGCHAIN_API_KEY"] = LANGSMITH_API_KEY
                os.environ["LANGCHAIN_PROJECT"] = LANGSMITH_PROJECT
                logger.info(f"🔍 Q&A tracing enabled for {trace_id}")

            # Execute Q&A workflow
            try:
                state = self._run_retrieval_loop(state, retriever_agent)
                state = analyst_agent.generate_answer(state)
                if LANGSMITH_TRACING:
                    logger.info(f"✅ Q&A traced to LangSmith: {trace_id}")
            except Exception as e:
                logger.error(f"❌ Q&A execution failed: {e}")
                raise

            answer_text, output_guardrails = _apply_output_guardrails(state.get("analysis_report", ""))
            state["analysis_report"] = answer_text
            state["guardrails"]["output"] = output_guardrails

            if not answer_text:
                answer_text = (
                    "I couldn't generate an answer from the current context. "
                    "Please try rephrasing your question."
                )
            if (
                state.get("evidence_sufficient")
                and answer_text.strip().lower() == "insufficient evidence to answer."
            ):
                answer_text = _build_qa_fallback_answer(student_uid, cleaned_query)

            end_time = datetime.now()
            processing_time_ms = int((end_time - start_time).total_seconds() * 1000)

            # Track which agents were actually executed
            agents_executed = ["IntentRouter", "InputGuardrails"]
            if not skip_data_ingester:
                agents_executed.append("DataIngester")
            agents_executed.extend(["Retriever", "Analyst", "OutputGuardrails"])
            
            is_ai_generated = state.get("model_used") not in ["", "error-fallback"]
            used_fallback = bool(state.get("fallback_context"))
            
            response = {
                "success": True,
                "student_uid": student_uid,
                "intent": "qa",
                "subject": subject,
                "topic": topic,
                "query": cleaned_query,
                "answer": answer_text,
                "message": "Performance query answered successfully.",
                "evidence_sufficient": state.get("evidence_sufficient", False),
                "evidence_quality_score": state.get("evidence_quality_score", 0.0),
                "retrieval_attempts": state.get("retrieval_attempt", 0),
                "execution_log": state.get("messages", []),
                "agents_executed": agents_executed,
                "execution_path": "qa_workflow_skip_ingestion" if skip_data_ingester else "qa_workflow",
                "is_fallback": used_fallback and not is_ai_generated,
                "response_source": "ai_generated" if is_ai_generated else ("database_fallback" if used_fallback else "database_only"),
                "guardrails": state.get("guardrails", {}),
                "processing_time_ms": processing_time_ms,
                "model_used": state.get("model_used", ""),
                "model_configured": DEFAULT_MODEL_NAME,
                "api_key_used": _get_api_key_hint(),
                "trace_id": trace_id,
                "timestamp": end_time.isoformat()
            }
            report_body = (
                "## Performance Q&A\n\n"
                f"**Question:** {cleaned_query}\n\n"
                f"**Answer:** {answer_text}\n"
            )
            response["analysis_report"] = report_body
            self.save_performance_report(student_uid, {
                "analysis_report": report_body,
                "report_format": "qa",
                "agent_statuses": state.get("agent_statuses", {}),
                "execution_log": state.get("messages", []),
                "trace_id": trace_id,
                "evidence_sufficient": state.get("evidence_sufficient", False),
                "evidence_quality_score": state.get("evidence_quality_score", 0.0),
                "retrieval_attempts": state.get("retrieval_attempt", 0),
                "errors": state.get("errors", []),
                "success": True,
                "processing_time_ms": processing_time_ms,
                "model_used": state.get("model_used", "")
            })
            return response
        except Exception as e:
            logger.error(f"Error generating performance answer: {e}")
            agents_executed = ["IntentRouter", "InputGuardrails"]
            if data_agent:
                agents_executed.append("DataIngester")
            return {
                "success": False,
                "student_uid": student_uid,
                "intent": "qa",
                "subject": subject,
                "topic": topic,
                "query": cleaned_query,
                "error": str(e),
                "message": "Failed to answer performance query.",
                "agents_executed": agents_executed,
                "execution_path": "qa_workflow_error",
                "is_fallback": False,
                "response_source": "error",
                "guardrails": state.get("guardrails", {}),
                "model_used": state.get("model_used", ""),
                "model_configured": DEFAULT_MODEL_NAME,
                "api_key_used": _get_api_key_hint(),
                "timestamp": datetime.now().isoformat()
            }
        finally:
            if data_agent:
                data_agent.close()

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
        state = make_initial_state(student_uid)

        try:
            # Check cooldown first
            cooldown_check = self.check_cooldown(student_uid, admin_key)
            if not cooldown_check.get('can_generate', False):
                return {
                    "success": False,
                    "student_uid": student_uid,
                    "intent": "report",
                    "subject": None,
                    "topic": None,
                    "error": cooldown_check.get('error', 'cooldown_active'),
                    "cooldown_remaining": cooldown_check.get('cooldown_remaining', 0),
                    "cooldown_end": cooldown_check.get('cooldown_end'),
                    "agents_executed": ["CooldownChecker"],
                    "execution_path": "cooldown_blocked",
                    "is_fallback": False,
                    "response_source": "cooldown_limit",
                    "model_used": "",
                    "model_configured": DEFAULT_MODEL_NAME,
                    "model_invoked": False,
                    "api_key_used": _get_api_key_hint(),
                    "timestamp": datetime.now().isoformat()
                }

            # Initialize workflow (but may skip later if running only analyst)
            app, data_agent = self.initialize_workflow()

            # Create initial state
            state = make_initial_state(student_uid)
            # Allow skipping DataIngesterAgent to avoid expensive Neo4j reimport
            # Use admin_key='skip_data_ingester' to use existing Neo4j data
            skip_data_ingester = False
            if isinstance(admin_key, str) and admin_key.strip().lower() == 'skip_data_ingester':
                skip_data_ingester = True
            
            state["agent_statuses"] = {}
            state["workflow_progress"] = []
            state["errors"] = []
            state["processing_time_ms"] = 0
            state["model_used"] = "gemini-2.5-flash"

            logger.info(f"\n🚀 Starting Performance Analysis for student {student_uid}...\n")

            # If skip_data_ingester is enabled, run Retriever + Analyst using existing Neo4j data
            if skip_data_ingester:
                logger.info("ℹ️ Skipping DataIngesterAgent - using existing Neo4j data")
                logger.info("🔄 Running Retriever + Analyst workflow...")
                
                try:
                    # Initialize agents (without data ingestion)
                    data_agent = DataIngesterAgent()
                    data_agent.connect()  # Connect but don't extract/import
                    retriever_agent = RetrieverAgent(data_agent.neo4j_driver, data_agent.embedding_model)
                    analyst_agent = AnalystAgent()
                    
                    # Run retrieval loop
                    state = self._run_retrieval_loop(state, retriever_agent)
                    
                    # Generate report
                    state = analyst_agent.generate_report(state)
                    
                    # Build response
                    end_time = datetime.now()
                    processing_time_ms = int((end_time - start_time).total_seconds() * 1000)
                    
                    response = {
                        'success': True,
                        'student_uid': student_uid,
                        'intent': 'report',
                        'subject': None,
                        'topic': None,
                        'analysis_report': state.get('analysis_report', ''),
                        'evidence_sufficient': state.get('evidence_sufficient', False),
                        'evidence_quality_score': state.get('evidence_quality_score', 0.0),
                        'retrieval_attempts': state.get('retrieval_attempt', 0),
                        'execution_log': state.get('messages', []),
                        'agents_executed': ['CooldownChecker', 'Retriever', 'Analyst'],
                        'execution_path': 'report_workflow_skip_ingestion',
                        'is_fallback': False,
                        'response_source': 'ai_generated' if state.get('model_used') else 'basic_analysis',
                        'agent_statuses': state.get('agent_statuses', {}),
                        'workflow_progress': state.get('workflow_progress', []),
                        'errors': state.get('errors', []),
                        'processing_time_ms': processing_time_ms,
                        'model_used': state.get('model_used', ''),
                        'model_configured': DEFAULT_MODEL_NAME,
                        'api_key_used': _get_api_key_hint(),
                        'trace_id': state.get('trace_id'),
                        'timestamp': end_time.isoformat()
                    }

                    # Save report
                    if response['success']:
                        save_success = self.save_performance_report(student_uid, response)
                        if not save_success:
                            logger.warning('Failed to save performance report to database')

                    # Cleanup
                    data_agent.close()
                    
                    return response
                    
                except Exception as e:
                    logger.error(f"Error in skip_data_ingester workflow: {e}")
                    end_time = datetime.now()
                    processing_time_ms = int((end_time - start_time).total_seconds() * 1000)
                    return {
                        'success': False,
                        'student_uid': student_uid,
                        'intent': 'report',
                        'subject': None,
                        'topic': None,
                        'error': str(e),
                        'agents_executed': ['CooldownChecker'],
                        'execution_path': 'report_workflow_skip_ingestion_error',
                        'is_fallback': False,
                        'response_source': 'error',
                        'processing_time_ms': processing_time_ms,
                        'model_used': '',
                        'model_configured': DEFAULT_MODEL_NAME,
                        'api_key_used': _get_api_key_hint(),
                        'timestamp': end_time.isoformat()
                    }

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

            # Determine agents executed
            agents_executed = ["CooldownChecker", "DataIngester", "Retriever", "Analyst"]
            
            # Prepare response
            response = {
                "success": workflow_result["success"],
                "student_uid": student_uid,
                "intent": "report",
                "subject": None,
                "topic": None,
                "analysis_report": workflow_result["analysis_report"],
                "evidence_sufficient": workflow_result["evidence_sufficient"],
                "evidence_quality_score": workflow_result["evidence_quality_score"],
                "retrieval_attempts": workflow_result["retrieval_attempts"],
                "execution_log": workflow_result["execution_log"],
                "agents_executed": agents_executed,
                "execution_path": "report_workflow",
                "is_fallback": False,
                "response_source": "ai_generated" if workflow_result.get("model_used") else "basic_analysis",
                "agent_statuses": workflow_result.get("agent_statuses", state.get("agent_statuses", {})),
                "workflow_progress": workflow_result.get("workflow_progress", state.get("workflow_progress", [])),
                "errors": state.get("errors", []),
                "processing_time_ms": processing_time_ms,
                "model_used": workflow_result.get("model_used", state.get("model_used", "")),
                "model_configured": DEFAULT_MODEL_NAME,
                "api_key_used": _get_api_key_hint(),
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

            # Determine which agents executed before error
            agents_executed = ["CooldownChecker"]
            if state.get("messages"):
                if any("Agent 1" in msg for msg in state["messages"]):
                    agents_executed.append("DataIngester")
                if any("Agent 2" in msg for msg in state["messages"]):
                    agents_executed.append("Retriever")
                if any("Agent 3" in msg for msg in state["messages"]):
                    agents_executed.append("Analyst")

            error_details = {
                "message": str(e),
                "code": "report_generation_failed",
                "stack_snippet": str(e)[:200]  # Limited stack trace
            }

            logger.error(f"Error generating performance report: {str(e)}")
            return {
                "success": False,
                "student_uid": student_uid,
                "intent": "report",
                "subject": None,
                "topic": None,
                "error": str(e),
                "errors": [error_details],
                "agents_executed": agents_executed,
                "execution_path": "report_workflow_error",
                "is_fallback": False,
                "response_source": "error",
                "processing_time_ms": processing_time_ms,
                "model_used": state.get("model_used", ""),
                "model_configured": DEFAULT_MODEL_NAME,
                "api_key_used": _get_api_key_hint(),
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
