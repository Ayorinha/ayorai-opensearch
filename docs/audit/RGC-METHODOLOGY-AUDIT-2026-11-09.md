Revisão por ferramenta automatizada, publicada pelo mantenedor.

# Auditoria de continuidade metodológica — RGC PT-BR

**Data da verificação:** 2026-11-09  
**Base Git auditada:** `main` em `ed533aad78e30d31d59cfcd8c073679000f585f9`  
**Natureza:** revisão documental interna de consistência e prontidão. Não é revisão humana independente, parecer jurídico, validação institucional, resultado experimental ou aprovação de congelamento.

## 1. Escopo e limites

Esta auditoria verifica o estado público do repositório, a linhagem da PR #269, a documentação metodológica e o código/testes do executor RGC. Não acessa arquivos privados de anotação ou do piloto.

A alteração documental associada a esta auditoria:
- alinha a identificação de componentes em `docs/eval/STATISTICS.md` à redação aprovada da DEC-023;
- marca como pendentes de confirmação humana os detalhes de RNG/versão e interpolação de quantis que não constam das entradas aprovadas de DEC-021/022;
- registra este retrato e os bloqueios encontrados.

Não são alterados o pré-registro RGC, o protocolo normativo, o executor, testes, Judge, Golden, manifests, hashes, fontes, casos, rótulos, workflows, releases ou tags. Nenhum benchmark foi executado.

## 2. Estado GitHub confirmado

### `main`

