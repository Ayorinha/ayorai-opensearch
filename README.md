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
- **Prompt-injection aware:** instruction-like text inside retrieved evidence remains data.
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

Measured on **Golden v0.1**. The frozen majority baseline is **43.33%**.

| Path | Accuracy | Interpretation |
|---|---:|---|
| A | **76.67%** | research only |
| B | **66.67%** | commercial candidate |
| C | **33.33%** | deterministic ablation |

For the commercial-candidate comparison, **B = 66.67% vs baseline 43.33% (p=0.0085)**.

### What these numbers do not show

- They are **development-set results**, not production-generalization evidence.
- The current development corpus contains **English documents**.
- Portuguese-document generalization is reserved for the **hidden Golden v1**.
- A is **research only**; B is the **commercial candidate**.
- The results do not establish regulatory certification, legal compliance or universal factual accuracy.

## Golden integrity

The frozen evaluation artifacts are content-addressed and must not be silently replaced.

| Artifact | SHA-256 |
|---|---|
| Golden v0 | <code>2613aefccf232989833b80c0d23257e6e9f312e0f6b720801a0658407b2f1c75</code> |
| Golden v0.1 | <code>a7076512196c1ee9670478f036f7a3996fe89a483efad140ec7b985a54846fb9</code> |
| Corpus | <code>ce2333ccfe4003ebfc90819400beaf6a245620754deb8572c7611bd8bbb7dea3</code> |

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
~~~

Always record the commit SHA, suite version and semantic report digest with an evaluation result.

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
