# FuturePath AI — R1 Final Engineering Record

**Release:** R1 — Career Profile Intelligence  
**Status:** Final engineering record  
**Repository:** `KrishnaGopalYadav/futurepath-ai`

## 1. R1 objective

R1 establishes the durable **Know Me** layer: authenticate the user, capture resume evidence, process it asynchronously, extract structured career facts, persist them with provenance, and provide a user-controlled career profile.

Core rule:

> **AI proposes candidate data; deterministic application code validates, normalizes, authorizes and persists system state.**

R2 consumes the confirmed R1 profile rather than rebuilding resume ingestion.

## 2. How R1 started

The MVP started with a login page offering username/password and Google SSO, followed by a career page. The implementation then grew into a complete vertical slice.

Technology selected:

- Next.js / React
- FastAPI / Python
- PostgreSQL
- SQLAlchemy + Alembic
- Redis + Celery
- pypdf
- Docker Compose
- GitHub Actions
- optional OpenAI-compatible structured extraction
- deterministic local extraction fallback

RAG, agents, MCP, Kafka, Kubernetes and microservices were deliberately deferred under the **measure before migrate** principle.

## 3. Complete R1 flow

```text
Authenticate
  ↓
Upload PDF
  ↓
Validate + SHA-256
  ↓
Persist resume metadata
  ↓
Create processing job
  ↓
Redis → Celery Worker
  ↓
Extract PDF text
  ↓
Structured extraction / deterministic fallback
  ↓
Validate + normalize
  ↓
Persist profile entities + provenance
  ↓
Career workspace
  ↓
User review + correction
  ↓
Confirmed profile
```

## 4. Authentication and identity

PostgreSQL `users` is the durable identity source. Google identity is represented by `auth_provider` + `auth_subject`; the internal UUID is used by owned application records.

A Google test user was verified in PostgreSQL and repeated Google login resolution was verified against the same internal UUID. Email is profile information, not the sole external identity key.

## 5. Database foundation

R1 uses:

```text
users
resumes
processing_jobs
resume_extractions
career_profiles
experiences
education
projects
certifications
skills
user_skills
```

PostgreSQL is authoritative. Redis, Celery worker memory and model responses are not business state. Resume-derived records retain `source_resume_id` where applicable.

## 6. Resume ingestion

The upload boundary validates PDF type and a 10 MB limit, calculates SHA-256, creates a private server-generated storage key, persists metadata, creates a processing job and returns `202 Accepted`.

Client filenames are metadata only and never become filesystem paths. Binary files remain outside PostgreSQL behind a storage abstraction.

## 7. Asynchronous processing

```text
FastAPI → Redis → Celery → Worker → PostgreSQL
```

`processing_jobs` persists `queued`, `running`, `succeeded`, `failed` and `cancelled` states plus retry information.

Celery + Redis was chosen because R1 needs background jobs, retries and worker concurrency. Kafka was deferred because R1 does not yet require replayable enterprise event streams or multiple independent consumers.

## 8. Extraction

The worker reads the private PDF with pypdf, cleans the text, then uses either structured model extraction or a deterministic local fallback.

The AI boundary is:

```text
text → candidate JSON → validation → normalization → persistence
```

Raw model output is never authoritative database state.

Extraction is versioned as `r1-v1` and retained in `resume_extractions.extracted_data` for traceability/reprocessing.

## 9. Deterministic fallback

The fallback recognizes common sections such as `PROFESSIONAL SUMMARY`, `TECHNICAL SKILLS`, `PROFESSIONAL EXPERIENCE`, `EDUCATION`, `PROJECTS` and `CERTIFICATIONS`.

It exists so local development and CI can validate the full pipeline without requiring an external model provider. It is intentionally conservative and is not claimed to equal semantic LLM extraction.

## 10. Normalization and the education failure

Dates, optional fields, aliases and skills are normalized before persistence. Skills use deterministic case/whitespace normalization.

A major failure was a Celery retry loop caused by an education item containing only:

```text
end_date
institution
qualification
start_date
```

The normalizer incorrectly required `field_of_study`. That field is optional, so the normalizer was fixed to accept the valid minimal shape and persist the missing value as null.

The fix was verified with a real PostgreSQL record for:

```text
University of Pune
B.Tech in Computer Science and Engineering
2017-01-01 → 2021-01-01
```

The associated `r1-v1` extraction reported one education item.

## 11. Provenance

R1 follows:

```text
Fact → Evidence → Inference → Recommendation
```

Resume-derived entities retain their source resume where applicable and skill evidence can be retained with the extraction. This is the basis for future explainability.

## 12. Persistence

Successful extraction persists the career profile, experiences, education, projects, certifications and normalized user skills. The extraction JSONB is retained as the versioned candidate record.

The persistence boundary is user-scoped and deterministic. A job must not be considered successfully processed while leaving incoherent partial business state.

## 13. What was proven locally

A real local resume was processed end-to-end with:

```text
extractor_version = r1-v1
status             = succeeded
skills             = 31
experiences        = 2
education          = 1
projects           = 9
certifications     = 3
```

PostgreSQL queries independently verified persisted experiences, education, projects, certifications and skills. The worker reached `succeeded` and the API/worker were validated under Docker Compose.

## 14. Docker and CI cleanup

The API image uses `/app` as `WORKDIR`; the Python package is `/app/app`. An earlier local test incorrectly used `/app/backend/tests`, which does not exist in the image.

The Dockerfile now includes repository tests at `/app/tests`.