- HEAD: [`ed533aad78e30d31d59cfcd8c073679000f585f9`](https://github.com/Ayorinha/ayorai-opensearch/commit/ed533aad78e30d31d59cfcd8c073679000f585f9).
- O commit é o merge da [PR #511](https://github.com/Ayorinha/ayorai-opensearch/pull/511), concluído em 2026-11-09 15:21:43 UTC. A PR adicionou endpoints de verificação documental `/v1/check` e `/v1/fields`, ingestão de PDF e testes; não alterou os artefatos metodológicos RGC.
- No SHA atual foram encontrados **15 check-runs, todos concluídos com `success`**. O endpoint legado de commit statuses retornou zero registros e estado `pending`; esse endpoint vazio não contradiz os 15 check-runs concluídos e não foi usado como evidência de falha de CI.

### PR #269 e linhagem

- [PR #269](https://github.com/Ayorinha/ayorai-opensearch/pull/269): **fechada sem merge**, ainda marcada Draft no registro consultado; fechada em 2026-10-19. Head `f161c14b1bf196dd111e176ac04907d6eaa7f1f3`; cinco commits; dois arquivos no diff (`docs/ARCHITECTURE.md` e `docs/eval/METHODOLOGY-REVIEW-RGC-PTBR-2026-10-18.md`).
- Conversa: três comentários; submissões de review: zero; comentários inline: zero.
- No head da #269: 20 check-runs, **19 success e 1 skipped** (`rgc-design-simulation`); nenhum check-run falhou. Esses checks são históricos do head citado, não checks da main atual.
- A #269 foi substituída pela [#272](https://github.com/Ayorinha/ayorai-opensearch/pull/272), fechada sem merge; a revisão documental foi incorporada pela [#273](https://github.com/Ayorinha/ayorai-opensearch/pull/273), merge commit `5719db48fc82c726671af7c9c7f7ef386d161edb`.
- A [#274](https://github.com/Ayorinha/ayorai-opensearch/pull/274), merge commit `c639d0fda7a6fb8ab29bb438611ee536b1f3ddc2`, corrigiu a derivação da Baseline B a partir da partição pública de desenvolvimento. A [#275](https://github.com/Ayorinha/ayorai-opensearch/pull/275), merge commit `9610d24e81fa9639462b610b8915ee5162a26d2a`, esclareceu o marcador `RULE_GAP` na ficha em branco do piloto 02. Essas tarefas concluídas não devem ser reiniciadas.

### PR #512 — estado não vigente

- [PR #512](https://github.com/Ayorinha/ayorai-opensearch/pull/512) permanece aberta em Draft. Head `57f10f038f132fcdd497e35b377bf68857063a85`; base declarada `22c58088e2a8b58f9fa1879cc2ac81516ebfc6be); dois commits; diff de um arquivo (`docs/STATUS.md`).
- Seus 20 check-runs concluíram com `success`, mas isso valida somente aquele head. Há uma review `COMMENTED` e um comentário do mantenedor registrando que a base está desatualizada após o merge da #511. Não é aprovação nem status vivo da main.
- `docs/STATUS.md` na main ainda declara atualização em 2026-11-08. A fotografia atual de 2026-11-09 deve ser lida neste documento até que uma atualização de status baseada no SHA atual seja revisada.

## 3. Decisões aprovadas preservadas

O índice `docs/DECISIONS-PENDING.md` registra como aprovadas pelo mantenedor:
- **DEC-014:** Baseline B derivada somente dos rótulos da partição pública de desenvolvimento; Baseline A apenas descritiva.
- **DEC-017:** falhas de integridade interrompem; predição presente inválida permanece no denominador como erro.
- **DEC-018:** H1 confirmatória somente na partição oculta.
- **DEC-019:** `bootstrap_cluster_id` é metadado inicial de agrupamento por artigo/`bundle:`.
- **DEC-020:** Cohen's kappa não ponderado e gate pontual `κ ≥ 0,6`, com exclusão/reporting separado de `RULE_GAP`.
- **DEC-021 (2026-11-07):** sign-flip bilateral por componentes conectados é o teste confirmatório primário de H1; McNemar por caso e Obuchowski são sensibilidades.
- **DEC-022 (2026-11-07):** IC95% percentil de kappa por bootstrap de componente; 10.000 reamostragens, seed `20261003`, réplicas indefinidas contabilizadas e instabilidade se exceder 5%; o gate pontual de 0,6 permanece.
- **DEC-023 (2026-11-07):** componentes transitivos por qualquer artigo compartilhado em `cited_article_ids`; o ID aprovado é `component:` + IDs únicos ordenados lexicalmente e unidos por `+`.

DEC-021 a DEC-023 autorizam a especificação documental, não a implementação, execução, alteração do pré-registro/protocolo ou congelamento.

## 4. Conflitos e diferenças comprovados

### RGC-01 — H1: sign-flip aprovado versus McNemar ainda normativo no pré-registro/executor

**Fatos verificados**
- DEC-021 define sign-flip por componente como teste confirmatório primário.
- O §5 de `docs/eval/PREREGISTRATION-RGC-v1.md` ainda condiciona H1 ao McNemar exato bilateral com `p < 0,05`.
- `docs/eval/RUNNER-RGC-v1.md` ainda lista McNemar como comparação e critério.
- `evals/ptbr/rgc_eval.py` importa `mcnemar_exact_pvalue`, calcula o p-valor de McNemar e usa `mcnemar_p_below_0_05` em `h1_supported`.

**Conclusão:** conflito real entre a decisão aprovada e os artefatos normativos/executor. Nenhum resultado confirmatório pode ser calculado ou interpretado até uma emenda datada, autorizada pelo mantenedor, reconciliar os documentos. O pré-registro e o protocolo não foram alterados nesta tarefa.

### RGC-02 — IC de kappa: DEC-022 por componente versus Emenda 10 por caso

**Fatos verificados**
- DEC-022 aprova bootstrap por componente.
- A Emenda 10 de `PROTOCOL-GOLDEN-V1.md` ainda especifica IC95% por bootstrap de casos.
- `evals/ptbr/rgc_agreement.py` usa `random.Random(seed)`, sorteia índices individuais de casos e publica `ci95_case_bootstrap`.
- `tests/test_rgc_agreement.py` cobre a versão por caso, não o bootstrap por componente.

**Conclusão:** a ferramenta de concordância não implementa DEC-022. A reconciliação normativa e a implementação continuam pendentes; não processar anotações humanas sob uma especificação conflitante.

### RGC-03 — Identificador de componente

**Fatos verificados**
- DEC-023, no índice aprovado, define `component:` + IDs de artigos únicos em ordem lexical, unidos por `+`.
- A redação anterior de `docs/eval/STATISTICS.md` especificava outro identificador (`component:sha256:` sobre JSON canônico).

**Correção documental desta PR:** `STATISTICS.md` foi alinhado à forma explícita da DEC-023. Nenhum ID real foi calculado e nenhum caso foi lido ou modificado.

### RGC-04 — Parâmetros operacionais não especificados nas entradas de decisão

**Fatos verificados**
- DEC-021 fixa 10.000 sorteios e seed para `K > 20), mas não nomeia PRNG, versão de biblioteca ou ordem de consumo.
- DEC-022 fixa bootstrap por componente, número de reamostragens e seed, mas não define PRNG/versão nem método de interpolação dos quantis.
- A redação anterior de `STATISTICS.md` tratava NumPy 2.3.3/PCG64 e quantil linear como fixados.

**Correção documental desta PR:** esses detalhes passam a ser marcados como pendentes de confirmação explícita do mantenedor. Nenhuma escolha foi feita nesta auditoria.

### RGC-05 — Executor e testes ainda não implementam DEC-021–023

**Fatos verificados**
- `rgc_eval.py` mantém bootstrap por `bootstrap_cluster_id`, usando `random.Random(SEED)`; não constrói a união transitiva de todos os `cited_article_ids` nem implementa sign-flip.
- O critério H1 do executor ainda depende de McNemar.
- `rgc_agreement.py` ainda usa bootstrap por caso.
- Os testes RGC consultados cobrem as rotinas antigas com fixtures sintéticas; não foram encontrados testes para componentes transitivos, sign-flip ou bootstrap de kappa por componente.

**Limite:** DEC-021–023 registram que a implementação ainda não está autorizada. Esta PR não altera código nem adiciona testes de execução.

## 5. Piloto, congelamento e dados

- A ficha versionada `docs/eval/PILOT-RGC-02-WORKSHEET.md` continua sendo um formulário em branco, com instruções explícitas de preenchimento humano, sem consulta a IA e sem executar o ATTRACTOR sobre casos do piloto.
- `docs/eval/PROTOCOL-FREEZE.json` não existe na main consultada; há somente o template de freeze.
- Não foram acessados arquivos privados do piloto, nem criados, completados ou rotulados casos. O sistema não foi executado sobre casos do piloto ou benchmark nesta tarefa.
- O protocolo RGC permanece **[PROPOSTO]**, não congelado. A documentação de status consultada não publica resultado de benchmark RGC.

## 6. Próximos passos e gates

1. **Pendente do mantenedor:** confirmar os parâmetros operacionais de reprodutibilidade (PRNG/versão, ordem dos sorteios e interpolação dos quantis), ou decidir explicitamente que não serão fixados além do que já consta nas DEC.
2. **Pendente de emenda autorizada:** reconciliar o critério H1 no pré-registro e na especificação do runner com DEC-021.
3. **Pendente de emenda autorizada:** reconciliar a Emenda 10/DEC-020 com DEC-022 no protocolo e nos documentos de execução.
4. **Após autorização específica para implementação:** desenvolver componentes, sign-flip e bootstrap de kappa em branch/PR, usando exclusivamente fixtures sintéticas nos testes; não executar RGC real.
5. **Gate humano independente:** piloto 02 manual sem IA e sem execução do sistema; segunda anotação humana independente, adjudicação, revisão F-01, proveniência e isolamento da partição oculta.
6. **Decisões separadas:** eventual aprovação do protocolo, congelamento e execução continuam dependendo de autorização explícita posterior do mantenedor.

## 7. Evidência e reprodutibilidade desta auditoria

- Base: `main` SHA `ed533aad78e30d31d59cfcd8c073679000f585f9`.
- CI da base: 15/15 check-runs concluídos com sucesso.
- PR #269: head `f161c14b1bf196dd111e176ac04907d6eaa7f1f3`; 19/20 success, 1 skipped; 3 comentários; 0 reviews; 0 inline comments.
- PR #512: head `57f10f038f132fcdd497e35b377bf68857063a85`; 20/20 success, mas base antiga e Draft.
- Arquivos metodológicos lidos na main: `docs/DECISIONS-PENDING.md`, `docs/eval/STATISTICS.md`, `docs/eval/PREREGISTRATION-RGC-v1.md`, `docs/eval/PROTOCOL-GOLDEN-V1.md`, `docs/eval/RUNNER-RGC-v1.md`, `evals/ptbr/rgc_eval.py`, `evals/ptbr/rgc_agreement.py` e testes RGC correspondentes.

**Este documento é uma auditoria interna de consistência. Não representa validação externa, aprovação científica independente, congelamento de protocolo ou autorização de execução.**


---

## Adendo de revalidação — 2026-11-11

Este adendo atualiza os fatos de continuidade sem reescrever o snapshot de 2026-11-09. Ele não altera decisões, não aprova método, não congela o protocolo e não autoriza implementação ou execução.

### 1. `main` e CI no estado reconsultado

- HEAD atual: [`b64e56d28e49f1d680e2b281f2b11e0acb39914a`](https://github.com/Ayorinha/ayorai-opensearch/commit/b64e56d28e49f1d680e2b281f2b11e0acb39914a), commit de 2026-11-11 07:12:17 UTC (`ci: validate benchmark and artifact dependency pins`, PR #525).
- O endpoint de check-runs retornou **13/13 concluídos com `success`** nesse SHA. CI: [run 42977783041](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/42977783041); Security: [run 42977782962](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/42977782962); CodeQL: [run 42977782987](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/42977782987).
- O endpoint legado de commit statuses não retornou registros. Isso não foi interpretado como falha: os 13 check-runs individuais do SHA foram consultados diretamente.
- A comparação de `ed533aad78e30d31d59cfcd8c073679000f585f9` até o HEAD atual mostra cinco commits novos. Os arquivos alterados nesse intervalo são workflows, `AGENTS.md` e código/testes da API; não aparecem alterações no pré-registro, protocolo, executor, ferramenta de concordância ou testes metodológicos RGC.
- `docs/STATUS.md` na `main` ainda registra atualização em 2026-11-08. A atualização de status datada de 2026-11-11 está proposta na #512 e ainda não foi integrada.

### 2. PR #269 e linhagem — confirmação atual

- [#269](https://github.com/Ayorinha/ayorai-opensearch/pull/269) continua **fechada sem merge**, em estado Draft no registro do GitHub; head `f161c14b1bf196dd111e176ac04907d6eaa7f1f3`, cinco commits e dois arquivos alterados. O diff inclui a alteração incidental em `docs/ARCHITECTURE.md` e o documento de revisão metodológica.
- A conversa tem três comentários; não há submissões de revisão nem threads inline.
- No head histórico da #269, os 20 check-runs são: **19 success, 1 skipped** (`rgc-design-simulation`) e zero falhas. Esses resultados não são checks da `main` atual.
- [#272](https://github.com/Ayorinha/ayorai-opensearch/pull/272) também foi fechada sem merge. A revisão documental final foi incorporada pela [#273](https://github.com/Ayorinha/ayorai-opensearch/pull/273), merge commit `5719db48fc82c726671af7c9c7f7ef386d161edb`, com alteração apenas do documento metodológico.
- A correção da Baseline B já foi integrada pela [#274](https://github.com/Ayorinha/ayorai-opensearch/pull/274), commit `c639d0fda7a6fb8ab29bb438611ee536b1f3ddc2`. O esclarecimento de `RULE_GAP` somente no piloto já foi integrado pela [#275](https://github.com/Ayorinha/ayorai-opensearch/pull/275), commit `9610d24e81fa9639462b610b8915ee5162a26d2a`. Não reiniciar essas tarefas.

### 3. PRs documentais em andamento

- [#514](https://github.com/Ayorinha/ayorai-opensearch/pull/514) permanece aberta em Draft. Antes deste adendo, seu head era `dfd4b8ec7188a57b925f4d1b12d818c9359592c7`, com 20/20 check-runs e 7/7 workflow runs concluídos com sucesso; tinha um comentário de conversa, nenhuma submissão formal de review e nenhuma thread inline. O diff contém somente `docs/eval/STATISTICS.md` e este relatório.
- A #514 foi criada sobre `ed533aad78e30d31d59cfcd8c073679000f585f9`. Após a inclusão deste adendo, a comparação com a `main` atual mostra a branch **4 commits à frente e 5 atrás**; os cinco commits novos da `main` não tocaram os arquivos RGC envolvidos. O PR continua Draft e não deve ser mesclado nem considerado sincronizado por causa dos checks do head anterior. Qualquer novo commit exige rechecagem do SHA exato.
- [#512](https://github.com/Ayorinha/ayorai-opensearch/pull/512) permanece aberta em Draft, com diff restrito a `docs/STATUS.md`, head atual `7df2fb5e1355f8b94c625953e9dc8f4d036e9034` e base `b64e56d28e49f1d680e2b281f2b11e0acb39914a`. No head atual foram encontrados sete workflow runs, todos ainda **queued**; não há conclusão verde a declarar. A review `COMMENTED` e os 20 checks citados em registros anteriores pertencem a um head anterior e não são transferíveis ao head atual.
- Na #514, a alteração proposta em `STATISTICS.md` corrige o identificador de componente para a forma da DEC-023 e deixa PRNG/versão/ordem/interpolação como detalhes não aprovados. Essa correção ainda não está na `main`; a versão da `main` mantém a forma anterior `component:sha256:` e parâmetros operacionais que não constam das decisões aprovadas.

### 4. Revalidação metodológica no código e nos testes da `main`

A comparação documental e a inspeção dos arquivos atuais confirmam que os conflitos RGC-01 a RGC-05 descritos acima continuam presentes:

1. **H1 — DEC-021 versus pré-registro/executor:** DEC-021 aprova sign-flip bilateral por componente como teste confirmatório primário. O §5 do pré-registro ainda usa McNemar exato como condição de H1; `rgc_eval.py` calcula `mcnemar_exact_pvalue` e inclui `mcnemar_p_below_0_05` em `h1_supported`. McNemar deve permanecer apenas como sensibilidade segundo a decisão aprovada.
2. **IC de kappa — DEC-022 versus protocolo/executor:** DEC-022 aprova bootstrap por componente. A Emenda 10 ainda descreve bootstrap por caso; `rgc_agreement.py` usa `random.Random(seed)`, sorteia índices de casos com `randrange(n)` e reporta `ci95_case_bootstrap`. Os testes de concordância continuam cobrindo bootstrap por caso, não por componente.
3. **Unidade final — DEC-023 versus executor:** DEC-023 exige componentes conectados transitivamente quando quaisquer casos compartilham artigo em `cited_article_ids`. O runner ainda agrupa diretamente por `bootstrap_cluster_id` (DEC-019), sem construir a união transitiva dos artigos citados. Os testes existentes validam clusters e bundles de entrada, mas não a construção de componentes transitivos.
4. **Reprodutibilidade:** DEC-021/022 fixam número de reamostragens e seed, mas não fixam PRNG/versão, ordem de consumo ou interpolação dos quantis. Esses parâmetros continuam pendentes de decisão explícita; não adotar silenciosamente NumPy/PCG64, `random.Random` ou um método de quantil como se já fossem exigência aprovada.
5. **Escopo da aprovação:** DEC-021 a DEC-023 autorizam apenas preparar a PR documental. Não autorizam alterar o pré-registro, o protocolo, o executor ou os testes metodológicos; tampouco autorizam execução ou congelamento. A implementação permanece bloqueada até autorização específica e reconciliação normativa.

### 5. Estado humano e salvaguardas

- O protocolo RGC continua **[PROPOSTO]**, não congelado. `docs/eval/PROTOCOL-FREEZE.json` não existe na `main`; a ficha do Piloto 02 continua em branco.
- Piloto 02 manual sem IA e sem executar o sistema, segunda anotação independente, adjudicação, revisão humana independente F-01, proveniência por dispositivo e isolamento da partição oculta permanecem pendentes.
- Nenhum arquivo privado de anotação/piloto foi acessado nesta revalidação. Nenhum caso foi criado, visto, completado ou rotulado; o ATTRACTOR não foi executado em casos RGC.
- Não há resultado de benchmark RGC nem validação externa a declarar.

**Próximos gates:** decisão humana sobre os detalhes operacionais ainda não especificados; autorização/emenda datada para reconciliar pré-registro e protocolo com DEC-021/022; autorização específica de implementação em branch/PR com fixtures sintéticas; e conclusão dos gates humanos do piloto e da anotação. Nenhum desses gates é satisfeito por este adendo.
