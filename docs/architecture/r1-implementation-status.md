# FuturePath AI — R1 Implementation Status

**Release:** R1 — Career Profile Intelligence  
**Status:** Backend ingestion/extraction/persistence validated locally; R1 product-surface hardening remains before R2  
**Purpose:** Short operational status. See `r1-complete-implementation.md` for the complete implementation history, issues, decisions, and validation record.

## R1 goal

> **What do we understand about my career today?**

R1 establishes a trustworthy, user-owned career profile from resume data. The system must distinguish source evidence from AI interpretation and must keep the user in control of confirmed profile data.

## Completed and validated

### Identity and authentication

- Password authentication backed by PostgreSQL.
- Google OAuth authentication backed by the same `users` table.
- Stable internal UUID identity.
- Provider/subject uniqueness prevents duplicate Google identities.
- Subsequent Google logins resolve to the same internal user UUID.
- Authenticated ownership checks protect user-owned career data.

### Resume ingestion

- PDF-only upload validation.
- 10 MB upload limit.
- SHA-256 checksum calculation.
- Same-user duplicate-content suppression.
- Server-generated private storage keys.
- Local Docker-mounted file storage behind a storage abstraction.
- Durable `resumes` metadata in PostgreSQL.

### Asynchronous processing

- Redis broker.
- Celery worker.
- Durable `processing_jobs` records.
- Job lifecycle states: `queued`, `running`, `succeeded`, `failed`, `cancelled`.
- Bounded retry behavior with backoff.
- Retry path reuses durable resume/job state rather than creating an unowned duplicate.

### R1 extraction

- PDF text extraction with `pypdf`.
- Optional structured OpenAI-compatible extraction.
- Deterministic local fallback when an AI key is not configured.
- Deterministic skill normalization.
- Structured extraction data is persisted in `resume_extractions`.
- Source provenance is retained through `source_resume_id` and skill evidence notes.

### PostgreSQL persistence

The validated R1 path persists:

- career summary/headline
- experiences
- education
- projects
- certifications
- canonical skills
- user-skill associations
- skill evidence
- resume metadata
- processing jobs

A successful local extraction was validated with:

```text
31 skills
2 experiences
1 education record
9 projects
3 certifications
status = succeeded
extractor_version = r1-v1
```

The education persistence issue was specifically fixed and re-tested after the extractor returned education objects using a different field shape.

### Runtime

The local Docker Compose stack has been validated with:

```text
Frontend  :3000
API       :8000
Worker    Celery
Postgres  :5432
Redis     :6379
```

The API and worker were also tested through restart/failure scenarios during implementation.

## Important issues fixed during R1

1. **Repository/branch mismatch** — development was initially performed against a different remote; the working fork was synchronized and later reconciled with Akash's `main`.
2. **PostgreSQL container-name conflict** — an existing `futurepath-db` container prevented Compose from creating the replacement service; the local container lifecycle was cleaned up.
3. **Alembic path confusion** — `alembic -c backend/alembic.ini` was invoked with the wrong in-container path; the Compose build context was reconciled with the actual `/app` layout.
4. **Python import path failure** — Alembic initially could not import `app.config`; the Docker image layout and Python module path were corrected so the application package is available as `/app/app`.
5. **API/worker startup failure** — `tasks.py` referenced `process_resume` while the implementation was missing/mismatched; the processing entry point was restored and the API/worker became healthy.
6. **No-key extraction weakness** — the initial deterministic fallback could preserve raw text while producing empty structured collections; a conservative deterministic parser was added so the local path remains useful without an AI key.
7. **Education normalization failure** — R1 extraction produced education keys such as `institution`, `qualification`, `start_date`, and `end_date`, while persistence expected a narrower shape. Alias-aware normalization and education recovery were added; education now persists correctly.
8. **Schema/query mismatch during validation** — validation queries initially assumed columns such as `resumes.status` or `resume_extractions.raw_text` that do not exist in the implemented schema. Validation was changed to inspect the actual schema and `extracted_data` JSON instead.
9. **Repeated identical uploads** — duplicate content was observed as multiple resume records across tests. The behavior was clarified as same-user checksum suppression rather than global cross-user deduplication, preserving privacy boundaries.

## Deliberately deferred

### Career Profile as a user-controlled surface

The next R1 work is not another extraction feature. It is the product layer around the extracted data:

- display extracted career data clearly;
- show evidence/provenance for extracted fields;
- let users correct or reject extracted information;
- persist confirmed corrections without silently overwriting them on later extraction;
- define precedence between resume-derived data and user-confirmed data.

### Embeddings / pgvector foundation

Embeddings are intentionally not treated as complete merely because pgvector appears in the architecture documents. Before adding the vector column/index we must finalize:

- the actual R1/R2 feature that needs embeddings;
- embedding model/provider and version;
- vector dimension;
- similarity metric;
- content hash/version semantics;
- regeneration behavior after profile edits;
- active-vector selection;
- failure/retry behavior.

Do not invent a vector dimension or add an index without a real query use case.

### OCR

Deferred until real resume samples demonstrate meaningful image-only/scanned-PDF demand.

### Production object storage

Local private storage remains the development implementation. Production object storage can be introduced behind the existing storage abstraction when deployment requirements justify it.

### RAG, agents, MCP, Kafka, microservices, Kubernetes/OpenShift

These remain later-stage capabilities. They are not prerequisites for completing R1.

## R1 acceptance gate before R2

R2 must not start until all of the following are true:

- [x] Password login works.
- [x] Google login works and resolves to a stable existing user UUID on repeat login.
- [x] Resume upload creates durable metadata and a processing job.
- [x] Worker consumes the job successfully.
- [x] Extracted structured data is persisted to PostgreSQL.
- [x] Education, experience, project, certification, and skill persistence has been validated.
- [x] Resume provenance is preserved.
- [x] Failed processing can be retried safely.
- [x] Same-user duplicate upload suppression works.
- [ ] Career profile displays extracted data as user-owned product data.
- [ ] Evidence/provenance is visible at the appropriate field/entity level.
- [ ] User corrections are persisted as confirmed state.
- [ ] Reprocessing cannot silently overwrite user-confirmed corrections.
- [ ] Embedding foundation is implemented and tested, or explicitly removed from the R1 acceptance criteria through an architecture decision.

**R2 begins only after this gate is closed.**