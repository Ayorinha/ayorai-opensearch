# State of the Art — Auditable Claim Verification (PT/EN)

**Research date:** 2026-10-03  
**Access-date convention:** every external source cited below was checked on 2026-10-03.

## 1. Executive findings

The current public state of the art is strong at *claim/document classification*, but most published systems optimize a scalar or binary support score. ATTRACTOR's design target is different: an auditable verification layer in which model outputs are evidence, deterministic rules handle explicit structured contradictions, dependency-aware evidence clusters prevent double counting, and ADR-002 alone emits the final verdict.

This is not a claim that ATTRACTOR is more accurate than every published system. Its differentiator is the verification contract and auditability boundary.

## 2. LLM-AggreFact

The official LLM-AggreFact leaderboard reports the following average balanced accuracies: Bespoke-MiniCheck-7B **77.4**, Claude-3.5 Sonnet **77.2**, Granite Guardian 3.3 **76.5**, and MiniCheck-Flan-T5-L **75.0**. The same leaderboard contains substantial per-dataset variation, so the aggregate should not be interpreted as a universal ceiling. [LLM-AggreFact leaderboard](https://llm-aggrefact.github.io/), accessed 2026-10-03.

The MiniCheck paper introduced the benchmark and reports specialized fact-checkers evaluated across heterogeneous factual-consistency datasets. Its training recipe combines 14K synthetic examples with a 21K hard subset of ANLI for MiniCheck-FT5 and MiniCheck-DBTA. [MiniCheck paper](https://aclanthology.org/2024.emnlp-main.499/), accessed 2026-10-03.

**Questioning the preliminary claim:** “the real ceiling is 77–80%” is not established by the leaderboard. The observed scores show that 75–77% is achievable on this benchmark, but a benchmark-specific range is not a theoretical ceiling for factual verification.

The claim that analyses establish “at least 6% wrong labels in AggreFact” is also not adopted as a project fact without a primary-source error audit defining the denominator and label adjudication protocol. The benchmark's reported results are treated as measurements, not as proof that its labels are wrong.

## 3. What leading systems do that ATTRACTOR does not — yet

### MiniCheck family
MiniCheck uses a specialized binary support/unsupported objective and synthetic Claim-to-Document and Document-to-Claim generation. MiniCheck-FT5 uses Flan-T5-Large and a 35K training mixture; the paper states that 21K ANLI examples plus 14K synthetic examples were used. It is highly focused on the support decision, but it does not define ATTRACTOR's deterministic multi-verdict Judge, provenance-completeness semantics, or source-dependency clustering as the final decision boundary.

Bespoke-MiniCheck-7B is a 7B model fine-tuned on 21K ANLI examples plus 14K synthetic examples and is released under CC BY-NC 4.0. The model card explicitly describes its 35K mixture and binary fact-checking use. [Bespoke model card](https://huggingface.co/bespokelabs/Bespoke-MiniCheck-7B), accessed 2026-10-03.

### Granite Guardian 3.3/4.1
IBM describes Granite Guardian as a scoring model for safety, groundedness/RAG and agentic risks. Granite Guardian 4.1 adds BYOC and reports an average LM-AggreFact balanced accuracy around 0.76 in its model card. IBM states that Granite Guardian is released under Apache 2.0 for research and commercial use. The official model card says it is trained and tested only on English data. [IBM Granite Guardian documentation](https://www.ibm.com/granite/docs/models/guardian), accessed 2026-10-03.

ATTRACTOR does not currently use Granite Guardian as its Judge. This is intentional: a model-generated score must not become the final verdict merely because it performs strongly on an external benchmark.

### Multilingual resources
MADLAD-400-3B-MT is a multilingual translation model covering 400+ languages; its model card states Apache 2.0 and publicly available training data. It can support translation-then-verification, but translation introduces a second model boundary and therefore must be represented in provenance. [MADLAD model card](https://huggingface.co/google/madlad400-3b-mt), accessed 2026-10-03.

PsiloQA is a multilingual hallucination-detection benchmark covering 14 languages, with 63,792 training examples and 2,897 test examples; its dataset card states CC-BY-4.0. [PsiloQA dataset card](https://huggingface.co/datasets/s-nlp/PsiloQA), accessed 2026-10-03.

MultiHal is a 2026 multilingual, multihop hallucination benchmark grounded in knowledge-graph paths. The authors mined 140K KG paths and curated 25.9K high-quality paths; the published evaluation covers multiple languages and models. [PMLR paper](https://proceedings.mlr.press/v306/lavrinovics26a.html), accessed 2026-10-03.

## 4. Portuguese evidence

ASSIN 2 is a Brazilian-Portuguese textual entailment/semantic-similarity corpus. The maintained Hugging Face dataset metadata currently marks its license as **unknown**, while the original dataset metadata used an empty license field. Therefore ATTRACTOR must not infer commercial permission from the absence of a declared license. The corpus contains 6,500 training, 500 validation and about 2,448 test pairs in the released dataset. [ASSIN 2 dataset metadata](https://huggingface.co/datasets/nilc-nlp/assin2), accessed 2026-10-03.

**Conclusion:** ASSIN 2 is useful evidence for Portuguese NLI research, but it is not a clean commercial-training source under ATTRACTOR's policy unless its licensing is independently clarified.

The project should therefore treat PT capability as an evaluation and engineering target rather than assuming that a Portuguese dataset is legally reusable for commercial model training.

## 5. Conformal prediction and factuality

Mohri & Hashimoto's 2024 *Language Models with Conformal Factuality Guarantees* connects conformal prediction with entailment sets and proposes a way to obtain high-probability correctness guarantees by expanding uncertainty sets/backing off from overly specific outputs. Their experiments report 80–90% correctness guarantees while retaining much of the original output. This is a statistical guarantee framework, not a replacement for evidence provenance or deterministic adjudication. [Paper](https://arxiv.org/abs/2402.10978), accessed 2026-10-03.
\nSuccessors strengthen the idea in two directions. Rubin-Toles et al. (ICLR 2025) introduce coherent factuality, applying split conformal prediction over a deducibility graph so that dependent reasoning claims are calibrated jointly. CoFact (ICLR 2026) explicitly addresses covariate shift by reweighting calibration data, targeting settings where the exchangeability assumption can fail. A 2026 ICML paper, *Differentiable Conformal Training for LLM Reasoning Factuality*, proposes a differentiable relaxation of coherent factuality while retaining its guarantees. These results make conformal calibration a plausible future layer for ATTRACTOR, but they do not justify changing the deterministic Judge in F1.1. [ICLR 2025](https://proceedings.iclr.cc/paper_files/paper/2025/hash/679fcceef65c3d855aa885bd024542c1-Abstract-Conference.html), [CoFact ICLR 2026](https://proceedings.iclr.cc/paper_files/paper/2026/hash/bd074b828bbd782d4bece89306caff84-Abstract-Conference.html), [ICML 2026](https://proceedings.mlr.press/v306/hittesdorf26a.html), accessed 2026-10-03.\n
For ATTRACTOR, the useful research direction is **conformal acceptance/calibration on top of the deterministic Judge**, not replacing the Judge with a probabilistic model. Future work should reserve a calibration set outside Golden v0 and report coverage/error guarantees separately.

## 6. Where ATTRACTOR is structurally different

| Dimension | Common benchmark fact-checker | ATTRACTOR |
|---|---|---|
| Final decision | Usually model score/class | Deterministic ADR-002 Judge |
| Evidence dependency | Often implicit | Explicit dependency clusters |
| Provenance completeness | Usually not a final-verdict condition | Explicit Judge input |
| Exact source span | Model-dependent | Character offsets are first-class evidence |
| Structured numeric rules | Often learned | Deterministic PT/EN rules before NLI |
| PT/EN | Varies; many leaders are English | Explicit PT/EN path in F1 |
| Audit reproducibility | Benchmark/model-centric | Frozen Golden, config hash, provenance and report hash |
| License gate | External to metric | Runtime EVAL_ONLY/COMMERCIAL_DEFAULT policy |

These are architectural differences, not accuracy claims.

## 7. Where I disagree with the preliminary Claude assessment

1. **“77–80% is the real ceiling.”** I do not accept this as established. It is a benchmark observation, not a demonstrated ceiling.
2. **“At least 6% of AggreFact labels are wrong.”** I do not promote this to fact without a primary adjudication study specifying the disputed cases and denominator.
3. **License symmetry.** The previous OPUS treatment was too conservative if the rule was meant to be “no declared NC dataset.” The consistent policy is now: permissive fixed weights + no *declared* NC training data + fixed revision + verification date. Unknown or incompletely inventoried data is a legal-risk note, not automatically an NC finding.
4. **Granite Guardian as a direct substitute for ATTRACTOR Judge.** Its benchmark performance is relevant, but its model-generated yes/no score does not satisfy ATTRACTOR's deterministic final-verdict contract.

## 8. Research roadmap

1. Add independent calibration/conformal evaluation without modifying Golden v0.
2. Add multilingual benchmarks such as PsiloQA and MultiHal as external evaluation corpora, preserving their licenses.
3. Evaluate Granite Guardian 4.1 as an optional external comparator, not as the final Judge.
4. Evaluate MiniCheck variants in EVAL_ONLY.
5. Build Portuguese-specific error suites for numbers, negation, entities, temporal shifts and republication.
6. Keep all external benchmark results separate from Golden v0 so no development leakage occurs.
