# FuturePath AI — Release 1 Complete Implementation

**Release:** R1 — Career Profile Intelligence  
**Document type:** Implementation history, engineering record, design-decision and interview-preparation document  
**Status:** Implementation record  
**Repository:** `KrishnaGopalYadav/futurepath-ai`

---

## 1. Executive summary

Release 1 answers one foundational product question:

> **What do we understand about my career today?**

R1 started as a login-and-resume-ingestion MVP and evolved into a durable career-profile pipeline. The implementation established authentication, PostgreSQL-backed user identity, resume ingestion, private file storage, Redis/Celery asynchronous processing, PDF extraction, structured career extraction, deterministic fallback parsing, validation, normalization, provenance, and persistence of career entities.

The most important engineering principle was:

> **AI proposes candidate career data; deterministic application code validates, normalizes, authorizes and persists system state.**

The implementation was validated locally using Docker Compose with PostgreSQL, Redis, FastAPI, Celery and the frontend. Real resume processing was verified end-to-end, including successful persistence of 31 skills, 2 experiences, 1 education record, 9 projects and 3 certifications for a test resume.

R1 is therefore **not a blank MVP anymore**. The processing engine is proven. The remaining R1 work is the user-controlled career-profile product surface: clear display, evidence/provenance presentation, corrections, confirmed-state persistence and protection of manual corrections during reprocessing. The embedding foundation must also be either completed with an explicitly selected model/design or formally removed from the R1 acceptance criteria.

R2 should start only after that R1 acceptance gate is closed.

---

# 2. Product context

FuturePath AI is a personal career and future intelligence platform. The broader product loop is:

```text
Know Me
   ↓
Understand the Market
   ↓
Identify Gaps
   ↓
Recommend Actions
   ↓
Measure Progress
   ↓
Know Me again
```

R1 is intentionally the **Know Me** foundation. R2 will use the resulting profile to answer:

> **What am I missing for a target role?**

The master HLD defines the progressive release model as R1 Career Profile Intelligence → R2 Career Gap & Target Role Intelligence → R3 Market & Learning Intelligence → R4 Continuous Personal Career Intelligence.

---

# 3. How we started R1

The project began from an architectural/product-design phase rather than immediately implementing every advanced AI capability.

The design documents established the following baseline:

- Next.js / React frontend.
- FastAPI + Python backend.
- Modular-monolith application architecture.
- PostgreSQL as the transactional system of record.
- Redis + Celery for asynchronous work.
- pypdf/pdfplumber for PDF processing.
- Structured JSON output with Pydantic validation.
- Docker Compose for reproducible local development.
- SQLAlchemy + Alembic for persistence and migrations.
- GitHub Actions as the CI/CD baseline.
- pgvector as the eventual vector capability when a concrete embedding use case and model are finalized.

The architecture documents explicitly argued for progressive evolution instead of deploying the eventual R4 architecture immediately. RAG, agents, MCP, Kafka, microservices and Kubernetes were therefore treated as later capabilities with measurable change triggers rather than R1 prerequisites.

---

# 4. R1 implementation sequence

The implementation evolved through the following practical sequence.

## Step 1 — Authentication foundation

The first usable MVP requirement was a secure login experience with two paths:

```text
Username / Password
        OR
Google OAuth
```

The application was then moved to a PostgreSQL-backed identity model rather than keeping user identity only in application memory or frontend state.

### Result

The `users` table became the durable application identity source.

Important identity fields include:

```text
id
username
email
password_hash
is_active
auth_provider
auth_subject
created_at
updated_at
```

The critical uniqueness rule is:

```text
(auth_provider, auth_subject) UNIQUE
```

This means the provider's stable subject identifies the external account while the application UUID identifies the internal user.

### Why this design?

Email is useful profile information but should not be the sole identity key. Provider + subject gives a stable identity boundary and allows multiple authentication providers without creating duplicate internal users.

### Validation performed

A Google-authenticated test user was persisted into PostgreSQL and subsequent Google login resolution was verified against the same user identity rather than creating another account.

---

# 5. Step 2 — PostgreSQL data foundation

The relational career model was implemented around a single internal user identity.

Core entities include:

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

The relationships establish ownership and provenance.

For example:

