> **Nota de consolidação:** E1-02 e E1-04 foram tratados em #442, #443 e #444/#445.

# AYORAI ATTRACTOR — Revisão estática E1: API, identidade e confiabilidade

- **Data:** 2026-11-06
- **Baseline:** `main` em `0b2d92f4a55cfe3090d2affba2d86c17221ff6ed`
- **Branch:** `audit/e1-api-reliability-boundaries`
- **Tipo:** revisão estática de código e testes existentes
- **Não é:** pentest, teste de carga, auditoria independente, prova de exploração ou validação de produção.

## 1. Escopo examinado

Foram lidos os arquivos versionados na baseline:

- `src/ayorai_attractor/api/app.py`
- `src/ayorai_attractor/api/auth.py`
- `src/ayorai_attractor/orchestrator.py`
- `src/ayorai_attractor/tenant.py`
- `src/ayorai_attractor/models.py`
- `src/ayorai_attractor/audit_store.py`
- `tests/test_api.py`
- `tests/test_api_auth.py`
- `tests/test_audit_store.py`
- `docs/security/API-AUTH.md`
- `pyproject.toml`

Nenhum teste foi executado nesta revisão; não foram alterados dados, casos RGC, Judge, Golden, manifests ou hashes.

## 2. Achados

### E1-01 — Contexto de tenant não está ligado à autenticação HTTP

**Fato observado:** `TenantContext` existe e `Attractor.run` aceita contexto opcional. Porém, as rotas `/v1/opensearch` e `/v1/audit` chamam `engine.run(request)` sem fornecer `tenant_context`. O middleware de API key valida a credencial, mas não associa a chave validada a uma identidade de tenant/subject nem a escopos.

**Risco:** a presença de uma classe de contexto multi-tenant não demonstra isolamento efetivo por tenant no caminho HTTP. Não há evidência, nesses pontos de entrada, de autorização por operação ou partição de dados por tenant.

**Classificação:** lacuna de segurança arquitetural confirmada no caminho de integração inspecionado; impacto real depende do modelo de implantação e de outros controles externos.

**Próximo passo:** definir identidade autenticada e mapeamento de chave para principal/tenant, autorização por escopo e propagação obrigatória do contexto até providers, jobs, audit store e logs. Não aceitar tenant informado livremente pelo cliente como identidade confiável.

### E1-02 — Persistência SQLite compartilhada entre chamadas concorrentes sem serialização explícita

**Fato observado:** `api/app.py` cria `audit_store = AuditTraceStore()` global na importação. O store abre uma única conexão SQLite com `check_same_thread=False`; os handlers síncronos de API podem ser executados concorrentemente pelo thread pool. O store não apresenta lock explícito em torno de operações compostas de leitura/escrita.

**Risco:** a configuração permite acesso à mesma conexão por múltiplas threads, mas o código inspecionado não documenta nem impõe serialização da sequência SQL/commit. Isso merece validação de concorrência e ciclo de vida antes de tratar o store como backend operacional multi-worker. O SQLite também é local ao processo/volume e não fornece compartilhamento transacional entre réplicas por si só.

**Classificação:** risco de concorrência e escalabilidade confirmado por inspeção; falha concorrente efetiva ainda não reproduzida.

**Próximo passo:** definir contrato de armazenamento (uma conexão por operação ou writer serializado), política de transação, timeout/busy handling e suporte explícito a uma ou múltiplas réplicas. Não trocar backend sem decisão arquitetural e migração.

### E1-03 — Autenticação por API key não fornece autorização granular

**Fato observado:** o middleware compara HMACs de uma lista de chaves e autoriza ou rejeita a requisição. Não há identidade/escopos diferenciados por chave no middleware examinado. A documentação reconhece que autenticação não substitui authorization scopes.

**Risco:** uma chave válida tem acesso indistinto às rotas protegidas expostas por esse middleware. Isso não prova exposição indevida em produção, mas não satisfaz por si só o princípio de menor privilégio por cliente/operação.

**Próximo passo:** especificar principal, escopos por rota, rotação/revogação individual e trilha de auditoria de concessão/revogação. Manter compatibilidade explícita de contrato.

### E1-04 — Limitação de taxa não existe no middleware de aplicação examinado

