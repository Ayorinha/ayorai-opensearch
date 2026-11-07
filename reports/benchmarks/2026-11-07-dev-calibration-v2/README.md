# Resultado de calibração — Phase 1b, DEV completo, Calibration V2

**Data do registro:** 2026-11-07  
**Estado:** relatório documental de resultados DEV; não é avaliação TEST nem resultado de ranking.  
**Partição:** DEV do LLM-AggreFact, 30.420 casos, 11 coortes.  
**Modelos:** FactCG, MiniCheck e mDeBERTa, com protocolos oficiais.  
**Execução:** CPU, fp32.  
**Separação:** DEV-A (15.214 casos) para seleção e ajuste/cross-fitting; DEV-B (15.206 casos) para LTT e análise descritiva.

## Resumo metodológico e operacional

A execução completa de DEV foi iniciada na run [42389121599](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/42389121599), no head `34b7ccd654896890ab0197bffd6c607fbc3f729e`. O job plan e os 93 shards (3 modelos × 31 shards) concluíram com sucesso. O job aggregate falhou em aproximadamente 13 segundos com `ModuleNotFoundError`, antes de decifrar qualquer artefato. A correção está na PR #481; a re-agregação foi executada na run [42418593837](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/42418593837), no código `c3946aec35eeb32551c92f97472308ccdd20a744`. Ela verificou a origem da execução, decifrou os artefatos no ambiente protegido e passou nas verificações de completude e privacidade. Não houve reexecução de inferência.

A execução exigiu aprovações do environment por job, conforme a matriz de 93 jobs avançou. Esse fluxo produziu muitas solicitações de aprovação e é uma observação operacional para melhoria futura, não uma alteração dos resultados.

## Camada 1 — seleção de modelo

Regra: BA cross-fitted em DEV-A, média macro simples por dataset. FactCG foi selecionado pela regra registrada na PR #477; não houve empate nem candidato inelegível.

| Modelo | BA cross-fitted (média macro por dataset) | Decisão |
|---|---:|---|
| FactCG | **0,7468 (74,68%)** | Selecionado |
| MiniCheck | 0,7287 (72,87%) | Não selecionado |
| mDeBERTa | 0,6257 (62,57%) | Não selecionado |

A referência de baseline por regras é 49,2% (run [42276765499](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/42276765499), TEST). FactCG foi publicado com 75,6% no LLM-AggreFact; essa referência publicada não substitui a métrica DEV deste relatório.

### FactCG — BA por dataset em DEV-A

| Dataset | BA |
|---|---:|
| AggreFact-CNN | 0,6286 |
| AggreFact-XSum | 0,6805 |
| ClaimVerify | 0,7380 |
| ExpertQA | 0,5951 |
| FactCheck-GPT | 0,7906 |
| Lfqa | 0,8631 |
| RAGTruth | 0,8019 |
| Reveal | 0,8953 |
| TofuEval-MediaS | 0,6981 |
| TofuEval-MeetB | 0,7119 |
| Wice | 0,8113 |

O ponto fraco observado nesta partição é ExpertQA (BA 0,5951). Essa observação é descritiva de DEV, não uma conclusão sobre desempenho TEST.

## Camada 2 — métricas probabilísticas cross-fitted em DEV-A

Métricas calculadas para todos os casos de DEV-A.

| Modelo | AUROC | AUPRC | Brier | ECE (15 bins) | Log-loss |
|---|---:|---:|---:|---:|---:|
| FactCG | 0,8650 | 0,9454 | 0,1168 | 0,0054 | 0,3708 |
| MiniCheck | 0,8224 | 0,9200 | 0,1306 | 0,0076 | 0,4132 |
| mDeBERTa | 0,6936 | 0,8569 | 0,1630 | 0,0083 | 0,5013 |

Prevalência de SUPPORTED em DEV-A: **0,7602 (76,02%)**. A prevalência elevada é importante para interpretar as métricas e a distribuição dos rótulos.

## Camada 3 — LTT em DEV-B, FactCG

**Resultado pela regra originalmente registrada: 0/11 coortes certificadas.**

Em todas as 11 coortes, `stop_reason = "n_below_25; sequence_stopped"` e `tested_thresholds = []`. A implementação tratou o primeiro limiar inelegível (`t=0,99`, normalmente com menos de 25 respostas aceitas) como não rejeição e interrompeu a sequência.

A causa é uma falha de desenho/operacionalização do pré-registro, não uma falha atribuída ao modelo: o §5.2 determinava avançar somente após rejeitar a hipótese nula, mas também exigia pelo menos 25 respostas aceitas para o teste ser elegível. Com IVAP, probabilidades de confiança ≥0,99 são raras. Interpretar um limiar inelegível como não rejeição torna a certificação praticamente impossível. A emenda metodológica será tratada em PR separada e, por ter sido motivada após observar DEV-B, não altera retroativamente este resultado.