```text
users
  │
  ├── resumes
  │      └── processing_jobs
  │      └── resume_extractions
  │
  └── career_profiles
         ├── experiences
         ├── education
         ├── projects
         ├── certifications
         └── user_skills
```

### Why PostgreSQL?

The domain is relational. Users own resumes and profiles; profiles contain structured entities; skills are normalized and associated with users; processing jobs have lifecycle state. PostgreSQL gives us ACID transactions, foreign keys, unique constraints and queryability in one primary persistence boundary.

### Important principle

PostgreSQL is the source of truth. Redis messages, worker memory and LLM responses are not authoritative business state.

---

# 6. Step 3 — Resume ingestion

The resume API was implemented as a durable ingestion boundary.

The flow became:

```text
User
 ↓
POST /resumes
 ↓
Validate upload
 ↓
Calculate SHA-256
 ↓
Generate private storage key
 ↓
Persist resume metadata
 ↓
Create processing job
 ↓
Return 202 Accepted
```

### Upload constraints

- PDF-only input.
- 10 MB default limit.
- Client filename retained as metadata, not as a filesystem path.
- Server-generated storage keys.
- SHA-256 checksum for integrity and same-user duplicate suppression.

### Why store files outside PostgreSQL?

The PDF is a binary artifact rather than relational business state. Keeping bytes in private file storage avoids unnecessarily increasing database and backup size and leaves a clean path toward object storage later.

### Security principle

A client-supplied filename is never trusted as a storage path.

---

# 7. Step 4 — Asynchronous resume processing

PDF parsing and AI extraction can take materially longer than an ordinary API request. Processing them synchronously would tie up API workers and make the user wait.

The architecture therefore introduced:

```text
FastAPI
   ↓
Redis
   ↓
Celery
   ↓
Worker
```

### Durable job model

`processing_jobs` records persist the lifecycle independently of Celery's in-memory execution state.

Supported states include:

```text
queued
running
succeeded
failed
cancelled
```

The worker uses bounded retries with backoff for retryable failures.

### Why Celery + Redis?

We needed:

- queue buffering;
- independent worker processes;
- retries;
- controlled concurrency;
- horizontal worker scaling.

Kafka was deliberately deferred because R1 has a job-processing problem, not an enterprise event-streaming problem requiring replay and multiple independent consumers.

---

# 8. Step 5 — PDF text extraction

The worker reads the private stored PDF and extracts text using `pypdf`.

Conceptually:

```text
Stored PDF
   ↓
pypdf
   ↓
Extracted text
   ↓
Normalization
```

The implementation also cleans problematic characters and whitespace before parsing.

A checksum is re-verified when the worker reads the stored file, protecting the pipeline from accidental file corruption or mismatch.

### OCR decision

OCR was deliberately not made a default dependency. Scanned/image-only PDFs can require OCR, but adding OCR infrastructure before observing real demand would increase cost and complexity.

OCR remains a demand-driven follow-up.

---

# 9. Step 6 — Structured career extraction

After text extraction, the worker produces a structured career candidate.

The intended AI path is:

```text
Resume text
   ↓
Structured LLM call
   ↓
JSON candidate
   ↓
Validation
   ↓
Normalization
   ↓
Persistence
```

The structured result contains concepts such as:

- summary;
- headline;
- experiences;
- education;
- skills;
- projects;
- certifications.

The LLM is explicitly instructed not to invent facts and to provide evidence notes for skills where supported.

### Why structured output?

Free-form text is difficult to validate and persist safely. A schema-constrained result makes the boundary between probabilistic AI and deterministic application logic explicit.

The core rule is:

> **Never allow raw LLM output to become database state without validation and normalization.**

---

# 10. Step 7 — Deterministic fallback

A local development path was needed even when an OpenAI API key was not configured.

The implementation therefore added a conservative deterministic parser for text-based resumes.

It can identify structured sections such as:

```text
PROFESSIONAL SUMMARY
TECHNICAL SKILLS
PROFESSIONAL EXPERIENCE
EDUCATION
PROJECTS
CERTIFICATIONS
```

and extract basic structured entities from recognizable patterns.

### Why?

This keeps the ingestion and job pipeline testable without making local development completely dependent on an external AI provider.

### Important limitation

The fallback is intentionally conservative. It is not claimed to equal semantic LLM extraction. It is a resilience/development path, not the final intelligence engine.

---

# 11. Step 8 — Validation and normalization

