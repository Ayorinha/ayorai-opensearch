# Changelog

All notable changes to AYORAI ATTRACTOR are documented here.

## [Unreleased]

Preparação da próxima versão de produto. Nenhuma tag, release ou DOI foi criado. Não traz resultado confirmatório de acurácia; o protocolo RGC permanece não congelado.

### API
- Correção (stance, `/v1/check`, detector v16, AP1): quando o trecho traz um valor por ano em orações separadas ("40 milhões em 2023 e 55 milhões em 2024"), o valor do ano afirmado passa a ficar ligado ao sujeito e ao atributo da frase; a afirmação de 40 milhões em 2024 é refutada (na v15, abstenção). Golden v0, v0.1 e smoke-v0 inalterados.
- Correção (stance, `/v1/check`, detector v15): defeitos encontrados pela bateria sintética multidomínio de 2026-11-22. Unidades da mesma grandeza (MW e kW, km e m, dias e horas) passam a ser comparadas depois de normalizadas; antes, "120 kW" confirmava "120 MW". O valor de outro ano na mesma frase ("120 milhões em 2023 e 95 milhões em 2024") deixa de apoiar a afirmação sobre 2024. O "no" português ("investe no setor têxtil") não é mais lido como negação inglesa. Um trecho sobre outra entidade, uma filial ou um nome semelhante ("Banco Horizonte Sul") não confirma nem contradiz. Uma afirmação composta não é refutada por um trecho que confirma só uma das partes. Substantivos de tipo antes de um nome ("município de", "estudo") não contam como predicado. Anos de 1000 a 1899 depois de "em" passam a ser anos. Na bateria de 600 casos, o falso `refuted` caiu de 11,9% para 0% e o falso apoio de 5,6% para 0%; os casos são sintéticos e os rótulos foram definidos pelo autor a partir do contrato, sem anotação humana. Golden v0, v0.1 e smoke-v0 inalterados.
- Correção (stance, `/v1/check`, `/v1/fields` e `/v2/audit`): um ano de outro evento refutava a afirmação. "A receita da Vértice foi de 40 milhões em 2024." contra "A Vértice foi fundada em 1998 e tem sede em Curitiba." saía `refuted`, porque o "em 2024" da afirmação e o ano de fundação eram comparados como o mesmo fato. Agora um conflito de ano só conta quando o ano está ancorado na proposição da afirmação: outro fato dela (receita, contagem, valor) é comparado no mesmo trecho, ou a afirmação só traz anos e compartilha com o trecho uma palavra de predicado que não é nome próprio. Sem âncora, o resultado é abstenção (`insufficient_evidence`). O mesmo vale para outro período: se a afirmação liga um fato a um ano (receita de 2024) e o trecho só fala de outros anos (receita de 2023), o trecho não confirma nem contradiz. Nomes no início da frase e verbos genéricos ("ter", "ser", "estar") não contam como predicado compartilhado. Contradições reais, apoio, conflito e as referências congeladas do Golden v0, v0.1 e smoke-v0 não mudaram. O defeito foi encontrado pela POC remota de 2026-11-22 (caso C2). Numerais de nomes próprios ("Holding Três Rios", "Construtora 2000") passam a ser identificadores, e não quantidades ou anos: antes, um deles podia transformar uma contradição real de data em abstenção (P8, bateria multidomínio de 2026-11-22). Um ano em título na evidência ("Relatório Anual 2023") continua datando o que reporta.
- Observabilidade: `GET /ready` (readiness, sem chave; 503 quando o banco da trilha não responde), separado do `GET /health` (liveness); `GET /metrics` em formato Prometheus, protegido pela chave, com contagem por rota, método e status, histograma de latência por rota e falhas de gravação da trilha. Rótulos limitados: nenhum conteúdo, chave ou trace ID. Regras de alerta em `docker/observability/prometheus-alerts.yml`; SLOs propostos e recuperação em `docs/observability/SLO-AND-ALERTS.md`.
- Correção: requisições a `/v2/audit` recusadas antes do roteamento (401, 413, 429) apareciam no log de acesso como `unmatched`; agora são registradas como `/v2/audit`.
- Correção (proveniência, ADR-002 §2): no `/v1/check`, texto enviado pelo cliente chegava a `verified`, o veredito reservado a evidência com proveniência completa, embora o servidor nunca tenha acessado a origem (a `url` do documento é só metadado). Cada documento informa agora `provenance`: `client_supplied` (teto `supported`) ou `server_retrieved` (obtido pelo próprio servidor no `/v2/audit`; com URL, pode chegar a `verified`). A proveniência entra na identidade do `trace_id` (`document-check-trace-3`, `document-check-5`).
- Correção (independência das fontes, ADR-002 §3): no `/v1/check` e no `/v2/audit`, a origem de cada documento era o SHA-256 do texto bruto, então o mesmo texto com outra caixa, sem acentos, com outra pontuação ou com um prefixo contava como segunda fonte independente e levava a `verified`. Agora documentos com o mesmo texto normalizado, ou quase-duplicatas (contenção ≥ 0,8 de sequências de 5 palavras), compartilham a origem (`document-check-4`). Um texto curto reproduzido dentro de outro documento também é a mesma origem.
- Correção: os providers OpenSearch juntavam todos os resultados num único texto, cortado em 2.000 caracteres. O `/v2/audit` via então um só documento: nunca mais de uma fonte independente (teto `partially_supported`), sem URL nem ID por resultado, e o conteúdo depois do corte se perdia. Agora cada resultado é uma fonte própria (`ProviderResponse.documents`), com URL canônica, ID e data de publicação quando o índice os tem, e até 20.000 caracteres. Resultados com a mesma URL formam um único cluster. Uma busca sem resultados deixou de produzir uma "fonte independente" com o texto fixo de ausência.
- `POST /v2/audit`: busca e adjudicação ADR-002 de ponta a ponta. Só evidência independente vira documento (#587).
- Correção: o rastro do `/v2/audit` era gravado antes da adjudicação e guardava só contagens; não mostrava quais vereditos o cliente recebeu. Agora ele é gravado depois, como `r2-v4` (esquema 4), e vincula `check_trace_id` e `adjudication_sha256` (SHA-256 RFC 8785 da adjudicação devolvida) ao digest de replay e ao HMAC. O cliente recalcula o mesmo digest a partir da resposta.
- Correção: a seleção de trechos do `/v1/check` e do `/v2/audit` deixava documentos fora da adjudicação quando outros os superavam em relevância. Uma contradição explícita podia ser ignorada, e o resultado sair `verified`. Agora o melhor trecho de cada documento relacionado também é avaliado (`document-check-3`).
- `/v1/fields`: somente dígitos ASCII simples (field-check-3) e sinal de menos ligado ao número ou valor (field-check-4) (#545, #546).
- Respostas dos providers HTTP limitadas em tamanho, sem compressão e com prazo total (#561).
- Limite de concorrência das rotas pesadas (HTTP 503), opcionalmente compartilhado entre workers do mesmo host com `ATTRACTOR_INFLIGHT_SCOPE=host` (#556, #563).
- Endurecimento do fencing de jobs, da integridade do armazenamento e da segurança dos providers (#555).

### Autenticação
- Escopos, expiração e revogação sem reinício das chaves de API (ADR-012, DEC-031).
  - **Arquivo de chaves:** `ATTRACTOR_API_KEYS_FILE` é relido quando muda; cada chave tem escopos (`verify`, `audit:write`, `audit:read`, `metrics`), `expires_at` e `revoked_at`/`revoked_by`.
  - **Respostas:** chave desconhecida, expirada ou revogada recebe 401; sem o escopo da rota, 403.
  - **Arquivo inválido depois da subida:** o serviço mantém o último válido, e a métrica `attractor_api_keys_reload_failures_total` dispara o alerta `AttractorApiKeysReloadFailing`.
  - **Emissão e revogação:** `python -m ayorai_attractor.api.keys`, com gravação atômica. A ferramenta lê a chave por stdin e grava só o digest; nunca gera nem exibe a chave.
  - **Compatibilidade:** `ATTRACTOR_API_KEYS_HMAC_SHA256` continua como antes, com todos os escopos, e o principal de cada chave não muda.

### Tenant
- Tenant distinto de principal (ADR-013, DEC-032).
  - **Campo `tenant`** no arquivo de chaves, opcional; sem ele, a chave fica no tenant `default`.
  - **Leitura:** rastros legíveis por qualquer chave do mesmo tenant com `audit:read`; 404 entre tenants. O modo legado continua só com o dono.
  - **Log de verificação:** o tenant entra no registro salgado (`ayorai.verify-record.v2`), nunca na folha pública.
  - **Sem migração:** o esquema assinado da trilha não mudou.

### Trilha de auditoria
- Registro verificável do `/v1/verify` (ADR-010, fases 2 e 3).
  - **O que faz:** com `ATTRACTOR_VERIFY_LOG_MODE=local` ou `required`, cada decisão `r2-a` entra num log Merkle RFC 6962 com checkpoints C2SP assinados em Ed25519, e a resposta ganha `audit_status` e `audit_receipt`. O recibo traz folha, prova de inclusão, checkpoint assinado, sal e registro, e é verificável sem o servidor com a chave publicada em `GET /v1/verify/log`.
  - **Contrato:** `Idempotency-Key` (mesmo recibo; outra entrada devolve 409); o modo `required` falha fechado com 503, sem veredito.
  - **Privacidade:** o veredito fica só no compromisso com sal, e `erase()` atende pedidos de apagamento.
  - **Padrão:** `off`, que não muda nada.
  - **Dependência nova:** `cryptography` (Ed25519), incluída no lock da imagem com hash.
  - **Desempenho:** árvore incremental, com gravação de cerca de 1,2 ms até 50 mil eventos e `verify_log()` linear.
  - **Decisões 5 a 7 da ADR-010 registradas em 2026-11-21:** escritor Python (DEC-028), testemunhas em duas etapas (DEC-029) e carimbo do tempo ICP-Brasil adiado (DEC-030). Ficam registradas na ADR-010, no ADR-009 §15.1 e no `DECISIONS-APPROVED.md`.
  - **Verificação independente:** recibos, checkpoints e provas de consistência conferidos com `golang.org/x/mod/sumdb/note` e `transparency-dev/merkle` (`tests/auditlog/vectors/`).
- Endurecimento do log verificável (P2, ADR-010). Relatórios: `docs/audit/P2-REPORT.md` e `docs/audit/P2-CLOSURE-REPORT.md`.
  - **`verify_log()`:**
    - reabre o compromisso de cada registro com o sal guardado;
    - aponta registro órfão, restaurado ou parcialmente apagado;
    - aponta checkpoint ausente e folha de esquema desconhecido.
  - **Idempotência:**
    - um reenvio só devolve o recibo guardado se ele ainda abre o próprio evento (folha, assinatura, inclusão, compromisso e entrada); se não abre, o modo `required` responde 503 e o `local` responde `not_recorded`;
    - `verify_log()` audita a tabela de idempotência;
    - o apagamento LGPD também apaga o registro e o sal do recibo guardado, e o reenvio de um evento apagado recebe 409.
  - **Testemunhas C2SP:** cliente `tlog-witness` e verificação de cossignaturas Ed25519, sem testemunha configurada. Foi testado contra a testemunha de referência torchwood v0.10.0, executada localmente.
- Correção: uma falha da retenção automática, que roda depois do commit do rastro, deixa de chegar ao chamador como erro de gravação. O rastro já está gravado; a purga parcial é desfeita e o erro vai para o log (só o tipo da exceção), e a retenção roda de novo na próxima gravação após o intervalo.
- Correção: uma falha ao gravar a entrada da cadeia (ou o registro de uma purga) desfaz a transação inteira. Antes, o rastro ou a exclusão ficavam pendentes na conexão, e a próxima gravação bem-sucedida os confirmava: o chamador recebia erro, mas o rastro ficava gravado sem entrada na cadeia. A selagem, a resselagem e o sequenciamento também desfazem a transação em caso de erro, e a rotação confere a cadeia sob a mesma trava que a reassina.
- Cadeia de sequência (`audit_chain`, aditiva; rastros, digests e MACs existentes não mudam): todo rastro gravado entra numa sequência com elos encadeados por HMAC. `verify_chain()` detecta rastro apagado no meio da trilha, entrada removida ou reescrita e rastro inserido fora da API; com um `checkpoint()` guardado fora do host, detecta também truncamento e rollback. A retenção registra suas purgas na cadeia. `sequence_unsequenced()` encadeia uma base antiga; `reseal_with_active_key()` reassina a cadeia íntegra. Resolve a parte local do P2-1 (#433).
- Rotação de chave HMAC: `AuditTraceStore.reseal_with_active_key()` assina de novo, com a chave ativa, os rastros válidos assinados por chaves antigas, para que elas possam ser aposentadas. Rastros inválidos não são re-selados. O procedimento está no manual de operação.
- Rastros com dono, formato r2-v3, metadados, backup e HMAC externo (`ATTRACTOR_AUDIT_HMAC_KEYS`) (#564).
- HMAC exigido em todas as versões de replay quando há chaves configuradas: um rastro selado não volta a validar sem o MAC (#575).
- `ATTRACTOR_AUDIT_HMAC_REQUIRED` impede que o serviço suba sem chaves HMAC (#586).
- Retenção automática com `ATTRACTOR_AUDIT_RETENTION_DAYS` (desligada por padrão): rastros vencidos são removidos na inicialização e, no máximo, uma vez por hora nas gravações (#586).
- Correção: o Docker Compose guarda os rastros no volume nomeado `attractor-audit`. Antes, eles se perdiam a cada recriação do contêiner. A imagem cria `/app/.attractor` com dono no usuário do serviço (#586).

### AYORAI-PT-NLI (ADR-008), integração de inferência
- Novo `ayorai_attractor.verification.pt_nli`: backend EuroBERT para stance por pares (SUPPORTS, CONTRADICTS, NEUTRAL) e `build_pt_nli_detector()`, que se usa em `check_documents(stance_detector=...)`.
- **Carregamento com falha fechada:**
  - sem código remoto (`trust_remote_code=False`; exige `transformers>=5.3.0`, com EuroBERT nativo);
  - revisão como SHA completo;
  - `model_type` `eurobert`;
  - três rótulos de NLI exigidos. O modelo base público, sem cabeça NLI, é recusado.
- **Licença:** pesos `UNAUDITED` só carregam em modo de avaliação ou com opt-in explícito.
- **Escopo:** sem treinamento, sem dependência nova, sem ligação com a API e sem mudança no Judge, no Golden ou no RGC. Modelo base fixado em `EuroBERT/EuroBERT-210m@39b51e15`.

### Detector de posição (stance) por regras
- v8, com erros conhecidos fixados em testes (#565).
- v9: negação restrita às frases da afirmação e negação relatada classificada como neutra (#570).
- v10: afirmações hipotéticas ou não assertivas e valores-limite ("acima de", "mais de", "superou") não confirmam a afirmação (#585).
- v12: pergunta ("…em 2024?"), condição no início da frase ("Se…", "Caso…", "Supondo que…"), meta ou intenção ("a meta é atingir…", "pretende") e aviso de retificação ou errata na frase da afirmação ou na vizinha, no mesmo parágrafo, deixam de confirmar a afirmação; um aviso em outra parte do documento não interfere. Quando a palavra faz parte da própria afirmação ("a meta de inflação foi de 3%"), ela continua sendo confirmada. Golden v0 e v0.1 inalterados. A versão 11 ficou reservada à mudança de escala da #571 e não foi usada.
- v13: número seguido de palavra de escala sem moeda é lido com a escala ("1,2 bilhão" e "1.200 milhões" são a mesma quantidade; antes, 1,2 contra 1200 gerava falsa contradição). Um substantivo contável logo depois da escala ("2,0 milhões de clientes") vira contagem desse substantivo. Muda um caso do Golden v0.1 (`x02`, agora correto): 11/30 em vez de 10/30, com a nova referência `1fd6fdb7…` aprovada pelo mantenedor em 2026-11-21. Golden v0 inalterado (#571, refeita sobre o v12).

### Segurança, cadeia de suprimentos e imagem
- Isolamento dos rótulos gold no benchmark DEV da Phase 1b (P3/A1). Relatório: `docs/audit/P3-A1-HARDENING-2026-11-26.md`. Nenhuma execução DEV/TEST foi feita.
  - **Inferência sem rótulos:** os jobs de inferência recebem só `record_id`, documento, afirmação e coorte, cifrados. O identificador do registro não depende do rótulo.
  - **Caches cifrados à parte:** rótulos gold e scores ficam em caches separados, com chaves distintas, e só são juntados na avaliação.
  - **Manifesto e entrada cifrados:** o manifesto (IDs por registro) e a entrada de inferência sobem cifrados com AES-256-GCM. O SHA-256 da entrada é conferido antes de cifrar e depois de decifrar.
  - **Execuções de origem:** re-agregação e experimentos só aceitam origem com commit na `main` deste repositório.
  - **Retenção:** os caches reenviados não ultrapassam a janela de 30 dias da execução de origem. Decisão DEC-033 (2026-11-28, opção A).
  - **Execução minimal:** não recebe a chave gold nem guarda rótulos gold (`--discard-gold-labels`). Testes de contrato limitam os secrets de cada workflow a uma lista permitida.
  - **Dependências travadas por hash:** os jobs que têm as chaves e não rodam inferência instalam `requirements-phase1b-protected.txt` com hashes (`cryptography` 50.0.2, `pyarrow` 23.0.1). Antes instalavam `cryptography` 46.0.3, que tem alertas de segurança publicados.
- `docker-compose.yml` endurecido: raiz só de leitura, `/tmp` em tmpfs `noexec,nosuid`, `cap_drop: ALL` e `no-new-privileges`, validados na homologação local de 2026-11-21 (`docs/audit/HOMOLOGATION-LOCAL-2026-11-21.md`).
- Ferramentas de operação: `scripts/ops/homologation_smoke.py` (16 verificações de segurança e operação contra uma instância) e `scripts/benchmarks/load_test.py` (carga em laço fechado). A medição de capacidade de 2026-11-21 está em `docs/benchmarks/CAPACITY-2026-11-21.md`.
- Correção: erros de providers deixam de expor ao cliente da API a URL interna completa da busca (host, porta e índice), que aparecia em `failures[].message` em respostas 4xx e 5xx do OpenSearch. O cliente recebe só o tipo do erro; o detalhe vai para o log do servidor.
- Imagem Docker fixada por digest, dependências instaladas por lock com hash e pisos de segurança das dependências (#556, #562).
- Varredura da imagem com Grype e proveniência SLSA assinada das distribuições (#568).
- Dependabot sem os pins históricos do benchmark e sem novas linhas de Python na imagem (#567); `actions/download-artifact` 8.0.2 (#520); ruff 0.17.5 (#569).
- Documentação da integridade da auditoria e dos controles de admissão (#574) e guia de limite de requisições compartilhado entre réplicas (`docs/security/EDGE-RATE-LIMIT.md`).

### RGC e avaliação (sem resultado)
- Phase 1b DEV (P3/A1, DEC-034, opção A): a primeira execução protegida minimal encontrou no DEV fixado 46 identidades repetidas (50 linhas extras), 5 delas com rótulos divergentes, e parou antes de cifrar ou inferir. Agora cópias com o mesmo rótulo contam uma vez, e identidades com rótulos divergentes são excluídas: o pipeline nunca escolhe um rótulo gold. A mesma regra vale para o manifesto, a preparação dos artefatos e o mapa de documentos. O manifesto passa a `phase1b-dev-manifest-v3` e registra só as contagens da resolução. Manifestos v2 não são reaproveitáveis.
- Texto superado por retificação não é evidência (Emenda 4, DEC-011 opção A): o corpus pode declarar `superseded_spans` por documento, validados com falha fechada, e o runner `rgc-eval/0.14.0` retira da adjudicação os trechos que os tocam, listando-os em `excluded_superseded_passages`. O teste de propriedade que era `xfail` passa a ser normal; o Judge não muda; o corpus atual não declara o campo.
- DEC-027: reconciliação estatística do RGC (#548). O runner `rgc-eval/0.8.0` e a ferramenta de concordância entre anotadores sorteiam toda amostra bootstrap com o RGC-PRNG-1 (gerador SHA-256 especificado byte a byte, com vetores de referência publicados) e calculam intervalos de 95% pelo percentil tipo 7 de Hyndman–Fan. Os intervalos deixam de ser numericamente comparáveis com `rgc-eval/0.7.0` (#549).
- Gramática canônica única de ID de artigo (E1, #550); componentes de artigos conectados determinísticos (#532); gate de resolução de componentes antes da anotação (E4/D7, #551); H1 por sign-flip de componentes e IC por componente no runner (Emenda 11, #552).
- Protocolo de relação entre passagens (proposto) e harness para contradições de `/v1/check` (#547).
- DEC-022 na concordância entre anotadores: `rgc_agreement.py` publica o IC95% de kappa por bootstrap de componente (`ci95_component_bootstrap`, com réplicas indefinidas e marcação de instável) e mantém o IC por caso como sensibilidade. A CLI exige `--cases` (lê só `case_id` e `cited_article_ids`) e registra `inputs.cases_sha256`. O runner `rgc-eval/0.13.0` recalcula o relatório com os componentes dos casos aprovados e recusa relatório sem o IC por componente ou calculado sobre outros casos. O gate continua na estimativa pontual. As emendas datadas do texto normativo estão propostas em `docs/eval/AMENDMENT-PROPOSAL-2026-11-21-DEC-022.md`.
- Testes do Judge 2.0 e cenários E2E (#556).
- Runner `rgc-eval/0.12.0` (#580): captura única, em snapshots imutáveis, dos bytes de todas as entradas, do protocolo, do manifesto de congelamento e do código congelado; validação, avaliação e hashes usam só os snapshots; manifesto de execução verificado e publicação atômica sem sobrescrita.
- A avaliação roda num interpretador Python isolado (`-I -S`), com ambiente mínimo e importando só o snapshot (#584). O modo filho só é aceito dentro de um snapshot criado pelo processo pai; variáveis de ambiente forjadas não pulam mais a exigência de checkout limpo da partição oculta.
- A ferramenta de concordância calcula kappa e hashes sobre os mesmos bytes lidos uma única vez e recusa JSON com chave duplicada (#576).
- O gate de H1 exige resolução estatística suficiente (`significance_below_005_possible`) quando o teste primário é o sign-flip por componente (#577).
- `docs/eval/STATISTICS.md` reconciliado com a DEC-027 e com o código atual (#583); registros metodológicos datados de 2026-11-13 e 2026-11-17 (#539, #581).
- A revisão técnica dessas mudanças foi feita por ferramenta automatizada; a revisão humana independente prevista no `CONTRIBUTING.md` continua pendente. O protocolo RGC continua [PROPOSTO]; nenhuma execução RGC foi feita.

### Documentação
- Preparação da próxima release (`docs/engineering/RELEASE-PREP-NEXT.md`): o que entra, compatibilidade, evidências, reprodução independente da distribuição (SHA-256 idênticos aos do CI para `main` @ `f1c7621`) e passos de publicação do mantenedor. Nenhuma tag, release ou DOI criado.
- Relatórios F1.2 (`reports/f1.2-*.json`) sem caminhos absolutos de ambientes de execução: `package_file` passa a ser relativo, e os três hashes semânticos foram recalculados e registrados, junto com os antigos, em `docs/eval/F1.2-RESULTS.md`. Nenhuma métrica mudou. O guia de anotação passa a dizer, como a Emenda 4, que ausência de evidência que aborde a afirmação é `UNVERIFIED`.
- Auditoria pós-encerramento de 2026-11-21 (`docs/audit/POST-CLOSURE-AUDIT-2026-11-21.md`): revisão pós-merge das #599 a #603, inventário das 92 branches por conteúdo, IDs DEC-025 e DEC-026 reservados como propostas não decididas, ADR-010 no índice de ADRs, remissão normativa no guia de anotação e matriz de prontidão para POC e produção no `ROADMAP.md`.
- ADR-011 (família de regras do Judge por rota), ADR-001 aceito, decisões DEC-001, DEC-003, DEC-004 e DEC-006 registradas, índice das aprovações em `DECISIONS-APPROVED.md`, roteiro de longo prazo (`docs/ROADMAP.md`) e política dos pins históricos (`docs/security/HISTORICAL-PINS.md`, com teste de isolamento).
- `/v1/check`, `/v1/fields`, dono dos rastros, backup e novas variáveis documentados (#566); status de engenharia atualizado (#572, #578).

### Manutenção
- Phase 1b, P4-01 (cadeia de suprimentos do job de inferência): os jobs `shard`, que têm a chave de artefato e decifram o DEV, passam a instalar só wheels com hash conferido (`requirements-phase1b-torch-cpu.txt`, `requirements-phase1b-inference.txt`), com versão e hash em todo pacote, inclusive os transitivos, que antes não tinham versão fixada. O torch vai para 2.14.0+cpu e o transformers para 5.24.0, corrigindo os alertas altos das duas versões históricas; os hashes do PyTorch vêm dos wheels oficiais. A troca só entrou depois de provada a equivalência de escores com o ambiente histórico nos três modelos (`phase1b-inference-equivalence.yml`: mesma divisão em blocos, diferença máxima de 2,6e-6, nenhuma decisão trocada). Para isso, o shard lê o `tokenizer.json` de cada revisão fixada, porque o `AutoTokenizer` do transformers 5.x reconstrói o tokenizador DeBERTa-v2 de outra forma (`docs/audit/P4-INFERENCE-EQUIVALENCE-2026-11-28.md`). O `nltk` 3.9.4, com 31 alertas altos ou críticos, deixa de ser instalado: a segmentação dele está embutida em `vendor_nltk`, idêntica em 25.185 textos e conferida a cada PR. A 3.10.4 segmenta de forma diferente e não foi adotada. Também saíram do lock pacotes que o job não importa: o `pyarrow` 21.0.0 (alerta alto) e o `pandas`, com as dependências dele. O `setuptools`, só requisito de instalação do torch, vai de 78.1.0 para 84.2.1. O registro histórico do ambiente (`reproducibility/phase1b-dev-2026-11-07/`) volta para a `main`.
- Testes de recuperação: processo morto (SIGKILL) durante a escrita no log de verificação e na fila de jobs (#651).
- Diagnóstico: uma falha ao gravar o log de verificação do `/v1/verify` só incrementava a métrica; agora também gera um log `ERROR` com o modo e o tipo da exceção. Uma falha do handler no `JobExecutor` era descartada sem registro; agora gera um log `WARNING` com o job, a tentativa e o tipo da exceção. A mensagem da exceção não é registrada, porque pode conter dados da requisição ou do payload. O comportamento da API e dos jobs não mudou.
- `Makefile`: as ferramentas rodam com `python -m`, para que uma instalação fora do ambiente do projeto (pipx, `~/.local/bin`) não substitua a do projeto. `make typecheck-eval` usa `--explicit-package-bases`, como a CI; antes falhava localmente. `format` entrou no `.PHONY`.

### Limites
- Nenhum resultado de RGC existe ou foi produzido. Nenhum benchmark em português validado; nenhuma certificação.
- A troca do detector para a v11 (#571) muda a referência do Golden v0.1 e depende de aprovação explícita do mantenedor; não faz parte desta lista.
- Os limitadores de taxa da aplicação são locais ao processo. Com mais de um worker ou réplica, é preciso impor um limite agregado no gateway.

## [0.8.0] — 2026-11-13

Versão de produto e de segurança da cadeia de dependências. Não traz resultado confirmatório novo de acurácia; os resultados de benchmark desta versão são exploratórios em DEV.

### API de verificação por documentos
- `POST /v1/check`: confere afirmações ou uma resposta de IA contra documentos enviados (texto ou PDF com camada de texto); cada trecho de evidência traz offsets e página, e `UNVERIFIED` significa abstenção (#511).
- `POST /v1/fields`: compara valores enviados (dinheiro, data, CPF/CNPJ, número, texto) com um documento, com resultados `conforme`, `divergente`, `ambiguo`, `ausente` e `invalido` (#511).
- Identidade do rastro vinculada aos limites de página em `/v1/check` (#516) e à identidade completa do documento em `/v1/fields` (#515); documentação da identidade de rastro v2 (#526).

### Segurança e dependências
- Auditoria estrita de dependências no CI (#533) e validação de pins de benchmark e de actions de artefato (#525); ruff fixado em 0.17.4 (#494); downloads de releases fixadas com nova tentativa em falhas transitórias (#502); atualização do grupo codeql-action (#518).
- Ambiente NLI moderno auditado em arquivo próprio, sem alterar os pins dos workflows de produção DEV: transformers 5.22.2, huggingface-hub 1.32.0, pandas 3.1.1, pyarrow 26.0.1, torch 2.14.0 CPU e NumPy 2.3.3 único; `accelerate` removido; auditoria OSV e PyPI estrita e SBOM CycloneDX no workflow (#536).
- `project.license` passa a usar a expressão SPDX `Apache-2.0` (o formato de tabela será recusado pelo setuptools a partir de 18/02/2027).
- Nenhum `actions/checkout` persiste a credencial do GitHub; o push do `source-capture` usa o token só no comando de envio, via `GIT_ASKPASS` (#538).
- Permissões de escrita concedidas por job, nunca ao workflow inteiro (`codeql`, `source-capture`), com teste de regressão (#540).

### Benchmarks (exploratório, DEV)
- Emenda 2 do Learn then Test: limiares inelegíveis são pulados (#488). A reagregação exploratória e pós-hoc sob essa regra e a análise de poder estão registradas (#492). O resultado oficial da v0.7.0 permanece 0/11.
- Cache DEV cifrado de scores por instância e workflow de experimentos sobre o cache (#496); cache v2 com identificadores de documento (#508).
- Ensemble E3 de regra fixa (#497), pré-registro aprovado para execução exploratória (#495, #501) e relatório exploratório em DEV-A (#503).
- Roadmap de acurácia v0.8 (#489), radar tecnológico e gate de contaminação (#490), ledger de proveniência por célula A4 (#499) e DEC-024, opção B (#493).

### Governança e documentação
- Merge por agentes somente com autorização individual do mantenedor (#513).
- Decisões estatísticas por componente documentadas (#491); documentação pública alinhada à v0.7.0 (#486); DOI da v0.7.0 registrado (#485).

### Limites
- Nenhum resultado confirmatório novo. Os números de E3 e da Emenda 2 são exploratórios em DEV; o split TEST não foi usado.
- A confirmação P1 em DEV-B e a estatística por componentes do RGC (#532) não fazem parte desta versão.
- O registro travado por hash do ambiente que produziu os resultados DEV (#535) não faz parte desta versão: depende de decisão do mantenedor sobre os alertas de segurança do `nltk 3.9.4` usado por esse ambiente. Os workflows de produção DEV continuam com os pins por versão já existentes.
- Nenhum benchmark em português; o protocolo RGC permanece não congelado. Nenhuma certificação.

## [0.7.0] — 2026-11-07

Primeira medição completa em benchmark internacional (LLM-AggreFact, partição DEV) com calibração pré-registrada. O DOI desta versão registra o resultado **antes** da emenda ao pré-registro sobre limiares inelegíveis, que fica para a versão seguinte.

### Resultados registrados
- **Calibration V2 — DEV completo (PRs #479–#482):** 30.420 casos, 11 coortes, três modelos de terceiros (FactCG, MiniCheck, mDeBERTa; licença MIT), FactCG e MiniCheck com protocolos oficiais de referência e mDeBERTa com protocolo próprio do AYORAI, em CPU fp32. FactCG selecionado em DEV-A pela regra pré-registrada (#477), com BA cross-fitted de **74,68%** (média macro por dataset); ECE 0,0054; AUROC 0,8650. Camada LTT em DEV-B: **0/11 coortes certificadas pela regra registrada** (a sequência parou no primeiro limiar inelegível). Resultado DEV, não TEST nem ranking. Relatório: `reports/benchmarks/2026-11-07-dev-calibration-v2/`.
- **Linha de base RuleStance — LLM-AggreFact TEST (#471):** BA 49,2% (n=29.320).

### Benchmarks e calibração
- Harness de avaliação internacional, pins do dataset e proveniência (#462–#464).
- Piloto de throughput DEV e execução Phase 1b em shards com protocolos oficiais (FactCG, MiniCheck) e protocolo próprio (mDeBERTa), artefatos cifrados (AES-GCM) e aprovação do mantenedor (#465–#467).
- Calibração DEV e métricas (#472); Calibration V2 pré-registrada (#473): splits determinísticos e métricas probabilísticas (#474), Venn-Abers/IVAP com cross-fitting e Mondrian (#475), certificação seletiva Learn then Test (#476), seleção pré-registrada de um único modelo (#477) e integração ao agregador (#479).
- Workflow DEV completo protegido (#480) e caminho de re-agregação sem nova inferência (#481).

### API, segurança e auditoria
- Rate limiting limitado na autenticação e isolamento dos limitadores; documentação de 429 e confiança em proxy (#442, #445).
- Acesso serializado ao armazenamento SQLite de auditoria (#443).
- IDs de correlação gerados pelo servidor (#478).
- Teste do pipeline offline com sockets bloqueados (#446).

### RGC e verificação
- Emendas estatísticas DEC-021..DEC-023 (#468); validações de IDs de cluster e de anotação (#452, #454).
- Testes de invariância (paráfrase, retificação normativa, propriedades do Judge 2.0) e JSON Schema versionado do relatório Golden.

### Documentação
- Política de alegações públicas (#461), demo Docker/curl, roadmap de engenharia e auditoria E1.

### Limites
- Nenhum resultado de benchmark em português; RGC permanece não congelado.
- Nenhuma certificação estatística obtida; o projeto não é apresentado como certificado.

## [0.6.0] — 2026-10-23

### Mudanças incompatíveis previstas para a versão global 0.6.0

- **Autenticação por API key obrigatória por padrão:** a aplicação passa a iniciar em modo `api_key` por padrão e falha fechada quando o material de chave exigido está ausente ou malformado. Clientes e implantações devem configurar o material de autenticação e enviar `Authorization: Bearer <chave>` ou `X-API-Key: <chave>`. `/health` permanece público. Definir `ATTRACTOR_AUTH_MODE=off` é uma exceção explícita para desenvolvimento local isolado, não um padrão de implantação. Esta mudança é da versão global do produto; não altera a identificação independente do executor `rgc-eval/0.7.0`.

### Evaluation tooling
- **2026-10-23 — executor RGC `rgc-eval/0.7.0` (contrato de entrada: PR #398; alinhamento da versão: PR #399):** a validação dos rótulos-ouro JSONL agora rejeita linha em branco, JSON inválido, campos extras ou ausentes, `case_id` vazio ou não textual, veredito não textual/fora do vocabulário e IDs duplicados; não há coerção silenciosa de tipos. Entradas que antes eram aceitas por coerção ou tolerância a linhas vazias podem agora ser rejeitadas. A versão do executor foi incrementada para refletir a mudança material do contrato.
- **2026-10-23 — validação estrita de documentos-fonte (`load_documents`, PR #399; executor RGC `rgc-eval/0.7.0`):** `DOCUMENTS.jsonl` agora rejeita linha em branco, JSON inválido, objeto/campos obrigatórios ausentes e campos obrigatórios vazios ou de tipo incorreto. `source_id` duplicado também é rejeitado, como já ocorria antes desta alteração; essa regra não é uma mudança de comportamento. Quando presente, `text_sha256` deve conter exatamente 64 caracteres hexadecimais minúsculos e corresponder ao SHA-256 do texto UTF-8; formato inválido ou divergência interrompe a leitura. `text_sha256` continua opcional e campos adicionais não são rejeitados por esta validação. Entradas antes toleradas apesar de linhas vazias ou dados obrigatórios malformados podem agora ser rejeitadas; corrija os documentos-fonte, sem contornar o validador.
- **2026-10-22 — extração e payload NLI (PRs #391 e #393):** quando ausente, o offset final da evidência passa a ser `start_offset + len(content)`; o payload do adaptador NLI é validado em modo estrito. Confiança ausente permanece `0.0`, isto é, “sem nota”/valor padrão não pontuado — não é um veredito nem autoriza o Judge.
- **Limite científico:** nenhum caso RGC real foi avaliado e nenhuma métrica de benchmark foi produzida; o protocolo RGC permanece [PROPOSTO], não congelado.
- **2026-10-21 — executor RGC `rgc-eval/0.6.0`:** incrementa a versão do executor após a inclusão dos gates de congelamento do protocolo, integridade do runner, proveniência das fontes e aprovação humana das anotações (PRs #378–#382). A versão e o hash do código continuam sendo vinculados separadamente pelo manifesto de congelamento. Somente testes e simulações sintéticas foram executados; nenhum caso real RGC foi avaliado e nenhuma métrica de benchmark foi produzida.
- **2026-10-21 — executor RGC `rgc-eval/0.5.0`:** incrementa `RUNNER_VERSION` porque `--partition` é obrigatório e o relatório passa a identificar o intervalo primário por cluster de artigo (DEC-019/Emenda 9), com bootstrap por caso como sensibilidade. O relatório sintético testa explicitamente `runner_version`; não houve execução sobre casos RGC nem produção de métricas RGC.

### Compatibility notes
- **2026-10-21 — r1-a JSON `null` request body (controlled reproduction):** PR #274 restored the `/v1/verify` response to the frozen contract in `tests/fixtures/r1-a-error-baseline.json` (captured from `c7e3868f3f6f34ce153d9ec6605645fad8681e2e`); `null_body` expects HTTP 422 with type `missing`, and the fixture was not modified. The isolated script `scripts/repro_null_body_contract.py` ran with Python 3.11 across FastAPI `0.115.0`, `0.117.0`, `0.119.0`, `0.121.0`, `0.123.0`, `0.125.0`, `0.127.0`, `0.128.2`, each paired with Pydantic `2.10.0` and `2.13.5` and `httpx==0.27.2` (16 combinations; matrix in the workflow introduced by this PR). In every combination, both synthetic route styles returned HTTP 422 `missing` at `loc=["body"]`; direct `model_validate(None, from_attributes=True)` returned `model_attributes_type` in both tested Pydantic versions. No FastAPI/Pydantic threshold was identified in the tested range. The evidence does not justify a dependency bound in `pyproject.toml`. Exact per-job commands: `python -m pip install "fastapi==${{ matrix.fastapi }}" "pydantic==${{ matrix.pydantic }}" "httpx==0.27.2"` then `python scripts/repro_null_body_contract.py`. This note changes no API behavior or frozen fixture.
- **Nota corretiva (2026-10-21) — matriz inicial incompleta:** a conclusão anterior de que nenhum limiar FastAPI/Pydantic havia sido identificado se aplicava apenas às 16 combinações antigas (FastAPI até `0.128.2`, Pydantic `2.10.0`/`2.13.5`, `httpx==0.27.2`) e não cobria as versões atuais permitidas por `pyproject.toml`. Ela fica superada pela bissecção controlada ampliada desta PR, que testa FastAPI `0.128.2`–`0.157.0` (incluindo a série `0.156.x`) com Pydantic `2.14.1`, e Pydantic `2.10.0`, `2.13.5`, `2.14.0`, `2.14.1` com FastAPI `0.157.0`; todos os jobs executam o script isolado sem importar a aplicação nem tocar na fixture. O caminho sintético `v0.5.0-style` replica o tratamento explícito de `payload is None` na API atual e falha o job se não preservar HTTP 422 `missing`. A nota de resultado definitivo será registrada após os jobs concluírem.

**Nota (2026-10-21):** a previsão acima foi cumprida; o resultado final está registrado no item seguinte.
- **Resultado final da bissecção (2026-10-21):** a primeira versão publicada/testada que altera o tipo de erro no estilo de rota tipado v0.4.0 é FastAPI `0.151.0`: `0.150.0` retorna HTTP 422 `missing`, enquanto `0.151.0` e as versões testadas até `0.157.0` retornam HTTP 422 `model_attributes_type`. As versões `0.150.1`–`0.150.8` não existem no índice de pacotes (o `pip install` falhou com `No matching distribution found`), portanto foram removidas da matriz; a fronteira entre versões publicadas testadas é `0.150.0` → `0.151.0`. O estilo v0.5.0, com guarda explícita para `payload is None`, retorna HTTP 422 `missing` em todas as versões testadas, refletindo o tratamento explícito da API atual. Com FastAPI `0.157.0`, Pydantic `2.10.0`, `2.13.5`, `2.14.0` e `2.14.1` mantém esse mesmo contraste: o estilo tipado retorna `model_attributes_type`, e o estilo v0.5.0 retorna `missing`; a chamada direta `model_validate(None, from_attributes=True)` retorna `model_attributes_type`. Os comandos por job foram `python -m pip install "fastapi==${{ matrix.fastapi }}" "pydantic==2.14.1" "httpx==0.28.1"` (varredura FastAPI) ou `python -m pip install "fastapi==0.157.0" "pydantic==${{ matrix.pydantic }}" "httpx==0.28.1"` (varredura Pydantic), seguidos de `python scripts/repro_null_body_contract.py`. A reprodução não importa a aplicação nem toca na fixture. Como a API atual trata JSON `null` explicitamente e o contrato congelado continua passando, não há base para impor limite adicional no `pyproject.toml`.


### Added
- API-key authentication (`ATTRACTOR_AUTH_MODE=off|api_key`): `Authorization: Bearer` or `X-API-Key`, keyed HMAC-SHA-256 digests compared in constant time, mandatory 32-byte pepper, fail-closed configuration, `/health` stays public (initial implementation PR #219; secure-by-default correction in this PR). The application now defaults to `api_key` and refuses to start when required key material is missing or malformed. `off` must be selected explicitly for isolated local development only. The OpenAPI contract is unchanged.
- `X-Request-ID` propagation and one privacy-safe JSON access record per request; bodies, claims, excerpts, query strings and credentials are never logged (PR #221).
- RGC benchmark preparation (no benchmark result exists): DEC-002 source policy (#176), byte-exact capture of Resolution Anatel 765/2023 and its two rectifications with SHA-256 (#177), deterministic derived text (#178), proposed runner `rgc-eval` with Judge decision-state counts and annotated atoms for compound claims (#179, #195, #203), protocol Amendments 2–4 (#193, #205, #227), discarded exploratory pilot report (#209) and blank second-pilot worksheet (#229). The protocol is not frozen.
- `make reproduce` re-runs the CI evidence with one command (PR #213); fixed Schemathesis seed with saved reports (PR #212); `py.typed` and strict mypy gate for the RGC runner (PR #215).
- Proposed ADR-010, verifiable audit log (PR #220). Not implemented; no audit field exists in the API.

### Changed
- Docker runtime hardened: non-root user, image `HEALTHCHECK` on `/health`, host port bound to `127.0.0.1`, Compose defaults to `api_key` mode (PR #222); the container smoke test now exercises authenticated and unauthenticated calls (PR #226).
- Repository formatted with `ruff format` (AST-identical) and formatting enforced in CI (PR #216).
- Six experimental modules covered by minimal tests and labelled out of verified scope (PR #214).

### Fixed
- Structured privacy-safe JSON access records now reach Uvicorn output; the server's default access logger is disabled in the Docker and `make run` commands to avoid duplicate records and query-string leakage.
- Enforce fail-closed startup with Uvicorn's explicit `--lifespan on`: Docker, `make run`, API startup examples and contract-test workflows now force lifespan startup; real-server regression tests cover missing authentication configuration.
- `pip install`ed packages can load the Judge rules: a byte-identical copy of `rules/judge-2.0.0.json` ships as package data; `rules_sha256` unchanged (PR #224).
- r2-a evidence with `canonical_url` is adjudicated instead of returning `SCHEMA_VIOLATION` (issue #182, PR #192).
- Duplicate trace IDs are rejected by the audit trail; integrity limits documented (PR #217).
- Configurable HTTP request-body size limit enforced (PR #218) and verified against a real Uvicorn server for oversized bodies with Content-Length and chunked bodies without Content-Length (PR #223).


### Governança
- Descrições de pull requests padronizadas sem rodapés de ferramentas em 17/10/2026. O conteúdo técnico e o histórico de commits foram preservados; o histórico de edição das descrições permanece disponível no GitHub.
- Revisões produzidas por ferramenta automatizada passam a ser identificadas como tal; pareceres anteriores foram reidentificados. A revisão humana independente das PRs desde a v0.5.0 continua pendente.


### RGC methodology and tooling (2026-10-21)
- DEC-017 through DEC-020 were explicitly approved and recorded in dated amendments. The RGC protocol remains [PROPOSTO] and unfrozen.
- The RGC executor now separates the hidden confirmatory partition from public descriptive development data, and supports article-cluster bootstrap as the primary confidence interval with case bootstrap as sensitivity. No RGC cases were created or evaluated.
- Added a deterministic inter-annotator agreement calculator for unweighted Cohen's kappa, with a point-estimate gate of 0.6, a case-bootstrap 95% interval, confusion matrix, class marginals and auditable RULE_GAP exclusions. It has only been tested with synthetic data; no human annotation files were processed.
- A controlled FastAPI/Pydantic matrix did not identify a dependency-version threshold for the frozen JSON-null body contract; no dependency bound was added and the fixture remains unchanged.
- Expanded test coverage for plugin registry and provider error paths, extended strict mypy to both RGC evaluation modules, and removed remaining Bandit comment-parser warnings. The security CI reported no known dependency vulnerabilities.
- Added technical manual chapters for operations, security, reproducibility, evaluation, audit and governance. Documentation and CI evidence do not constitute certification, independent review or production readiness.
- Human pilot annotation, second independent annotation, F-01 independent review and the decision to freeze the protocol remain pending.

## [0.5.0] — 2026-10-13

### Added
- Judge 2.0.0: versioned rule contract and deterministic decision gates G1, G2 and E1–E3 (item 2.2).
- Atomic and composite rules (item 2.3; PRs #154 and #159).
- Canonical output and `verify_output` (item 2.4; PR #160).
- Additive `r2-a` contract on `POST /v1/verify`, preserving `r1-a` byte-identically (item 2.5; PR #161).
- Derived Golden r2 fixtures (item 2.6; PR #165).
- Canonical explanations and rule-level traceability (item 2.7; PR #167).

### Changed
- RFC 8785 canonicalization for `input_sha256` and `output_sha256` (PR #164).
- API Contract Guard with oasdiff, Schemathesis and an OpenAPI snapshot (PR #162).
- Complete response contract and Schemathesis `--checks all` (PR #163).
- Phase 2 — Judge 2.0 items 2.1–2.7 are prepared as the v0.5.0 release scope; API details are in `docs/api/CHANGELOG-API.md`.
- Brand banner update (PR #158) and post-v0.4.0 project metadata/DOI update (PR #156).

### Fixed
- Restored legacy `max_agents` coercion on `POST /v1/opensearch` for compatibility (PR #169).

### Deprecated
- Removal of `ResponseStatus`, the `verification` and `confidence` fields, and the `r1-a` path with 1.x rules is postponed to v0.6.0. Nothing is removed in v0.5.0.

## [0.4.0] — 2026-10-11

### CI reproducibility

- Pin all GitHub Actions workflow runners to `ubuntu-24.04` instead of the moving `ubuntu-latest` alias. Any future operating-system change requires a dedicated pull request and verification of the three evaluation `semantic_sha256` values (Golden v0, Golden v0.1 and smoke-v0); frozen artifacts and expected digests must remain unchanged.

### Verification

### Fixed

- Secret-leak checks now inspect real Pydantic response models, dataclasses, `bytes`, and `bytearray`; empty secrets are rejected. The helper detects leakage of an exact known secret and is not a generic credential detector (PR #147).
- `/v1/verify` now returns structured HTTP 422 responses only for the five classified invalid Judge input conditions: duplicate evidence IDs, dangling references, duplicate stances, duplicate claim IDs, and stances referencing nonexistent claims. Unexpected `ValueError` exceptions are not translated into client errors. The r1-a baseline fixture records the three previously observed 500 cases as structured 422 invalid requests; regression tests cover all five categories and a 250-example Hypothesis property check.

### Changed

- OpenAPI schema of the `/v1/verify` `status` field now references `Verdict` and `ResponsePolicy` via `anyOf`; accepted wire values are unchanged.

- (F1.3) Split transport-level abstention into `ResponsePolicy`; `VerificationResponse.status` now distinguishes `Verdict` from abstention policy, and `verdict` is typed as `Verdict | None`. The deprecated `ResponseStatus` compatibility enum remains available until v0.5.0; production contracts use `Verdict | ResponsePolicy`. The `/v1/verify` r1-a wire values are unchanged.

- **Removed (PR 1.3 / #129):** `VerificationStatus` (`src/ayorai_attractor/models.py`) and `EvidenceStore.status()` (`src/ayorai_attractor/evidence/core.py`) were removed. This is a breaking change for consumers importing `VerificationStatus`; migrate to the formal deterministic verdict contract at `/v1/verify` rather than deriving factual status from the evidence store. To reproduce the historical legacy baseline, check out the `baseline-legacy-v0` tag; do not regenerate it with current code.

- Search and audit responses no longer claim a factual verdict: `verification` is deprecated and
  returned as `null`, `verdict_authority` is `not_adjudicated`, and `/v1/verify` is the canonical
  formal-verification endpoint. Operational failures are reported separately in `operation_status`.
  The deprecated `verification` and `confidence` response fields are scheduled for removal in v0.5.0.
- SQLite audit storage uses a versioned schema via `PRAGMA user_version` and idempotent migration from existing databases. The migration preserves `legacy_verification` and does not rewrite historical digests. Replay records distinguish `r2-v1` (legacy verification values) and `r2-v2` (`not_adjudicated`); audit lookup exposes `replay_integrity` as `valid` or `invalid` so tampered records can be identified.

- Rule stance (detector version 6): Portuguese number words, legal duplicates `40 (quarenta)`, fractions and multipliers, duration conversion (1 ano = 12 meses), `vezes`/`dias-multa`, set semantics per fact, comparative bounds not read as negation, competing named actors block support. New module `verification/pt_normalize.py`.

- Rule stance (detector version 5): negation is now language dependent; Portuguese contractions (`no`, `na`, `nos`, `nas`) and `sem` are no longer read as negation, and `jamais`, `nem`, `nenhum(a)`, `ninguém` are.
- Rule stance: dates are recognised in Portuguese written form (`10 de março de 2026`, `1º de abril de 2026`), slash form (`10/03/2026`, day/month in Portuguese and month/day in English) and month form (`março de 2026`), compared only at the asserted granularity.
- Rule stance: opposite directional predicates on the same proposition (`subiu`/`caiu`, `aumentou`/`diminuiu`, `aprovou`/`rejeitou`, `rose`/`fell`) are classified as CONTRADICTS even when the numbers coincide.
- These fixes come from code review and new adversarial tests; no Golden case, threshold or frozen artifact was used or changed, and no new evaluation was run.

### Evaluation

- PT-CP-Audit: realistic audit simulation on the real Brazilian Penal Code (152 cases, dev/test by provision). Rule stance v5 → v6 on the held-out test (hand-written cases): false-support rate 25.9% → 14.8%, accuracy 65.0% → 72.5%, McNemar p ≈ 0.45 (directional). See `evals/pt-cp-audit/RESULTS.md`.

- F1.2 (pre-registered in `docs/eval/PREREGISTRATION-F1.2.md`, measured once): rule path C v4 → v5 left balanced accuracy unchanged on Golden v0 (42.73%) and v0.1 (48.18%), McNemar p = 1.0, with no regression. Four wrong `REFUTED` verdicts became wrong `UNVERIFIED`. Current path C accuracy on Golden v0 is 23.33% (the 26.67% in F1 was measured on older rule code). See `docs/eval/F1.2-RESULTS.md`.

### Governance

- Added authorship, trademark, DCO, licensing and release-provenance documentation.

### Security

- Added `docs/THREAT-MODEL.md` with scope, assets, threats, current defenses and known gaps.
- `ReplayStore.get` now accepts only 64-character lowercase hex digests (blocking path traversal) and rejects replay files whose internal digest differs from the requested digest.
- All GitHub Actions are pinned to full commit SHAs with version comments.
- Frozen evaluation sets and F1 thresholds are now enforced by SHA-256 tests.
- Added a guard against committing hidden Golden v1 files.
- Added a training-data license manifest gate (`scripts/check_training_manifest.py`).
- Evidence excerpts are now located in the original source; evidence not found verbatim is dropped and recorded in the audit trail (GAP B).

## [0.3.0] - 2026-10-04

### Verification

- NLI is loaded lazily under ADR-005, keeping the optional model stack out of the base import path.
- FACT was rewritten with adversarial tests covering numeric, entity, date, negation, comparison and provenance-sensitive cases.
- Provenance handling was corrected across evidence and stance paths.
- Golden v0.1 was frozen with a pre-registration and explicit development-set disclosure.
- E1 was measured on Golden v0.1 against the 43.33% majority baseline.
- E2 and E3 negative findings are documented; E3 remains a manual/audit-only negative evaluation rather than a promotion result.
- ADR-006, ADR-007 and ADR-008 record the subsequent evaluation, Portuguese span-detection and commercial NLI design decisions.
- E3 manual reconciliation and disclosure were recorded without changing the historical measurement.
- `actionlint 1.7.12` is pinned by direct archive SHA-256 verification.
- `judge-smoke.jsonl` is the public deterministic Judge smoke fixture; the name Golden v1 remains reserved for the future hidden Portuguese evaluation set.

### E1 measurement

| Path / reference | Golden v0 | Golden v0.1 |
|---|---:|---:|
| A | **40.00%** | **76.67%** |
| B | **43.33%** | **66.67%** |
| C | **26.67%** | **33.33%** |
| Majority baseline | **43.33%** | **43.33%** |

Golden v0.1's previously reported one-sided exact binomial comparisons versus the 43.33% baseline are A p=0.0002 and B p=0.0085. These values are historical measurements, not a new evaluation.

**Disclosure:** Golden v0.1 was rewritten after the author had seen per-case Path C results, as disclosed in `docs/eval/PREREGISTRATION-GOLDEN-v0.1.md`. Both versions are development sets (n=30); the corpus has 52 synthetic documents, all tagged `en-US`. On v0, the 95% confidence intervals for A and B include the 43.33% baseline. Report both versions and do not interpret v0.1 alone as confirmatory evidence.

### Mandatory limitations

- **A is EVAL_ONLY. B is the candidate commercial path.**
- **Golden v0 and v0.1 are development/evaluation-development sets**, not evidence of production generalization.
- The current corpus contains **English documents with Portuguese claims**. It is therefore not a Portuguese-document generalization benchmark.
- Generalization is reserved for the **hidden Golden v1**, which must contain genuinely Portuguese documents and remain untouched during development.

## [0.2.0] - 2026-10-03

### Verification

- F0 stabilization release candidate: deterministic claim-as-input verification boundary, provenance-preserving evidence, and auditable Golden evaluation.
- File-wide Ruff suppression removed from the verification and evaluation paths.
- ADR-004 records the claim-as-input contract.
- F0 stabilization: fixed numeric cross-evidence comparison, duplicate verification exports, and stale Golden abstention assertions; CI evidence pending on the updated P0 branch.
- Versioned pre-fix Golden reproduction records the 9/30 claim-pipeline result.
- Claim verification accepts caller-supplied claims separately from evidence.
- Claim extraction is response-only and cannot read evidence.
- ADR-003 adds NEUTRAL stance semantics.
- Numeric contradiction detection aligns unit and attribute context.
- Negation detection uses token boundaries.
- Production parsing/mapping failures abstain with a recorded reason.
- LLM claim and stance payloads use strict Pydantic schemas.
- P0.c Golden runner now verifies expected_claims text without consuming verdict labels and reports statistical comparison against the legacy runner.

### Engineering

- Deterministic R1 verification contracts stabilized.
- Numeric/date locale handling hardened.
- Explicit abstention response contracts.
- Full Golden v0 regression remains a diagnostic/development artifact.

## [0.1.0] - 2026-09-30

### Added

- Phase 0 baseline and reproducibility artifacts;
- FastAPI API and CLI;
- provider contracts and deterministic mock provider;
- evidence store and evidence graph;
- deterministic verification foundation;
- security and community health files.

[0.3.0]: https://github.com/Ayorinha/ayorai-opensearch/releases/tag/v0.3.0
[0.2.0]: https://github.com/Ayorinha/ayorai-opensearch/releases/tag/v0.2.0
[0.1.0]: https://github.com/Ayorinha/ayorai-opensearch/releases/tag/v0.1.0
