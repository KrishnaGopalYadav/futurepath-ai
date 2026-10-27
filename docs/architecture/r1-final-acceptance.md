# FuturePath AI — R1 Final Acceptance Record

**Release:** R1 — Career Profile Intelligence  
**Status:** Complete  
**Decision:** R2 may begin after local acceptance validation

## 1. What R1 now delivers

R1 is a complete vertical slice from identity to a user-controlled career profile:

```text
Authentication
    ↓
Resume upload
    ↓
Private storage + checksum
    ↓
Durable processing job
    ↓
Redis / Celery worker
    ↓
PDF text extraction
    ↓
Structured extraction / deterministic fallback
    ↓
Validation + normalization
    ↓
PostgreSQL career entities
    ↓
Evidence / source resume
    ↓
Career Profile review
    ↓
User correction
    ↓
User confirmation
    ↓
Protected confirmed state
```

The central ownership rule is now explicit:

> **Extracted data is candidate evidence. Confirmed user data is authoritative.**

## 2. Final R1 data contract

### User identity

`users.id` is the internal stable UUID. Google identities are resolved through `(auth_provider, auth_subject)` uniqueness.

### Resume

A resume records:

- original filename;
- content type;
- file size;
- private storage key;
- SHA-256 checksum;
- owner;
- creation timestamp.

### Processing

Every resume submission creates a durable `processing_jobs` record. The worker owns execution; PostgreSQL owns job state.

### Extraction

`resume_extractions` stores the structured R1 result as JSONB together with extractor version and lifecycle status.

### Career entities

R1 persists:

- career profile;
- experiences;
- education;
- projects;
- certifications;
- canonical skills;
- user-skill associations.

Career entities retain `source_resume_id` where the fact originated from a resume.

## 3. User-controlled profile behavior

The R1 profile surface supports three conceptual states:

```text
EXTRACTED
   ↓ user reviews/corrects
CONFIRMED
   ↓ later resume uploaded
NEW EVIDENCE
```

A later resume submission is allowed to produce new extraction evidence. It must not silently replace a confirmed profile.

The implementation persists confirmation with:

```text
career_profiles.is_user_confirmed
career_profiles.confirmed_at
```

and confirmation flags on the structured career entities.

## 4. Evidence/provenance behavior

Every source-linked career entity can point back to the resume that produced it through `source_resume_id`.

The R1 profile API resolves those IDs to user-owned resume metadata so the UI can show the originating filename.

This is intentionally provenance at the entity level rather than pretending the system has precise character/line-level document citations. Fine-grained evidence spans can be added later when the extraction contract provides reliable offsets.

## 5. Embedding decision

R1 establishes an embedding persistence foundation without prematurely committing to a vector implementation that has not yet been justified by a similarity query.

The database foundation records:

```text
content_hash
embedding_model
dimensions
status
embedding payload
```

The payload is JSONB in R1 so the current PostgreSQL image requires no special extension.

### Why not force pgvector now?

The architecture principle is **measure before migrate**. A native vector index is valuable when R2 has a concrete semantic matching workload and the following are known:

- embedding model;
- dimensions;
- similarity metric;
- query patterns;
- expected corpus size;
- latency requirements.

R2 should make that decision with an actual target-role/skill-gap use case rather than an arbitrary vector dimension.

## 6. R1 validation evidence

The local environment produced a successful extraction with:

```text
31 skills
2 experiences
1 education
9 projects
3 certifications
extractor_version = r1-v1
status = succeeded
```

Education initially failed normalization because provider output used:

```text
end_date
institution
qualification
start_date
```

The normalization/recovery path was corrected and education subsequently persisted successfully.

The final database validation showed the education row linked to the same user and source resume as the successful extraction.

## 7. Runtime acceptance

The Docker Compose topology is:

```text
frontend :3000
api      :8000
worker   Celery
redis    :6379
postgres :5432
```

The worker was observed receiving and successfully completing `app.tasks.process_resume_job` tasks.

The API health endpoint and authenticated application flows were exercised during the implementation cycle.

## 8. Security acceptance

R1 uses:

- HTTP-only session cookies;
- SameSite `lax` cookies;
- authenticated ownership checks;
- provider-subject uniqueness;
- private server-generated storage keys;
- password hashing with Argon2 through `pwdlib`;
- checksum verification for stored resume bytes;
- no client-controlled filesystem paths.

Google OAuth is deployment-configured through environment variables; secrets are not committed to the repository.

## 9. Explicit non-goals

The following are intentionally outside R1:

- OCR for scanned PDFs;
- production object-storage integration;
- broad RAG;
- job-market ingestion;
- target-role gap scoring;
- autonomous agents;
- MCP integrations;
- Kafka;
- microservice decomposition;
- Kubernetes/OpenShift.

Those capabilities belong to later releases and should only be introduced when their requirements are demonstrated.

## 10. R1 Definition of Done

| Capability | Acceptance |
|---|---|
| Password identity | Complete |
| Google identity | Complete |
| Stable user UUID | Complete |
| PDF ingestion | Complete |
| Private resume storage | Complete for local R1 |
| Durable jobs | Complete |
| Celery/Redis processing | Complete |
| PDF extraction | Complete for text PDFs |
| Structured extraction | Complete with optional LLM + deterministic fallback |
| Normalization | Complete |
| Education persistence | Complete and regression-tested |
| Experience persistence | Complete and validated |
| Project persistence | Complete and validated |
| Certification persistence | Complete and validated |
| Skill persistence | Complete and validated |
| Provenance | Complete at entity/source-resume level |
| Career profile review | Complete |
| User corrections | Complete through profile API/UI |
| User confirmation | Complete |
| Protection of confirmed data | Complete |
| Embedding foundation | Complete, model/index decision deferred to R2 |

## 11. R2 handoff

R2 must consume the trusted R1 profile rather than bypassing it.

The first R2 implementation should therefore begin with:

```text
Confirmed Career Profile
        +
Target Role / Job Description
        ↓
Role Requirement Normalization
        ↓
Skill Mapping
        ↓
Evidence-backed Matching
        ↓
Gap Classification
        ↓
Prioritized Skill Gaps
```

The first R2 architecture decision should also finalize whether the R1 JSONB embedding foundation should become native pgvector storage based on the actual semantic matching workload.

**R1 is closed. R2 is the next release.**