AI output is treated as untrusted candidate data.

The persistence layer validates and normalizes it before writing relational state.

Examples:

- dates are parsed into database date values;
- missing values remain nullable instead of being invented;
- experience aliases such as `company` / `company_name` can be normalized;
- education aliases are accepted;
- skills are normalized deterministically using case/whitespace normalization;
- invalid or incomplete entities are skipped or rejected according to domain rules.

### Why deterministic normalization?

The same skill should not become several database records merely because an LLM produced different casing or spacing.

For example:

```text
Python
python
 Python 
```

should resolve to the same normalized skill identity.

---

# 12. Step 9 — Provenance and evidence

R1 was designed around the principle:

```text
Fact
 ↓
Evidence
 ↓
Inference
 ↓
Recommendation
```

Resume-derived entities retain `source_resume_id`.

Skills additionally retain evidence notes where available.

This is important because career intelligence must be explainable. A user should eventually be able to ask:

> Why does FuturePath think I have this skill?

and trace the answer to source evidence.

---

# 13. Step 10 — Persistence

After validation and normalization, the worker persists the structured profile in PostgreSQL.

The implementation creates/updates the user's career profile and persists source-linked records for:

```text
Experience
Education
Project
Certification
UserSkill
```

Skill records are canonicalized through the `skills` table and associated with the user through `user_skills`.

The extraction itself is also recorded in `resume_extractions` with:

```text
extractor_version = r1-v1
status = succeeded / failed / pending
extracted_data = JSONB
```

### Transaction principle

Profile-related writes should succeed as a coherent database operation. A persistence error must not leave half-created career data as if extraction succeeded.

Slow external operations should happen outside a long-lived database transaction.

---

# 14. Step 11 — Career profile API and UI

The career page became the application surface for the extracted profile.

The user can:

- access the career page after authentication;
- upload a resume;
- see processing state;
- retry eligible failures;
- review/correct career information.

The API performs ownership checks using the authenticated internal user identity.

### Important remaining product hardening

The architecture documents are stronger than the current UI in one important respect: the final R1 surface should make evidence/provenance visible and should distinguish extracted candidate data from user-confirmed data.

That distinction must be completed before R2.

---

# 15. Step 12 — Dockerized local environment

R1 was made reproducible through Docker Compose.

The validated local service topology is:

```text
                 ┌──────────────┐
                 │   Frontend   │ :3000
                 └──────┬───────┘
                        │
                        ▼
                 ┌──────────────┐
                 │     API      │ :8000
                 └──────┬───────┘
                        │
             ┌──────────┴──────────┐
             ▼                     ▼
          Redis                 PostgreSQL
             │                     │
             ▼                     │
          Celery ──────────────────┘
          Worker
```

The Compose environment was tested through actual container startup, API access, worker readiness and PostgreSQL queries.

---

# 16. Real implementation problems and how we solved them

This section is intentionally detailed because these failures are part of the engineering record.

## 16.1 Git remote / repository confusion

At one point the local repository pointed to a different remote repository than the intended working fork.

### Lesson

Always verify:

```bash
git remote -v
git status
git log --oneline -5
```

before pushing or synchronizing branches.

We subsequently established the fork as `origin` and Akash's repository as the upstream/source-of-truth relationship.

---

## 16.2 PostgreSQL container-name conflict

Compose reported:

```text
Conflict. The container name "/futurepath-db" is already in use
```

### Cause

A previous PostgreSQL container already owned the explicit container name.

### Lesson

Explicit `container_name` values create naming collisions across Compose projects. Container lifecycle must be managed carefully, or service-scoped Compose names can be preferred.

---

## 16.3 Alembic configuration path error

Running Alembic with the wrong in-container path produced:

```text
FAILED: No 'script_location' key found in configuration.
```

The local file was valid, but the command referenced a path/layout that did not exist inside the container.

### Lesson

Always distinguish:

```text
host filesystem
vs
container filesystem
```

Docker build context and `WORKDIR` determine what paths exist inside the image.

---

## 16.4 Missing `/app/backend`

The container did not contain `/app/backend` because the Dockerfile uses `/app` as the working directory and copies the application package into `/app/app`.

The relevant pattern is:

```text
WORKDIR /app
COPY app ./app
```

Therefore:

```text
/app/app
```

contains the Python package, not `/app/backend`.

