# FuturePath AI — R1 Implementation

## 1. R1 goal

R1 turns a processed resume into a durable, user-controlled Career Profile. Resume extraction is treated as evidence; user-confirmed profile data is authoritative.

## 2. How we started

R1 began after authentication, PostgreSQL persistence, Redis/Celery processing, and the resume upload flow were working. The initial extraction pipeline proved that a resume could be converted into structured skills, experience, education, projects, and certifications.

The first successful sample resume produced 31 skills, 2 experiences, 1 education record, 9 projects, and 3 certifications.

## 3. Architecture established

- FastAPI API for authenticated profile and resume operations.
- PostgreSQL for durable users, resumes, processing jobs, extraction snapshots, and career facts.
- Redis + Celery for asynchronous resume processing.
- R1 extractor version `r1-v1`.
- `source_resume_id` on extracted career facts for provenance.
- `is_user_confirmed` and `confirmed_at` for authority/confirmation state.
- `career_profile_embeddings` as the database foundation for a future vector representation.
- Next.js R1 Career Profile UI.

## 4. Important implementation issues and fixes

### 4.1 Container Python path / Alembic layout

The Docker image runs the application from `/app` and copies the repository-level `app` package into `/app/app`. Alembic must therefore resolve the same application package instead of assuming `/app/backend` exists inside the container.

### 4.2 Resume extraction produced education aliases

The extractor returned education objects using keys such as `institution`, `qualification`, `start_date`, and `end_date`. The persistence layer originally rejected some provider-shaped education payloads. R1 added explicit education alias normalization and a diagnostic error listing received keys when normalization cannot produce a valid record.

### 4.3 Empty education persistence

Extraction success was not enough: the structured data had to become relational records. R1 validation now checks both the extraction JSON and the normalized `education` table. A successful R1 extraction with zero normalized records is treated as a persistence defect rather than a successful product outcome.

### 4.4 Confirmed data could be overwritten by a later resume

The initial implementation persisted every extraction directly into the career tables. That conflicted with the product rule that a confirmed profile is authoritative. The corrected design makes confirmation a write-protection boundary: subsequent automatic extraction remains stored as resume evidence but does not replace confirmed career facts.

### 4.5 Career Profile was initially read-only

The first R1 UI displayed extracted information and allowed confirmation, but did not provide a user correction workflow. R1 completion adds authenticated profile/item updates and UI editing so the user can correct AI output before treating it as authoritative.

## 5. R1 user workflow

```text
Upload resume
    ↓
Create durable Resume + ProcessingJob
    ↓
Celery worker executes r1-v1
    ↓
Store ResumeExtraction JSON
    ↓
Normalize career facts with source_resume_id
    ↓
Career Profile displays facts + evidence
    ↓
User edits incorrect facts
    ↓
Save corrections
    ↓
Confirm profile
    ↓
Confirmed records become authoritative
    ↓
Profile content hash marks embedding as pending
```

## 6. Provenance model

Every extracted experience, education, project, certification, and user skill can retain `source_resume_id`. The R1 API resolves those IDs to the user's uploaded resume metadata and exposes the filename as evidence in the UI.

The raw extraction remains in `resume_extractions.extracted_data`, providing an audit snapshot independent of the normalized career tables.

## 7. Confirmation model

Confirmation is intentionally separate from extraction. AI output is provisional. A user can review and correct it. Once confirmed, the profile and individual career records are marked user-confirmed. Automatic R1 processing must not silently overwrite those records.

## 8. Embedding foundation

R1 establishes a one-row-per-user `career_profile_embeddings` table containing:

- canonical profile `content_hash`
- embedding model identifier
- dimensions
- lifecycle status (`pending`, `ready`, `failed`)
- optional JSON embedding payload
- timestamps

R1 does not pretend that a production embedding model has been selected. The content hash provides deterministic invalidation and gives R2 a clean seam for plugging in a real embedding provider/vector type.

## 9. Testing strategy

R1 tests cover:

- education normalization aliases
- date normalization
- profile update validation
- item update validation and ownership
- confirmation behavior
- embedding content-hash invalidation
- protection of confirmed profiles during subsequent extraction
- API authentication boundaries

The local Docker acceptance test should verify:

1. `docker compose up -d --build`
2. `docker compose exec api alembic upgrade head`
3. API `/health` returns 200.
4. Login succeeds.
5. Resume upload returns 202.
6. Celery job reaches `succeeded`.
7. R1 extraction contains structured counts.
8. Career Profile displays evidence.
9. A user correction survives page reload.
10. Confirmation marks the profile authoritative.
11. A later resume does not overwrite the confirmed correction.
12. The embedding row is `pending` with a changed content hash after a confirmed edit.

## 10. Design decisions

### Evidence versus truth

The resume is evidence; the Career Profile is the product state. This prevents repeated AI extraction from becoming an uncontrolled source of truth.

### Explicit confirmation

A user confirmation boundary makes the system explainable and gives R2 a stable input profile.

### Database-native embedding foundation

R1 keeps the embedding metadata in PostgreSQL without forcing pgvector or a specific provider before R2 requirements are known.

### Versioned extraction

`r1-v1` is persisted with each extraction so parser/model behavior can be reproduced and future extractor versions can coexist.

## 11. R1 definition of done

R1 is complete when the user can upload a resume, inspect extracted career facts and their evidence, correct those facts, save them, confirm the profile, reload it without losing corrections, and trust that subsequent automatic resume processing will not silently replace confirmed data. The embedding foundation must also produce deterministic invalidation metadata for future semantic search.

## 12. R2 boundary

R2 starts only after the above workflow passes end-to-end. R2 can then use the confirmed Career Profile to implement target-role intelligence, skill-gap analysis, and eventually semantic retrieval against the embedding representation.
