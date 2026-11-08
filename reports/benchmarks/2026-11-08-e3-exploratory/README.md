# E3 — relatório de resultado exploratório em DEV-A (2026-11-08)

**Status:** resultado exploratório, não confirmatório.  
**Autoria:** ANDERSON AYORA.  
**Pré-registro:** `docs/benchmarks/PREREG-E3-ENSEMBLE-v0.8.md`, aprovado em 2026-11-08 para execução exploratória em DEV; não autoriza TEST.  
**Decisão metodológica:** DEC-024, Opção B.  
**Escopo:** registro documental de resultados agregados. Não altera código, Judge, Golden, thresholds de produção, elegibilidade congelada, workflow, cache ou protocolo.

## 1. Resumo executivo

A configuração **E3b-01 (FactCG + MiniCheck-DeBERTa-v3-Large, média de logits com clipping fixo)** obteve BA macro DEV-A de **0,7611**, contra **0,7475** do FactCG isolado: diferença de **+0,0136**. O IC95% bootstrap pareado por coorte foi **[+0,0059; +0,0212]**. O ganho pontual supera o limiar prático pré-registrado de +0,005 e o limite inferior do intervalo é positivo.

O resultado justifica selecionar E3b-01 como **candidata exploratória** para a próxima etapa metodológica, não como substituta confirmada, modelo de produção ou certificação. A execução cobre 10 coortes elegíveis, não as 11 coortes originais; **WiCE permaneceu excluída**. O bootstrap com dez clusters é aproximado e potencialmente instável.

O custo agregado informado para E3b-01 foi **8,5848**, contra **4,3036** para FactCG (aproximadamente 2,0×). Em ExpertQA, foi observada variação de **−0,012**. Portanto, o ganho global não significa melhora uniforme em todas as coortes nem eficiência operacional superior.

## 2. Proveniência e escopo observado

| Campo | Valor |
|---|---|
| Repositório | `Ayorinha/ayorai-opensearch` |
| SHA do código executado | `ba65753382cecdff0403461becc976916e30d4b8` |
| Partição | DEV-A |
| Matriz | `exploratory_pre_ledger` |
| Volume informado | 15.214 registros |
| Coortes elegíveis no agregado | 10 |
| Coorte excluída | WiCE |
| Execução de reagregação/cache de origem | [run 42477997402](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/42477997402) |
| Experimento de cache | [run 42485634513](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/42485634513) |
| Execução intermediária | [run 42480384607](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/42480384607) |
| Execução intermediária | [run 42483517733](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/42483517733) |
| SHA-256 do artefato JSON agregado (prefixo/sufixo registrados) | `10b530ab…e732c9` |
| SHA-256 do relatório interno (prefixo/sufixo registrados) | `43dcd7ef…942157` |

Os runs listados são workflows de execução manual já concluídos antes desta PR. Esta PR não os dispara, não os repete e não solicita aprovação de ambiente. Os dados publicados aqui são somente agregados; não são incluídos registros, scores individuais, rótulos ou conteúdo de cache.

## 3. Resultados agregados

Baseline FactCG: **BA macro 0,7475**, custo **4,3036**.

| Configuração | BA macro | Δ vs. FactCG | IC95% bootstrap pareado |
|---|---:|---:|---:|
| E3b-01 — FactCG + MiniCheck, média de logits | **0,7611** | **+0,0136** | **[+0,0059; +0,0212]** |
| E3a-01 — FactCG + MiniCheck, média de probabilidades | 0,7541 | +0,0066 | [+0,0006; +0,0125] |
| E3b-04 — trio, média de logits | 0,7550 | +0,0074 | [−0,0044; +0,0185] |
| E3a-04 — trio, média de probabilidades | 0,7477 | +0,0002 | [−0,0121; +0,0108] |
| E3b-03 — FactCG + mDeBERTa, média de logits | 0,7516 | +0,0041 | [−0,0038; +0,0133] |
| E3a-03 — FactCG + mDeBERTa, média de probabilidades | 0,7439 | −0,0037 | [−0,0257; +0,0124] |
| E3a-02 / E3b-02 | Não avaliáveis | — | — |
| E3a-05 / E3b-05 | Não avaliáveis | — | — |