### Lesson

Never infer container paths from repository paths. Inspect the Dockerfile and image layout.

---

## 16.5 `ModuleNotFoundError: app.config`

Alembic initially failed with:

```text
ModuleNotFoundError: No module named 'app.config'
```

Inspection of `sys.path` showed that `/app` was not available to Python in the failing invocation.

The application layout and invocation were reconciled so that the package is importable as:

```text
app.config
```

### Lesson

Python import problems inside containers are often path/layout problems rather than missing source files. Verify `WORKDIR`, `COPY`, `sys.path` and package initialization together.

---

## 16.6 API and worker import failure

The API and worker entered restart loops after:

```text
ImportError: cannot import name 'process_resume' from 'app.resume_processing'
```

### Cause

The Celery task expected a processing entry point that did not match the current `resume_processing.py` implementation.

### Resolution

The R1 processing entry point was restored so the Celery task could invoke the extraction/persistence pipeline.

### Result

Both API and worker became healthy and the worker registered:

```text
app.tasks.process_resume_job
```

---

## 16.7 Initial extraction persisted zero structured entities

A test extraction succeeded but produced:

```text
skills = 0
experiences = 0
education = 0
projects = 0
certifications = 0
```

while the raw extracted text clearly contained career information.

### Cause

The no-AI-key deterministic path preserved the text but did not initially provide enough structured parsing.

### Resolution

A conservative deterministic extraction path was implemented for recognizable resume sections and patterns.

### Lesson

A successful processing job does not necessarily mean a successful product outcome. We must validate the **semantic payload**, not only the queue/job status.

---

## 16.8 Education extraction normalization failure

The worker initially retried with:

```text
R1 education item could not be normalized; received keys:
['end_date', 'institution', 'qualification', 'start_date']
```

### Cause

The extractor's education representation and the persistence normalizer did not agree on field aliases/shape.

### Resolution

Education normalization was made alias-aware and tolerant of nested provider-style values. The persistence path now recognizes fields such as institution, qualification/degree, field of study and date variants.

### Result

A subsequent validated extraction produced and persisted:

```text
institution = University of Pune
qualification = B.Tech in Computer Science and Engineering
start_date = 2017-01-01
end_date = 2021-01-01
```

The database then showed a persisted education row linked to the source resume.

### Lesson

Schema contracts must be tested against actual model output, not only idealized examples.

---

## 16.9 Validation query/schema mismatch

Some validation queries assumed fields that were not present in the actual schema, such as:

```text
resumes.status
resume_extractions.raw_text
```

The actual schema instead keeps processing state in `processing_jobs` and extracted content in `resume_extractions.extracted_data` JSONB.

### Lesson

When validating a live system, inspect the actual database schema first and then formulate queries against the implemented contract.

---

## 16.10 Duplicate resume testing

The same PDF was uploaded multiple times during testing.

The resulting database contained multiple resume IDs for the same checksum across repeated tests.

The intended invariant is **same-user duplicate suppression**, not global deduplication across all users. Global deduplication would create a privacy side channel because one user could potentially infer that another user uploaded the same document.

### Lesson

Idempotency must be defined with an explicit scope. For private career documents, the owner boundary matters as much as the checksum.

---

# 17. Design decisions taken in R1

## 17.1 Modular monolith instead of microservices

### Decision

Use FastAPI as a modular monolith.

### Why

R1 boundaries are still evolving. Microservices would add network calls, distributed tracing, deployment complexity and consistency problems before independent deployment or scaling is demonstrably required.

### Evolution trigger

Extract a service only when independent deployment, scaling, ownership, runtime or failure isolation becomes measurable and valuable.

---

## 17.2 Redis + Celery instead of synchronous processing

### Decision

Use Redis as the broker and Celery workers for resume processing.

### Why

PDF/LLM work is long-running relative to normal HTTP handling. The queue protects the API and provides retries and worker scaling.

### Rejected for R1

- FastAPI `BackgroundTasks`: same-process and weaker durability/recovery semantics.
- Kafka: event-streaming capability exceeds the immediate R1 requirement.

---

## 17.3 PostgreSQL instead of a document database

### Decision

PostgreSQL is authoritative.

### Why

Career information is relational and requires ownership, constraints, transactions and joins. PostgreSQL also provides a path to pgvector without introducing another persistence system.

---

