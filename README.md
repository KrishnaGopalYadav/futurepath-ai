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
- [R1 Final Acceptance](docs/architecture/r1-final-acceptance.md)

### Architecture Decisions

- [Master Architecture Decisions](docs/decisions/Final_DecisionDoc.md)
- [Release 1 Architecture Decision Record](docs/decisions/Release1_decisionDoc.md)

## Current Product Status

### R1 — Career Profile Intelligence
**Status: COMPLETE**

R1 is the first complete vertical slice of FuturePath AI. It establishes a durable, user-owned career profile from resume evidence.

The validated implementation supports:

- Password and Google authentication.
- PostgreSQL-backed user identity with stable UUIDs.
- PDF resume upload and validation.
- SHA-256 integrity verification.
- Private local file storage through a storage abstraction.
- Durable processing jobs.
- Redis + Celery asynchronous processing.
- PDF text extraction with pypdf.
- Structured extraction through an optional OpenAI-compatible call.
- Deterministic extraction fallback for local testing.
- Skill normalization.
- PostgreSQL persistence of summary, experiences, education, projects, certifications, skills and evidence.
- Resume provenance.
- Processing status and retry handling.
- Career profile review and correction.
- Explicit user confirmation.
- Protection of confirmed profile data from silent overwrite during later resume processing.
- An embedding persistence foundation with content hashing, model/version metadata and lifecycle state.

A real local extraction was validated with:

```text
31 skills
2 experiences
1 education
9 projects
3 certifications
status = succeeded
extractor_version = r1-v1
```

See [R1 Final Acceptance](docs/architecture/r1-final-acceptance.md) for the final gate and [R1 Complete Implementation](docs/architecture/r1-complete-implementation.md) for the detailed engineering history.

### R2 — Career Gap & Target Role Intelligence

**Next release.** R2 starts from the confirmed R1 profile rather than re-implementing resume ingestion.

Planned capabilities:

- Target role definition.
- Job-description / role requirement ingestion.
- Skill normalization and taxonomy mapping.
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
