Estado: Atual · Referência: main @ 85d6c2b + integração local · Atualizado: 2026-11-15
Fontes de verdade: `src/ayorai_attractor/api/app.py`, `src/ayorai_attractor/api/auth.py`, `src/ayorai_attractor/api/request_context.py`, `src/ayorai_attractor/api/logging_config.py`, `src/ayorai_attractor/models.py`, `src/ayorai_attractor/verification/api_models.py`, `docs/api/openapi.json`, `docs/security/API-AUTH.md`, testes `tests/test_api.py`, `tests/test_api_auth.py`, `tests/test_api_request_context.py`, `tests/test_api_uvicorn_body_limit.py`, `tests/test_verification_api.py` e `tests/test_openapi_snapshot.py`.

# 04 — API HTTP e contratos

## Propósito

Este capítulo descreve a interface HTTP implementada, os limites de entrada, a autenticação e a diferença entre pesquisa/auditoria operacional e verificação factual formal. Os contratos de referência são o código e o snapshot OpenAPI; exemplos não substituem validação contra esses artefatos.

## Como funciona

A aplicação é uma instância FastAPI. No início do ciclo de vida, valida a configuração de autenticação, de provider e do limite de concorrência (`ATTRACTOR_MAX_INFLIGHT_HEAVY`) e configura o logging; no encerramento, fecha o armazenamento de rastros de auditoria. O middleware de contexto de requisição gera um identificador de correlação (o valor de `X-Request-ID` enviado pelo cliente é descartado) e registra metadados da resposta. O limite de corpo é aplicado antes do parsing da aplicação, e a autenticação por chave é habilitada por padrão.

### Endpoints

| Método e rota | Entrada/saída | Papel e limite |
|---|---|---|
| `GET /health` | Objeto JSON com `status` e `service` | Endpoint público de saúde; não é um teste completo de dependências externas nem de desempenho. |
| `POST /v1/opensearch` | `SearchRequest` → `SearchResponse` | Executa o fluxo de pesquisa. A resposta declara `verification: null` e `verdict_authority: "not_adjudicated"`; não equivale a um veredito factual do Judge. |
| `POST /v1/audit` | `SearchRequest` → `AuditResponse` | Executa a pesquisa e apresenta achados e contagens de auditoria. Também declara que não houve adjudicação factual e indica `/v1/verify` como endpoint formal de verificação. |
| `GET /v1/audit/{trace_id}` | Identificador do rastro → `AuditTraceResponse` | Retorna metadados persistidos dos rastros criados por `POST /v1/audit`. Nenhuma outra rota persiste rastros: o `trace_id` de `/v1/opensearch` (também `tr_…`) e os de `/v1/check` (`chk_…`) e `/v1/fields` (`fld_…`) respondem 404 aqui. `chk_` e `fld_` são digests do conteúdo da requisição e do motor; o resultado se reproduz reenviando a mesma requisição. Responde 404 se o identificador não existir; a implementação declara que não expõe evidências brutas ou prompts nessa rota. O armazenamento é um arquivo SQLite (`ATTRACTOR_AUDIT_DB`, padrão `.attractor/audit.sqlite3`): num container sem volume para esse caminho, os rastros se perdem quando o container é recriado. |
| `POST /v1/verify` | Contrato `r1-a` ou `r2-a` → envelope correspondente | Encaminha a entrada ao contrato de compatibilidade legado `r1-a` ou ao contrato canônico do Judge 2.0.0 `r2-a`. A resposta OpenAPI documenta as duas formas por `oneOf`. |
| `POST /v1/check` | `CheckRequest` (`c1`) → `CheckResponse` | Verifica afirmações contra documentos enviados pelo cliente: seleção de trechos, detector por regras e Judge determinístico ADR-002. Não busca fontes externas e não persiste o resultado. Até 20 documentos (texto de até 200.000 caracteres, ou PDF com camada de texto em base64) e até 50 afirmações, ou uma `answer` de até 20.000 caracteres. O campo `url` do documento é apenas metadado: o servidor não o acessa. |
| `POST /v1/fields` | `FieldsRequest` (`f1`) → `FieldsResponse` | Confere até 100 campos tipados (`money`, `date`, `cpf_cnpj`, `number`, `text`) contra um documento enviado pelo cliente; o resultado por campo é `conforme`, `divergente`, `ambiguo`, `ausente` ou `invalido`. Não persiste o resultado. |

### Fluxo de verificação

