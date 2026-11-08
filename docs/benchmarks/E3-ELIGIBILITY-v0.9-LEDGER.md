# E3 Eligibility v0.9 — matriz proposta derivada do ledger A4

**Status:** PROPOSTA documental; Draft; não aprovada para execução.  
**Data:** 2026-11-08.  
**Fonte primária:** [CONTAMINATION-LEDGER-v0.8.md](CONTAMINATION-LEDGER-v0.8.md), especialmente §§3–4.  
**Escopo:** transcrição célula a célula do estado do ledger para uma matriz com o mesmo schema da v0.8. Nenhum modelo foi executado, nenhum peso foi baixado e nenhum resultado foi estimado.

## 1. Regra de derivação

Cada célula membro × coorte permanece bloqueada se o ledger indicar contaminação/exposição conhecida **ou** status UNVERIFIED. Falta de evidência, ausência de IDs, ausência de manifests, ausência de revisão imutável ou ausência de crosswalk nunca é interpretada como independência. A matriz proposta tem **0/55 células elegíveis e 55/55 bloqueadas**.

O arquivo novo é [e3-eligibility-v0.9-ledger.json](../../configs/benchmarks/e3-eligibility-v0.9-ledger.json). O arquivo [e3-eligibility-v0.8.json](../../configs/benchmarks/e3-eligibility-v0.8.json) não foi alterado; seu hash pré-registrado permanece fora do escopo desta proposta.

## 2. Matriz célula a célula

As fontes abaixo indicam, para cada célula, a linha correspondente do ledger (§4.x) e a fonte original da coorte (ledger §3). O status textual é transcrito do ledger; a classificação operacional desta proposta é BLOQUEADO em todos os casos.

### MiniCheck-DeBERTa-v3-Large

