<div align="center">

<p align="center"><img src="docs/assets/brand/ayorai-attractor-banner.png" alt="AYORAI ATTRACTOR" width="720"></p>

# AYORAI ATTRACTOR

**Auditable verification for AI answers.**
*Every claim checked against its source. Every verdict reproducible.*

[![CI](https://github.com/Ayorinha/ayorai-opensearch/actions/workflows/ci.yml/badge.svg)](https://github.com/Ayorinha/ayorai-opensearch/actions/workflows/ci.yml)
[![Security](https://github.com/Ayorinha/ayorai-opensearch/actions/workflows/security.yml/badge.svg)](https://github.com/Ayorinha/ayorai-opensearch/actions/workflows/security.yml)
[![CodeQL](https://github.com/Ayorinha/ayorai-opensearch/actions/workflows/codeql.yml/badge.svg)](https://github.com/Ayorinha/ayorai-opensearch/actions/workflows/codeql.yml)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23125082.svg)](https://doi.org/10.5281/zenodo.23125082)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue)

🇧🇷 [Português](#em-português) · 📘 [Guia passo a passo](docs/GUIA-PASSO-A-PASSO.md) · ⚖️ [Conformidade no Brasil](docs/CONFORMIDADE-BRASIL.md) · 💼 [Para investidores e parceiros](docs/INVESTIDORES.md)

</div>

---

## The problem

Generative AI can produce fluent answers with citations that do not actually support the claims attached to them. For an organization that needs traceability, this creates an audit gap: when someone asks why a system reached a conclusion, a narrative response is not enough.

## The answer

ATTRACTOR separates an AI answer into individual **claims**, connects each claim to **evidence**, derives **stance** from explicit rules or model-assisted analysis, and lets a **deterministic Judge** decide the final verification state.

> **Intelligence ≠ Authorization ≠ Execution**

~~~mermaid
flowchart LR
    A["AI answer"] --> B["Claim extraction"]
    B --> C["Evidence<br/>sources, offsets, provenance"]
    C --> D["Stance<br/>supports / contradicts / neutral"]
    D --> E{"Deterministic Judge<br/>fixed, versioned rules"}
    E --> F["Verdict"]
    E --> G["Proof trail<br/>claim → source span → SHA-256"]
~~~

| Layer | Responsibility | Can decide the final verdict? |
|---|---|---|
| Intelligence | language-model assistance for claim/evidence analysis | ❌ No |
| Authorization | deterministic Judge and explicit rules | ✅ Yes — the only component |
| Execution | consuming application | ❌ No |

The model may read, classify or assist evidence analysis. It does not become the authority that selects the final verdict. This is scoped claim-evidence mismatch detection, not a guarantee that every hallucination will be detected.

## Six possible verdicts

<code>VERIFIED</code> · <code>SUPPORTED</code> · <code>PARTIALLY_SUPPORTED</code> · <code>UNVERIFIED</code> · <code>REFUTED</code> · <code>CONFLICTING</code>

When evidence conflicts, ATTRACTOR can return <code>CONFLICTING</code> instead of silently selecting a preferred source. When evidence is insufficient, it can return <code>UNVERIFIED</code> instead of guessing.

## Why it matters

- **Reproducible:** the same structured input and rules produce the same verification state.
- **Auditable:** each result can retain claim, evidence, provenance and source-span references.
- **Tamper-evident:** evaluation inputs and outputs can be content-addressed with SHA-256.
- **Multilingual by design:** Portuguese is a primary future evaluation target while English documents remain explicitly disclosed in the current development evidence.
- **Injection-resilience design:** the threat model and evaluation corpus include instruction-like text in evidence; this is a tested risk area, not a claim of immunity. See [Threat Model](docs/THREAT-MODEL.md), [security tests](tests/test_verification_response_security.py), and the [traceability matrix](docs/TRACEABILITY-MASTER.md).
- **Open core:** the verification boundary, evaluation methodology and engineering evidence are publicly inspectable.
- **Governance-oriented:** the architecture is designed to support traceability, evidence preservation and controlled AI-assisted workflows.

## Where it applies

| Scope | Status |
|---|---|
| **Current domain — Brazilian telecommunications regulation (D10)** | Evidence-based verification for claims concerning Anatel rules, initially focused on the General Consumer Rights Regulation (RGC). |
| Other possible domains (outside current scope) | Insurance, legal and compliance, public sector, internal audit, financial services and capital markets are possible future applications, not validated current use cases. |

## Evidence (historical measurements, v0.3.0)

The development measurements are reported side by side; neither set establishes production generalization.

| Path | Golden v0 | Golden v0.1 |
|---|---:|---:|
| A | **40.00%** | **76.67%** |
| B | **43.33%** | **66.67%** |
| C | **26.67%** | **33.33%** |
| Majority baseline | **43.33%** | **43.33%** |

**Important metric/version note:** the 26.67% Path C value in the historical E1 table was measured with older code at commit `c4b73f4` (2026-10-03); it is not the current Path C accuracy on Golden v0. With the current rule code evaluated in F1.2, Path C accuracy on Golden v0 is **23.33%** (both baseline v4 and candidate v5). The historical E1 figure is retained above as a historical measurement, not relabelled as a current result. See [`docs/eval/F1.2-RESULTS.md`](docs/eval/F1.2-RESULTS.md) for the version-specific comparison.

**Limitations that apply to both columns:** these are development sets, not a production-generalization benchmark; each suite contains **34 cases, 30 with a global verdict**; the corpus has 52 synthetic documents, all tagged `en-US`. Golden v0.1 was rewritten after its author had seen per-case results, as disclosed in [its pre-registration](docs/eval/PREREGISTRATION-GOLDEN-v0.1.md); therefore, v0.1 is not independent confirmatory evidence and must be reported alongside Golden v0. On Golden v0, the 95% confidence intervals for A and B include the 43.33% majority baseline. The results do not establish Portuguese-document generalization, regulatory certification, legal compliance or universal factual accuracy.

Path A is **research-only / EVAL_ONLY**. Path B is described elsewhere in the project as a candidate commercial path, subject to the project's model-license policy and independent verification; these accuracy figures alone do not establish commercial clearance.

## CI environment reproducibility

All GitHub Actions workflow jobs explicitly use `ubuntu-24.04`; they do not rely on the moving `ubuntu-latest` alias. This pins the runner's Ubuntu release, not every package or external service installed during a workflow.

Any future operating-system change must be proposed in a dedicated pull request. Before that change is accepted, compare the three evaluation `semantic_sha256` values (Golden v0, Golden v0.1 and smoke-v0) against the frozen references, and investigate any difference. Frozen inputs, thresholds and expected digests must not be edited to make a runner migration pass.

## Golden integrity

The frozen evaluation artifacts are content-addressed and must not be silently replaced.

Local `.attractor/` audit and replay data must not be versioned; evidence requiring traceability should be deliberately exported as a reviewed report, never committed directly from that runtime directory.

| Artifact | SHA-256 |
|---|---|
| Golden v0 | <code>2613aefccf232989833b80c0d23257e6e9f312e0f6b720801a0658407b2f1c75</code> |
| Golden v0.1 | <code>a7076512196c1ee9670478f036f7a3996fe89a483efad140ec7b985a54846fb9</code> |
| Corpus | <code>ce2333ccfe4003ebfc90819400beaf6a245620754deb8572c7611bd8bbb7dea3</code> |

## Evaluation glossary

- **F0–F6:** roadmap phases (for example, F1 means the multilingual-stance phase), not statistical metrics.
- **macro-F1:** the macro-averaged F1 classification metric; report it separately from accuracy and balanced accuracy.
- **E1:** the historical evaluation/reporting label for the global-verdict accuracy results described above.

## Roadmap — current execution sequence

1. **Phase 1 — completed (v0.4.0):** single deterministic Judge authority for the final verdict, tamper-evident audit trail, and structured HTTP 422 errors.
2. **Phase 2 — Judge 2.0 — completed (v0.5.0):** items 2.1–2.7: the normative contract, gates, deterministic adjudication, API contracts, derived Golden sets, canonical-result explanations and generated traceability.
3. **Reproducibility:** strengthen deterministic replay, provenance and auditable execution records.
4. **PT-BR benchmark:** build and document an evidence-based benchmark focused on Brazilian telecommunications regulation, starting with Anatel's General Consumer Rights Regulation (RGC).
   - **Progress (2026-10-16):** official source bytes captured (#177), deterministic derived text documented (#178), and deterministic runner proposed (#179). Protocol Amendment 2 is recorded in [#193](https://github.com/Ayorinha/ayorai-opensearch/pull/193), decisions DEC-007, DEC-008 and DEC-009 are recorded as approved in [#194](https://github.com/Ayorinha/ayorai-opensearch/pull/194), and the canonical URL serialization issue #182 was corrected with regression tests in [#192](https://github.com/Ayorinha/ayorai-opensearch/pull/192). Human annotation has not started. Next human step: 20-case annotation pilot.
5. **Demonstration:** prepare a reproducible demonstration with explicit limitations and evidence.
6. **Institutional package:** prepare technical and governance materials for research and institutional review.

The deterministic Judge remains **outside the model** and is the sole authority for the final verdict. Models may assist with analysis; they do not authorize or issue the final decision.

## Quickstart

~~~bash
git clone https://github.com/Ayorinha/ayorai-opensearch.git
cd ayorai-opensearch
git switch main
# For the stable v0.5.0 release instead, use: git switch --detach v0.5.0
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
ruff check .
mypy src/ayorai_attractor
~~~

Optional NLI backends (downloads large model dependencies): `pip install -e ".[dev,nli]"`.

For the frozen evaluation:

~~~bash
attractor eval --suite golden-v0 --out reports/golden-v0.json
attractor eval --suite golden-v0.1 --out reports/golden-v0.1.json
~~~

Evaluation commands write generated files to `reports/`; do not commit those generated report files.

Evaluation reports expose two deliberately distinct hashes:

- `content_sha256` is the legacy digest and its semantics are unchanged. It excludes the top-level `latency_ms` and `git_sha`, but includes per-result timing such as `results[].latency_ms`; therefore, it may differ between otherwise equivalent executions.
- `semantic_sha256` uses version `semantic_digest_version="1"`. It recursively excludes execution-volatile fields (`latency_ms`, `git_sha`, both digest fields, and wall-clock timestamp fields) while retaining predictions, labels and metrics. It hashes canonical UTF-8 JSON with sorted keys, compact separators and `ensure_ascii=False`.

Use `semantic_sha256` to compare semantic evaluation results across repeated runs; do not treat it as a substitute for frozen-input hashes or as proof of replay correctness by itself. The reference metrics and reproduction commands are recorded in [Semantic Digest v1 Reference](docs/eval/SEMANTIC-DIGEST-V1-REFERENCE.md).

Always record the commit SHA, suite version and both report digests with an evaluation result.

## ADRs

[ADR-009 — Deterministic adjudication contract](docs/adr/ADR-009-deterministic-adjudication-contract.md) is implemented for Judge 2.0: gates, deterministic adjudication, canonical output with rule trace, explanations and generated traceability. SHA-256 hashes identify content; they do not prove that a claim is true. The documented in-process forgery limitation remains.

| ADR | Decision |
|---|---|
| ADR-001 | namespace and package boundary |
| ADR-002 | deterministic Judge rules and final-verdict authority |
| ADR-003 | three-state stance semantics |
| ADR-004 | claim-as-input contract |
| ADR-005 | hybrid multilingual stance detection |
| ADR-006 | metadata, independence and numeric semantics |
| ADR-007 | Portuguese unsupported-span research path |
| ADR-008 | AYORAI-PT-NLI commercial stance path |

## Public-claim evidence map

Use the [TRACEABILITY-MASTER](docs/TRACEABILITY-MASTER.md) as the current implementation/evidence register; a feature name or architecture diagram alone is not proof that every control is complete.

| Public claim | Evidence and qualification |
|---|---|
| The deterministic Judge is the sole final-verdict authority | [ADR-009](docs/adr/ADR-009-deterministic-adjudication-contract.md) (normative adjudication contract), [ADR-002](docs/adr/ADR-002-judge-rules.md) and Judge implementation/tests; confirm implementation against the exact release commit. |
| Evaluation numbers describe development performance | [F1.2 results](docs/eval/F1.2-RESULTS.md) and [Golden v0.1 pre-registration](docs/eval/PREREGISTRATION-GOLDEN-v0.1.md); the sets are synthetic and not production-generalization evidence. |
| Artifact integrity uses SHA-256 | Frozen hashes listed above and the evaluation digest reference; hashes establish byte/semantic integrity under their defined rules, not factual correctness. |
| Injection resistance is addressed | [Threat Model](docs/THREAT-MODEL.md), security tests, and synthetic Golden injection cases; these do not establish immunity to all attacks. |
| Regulatory compliance | No certification or legal compliance is claimed; see [Brazil compliance notes](docs/CONFORMIDADE-BRASIL.md). |

## Status

**Research and engineering reference implementation.**

ATTRACTOR is **not certified**, does not constitute legal advice, and does not by itself establish regulatory compliance. It is designed to support evidence traceability, reproducibility, auditability and controlled AI-assisted verification.

## Em português

O ATTRACTOR é uma camada de verificação baseada em evidências para respostas de IA. Ele separa **afirmação, evidência, posicionamento, proveniência e decisão final**.

O princípio central é:

> **Inteligência ≠ Autorização ≠ Execução**

Modelos podem ajudar a analisar evidências, mas o **Judge determinístico** permanece como a única autoridade para o veredito final.

Os resultados atuais são de desenvolvimento. A generalização para documentos genuinamente em português permanece reservada ao **Golden v1 oculto**. Hashes SHA-256 identificam conteúdo, mas não provam a verdade de uma afirmação; a limitação de forja em processo continua documentada.

---

## License

Apache-2.0. See [LICENSE](LICENSE).

## Authorship and citation

**Author and technical direction:** Anderson Leon Ayora.

- [Authorship and technical direction](docs/AUTHORSHIP.md)
- [Citation metadata](CITATION.cff)
- Concept DOI (all versions): [10.5281/zenodo.23125082](https://doi.org/10.5281/zenodo.23125082)
- v0.5.0: [10.5281/zenodo.23344005](https://doi.org/10.5281/zenodo.23344005)
- v0.4.0: [10.5281/zenodo.23300849](https://doi.org/10.5281/zenodo.23300849)