## 17.4 Local private file storage instead of immediate object storage

### Decision

Use a storage abstraction with a Docker-mounted local implementation.

### Why

It keeps local development simple while preserving an interface that can later point to production object storage.

---

## 17.5 Structured LLM output instead of free-form generation

### Decision

Use structured JSON/schema output and validate before persistence.

### Why

Structured output is easier to validate, test, normalize and persist. It also makes model errors explicit instead of allowing prose to silently become data.

---

## 17.6 Deterministic logic around the LLM

### Decision

Use the LLM for semantic extraction, but use application code for validation, normalization, ownership, persistence and state transitions.

### Why

Those operations need reproducibility and predictable invariants.

---

## 17.7 Evidence/provenance

### Decision

Keep source-resume relationships and skill evidence notes.

### Why

FuturePath is supposed to provide explainable career intelligence, not opaque scores. Provenance also enables user correction and later evaluation.

---

## 17.8 No OCR by default

### Decision

Use text extraction first and introduce OCR only when real resume samples justify it.

### Why

OCR adds processing cost and another failure mode. There was no evidence yet that scanned documents were common enough to justify making it mandatory.

---

## 17.9 No RAG in R1

### Decision

R1 remains focused on building the user's structured career state.

### Why

R1 has a source-document extraction problem rather than a broad external-knowledge retrieval problem. RAG becomes much more valuable when role, market and learning knowledge domains exist.

---

## 17.10 No agents in R1

### Decision

Use deterministic workflows.

### Why

There is no genuine autonomous multi-step planning requirement yet. Agents would increase cost, non-determinism and testing complexity without solving an R1 problem.

---

## 17.11 No Kafka in R1

### Decision

Redis/Celery is enough for the initial job workflow.

### Why

Kafka becomes valuable when durable event history, replay, multiple consumers or high event volume becomes an actual requirement.

---

## 17.12 No Kubernetes in R1

### Decision

Docker Compose for local development and R1 validation.

### Why

Kubernetes solves production orchestration problems that do not yet exist at the local MVP scale.

---

# 18. R1 architecture after implementation

```text
                         USER
                           │
                           ▼
                    Next.js / React
                           │
                           ▼
                   FastAPI application
                    (modular monolith)
                     │            │
                     │            └───────────────┐
                     ▼                            ▼
                   Redis                      PostgreSQL
                     │                       (source of truth)
                     ▼                            │
               Celery Worker                     │
                     │                            │
             ┌───────┼────────┐                   │
             ▼       ▼        ▼                   │
           PDF     LLM     Validation              │
             │       │        │                    │
             └───────┴────────┘                    │
                       │                            │
                       ▼                            │
                Normalization                       │
                       │                            │
                       └──────────────┬─────────────┘
                                      ▼
                              Career profile data
```

The production architecture can later add embeddings, RAG, market data and learning data without making those components part of the R1 critical path.

---

# 19. Data consistency model

The R1 system intentionally separates three categories:

### Source artifact

The uploaded resume PDF and its checksum/storage metadata.

### Extracted candidate data

The versioned `resume_extractions.extracted_data` JSONB and source-linked relational entities.

### User-controlled confirmed data

The career profile state that the user has reviewed and explicitly corrected or confirmed.

This separation is essential for the next R1 step. A future reprocessing operation must not blindly replace confirmed user edits.

---

# 20. Testing strategy used

Testing was performed as an end-to-end local system rather than only as isolated unit code.

## Infrastructure validation

```bash
docker compose ps
docker compose logs api
docker compose logs worker
```

Expected:

```text
API      Up / healthy
Worker   ready
Postgres healthy
Redis    healthy
Frontend available
```

## Authentication validation

Validated both password and Google login paths, including stable identity resolution for Google users.

## Resume ingestion validation

Verified:

- PDF upload accepted.
- Resume metadata persisted.
- Processing job persisted.
- Worker received the task.
- Job reached `succeeded` for valid input.

## Extraction validation

The successful R1 test result demonstrated:

```text
skills          = 31
experiences     = 2
education       = 1
projects        = 9
certifications  = 3
```

## Database validation

Queries were adapted to the actual schema. `resume_extractions.extracted_data` was inspected as JSONB rather than assuming a separate raw-text column, and processing status was read from `processing_jobs` rather than an absent `resumes.status` column.

