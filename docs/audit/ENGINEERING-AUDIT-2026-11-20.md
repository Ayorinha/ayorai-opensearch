Revisão por ferramenta automatizada, publicada pelo mantenedor.

# Auditoria técnica — 2026-11-20

- **`main` auditada:** `5c757ac555746fcb28141f8dc7b9d938b5ba3b3f` (merge da #588). Workflows pós-merge nesse SHA: CI [44741658018](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/44741658018), Security [44741658038](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/44741658038) e CodeQL [44741657857](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/44741657857), todos com sucesso. A árvore é idêntica à do head `f925e43` da #588, onde passaram 37 checks, inclusive o Schemathesis.
- **Conflito de interesse:** as PRs #585 a #588 e #571 foram produzidas com a mesma ferramenta automatizada que fez esta auditoria. Nesses pontos, esta não é a revisão humana independente pedida no `CONTRIBUTING.md`.
- **Método:** leitura do código e execução direta. Foram usados:
  - bateria adversarial sintética no `check_documents` (37 casos);
  - 20 cenários de adulteração e falha da trilha de auditoria;
  - sondas da API com `TestClient`;
  - Bandit e pip-audit;
  - inspeção dos workflows;
  - comparação caso a caso do Golden v0.1 entre a `main` e a #571;
  - teste do gateway nginx com duas réplicas em Docker.
- **Limite dos testes:** os testes sintéticos são verificações de engenharia, não resultados científicos.

## 1. Achados e situação

Nenhum artefato protegido foi alterado. Todas as correções estão em PRs abertas e **não integradas**; cada uma depende de autorização individual do mantenedor.

| ID | Gravidade | Achado | Evidência | Situação |
|---|---|---|---|---|
| P0-1 | P0 | `/v1/check` e `/v2/audit` avaliavam só os 3 trechos mais relevantes entre todos os documentos. Com 4 documentos que confirmam e 1 que contradiz explicitamente, o resultado era `verified` e o contraditório nunca era examinado. | Reprodução nas duas ordens; `TOP_K_PASSAGES = 3` em `verification/document_check.py` | Corrigido na #589 (`document-check-3`) |
| P1-1 | P1 | Cópias quase idênticas (caixa, acento, pontuação, prefixo) contam como fontes independentes e chegam a `verified`. `normalized_content_hash` nunca é preenchido. | 4 casos adversariais | **Depende de autorização:** é a regra de independência do Judge (ADR-002 §3) |
| P1-2 | P1 | Texto colado sem URL chega a `verified`: `retrieved_at` é o momento da checagem e `origin_id` é o hash do conteúdo. | Caso base com 2 documentos anônimos | **Depende de autorização:** proveniência do Judge (ADR-002 §2) |
| P1-3 | P1 | `/v1/check` e `/v2/audit` usam o Judge 1.x (emite `verified` e converte `UNVERIFIED` em abstenção), embora o ADR-009 seja normativo e limite as regras 1.x "até a v0.5.0". | `document_check.py` usa `judge.py`; a versão do projeto é 0.8.0 | **Depende de decisão:** migrar para o `r2-a` ou registrar uma exceção |
| P1-4 | P1 | O OpenSearch juntava todos os resultados num texto cortado em 2.000 caracteres, o que dava um único documento: teto `partially_supported`, sem URL nem ID por resultado e conteúdo perdido. Busca sem resultados virava "fonte independente". | 5 fontes concordantes resultavam em `docs=1` | Corrigido na #591 |
| P1-5 | P1 | O rastro do `/v2/audit` era gravado antes da adjudicação, só com contagens. A documentação dizia que o resultado era registrado. | `GET` mostrava `not_adjudicated`, sem vínculo | Corrigido na #590 (`r2-v4` com `adjudication_sha256`) |
| P1-6 | P1 | Pergunta, condição, meta e retificação eram aceitas como apoio. | Bateria adversarial: 27/37 antes; 31/37 com a #592 | Corrigido na #592 (detector v12; Golden inalterado) |
| P1-7 | P1 (científico) | Acurácia na `main`: Golden v0 com 7/30 (IC95% 10–40%) e v0.1 com 10/30 (IC95% 17–50%), abaixo do baseline de classe majoritária (13/30). Erro dominante: `UNVERIFIED` quando a referência espera apoio. | `ayorai eval --suite golden-v0[.1]` | Aberto. Não é corrigível sem trabalho metodológico; não ajustar ao Golden |
| P2-1 | P2 | Apagar uma linha inteira da trilha não deixa vestígio; a retenção também apaga sem registro. | `DELETE` seguido de `verify_all` = `{valid:1, invalid:0}` | **Depende de decisão de desenho:** encadeamento ou checkpoint assinado (existe Merkle em `auditlog/`, do ADR-010) |
| P2-2 | P2 | Não havia como aposentar uma chave HMAC sem invalidar os rastros dela. | Rotação seguida de `verify_all` com os antigos `invalid` | Corrigido na #594 (`reseal_with_active_key`) |
| P2-3 | P2 | `docs/STATUS.md` descrevia a `main` de 17/11. | — | Corrigido nesta PR |
| P2-4 | P2 | A descrição pública da #588 termina com um rodapé promocional de ferramenta (AGENTS.md §2). | Corpo da #588 | **Depende de autorização (AGENTS.md §3):** propõe-se remover a linha e o separador anterior |
| P2-5 | P2 | Erros 401, 404 e 503 do OpenSearch devolviam ao cliente a URL interna completa (host, porta e índice). | Reproduzido com `httpx.MockTransport` | Corrigido na #593 |
| P2-6 | P2 | 18 PRs abertas, algumas empilhadas (#584 sobre a #580, #527 sobre a #505) e sobrepostas (#553 e #583; #554 e #580). | API do GitHub | **Decisão do mantenedor** |
| P3-1 | P3 | `requirements-benchmark-pilot.txt` tem `transformers` 4.55.4, `pyarrow` 21.0.0 e `accelerate` 1.10.1 com avisos conhecidos (pip-audit). São pins históricos usados em 3 workflows DEV. | pip-audit | **Decisão do mantenedor:** isolar sem trocar pins |
| P3-2 | P3 | Limite de requisições local ao processo. | Documentado | Gateway testado (seção 3) |
| P3-3 | P3 | Erros 422 ecoam a entrada do próprio cliente. | Sonda da API | Baixo risco; sem mudança |
| P3-4 | P3 | SQLite local é ponto único para várias réplicas. | Desenho | Decisão de infraestrutura |
| P3-5 | P3 | Retenção desligada por padrão; dono pseudônimo; sem exclusão por titular. Nenhuma conformidade legal é declarada. | Código e manual | Decisão de produto e jurídica |

## 2. Controles verificados que funcionam

- **Caminho do veredito:** só regras determinísticas. O detector é o `RuleStanceDetector`, envolvido pelo `ConservativeStanceDetector`, e o veredito sai de `verification/judge.py` ou `judge2/`. `council.py` e `arena.py` não estão ligados à API. O provider de LLM nunca marca `independent=True`, e o `/v2/audit` filtra pelo campo `independent`.
- **Trilha (19 de 20 cenários):**
  - remoção do MAC, alteração de conteúdo e de dono, downgrade de versão → `invalid`;
  - banco selado sem chaves → não abre;
  - chave errada → `invalid`;
  - banco corrompido → erro;
  - reinício e backup/restauração preservam o rastro, e o backup não sobrescreve;
  - a retenção remove só o vencido;
  - 8 threads (200 gravações) e 2 conexões no mesmo arquivo → sem erro;
  - leitura do rastro de outro dono → 404;
  - a exclusão de uma linha inteira não é detectada (P2-1).
- **API:**
  - chave com menos de 32 caracteres recusada; `Authorization` e `X-API-Key` juntos → 401; 401 genérico;
  - 404 idêntico para rastro inexistente e rastro de terceiro;
  - campos extras e versão de schema recusados; JSON e UTF-8 inválidos → 422; corpo acima do limite → 413; limite de 50 afirmações;
  - `X-Request-ID` sempre gerado pelo servidor.
- **Cadeia de suprimentos:**
  - workflows com `contents: read` ou `permissions: {}` no topo, actions fixadas por SHA, nenhum `pull_request_target`;
  - imagem com base fixada por digest e 33 de 33 dependências com `--require-hashes`, rodando como usuário `attractor`;
  - Bandit sem achados;
  - pip-audit sem vulnerabilidades no lock da imagem nem no ambiente NLI.

## 3. Gateway com duas réplicas (teste local de integração)

Teste local em Docker, não validação em produção. Montagem: `nginx:1.27-alpine` com a configuração de `docs/security/EDGE-RATE-LIMIT.md` (porta 8080 sem TLS; `rate=60r/m`, `burst=20`) na frente de duas réplicas da imagem do serviço, com `FORWARDED_ALLOW_IPS` apontando para o gateway. O `nginx -t` aceitou a configuração.

| Cenário | Resultado |
|---|---|
| 100 requisições direto às 2 réplicas, sem gateway | 100 × 404, nenhum 429: cada réplica tem seu próprio limite |
| 100 requisições pelo gateway | 21 × 404 e 79 × 429: limite agregado, com tráfego nas duas réplicas |
| `X-Forwarded-For` forjado pelo gateway, logo após o anterior | 429: o gateway sobrescreve o cabeçalho |
| 130 requisições direto a uma réplica, cada uma com `X-Forwarded-For` forjado diferente | 120 × 404 e 10 × 429: o cabeçalho de origem não confiável é ignorado |

Os logs das réplicas trazem rota, status e duração, sem IP do cliente nem conteúdo.

## 4. Avaliação da #571 (detector v11, Golden v0.1 de 10/30 para 11/30)

- **Fato verificado:** comparando todos os casos entre a `main` e a #571, só a previsão do `x02` muda, de `PARTIALLY_SUPPORTED` para `CONFLICTING`. A referência é `CONFLICTING`: o doc-005 diz 2,0 milhões de clientes e o doc-018 diz 2,3 milhões. O digest calculado (`1fd6fdb7…`) é o candidato documentado.
- **Ressalvas:** a correção foi desenhada depois de ver a falha num conjunto público, então há risco de sobreajuste; +1 caso em 30 não tem significância estatística; a #571 foi produzida pela mesma ferramenta. Recomenda-se revisão humana independente antes da aprovação.

## 5. Decisões reservadas ao mantenedor

1. Autorizar ou não cada uma das PRs #589, #590, #591, #592, #593 e #594 (e esta).
2. #571: aprovar ou recusar a mudança de referência do Golden v0.1.
3. P1-1 e P1-2: autorizar a mudança das regras de independência e de proveniência do Judge.
4. P1-3: migrar `/v1/check` e `/v2/audit` para o `r2-a`, ou registrar uma exceção ao ADR-009.
5. P2-1: desenho da detecção de exclusão (encadeamento, checkpoint assinado ou log Merkle).
6. P2-4: remover o rodapé da descrição da #588.
7. P2-6 e P3-1: destino das PRs abertas e isolamento dos pins históricos.

## 6. Matriz de maturidade

Cada área foi avaliada pelo que a evidência mostra, sem percentuais. "PR aberta" significa corrigido e testado, mas não integrado.

| Área | Estado atual | Evidência | Falhas pendentes | Critério objetivo de conclusão |
|---|---|---|---|---|
| Arquitetura | Separação entre inteligência e veredito respeitada no caminho da API | Seção 2 | P1-3 (dois contratos de Judge em uso) | Uma única família de regras normativa por rota, documentada no ADR |
| Judge | Determinístico e reprodutível; contagem de clusters correta | `judge.py`; `tests/verification/test_judge2_*.py` (o mapeamento explícito para T1–T11 do ADR-009 não foi verificado) | P1-1, P1-2; P0-1 e P1-6 em PR aberta | P1-1 e P1-2 decididos; #589 e #592 integradas; bateria adversarial sem falso apoio |
| Evidências | Fonte independente separada do LLM | Seção 2 | P1-4 em PR aberta; adaptador HTTP genérico ainda junta tudo | #591 integrada; adaptador genérico com schema declarado ou desativado |
| API | Contratos estáveis, Schemathesis verde | 37 checks da #588 | P1-5 e P2-5 em PR aberta | #590 e #593 integradas; Schemathesis verde no SHA final |
| Segurança | Autenticação, isolamento, limites e cabeçalhos verificados | Seção 2 | P2-5 em PR aberta; P3-3 | #593 integrada; revisão humana independente da área |
| Trilha de auditoria | HMAC efetivo contra alteração, downgrade e remoção de MAC | 19 de 20 cenários | P2-1; P1-5 e P2-2 em PR aberta | #590 e #594 integradas; detecção de exclusão decidida e implementada |
| Infraestrutura | Imagem endurecida; Compose com volume persistente; gateway testado localmente | Seção 3; testes Docker da #586 | Sem implantação real; SQLite por réplica | Implantação de homologação com gateway, TLS e backup testados |
| Observabilidade | Log estruturado sem conteúdo, com `request_id` | Logs da seção 3 | Sem métricas ou alertas ligados a uma plataforma | Painel com latência, 429/503 e falhas de verificação da trilha, com alerta |
| Engenharia de software | 2374 testes em 3.11, 3.12 e 3.13; ruff e mypy limpos; mutação nas mudanças novas | CI e testes locais | Mutação só nas mudanças desta auditoria | Mutação periódica nos módulos críticos, com sobreviventes triados |
| Cadeia de suprimentos | Locks com hash, actions fixadas, Grype, SBOM e SLSA | Workflows; pip-audit | P3-1 | Pins históricos isolados de qualquer caminho com segredos ou entrada externa |
| Benchmark científico | Golden v0 e v0.1 abaixo do baseline; RGC não congelado | P1-7; `docs/STATUS.md` | Tudo o que depende de anotação humana | Protocolo RGC congelado, segunda anotação, execução única autorizada e resultado publicado com IC |
| Documentação | Corrigida nesta auditoria onde estava errada | Esta PR e as PRs acima | Rodapé da #588 (P2-4) | STATUS igual à `main` real a cada integração |
| Preparação para POC | Fluxo ponta a ponta existe; vínculo da adjudicação e fontes separadas em PR aberta | `docs/poc/POC-PROPOSAL.md` | #589, #590, #591 não integradas; P1-1 e P1-2 | Critérios de aceitação da proposta de POC atendidos em homologação |
| Preparação para produção | Não validada | — | Implantação real, revisão independente, P1-1, P1-2, P1-3, P2-1 | Implantação real com evidência de operação, recuperação e segurança |

**Níveis separados:**
- **Maturidade de engenharia:** avançada no núcleo (Judge, trilha e API), com correções relevantes aguardando integração.
- **Validação científica:** ausente. O Golden atual está abaixo do baseline e o RGC não está congelado.
- **Prontidão operacional:** só testes locais; nenhuma implantação real.
- **Prontidão institucional:** nenhuma certificação, homologação ou validação externa existe ou é alegada.
