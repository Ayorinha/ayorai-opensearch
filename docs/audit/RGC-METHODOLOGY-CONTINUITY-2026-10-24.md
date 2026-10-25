# RGC PT-BR — verificação de continuidade

**Data da verificação:** 2026-10-24  
**Natureza:** auditoria documental e registro de estado; não é aprovação, congelamento, validação científica, jurídica, institucional ou revisão humana independente.

## 1. Estado Git confirmado

- Repositório: `Ayorinha/ayorai-opensearch`; branch padrão: `main`.
- `main` observado: `6fcdb7d5e5ad1df19aa1d531fec07805b0c5545a`, merge da [PR #402](https://github.com/Ayorinha/ayorai-opensearch/pull/402).
- Os dez workflows da PR #402 passaram no head `d4d8cb0a83bb855b8b07ab108e94905798bd5d85`. Esses resultados são do head da PR, não do SHA de merge.
- Para `6fcdb7d`, a consulta de status combinado retornou zero registros e a consulta de workflows associados ao SHA não retornou runs. **Checks pós-merge da `main` não confirmados.**
- Os commits mais recentes observados incluem #399 (`3f12d54f89da938deb50b6ef58396c7b29efbb86`), #400 (`27cc94863f89de51ffda72223967cbcaa91f27cb`), #401 (`3642e434a88c560d0950fc2c4dbdf7798f2d20ca`) e #402 (`6fcdb7d5e5ad1df19aa1d531fec07805b0c5545a`).

## 2. PR #269 — verificação direta

- [PR #269](https://github.com/Ayorinha/ayorai-opensearch/pull/269): fechada sem merge, ainda marcada Draft no registro retornado; head `f161c14b1bf196dd111e176ac04907d6eaa7f1f3`.
- Comentários de conversa: 3. Submissões de revisão: 0. Threads inline: 0.
- Os sete workflows retornados para esse head estão concluídos com sucesso: [CI](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/39241516692), [CodeQL](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/39241516946), [Security](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/39241516787), [Dependency Review](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/39241516590), [API Contract Guard](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/39241516739), [Schemathesis](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/39241517114) e [Golden r2 Migration](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/39241516646).
- A linhagem documental posterior já está incorporada pela PR #273, mesclada em `5719db48fc82c726671af7c9c7f7ef386d161edb`. Não reiniciar a revisão original nem interpretar #269 como mergeada.

## 3. PR #403 — verificação anterior à atualização documental

- [PR #403](https://github.com/Ayorinha/ayorai-opensearch/pull/403) estava aberta em Draft, base `main`, head observado `e03df9f2c293d62fcdea1b1afe3ac4e273ad8ca1`.
- O diff consultado continha apenas `docs/STATUS.md` e `docs/audit/RGC-METHODOLOGY-CONTINUITY-2026-10-23.md`.
- Não havia comentários de conversa, submissões de revisão ou threads inline.
- Os sete workflow runs do head `e03df9f` concluíram com sucesso: [CI](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/40051166732), [Security](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/40051166743), [CodeQL](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/40051166738), [Dependency Review](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/40051166791), [API Contract Guard](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/40051166773), [Schemathesis](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/40051166745) e [Golden r2 Migration](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/40051166742).
- **Esses resultados validam somente o head anterior `e03df9f`.** A inclusão deste registro e a atualização do STATUS criam novo head; os checks precisam ser executados novamente. Não há aprovação nem merge.

## 4. Revisão metodológica cruzada

A leitura conjunta do pré-registro, protocolo, especificação do executor e decisões confirma as seguintes regras já aprovadas, que devem ser preservadas:

- **Baselines (DEC-014 / Emenda 6):** B é a baseline primária, calculada apenas com rótulos humanos da partição pública de desenvolvimento e aplicada sem alteração à avaliação; A é a baseline-oráculo descritiva da partição avaliada e fica excluída de H1.
- **H1 (DEC-018 / Emenda 8):** análise confirmatória somente na partição oculta; os casos públicos são exploratórios/descritivos.
- **Integridade versus predição (DEC-017 / Emenda 7):** registro ausente, duplicado ou estruturalmente inconsistente interrompe a avaliação; uma predição presente, mas inválida, permanece no denominador e conta como erro.
- **Incerteza (DEC-019 / Emenda 9):** bootstrap percentil por cluster de artigo como intervalo primário; bootstrap por caso como sensibilidade. Preservar parâmetros aprovados e regra de agrupamento multiartigo.
- **Concordância (DEC-020 / Emenda 10):** Cohen's kappa não ponderado, gate na estimativa pontual `κ ≥ 0,6`, com IC95%, concordância observada, matriz de confusão e marginais por classe; exclusões `RULE_GAP` devem ser contabilizadas separadamente segundo a regra aprovada.

### Ambiguidade editorial a acompanhar — sem alterar decisões

Em `docs/DECISIONS-PENDING.md`, os quadros iniciais registram DEC-017 a DEC-020 como aprovadas, enquanto o texto explicativo histórico de algumas opções ainda usa formulações como “pendente de aprovação” e “se aprovada”. As aprovações datadas ao final das entradas e as Emendas 7–10 do pré-registro/protocolo esclarecem o estado vigente. Isto é um risco de leitura/editorial, não evidência de que as decisões foram revogadas. Não reescrever o histórico nesta atualização; uma limpeza futura deve preservar literalmente a trilha de decisão e distinguir proposta histórica de decisão vigente.

## 5. Portões humanos ainda abertos

1. Executar o piloto 02 manualmente, sem IA e sem executar o ATTRACTOR sobre seus casos.
2. Obter uma segunda anotação de pessoa distinta, independente e sem acesso aos rótulos iniciais; documentar divergências e adjudicação.
3. Demonstrar a independência dos anotadores e verificar proveniência, vigência e retificações por caso.
4. Confirmar a separação efetiva da partição oculta antes da análise confirmatória.
5. Concluir a revisão humana independente F-01.
6. Só depois da revisão do piloto e das demais evidências, o mantenedor poderá decidir explicitamente se revisa ou congela o protocolo.

A meta de 300 casos continua condicionada à elegibilidade e qualidade; não é quota para preencher artificialmente. O protocolo permanece **[PROPOSTO]**, não congelado.

## 6. Decisão humana separada: publicação v0.6.0

A preparação da v0.6.0 está mesclada, mas isso não comprova tag, GitHub Release ou publicação. A documentação mantém uma contradição entre a data/autorização descritas em `CITATION.cff`, `CHANGELOG.md` e `docs/release/v0.6.0.md`. Não criar tag, alterar DOI ou publicar por inferência; aguardar decisão explícita do mantenedor.

## 7. Limites desta atualização

Este registro não altera código, Judge, Golden, manifests, hashes, pré-registro, decisões aprovadas, fontes capturadas, fixtures ou artefatos/casos do piloto/benchmark. Nenhum caso foi criado ou rotulado por IA, o sistema não foi executado sobre casos RGC, nenhuma métrica foi produzida e nenhuma validação externa é alegada.