Fonte do modelo: [MiniCheck checkpoint card](https://huggingface.co/lytang/MiniCheck-DeBERTa-v3-Large) · [MiniCheck paper](https://arxiv.org/abs/2404.10774), ledger §4.1.

| Coorte | Status no ledger | Fonte da célula (coorte) |
|---|---|---|
| AggreFact-CNN | UNVERIFIED — BLOQUEADO | [Tang et al., ACL 2023](https://aclanthology.org/2023.acl-long.650/) · CONTAMINATION-LEDGER-v0.8.md §4.1 |
| AggreFact-XSum | UNVERIFIED — BLOQUEADO | [Tang et al., ACL 2023](https://aclanthology.org/2023.acl-long.650/) · CONTAMINATION-LEDGER-v0.8.md §4.1 |
| TofuEval-MediaS | UNVERIFIED — BLOQUEADO | [TofuEval, NAACL 2024](https://aclanthology.org/2024.naacl-long.251/) · CONTAMINATION-LEDGER-v0.8.md §4.1 |
| TofuEval-MeetB | UNVERIFIED — BLOQUEADO | [TofuEval, NAACL 2024](https://aclanthology.org/2024.naacl-long.251/) · CONTAMINATION-LEDGER-v0.8.md §4.1 |
| Wice | BLOCKED — fonte WiCE no treino; identidade exata pendente | [WiCE, EMNLP 2023](https://aclanthology.org/2023.emnlp-main.470/) · CONTAMINATION-LEDGER-v0.8.md §4.1 |
| REVEAL | UNVERIFIED — BLOQUEADO | [REVEAL, arXiv:2402.00559](https://arxiv.org/abs/2402.00559) · CONTAMINATION-LEDGER-v0.8.md §4.1 |
| ClaimVerify | UNVERIFIED — BLOQUEADO | [ClaimVerify, Findings EMNLP 2023](https://aclanthology.org/2023.findings-emnlp.467/) · CONTAMINATION-LEDGER-v0.8.md §4.1 |
| FactCheck-GPT | UNVERIFIED — BLOQUEADO | [FactCheck-GPT, arXiv:2311.09000](https://arxiv.org/abs/2311.09000) · CONTAMINATION-LEDGER-v0.8.md §4.1 |
| ExpertQA | UNVERIFIED — BLOQUEADO | [ExpertQA, arXiv:2309.07852](https://arxiv.org/abs/2309.07852) · CONTAMINATION-LEDGER-v0.8.md §4.1 |
| LFQA | UNVERIFIED — BLOQUEADO | [LFQA, arXiv:2310.12150](https://arxiv.org/abs/2310.12150) · CONTAMINATION-LEDGER-v0.8.md §4.1 |
| RAGTruth | UNVERIFIED — BLOQUEADO | [RAGTruth, arXiv:2401.00396](https://arxiv.org/abs/2401.00396) · CONTAMINATION-LEDGER-v0.8.md §4.1 |

### MiniCheck-Flan-T5-Large

Fonte do modelo: [MiniCheck-Flan-T5-Large card](https://huggingface.co/lytang/MiniCheck-Flan-T5-Large) · [MiniCheck paper](https://arxiv.org/abs/2404.10774) · [FLAN tasks.py](https://github.com/google-research/FLAN/blob/main/flan/tasks.py), ledger §4.2.

| Coorte | Status no ledger | Fonte da célula (coorte) |
|---|---|---|
| AggreFact-CNN | BLOCKED — exposição de fonte no backbone; deduplicação pendente | [Tang et al., ACL 2023](https://aclanthology.org/2023.acl-long.650/) · CONTAMINATION-LEDGER-v0.8.md §4.2 |
| AggreFact-XSum | BLOCKED — exposição de fonte no backbone; deduplicação pendente | [Tang et al., ACL 2023](https://aclanthology.org/2023.acl-long.650/) · CONTAMINATION-LEDGER-v0.8.md §4.2 |
| TofuEval-MediaS | UNVERIFIED — BLOQUEADO | [TofuEval, NAACL 2024](https://aclanthology.org/2024.naacl-long.251/) · CONTAMINATION-LEDGER-v0.8.md §4.2 |
| TofuEval-MeetB | UNVERIFIED — BLOQUEADO | [TofuEval, NAACL 2024](https://aclanthology.org/2024.naacl-long.251/) · CONTAMINATION-LEDGER-v0.8.md §4.2 |
| Wice | BLOCKED — fonte WiCE no fine-tuning; deduplicação pendente | [WiCE, EMNLP 2023](https://aclanthology.org/2023.emnlp-main.470/) · CONTAMINATION-LEDGER-v0.8.md §4.2 |
| REVEAL | UNVERIFIED — BLOQUEADO | [REVEAL, arXiv:2402.00559](https://arxiv.org/abs/2402.00559) · CONTAMINATION-LEDGER-v0.8.md §4.2 |
| ClaimVerify | UNVERIFIED — BLOQUEADO | [ClaimVerify, Findings EMNLP 2023](https://aclanthology.org/2023.findings-emnlp.467/) · CONTAMINATION-LEDGER-v0.8.md §4.2 |
| FactCheck-GPT | UNVERIFIED — BLOQUEADO | [FactCheck-GPT, arXiv:2311.09000](https://arxiv.org/abs/2311.09000) · CONTAMINATION-LEDGER-v0.8.md §4.2 |
| ExpertQA | UNVERIFIED — BLOQUEADO | [ExpertQA, arXiv:2309.07852](https://arxiv.org/abs/2309.07852) · CONTAMINATION-LEDGER-v0.8.md §4.2 |
| LFQA | UNVERIFIED — BLOQUEADO | [LFQA, arXiv:2310.12150](https://arxiv.org/abs/2310.12150) · CONTAMINATION-LEDGER-v0.8.md §4.2 |
| RAGTruth | UNVERIFIED — BLOQUEADO | [RAGTruth, arXiv:2401.00396](https://arxiv.org/abs/2401.00396) · CONTAMINATION-LEDGER-v0.8.md §4.2 |

### FactCG-DeBERTa-v3-Large

Fonte do modelo: [FactCG checkpoint card](https://huggingface.co/yaxili96/FactCG-DeBERTa-v3-Large) · [FactCG paper](https://arxiv.org/abs/2501.17144), ledger §4.3.

| Coorte | Status no ledger | Fonte da célula (coorte) |
|---|---|---|
| AggreFact-CNN | UNVERIFIED — BLOQUEADO (exposição de validation conhecida) | [Tang et al., ACL 2023](https://aclanthology.org/2023.acl-long.650/) · CONTAMINATION-LEDGER-v0.8.md §4.3 |
| AggreFact-XSum | UNVERIFIED — BLOQUEADO (exposição de validation conhecida) | [Tang et al., ACL 2023](https://aclanthology.org/2023.acl-long.650/) · CONTAMINATION-LEDGER-v0.8.md §4.3 |
| TofuEval-MediaS | UNVERIFIED — BLOQUEADO (exposição de validation conhecida) | [TofuEval, NAACL 2024](https://aclanthology.org/2024.naacl-long.251/) · CONTAMINATION-LEDGER-v0.8.md §4.3 |
| TofuEval-MeetB | UNVERIFIED — BLOQUEADO (exposição de validation conhecida) | [TofuEval, NAACL 2024](https://aclanthology.org/2024.naacl-long.251/) · CONTAMINATION-LEDGER-v0.8.md §4.3 |
| Wice | BLOCKED — fonte WiCE no treino; deduplicação pendente | [WiCE, EMNLP 2023](https://aclanthology.org/2023.emnlp-main.470/) · CONTAMINATION-LEDGER-v0.8.md §4.3 |
| REVEAL | UNVERIFIED — BLOQUEADO (exposição de validation conhecida) | [REVEAL, arXiv:2402.00559](https://arxiv.org/abs/2402.00559) · CONTAMINATION-LEDGER-v0.8.md §4.3 |
| ClaimVerify | UNVERIFIED — BLOQUEADO (exposição de validation conhecida) | [ClaimVerify, Findings EMNLP 2023](https://aclanthology.org/2023.findings-emnlp.467/) · CONTAMINATION-LEDGER-v0.8.md §4.3 |
| FactCheck-GPT | UNVERIFIED — BLOQUEADO (exposição de validation conhecida) | [FactCheck-GPT, arXiv:2311.09000](https://arxiv.org/abs/2311.09000) · CONTAMINATION-LEDGER-v0.8.md §4.3 |
| ExpertQA | UNVERIFIED — BLOQUEADO (exposição de validation conhecida) | [ExpertQA, arXiv:2309.07852](https://arxiv.org/abs/2309.07852) · CONTAMINATION-LEDGER-v0.8.md §4.3 |
| LFQA | UNVERIFIED — BLOQUEADO (exposição de validation conhecida) | [LFQA, arXiv:2310.12150](https://arxiv.org/abs/2310.12150) · CONTAMINATION-LEDGER-v0.8.md §4.3 |
| RAGTruth | UNVERIFIED — BLOQUEADO (exposição de validation conhecida) | [RAGTruth, arXiv:2401.00396](https://arxiv.org/abs/2401.00396) · CONTAMINATION-LEDGER-v0.8.md §4.3 |

### mDeBERTa-v3-base NLI

Fonte do modelo: [mDeBERTa checkpoint card](https://huggingface.co/MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7), ledger §4.4.

| Coorte | Status no ledger | Fonte da célula (coorte) |
|---|---|---|
| AggreFact-CNN | UNVERIFIED — BLOQUEADO | [Tang et al., ACL 2023](https://aclanthology.org/2023.acl-long.650/) · CONTAMINATION-LEDGER-v0.8.md §4.4 |
| AggreFact-XSum | UNVERIFIED — BLOQUEADO | [Tang et al., ACL 2023](https://aclanthology.org/2023.acl-long.650/) · CONTAMINATION-LEDGER-v0.8.md §4.4 |
| TofuEval-MediaS | UNVERIFIED — BLOQUEADO | [TofuEval, NAACL 2024](https://aclanthology.org/2024.naacl-long.251/) · CONTAMINATION-LEDGER-v0.8.md §4.4 |
| TofuEval-MeetB | UNVERIFIED — BLOQUEADO | [TofuEval, NAACL 2024](https://aclanthology.org/2024.naacl-long.251/) · CONTAMINATION-LEDGER-v0.8.md §4.4 |
| Wice | UNVERIFIED — BLOQUEADO | [WiCE, EMNLP 2023](https://aclanthology.org/2023.emnlp-main.470/) · CONTAMINATION-LEDGER-v0.8.md §4.4 |
| REVEAL | UNVERIFIED — BLOQUEADO | [REVEAL, arXiv:2402.00559](https://arxiv.org/abs/2402.00559) · CONTAMINATION-LEDGER-v0.8.md §4.4 |
| ClaimVerify | UNVERIFIED — BLOQUEADO | [ClaimVerify, Findings EMNLP 2023](https://aclanthology.org/2023.findings-emnlp.467/) · CONTAMINATION-LEDGER-v0.8.md §4.4 |
| FactCheck-GPT | UNVERIFIED — BLOQUEADO | [FactCheck-GPT, arXiv:2311.09000](https://arxiv.org/abs/2311.09000) · CONTAMINATION-LEDGER-v0.8.md §4.4 |
| ExpertQA | UNVERIFIED — BLOQUEADO | [ExpertQA, arXiv:2309.07852](https://arxiv.org/abs/2309.07852) · CONTAMINATION-LEDGER-v0.8.md §4.4 |
| LFQA | UNVERIFIED — BLOQUEADO | [LFQA, arXiv:2310.12150](https://arxiv.org/abs/2310.12150) · CONTAMINATION-LEDGER-v0.8.md §4.4 |
| RAGTruth | UNVERIFIED — BLOQUEADO | [RAGTruth, arXiv:2401.00396](https://arxiv.org/abs/2401.00396) · CONTAMINATION-LEDGER-v0.8.md §4.4 |

### HHEM-2.1-Open

Fonte do modelo: [HHEM checkpoint card](https://huggingface.co/vectara/hallucination_evaluation_model) · [EMNLP Industry 2025 paper](https://aclanthology.org/2025.emnlp-industry.54/), ledger §4.5.

| Coorte | Status no ledger | Fonte da célula (coorte) |
|---|---|---|
| AggreFact-CNN | UNVERIFIED — BLOQUEADO (backbone e fontes confidenciais) | [Tang et al., ACL 2023](https://aclanthology.org/2023.acl-long.650/) · CONTAMINATION-LEDGER-v0.8.md §4.5 |
| AggreFact-XSum | UNVERIFIED — BLOQUEADO (backbone e fontes confidenciais) | [Tang et al., ACL 2023](https://aclanthology.org/2023.acl-long.650/) · CONTAMINATION-LEDGER-v0.8.md §4.5 |
| TofuEval-MediaS | UNVERIFIED — BLOQUEADO (treino parcialmente confidencial) | [TofuEval, NAACL 2024](https://aclanthology.org/2024.naacl-long.251/) · CONTAMINATION-LEDGER-v0.8.md §4.5 |
| TofuEval-MeetB | UNVERIFIED — BLOQUEADO (treino parcialmente confidencial) | [TofuEval, NAACL 2024](https://aclanthology.org/2024.naacl-long.251/) · CONTAMINATION-LEDGER-v0.8.md §4.5 |
| Wice | UNVERIFIED — BLOQUEADO (treino parcialmente confidencial) | [WiCE, EMNLP 2023](https://aclanthology.org/2023.emnlp-main.470/) · CONTAMINATION-LEDGER-v0.8.md §4.5 |
| REVEAL | UNVERIFIED — BLOQUEADO (treino parcialmente confidencial) | [REVEAL, arXiv:2402.00559](https://arxiv.org/abs/2402.00559) · CONTAMINATION-LEDGER-v0.8.md §4.5 |
| ClaimVerify | UNVERIFIED — BLOQUEADO (treino parcialmente confidencial) | [ClaimVerify, Findings EMNLP 2023](https://aclanthology.org/2023.findings-emnlp.467/) · CONTAMINATION-LEDGER-v0.8.md §4.5 |
| FactCheck-GPT | UNVERIFIED — BLOQUEADO (treino parcialmente confidencial) | [FactCheck-GPT, arXiv:2311.09000](https://arxiv.org/abs/2311.09000) · CONTAMINATION-LEDGER-v0.8.md §4.5 |
| ExpertQA | UNVERIFIED — BLOQUEADO (treino parcialmente confidencial) | [ExpertQA, arXiv:2309.07852](https://arxiv.org/abs/2309.07852) · CONTAMINATION-LEDGER-v0.8.md §4.5 |
| LFQA | UNVERIFIED — BLOQUEADO (treino parcialmente confidencial) | [LFQA, arXiv:2310.12150](https://arxiv.org/abs/2310.12150) · CONTAMINATION-LEDGER-v0.8.md §4.5 |
| RAGTruth | BLOCKED — RAGTruth train usado no modelo | [RAGTruth, arXiv:2401.00396](https://arxiv.org/abs/2401.00396) · CONTAMINATION-LEDGER-v0.8.md §4.5 |

## 3. Diferenças em relação à v0.8

- A v0.8 tinha status `exploratory_pre_ledger` e aplicava apenas bloqueios explícitos do pré-registro E3; por isso algumas células não bloqueadas eram tratadas como elegíveis na matriz exploratória.
- A v0.9 proposta deriva os bloqueios das 55 avaliações do ledger A4. Todas as células passam a integrar `blocked_cohorts`, inclusive aquelas classificadas como UNVERIFIED.
- Bloqueios conhecidos ficam descritos no ledger: exposição MiniCheck/WiCE; exposição FLAN/CNN-DailyMail e XSum; uso de RAGTruth train pelo HHEM; e exposição de seleção/threshold tuning do FactCG no validation LLM-AggreFact.
- As células restantes continuam bloqueadas por proveniência incompleta, confidencialidade, falta de revisão imutável ou ausência de deduplicação verificável.
- A configuração mantém os mesmos nomes de membros, ordem das coortes, comparador e configurações da v0.8. Apenas o status e os conjuntos de bloqueio refletem o ledger.

## 4. Limites e próximos gates

Esta proposta não substitui a matriz v0.8, não autoriza execução, não altera qualquer pré-registro aprovado e não permite recalcular resultados exploratórios como se fossem confirmatórios. A matriz só poderá ser adotada após revisão independente, verificação do schema e decisão explícita do mantenedor. Qualquer futura elegibilidade exige evidência positiva específica por célula, revisão imutável, manifests, split, deduplicação por IDs/conteúdo e relatório de overlap.

**Conclusão:** o estado conservador do ledger resulta em 0/55 células elegíveis. Nenhuma inferência de ausência de contaminação foi feita.
