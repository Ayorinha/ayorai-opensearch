# AYORAI ATTRACTOR — Engineering Status

Updated: 2026-11-21 — `main` @ `a91da0fb6d451b20433f0952516ec6d5e733bc39` (merge PR #621), before the merge of this status update. Post-closure audit: [audit/POST-CLOSURE-AUDIT-2026-11-21.md](audit/POST-CLOSURE-AUDIT-2026-11-21.md). Next-release preparation: [engineering/RELEASE-PREP-NEXT.md](engineering/RELEASE-PREP-NEXT.md).

This file is the single source of current project status. Historical documents describe the SHA they audited and must not be treated as a live status dashboard.

Historical snapshots and the previous execution-cycle merge table are preserved in [docs/history/STATUS-SNAPSHOTS.md](history/STATUS-SNAPSHOTS.md).

## Atualização — 2026-11-28 (P2 e P3 integradas)

- **P2, trilha verificável (ADR-010):** #634 integrada em 2026-11-22 (`3932d171`). Relatório: [audit/P2-CLOSURE-REPORT.md](audit/P2-CLOSURE-REPORT.md).
- **P3/A1, isolamento dos rótulos gold no DEV da Phase 1b:** #644 integrada em 2026-11-28 (`ef5679c0`); substitui #635, #636 e #642. Retenção conforme a DEC-033 (opção A). Relatório: [audit/P3-CLOSURE-REPORT-2026-11-28.md](audit/P3-CLOSURE-REPORT-2026-11-28.md).
- **Validação:** CI verde na `main` depois de cada merge; 3.392 testes; hashes do Golden inalterados. É evidência de software, não validação científica: nenhum workflow DEV ou TEST foi executado.
- **Pendências do mantenedor antes de qualquer disparo DEV:** confirmar o Environment `international-benchmark-maintainer-approval` (só `main`, sem tags, aprovador obrigatório, dois secrets distintos) e autorizar o primeiro disparo (recomendado: minimal).

## Estado atual — 2026-11-21 (operação, homologação local e preparação de release)

- **Integradas em 2026-11-21, por autorização do mantenedor e com CI verde no HEAD final de cada PR:**
  - #598: coerência da documentação RGC;
  - #599: detector v13, escala sem moeda. Substitui a #571, fechada. Muda a referência do Golden v0.1 para `1fd6fdb7…` (11/30), aprovada pelo mantenedor; Golden v0 e smoke-v0 inalterados;
  - #600: IC de kappa por componente, DEC-022, com o runner `rgc-eval/0.13.0`;
  - #602: cadeia de sequência da trilha (`verify_chain`, `checkpoint`), parte local do P2-1;
  - #601: ADR-011, que mantém o Judge do ADR-002 por rota e resolve o P1-3;
  - #603: decisões de governança, roteiro e STATUS;
  - #604: a trilha desfaz a transação quando a gravação da cadeia falha (defeito achado na revisão pós-merge da #602);
  - #605: tratamento da revisão da #600 (definição de K, Emenda 12 completa na proposta);
  - #606: auditoria pós-encerramento, inventário das branches, índices de ADR e decisões;
  - #609: texto superado por retificação não é evidência (`rgc-eval/0.14.0`); a suíte não tem mais nenhum `xfail`;
  - #610: relatórios F1.2 sem caminhos internos (hashes recalculados e registrados); guia de anotação alinhado à Emenda 4;
  - #611: falha da retenção depois do commit não vira erro de gravação;
  - #614: reconciliação documental do ciclo;
  - #615: reconciliação documental da v0.8.0 (de outra sessão do mantenedor); #616 atualizou o site em `gh-pages`;
  - #619: integração de inferência do AYORAI-PT-NLI (EuroBERT, ADR-008), com falha fechada, sem treinamento nem ligação com a API;
  - #620: `GET /ready`, `GET /metrics`, regras de alerta, SLOs propostos e roteiro de recuperação ([observability/SLO-AND-ALERTS.md](observability/SLO-AND-ALERTS.md));
  - #621: homologação local da imagem ([audit/HOMOLOGATION-LOCAL-2026-11-21.md](audit/HOMOLOGATION-LOCAL-2026-11-21.md)), medição de capacidade ([benchmarks/CAPACITY-2026-11-21.md](benchmarks/CAPACITY-2026-11-21.md)) e Compose endurecido.
- **Distribuição:** os artefatos do CI da `main` @ `f1c7621` foram reconstruídos de forma independente com SHA-256 idênticos e têm atestação SLSA ([engineering/RELEASE-PREP-NEXT.md](engineering/RELEASE-PREP-NEXT.md), §5).
- **Verificação na `main` `3798be6` (SHA completo no cabeçalho):**
  - CI, Security e CodeQL passaram no SHA exato;
  - jobs de teste Python 3.11, 3.12 e 3.13, regressões Judge/Golden, lint e build de distribuições concluíram com sucesso;
  - a contagem `2602 passed` foi observada no HEAD da PR #614 (`5516191`), não deve ser atribuída automaticamente a qualquer SHA posterior sem consultar o respectivo log;
  - `scripts/reproduce.py`: Golden v0 7/30, v0.1 11/30, Judge 6/6;
  - `ruff`, `mypy` e `mypy --strict` do runner sem erros;
  - `bandit` 0;
  - nenhum TODO ou FIXME em `src`, `evals` e `scripts`.
- **Sem revisão registrada antes do merge:** #599, #601, #602 e #603. A #600 recebeu revisão; seus dois comentários foram tratados na #605. A revisão pós-merge por ferramenta automatizada está em [audit/POST-CLOSURE-AUDIT-2026-11-21.md](audit/POST-CLOSURE-AUDIT-2026-11-21.md) e encontrou um defeito na #602, corrigido na #604.
- **Decisões do mantenedor registradas em 2026-11-21** ([DECISIONS-APPROVED.md](DECISIONS-APPROVED.md#decisões-de-2026-11-21)):
  - DEC-001 encerrada: lock com hashes e imagem por digest;
  - DEC-003: ADR-001 aceito;
  - DEC-004: o repositório mantém o nome;
  - DEC-006: stance em português é a próxima prioridade técnica.

  Nenhuma decisão continua pendente no registro.
- **Issues:** #433, #434 e #435 foram fechadas. O que falta delas é roteiro, não defeito, e está em [ROADMAP.md](ROADMAP.md).
- **Pins históricos (P3-1):** mantidos e isolados em workflows manuais, com regra testada; ver [security/HISTORICAL-PINS.md](security/HISTORICAL-PINS.md).
- **PRs abertas em 2026-11-21, de outra sessão do mantenedor:** #617 (STATUS da v0.8.0, superada por esta atualização) e #618 (prova de conceito do escritor da ADR-010; o teste em Python 3.11 falha e ela altera a ADR-010, que é protegida). Nenhuma das duas foi mesclada por esta sessão. A #613 foi fechada. Não há issues abertas (`0`).
- **ADR-010, fases 2 e 3 (PR #623, mesclada em 2026-11-21):**
  - log Merkle com checkpoints C2SP assinados e registro do `/v1/verify` (`audit_status`, `audit_receipt`, `Idempotency-Key`; modo padrão `off`);
  - verificação cruzada com referências em Go;
  - 50 mil eventos a cerca de 1,2 ms por gravação.

  Estado: **concluída no escopo decidido**. As decisões 5 a 7 foram tomadas pelo mantenedor em 2026-11-21 (DEC-028, DEC-029 e DEC-030) e registradas na ADR-010, no ADR-009 §15.1 e no `DECISIONS-APPROVED.md`. A #618 (POC isolada) foi mesclada em 2026-11-21.

  O que fica para depois, por decisão:
  - testemunhas independentes (etapa 2 da DEC-029);
  - carimbo do tempo ICP-Brasil (adiado pela DEC-030);
  - medição no hardware de produção.

  Até haver duas testemunhas independentes, o log não resiste ao operador que detém a chave.
- **ADR-012, chaves de API (2026-11-21):** escopos, expiração e revogação sem reinício, por arquivo de chaves relido quando muda (DEC-031). O modo legado, só com a variável, não muda.
- **ADR-013, tenant (2026-11-22):** cada chave do arquivo pode ter `tenant`. Uma equipe lê a própria trilha com `audit:read`, e entre tenants a resposta é 404. O registro do log de verificação traz o tenant (`ayorai.verify-record.v2`). O esquema assinado da trilha não mudou (DEC-032).
- **Release:** v0.8.0 publicada em 2026-11-13; tag `v0.8.0` aponta para `92ea5eb86b69724b05834d98c326e8315bb6b655`, commit com assinatura verificada pelo GitHub; [GitHub Release](https://github.com/Ayorinha/ayorai-opensearch/releases/tag/v0.8.0). CI, Security e CodeQL da tag passaram. O Version DOI v0.8.0 ainda não estava registrado no Zenodo em 2026-11-21. DOI de conceito: `10.5281/zenodo.23125082`; Version DOI v0.7.0: `10.5281/zenodo.24045951`.

### Classificação do estado

| Estado | Itens |
|---|---|
| **Integrado na `main` e testado** | Judge ADR-002 em `/v1/check`, `/v1/fields`, `/v2/audit` e Judge 2.0 `r2-a` em `/v1/verify`, uma família por rota (ADR-011); detector por regras v13; independência por conteúdo normalizado e proveniência (`document-check-5`); trilha SQLite `r2-v3`/`r2-v4` com HMAC, rotação, retenção e cadeia de sequência; runner RGC `rgc-eval/0.14.0` com IC por componente para acurácia, H1 e kappa e exclusão de texto superado; imagem por digest, lock com hash, Grype, SBOM e SLSA |
| **Integrado sem revisão humana independente** | Runner e ferramenta de concordância do RGC (#576, #577, #580, #584, #600, #609); detector v13 (#599); cadeia de auditoria (#602, #604, #611). A revisão pós-merge por ferramenta automatizada não substitui a humana |
| **Texto normativo aguardando o mantenedor** | Emendas datadas da DEC-022 (pré-registro e protocolo) e Emenda 11 no protocolo: texto pronto em [eval/AMENDMENT-PROPOSAL-2026-11-21-DEC-022.md](eval/AMENDMENT-PROPOSAL-2026-11-21-DEC-022.md). Os arquivos são protegidos e não foram editados por ferramenta automatizada |
| **Configuração do repositório (só pelo mantenedor, em Settings)** | Dependabot alerts e security updates desligados; 94 branches consultadas em 2026-11-21 (`main`, `gh-pages`, 90 branches antigas do inventário e as duas heads das PRs abertas #613 e #615). O repositório apaga a branch de origem quando a PR é mesclada (`delete_branch_on_merge`); a contagem de 94 incluía branches de PRs que estavam abertas na hora. A classificação por conteúdo de cada branch está no relatório de auditoria: 22 vazias ou já incorporadas, que são as candidatas à exclusão pelo mantenedor, 12 com conteúdo não incorporado e 56 em conflito com a `main`, que pedem triagem. A exigência de aprovação no ruleset continua 0 de propósito: com um único mantenedor, o GitHub não permite aprovar a própria PR, e exigir 1 aprovação bloquearia todo merge |
| **Roteiro** | [ROADMAP.md](ROADMAP.md): persistir o veredito do `/v1/verify`, log Merkle, escopos e expiração de chaves, tenant, observabilidade, build reprodutível |
| **Não validado / limites científicos** | Implantação real; POC (proposta); Golden v0 7/30 e v0.1 11/30, abaixo do baseline majoritário (13/30); RGC sem resultado validado. PT-CP-Audit possui avaliação interna separada (test manual n=40: acurácia 65,0%→72,5%, apoio falso 25,9%→14,8%, McNemar p=0,453125; test completo n=68: acurácia 76,5%→83,8%, apoio falso 17,1%→9,8%, p=0,179688). Resultado direcional, sem significância estatística; não equivale a validação externa nem a benchmark RGC. |

- **RGC:** protocolo **[PROPOSTO]**, não congelado. Só pessoas podem fazer: piloto 02, segunda anotação independente, revisão F-01, inserção das emendas propostas, congelamento e execução única. Nenhum caso RGC foi criado, visto, rotulado ou executado.
- **Limites de alegações:** existe avaliação interna PT-CP-Audit em português, mas não há benchmark RGC PT-BR validado, validação externa independente, certificação ou demonstração de conformidade legal. **INFERÊNCIA:** a evidência registrada não basta para declarar o sistema pronto para produção.

## Snapshot — 2026-11-20 (substituído pelo estado de 2026-11-21)

- **Main:** `3342b5ee129c79b1724ae36f1cbee4e9f03a2d54` (merge da #539), antes do merge desta atualização (#595). CI, Security e CodeQL pós-merge verdes em cada merge anterior desta data; o detalhe por SHA está em [audit/PR-INVENTORY-2026-11-20.md](audit/PR-INVENTORY-2026-11-20.md), §8.
- **Integradas em 2026-11-20, por autorização individual do mantenedor:** #589 (todo documento relacionado chega à adjudicação), #590 (rastro `r2-v4` vincula a adjudicação do `/v2/audit`), #591 (uma fonte por resultado de busca), #592 (detector v12), #593 (erros de provider sem URL interna), #594 (rotação de chave HMAC), #596 (cópias e quase-duplicatas não são fontes independentes), #597 (texto do cliente não chega a `verified`), #580, #584, #576 e #577 (runner RGC: snapshots E5, interpretador isolado, concordância por snapshot, gate H1), #583 (STATISTICS.md × DEC-027), #581 e #539 (registros metodológicos datados).
- **Fechadas sem merge, com branches preservadas e destino registrado no inventário:** #553 e #554 (substituídas por #583 e #580), #579 (superada por esta atualização), #531 (superada pela #583), #504, #505, #507, #509 e #527 (benchmarks exploratórios não executados), #535 (ambiente histórico Phase 1b; hashes registrados no inventário).
- **Aberta:** #571 (detector v11; muda a referência do Golden v0.1), adiada por decisão do mantenedor.
- **Release:** a versão de código continua `0.8.0`. Nenhuma tag, release ou DOI nova; o `[Unreleased]` do CHANGELOG reúne as mudanças.

### Classificação do estado

| Estado | Itens |
|---|---|
| **Integrado na `main` e testado** | Judge determinístico ADR-002 (`/v1/check`, `/v1/fields`, `/v2/audit`) e Judge 2.0 `r2-a` (`/v1/verify`); seleção de trechos por documento; independência das fontes por conteúdo normalizado (`document-check-4`); proveniência `client_supplied`/`server_retrieved` (`document-check-5`; `/v1/check` limitado a `supported`); detector por regras v12; fontes de busca separadas; trilha SQLite `r2-v3`/`r2-v4` com HMAC, backup, `seal_unsealed`, `reseal_with_active_key` e retenção opcional; erros de provider sem dados internos; runner RGC `rgc-eval/0.12.0` com snapshots E5 e interpretador isolado; imagem fixada por digest e lock com hash; Grype, SBOM e SLSA |
| **Integrado sem revisão humana independente** | Runner RGC (#576, #577, #580, #584): revisão técnica feita por ferramenta automatizada, sem defeito bloqueante; a revisão humana independente prevista no `CONTRIBUTING.md` continua pendente |
| **Dependente de decisão do mantenedor** | #571 (Golden v0.1); contrato do Judge no `/v1/check` e `/v2/audit` (Judge 1.x × `r2-a` do ADR-009); detecção de exclusão e rollback na trilha (issue #433, exige ADR); escopos, expiração e revogação de chaves (issue #434); IC do kappa por componente (DEC-022, exige emenda datada da Emenda 10); registro das decisões aprovadas DEC-017..020, 023 e 027 em `DECISIONS-APPROVED.md`; pins históricos com avisos de segurança; Dependabot security updates e aprovação obrigatória no ruleset; branches sem PR (entre elas `eval/rgc-pilot`) |
| **Experimental** | Provider de LLM compatível com OpenAI; NLI opcional; recuperação híbrida OpenSearch; módulos `council` e `arena` (não ligados à API) |
| **Testado só localmente** | Gateway nginx com duas réplicas (limite agregado e `X-Forwarded-For`); Compose com volume e HMAC exigido |
| **Não validado** | Implantação em produção ou homologação; POC (proposta, não executada); acurácia científica: Golden v0 7/30 e v0.1 10/30, abaixo do baseline de classe majoritária (13/30); RGC sem resultado |

- **RGC e português:** o protocolo RGC continua **[PROPOSTO]**, não congelado. Nenhum caso RGC foi criado, visto, rotulado ou executado. Faltam, e só pessoas podem fazer: piloto 02, segunda anotação independente, revisão independente F-01, verificação de proveniência, vigência e retificações, isolamento da partição oculta e decisão de congelamento. O congelamento vincula `verification/stance.py`: a #571 deve ser decidida antes dele.
- **Limites de alegações:** não há benchmark em português publicado, validação externa independente, certificação regulatória nem conformidade legal. **INFERÊNCIA:** a evidência registrada não basta para declarar o sistema pronto para produção.

## Snapshot — 2026-11-17 (substituído pelo estado de 2026-11-20)

- **Main:** `345e94f180427245a62f0a5d79ff49cefbd6a975`, integração da PR [#574](https://github.com/Ayorinha/ayorai-opensearch/pull/574), atualização documental dos controles de integridade de auditoria e admissão. A atualização anterior de status (#572) registrava `267a29e`; foi superada pelas integrações posteriores.
- **CI pós-merge da main:** não confirmado. A consulta de workflows e a consulta de status combinado para `345e94f180427245a62f0a5d79ff49cefbd6a975` não retornaram execuções/status. Checks de PR não devem ser apresentados como CI pós-merge.
- **Release v0.8.0:** publicada em 2026-11-13; a tag `v0.8.0` aponta para `92ea5eb86b69724b05834d98c326e8315bb6b655`, cuja assinatura GitHub foi verificada como válida. O DOI específico da versão v0.8.0 ainda não está registrado; o DOI de conceito permanece `10.5281/zenodo.23125082`.
- **Integrações recentes na main:** #564 introduziu a trilha de auditoria com dono, r2-v3, metadados, backup e HMAC; #565 integrou o detector por regras v8 e fixou erros conhecidos; #566 alinhou documentação de API, proprietário dos rastros, backup e variáveis; #567 restringiu atualizações automáticas para preservar pins históricos do benchmark e a linha Python suportada pela imagem; #568 adicionou varredura Grype da imagem, artefato CycloneDX e proveniência SLSA assinada para sdist/wheel; #569 atualizou Ruff para 0.17.5; #570 corrigiu escopo de negação sentencial e negação relatada; #574 documentou integridade de auditoria e controles de admissão.
- **Detector de postura v9 (#570):** a negação é considerada somente nas frases que cobrem a afirmação; negações relatadas, como “X negou que P”, são neutras. O commit registra que os digests semânticos Golden v0 e v0.1 permaneceram iguais nessa alteração. A PR #571, ainda aberta, propõe uma mudança distinta que altera a referência Golden v0.1 e requer aprovação específica.
- **Segurança da cadeia de suprimentos:** a #568 adicionou Grype com binário verificado por SHA-256, falha para achados altos/críticos com correção disponível, artefato CycloneDX e atestação SLSA verificada no job. A #567 mantém fora das atualizações automáticas o ambiente histórico do benchmark e não amplia a linha Python da imagem além da suportada.
- **Auditoria HMAC:** a #575 propõe exigir MAC em todas as versões de replay suportadas e a configuração externa `ATTRACTOR_AUDIT_HMAC_REQUIRED`. No HEAD `da16071713e8e7a8963f0128cb832ccd613847b3`, os sete workflow runs retornados pela consulta terminaram com sucesso. A PR permanece aberta; falta revisão humana independente para a mudança de segurança e validação operacional de configuração/rotação/backup de chaves. Na proposta #575, HMAC obrigatório continua opt-in; não inferir que ambientes estejam protegidos sem configurar a opção e as chaves.
- **PRs abertas observadas em 2026-11-17, antes da abertura desta atualização (#578):** 14 no total — 11 Draft e 3 abertas fora de Draft. A #578 é esta PR de status e não integra aquela contagem; após sua integração, a lista deve ser reconsultada. Lista e heads são dinâmicos; consultar GitHub antes de agir:
  - **#575 — aberta, não Draft:** HMAC em todas as versões de replay; aguarda revisão humana independente e decisão de integração.
  - **#577 — Draft:** gate H1 para resolução informativa do sign-flip por componente; 8 workflow runs retornados com sucesso no HEAD `11dd79cc0eda157dcb355d36ddd9138092008022`. Teste sintético; sem execução em dados RGC.
  - **#576 — Draft:** vincula métricas de concordância aos mesmos snapshots de bytes usados no parsing; 8 workflow runs retornados com sucesso no HEAD `5853066ee7d9a6d5d1bb5767d8f6ecb22fd20561`. Revisão automatizada COMMENTED sem bloqueador identificado; não houve leitura de anotações reais.
  - **#554 — Draft:** manifesto por execução e dependências do runner (E5); GitHub reportou `mergeable=false` no head consultado. A questão de publicação concorrente/TOCTOU precisa ser resolvida antes da integração.
  - **#553 — Draft:** reconciliação documental de STATISTICS.md com DEC-027 e o runner.
  - **#571 — aberta, não Draft:** detector v10; altera a referência Golden v0.1 e depende de aprovação metodológica explícita. Não integrar por inferência de autorização.
  - **#539 — Draft:** continuidade metodológica RGC.
  - **#535 — Draft:** ambiente histórico Phase 1b DEV; GitHub reportou `mergeable=false`; não contornar Dependency Review nem modificar pins históricos sem decisão e prova de equivalência.
  - **#531 — aberta, não Draft:** identidade de componente e auditoria metodológica; permanece sujeita à reconciliação com DEC-023/decisão do mantenedor.
  - **#527 — Draft:** governança do fluxo P1 e lock one-shot; base é `feat/e3-confirm-dev-b`, não `main`.
  - **#505 — Draft:** confirmação P1 em DEV-B; GitHub reportou `mergeable=false`. Não executar DEV-B sem autorização específica.
  - **#504 — Draft:** DEC-025, pré-registro E3 proposto e helper de planejamento LTT; não autoriza execução.
  - **#509 — Draft:** proposta DEC-026 e reconciliação de elegibilidade de 55 células.
  - **#507 — Draft:** proposta de protocolo MiniCheck-Flan-T5-Large; sem download de pesos ou inferência.
- **Outras observações de CI:** #575 teve sete workflow runs retornados com sucesso no HEAD citado; #576 e #577 tiveram oito cada. Esses resultados são específicos dos respectivos heads, não da main.
- **RGC e português:** o protocolo RGC permanece **[PROPOSTO]**, não congelado. #576 e #577 usam apenas regressões sintéticas; nenhuma anotação humana real foi lida, nenhum caso do Piloto 02 ou benchmark definitivo foi criado/rotulado nesta execução, o ATTRACTOR não foi executado sobre casos RGC e nenhuma métrica científica foi produzida.
- **Pendências humanas/científicas:** piloto 02 manual sem IA e sem execução do sistema; segunda anotação independente por outra pessoa; revisão humana independente F-01; verificação de proveniência/vigência/retificações e isolamento da partição oculta; decisão separada do mantenedor sobre congelamento. CI sintético não substitui esses gates.
- **Versão de código:** `0.8.0` em `pyproject.toml`, `src/ayorai_attractor/__init__.py` e `CITATION.cff`.
- **API documental:** `POST /v1/check` verifica afirmações/respostas contra texto ou PDF com camada de texto; `UNVERIFIED` é exposto como abstenção (`status: "abstain/no_answer"`, `verdict: null`). `POST /v1/fields` compara campos documentais e retorna `conforme`, `divergente`, `ambiguo`, `ausente` ou `invalido`.
- **Limites de alegações:** não há benchmark RGC em português publicado, validação externa independente, certificação regulatória ou conformidade legal automática. **INFERÊNCIA:** a evidência atualmente registrada não é suficiente para declarar o sistema pronto para produção. O estado de engenharia deve ser descrito separadamente da validação científica e operacional.

> As seções seguintes preservam snapshots históricos. Datas, SHAs e estados registrados nelas descrevem exclusivamente o momento da respectiva captura e não substituem o estado atual acima.

## Snapshot — 2026-10-25

- **`main` de referência para este snapshot:** `4f3c0cea4e40df5141521c4a12010bc3da5ac365` (merge da PR #410, testes de cobertura). No SHA exato, os runs pós-merge [CI 40213557463](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/40213557463), [Security 40213557486](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/40213557486) e [CodeQL 40213557412](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/40213557412) concluíram com sucesso. O CI executou a matriz Python 3.11–3.13: `1201 passed, 1 skipped in 39.65s`; cobertura global 95%. O merge desta atualização documental produzirá outro SHA de `main`.
- **v0.7.0 publicada:** data oficial da versão 2026-11-07; tag `v0.7.0` em `43bbe8e562375d3160851610f3e7b0bc05437900` (merge da PR #484); GitHub Release publicada em 2026-11-08T00:07Z; Version DOI [`10.5281/zenodo.24045951`](https://doi.org/10.5281/zenodo.24045951); Concept DOI `10.5281/zenodo.23125082`. Registra o primeiro resultado DEV da Calibration V2, antes da emenda sobre limiares inelegíveis.
- **v0.6.0 publicada:** data oficial da versão 2026-10-23; tag `v0.6.0` em `6fcdb7d5e5ad1df19aa1d531fec07805b0c5545a`; GitHub Release publicada em 2026-10-24T00:41Z; Version DOI `10.5281/zenodo.23607357`; Concept DOI `10.5281/zenodo.23125082`.
- **Comandos e jobs observados no CI do SHA `4755f94`:** testes Python 3.11, 3.12 e 3.13 passaram; `pytest -q` no job `namespace-compatibility` passou; `ruff check .` e `ruff format --check .` passaram nos jobs de teste; `mypy --strict` e os gates de regressão Judge/Golden passaram; o build de sdist/wheel e a verificação SHA-256 passaram. Estes são resultados do CI, não execução local.
- **CI da release:** os 10 workflows da PR #402 passaram no head `d4d8cb0a83bb855b8b07ab108e94905798bd5d85`. Os 8 workflows da PR #405 e os 7 workflows da PR #406 também passaram nos respectivos heads antes dos merges. Esses resultados são específicos dos heads citados e não devem ser descritos como execução local nem como CI pós-merge do SHA atual de `main`.
- **Proveniência de distribuição:** o artefato do run [40022675628](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/40022675628) foi baixado; `sha256sum -c SHA256SUMS.txt` retornou `OK` para sdist e wheel. A comparação do MD5 do ZIP Zenodo com o zipball da tag é registrada como conferência automatizada, não independente; consulte [RELEASE-PROVENANCE.md](release/RELEASE-PROVENANCE.md).
- **RGC:** o protocolo permanece **[PROPOSTO]**, não congelado; `docs/eval/PROTOCOL-FREEZE.json` não existe; o executor bloqueia a execução sem `PROTOCOL-FREEZE.json` e sem aprovação humana da anotação. Nenhum caso RGC foi criado/completado/rotulado e o ATTRACTOR não foi executado em casos RGC.
- **Pendências humanas:** piloto 02 manual sem IA e sem execução do sistema, segunda anotação por outra pessoa, revisão humana independente F-01 e decisão separada do mantenedor sobre congelamento. A revisão automatizada não é independente.

> As seções seguintes preservam snapshots e referências históricas; statements sobre a publicação ainda pendente refletem o estado registrado na data original e foram superados pela publicação de 2026-10-23.

## Snapshot confirmado — 2026-10-24 (rechecagem)

- **`main` observado:** `6fcdb7d5e5ad1df19aa1d531fec07805b0c5545a`; não houve commit mais novo desde a verificação anterior.
- **Checks pós-merge da `main`:** status combinado sem registros e consulta de workflows sem runs para esse SHA. O CI pós-merge permanece não confirmado.
- **PR #269:** fechada sem merge; head `f161c14b1bf196dd111e176ac04907d6eaa7f1f3`; 3 comentários de conversa, 0 submissões de revisão e 0 threads inline. Os 7 workflows consultados no head terminaram com sucesso. A revisão foi sucedida por PRs documentais posteriores, incluindo a #273 mesclada.
- **PR #403 antes desta atualização:** aberta em Draft, head `e03df9f2c293d62fcdea1b1afe3ac4e273ad8ca1`; o diff tinha 2 arquivos e não havia comentários, submissões de revisão ou threads inline. Os 7 workflows consultados para esse head terminaram com sucesso: [CI](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/40051166732), [Security](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/40051166743), [CodeQL](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/40051166738), [Dependency Review](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/40051166791), [API Contract Guard](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/40051166773), [Schemathesis](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/40051166745) e [Golden r2 Migration](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/40051166742). **Esses checks pertencem somente ao head anterior**; o novo registro documental exige checks no novo head.
- **Atualização documental:** `docs/audit/RGC-METHODOLOGY-CONTINUITY-2026-10-24.md` consolida a rechecagem e os portões metodológicos; esta atualização está sendo rebaseada na `main` atual e precisa de checks no novo head.
- **Revisão RGC:** DEC-014 e DEC-017–DEC-020 permanecem preservadas. B é a baseline primária de desenvolvimento; A é descritiva; H1 usa apenas a partição oculta; bootstrap por cluster de artigo é primário; concordância humana continua exigida. A rechecagem identificou linguagem histórica contraditória sobre DEC-018 em `PREREGISTRATION-RGC-v1.md`, `STATISTICS.md`, `PROTOCOL-GOLDEN-V1.md` e `DECISIONS-PENDING.md`; o estado aprovado está registrado nas emendas posteriores. Os arquivos normativos não foram alterados; recomenda-se apenas rotular melhor os trechos históricos numa PR documental separada. O protocolo segue **[PROPOSTO]**, não congelado.
- **Pendências humanas:** piloto 02 manual sem IA/sem execução do sistema, segunda anotação independente e adjudicação, comprovação da independência, proveniência/vigência/retificações por caso, isolamento da partição oculta e revisão independente F-01.
- **Release v0.6.0:** publicada em 2026-10-23; a inconsistência documental foi resolvida nas PRs #405 e #406, sem alterar a tag, a release ou os DOIs.
- **Limites:** nenhum caso foi criado/rotulado por IA; nenhuma execução RGC ou métrica foi produzida; não há alegação de validação externa.

## Snapshot confirmado — 2026-10-23 (após PR #402)

- **Registro histórico de `main` em 2026-10-23:** `6fcdb7d5e5ad1df19aa1d531fec07805b0c5545a`, merge da PR [#402](https://github.com/Ayorinha/ayorai-opensearch/pull/402), que preparou a v0.6.0. A publicação foi confirmada posteriormente e está registrada no estado atual acima.
- **Checks da PR #402:** 10/10 workflow runs concluídos com sucesso no head `d4d8cb0a83bb855b8b07ab108e94905798bd5d85`: [CI](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/40020388194), [Security](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/40020388149), [CodeQL](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/40020388355), [Dependency Review](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/40020388016), [API Contract Guard](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/40020388174), [Schemathesis](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/40020388359), [Golden r2 Migration](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/40020388072), [Docker smoke](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/40020388217), [NLI Optional Dependency Smoke](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/40020388326) e [Null body compatibility reproduction](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/40020388090). Estes resultados pertencem ao head da PR, não ao SHA de merge.
- **Checks pós-merge da `main`:** a consulta de status combinado para `6fcdb7d` não retornou registros, e a consulta de workflows associada ao SHA não forneceu runs pós-merge. Portanto, o CI pós-merge da `main` não está confirmado neste snapshot.
- **PR #398:** mesclada em `641591973da25ede8234958b0a36b62423476630`; o head `d2cf29aa4fbb9b519955b22e3b036a9a18f3c9b6` teve oito workflows retornados, todos com sucesso: [CI](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/39761814878), [CodeQL](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/39761814819), [Security](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/39761814840), [Dependency Review](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/39761814854), [API Contract Guard](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/39761814873), [Schemathesis](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/39761814957), [Golden r2 Migration](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/39761814783) e [RGC Design Simulation](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/39761814921). A mudança é validação estrita do JSONL de rótulos e testes sintéticos; não criou nem alterou casos.
- **PR #269 e linhagem documental:** #269 está fechada sem merge, em Draft, head `f161c14b1bf196dd111e176ac04907d6eaa7f1f3`; há três comentários de conversa, nenhuma submissão de review e nenhum thread inline. Os sete workflows do head terminaram com sucesso ([CI](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/39241516692), [CodeQL](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/39241516946), [Security](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/39241516787), [Dependency Review](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/39241516590), [API Contract Guard](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/39241516739), [Schemathesis](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/39241517114) e [Golden r2 Migration](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/39241516646)). A #269 foi substituída pela #272; a #272 foi substituída pela [#273](https://github.com/Ayorinha/ayorai-opensearch/pull/273), que foi mesclada em `5719db48fc82c726671af7c9c7f7ef386d161edb` e alterou apenas `docs/eval/METHODOLOGY-REVIEW-RGC-PTBR-2026-10-18.md`. Os sete workflows da #273 também passaram. A [PR #275](https://github.com/Ayorinha/ayorai-opensearch/pull/275) foi mesclada alterando apenas a ficha do piloto 02; isso não representa criação ou execução de casos.
- **Mudanças recentes:** [#399](https://github.com/Ayorinha/ayorai-opensearch/pull/399) alinhou a validação de documentos-fonte e o executor `rgc-eval/0.7.0`; [#400](https://github.com/Ayorinha/ayorai-opensearch/pull/400) e [#401](https://github.com/Ayorinha/ayorai-opensearch/pull/401) consolidaram documentação; [#402](https://github.com/Ayorinha/ayorai-opensearch/pull/402) preparou a v0.6.0. A publicação foi confirmada em 2026-10-25 e registrada nas PRs #405 e #406.
- **Histórico — inconsistência de release identificada em 2026-10-24, resolvida em 2026-10-25:** `CITATION.cff`, `CHANGELOG.md` e `docs/release/v0.6.0.md` foram alinhados com a publicação já existente; veja as PRs #405 e #406. Nenhuma tag, release ou DOI foi criada ou alterada para resolver a inconsistência.
- **Limite científico:** RGC permanece `[PROPOSTO]`, não congelado. Piloto 02 manual, segunda anotação humana independente, revisão independente F-01, verificação do isolamento oculto e decisão formal de congelamento continuam pendentes. Não há métricas RGC nem validação externa declarada.

Registros detalhados: [verificação de continuidade de 2026-10-24](audit/RGC-METHODOLOGY-CONTINUITY-2026-10-24.md), que consolida a minuta de 2026-10-23.

## Documentação e referências — classificação de estado

| Estado | Item | Interpretação atual |
|---|---|---|
| **HISTÓRICO** | `main` após a PR #402 — `6fcdb7d5e5ad1df19aa1d531fec07805b0c5545a` | A preparação global v0.6.0 foi mesclada em 2026-10-23. Naquele registro, a tag/release ainda não havia sido confirmada; a publicação posterior está registrada no estado atual acima. |
| **VIGENTE** | Autenticação da API | `api_key` é o modo padrão; a aplicação falha fechada quando falta material obrigatório. Consulte `docs/api/CHANGELOG-API.md` para migração. |
| **HISTÓRICO** | Release global `0.5.0` | Versão publicada anterior. DOI específico da versão: [`10.5281/zenodo.23344005`](https://doi.org/10.5281/zenodo.23344005). |
| **VIGENTE** | DOI no `CITATION.cff` | O campo `doi` mantém o DOI de conceito `10.5281/zenodo.23125082`; `identifiers` ainda registra o DOI específico da v0.7.0 `10.5281/zenodo.24045951` até o DOI da v0.8.0 ser emitido. A versão é `0.8.0` e a data oficial é `2026-11-13`. |
| **HISTÓRICO** | Release global `0.6.0` | Versão publicada anterior. DOI específico da versão: [`10.5281/zenodo.23607357`](https://doi.org/10.5281/zenodo.23607357). |

**Registro de decisão de DOI — resolvido em 2026-10-25:** o campo `doi` permanece no DOI de conceito e `identifiers` contém o DOI específico da versão v0.6.0. Os dois identificadores têm funções distintas.

> **Aviso histórico — 2026-10-23:** a seção abaixo descreve a referência `641591973da25ede8234958b0a36b62423476630` e o estado anterior às PRs #399–#402. Para o estado atual, use o snapshot confirmado acima; não trate as referências antigas como estado corrente.

## Consolidated process and RGC runner update — 2026-10-23

- **Reference `main` SHA for this batch:** `641591973da25ede8234958b0a36b62423476630`.
- **Origin of commit `6415919`: merged via PR #398, not a direct push.** PR: [#398 — strict validation of gold-label JSONL](https://github.com/Ayorinha/ayorai-opensearch/pull/398). Reviewed head SHA: `d2cf29aa4fbb9b519955b22e3b036a9a18f3c9b6`; merge commit: `641591973da25ede8234958b0a36b62423476630`. This was not a process deviation.
- **PR #398 head checks (all completed successfully on that exact head SHA):** [CI](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/39761814878), [CodeQL](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/39761814819), [Security](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/39761814840), [Dependency Review](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/39761814854), [API Contract Guard](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/39761814873), [Schemathesis Full API Contract](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/39761814957), [Golden r2 Migration](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/39761814783), and [RGC Design Simulation](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/39761814921). These results apply to the PR #398 head SHA, not to a different commit.
- **Runner version:** the strict gold-label JSONL contract is a material input-contract change; `RUNNER_VERSION` and the synthetic report assertion are advanced to `rgc-eval/0.7.0`. Labels that relied on type coercion or blank-line tolerance may now be rejected.
- **Extraction history (2026-10-22):** evidence end offset uses `start_offset + len(content)` when absent; NLI payloads are validated strictly; missing confidence defaults to `0.0` (“sem nota”), not a verdict. See [PR #391](https://github.com/Ayorinha/ayorai-opensearch/pull/391) and [PR #393](https://github.com/Ayorinha/ayorai-opensearch/pull/393).
- **Current batch:** [PR #399](https://github.com/Ayorinha/ayorai-opensearch/pull/399) consolidates strict source-document validation, runner-version alignment, the runner specification, changelog, and this single STATUS update. Its head checks must be evaluated separately; PR #398 checks do not validate PR #399.
- **Historical scientific boundary at the 2026-10-23 snapshot:** no real RGC case had been evaluated and no benchmark metric had been produced. The protocol remains `[PROPOSTO]`, not frozen. Pilot 02, a second independent human annotation and independent human review F-01 remain pending. No Judge, Golden v0/v0.1, frozen thresholds, preregistration or benchmark cases were changed by that batch. The statement that no tag or release was authorized is historical and was superseded by the software publication; publication does not authorize RGC execution or protocol freeze.


## Execution snapshot recorded on 2026-10-22

- **Main reference SHA when this snapshot was prepared:** `a44d0564d429d956898e819721299f715b46bda2` — [PR #393 merge commit](https://github.com/Ayorinha/ayorai-opensearch/commit/a44d0564d429d956898e819721299f715b46bda2).
- **PR #391 merged:** [test(extraction): cover provenance and adapter contracts](https://github.com/Ayorinha/ayorai-opensearch/pull/391), squash SHA `bf49dba9e7e66bdc0af0203845547b8541e81cca`. The seven PR workflows passed for its reviewed head SHA.
- **PR #393 merged:** [fix(extraction): validate NLI payloads and source offsets](https://github.com/Ayorinha/ayorai-opensearch/pull/393), squash SHA `a44d0564d429d956898e819721299f715b46bda2`. The seven PR workflows passed for reviewed head `e5b0be75295ff32fc5635e2ae8ccde4521980b9f`; these are PR-head results, not a claim that post-merge checks for the resulting main SHA were independently queried.
- **Extraction hardening:** missing evidence end offsets now use `start_offset + len(content)`; NLI adapter payloads are validated strictly and malformed payloads are covered by regression tests. An omitted NLI confidence remains `0.0` as an unscored default, not as a Judge verdict.
- **PR #394 merged:** [docs(status): record extraction fixes and current PR state](https://github.com/Ayorinha/ayorai-opensearch/pull/394), squash SHA `f94e86db89eb000c4764c49b949a30d65e63e421`. This documentation follow-up clarifies that the snapshot above records the state at preparation time, not the current HEAD after this follow-up merge.
- **PR #395 merged:** [docs(status): clarify snapshot timestamp and follow-up merge](https://github.com/Ayorinha/ayorai-opensearch/pull/395), squash SHA `bd99f4b3e25a785cdcc08172d860a317532e6d90`. The current `main` reference after this documentation-only merge is `bd99f4b3e25a785cdcc08172d860a317532e6d90`; the historical CI statements above refer to their explicitly named commit/PR heads, not to post-merge checks for this SHA. The combined-status query returned no status records, so main CI is not confirmed by that query.
- **PR #396 merged:** [docs(status): record PR #395 merge and main reference](https://github.com/Ayorinha/ayorai-opensearch/pull/396), squash SHA `f7277d3e00a0efb8c47d8a5366bc9eba0db38778`. All seven PR workflows passed for reviewed head `da3ad5f9cc0145154e38cb1f62fbee137cd8fdfd`, including CI on Python 3.11, 3.12 and 3.13, Security, CodeQL, Dependency Review, API Contract Guard, Schemathesis and Golden r2 Migration. These are PR-head results; they are not a claim that post-merge main checks were separately queried.
- **Historical release state at the 2026-10-23 snapshot:** v0.5.0 was the latest published release at that time. The later v0.6.0 publication is documented in the current-status section above.
- **Scientific boundary unchanged:** RGC PT-BR remains `[PROPOSTO]`, not frozen. Pilot 02, a second independent human annotation and independent human review F-01 remain pending. No RGC cases were created/labeled by AI, no ATTRACTOR execution over pilot/benchmark cases occurred, and no RGC metrics or external-validation claims were produced.
- **Scope boundary:** Judge, Golden manifests/hashes, preregistration, benchmark cases and release metadata were not changed by PRs #391 or #393.

The execution snapshot above is historical as of its preparation time. Historical snapshots below remain historical and are not retroactively rewritten.

## API contract note (2026-10-21) — r1-a JSON null

The frozen contract remains HTTP 422 with error type `missing` and location `["body"]`; the fixture `tests/fixtures/r1-a-error-baseline.json` was not modified. The controlled isolated reproduction in [`scripts/repro_null_body_contract.py`](../scripts/repro_null_body_contract.py) tested 16 FastAPI/Pydantic combinations: FastAPI `0.115.0, 0.117.0, 0.119.0, 0.121.0, 0.123.0, 0.125.0, 0.127.0, 0.128.2`, each paired with Pydantic `2.10.0` and `2.13.5`, plus `httpx==0.27.2`. Both synthetic route styles reflecting the v0.4.0 typed-body route and v0.5.0 Any/Body + manual validation route returned 422 `missing`; direct `model_validate(None, from_attributes=True)` returned `model_attributes_type` in both tested Pydantic versions. No version threshold was identified; no dependency bound was added. Exact commands are recorded in CHANGELOG.md and the workflow from PR #339. This reproduces the relevant route styles in isolation rather than importing the tagged application, and does not establish behavior outside the tested matrix.

**Correction dated 2026-10-21:** the paragraph above describes only the initial 16-combination matrix and is historical. The expanded controlled bisection found the first change in the typed-route style between FastAPI `0.150.0` (`missing`) and `0.151.0` (`model_attributes_type`); the v0.5.0 explicit `payload is None` guard preserves HTTP 422 `missing` through FastAPI `0.157.0` with Pydantic tested through `2.14.1`. No API, fixture or dependency bound changed; see the final bisection result in `CHANGELOG.md`.

## Current execution snapshot (2026-10-21)

- **SHA de referência validado antes desta atualização documental:** `c9994dd2ef907f05b603626f4845b44739c285ca`. Esta é a revisão da `main` que incorpora o fechamento das etapas 1–3; esta PR atualiza somente status e rascunho de release, portanto seu próprio merge terá outro SHA.
- **CI da referência:** [run 39638074704](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/39638074704) concluído: **12 checks com sucesso, 1 ignorado** por condição de workflow (`rgc-design-simulation`), zero falhas. Testes Python 3.11, 3.12 e 3.13 passaram.
- **Segurança e análise estática:** [security run 39638075257](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/39638075257) e [CodeQL/analyze run 39638074782](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/39638074782) concluídos com sucesso.
- **Saída de testes (Python 3.12):** `1126 passed, 1 skipped in 47.79s`; cobertura geral 94% (4.214 statements, 251 missed). O job `namespace-compatibility` também executou `pytest -q` e passou.
- **Qualidade no CI:** `ruff check .` — `All checks passed!`; `ruff format --check .` — `360 files already formatted`; `mypy --strict evals/ptbr/rgc_eval.py evals/ptbr/rgc_agreement.py` — `Success: no issues found in 3 source files`. O mypy estrito geral também passou: 91 source files sem erros.
- **PRs mescladas neste fechamento:** #362 (guarda inicial de consistência; SHA `0f06995f51d3d2cfded56b849c7300ac7c3b3300`); #369 (guarda de emendas; SHA `1e77df724d432b05d230b112afd3ca6ff83eb3b0`); #370 (consistência documental; SHA `7fc9ae9708ff8ee46ffe2398efa4d6024d36ce90`); #373 (justificativas `# nosec`; SHA `fc12c38e5bc2967642d2bd941d01fc52b4f206fb`); #374 (status/rascunho anterior; SHA `a269d5f5371f3b2545635515d6b98d8cfe679ba6`); #375 (consolidação da guarda, removeu o teste duplicado; SHA `daf9ce3771712f60ddce2ff76e7118d25fafb656`); #376 (auditoria de desvios de processo; SHA `c9994dd2ef907f05b603626f4845b44739c285ca`).
- **PRs fechadas sem merge:** #371 foi substituída por esta atualização final; #372 foi substituída pela #373; #367 foi substituída pela #373; #368 foi substituída pela #370. A #373, não a #372, é o merge efetivo das justificativas `# nosec`.
- **Fechamentos anteriores do mesmo ciclo:** #307, #328, #330, #334, #336, #338, #340, #343, #344, #346, #348 e #350 permanecem registrados no snapshot histórico e no relatório de limpeza de branches.
- **PRs abertas no snapshot de referência:** nenhuma. A PR atual de status/release é criada depois desse snapshot; após seu merge, a API será consultada novamente para confirmar zero PRs abertas.
- **Branches remotas:** nenhuma branch foi apagada. A auditoria de candidatas permanece em [BRANCH-CLEANUP-2026-10-21.md](audit/BRANCH-CLEANUP-2026-10-21.md); a limpeza das aproximadamente 205 branches requer ação manual autorizada.
- **Limites científicos:** DEC-017–DEC-020 continuam aprovadas. O protocolo RGC permanece `[PROPOSTO]`, não congelado. Nenhum caso de piloto/benchmark foi criado, completado ou rotulado; o ATTRACTOR não foi executado em casos RGC e nenhuma métrica RGC foi produzida. A revisão automatizada não é independente; F-01 continua aberto.

## Release and system boundaries

- A release publicada mais recente é **v0.8.0** ([GitHub Release](https://github.com/Ayorinha/ayorai-opensearch/releases/tag/v0.8.0)); o DOI de versão da v0.8.0 ainda não foi registrado. A versão anterior, v0.7.0, tem o DOI [10.5281/zenodo.24045951](https://doi.org/10.5281/zenodo.24045951); o DOI de todas as versões é [10.5281/zenodo.23125082](https://doi.org/10.5281/zenodo.23125082).
- As notas da v0.6.0 estão em `docs/release/v0.6.0.md`; publicação confirmada. Nenhuma tag ou release foi criada ou alterada por esta atualização documental.
- The RGC protocol remains `[PROPOSTO]`; approved decision options define rules but do not freeze the protocol or authorize a benchmark run.
- No claims of certification, institutional validation, independent review or production readiness are supported by the current evidence.

## Maintainer decisions and governance

- **DEC-017 — approved by the maintainer (2026-10-21), Option A:** a missing/integrity-invalid record interrupts; a present but invalid prediction counts as an error in the denominator. Implementation/doc alignment: PRs #335 and #337.
- **DEC-018 — approved by the maintainer (2026-10-21), Option A:** H1 is confirmatory only on the hidden partition (~90 cases); the ~210 public cases are descriptive/exploratory. Executor requires an explicit partition. PR #342.
- **DEC-019 — approved by the maintainer (2026-10-21), Option A:** article-cluster bootstrap is the primary 95% CI; case bootstrap is sensitivity. `bootstrap_cluster_id` is required for hidden cases, with canonical multi-article bundle rules. PR #349.
- **DEC-020 — approved by the maintainer (2026-10-21), Option A:** unweighted Cohen's kappa, point-estimate gate `κ ≥ 0.6`, case-bootstrap 95% CI, confusion matrix/class marginals, and auditable `RULE_GAP` exclusions. Calculator and guide are in PR #351.
- Other decisions remain as recorded in [DECISIONS-PENDING.md](DECISIONS-PENDING.md); do not infer approval from an implementation or CI result.
- **Protocol freeze:** not approved by these decisions. The protocol remains proposed; no definitive case set has been created.

## Schemathesis issue #250

Issue [#250](https://github.com/Ayorinha/ayorai-opensearch/issues/250) was closed after #259 corrected the asymmetric `negative_data_rejection` exclusion between `/v1/opensearch` and `/v1/audit`. It remains **under observation for recurrence**. The historical failing run and its falsifying case were not found; do not claim the historical failure was reproduced. PR #253 preserves logs, served OpenAPI, and Hypothesis examples for future failures.

## Next human step: RGC pilot 02

1. Conduct pilot 02 with human annotation only and without AI assistance; record methodological findings and discard pilot labels as required by the protocol.
2. Obtain a second annotation from a different person, independently of the first annotation. Only after both human annotation files exist should the agreement calculator be run; it has not processed real annotation data.
3. Complete the independent human review F-01.
4. Decide separately whether to freeze the protocol and whether the hidden partition's provenance/isolation gates are satisfied. No case creation, labeling, system execution or benchmark metrics are authorized before those gates.

## Deferred work

- Manual chapters 01–04 have `Estado: Atual`; chapters 05–10 are linked in `docs/manual/README.md`.
- Coverage is 95% overall. PR #410 added tests only (no production behavior changes); `verification/extraction.py` (101 statements), `audit.py` (42 statements), and `orchestrator.py` (40 statements) now each have 100% line coverage. The registry and OpenAI-compatible provider also retain 100% line coverage.
- Strict mypy now covers both RGC evaluation modules. Keep the scope evidence-driven and extend it only where the gate passes.
- Security CI is clean: pip-audit found no known vulnerabilities; Bandit found no issues after comment-parser warning cleanup.
- **Snapshot histórico de 2026-10-23:** as notas v0.6.0 ainda eram tratadas como rascunho naquele momento; a publicação posterior foi confirmada e está registrada no estado atual.
- Remote branch deletion remains blocked by missing connector capability. The audit records candidates but does not claim deletion.

## Engineering gates

- Frozen `rules/`, Judge 2.0, Golden files, manifests, hashes, RGC source captures, release artifacts, and preregistrations remain protected.
- The current access log is privacy-conscious operational evidence, not proof of tamper resistance.
- `/health` remains public; rate limiting and service-owned TLS are not implemented.
- Green checks are SHA-specific and do not substitute for independent human review.
- Do not claim benchmark results, legal compliance, production readiness, or institutional partnership without evidence.


## Incremental benchmark-integrity update — 2026-10-21

**Reference SHA before this status-only update:** `eade15e0e1475689f329d8d382c12eada2f894e1`. This snapshot records the merged engineering work below; the final SHA of this documentation update must be read from its merge commit, not predicted here.

- **PR #378** — `feat(eval): enforce RGC protocol freeze gate`: RGC evaluation fails closed unless the protocol, preregistration, runner specification and an explicit freeze manifest are present.
- **PR #379** — `fix(eval): bind RGC freeze to runner integrity`: the freeze manifest binds the exact protocol, preregistration, runner specification, runner code and runner version.
- **PR #380** — `fix(eval): require declared source provenance in pilot checker`: each filled pilot case must identify a captured source, and the excerpt must be found literally in that declared source. Synthetic regression tests cover missing, unknown and mismatched source identifiers. PR #380 CI completed with 19 successful checks and one conditionally skipped design-simulation job; no checks failed.

**Scientific status is unchanged:** the RGC PT-BR protocol remains `[PROPOSTO]`; no real pilot or benchmark cases were created or labeled by this engineering work, the ATTRACTOR was not run on RGC cases, and no RGC metrics were produced. No real protocol-freeze manifest was created; the published software tag/release does not freeze the RGC protocol. The automated checks are not an independent human review, and F-01 remains open.

**Next blocking dependency:** a human must conduct pilot 02 privately, without AI assistance and without running the ATTRACTOR, then record only methodological findings. A second annotator and independent human review remain necessary before a maintainer freeze decision and any definitive dataset work.

## Incremental benchmark-integrity update — 2026-10-21 (runner 0.6.0)

**Reference SHA before this status update:** `970af6ddc7d912552e18fbc01bed534242f9b56a`. This status-only PR records the subsequent integrity work; read the merge commit for the resulting `main` SHA.

- **PR #381** — `docs(status): record RGC freeze and provenance gates`, SHA `9045549a81f4ad024782598698e2061a3a7d13c0`.
- **PR #382** — `feat(eval): require RGC annotation approval evidence`, SHA `44291a2ad2b89e783f725394c9297d982c25536a`. Evaluation now requires human agreement/adjudication evidence bound to the exact annotation inputs, cases, labels, development partition and report; agreement reports preserve input hashes.
- **PR #383** — `ci: run RGC design simulation on relevant changes`, SHA `ea4e7de19bfe9132501e466075334dddaede61d5`. The synthetic design simulation has a dedicated workflow, manual dispatch and artifact preservation.
- **PR #384** — `test(rgc): cover synthetic design simulation invariants`, SHA `5ad402ab9f73e6b592d5fb75168d54030ae2a196`. Added deterministic tests for agreement coefficients, baseline tie-breaking and synthetic prediction accuracy. All checks, including the RGC design simulation, passed for this PR.
- **PR #385** — `fix(eval): advance RGC runner version to 0.6.0`, SHA `970af6ddc7d912552e18fbc01bed534242f9b56a`. The executor version now matches the material changes to protocol-freeze, runner-integrity, source-provenance and annotation-approval gates. PR CI and post-merge CI, security and CodeQL all passed; the dedicated synthetic design-simulation workflow also completed successfully ([run 39649859657](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/39649859657)).

**Scientific status is unchanged:** the RGC PT-BR protocol remains `[PROPOSTO]`, not frozen. No real pilot or definitive benchmark cases were created, reviewed or labeled by this engineering work. The ATTRACTOR was not run on RGC cases and no RGC metrics were produced. No real protocol-freeze manifest was created; the published software tag/release does not freeze the RGC protocol. F-01 remains open and automated review is not independent human review.

**Blocking human work:** conduct pilot 02 privately without AI assistance or ATTRACTOR execution; obtain a second independent annotation; complete human review F-01; then make separate maintainer decisions about protocol freeze and the hidden partition's provenance/isolation gates.


## Additional benchmark-integrity limitation — independent annotator identity

The RGC runner binds annotation A and B by SHA-256, verifies the agreement report and requires a passing Cohen's kappa gate plus an approval/adjudication record. These controls establish artifact integrity, not the real-world identity of the people who produced the two files. The current manifest schema does not independently prove that annotator A and annotator B are different people.

- **Operational gate:** the human approver must explicitly attest that the annotations were produced independently by two different people and preserve the attestation with the private study records.
- **Possible technical hardening:** add distinct pseudonymous annotator identifiers to the agreement report and approval manifest, validate that the identifiers differ, and test missing/equal identifiers fail closed.
- **Decision boundary:** this would change the benchmark artifact schema and must be explicitly approved by the maintainer before implementation. No such schema change is made here.

This limitation does not authorize pilot case creation, system execution, protocol freeze, or benchmark claims.


## Current execution update — 2026-10-21 (manual index reconciliation)

- **Current reference SHA:** `620e39f7e2fb7437b576d7dc935cab6ffcbe08b0` ([PR #388 merge](https://github.com/Ayorinha/ayorai-opensearch/commit/620e39f7e2fb7437b576d7dc935cab6ffcbe08b0)).
- **PR #388:** merged by squash after all seven associated workflow runs completed successfully: CI, Security, CodeQL, Dependency Review, API Contract Guard, Schemathesis Full API Contract, and Golden r2 Migration. The latest run results showed success for all seven workflows.
- **Manual index:** `docs/manual/README.md` now links all ten existing chapters and explains that `Atual` is a documentation status, not proof of automatic revalidation against HEAD.
- **Open PRs:** none were returned by the repository open-PR search immediately after the merge.
- **Scientific and release boundaries unchanged:** RGC remains `[PROPOSTO]`, not frozen; no real pilot/benchmark cases or RGC metrics were created by this engineering work; F-01 and the independent human annotation/review gates remain open. v0.6.0 is published, but the software release does not freeze the RGC protocol or authorize RGC execution.
