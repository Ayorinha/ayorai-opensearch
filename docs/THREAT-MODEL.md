# ATTRACTOR Threat Model

## 1. Scope

ATTRACTOR protects the integrity of claim-level verification: caller-supplied claims are evaluated against a closed-world evidence set, stance is produced from evidence, provenance is retained, and the final verdict is selected by the deterministic Judge.

In scope:
- resistance to document/model text attempting to steer the final verdict;
- evidence identity, source metadata and provenance;
- deterministic verdict computation;
- replay integrity;
- evaluation-set isolation and license boundaries;
- CI and dependency supply-chain controls.

Out of scope:
- proving that an external source itself is truthful;
- securing the host, GitHub account, credentials, network or deployment environment;
- preventing a compromised upstream model or dependency from behaving maliciously;
- legal compliance or copyright clearance by the runtime itself;
- guaranteeing generalization beyond the evaluated data.

## 2. Assets

- Final deterministic Judge verdict.
- Evidence and provenance trail: source identifiers, locations, retrieval time, offsets, excerpts, hashes and stance provenance.
- Replay bundles and their content digests.
- Frozen Golden v0/v0.1 evaluation material and manifests.
- Hidden Golden v1, reserved for held-out Portuguese-document evaluation.
- Model weights, exact revisions, model metadata and license decisions.
- Evaluation and training-data manifests, including license status.

## 3. Threats and current controls

### A. Prompt injection

**Threat:** AI output or document text attempts to instruct the system to change the verification result, reveal evaluator material, or override the current question.

**Current defense:** The verification contract treats caller-supplied claims as authoritative input and does not derive claims from evidence. The final verdict is produced by the deterministic Judge; NLI, translation and rules produce only stance edges. Golden injection cases explicitly exercise instruction-like document text.

**Code:** `src/ayorai_attractor/verification/claim_pipeline.py`, `src/ayorai_attractor/verification/judge.py`; regression data in `evals/golden/v0.jsonl` and `evals/golden/v0.1.jsonl`.

### B. Forged citation

**Threat:** An AI supplies a citation or quoted passage that does not exist in the source document.

**Defense requirement:** The system must never accept an AI-provided citation as proof; evidence must be located in the original document and represented by validated source identity and offsets.

**Current defense:** The synthesis gate only accepts citation IDs that are present in the available evidence set. Evidence records carry source identity, source location, canonical URL where available, retrieval time and offsets.

**GAP:** The current verification core does not independently re-open the original source and verify that the cited excerpt exactly matches the source content at the recorded offsets. A caller can construct an Evidence record containing an invented excerpt while satisfying the schema.

**Code:** `src/ayorai_attractor/synthesis.py`, `src/ayorai_attractor/verification/models.py`, `src/ayorai_attractor/verification/claim_pipeline.py`.

### C. Wrong provenance in translated documents

**Threat:** Translation changes character positions and a winning NLI window is recorded against translated text rather than the original source.

**Current defense:** The translated stance path records translation provenance separately; the audit trail retains the original source excerpt. Evidence windows are based on the Evidence offsets, and regression coverage exists for translated stance provenance. The project records a known limitation that translated evidence currently points to the original evidence as a whole rather than a sentence-level aligned span.

**Code:** `src/ayorai_attractor/verification/stance.py`, `src/ayorai_attractor/verification/translation.py`, `tests/verification/test_translated_stance_provenance.py`, `docs/adr/ADR-005-hybrid-multilingual-stance.md`.

### D. Replay tampering

**Threat:** An attacker modifies a stored replay or causes a requested digest to resolve to content with a different internal digest.

**Current defense:** `ReplayStore.get` accepts only 64-character lowercase hex digests (blocking path traversal) and rejects files whose internal digest differs from the requested digest.

**Code:** `src/ayorai_attractor/replay_store.py`.

### E. Hidden Golden v1 leakage

**Threat:** Hidden Golden v1 cases leak into training, feature selection, threshold tuning, or other development decisions.

**Current defense:** Golden v1 is reserved as a hidden Portuguese evaluation set; project ADRs state that v0/v0.1 are development data and that Golden v1 must remain isolated and untouched during development.

**GAP:** The repository does not provide a technical access-control or training-pipeline enforcement mechanism that prevents a future developer, job, or dataset-construction process from reading or using the hidden Golden v1 material.

**Code/docs:** `docs/eval/GOLDEN-NAMING.md`, `docs/eval/ADR-007.md`, `docs/eval/ADR-008.md`.

### F. License contamination

**Threat:** A model or dataset marked EVAL_ONLY is accidentally used for commercial operation or training.

**Current defense:** The model-license policy defines EVAL_ONLY and COMMERCIAL_DEFAULT states, records exact revisions, and the runtime license guard rejects EVAL_ONLY backends unless evaluation mode or explicit opt-in is active. ADR-008 also excludes unclear or non-commercial datasets from training.

**GAP:** There is no automated repository-wide training-data manifest gate that proves every future training input is license-cleared before training starts. The current controls are policy/documentation plus the runtime backend guard.

**Code/docs:** `src/ayorai_attractor/verification/nli.py` (`_license_guard`), `docs/legal/MODEL-LICENSE-POLICY.md`, `docs/eval/ADR-008.md`.

### G. Evaluation overfitting

**Threat:** Repeatedly inspecting evaluation results and tuning rules, thresholds or models to improve the visible evaluation set.

**Current defense:** v0/v0.1 are explicitly development sets; H1 and F1 documentation records development-set limitations; Golden v1 is reserved for generalization and preregistration requirements prohibit tuning on it.

**GAP:** These controls are primarily procedural/documentary. The repository does not technically prevent a developer from running an evaluation, inspecting per-case results, and changing code or thresholds based on those results.

**Code/docs:** `docs/eval/PREREGISTRATION-GOLDEN-v0.1.md`, `docs/eval/PREREGISTRATION-H1.md`, `docs/eval/ADR-008.md`.

### H. Supply-chain compromise

**Threat:** A dependency, GitHub Action, package, or CI tool is compromised or replaced upstream.

**Current defense:** CI runs dependency auditing, Bandit, CodeQL and workflow linting. Dependabot tracks both Python dependencies and GitHub Actions. The workflow-lint job pins actionlint to version 1.7.12 and verifies its SHA-256 archive hash.

**GAP:** GitHub Actions in the workflows are referenced by mutable version tags such as `@v7` and `@v4`, rather than immutable commit SHAs. Dependabot reduces maintenance risk but does not make action references immutable.

**Code:** `.github/workflows/ci.yml`, `.github/workflows/security.yml`, `.github/workflows/codeql.yml`, `.github/dependabot.yml`.

## 4. Gaps summary

| ID | Gap | Priority |
|---|---|---|
| B | Original-source citation/excerpt is not independently revalidated against the source at verification time. | high |
| E | No technical isolation gate prevents hidden Golden v1 leakage into development/training. | high |
| F | No automated training-data license manifest gate prevents EVAL_ONLY contamination before training. | high |
| G | No technical control prevents tuning against visible evaluation results. | medium |
| H | GitHub Actions use mutable version tags instead of immutable commit SHAs. | medium |

## 5. Non-goals

ATTRACTOR does not promise:
- legal, regulatory, copyright or licensing compliance by itself;
- that external sources are truthful;
- universal factual accuracy;
- immunity from compromised dependencies, models or infrastructure;
- production security certification;
- generalization from Golden v0/v0.1;
- that experimental evaluation results constitute production evidence.

Results and defenses are experimental unless separately validated and evidenced.
