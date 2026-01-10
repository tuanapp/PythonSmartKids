# Performance Report + Q&A Agents

This document summarizes the flow implemented in `performance_report_service.py` and represented in `agents.wsd`.

## High-Level Flow

1. Intent routing
   - `IntentRouterAgent` classifies as `report` or `qa` using heuristics + optional LLM check.
   - It extracts `subject` and `topic` from aliases/keywords when possible.

2. Input guardrails
   - Mask PII, detect prompt injection, and disallowed content.
   - If blocked, the request returns a safe response immediately.

3. Branch by intent
   - Report: full multi-agent report generation with cooldown check (optional skip-ingestion path).
   - QA: targeted retrieval and focused answer for a specific subject/topic (skips ingestion by default).

## QA Flow (intent = qa)

1. Entity inference
   - If `subject`/`topic` are missing, infer them from the query.

2. Fallback context (Postgres)
   - `_build_qa_fallback_answer` queries `knowledge_question_attempts` with keyword filters.
   - The "Most missed questions" list is extracted and injected into the QA context when available.

3. Neo4j retrieval loop (max retries, skip ingestion)
   - Q&A currently skips ingestion unconditionally and uses existing Neo4j data (no re-import).
   - Graph context: subject/topic accuracy plus hierarchical breakdown (Topic -> SubTopic -> Concept).
   - Vector context: similarity search over attempt embeddings with hierarchical metadata.
   - Hybrid context: graph + question-type breakdown + vector + fallback combined.

4. Evidence check
   - `assess_evidence_quality` computes a score (0-1) from summary lengths and attempt counts.
   - Evidence is sufficient if score >= 0.7 or any subject has >= `MIN_ATTEMPTS_PER_SUBJECT` attempts.

5. Answer generation
   - `AnalystAgent.generate_answer` uses a scoped prompt:
     - hierarchical weak concepts (Topic -> SubTopic -> Concept)
     - difficulty + Bloom's levels when available
     - missed examples and targeted improvement tips

6. Output guardrails + fallback
   - Output guardrails filter disallowed content.
   - If the answer is empty or "insufficient evidence" despite adequate evidence, fallback DB summary is used.

## Report Flow (intent = report)

1. Cooldown check
   - Enforces 24-hour cooldown using `performance_reports` timestamps.
   - Cooldown can be bypassed if `admin_key` matches the server-side `ADMIN_KEY` environment variable.

2. Workflow (two paths)
   - Default: `DataIngesterAgent` loads Postgres data, imports to Neo4j with hierarchical categorization,
     creates embeddings + vector index.
   - Optional: `admin_key='skip_data_ingester'` runs Retriever + Analyst only (reuse existing Neo4j data).
   - Retrieval loop runs without subject/topic filters.
   - `AnalystAgent.generate_report` creates the full markdown report using hierarchical context.

3. Persistence
   - Results are saved to `performance_reports` with metadata.
   - Optional LangSmith tracing is recorded when configured.

## Runtime Switches

- `PERFORMANCE_REPORT_ISOLATE_ANALYST=true`: runs a minimal workflow that invokes `AnalystAgent` only (for testing).
- If LangGraph is unavailable, the service falls back to a simplified workflow path.

## Key Implementation Details

- Intent routing returns `{intent, subject, topic}` with heuristic + LLM fallback.
- QA fallback context is always constructed and merged into the QA context.
- Retrieval retries until evidence is sufficient or retry limit reached.
- Hierarchical taxonomy: Topic -> SubTopic -> Concept, plus Difficulty + Bloom's levels.
- Responses include `model_used`, `model_configured`, masked `api_key_used`, and `trace_id` (when tracing is enabled).
- Safety checks exist on input and output, with guardrail details included in the response.

## Typical Response Fields

- `success`, `student_uid`, `intent`
- `subject`, `topic`, `query`
- `answer` (QA) / `analysis_report` (report)
- `evidence_sufficient`, `evidence_quality_score`
- `retrieval_attempts`, `processing_time_ms`
- `model_used`, `model_configured`, `api_key_used`
- `agents_executed`, `execution_path`, `response_source`, `is_fallback`
- `guardrails`, `agent_statuses`, `workflow_progress`, `errors`
- `trace_id`, `timestamp`