**Fato observado:** `APIKeyAuthMiddleware` implementa autenticação, e `RequestBodyLimitMiddleware` limita o corpo a 2 MiB por padrão. Não foi identificado rate limiter na cadeia de middleware lida. A documentação de autenticação também declara que autenticação não substitui rate limiting.

**Risco:** o limite de corpo reduz uma classe de abuso, mas não limita frequência, concorrência, custo por operação ou chamadas a provedores externos.

**Próximo passo:** threat model por endpoint e custo; decidir limites por principal/rota, armazenamento distribuído quando houver múltiplos workers/réplicas, resposta 429 e comportamento explícito na indisponibilidade do backend. Não fixar quotas sem dados operacionais.

### E1-05 — Bufferização integral do corpo HTTP

**Fato observado:** `RequestBodyLimitMiddleware` acumula o corpo completo em `bytearray` até o limite configurado, antes de repassá-lo à aplicação. O limite padrão é 2 MiB e é validado como positivo.

**Risco:** o limite é finito, mas memória consumida por requisições simultâneas cresce com o número de corpos bufferizados. O middleware não demonstra controle de concorrência ou orçamento global de memória.

**Próximo passo:** avaliar streaming/limite no proxy e limite de concorrência por rota; manter o limite individual e documentar orçamento de memória sob carga.

### E1-06 — Testes existentes não cobrem ainda os limites operacionais identificados

**Fato observado:** os testes atuais cobrem autenticação fail-closed, headers duplicados, rotação por lista, corpo acima do limite, persistência, migração e adulteração de campos do replay digest. Não encontrei nos arquivos de teste lidos uma demonstração de isolamento por tenant na API, escopos por chave, concorrência real do SQLite ou comportamento de rate limit distribuído.

**Classificação:** ausência de evidência nos testes examinados; não significa que não exista cobertura em qualquer outro lugar do repositório.

**Próximo passo:** mapear todos os testes e workflows antes de adicionar testes. Não criar fixtures que representem casos de benchmark. Para validar criptografia, priorizar vetores públicos existentes. Para concorrência e segurança operacional, usar testes de integração apropriados somente depois de aprovar a arquitetura.

## 3. Aspectos positivos confirmados

- API key é obrigatória por padrão e a configuração inválida impede inicialização.
- Chaves curtas são rejeitadas; HMAC-SHA-256 usa pepper separado e comparação constante.
- Cabeçalhos de credencial duplicados ou mecanismos simultâneos são rejeitados.
- `/health` é explicitamente público.
- O corpo HTTP tem limite individual configurável.
- O SQLite não armazena prompts brutos, trechos de evidência, credenciais ou saídas de modelo, conforme o próprio módulo.
- O contrato de veredito mantém o Judge como autoridade separada; `/v1/opensearch` e `/v1/audit` indicam `not_adjudicated`.

## 4. Ordem técnica recomendada

1. Definir modelo de identidade, tenant e escopos antes de alegar isolamento multi-tenant.
2. Decidir política de rate limiting e limites de concorrência por operação.
3. Especificar contrato de persistência e concorrência do audit store; manter SQLite limitado a topologia suportada.
4. Avaliar bufferização e orçamento de memória sob carga.
5. Só então implementar alterações pequenas em PRs separadas, com testes de integração, compatibilidade OpenAPI e CI no SHA final.

## 5. Decisões que não devem ser tomadas automaticamente

- Não escolher quotas de produção sem perfil de carga.
- Não aceitar tenant vindo de header/campo livre como identidade autenticada.
- Não declarar multi-tenancy segura apenas porque `TenantContext` existe.
- Não migrar SQLite para outro banco sem ADR, plano de migração, backup/restore e critérios de consistência.
- Não alterar contratos públicos ou o Judge por conveniência.
- Não executar benchmark nem tocar nos 11 casos do Piloto 02.

## 6. Conclusão

A revisão estática E1 identificou três lacunas prioritárias no caminho HTTP: ausência de propagação de identidade/tenant, ausência de autorização granular por chave e ausência de rate limiting na aplicação examinada. Também identificou um risco de concorrência no uso da conexão SQLite global, que precisa ser reproduzido em teste de integração antes de ser classificado como defeito confirmado.

Esta revisão não altera código funcional e não declara prontidão de produção. O próximo passo é fechar as decisões de identidade/autorização e rate limiting antes de implementar controles, evitando criar uma solução distribuída incompatível com a topologia real.
