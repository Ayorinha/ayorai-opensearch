# Registro de continuidade — RGC PT-BR

**Data:** 2026-10-22  
**SHA de main observado:** `33393f84da6c2ade4c40f628c683dd793a5dfa02` ([commit](https://github.com/Ayorinha/ayorai-opensearch/commit/33393f84da6c2ade4c40f628c683dd793a5dfa02))  
**Natureza:** fotografia documental. Não aprova nem congela o protocolo e não é validação científica.

## Estado do repositório

- `main`: check-runs 12/12 concluídos com sucesso, incluindo testes Python 3.11–3.13, regressões Judge/Golden e Security. Evidências: [CI](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/39760225707) e [Security](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/39760225780).
- O endpoint de status combinado não retornou registros e exibiu `pending`; não o registrar como verde. O ruleset `Protecao-main-ATTRACTOR` está ativo e exige PR e checks obrigatórios.
- [PR #269](https://github.com/Ayorinha/ayorai-opensearch/pull/269): fechada sem merge; seus comentários informam substituição pela [#272](https://github.com/Ayorinha/ayorai-opensearch/pull/272), também fechada sem merge. A revisão atual está no arquivo `docs/eval/METHODOLOGY-REVIEW-RGC-PTBR-2026-10-18.md`; não atribuir merge à #269.
- [PR #398](https://github.com/Ayorinha/ayorai-opensearch/pull/398): aberta, sem review/comentários; head `d2cf29aa4fbb9b519955b22e3b036a9a18f3c9b6`. O diff limita-se à validação estrita de JSONL e testes sintéticos. Foram observados 20/20 check-runs com sucesso ([CI](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/39761814878), [Security](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/39761814840)). Não aprovada nem mergeada nesta tarefa.

## Estado metodológico

| Achado | Situação confirmada | Limite pendente |
|---|---|---|
| M-01 | Resolvido documentalmente: RGC usa cinco estados `judge2`; matriz ADR-002 6×6 é histórica. | Preservar Goldens históricos. |
| M-02 | DEC-017: registro ausente/inconsistente interrompe; predição presente inválida conta como erro. | Nenhuma avaliação confirmatória ocorreu. |
| M-03 | DEC-019: bootstrap por cluster de artigo primário; bootstrap por caso como sensibilidade. | Sem casos reais ou métricas RGC. |
| M-04 | DEC-020 define kappa não ponderado, gate pontual ≥ 0,6, IC95% e relatório de concordância. | Anotações humanas ainda não processadas. |
| M-05 | Aberto: hashes não provam que anotadores A/B são pessoas diferentes ([PR #387](https://github.com/Ayorinha/ayorai-opensearch/pull/387)). | Atestação humana; eventual schema adicional requer decisão do mantenedor. |
| M-06 | Aberto: 300 é meta condicionada, não quota. | Plano de cobertura/precisão após o piloto, sem fabricação de casos. |
| M-07 | DEC-018: H1 só na partição oculta; B deriva da partição pública e é primária; A é descritiva. | Partição real e isolamento ainda não verificados. |
| M-08 | Proveniência, vigência e retificação documentadas. | Conferência por caso ainda pendente. |
| M-09 | Limites de contaminação/generalização documentados. | Sem avaliação RGC de robustez; conjunto oculto não prova ausência de contaminação prévia. |
| M-10 | Piloto exploratório separado do confirmatório. | Piloto 02 humano e decisão explícita de congelamento pendentes. |
| M-11 | Emenda 6 alinha baseline A/B à DEC-014. | Consistência documental não demonstra desempenho. |
| F-01 | Revisão independente permanece aberta. | CI e revisão automatizada não são validação externa. |

## Portões ainda obrigatórios

1. Piloto 02 manual, sem IA e sem executar o ATTRACTOR; depois, descartar os casos e registrar apenas achados metodológicos.
2. Duas anotações humanas independentes, divergências/adjudicação, relatório de concordância e atestações/aprovações exigidas.
3. Plano de cobertura sem quotas artificiais; conjunto oculto fora do repositório público e com proveniência controlada.
4. Protocolo permanece **[PROPOSTO]** até revisão do piloto e decisão explícita do mantenedor; F-01 continua aberto.

## Limites

Esta nota não altera protocolo, pré-registro, Judge, Golden, manifests, hashes, fontes capturadas, decisões aprovadas, dados do piloto ou releases. Nenhum caso foi criado/rotulado por IA, nenhum caso RGC foi executado pelo sistema e nenhuma métrica RGC foi produzida.