- Se `schema_version` for omitido, `/v1/verify` usa o contrato `r1-a` para preservar compatibilidade.
- Se `schema_version` for `r2-a`, a entrada é validada como `Judge2VerificationRequest` e encaminhada à adjudicação canônica do Judge 2.0.0.
- O resultado deve ser interpretado conforme o envelope e o estado de decisão retornados. Ausência de veredito não significa refutação.
- Um corpo JSON `null` em `/v1/verify` produz HTTP 422 com tipo de erro `missing`, conforme o contrato congelado em `tests/fixtures/r1-a-error-baseline.json`. A fixture não deve ser editada para fazer um teste passar; alterações de contrato exigem processo explícito.
- `/v1/opensearch` e `/v1/audit` não adjudicam a veracidade de uma afirmação. A coleta de evidências e a resposta gerada não substituem uma chamada explícita a `/v1/verify`.

## Contratos e parâmetros

### Autenticação

A autenticação por chave de API é o modo padrão. O middleware isenta somente `/health`; as demais rotas HTTP, incluindo a documentação OpenAPI servida pela aplicação, passam pelo controle de autenticação.

- Configure `ATTRACTOR_AUTH_MODE=api_key`, `ATTRACTOR_API_KEY_PEPPER` e `ATTRACTOR_API_KEYS_HMAC_SHA256`.
- O pepper é um segredo de 32 bytes representado por 64 caracteres hexadecimais. A lista de digests contém valores HMAC-SHA-256 de 64 caracteres hexadecimais, separados por vírgula.
- A chave apresentada precisa ter pelo menos 32 caracteres. O cliente pode usar `Authorization: Bearer …` ou `X-API-Key`, mas não os dois ao mesmo tempo; cabeçalhos de credencial duplicados ou ambíguos são rejeitados.
- A aplicação compara o digest da chave apresentada com a lista configurada. A chave bruta não deve ser colocada no código, no repositório ou nos logs.
- `ATTRACTOR_AUTH_MODE=off` só deve ser usado explicitamente em desenvolvimento local isolado. A configuração inválida ou incompleta no modo `api_key` impede a inicialização, em vez de desabilitar a autenticação silenciosamente.

Os comandos de configuração e geração de credenciais ficam em [API-AUTH.md](../security/API-AUTH.md). Não copie segredos reais para exemplos, issues, pull requests ou documentação versionada.

### Limite de corpo e erros

- O limite padrão do corpo HTTP é 2 MiB (`2 * 1024 * 1024` bytes). `ATTRACTOR_MAX_BODY_BYTES` permite configurar outro limite inteiro positivo; valor inválido ou não positivo impede a criação do middleware.
- Corpo que não pode ser interpretado como JSON retorna HTTP 422 com `type` igual a `json_invalid`.
- HTTP 401 indica falha de autenticação e usa mensagem genérica.
- HTTP 413 indica que o corpo excedeu o limite configurado.
- HTTP 422 indica falha de validação do contrato ou entrada inválida para o endpoint.
- HTTP 404 em `GET /v1/audit/{trace_id}` indica que o rastro não existe **ou** não pertence à chave que fez a chamada; as duas situações têm resposta idêntica, para que o `trace_id` não sirva de oráculo de existência.

A aplicação documenta os envelopes de erro no OpenAPI. Clientes devem tratar códigos HTTP e corpo de resposta como parte do contrato, sem depender de mensagens internas de exceção.

### Rastros de auditoria: dono, integridade e versões

- Cada rastro gravado por `POST /v1/audit` registra o dono: um principal não secreto derivado da chave (`key:` seguido de 16 caracteres hexadecimais de um HMAC-SHA-256, sob o pepper e com rótulo de separação de domínio, do digest configurado da chave). Só a mesma chave lê o rastro. O principal não revela a chave nem o digest, e sem o pepper não pode ser ligado a uma entrada da lista de digests. Trocar o pepper muda todos os principais: rastros anteriores deixam de ser lidos pelas novas chaves. Com `ATTRACTOR_AUTH_MODE=off` não há dono.
- Rastros gravados antes do esquema 3 não têm dono. Por padrão (`ATTRACTOR_AUDIT_LEGACY_TRACES=hidden`) nenhuma chave os lê pela API; `shared` os torna legíveis por qualquer chave autenticada. Outro valor impede a inicialização.
- O esquema 3 registra também `recorded_at` (UTC, ISO 8601, largura fixa) e `software_version`. A migração a partir do esquema 2 é feita no próprio arquivo, ao abrir, e é idempotente.
- `replay_version` `r2-v3`: o digest SHA-256 cobre todos os campos persistidos, inclusive dono, data e versão. Rastros `r2-v2` continuam verificados pela regra anterior.
- Com `ATTRACTOR_AUDIT_HMAC_KEYS` configurada (`id:hex` com 32 bytes, separadas por vírgula; a primeira é a ativa), cada rastro novo recebe também um HMAC-SHA-256. Um MAC ausente, adulterado ou de chave desconhecida torna `replay_integrity` igual a `invalid`.
- O digest sem chave detecta corrupção e edição sem recálculo; o HMAC detecta quem escreve no banco sem a chave. Nenhum dos dois protege contra quem tem a chave HMAC ou controle do host: a trilha não é imutável.

