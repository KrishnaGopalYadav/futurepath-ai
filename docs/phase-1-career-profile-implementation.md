# Release 1 — Career Profile Intelligence Implementation Plan

## Why this is the next step

The FuturePath roadmap defines Release 1 as **Career Profile Intelligence**. The product question is:

> What do we understand about my career today?

The R1 journey is designed around resume ingestion, structured extraction, evidence/provenance, skill normalization, embeddings, persistent career data, processing status, retries and user correction.

The current branch already has authentication and a basic profile editor. This document records the remaining R1 implementation sequence so the project evolves according to the repository's architecture rather than introducing R2/R3 technologies prematurely.

## R1 architecture target

```text
Next.js
   ↓ REST
FastAPI modular monolith
   ├── Auth
   ├── Resume
   ├── Profile
   └── Skills
        ↓ enqueue
Redis
        ↓
Celery worker
   ├── file validation
   ├── PDF extraction
   ├── text normalization
   ├── structured LLM extraction
   ├── Pydantic validation
   ├── evidence/provenance
   ├── skill normalization
   └── embeddings
        ↓
PostgreSQL + pgvector
```

## Implementation order

1. Replace development-only table creation with Alembic migrations.
2. Introduce PostgreSQL + pgvector in Docker Compose while retaining SQLite only as an explicit lightweight development fallback if needed.
3. Add a Resume entity and ProcessingJob entity.
4. Add secure resume upload endpoint with content type, extension, size and ownership validation.
5. Add local object-storage abstraction so binary storage is separated from relational metadata.
6. Add pypdf/pdfplumber extraction service.
7. Add normalized extracted-text persistence.
8. Add Celery + Redis worker pipeline.
9. Add processing status transitions: PENDING → PROCESSING → COMPLETED or FAILED.
10. Add bounded retry/backoff and idempotency using document fingerprint/job identifiers.
11. Add structured LLM extraction behind an interface and validate output with Pydantic.
12. Persist extracted experiences, education, skills and evidence with provenance.
13. Add deterministic skill normalization.
14. Add configurable embeddings and pgvector persistence.
15. Add profile review/correction endpoints and UI.
16. Add observability: request ID, job ID, processing duration, errors, retries and LLM latency.
17. Add automated tests for authentication, upload validation, extraction, status transitions, retries, idempotency and authorization.
18. Add GitHub Actions CI for linting, tests, security checks and Docker builds.

## R1 acceptance criteria

A user can:

- authenticate securely;
- upload a valid PDF resume;
- receive a processing status rather than waiting on a long synchronous HTTP request;
- see extraction progress/result;
- review extracted career information;
- correct extracted information;
- save the confirmed profile;
- retry a failed processing job safely;
- never access another user's resume/profile data.

## Architecture guardrails

Do not introduce RAG, agents, MCP, Kafka, Kubernetes or OpenShift in R1 merely because they appear in the future-state architecture. The repository's architecture principle is to introduce complexity only when a measurable requirement justifies it.

R1 should remain a modular monolith with PostgreSQL/pgvector, Redis/Celery for asynchronous work, Docker Compose locally, and structured LLM output with deterministic application validation.
