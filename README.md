# FuturePath AI

> Personal Career & Future Intelligence Platform

## Vision

Given who I am today, what is happening in the market,
where am I falling short, what should I learn next,
and which opportunities are relevant to me?

## Product

FuturePath AI connects a person's current capabilities, career goals, market intelligence, skill gaps, and next actions.

- Career Profile
- Skill Intelligence
- Job Market Intelligence
- Skill Gap Analysis
- Personalized Learning
- Career Assistant

## Documentation

### Product

- [Product Vision](docs/product/1-product-vision.md)
- [Problem Statement](docs/product/2-problem-statement.md)
- [Personas](docs/product/3-personas.md)
- [Use Cases](docs/product/4-use-cases.md)
- [Functional Requirements](docs/product/5-functional-requirements.md)
- [Non Functional Requirements](docs/product/6-non-functional-requirements.md)

### Architecture

- [Architecture v0.1](docs/architecture/architecture-v0.1.md)
- [HLD Roadmap](docs/architecture/HLD_roadmap.md)
- [Final End-to-End HLD](docs/architecture/Final_HLD.md)
- [Phase 1 Database LLD](docs/architecture/phase-1-database-lld.md)
- [R1 Implementation Status](docs/architecture/r1-implementation-status.md)
- [R1 Complete Implementation](docs/architecture/r1-complete-implementation.md)

### Architecture Decisions

- [Master Architecture Decisions](docs/decisions/Final_DecisionDoc.md)
- [Release 1 Architecture Decision Record](docs/decisions/Release1_decisionDoc.md)

## Current Product Status

### R1 — Career Profile Intelligence
**Status: Processing foundation validated; final R1 product-surface hardening in progress**

The R1 processing engine is working end-to-end locally. The current implementation supports:

- Password and Google authentication.
- PostgreSQL-backed user identity with stable UUIDs.
- PDF resume upload and validation.
- SHA-256 integrity and same-user duplicate suppression.
- Private local file storage.
- Durable processing jobs.
- Redis + Celery asynchronous processing.
- PDF text extraction with pypdf.
- Structured extraction through an optional OpenAI-compatible call.
- Deterministic extraction fallback for local testing.
- Skill normalization.
- PostgreSQL persistence of summary, experiences, education, projects, certifications, skills and evidence.
- Resume provenance.
- Processing status and retry handling.

A real local extraction test has been validated with 31 skills, 2 experiences, 1 education record, 9 projects and 3 certifications.

### Remaining R1 acceptance work

Before R2 begins, finish the career profile as a trustworthy user-controlled surface:

- Display extracted career data clearly.
- Expose evidence/provenance.
- Allow corrections and confirmation.
- Persist confirmed user edits.
- Prevent later resume reprocessing from silently overwriting confirmed edits.
- Finalize the embedding foundation, or document an explicit decision to remove embeddings from the R1 acceptance criteria.

See [R1 Complete Implementation](docs/architecture/r1-complete-implementation.md) for the implementation history, issues encountered, fixes, architecture decisions, trade-offs and interview preparation.

## Release Roadmap

```text
R1 — Career Profile Intelligence
        ↓
R2 — Career Gap & Target Role Intelligence
        ↓
R3 — Market + Learning Intelligence
        ↓
R4 — Continuous Personal Career Intelligence
```

### R2 — Career Gap & Target Role Intelligence

R2 starts only after the R1 acceptance gate is closed.

Planned capabilities:

- Target role definition.
- Job-description / role requirement ingestion.
- Skill normalization.
- Exact + semantic matching.
- Deterministic gap scoring.
- Strong / partial / adjacent / missing / unknown classifications.
- Evidence-backed gap explanations.
- Prioritized skill gaps.

### R3 — Market + Learning Intelligence

Planned capabilities:

- Market job ingestion.
- Market skill taxonomy.
- Market trends and role clustering.
- Learning-resource ingestion.
- Multi-domain filtered RAG.
- Personalized learning recommendations.
- Semantic caching when measured demand justifies it.

### R4 — Continuous Personal Career Intelligence

Potential capabilities, introduced only when justified:

- Feedback-driven recommendation learning.
- Career outcome tracking.
- Autonomous workflows.
- Agents.
- MCP/tool integrations.
- Event-driven architecture.
- Kafka.
- Independently deployed services.
- Kubernetes/OpenShift.
- Dedicated vector infrastructure.

## Architecture Principle

FuturePath follows a **measure-before-migrate** approach.

Technology should follow demonstrated requirements rather than precede them.

> **Build the simplest architecture that works today. Measure it in reality. Evolve it when the evidence says it is time.**
