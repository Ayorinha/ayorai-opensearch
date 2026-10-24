# RGC PT-BR — continuidade e estado confirmado

**Data do snapshot:** 2026-10-23.
**Natureza:** registro documental de estado; não é aprovação, congelamento, validação científica ou revisão independente.

## 1. Referência Git

- `main` observado: `6fcdb7d5e5ad1df19aa1d531fec07805b0c5545a`, merge da PR #402.
- A PR #402 foi mesclada em 2026-10-23 às 20:53:20 UTC. A branch preparou a versão global 0.6.0 e o job de build de distribuições no CI; o merge não cria por si só tag, GitHub Release ou publicação em índice de pacotes.
- Commits recentes de merge: #399 `3f12d54f89da938deb50b6ef58396c7b29efbb86`; #400 `27cc94863f89de51ffda72223967cbcaa91f27cb`; #401 `3642e434a88c560d0950fc2c4dbdf7798f2d20ca`; #402 `6fcdb7d5e5ad1df19aa1d531fec07805b0c5545a`.

## 2. Checks: evidência e limites

### PR #402 — preparação v0.6.0

- Head auditado: `d4d8cb0a83bb855b8b07ab108e94905798bd5d85`.
- Dez workflow runs retornados, todos `completed/success`: CI, Security, CodeQL, Dependency Review, API Contract Guard, Schemathesis Full API Contract, Golden r2 Migration, Docker smoke, NLI Optional Dependency Smoke e Null body compatibility reproduction.
- Referências: [CI](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/40020388194), [Security](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/40020388149), [CodeQL](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/40020388355), [Dependency Review](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/40020388016), [API Contract Guard](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/40020388174), [Schemathesis](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/40020388359), [Golden r2 Migration](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/40020388072), [Docker smoke](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/40020388217), [NLI Optional Dependency Smoke](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/40020388326) e [Null body compatibility reproduction](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/40020388090).
- A consulta de status combinado do SHA de merge `6fcdb7d` retornou lista vazia; a consulta de workflows associada a esse SHA não forneceu runs pós-merge. Portanto, os resultados acima não são apresentados como CI pós-merge da `main`.

### PR #398 — validação estrita de rótulos-ouro

- Head: `d2cf29aa4fbb9b519955b22e3b036a9a18f3c9b6`; merge: `641591973da25ede8234958b0a36b62423476630`.
- Oito workflow runs retornados, todos concluídos com sucesso: CI, CodeQL, Security, Dependency Review, API Contract Guard, Schemathesis, Golden r2 Migration e RGC Design Simulation.
- Referências: [CI](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/39761814878), [CodeQL](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/39761814819), [Security](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/39761814840), [Dependency Review](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/39761814854), [API Contract Guard](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/39761814873), [Schemathesis](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/39761814957), [Golden r2 Migration](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/39761814783) e [RGC Design Simulation](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/39761814921).
- O diff ficou limitado a `evals/ptbr/rgc_eval.py` e `tests/test_rgc_eval_runner.py`. É endurecimento de contrato de entrada com testes sintéticos; não houve criação ou alteração de casos de benchmark.

## 3. PR #269 e sucessão documental

- [PR #269](https://github.com/Ayorinha/ayorai-opensearch/pull/269): fechada sem merge, Draft, head `f161c14b1bf196dd111e176ac04907d6eaa7f1f3`. Há três comentários de conversa; nenhuma submissão de review e nenhum thread inline. Os sete workflows retornados para o head concluíram com sucesso; status combinado não retornou registros.
- A #269 foi substituída pela [#272](https://github.com/Ayorinha/ayorai-opensearch/pull/272), também fechada sem merge. A #272 foi substituída pela [#273](https://github.com/Ayorinha/ayorai-opensearch/pull/273), mesclada em `5719db48fc82c726671af7c9c7f7ef386d161edb` em 2026-10-20.
- O diff da #273 continha apenas `docs/eval/METHODOLOGY-REVIEW-RGC-PTBR-2026-10-18.md`; os sete workflows do head `2ba363e9865b5f6ffaf6742bd202b0eea5cbbcf5` concluíram com sucesso. Essa é a revisão metodológica já incorporada à `main`; não reiniciar o trabalho original da #269 como se não tivesse sido feito.
- [PR #275](https://github.com/Ayorinha/ayorai-opensearch/pull/275) foi mesclada e alterou apenas `docs/eval/PILOT-RGC-02-WORKSHEET.md`. A existência/alteração da ficha não prova que o piloto foi executado ou que casos foram criados.

## 4. Revisão metodológica — estado a preservar

- O protocolo RGC PT-BR permanece **`[PROPOSTO]`**, não congelado.
- DEC-017–DEC-020 continuam aprovadas: integridade de registros versus predição inválida; H1 apenas na partição oculta; bootstrap por cluster de artigo como primário e bootstrap por caso como sensibilidade; critério de concordância humana conforme decisão aprovada.
- Não reabrir itens resolvidos documentalmente sem evidência nova. O achado histórico M-11 foi alinhado pela Emenda 6 à DEC-014: baseline B primária derivada apenas da partição pública; baseline A descritiva/oráculo na avaliação, excluída de H1.
- Portões humanos abertos: piloto 02 manual sem IA e sem execução do ATTRACTOR; segunda anotação humana independente e adjudicação; demonstração de independência dos anotadores; plano de cobertura/precisão sem quotas artificiais; verificação por caso de fonte, vigência e retificações; isolamento real da partição oculta; revisão humana independente F-01; decisão explícita de congelamento após revisar o piloto.
- F-01 permanece aberto. Checks de CI, análise automatizada e hashes de arquivos não demonstram revisão humana independente, validade jurídica, validação institucional ou ausência de contaminação prévia.

## 5. Discrepância documental de release — decisão humana pendente

- `CITATION.cff` declara `version: 0.6.0` e `date-released: 2026-10-23`; `CHANGELOG.md` também mostra `0.6.0` com essa data.
- `docs/release/v0.6.0.md` afirma que a publicação está autorizada mas ainda não executada, e mais abaixo lista definir a data e autorizar tag/publicação como pendências. O corpo da PR #402 diz que a data permanece pendente e que autorização de merge/tag/release exige decisões separadas.
- O DOI de conceito `10.5281/zenodo.23125082` foi preservado; não inferir que o DOI de conceito seja DOI específico de versão.
- Nenhuma tag/release foi confirmada por esta auditoria. Não modificar metadados, criar tag ou publicar como tentativa de resolver a contradição. Exigir confirmação explícita do mantenedor e depois atualizar documentação de forma consistente.

## 6. Limites e alterações desta continuidade

- Nenhum Judge, Golden, manifest, hash protegido, pré-registro, decisão aprovada, caso de piloto ou caso de benchmark foi alterado.
- Nenhum caso foi criado/rotulado com IA; o ATTRACTOR não foi executado sobre casos de piloto/benchmark; nenhuma métrica RGC foi produzida.
- Nenhuma alegação de validação externa foi feita.
- Esta nota é um registro de estado e revisão documental, não uma aprovação do protocolo nem uma autorização para executar o benchmark.