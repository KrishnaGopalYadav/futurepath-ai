# FuturePath AI — R1 Implementation

## 1. R1 goal

R1 turns a processed resume into a durable, user-controlled Career Profile. Resume extraction is evidence; user-confirmed Career Profile data is authoritative.

R1 is intentionally completed before R2. R2 should consume a stable, confirmed profile rather than raw, repeatedly changing extraction output.

## 2. How we started

R1 began after authentication, PostgreSQL persistence, Redis/Celery processing, and resume upload were working. The first extraction pipeline proved that a resume could be converted into structured skills, experience, education, projects, and certifications.

The successful sample resume produced **31 skills, 2 experiences, 1 education record, 9 projects, and 3 certifications**. That result established the extraction engine, but it also exposed an important product gap: successful extraction did not automatically mean the Career Profile was complete, editable, traceable, or authoritative.

## 3. R1 architecture

- **FastAPI** — authenticated API and R1 Career Profile endpoints.
- **PostgreSQL** — durable users, resumes, processing jobs, extraction snapshots, and normalized career facts.
- **Redis + Celery** — asynchronous resume processing.
- **Extractor `r1-v1`** — versioned extraction contract.
- **`source_resume_id`** — provenance from normalized career facts back to uploaded evidence.
- **`is_user_confirmed` / `confirmed_at`** — explicit authority boundary between AI evidence and user-approved data.
- **`career_profile_embeddings`** — database foundation for future semantic/vector retrieval.
- **Next.js** — Career Profile user experience.

## 4. End-to-end R1 workflow

```text
User signs in
    ↓
Upload PDF resume
    ↓
Create Resume + ProcessingJob
    ↓
Celery worker executes r1-v1
    ↓
Store ResumeExtraction JSON
    ↓
Normalize structured career facts
    ↓
Attach source_resume_id provenance
    ↓
Career Profile reads facts + evidence
    ↓
User reviews and edits
    ↓
Save corrections
    ↓
Confirm Career Profile
    ↓
Confirmed records become authoritative
    ↓
Profile content hash updates embedding state
```

## 5. What was implemented

### 5.1 Resume processing

The resume-processing engine stores the original PDF, creates a processing job, runs asynchronously through Celery, records the extraction under `r1-v1`, and persists normalized career facts.

The processing job lifecycle is explicit: `queued → running → succeeded` or `failed`/`cancelled`, with retry support for recoverable failures.

### 5.2 Career Profile surface

The R1 API exposes an authenticated Career Profile snapshot containing:

- profile/headline/summary information
- experiences
- education
- projects
- certifications
- skills
- resume evidence metadata
- confirmation state

The UI can therefore treat the Career Profile as a product surface rather than merely displaying raw extraction output.

### 5.3 User corrections

R1 supports saving user edits to the profile and its career sections. Existing records can be updated by ID, new records can be added, and removed records are deleted from the user's editable snapshot.

Ownership is enforced through the authenticated user ID, so one user cannot edit another user's profile records.

### 5.4 Confirmation

Confirmation is a deliberate user action. Once confirmed:

- the profile is marked `is_user_confirmed = true`
- `confirmed_at` records the confirmation time
- experiences, education, projects, certifications, and skills are marked user-confirmed

This makes the user's approved profile the authoritative product state.

### 5.5 Provenance / evidence

Normalized career facts retain `source_resume_id`. The R1 API resolves those IDs to the user's uploaded resume metadata, including filename and upload timestamp.

The raw extraction remains available in `resume_extractions.extracted_data`, giving the system an extraction snapshot separate from the normalized, user-controlled Career Profile.

### 5.6 Embedding foundation

R1 creates one `career_profile_embeddings` row per user containing:

- deterministic `content_hash`
- `embedding_model`
- `dimensions`
- lifecycle `status` (`pending`, `ready`, `failed`)
- optional JSON embedding payload
- timestamps

R1 deliberately does **not** select a production embedding provider or force pgvector. R2 can make that decision once target-role intelligence and semantic retrieval requirements are defined.

The content hash provides a deterministic invalidation boundary: meaningful profile changes can move the embedding state back to `pending`.

## 6. Issues encountered and how they were solved

### 6.1 Education extraction succeeded but education rows were empty