E3a usa média aritmética de probabilidades IVAP cross-fitted. E3b usa média aritmética de logits após clipping fixo em `[10⁻⁶, 1−10⁻⁶]`, seguida de sigmoid. Não foram ajustados pesos aprendidos. As configurações 02 e 05 não foram avaliáveis na matriz executada, pois os membros adicionais MiniCheck-Flan-T5 e HHEM não estavam disponíveis/elegíveis para compor essas configurações no experimento.

## 4. Interpretação estatística

- E3b-01 excedeu o limiar pré-registrado de ganho prático de **+0,005**.
- O IC95% reportado para E3b-01 ficou acima de zero; isso é evidência favorável dentro desta análise exploratória e deste denominador.
- E3a-01 também superou pontualmente +0,005, mas ficou abaixo de E3b-01 em BA.
- E3b-04 superou pontualmente +0,005, porém seu intervalo inclui zero; não se deve descrevê-lo como evidência inequívoca de ganho.
- E3b-03 não atingiu o limiar pontual de +0,005.
- E3a-04 ficou praticamente no baseline; E3a-03 ficou abaixo.
- Com **K=10 coortes**, o bootstrap por cluster fornece intervalo aproximado, sensível à composição e ao pequeno número de clusters. Não equivale a validação externa nem prova generalização para novas famílias de datasets.
- A queda de **0,012 em ExpertQA** deve ser mantida visível na interpretação: a média macro positiva pode coexistir com regressões localizadas.

O relatório não recalcula nem modifica métricas, folds, seed, limiar, conjunto de coortes ou critérios após os resultados. Valores apresentados são os agregados fornecidos pela execução registrada.

## 5. Custo e trade-offs

| Sistema | Custo agregado informado | Comparação |
|---|---:|---:|
| FactCG | 4,3036 | 1,00× |
| E3b-01 | 8,5848 | aproximadamente 2,00× |

O ganho de BA de E3b-01 vem acompanhado de custo aproximadamente duplicado. Antes de qualquer decisão de produto, medir latência p50/p95, throughput, memória, falhas e custo por unidade de trabalho sob ambiente comparável. O resultado atual não contém evidência suficiente para afirmar eficiência custo-benefício superior.

## 6. Limitações e classificação do resultado

1. **Exploratório:** a matriz é `exploratory_pre_ledger`; não é a matriz definitiva derivada do ledger A4.
2. **Elegibilidade:** dez coortes foram incluídas; WiCE foi excluída. Comparações futuras devem recalcular baseline e ensemble na mesma interseção de elegibilidade efetivamente aprovada.
3. **Incerteza:** dez clusters são poucos para inferência robusta por bootstrap.
4. **Heterogeneidade:** ExpertQA apresentou queda de 0,012, apesar do ganho macro.
5. **Custo:** E3b-01 custa aproximadamente o dobro do FactCG.
6. **Cobertura:** configurações que dependiam de MiniCheck-Flan-T5 e HHEM não foram avaliáveis.
7. **Generalização:** não há confirmação independente em DEV-B ou TEST.
8. **Produção:** nenhuma mudança no Judge determinístico, thresholds, contratos ou política de resposta é autorizada ou recomendada por este resultado.

**Classificação final:** evidência exploratória promissora para E3b-01 em DEV-A, condicionada à resolução da elegibilidade pelo ledger A4 e à validação independente futura. Não é resultado confirmatório, certificação, benchmark externo nem autorização de produção.

## 7. Próximos gates metodológicos (não executados por este relatório)

- Derivar e revisar a matriz de elegibilidade definitiva a partir do ledger A4; manter este relatório como registro histórico imutável da análise exploratória.
- Recalcular FactCG e ensemble na mesma interseção elegível, sem escolher denominadores após observar o resultado.
- Se houver autorização metodológica posterior, definir uma confirmação única em DEV-B com hipótese, métrica, coortes, denominador, calibradores, limiares e comparador fixados previamente. Não ajustar DEV-B.
- TEST permanece intocado. Qualquer uso futuro exige configuração integralmente congelada, pré-registro próprio, autorização explícita e uma única execução; publicar o resultado independentemente de ser positivo ou negativo.
- O Judge determinístico permanece a única autoridade de veredito. O ensemble é um sinal de avaliação, não uma autorização de execução.

---

*Documento de resultado exploratório. Revisão documental e CI não validam a hipótese científica nem convertem este resultado em confirmação independente.*