### Identificador de requisição e logs

- Para cada requisição, o servidor sempre gera um identificador próprio (32 caracteres hexadecimais) e substitui qualquer `X-Request-ID` enviado pelo cliente, inclusive no escopo visto pelos handlers.
- A resposta inclui esse `X-Request-ID` gerado pelo servidor.
- O registro estruturado contém identificador, método, rota normalizada, status HTTP e duração em milissegundos. O middleware não adiciona payload, afirmações, trechos de evidência, prompts ou credenciais ao registro.
- `ATTRACTOR_LOG_LEVEL` aceita `DEBUG`, `INFO`, `WARNING`, `ERROR` ou `CRITICAL`; o padrão é `INFO`.

### Compatibilidade de entrada

O campo `max_agents` mantém coerção legada para strings numéricas, floats integrais e booleanos, embora a forma preferida seja inteiro JSON entre 1 e 100. `require_primary_source` também preserva as formas de compatibilidade documentadas no OpenAPI. A remoção dessas formas legadas não deve ser antecipada por uma alteração isolada neste capítulo; consulte [CHANGELOG-API.md](../api/CHANGELOG-API.md) e o snapshot [openapi.json](../api/openapi.json).

## Limites conhecidos

- `/health` confirma apenas que a rota respondeu; não demonstra que toda integração externa esteja disponível.
- Autenticação por chave não substitui HTTPS em redes não confiáveis, controles de rede, autorização por escopo, limitação de taxa, rotação operacional de segredos ou gestão de incidentes.
- `/v1/opensearch` e `/v1/audit` não devem ser apresentados como endpoints de veredito factual.
- A existência de OpenAPI, autenticação, rastros e testes não constitui certificação, validação institucional ou garantia de prontidão para produção.
- `info.version` do OpenAPI (`0.1.0`) é a versão do documento de contrato HTTP e não acompanha a versão do pacote (`0.8.0` em `pyproject.toml`). As mudanças de contrato são registradas no [CHANGELOG-API](../api/CHANGELOG-API.md).
- O contrato congelado `r1-a` deve permanecer compatível; qualquer mudança precisa ser acompanhada por testes de contrato e decisão de versão apropriada.

## Evidências

- `src/ayorai_attractor/api/app.py`: rotas, dispatch de `r1-a`/`r2-a`, limite de corpo e lifecycle.
- `src/ayorai_attractor/api/auth.py`: configuração fail-closed, digest HMAC-SHA-256 e exceção de `/health`.
- `src/ayorai_attractor/api/request_context.py` e `logging_config.py`: correlação e logging estruturado.
- `tests/test_api_auth.py`, `tests/test_api_uvicorn_body_limit.py`, `tests/test_api_request_context.py` e `tests/test_verification_api.py`: testes de autenticação, limite, correlação e contratos.
- `tests/test_openapi_snapshot.py`: verificação do snapshot OpenAPI.
- `src/ayorai_attractor/audit_store.py`, `tests/test_api_trace_ownership.py`, `tests/test_audit_hmac.py`, `tests/test_audit_trace_metadata.py` e `tests/test_audit_store_durability.py`: dono, política de legado, HMAC, metadados, backup e retenção dos rastros.

## Ver também

- [01 — Visão geral](01-visao-geral.md)
- [02 — Arquitetura](02-arquitetura.md)
- [03 — Judge determinístico](03-judge.md)
- [Autenticação da API](../security/API-AUTH.md)
- [Changelog da API](../api/CHANGELOG-API.md)
- [OpenAPI](../api/openapi.json)