## Curva de cobertura — DESCRITIVA, NÃO CERTIFICADA

A curva abaixo é uma análise descritiva permitida pelo §5.3. **Não constitui certificação nem substitui o resultado 0/11 pela regra original.** Valores indicam maior cobertura observada com acerto ≥90% e pelo menos 25 respostas aceitas.

| Coorte | Limiar | Cobertura | Acerto observado |
|---|---:|---:|---:|
| RAGTruth | 0,54 | 98,0% | 90,1% |
| AggreFact-CNN | 0,81 | 83,8% | 90,1% |
| TofuEval-MeetB | 0,69 | 78,0% | 90,1% |
| ClaimVerify | 0,80 | 73,4% | 91,5% |
| Lfqa | 0,84 | 53,8% | 90,3% |
| TofuEval-MediaS | 0,92 | 51,1% | 90,0% |
| Reveal | 0,83 | 50,7% | 90,5% |
| AggreFact-XSum | 0,92 | 18,8% | 90,4% |
| FactCheck-GPT | 0,95 | 17,8% | 90,5% |
| ExpertQA | — | — | Não alcança 90% com n ≥ 25 |
| Wice | — | — | Não alcança 90% com n ≥ 25 |

A curva descreve somente DEV-B e não deve ser apresentada como desempenho confirmatório ou generalizada para TEST.

## Limitações e interpretação

- Este é um **resultado DEV**, não TEST.
- Não é entrada de ranking e não deve ser descrito como resultado oficial de ranking.
- A frase de síntese permitida é: **“acurácia balanceada cross-fitted de 74,7% na partição DEV (média macro por dataset, pré-registrada)”**.
- FactCG foi selecionado pela regra da #477; essa decisão de seleção não equivale a validação externa.
- ExpertQA é o ponto fraco entre os datasets de FactCG em DEV-A (BA 0,5951).
- A prevalência de SUPPORTED é 76,02% em DEV-A.
- A Camada 3 obteve **nenhuma coorte certificada pela regra registrada**. A curva de cobertura acima é descritiva, não confirmatória.
- Os números não demonstram generalização para dados TEST, produção ou outros domínios.

## Arquivos agregados

Os arquivos originais do artefato `phase1b-dev-full-aggregate` estão nesta pasta, sem modificação: [`phase1b-aggregate.json`](phase1b-aggregate.json) e [`PROVENANCE.json`](PROVENANCE.json). A conferência dos hashes está registrada em [PROVENANCE.md](PROVENANCE.md).

Hashes:
- SHA-256 do arquivo agregado: `106448dcee6dba1b9ae7075125d08a128cc7af19b7a490e0becdfb26bc1680fa`
- Campo `report_sha256`: `d411741824a86ac7cfba0471a8fa71cd89919f13a4e50243e11d0cf1e65e37f2`
- `manifest_sha256`: `deb3ef389553a03bb840e03a1e314e3f4d02dac50f4aa3d1c713c88a9dd55a74`

O artefato `phase1b-dev-full-aggregate` tem retenção de 30 dias. Este repositório não contém dados por instância.

## Componentes de terceiros

Os modelos e o dataset abaixo não foram criados por este projeto. Foram usados sem modificação dos pesos, nas revisões fixadas em [PROVENANCE.md](PROVENANCE.md). O código de avaliação, a calibração, o pré-registro e a infraestrutura deste relatório são do AYORAI ATTRACTOR.

| Componente | Autoria / origem | Licença declarada no Hugging Face |
|---|---|---|
| [FactCG-DeBERTa-v3-Large](https://huggingface.co/yaxili96/FactCG-DeBERTa-v3-Large) | autores do FactCG ([arXiv:2501.17144](https://arxiv.org/abs/2501.17144)); base `microsoft/deberta-v3-large` | MIT |
| [MiniCheck-DeBERTa-v3-Large](https://huggingface.co/lytang/MiniCheck-DeBERTa-v3-Large) | autores do MiniCheck ([arXiv:2404.10774](https://arxiv.org/abs/2404.10774)) | MIT |
| [mDeBERTa-v3-base-xnli-multilingual-nli-2mil7](https://huggingface.co/MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7) | Moritz Laurer | MIT |
| [LLM-AggreFact](https://huggingface.co/datasets/lytang/LLM-AggreFact) | autores do MiniCheck / LLM-AggreFact ([arXiv:2404.10774](https://arxiv.org/abs/2404.10774)) | termos de acesso aceitos em 2026-11-06: somente avaliação de benchmark; pré-treino e fine-tuning proibidos |

## Referências

- [Pré-registro Calibration V2](../../../docs/benchmarks/CALIBRATION-V2-PREREGISTRATION.md)
- [Execução DEV completa — run 42389121599](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/42389121599)
- [Re-agregação — run 42418593837](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/42418593837)
- [PR #481 — correção do aggregate](https://github.com/Ayorinha/ayorai-opensearch/pull/481)
