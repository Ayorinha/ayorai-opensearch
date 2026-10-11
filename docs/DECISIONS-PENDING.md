# Pending Decisions

This file records decisions that require explicit maintainer approval. It is a queue, not an approval record. No item below authorizes implementation or changes to an accepted ADR by itself.

Owner and final decision-maker: Anderson Leon Ayora  
Independent reviewer: Cláudio  
Source: AYORAI ATTRACTOR Prompt Mestre v4.1, execution queue

## DEC-001 — F3.5: uv lockfile and Docker image digests

- **Status:** Pending maintainer decision
- **Decision area:** Reproducible builds and software supply-chain controls
- **Question:** Should the project adopt a committed `uv.lock` and pin Docker base images by immutable digest?
- **Context:** A lockfile and image digests can improve repeatability and auditability, but introduce explicit update and maintenance work. A digest pin must be paired with a documented update process.
- **Options to evaluate:**
  1. Adopt both the `uv` lockfile and digest-pinned Docker base images.
  2. Adopt the lockfile first and defer Docker digest pinning.
  3. Defer both until the reproducibility workflow and maintenance policy are specified.
- **Impact to assess:** Developer setup, CI, container builds, security updates, reproducibility instructions, and dependency-update cadence.
- **Approval gate:** Anderson selects an option; Cláudio reviews the implementation proposal before any implementation PR.

## DEC-002 — F4.2: licensing and provenance of source material

- **Status:** Pending maintainer decision
- **Decision area:** Source licensing, permissions, provenance, and evaluation-data governance
- **Question:** What acceptance policy must each external source satisfy before its material is included in evaluation fixtures, examples, or distributable datasets?
- **Context:** Source attribution alone does not establish permission to redistribute content. Each source may have different copyright, license, terms-of-use, privacy, and retention constraints.
- **Options to evaluate:**
  1. Require a recorded license or explicit permission and provenance metadata for every source; exclude sources with unresolved redistribution rights.
  2. Permit documented exceptions for material used only as non-distributed test input, subject to legal and policy review.
  3. Separate public distributable fixtures from privately held evaluation material, with distinct controls and manifests.
- **Impact to assess:** Redistribution rights, benchmark reproducibility, privacy, provenance fields, CI enforcement, and maintenance of source manifests.
- **Approval gate:** Anderson approves the policy after reviewing the legal and technical implications; no source is presumed licensed by this entry.

## DEC-003 — M1: ADR-001 status transition to Accepted

- **Status:** Pending maintainer decision
- **Decision area:** Architecture decision governance
- **Question:** Is ADR-001 accurate and sufficiently implemented to change its status to `Accepted`, or must its scope and evidence be revised first?
- **Context:** A status label must reflect an explicit decision and the implementation/evidence actually available. This queue entry does not alter ADR-001 or presume acceptance.
- **Options to evaluate:**
  1. Mark ADR-001 `Accepted` after confirming its decision, scope, consequences, and supporting evidence.
  2. Keep its current status and revise the ADR or implementation evidence before reconsideration.
  3. Supersede it with a new ADR if the original decision is no longer appropriate, preserving historical traceability.
- **Impact to assess:** Architectural consistency, traceability, links from implementation and tests, and the audit history of decisions.
- **Approval gate:** Anderson explicitly approves the status change; Cláudio checks the exact ADR diff and its references.

## DEC-004 — M3: commercial documentation and repository name

- **Status:** Pending maintainer decision
- **Decision area:** Public positioning, product documentation, and repository identity
- **Question:** Which commercial-facing documentation is appropriate now, and should the repository name remain `ayorai-opensearch` or be changed?
- **Context:** Commercial material must accurately describe verified capabilities, limitations, evaluation results, licensing, and maturity. Repository renaming affects URLs, badges, integrations, documentation links, and external references.
- **Options to evaluate:**
  1. Keep `ayorai-opensearch` and update commercial documentation without implying capabilities not demonstrated by tests.
  2. Approve a new repository name and coordinate redirects, references, badges, and documentation in a dedicated change.
  3. Defer the naming decision and publish only technical documentation until positioning is approved.
- **Impact to assess:** Public discoverability, continuity of repository links, brand consistency, technical accuracy, and maintenance burden.
- **Approval gate:** Anderson decides the name and positioning; Cláudio reviews factual claims and the documentation diff before publication.

## Queue rules

- These are pending decisions, not accepted architecture or authorization to implement.
- Record the selected option, rationale, date, and approving maintainer before changing an item to decided.
- Keep implementation in a separate PR unless the maintainer explicitly approves a documentation-only decision record.
- Do not claim legal clearance, production readiness, or performance beyond the evidence actually available.