The extractor returned education data using keys such as `institution`, `qualification`, `start_date`, and `end_date`. Earlier normalization was too strict for provider-shaped output, so extraction could succeed while the relational `education` table remained empty.

**Fix:** explicit education normalization and validation were added. R1 verification checks both extraction JSON and normalized database rows.

**Lesson:** pipeline success must mean the complete business workflow succeeded, not merely that an upstream parser returned JSON.

### 6.2 Confirmed data needed protection from later resume uploads

A later resume may contain incomplete or contradictory information. Automatically replacing a user-confirmed profile would make the product unpredictable.

**Fix:** confirmation is an authority boundary. Resume extraction remains evidence; confirmed Career Profile records are not silently replaced by subsequent extraction.

### 6.3 Career Profile initially lacked a correction workflow

Displaying extracted data was not sufficient because resume parsing is probabilistic and users must be able to correct mistakes.

**Fix:** R1 added authenticated save/update behavior and confirmation semantics so users can review, correct, persist, and then approve their profile.

### 6.4 Docker test path mismatch

The repository's Dockerfile copies `backend/tests` into `/app/tests`. The correct in-container unittest discovery path is therefore `/app/tests`, not `/app/backend/tests`.

The local command is:

```bash
docker compose run --rm api python -m unittest discover -s /app/tests -p 'test_*.py'
```

The CI workflow uses the same command so local and CI test paths do not drift.

### 6.5 Alembic application import problem

The container runs the application package from `/app/app`. Alembic originally depended on an application import path that was not reliably available during migration startup.

**Fix:** `backend/alembic/env.py` was made independent of the application import graph and reads `DATABASE_URL` directly. This allows migrations to start before the FastAPI application imports.

### 6.6 Alembic revision was longer than PostgreSQL's version column

The R1 migration used revision ID `0002_r1_profile_confirmation_embeddings`. PostgreSQL's existing `alembic_version.version_num` column was `VARCHAR(32)`, while that revision identifier is longer than 32 characters. The migration therefore failed while Alembic attempted to record the new revision.

**Fix:** the R1 migration now widens `alembic_version.version_num` to `VARCHAR(64)` before Alembic records the new revision. The migration remains backward-compatible with databases currently at `0001_initial_schema`, and the downgrade deliberately leaves the version column at 64 characters so a long revision can be recorded safely during downgrade execution.

This was the cause of the startup loop seen as:

```text
sqlalchemy.exc.DataError: value too long for type character varying(32)
UPDATE alembic_version SET version_num='0002_r1_profile_confirmation_embeddings'
```

### 6.7 API and worker restart together when migrations fail

The Docker Compose API command runs migrations before Uvicorn. When migration startup fails, the API never reaches port 8000 and the worker may also restart if its application import graph depends on the same broken code/schema state.

**Operational rule:** inspect `docker compose logs api` first for startup/migration failures; do not debug browser login or upload behavior until `/health` is returning 200.

## 7. Design decisions and why

### Evidence versus truth

**Decision:** the resume is evidence; the Career Profile is product state.

**Why:** resumes can be stale, incomplete, ambiguous, or contain extraction errors. A stable user-controlled profile is required before intelligent recommendations can be trusted.

### Explicit confirmation

**Decision:** require a user confirmation step before treating extracted information as authoritative.

**Why:** this gives the user control, makes AI behavior explainable, and establishes a stable input contract for R2.

### Versioned extraction

**Decision:** persist `r1-v1` with each extraction.

**Why:** extraction behavior can evolve. Versioning allows future extractors to coexist and makes debugging/reprocessing more deterministic.

### Provenance on normalized facts

**Decision:** retain `source_resume_id` on career facts.

**Why:** users need evidence for where information came from, and the system needs an audit trail separating source evidence from user corrections.

### Database-native embedding foundation

**Decision:** store embedding metadata and an optional JSON representation in PostgreSQL during R1 rather than selecting pgvector/provider infrastructure prematurely.

**Why:** R1 establishes the contract and invalidation mechanism. R2 can select the embedding model, dimensions, vector database strategy, and retrieval architecture using actual product requirements.

### Single local/CI test command

**Decision:** CI executes the same unittest discovery command used inside the Docker API image.

