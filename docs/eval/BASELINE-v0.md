# Golden v0 Baseline

**System:** current-attractor  
**Suite:** golden-v0  
**Actions run:** https://github.com/Ayorinha/ayorai-opensearch/actions/runs/36759101933  
**Baseline job:** `freeze-and-baseline`  
**Baseline artifact:** `golden-v0-baseline-0d64694e760e1afa3e4e6f9e0df509302d74976b`  
**Frozen inputs:** 34 cases, 52 corpus documents  
**Network:** false  
**Cases with global verdict:** 30  
**Abstain cases:** 4

## Freeze evidence

The freeze workflow calculated SHA-256 values with `sha256sum` and published them in `evals/golden/MANIFEST.json`:

- `evals/golden/v0.jsonl`: `2613aefccf232989833b80c0d23257e6e9f312e0f6b720801a0658407b2f1c75`
- `evals/corpus/documents.jsonl`: `ce2333ccfe4003ebfc908194194?\n`

See the Actions log for the authoritative freeze calculation. The repository manifest records the same two SHA-256 values.

## Overall

| Metric | Result |
|---|---:|
| Correct global verdicts | 13 / 30 |
| Accuracy | **43.3333%** |
| Majority class | **PARTIALLY_SUPPORTED** |
| Majority-class baseline | **43.3333%** |
| Accuracy above majority class | **0.00 pp** |
| Abstention accuracy | 0 / 4 |
| Injection resistance | 3 / 3 = 100% |
| Latency p50 | 0.030 ms |
| Latency p95 | 0.061 ms |

## Accuracy by category

| Category | Correct | Total | Accuracy |
|---|---:|---:|---:|
| comparison | 1 | 2 | 50.0% |
| conflict | 0 | 3 | 0.0% |
| conflict-date | 0 | 1 | 0.0% |
| conflict-entity | 0 | 1 | 0.0% |
| conflict-negation | 0 | 1 | 0.0% |
| factual | 2 | 4 | 50.0% |
| independence-citation-chain | 1 | 1 | 100.0% |
| independence-hash | 1 | 1 | 100.0% |
| independence-republication | 2 | 2 | 100.0% |
| injection | 3 | 3 | 100.0% |
| injection-factual-corroborated | 0 | 1 | 0.0% |
| mock-only | 0 | 1 | 0.0% |
| multi-hop | 3 | 3 | 100.0% |
| numeric-tolerance | 0 | 1 | 0.0% |
| numeric-tolerance-boundary | 0 | 2 | 0.0% |
| provenance-complete | 0 | 1 | 0.0% |
| provenance-incomplete | 0 | 1 | 0.0% |
| refuted | 0 | 1 | 0.0% |

## Accuracy by expected state

| State | Correct | Total | Accuracy |
|---|---:|---:|---:|
| CONFLICTING | 0 | 8 | 0.0% |
| PARTIALLY_SUPPORTED | 13 | 13 | 100.0% |
| REFUTED | 0 | 1 | 0.0% |
| SUPPORTED | 0 | 1 | 0.0% |
| UNVERIFIED | 0 | 1 | 0.0% |
| VERIFIED | 0 | 6 | 0.0% |

## Confusion matrix

| Expected → Predicted | PARTIALLY_SUPPORTED |
|---|---:|
| CONFLICTING | 8 |
| PARTIALLY_SUPPORTED | 13 |
| REFUTED | 1 |
| SUPPORTED | 1 |
| UNVERIFIED | 1 |
| VERIFIED | 6 |

The four abstention cases are outside this global-verdict confusion matrix.

## Interpretação honesta

- O sistema atual prevê **PARTIALLY_SUPPORTED para todos os casos com evidência**; sua acurácia de **43,3333%** é exatamente igual à classe majoritária.
- Os 100% observados em independência, multi-hop e parte de factual são **coincidência com o rótulo majoritário**, não prova de capacidade geral de verificação.
- A resistência à injeção de **100%** é **trivial no estado atual**: o motor não interpreta o conteúdo como instrução; esse número só terá significado após o R1 implementar o tratamento de conteúdo/instruções previsto.
- A latência mede somente o motor offline com fixtures e **não representa latência de pesquisa real**.
- A métrica adicional obrigatória a partir do R1 é **acurácia acima da classe majoritária**, em pontos percentuais.

## Limites do baseline

Este baseline mede o sistema atual contra o golden v0 fechado. Não mede recuperação em corpus inteiro, busca externa, generalização ou capacidade do futuro Chief Judge. O conjunto v0 foi construído junto com o ADR-002; portanto, desempenho alto nele não seria evidência suficiente de generalização.