## Regression validation

After fixing education normalization, a new resume processing run produced a persisted education record and a successful extraction row.

---

# 21. What R1 taught us

## Lesson 1 — A job can succeed while the product result is wrong

A Celery `succeeded` state only means the task completed without raising its terminal exception. It does not prove the extracted career profile is complete or useful.

Therefore acceptance tests must validate semantic output counts and correctness, not just job status.

## Lesson 2 — AI output contracts need defensive normalization

Even structured model output can differ in optional fields or provider-specific representations. The persistence boundary needs explicit aliases and validation.

## Lesson 3 — Durable state and transient queues are different

Redis/Celery is execution infrastructure. PostgreSQL holds the durable business state required for recovery and auditability.

## Lesson 4 — User corrections must eventually outrank extraction

The product cannot continuously re-import a resume and overwrite information a user intentionally corrected.

## Lesson 5 — Architecture documents must be synchronized with implementation

The original design documents contain future-state capabilities such as embeddings, RAG and agents. They are architectural direction, not proof that every capability exists in code.

The implementation status document therefore separates **implemented**, **validated**, and **deferred** capabilities.

---

# 22. R1 definition of done

R1 is functionally ready for R2 when:

### Identity

- [x] Password login works.
- [x] Google login works.
- [x] Provider/subject uniqueness prevents duplicate external identities.
- [x] Repeat Google login resolves to the same internal UUID.

### Resume pipeline

- [x] PDF upload validation works.
- [x] Private storage works.
- [x] SHA-256 integrity/deduplication works within the user boundary.
- [x] Durable processing jobs exist.
- [x] Celery worker consumes jobs.
- [x] Retry behavior works.
- [x] PDF text extraction works.
- [x] Structured extraction works when configured.
- [x] Deterministic fallback works for local testing.
- [x] Extracted entities persist to PostgreSQL.

### Data quality

- [x] Experiences persist.
- [x] Education persists after normalization fix.
- [x] Projects persist.
- [x] Certifications persist.
- [x] Skills persist and normalize.
- [x] Source provenance is retained.

### User-controlled profile surface

- [ ] Extracted career data is presented cleanly as a profile.
- [ ] Evidence/provenance can be inspected by the user.
- [ ] User corrections persist as confirmed values.
- [ ] Reprocessing respects confirmed user corrections.
- [ ] Profile edits have explicit merge/replace semantics.

### Semantic foundation

- [ ] Embedding model/provider is selected.
- [ ] Vector dimension and similarity metric are documented.
- [ ] pgvector schema/index is implemented only if an actual R1/R2 feature needs it.
- [ ] Embedding regeneration semantics are tested.

R2 starts only after the unfinished R1 items are either implemented or explicitly removed from the R1 contract through a documented architecture decision.

---

# 23. What comes immediately after R1

The next engineering step is **not** RAG, agents, Kafka or Kubernetes.

It is to finish the career profile as a trustworthy user-controlled product surface:

```text
Extracted Data
      ↓
Career Profile UI
      ↓
Evidence / Provenance
      ↓
User Review
      ↓
Correction
      ↓
Confirmed State
      ↓
Safe Reprocessing
```

Once that is complete, R2 can begin with:

```text
Career Profile
      +
Target Role
      +
Role Requirements
      ↓
Hybrid Matching
      ↓
Gap Analysis
      ↓
Prioritized Gaps
```

---

# 24. Interview preparation — core questions

## Q1. Why did you choose a modular monolith?

**Answer:**

> R1's domain boundaries were still evolving. A modular monolith gives us logical separation without the operational cost of networked microservices. We can extract services later when independent deployment, scaling, ownership or failure isolation becomes a measurable requirement.

## Q2. Why asynchronous processing?

**Answer:**

> PDF extraction and LLM inference are long-running compared with normal API operations. Synchronous processing would hold HTTP workers and increase timeout risk. Redis and Celery let the API acknowledge ingestion quickly while workers process the durable job independently.

## Q3. Why PostgreSQL?

**Answer:**

> The career domain is relational. Users own profiles and resumes, profiles contain experiences and education, and skills are normalized and related to users. PostgreSQL gives us ACID transactions, foreign keys, uniqueness and queryability in one source of truth.

## Q4. Why not MongoDB?

**Answer:**

