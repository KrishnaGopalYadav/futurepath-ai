# FuturePath AI — R1 Implementation Status

**Release:** R1 — Career Profile Intelligence  
**Status:** **R1 complete locally and ready for R2**  
**Purpose:** Operational acceptance record. The companion `r1-complete-implementation.md` contains the detailed implementation history and engineering narrative.

## R1 goal

> **What do we understand about my career today?**

R1 establishes a trustworthy, user-owned career profile from resume data. AI extraction is treated as candidate evidence; the user remains the source of truth once data is confirmed.

## Completed and validated

### Identity and authentication

- Password authentication backed by PostgreSQL.
- Google OAuth authentication backed by the same `users` table.
- Stable internal UUID identity.
- Provider/subject uniqueness prevents duplicate Google identities.
- Repeat Google login resolves to the same internal user UUID.
- Authenticated ownership checks protect user-owned career data.

### Resume ingestion

- PDF-only upload validation.
- 10 MB upload limit.
- SHA-256 checksum calculation.
- Same-user duplicate-content behavior is explicit and audit-friendly.
- Server-generated private storage keys.
- Local Docker-mounted file storage behind a storage abstraction.
- Durable `resumes` metadata in PostgreSQL.

### Asynchronous processing

- Redis broker.
- Celery worker.
- Durable `processing_jobs` records.
- Job lifecycle states: `queued`, `running`, `succeeded`, `failed`, `cancelled`.
- Bounded retry behavior with backoff.
- Retry path reuses durable resume/job state.

### R1 extraction

- PDF text extraction with `pypdf`.
- Optional structured OpenAI-compatible extraction.
- Deterministic local fallback when an AI key is not configured.
- Deterministic skill normalization.
- Structured extraction persisted in `resume_extractions`.
- Provenance retained through `source_resume_id` and skill evidence notes.

### Career Profile product surface

- Extracted headline and professional summary are shown on the authenticated dashboard.
- A dedicated R1 profile surface displays experiences, education, skills, projects and certifications.
- Each persisted entity exposes its source resume when provenance is available.
- Users can edit the career-profile fields through the existing profile form.
- Users can explicitly confirm the profile.
- Confirmation is persisted with `is_user_confirmed` and `confirmed_at`.
- Experiences, education, projects, certifications and user skills also carry confirmation state.
- Once a profile is confirmed, later resume processing stores new extraction evidence without silently replacing the confirmed career data.

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
- extraction payloads
- profile confirmation state
- embedding-foundation metadata

A real local extraction was validated with:

```text
31 skills
2 experiences
1 education record
9 projects
3 certifications
status = succeeded
extractor_version = r1-v1
```

The education persistence issue was fixed and re-tested after the extractor returned education objects using a different field shape.

### Embedding foundation

R1 now establishes a model-agnostic persistence foundation in PostgreSQL:

- one embedding record per user profile;
- content hash for invalidation/versioning;
- embedding model identifier;
- dimensions;
- lifecycle status (`pending`, `ready`, `failed`);
- JSONB vector payload for portability during R1/R2 development.

The implementation deliberately does **not** require the standard PostgreSQL image to contain pgvector. A later R2 architecture decision can migrate the stored vector payload to a native `vector` column/index once the embedding model, dimensions, metric and real similarity-query workload are finalized.

### Runtime

The local Docker Compose stack has been validated with:

```text
Frontend  :3000
API       :8000
Worker    : Celery
Postgres  :5432
Redis     :6379
```

The API and worker were tested through startup/restart/failure scenarios during implementation.

## Major R1 issues and fixes

1. **Repository/branch mismatch** — development initially involved a different remote; the working fork was synchronized with the upstream/main history.
2. **PostgreSQL container-name conflict** — an existing `futurepath-db` container prevented Compose from creating a replacement; the local container lifecycle was cleaned up.
3. **Alembic path confusion** — Alembic was initially invoked against a host-style path that did not exist inside the image; the actual `/app` container layout was established.
4. **Python import path failure** — Alembic initially could not import `app.config`; the Docker image layout was corrected so `/app/app` is importable.
5. **API/worker startup failure** — `tasks.py` referenced a missing/mismatched `process_resume` entry point; the processing entry point was restored and API/worker startup became healthy.
6. **Weak no-key extraction fallback** — the local fallback could preserve raw text without useful structured collections; a conservative deterministic parser was added.
7. **Education normalization failure** — extractor output used education keys that did not match the original persistence assumptions. Alias-aware normalization and PDF-based recovery were added.
8. **Validation query/schema mismatch** — validation initially queried columns such as `resumes.status` and `resume_extractions.raw_text` that are not part of the schema. Validation was changed to inspect the actual schema and `extracted_data` JSONB.
9. **Repeated uploads during testing** — multiple test submissions made the same checksum appear more than once. The behavior was clarified as submission/audit history rather than global cross-user deduplication.
10. **User ownership risk during reprocessing** — extraction previously could replace records created from an earlier resume. R1 now has explicit confirmation state, and confirmed profiles are protected from later extraction overwrite.

## R1 acceptance gate

All R1 acceptance criteria are now implemented:

- [x] Password login works.
- [x] Google login works and resolves to a stable existing user UUID on repeat login.
- [x] Resume upload creates durable metadata and a processing job.
- [x] Worker consumes the job successfully.
- [x] Extracted structured data is persisted to PostgreSQL.
- [x] Education, experience, project, certification and skill persistence has been validated.
- [x] Resume provenance is preserved.
- [x] Failed processing can be retried safely.
- [x] Career profile displays extracted data as user-owned product data.
- [x] Evidence/provenance is visible for persisted entities.
- [x] User corrections can be persisted.
- [x] User confirmation is persisted.
- [x] Later resume processing cannot silently overwrite confirmed profile data.
- [x] Embedding foundation is established without prematurely locking the project to a vector dimension/index.

**R1 is complete. R2 can now begin.**

## Explicit R2 boundary

R2 is the intelligence layer above the trusted R1 profile. It should consume confirmed career data rather than re-implement resume ingestion.

Planned R2 capabilities:

- target-role definition;
- job-description / role requirement ingestion;
- skill normalization and taxonomy mapping;
- exact and semantic matching;
- deterministic gap scoring;
- strong / partial / adjacent / missing / unknown classifications;
- evidence-backed gap explanations;
- prioritized skill gaps.

Do not pull R3 market intelligence, broad RAG, agents, MCP, Kafka, microservices or Kubernetes into R2 unless a measured requirement appears.