**Why:** different test paths are a common source of false confidence. The container image is the runtime environment we actually ship locally, so CI should validate that same layout.

## 8. R1 validation checklist

Run from the repository root:

```bash
docker compose up -d --build
```

Then verify migration/startup:

```bash
docker compose ps
docker compose logs api --tail 100
curl -f http://localhost:8000/health
```

Run the same unit tests used by CI:

```bash
docker compose run --rm api python -m unittest discover -s /app/tests -p 'test_*.py'
```

Then perform the product acceptance flow:

1. Sign in.
2. Upload a PDF resume.
3. Confirm the upload returns `202 Accepted`.
4. Confirm the Celery worker receives `process_resume_job`.
5. Confirm the processing job reaches `succeeded`.
6. Confirm `resume_extractions.status = 'succeeded'`.
7. Confirm structured extraction counts are non-zero for the sample resume.
8. Confirm normalized `experiences`, `education`, `projects`, `certifications`, and `user_skills` rows exist.
9. Open Career Profile and verify extracted data is visible.
10. Verify evidence/provenance points back to the uploaded resume.
11. Edit a profile value and save it.
12. Reload the page and verify the correction persists.
13. Confirm the Career Profile.
14. Verify `is_user_confirmed = true` and `confirmed_at` is populated.
15. Upload/process another resume and verify confirmed values are not silently overwritten.
16. Verify the embedding row has a deterministic content hash and appropriate pending/ready lifecycle state.

## 9. Useful database verification queries

### Processing jobs

```sql
SELECT id, resume_id, job_type, status, attempt_count, error_code,
       created_at, started_at, finished_at
FROM processing_jobs
ORDER BY created_at DESC
LIMIT 10;
```

### Extraction summary

```sql
SELECT id, resume_id, extractor_version, status,
       jsonb_array_length(COALESCE(extracted_data->'skills', '[]'::jsonb)) AS skills,
       jsonb_array_length(COALESCE(extracted_data->'experiences', '[]'::jsonb)) AS experiences,
       jsonb_array_length(COALESCE(extracted_data->'education', '[]'::jsonb)) AS education,
       jsonb_array_length(COALESCE(extracted_data->'projects', '[]'::jsonb)) AS projects,
       jsonb_array_length(COALESCE(extracted_data->'certifications', '[]'::jsonb)) AS certifications
FROM resume_extractions
ORDER BY created_at DESC;
```

### Normalized education

```sql
SELECT id, user_id, institution, qualification, field_of_study,
       start_date, end_date, source_resume_id, is_user_confirmed
FROM education
ORDER BY created_at DESC;
```

### Confirmation state

```sql
SELECT user_id, is_user_confirmed, confirmed_at, updated_at
FROM career_profiles;
```

### Embedding foundation

```sql
SELECT user_id, content_hash, embedding_model, dimensions, status,
       created_at, updated_at
FROM career_profile_embeddings;
```

## 10. R1 definition of done

R1 is complete when all of the following are true:

- Authentication works.
- Resume upload is durable and authenticated.
- Asynchronous processing works.
- `r1-v1` extraction succeeds on the supported sample resume.
- Extracted career facts are normalized into relational tables.
- Education normalization is verified, not assumed.
- Career Profile is visible after processing.
- Career facts expose resume provenance.
- Users can correct and save profile data.
- Saved corrections survive reload.
- Users can explicitly confirm the profile.
- Confirmed records are protected from silent replacement by later extraction.
- Embedding content-hash state is maintained.
- The same Docker unittest command runs locally and in CI.
- Alembic migrations can reach `head` from the initial schema in a fresh CI database.
- The local Docker stack reaches healthy API and worker startup.

Only after this checklist passes should implementation move to R2.

## 11. R2 boundary

R2 starts from the confirmed Career Profile. Its responsibility is target-role and skill-gap intelligence, not fixing or redefining the R1 data foundation.

Expected R2 direction:

```text
Confirmed Career Profile
        ↓
Target Role Selection
        ↓
Role / Job Requirement Model
        ↓
Skill Normalization + Gap Analysis
        ↓
Priority / Readiness Signals
        ↓
Embedding + Semantic Retrieval
        ↓
Personalized Career Recommendations
```

R2 should reuse R1's provenance and confirmation semantics rather than bypassing them.