> MongoDB would be useful for flexible documents, but the core product needs relational integrity and joins. The structured career model benefits more from PostgreSQL's constraints and transactional semantics.

## Q5. Why use Redis and Celery rather than Kafka?

**Answer:**

> R1 has a background-job problem, not a durable event-stream problem. Redis/Celery gives buffering, retries and worker scaling with much lower operational complexity. Kafka becomes justified when replay, durable event history, multiple independent consumers or high event volume becomes material.

## Q6. Why not process the resume inside the API request?

**Answer:**

> Because PDF parsing and AI calls can be slow and failure-prone. Blocking the API would reduce throughput and make user-facing latency depend on external AI services.

## Q7. How did you make LLM output reliable?

**Answer:**

> The LLM returns structured candidate data. We validate it, normalize aliases and dates, enforce ownership and database constraints, and only then persist it. The model never gets to directly mutate system state.

## Q8. Why did education extraction fail?

**Answer:**

> The extractor returned an education object with `institution`, `qualification`, `start_date` and `end_date`, while the persistence normalizer did not initially handle that exact shape. We diagnosed it from the worker retry error, added alias-aware normalization, and verified the resulting education row in PostgreSQL.

## Q9. Why is provenance important?

**Answer:**

> Career intelligence affects personal decisions, so users need to understand why the system believes something about them. `source_resume_id` and evidence notes provide a foundation for traceability and correction.

## Q10. How do you prevent duplicate accounts for Google users?

**Answer:**

> We resolve the validated provider and stable subject into an internal UUID and enforce uniqueness on the provider/subject pair. Email is not the sole identity key. A repeated Google login therefore resolves to the existing user instead of creating a new account.

## Q11. What happens if the worker crashes?

**Answer:**

> The processing job is durable in PostgreSQL, while Celery handles execution and retries. The worker should be safe to run more than once for the same logical job, so persistence uses duplicate-safe operations and transaction boundaries.

## Q12. Why did we not implement OCR?

**Answer:**

> OCR is useful for scanned resumes, but it adds cost and complexity. We first support text-based PDFs and will add OCR when real resume samples demonstrate that scan coverage is a meaningful product requirement.

## Q13. Why did we not implement embeddings yet?

**Answer:**

> The architecture calls for semantic capabilities, but a production vector schema requires an actual embedding model, exact dimension, similarity metric and query use case. Adding a vector column without those decisions would create premature schema coupling. We will implement the embedding foundation when the feature contract is clear.

## Q14. Why no RAG in R1?

**Answer:**

> R1's primary problem is converting a user's resume into trustworthy structured career data. RAG becomes valuable when we have multiple external knowledge domains such as role requirements, market information and learning resources. That is why RAG is planned for a later release.

## Q15. Why no agents?

**Answer:**

> R1 workflows are deterministic. Agents introduce non-deterministic planning and tool selection, which would make the system harder to test and operate without solving a current product requirement.

## Q16. How would you scale this architecture?

**Answer:**

> First scale stateless API instances and Celery workers independently. Then measure PostgreSQL query and connection pressure. Only when evidence shows a bottleneck would we add read replicas, partitioning, dedicated vector infrastructure, Kafka or microservices.

---

# 25. R1 architecture story in 60 seconds

> “FuturePath AI R1 is a career-profile intelligence foundation. We chose a FastAPI modular monolith because the domain is evolving and we don't yet need distributed service boundaries. Resume ingestion is asynchronous because PDF and LLM processing are slow, so Redis and Celery decouple user requests from workers. PostgreSQL is the source of truth because the career domain is relational, while structured LLM output is treated as untrusted candidate data and validated before persistence. We store resumes privately outside the database and retain provenance back to the source resume. During implementation we had real issues with Docker paths, Alembic configuration, worker imports, deterministic extraction and education schema normalization; each was resolved through logs, schema inspection and end-to-end testing. We deliberately deferred OCR, RAG, agents, Kafka, microservices and Kubernetes until requirements justify them. The remaining R1 goal is to make the extracted profile fully user-controlled, evidence-backed and safe to reprocess. Then R2 can add target-role and skill-gap intelligence.”

---

# 26. Final R1 principle

> **R1 is successful when FuturePath can turn an untrusted resume document into durable, explainable, user-controlled career data without making the user wait for processing or allowing AI output to silently become truth.**

That foundation is what R2 should consume.
