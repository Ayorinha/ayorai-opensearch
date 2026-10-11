<div align="center">

# AYORAI ATTRACTOR

**Auditable verification for AI answers.**
*Every claim checked against its source. Every verdict reproducible.*

[![CI](https://github.com/Ayorinha/ayorai-opensearch/actions/workflows/ci.yml/badge.svg)](https://github.com/Ayorinha/ayorai-opensearch/actions/workflows/ci.yml)
[![Security](https://github.com/Ayorinha/ayorai-opensearch/actions/workflows/security.yml/badge.svg)](https://github.com/Ayorinha/ayorai-opensearch/actions/workflows/security.yml)
[![CodeQL](https://github.com/Ayorinha/ayorai-opensearch/actions/workflows/codeql.yml/badge.svg)](https://github.com/Ayorinha/ayorai-opensearch/actions/workflows/codeql.yml)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23125083.svg)](https://doi.org/10.5281/zenodo.23125083)
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

The model may read, classify or assist evidence analysis. It does not become the authority that selects the final verdict.

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

| Sector | Example use |
|---|---|
| Financial services | verify that an AI explanation matches approved evidence and policy |
| Capital markets | verify that AI summaries preserve reported facts and figures |
| Insurance | validate answers against policy wording and supporting evidence |
| Legal and compliance | detect citations that do not support the argument being made |
| Public sector | preserve evidence trails for AI-assisted answers to citizens |
| Internal audit | maintain a reproducible evidence record for AI-assisted conclusions |

## Evidence v0.3.0

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

## Roadmap F0–F6

~~~mermaid
flowchart LR
    F0["F0<br/>Deterministic verification"] --> F1["F1<br/>Multilingual stance"]
    F1 --> F2["F2<br/>Span-level evidence"]
    F2 --> F3["F3<br/>Public benchmarks"]
    F3 --> F4["F4<br/>Hidden Golden v1 in Portuguese"]
    F4 --> F5["F5<br/>Adoption"]
    F5 --> F6["F6<br/>Hardened release"]
    PT["AYORAI-PT-NLI<br/>Portuguese stance path"] --> F2
    F1 --> PT
~~~

The roadmap keeps the deterministic Judge outside the model. **AYORAI-PT-NLI** is a future stance-classification path; it does not become the final adjudicator.

## Quickstart

~~~bash
git clone https://github.com/Ayorinha/ayorai-opensearch.git
cd ayorai-opensearch
git checkout feat/f1-multilingual-stance
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,nli]"
pytest
ruff check .
mypy src/ayorai_attractor
~~~

For the frozen evaluation:

~~~bash
attractor eval --suite golden-v0 --out reports/golden-v0.json
attractor eval --suite golden-v0.1 --out reports/golden-v0.1.json
~~~

Evaluation reports expose two deliberately distinct hashes:

- `content_sha256` is the legacy digest and its semantics are unchanged. It excludes the top-level `latency_ms` and `git_sha`, but includes per-result timing such as `results[].latency_ms`; therefore, it may differ between otherwise equivalent executions.
- `semantic_sha256` uses version `semantic_digest_version="1"`. It recursively excludes execution-volatile fields (`latency_ms`, `git_sha`, both digest fields, and wall-clock timestamp fields) while retaining predictions, labels and metrics. It hashes canonical UTF-8 JSON with sorted keys, compact separators and `ensure_ascii=False`.

Use `semantic_sha256` to compare semantic evaluation results across repeated runs; do not treat it as a substitute for frozen-input hashes or as proof of replay correctness by itself. The reference metrics and reproduction commands are recorded in [Semantic Digest v1 Reference](docs/eval/SEMANTIC-DIGEST-V1-REFERENCE.md).

Always record the commit SHA, suite version and both report digests with an evaluation result.

## ADRs

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

Os resultados atuais são de desenvolvimento. A generalização para documentos genuinamente em português permanece reservada ao **Golden v1 oculto**.

---

## License

Apache-2.0. See [LICENSE](LICENSE).

## Authorship and citation

**Author and technical direction:** Anderson Leon Ayora.

- [Authorship and technical direction](docs/AUTHORSHIP.md)
- [Citation metadata](CITATION.cff)
- DOI: [10.5281/zenodo.23125083](https://doi.org/10.5281/zenodo.23125083)
