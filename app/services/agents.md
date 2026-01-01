# Performance Report + Q&A Agents

This document summarizes the flow implemented in `performance_report_service.py` and represented in `agents.wsd`.

## High-Level Flow

1. Intent routing
   - `IntentRouterAgent` classifies as `report` or `qa`.
   - It extracts `subject` and `topic` from the query when possible.

2. Input guardrails
   - Mask PII, detect prompt injection, and disallowed content.
   - If blocked, the request returns a safe response immediately.

3. Branch by intent
   - Report: full multi-agent report generation with cooldown check.
   - QA: targeted retrieval and focused answer for a specific subject/topic.

## QA Flow (intent = qa)

1. Entity inference
   - If `subject`/`topic` are missing, infer them from the query.

2. Fallback context (Postgres)
   - `_build_qa_fallback_answer` queries `knowledge_question_attempts` with keyword filters.
   - The “Most missed questions” list is extracted and injected into the QA context.

3. Neo4j retrieval loop (max retries)
   - Graph context: per-subject correct/incorrect counts, filtered by subject/topic.
   - Vector context: similarity search over attempt embeddings, filtered by subject/topic.
   - Hybrid context: graph + vector + fallback combined.

4. Evidence check
   - `assess_evidence_quality` computes a score (0–1) from summary lengths and attempt counts.
   - Evidence is sufficient if score >= 0.7 or any subject has >= `MIN_ATTEMPTS_PER_SUBJECT` attempts.

5. Answer generation
   - `AnalystAgent.generate_answer` uses a scoped prompt:
     - accuracy for topic (if available)
     - missed examples
     - a targeted improvement tip

6. Output guardrails + fallback
   - Output guardrails filter disallowed content.
   - If the answer is “insufficient evidence” despite adequate evidence, fallback DB summary is used.

## Report Flow (intent = report)

1. Cooldown check
   - Enforces 24-hour cooldown using `performance_reports` timestamps.

2. Workflow
   - `DataIngesterAgent` loads Postgres data, imports to Neo4j, and builds embeddings.
   - Retrieval loop runs without subject/topic filters.
   - `AnalystAgent.generate_report` creates the full markdown report.

3. Persistence
   - Results are saved to `performance_reports` with metadata.

## Key Implementation Details

- Intent routing returns `{intent, subject, topic}`.
- QA fallback context is always constructed and merged into the QA context.
- Retrieval retries until evidence is sufficient or retry limit reached.
- Responses include `model_used`, `model_configured`, and masked `api_key_used`.
- Safety checks exist on input and output.

## Typical Response Fields

- `success`, `student_uid`, `intent`
- `subject`, `topic`, `query`
- `answer` (QA) / `analysis_report` (report)
- `evidence_sufficient`, `evidence_quality_score`
- `retrieval_attempts`, `processing_time_ms`
- `model_used`, `model_configured`, `api_key_used`
- `guardrails`, `trace_id`, `timestamp`