Canonical R1 test command, used locally and by CI:

```bash
docker compose run --rm api \
  python -m unittest discover -s /app/tests -p 'test_*.py'
```

CI also creates a temporary CI `.env`, builds the image, starts PostgreSQL/Redis/API/worker, runs migrations, checks API health, confirms worker readiness and tears down the stack.

This makes the R1 test environment independent of the developer's host Python/pip setup.

## 15. Major engineering issues and lessons

### Git remote / branch confusion

Work moved between the Akash repository and the Krishna fork. The lasting rule is to verify `git remote -v`, branch, recent commits and comparison state before pushing.

### PostgreSQL container conflict

An existing `futurepath-db` caused a Compose naming collision. Container lifecycle cleanup resolved it. Explicit container names should be used carefully.

### Alembic path errors

Host paths were initially confused with container paths. The Dockerfile and commands were aligned to the real `/app` layout.

### API/worker import failure

A mismatch between `app.tasks` and `app.resume_processing` caused API and worker restart loops. The processing entry point was reconciled with the Celery task contract.

### Successful extraction with zero entities

An early deterministic path returned successful status while producing zero structured career entities. The fallback parser was strengthened and semantic extraction counts became part of validation.

### Education retry loop

Missing optional `field_of_study` caused repeated retries. The normalization contract was corrected so optional data stays optional.

### Post-login UI failure

The original `/welcome` page redirected to `/` whenever any parallel API call failed. This hid the real error and made successful login appear broken. The workspace was changed to show a recoverable error state with Retry instead of silently redirecting.

## 16. R1 UI enhancement

The post-login career workspace now includes:

- branded navigation;
- authenticated user identity;
- R1 status indicator;
- resume evidence/upload card;
- processing status badges;
- retry action;
- responsive desktop/mobile layout;
- loading state;
- recoverable API error state;
- editable career profile;
- save confirmation;
- explicit user-controlled/source-of-truth messaging.

Password login continues to redirect to `/welcome`. The workspace calls `/auth/me`, `/career-profile` and `/resumes` with credentials and presents errors rather than hiding them.

After frontend changes, rebuild with:

```bash
docker compose up -d --build frontend
```

After backend changes:

```bash
docker compose up -d --build api worker
```

## 17. Post-login local verification

If sign-in succeeds but the career workspace does not appear:

```bash
docker compose ps
curl -i http://localhost:8000/health
curl -I http://localhost:3000
docker compose logs api --tail 100
docker compose logs frontend --tail 100
```

The expected state is API/worker `Up`, PostgreSQL healthy, Redis healthy, API health `200`, and the frontend responding on port `3000`.

## 18. R1 acceptance boundary

Completed/proven:

- password authentication;
- Google authentication and stable provider identity;
- PostgreSQL user persistence;
- PDF upload and validation;
- SHA-256 integrity;
- private storage abstraction;
- durable processing jobs;
- Redis/Celery processing;
- PDF extraction;
- structured extraction;
- deterministic fallback;
- validation/normalization;
- experiences persistence;
- education persistence;
- projects persistence;
- certifications persistence;
- normalized skill persistence;
- resume provenance;
- retry handling;
- editable career profile;
- Docker-based R1 tests;
- CI environment isolation;
- improved post-login career workspace.

Before the R1→R2 gate, the remaining product-hardening items are:

1. expose evidence/provenance clearly at the individual profile/entity level;
2. make extracted-vs-confirmed state explicit wherever required by the final profile model;
3. exercise the embedding foundation against a concrete semantic use case, or formally remove it from R1 acceptance and activate it when R2 needs it.

## 19. Why R2 comes next

R2 answers:

> **What am I missing for a target role?**

It should consume the confirmed R1 profile and add target-role definitions, role/job requirement ingestion, skill taxonomy mapping, exact + semantic matching, deterministic gap scoring, evidence-backed explanations and prioritized skill gaps.

R2 must not re-implement R1 authentication, resume ingestion or the basic processing pipeline.

## 20. Interview Q&A

**Why PostgreSQL?** — The domain has ownership, relationships, uniqueness, transactions and queryable structured data. JSONB handles flexible extraction payloads.

**Why Redis + Celery?** — Resume processing is asynchronous and retryable; Celery provides task execution and retries while Redis provides broker/result infrastructure.

**Why not Kafka?** — R1 has a background-job problem, not a demonstrated enterprise event-stream requirement.

**Why not let the LLM write to PostgreSQL?** — Model output is probabilistic; application code must enforce schema, normalization, authorization and consistency.

**Why version extraction?** — Models/parsers change; versioning enables traceability and controlled reprocessing.

**Why checksum?** — It gives deterministic content integrity and duplicate-content detection without trusting filenames.

**Why provenance?** — Career intelligence must be explainable and traceable to evidence.

**Why a fallback parser?** — Local development and CI should remain useful without an external model provider.

**How would you scale?** — Measure queue latency, worker resource usage, extraction latency, database load and storage growth first; then scale workers/storage and introduce vector infrastructure, service decomposition, Kafka or Kubernetes only when evidence requires it.

## 21. Final R1 principle

```text
Authenticate
  ↓
Capture evidence
  ↓
Process asynchronously
  ↓
Extract candidate facts
  ↓
Validate + normalize
  ↓
Persist with provenance
  ↓
Let the user correct
  ↓
Confirm the profile
  ↓
Use confirmed profile for R2
```

**R1 is the trustworthy career-data foundation. R2 begins only after that foundation is user-controlled, explainable and stable.**
