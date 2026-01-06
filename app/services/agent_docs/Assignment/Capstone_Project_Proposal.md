
# Capstone Project Proposal: AI-Powered Educational Assistant - SmartBoy

Student Name: Tuan Khalib Cassim
Course: AI Orchestration Bootcamp
Date:2025-12-19

## 1. Introduction

### Problem Statement
SmartBoy is a production-ready educational platform for children, featuring interactive math games, spelling exercises, and knowledge-based quizzes. To maximize its impact, the project now integrates an advanced AI agent workflow for analyzing student data and generating actionable insights for teachers, parents, and students. The system must process natural language requests, retrieve and analyze educational data, and generate context-aware, safe responses.

### Target Users
- **Teachers**: Generate custom content, analyze student performance, and receive actionable reports.
- **Parents**: Get summaries and recommendations for their child's learning progress.
- **Students**: Receive personalized feedback and question sets.

### Possible Examples of User Prompts
1. "Summarize the student's math performance and suggest improvements."
2. "Draft a parent email about spelling progress."
3. "What are the most common mistakes in multiplication for grade 2?"
4. "Final Analysis report"
   1. """
        Example Output Format:

        ## Executive Summary
        Student shows strong performance in Science (85% accuracy) but struggles with Math (45%).

        ## 📚 Subject Analysis (Weakest First)

        ### 1. Math - 45% accuracy
        **Common Error Patterns:**
        - Multiplication table gaps (7x8, 6x9)
        - Fraction-to-decimal conversions

        **Recommendations:**
        1. Daily 5-minute times table practice
        2. Use visual fraction tools

        ### 2. Science - 85% accuracy
        **Strengths:** Strong conceptual understanding
        **Maintain by:** Regular reading, experiments
      """

## 2. Scope of Work

### A. Data Inflow (Frontend → DB)
- Data is collected via the SmartBoy mobile app (React/Capacitor frontend).
- User actions (game attempts, answers, scores) are sent to the backend (FastAPI) and stored in PostgreSQL (Neon cloud).
- The backend enforces business logic, user registration, and subscription management.

### B. Data Analysis (AI Agents, Neo4j)
- Data from PostgreSQL is ingested into Neo4j, which acts as both a knowledge graph and a vector database (see `docs/Colab/real/smartboy_agents.py`).
- Multi-agent workflow orchestrated via LangGraph:
  1. **Agent 1 (Data Ingester):** Extracts student, subject, and attempt data from PostgreSQL, generates embeddings, and imports nodes/relationships into Neo4j.
  2. **Agent 2 (Hybrid Retriever):** Uses Neo4j for both graph traversal (structured relationships) and vector similarity search (semantic patterns) to retrieve context.
  3. **Agent 3 (Analyst):** Generates reports and recommendations using Gemini (Google GenAI), based on retrieved context.
- The agent loop runs until sufficient evidence is gathered or returns "need more info".

### Guardrails
- **PII Masking**: Redacts personal info (names, emails, IDs) in outputs.
- **Prompt Injection Detection**: Flags/block attempts to override agent instructions.
- **Output Validation**: Ensures all responses cite sources or state "insufficient evidence".

### Demo Plan
Demo will process three sample prompts, showing:
1. Planner decision (intent + plan)
2. Retrieval output (top sources from Neo4j)
3. Final response (with citations)
Agent logs and intermediate outputs will be shown for each step.

## 3. Approach and Tools

### Framework and Model Choice
- **LangGraph**: For multi-agent orchestration and state management.
- **Neo4j 5.11+**: Unified graph + vector DB (no Chroma; all embeddings and relationships in Neo4j).
- **Gemini (Google GenAI)**: For report generation and advanced analysis.
- **SentenceTransformers**: For generating embeddings (384-dim, MiniLM).
- **FastAPI + PostgreSQL**: For data collection and business logic.

### Why This Fits
This approach leverages SmartBoy's robust backend and mobile frontend, adds a scalable AI analysis pipeline, and demonstrates best practices in agent chaining, hybrid retrieval, and safety guardrails. Neo4j's unified graph/vector model enables rich, explainable context for educational analysis.

## 4. System Architecture

### A. Architecture Diagram — Data Inflow (Frontend → DB)

Purpose: show the production data path used by the mobile app to record game attempts and user events into PostgreSQL.

```
[Mobile App (React/Capacitor)]
   ↓ HTTPS (REST)
[Backend API (FastAPI)]
   - Input validation (payload schema)
   - Auth (Firebase token verification)
   - Business rules (rate limits, subscription checks)
   ↓
[PostgreSQL (Neon)]
   - Tables: users, subjects, knowledge_question_attempts, prompts
   - Timestamps and event metadata
```

Notes:
- The backend validates request structure before DB writes (e.g., `knowledge_question_attempts` rows contain `uid`, `question`, `user_answer`, `evaluation_status`, `subject_id`, `datetime`).
- All writes follow existing repository layer patterns in `Backend_Python/app/repositories` and are used by the ingestion agent.

### B. Architecture Diagram — Data Analysis (ETL → Neo4j → Agents)

Purpose: show how analysis workflows run on the server side using the multi-agent pipeline implemented in `docs/Colab/real/smartboy_agents.py`.

```
[PostgreSQL (Neon)]
   ↓ (agent ETL)
[Agent 1: Data Ingester (LangGraph)]
   - Run SQL queries to extract users, attempts, subjects
   - Normalize rows, generate embeddings (SentenceTransformers)
   - Import into Neo4j as nodes/relationships (Student, KnowledgeAttempt, Subject)
   - Store embeddings on KnowledgeAttempt.embedding
   ↓
[Neo4j 5.11+ (Graph + Vector Index)]
   - Graph: Students, Attempts, Subjects, relations (ATTEMPTED, BELONGS_TO)
   - Vector index: attempt_embeddings for semantic search
   ↓
[Agent 2: Hybrid Retriever]
   - Graph traversals for structured stats (e.g., per-subject accuracy)
   - Vector queries for semantic mistake patterns (db.index.vector.queryNodes)
   ↓
[Agent 3: Analyst (Gemini)]
   - Consumes graph + vector context
   - Generates report with recommendations
   ↓
[Guardrails & Output Validator]
   - PII redaction, prompt-injection checks, citation enforcement
   ↓
[Final Response / Admin UI]
```

Notes:
- The Neo4j hybrid queries combine relational insights (counts, aggregates) with vector similarity to produce explainable, cited evidence shown in reports.
- Guardrails run after `Agent 3` to ensure outputs conform to required structure and to redact sensitive fields before presentation.


### Component Details
- **Frontend**: Collects user/game data, sends to backend.
- **Backend API**: Handles registration, business logic, and DB writes.
- **PostgreSQL**: Stores raw user/game data.
- **Agent 1 (Data Ingester)**: ETL from PostgreSQL to Neo4j, generates embeddings.
- **Neo4j**: Stores knowledge graph and vector embeddings for hybrid retrieval.
- **Agent 2 (Hybrid Retriever)**: Graph traversal + vector similarity search for context.
- **Agent 3 (Analyst)**: Generates actionable reports using Gemini, based on retrieved context.
- **Guardrails**: PII masking, prompt injection detection, output validation.

This modular architecture allows independent testing of each agent and seamless integration with the SmartBoy app. All analysis and retrieval is performed in Neo4j, ensuring explainable, reproducible outputs.

### Demo Plan
1. Demostrate how data inflow happens via the app already in production
2. Demostrate the Admin accessible Agents where reports can be generated & queried


