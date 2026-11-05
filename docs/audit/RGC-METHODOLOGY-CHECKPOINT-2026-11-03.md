Revisão por ferramenta automatizada, publicada pelo mantenedor.

# RGC PT-BR — checkpoint metodológico e de continuidade

**Data da verificação:** 2026-11-03  
**Natureza:** auditoria documental automatizada, não independente; não constitui aprovação, congelamento, validação científica, jurídica, institucional ou revisão humana independente.  
**Repositório:** Ayorinha/ayorai-opensearch  
**Base observada:** main em e7bce5c56955700b29e0baf9d90d60ca4320f314

## 1. Escopo e salvaguardas

Esta nota registra o estado do repositório, a linhagem da revisão iniciada na PR #269, os checks consultados e uma revisão cruzada das decisões metodológicas RGC com o executor e os testes existentes.

Não foram alterados Judge, Golden, pré-registro, protocolo normativo, decisões aprovadas, manifests, hashes, fontes capturadas, dados ou artefatos de piloto/benchmark. Não foram criados nem rotulados casos, não foi executado o ATTRACTOR sobre casos RGC e não foram calculadas métricas de benchmark. Nenhuma decisão humana foi tomada nesta nota.

## 2. Estado Git confirmado

- O commit mais recente observado na consulta de commits do repositório é e7bce5c56955700b29e0baf9d90d60ca4320f314, mensagem “ci: add manual merged-branch cleanup workflow (#412)”, criado em 2026-10-26T10:00:36Z.
- As PRs abertas #413, #417 e #420 consultadas usam esse mesmo SHA como base de main.
- docs/STATUS.md continua com atualização datada de 2026-10-25 e referência de main anterior, 4f3c0cea4e40df5141521c4a12010bc3da5ac365. O arquivo não foi alterado nesta revisão, pois seu conteúdo é um registro de status protegido por governança.
- A consulta de status combinado para e7bce5c não retornou entradas. A consulta de workflows disponível para commits é filtrada para execuções disparadas por pull request; portanto, ela não permite concluir o estado de workflows de push pós-merge. **O CI pós-merge da main não está confirmado por esta verificação.** Ausência de registros não é evidência de sucesso nem de falha.

## 3. PR #269 e linhagem documental

### PR #269

- Link: https://github.com/Ayorinha/ayorai-opensearch/pull/269
- Estado: fechada sem merge; o metadado ainda a identifica como Draft.
- Head observado: f161c14b1bf196dd111e176ac04907d6eaa7f1f3.
- Base SHA no momento da PR: 71e682c97bb12788ef95e799d889a2454bfdd0eb.
- Conversa: 3 comentários. Submissões de revisão: 0. Threads inline: 0.
- Checks consultados no head original: 7/7 workflows concluídos com sucesso — CI, CodeQL, Security, Dependency Review, API Contract Guard, Schemathesis Full API Contract e Golden r2 Migration.
- A PR não foi mesclada e não deve ser reaberta como se fosse a continuação ativa.

### Substituição e incorporação

- A PR #272 também foi fechada sem merge e substituída pela #273.
- A PR #273 foi mesclada em 2026-10-20T11:01:52Z; os sete workflows consultados no head da PR concluíram com sucesso. Ela incorporou a revisão metodológica documental.
- A PR #274 foi mesclada em 2026-10-20T10:29:02Z; os oito workflows consultados no head concluíram com sucesso. Corrigiu o executor para derivar a baseline B exclusivamente dos rótulos da partição pública de desenvolvimento e usar B — não A — nos critérios de H1.
- Os checks citados pertencem aos heads das respectivas PRs, não são checks pós-merge da main atual.

## 4. PRs Draft relevantes no estado consultado

| PR | Estado e head | Diff | Checks consultados |
|---|---|---:|---|
| [#413](https://github.com/Ayorinha/ayorai-opensearch/pull/413) | Aberta, Draft; 53d31dd802676198c3c9c6fec6aacf88955034a8 | 4 arquivos documentais | 7/7 workflows concluídos com sucesso |
| [#417](https://github.com/Ayorinha/ayorai-opensearch/pull/417) | Aberta, Draft; c860edd408ef5f18c2f2f97ba5300b24cccac474 | 6 arquivos; templates em branco | 8/8 workflows concluídos com sucesso, incluindo RGC Design Simulation |
| [#420](https://github.com/Ayorinha/ayorai-opensearch/pull/420) | Aberta, Draft; a9a02027c84acd0ef7fac7b2ffde8b8ab33eab81 | 2 arquivos: evals/ptbr/rgc_eval.py e tests/test_rgc_eval_runner.py | 8/8 workflows concluídos com sucesso |

### PR #413 — limpeza editorial histórica

O diff propõe distinguir propostas antigas do estado vigente de DEC-017–DEC-020 em documentos de decisão, estatística, manual e proposta de emenda. É documental e não altera regras do Judge, Golden, manifests ou casos. Permanece Draft; nenhum merge ou aprovação foi realizado nesta revisão.

### PR #417 — templates de gates humanos

O diff adiciona modelos vazios para declaração de independência, adjudicação, freeze e aprovação de anotação, além de documentação de custódia. Os placeholders são DRAFT e não constituem aprovações. O head atual consultado tem 8/8 workflows concluídos com sucesso. A simulação RGC desse workflow é sintética e não é execução do benchmark.

### PR #420 — integridade do runner

O head atual é a9a02027c84acd0ef7fac7b2ffde8b8ab33eab81, cujo commit mais recente corrige as quebras de linha escapadas nas fixtures JSONL. O diff:
- valida evidências oracle sem coerção de offsets, com IDs de documento conhecidos, trechos não vazios e igualdade exata com o texto-fonte;
- valida átomos e registros JSONL estritamente;
- exige correspondência exata dos IDs dos casos com os IDs das anotações A e B;
- rejeita rótulo RULE_GAP na partição oculta definitiva;
- faz preflight dos casos antes de chamar o preditor, evitando execução parcial se um caso posterior for inválido;
- mantém os testes novos com dados sintéticos.

O workflow CI do head concluiu com sucesso, incluindo jobs Python 3.11, 3.12 e 3.13, Ruff check/format, mypy estrito para os módulos RGC, pytest, regressões Judge/Golden, lint de workflows e build de distribuições. Os outros sete workflows também concluíram com sucesso. Não há comentários, submissões de revisão ou threads inline registrados na PR #420 no momento da consulta. A PR permanece Draft e não foi mesclada.

## 5. Revisão metodológica cruzada

A leitura do pré-registro, protocolo, STATISTICS.md, RUNNER-RGC-v1.md, DECISIONS-PENDING.md, executor e testes confirma os seguintes contratos aprovados. Eles devem ser preservados:

1. **Vocabulário — DEC-007:** cinco vereditos nominais de judge2 para RGC. A matriz 6×6 ADR-002 é histórica e não define o espaço de rótulos do RGC.
2. **Baseline — DEC-014 / Emenda 6:** B é a baseline primária, derivada exclusivamente dos rótulos humanos da partição pública de desenvolvimento, registrada antes da avaliação oculta e aplicada sem alteração. A é apenas uma baseline-oráculo descritiva da prevalência da partição avaliada e não participa de H1.
3. **Integridade — DEC-017 / Emenda 7:** registro ausente, duplicado, desconhecido ou estruturalmente inconsistente interrompe a execução. Uma predição presente, mas não mapeável ao vocabulário, permanece no denominador como INVALID_PREDICTION e conta como erro.
4. **H1 — DEC-018 / Emenda 8:** somente a partição oculta é confirmatória. A partição pública é de desenvolvimento e descrição; não entra no teste H1.
5. **Incerteza — DEC-019 / Emenda 9:** bootstrap percentil por cluster de artigo é primário para H1; bootstrap por caso é sensibilidade. O executor preserva a multiplicidade quando um cluster é sorteado mais de uma vez e reporta a contagem de clusters.
6. **Concordância — DEC-020 / Emenda 10:** Cohen's kappa não ponderado para os cinco rótulos; gate pela estimativa pontual κ ≥ 0,6. O IC95% por bootstrap de casos é reportado, mas seu limite inferior não é gate adicional. RULE_GAP é excluído do kappa e reportado separadamente.

### Correspondência observada no código e nos testes

- development_baseline_label deriva B apenas de development_labels; compute_metrics constrói B a partir desse rótulo e mantém A como estatística descritiva.
- evaluate impede sobreposição de IDs entre desenvolvimento e avaliação e substitui o critério H1 por “não testado” quando a partição declarada é development.
- Em hidden, compute_metrics recebe os bootstrap_cluster_id dos casos; o intervalo por cluster é usado como primário e o intervalo por caso é mantido como sensibilidade.
- O runner diferencia ausência estrutural de predição inválida e reporta INVALID_PREDICTION.
- rgc_agreement.py implementa kappa não ponderado, gate pontual, IC por bootstrap de casos, matriz de confusão, marginais e exclusões RULE_GAP.
- Os testes consultados são sintéticos; eles demonstram comportamento de software sob fixtures, não qualidade de anotações reais nem desempenho do ATTRACTOR no RGC.

### M-12 — proveniência e consistência da atribuição de clusters

**Achado de revisão, não defeito demonstrado em dados reais:** DEC-019 requer bootstrap_cluster_id estável e, para dependência conjunta sem artigo principal único, um bundle com IDs canônicos ordenados; também requer preservar cited_article_ids. No executor atual, a validação da partição oculta exige cluster não vazio e verifica a sintaxe/ordem dos IDs em bundle. A revisão do runner não encontrou validação que confronte bootstrap_cluster_id com cited_article_ids ou com a proveniência documental do caso, nem uma verificação mecânica de atribuições sobrepostas.

**Risco metodológico:** se casos que compartilham dependência documental forem distribuídos em clusters diferentes sem justificativa consistente, a reamostragem poderá tratar observações relacionadas como independentes. A regra aprovada de bundle como unidade própria deve ser preservada; este achado não autoriza redefinir a regra nem alterar DEC-019.

**Recomendação antes do congelamento:** definir e registrar a fonte de verdade dos IDs canônicos, a regra de atribuição de artigo principal/bundle, a conferência de cited_article_ids e o procedimento de auditoria humana da atribuição. Reportar sempre número de clusters e bundles. Se o mantenedor quiser validação automática adicional, fazê-la em PR separada, sem mudar a unidade estatística aprovada. Não criar casos para testar essa regra e não ajustar clusters depois de observar resultados.

### M-13 — número de clusters independentes e interpretação

A meta de aproximadamente 90 casos ocultos não informa, por si só, quantos clusters independentes existirão. DEC-019 já exige reportar a contagem de clusters; a interpretação de intervalos com poucos clusters deve ser descrita como limitação antes da avaliação. Não se propõe agora um novo limiar mínimo nem um gate pós-hoc.

### Ambiguidades editoriais remanescentes

- A redação original do §4 do pré-registro ainda descreve a baseline como calculada na partição avaliada; a Emenda 6 posterior define B como primária e A como descritiva, preservando o texto original como histórico.
- O pré-registro mantém uma “nota corretiva vigente” antiga sobre DEC-018 pendente, seguida por uma nota que a declara superada e pela Emenda 8 aprovada. A leitura correta decorre da emenda aprovada, mas a sequência é editorialmente confusa.
- Propostas antigas de DEC-017/DEC-018 continuam preservadas no protocolo e no registro de decisões, acompanhadas de notas de superação. A PR #413 trata parte dessas ambiguidades em documentos correlatos, mas não altera o pré-registro nem o protocolo.

**Ação conservadora:** preservar o histórico e não editar agora os documentos normativos. Uma futura PR documental pode acrescentar avisos editoriais inequívocos nos trechos históricos, sem alterar as regras aprovadas. A PR #413 deve ser revisada em seu próprio escopo.

## 6. Portões humanos ainda pendentes

1. Realizar o piloto 02 manualmente, sem IA na criação/rotulagem e sem executar o ATTRACTOR sobre os casos; descartar os casos após a revisão metodológica.
2. Obter segunda anotação por pessoa distinta, independente e sem acesso aos rótulos iniciais.
3. Registrar divergências e adjudicação humana, com justificativas rastreáveis às fontes oficiais.
4. Verificar proveniência, vigência, retificações e atribuição de clusters por caso.
5. Comprovar custódia e isolamento real da partição oculta.
6. Concluir a revisão humana independente F-01.
7. Somente após esses gates, o mantenedor poderá decidir separadamente se aprova e congela o protocolo.

O protocolo permanece **[PROPOSTO]**, não congelado. A ausência de um manifesto público PROTOCOL-FREEZE.json na main observada é compatível com esse estado; nenhum manifesto operacional foi criado nesta revisão.

## 7. Resultado desta revisão

- A revisão original da PR #269 não foi reiniciada: sua linhagem documental está incorporada pela #273, e a correção técnica de baseline B está na #274.
- O estado atual de #413, #417 e #420 foi registrado com seus heads e checks específicos.
- Foi identificado M-12, sobre proveniência/consistência da atribuição de clusters, e M-13, sobre a interpretação com poucos clusters. Ambos são pontos de revisão pré-freeze, não defeitos confirmados em dados reais.
- Nenhuma PR foi aprovada ou mesclada; nenhuma regra científica foi alterada.
- Não há casos RGC criados/rotulados nesta revisão, execução do sistema, cálculo de concordância real, métrica de benchmark ou validação externa.

## 8. Referências principais

- [PR #269 — revisão original](https://github.com/Ayorinha/ayorai-opensearch/pull/269)
- [PR #273 — incorporação documental](https://github.com/Ayorinha/ayorai-opensearch/pull/273)
- [PR #274 — baseline B no executor](https://github.com/Ayorinha/ayorai-opensearch/pull/274)
- [PR #413 — limpeza editorial](https://github.com/Ayorinha/ayorai-opensearch/pull/413)
- [PR #417 — templates dos gates humanos](https://github.com/Ayorinha/ayorai-opensearch/pull/417)
- [PR #420 — integridade do runner](https://github.com/Ayorinha/ayorai-opensearch/pull/420)
- [CI #420 — run 41738895240](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/41738895240)
- [RGC Design Simulation #420 — run 41738895261](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/41738895261)
- [docs/STATUS.md](https://github.com/Ayorinha/ayorai-opensearch/blob/main/docs/STATUS.md)
- [PREREGISTRATION-RGC-v1.md](https://github.com/Ayorinha/ayorai-opensearch/blob/main/docs/eval/PREREGISTRATION-RGC-v1.md)
- [PROTOCOL-GOLDEN-V1.md](https://github.com/Ayorinha/ayorai-opensearch/blob/main/docs/eval/PROTOCOL-GOLDEN-V1.md)
- [STATISTICS.md](https://github.com/Ayorinha/ayorai-opensearch/blob/main/docs/eval/STATISTICS.md)
- [RUNNER-RGC-v1.md](https://github.com/Ayorinha/ayorai-opensearch/blob/main/docs/eval/RUNNER-RGC-v1.md)
- [ANNOTATOR-AGREEMENT.md](https://github.com/Ayorinha/ayorai-opensearch/blob/main/docs/eval/ANNOTATOR-AGREEMENT.md)


## 9. Rechecagem de continuidade — 2026-11-04 (São Paulo)

Esta seção complementa o checkpoint anterior; não reabre tarefas concluídas nem substitui os registros históricos.

### Main e mudanças recentes

- **Main:** `e4471b87560cdd3518ea087791a747c5870793e1`, commit de atualização `actions/setup-python` para 7.1.0 via PR [#419](https://github.com/Ayorinha/ayorai-opensearch/pull/419), em 2026-11-04T20:45:21Z.
- A atualização anterior [#418](https://github.com/Ayorinha/ayorai-opensearch/pull/418) elevou `github/codeql-action` para 4.39.1; seu merge commit é `c1605e750dfa67d7b29e8a9d3da3bc017c9c7a29`.
- No SHA exato da main `e4471b8`, os **13 check runs** retornados estão concluídos com sucesso: CI (13 jobs), Security e CodeQL. [CI run 41909610488](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/41909610488), [Security 41909610613](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/41909610613), [CodeQL 41909610476](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/41909610476). Isso é evidência de engenharia no SHA, não validação científica RGC.

### PR #269 e linhagem já concluída

- [PR #269](https://github.com/Ayorinha/ayorai-opensearch/pull/269) permanece **fechada sem merge** (head `f161c14b1bf196dd111e176ac04907d6eaa7f1f3`). Na consulta atual: 3 comentários de conversa, 0 reviews submetidos e 0 threads inline. O head tinha 20 check runs concluídos: 19 success e `rgc-design-simulation` skipped por condição de workflow.
- Comentários da #269 registram sua substituição pela #272; a #272 também fechou sem merge. A revisão documental efetiva está incorporada pela [#273](https://github.com/Ayorinha/ayorai-opensearch/pull/273) (merge `5719db48fc82c726671af7c9c7f7ef386d161edb`), e a correção de baseline B pela [#274](https://github.com/Ayorinha/ayorai-opensearch/pull/274) (merge `c639d0fda7a6fb8ab29bb438611ee536b1f3ddc2`). Não reiniciar a #269.

### PR #421 — checkpoint anterior

- O head anterior `da37f248b6f227ed4e64cb0104075613b6b69a24` teve **20/20 checks success**. Esta atualização documental é um novo commit no mesmo Draft; seus checks próprios devem ser lidos no SHA novo, não herdados do head anterior.
- [PR #421](https://github.com/Ayorinha/ayorai-opensearch/pull/421) continua Draft, sem merge.

### PR #432 — consistência cluster↔citações

- Head inicial `9e9bc0d4732729edf3f10204651ce951680b4660`: CI falhou exclusivamente em `ruff format --check .` nos dois arquivos modificados; `ruff check .` passou. Python 3.11/3.12 foram cancelados após a falha no job 3.13. Os outros workflows, incluindo RGC Design Simulation, passaram.
- Correção estritamente de formatação enviada na mesma branch: `ecdd3c5865fadc380e5534eb2337028a213b9838` (`evals/ptbr/rgc_eval.py`) e `06a43b13daf0723d7b5666cbf5fb1a690332cb07` (`tests/test_rgc_eval_runner.py`). A autoria/committer dos quatro commits da PR foi confirmada como `ANDERSON AYORA <ayora.anderson@gmail.com>`. O diff segue limitado aos dois arquivos do executor/testes.
- No head `06a43b13daf0723d7b5666cbf5fb1a690332cb07`, a consulta mais recente retornou 20 check runs: 4 success e 16 in progress. **CI completo ainda pendente**; não declarar verde até terminar. A PR continua Draft e a API reporta estado `behind` em relação à main atual.
- [PR #432](https://github.com/Ayorinha/ayorai-opensearch/pull/432) recebeu comentário metodológico complementar. A validação é condicional: `validate_cluster_citations()` retorna sem checar quando `cited_article_ids` está ausente. DEC-019 diz que a lista completa de citações é preservada “quando aplicável”; permanece **decisão humana pendente** esclarecer se a lista deve ser obrigatória para todos os casos ocultos com artigo citado, especialmente bundles. Se a ausência for permitida, o relatório deve explicitar que a checagem de citações foi parcial. A função não verifica relevância jurídica nem se todos os artigos do bundle são substantivamente necessários.

### PR #431 — resumo do README

- O README foi corrigido para rotular os números de 1.201 testes, 95% de cobertura e mypy em 91 arquivos como **snapshot histórico de 2026-10-25**, vinculado ao SHA `4f3c0cea4e40df5141521c4a12010bc3da5ac365`; não é o HEAD atual.
- Commit `561665c93d785895d2771ac5fb4855123b0b5a64`, somente `README.md`; autoria e committer verificados. Os **20/20 checks** do novo head passaram. [PR #431](https://github.com/Ayorinha/ayorai-opensearch/pull/431) continua Draft e sem merge. `docs/STATUS.md` não foi alterado.

### Limites e pendências preservados

- Nenhuma alteração em Judge, Golden, regras, manifests, hashes, pré-registro ou protocolo normativo; nenhum caso de piloto/benchmark foi criado ou rotulado por IA; nenhum caso foi executado; nenhuma métrica RGC foi produzida.
- O protocolo continua **[PROPOSTO]**, não congelado. Piloto 02 humano sem IA e sem execução, segunda anotação independente, adjudicação/proveniência, revisão F-01 e decisão explícita do mantenedor continuam pendentes.
- CI verde é específico do SHA e não substitui revisão humana independente nem validação externa.
