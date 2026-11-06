# AYORAI ATTRACTOR — Auditoria técnica E0

- Data da inspeção: 2026-11-06
- Repositório: Ayorinha/ayorai-opensearch
- Baseline: main em 0b2d92f4a55cfe3090d2affba2d86c17221ff6ed
- Branch de registro: docs/engineering-completion-roadmap
- Escopo: inventário estático de engenharia, fora da validação científica RGC.
- Método: leitura dos arquivos versionados e dos workflows. Não houve execução local da aplicação, acesso a dados operacionais, alteração de código funcional ou execução de avaliação.

## 1. Resumo executivo

O repositório já possui uma base de engenharia relevante. Não é correto descrevê-lo como um protótipo sem controles: há API FastAPI, autenticação por API key fail-closed, limite de corpo documentado no runtime, testes de contrato, CI em Python 3.11/3.12/3.13, Ruff, mypy, pytest, CodeQL, Bandit, pip-audit, revisão de dependências, Docker smoke, tracing e primitivas Merkle.

A principal lacuna de arquitetura identificada é a distância entre a biblioteca criptográfica Merkle/commitment existente e o serviço de log verificável especificado na ADR-010. O armazenamento SQLite de traces atual é explicitamente local e não resistente a adulteração direta por quem controla o banco. Isso não deve ser confundido com o futuro log de transparência.

A auditoria E0 é um inventário estático baseado no SHA acima. Ela não constitui pentest, auditoria independente, teste de carga, revisão jurídica LGPD nem validação científica.

## 2. Matriz de maturidade por evidência

| Área | Evidência observada na baseline | Classificação E0 | Lacuna ou próximo gate |
|---|---|---|---|
| CI e testes | Workflow CI com matriz Python 3.11, 3.12 e 3.13; pytest, Ruff, mypy e regressões específicas | Implementado, sujeito ao resultado por SHA | Consolidar relatório de cobertura e evidências por módulo sem afrouxar gates |
| Segurança de código | CodeQL com security-extended; Bandit; pip-audit | Implementado | Confirmar tratamento de findings e política de exceções |
| Dependências | Dependabot semanal para pip e GitHub Actions; Dependency Review em PR | Parcial | Dependency Review está configurado como continue-on-error e warn-only; decidir política de bloqueio |
| API e contratos | Testes de API/auth; workflow API Contract Guard e Schemathesis | Implementado | Auditar compatibilidade, autorização por operação e limites de abuso |
| Autenticação | API key por padrão; configuração fail-closed; HMAC-SHA-256 com pepper; comparação constante; /health público | Implementado para autenticação básica | Rotação/revogação operacional, escopos e rate limiting não demonstrados pela autenticação |
| Armazenamento de auditoria legado | SQLite com migração versionada, rejeição de trace_id duplicado e digest de replay | Implementado com limite declarado | O próprio módulo declara que edição direta do banco/admin não é detectada; não vender como log inviolável |
| Merkle | RFC 6962/9162: hashing, raízes, inclusão e consistência; vetores públicos independentes transparency-dev; testes de mutação | Núcleo criptográfico implementado | Revisar cobertura de limites, entradas malformadas e verificação cruzada automatizada contínua |
| Compromissos | RFC 8785, salt aleatório de 32 bytes, domínio versionado e vetores | Primitiva implementada | Definir schema versionado de evento, recibo, custódia/eliminação do salt e fluxo operacional |
| Log verificável ADR-010 | ADR especifica tiles C2SP, checkpoints assinados, testemunhas, armazenamento e integração futura | Não implementado como serviço completo | Decisões 5–7 em aberto; writer Python versus Tessera; persistência append-only, checkpoint, assinaturas, testemunhas e recuperação |
| Proveniência de release | Registro de hashes sdist/wheel v0.6.0 e workflow que gera artefatos e SHA256SUMS | Parcial | SLSA provenance, assinatura, SBOM anexada à distribuição e prova temporal ainda descritas como futuras |
| SBOM | Workflow Security gera CycloneDX JSON como artefato de CI | Parcialmente implementado | Evidenciar SBOM vinculada a cada distribuição/release e procedimento de verificação independente |
| Docker | Imagem Python 3.12 slim; usuário não-root; healthcheck; smoke autenticado e bind local no Compose | Implementado com endurecimento pendente de avaliação | Base image não fixada por digest no Dockerfile inspecionado; revisar atualização, CVEs, runtime read-only e capacidades |
| Observabilidade | Métricas determinísticas, TraceContext e adaptador OpenTelemetry opcional | Parcial/experimental | Confirmar integração real nos caminhos críticos, exportação, redaction, retenção e alertas |
| Política de ferramentas | SecurityPolicy experimental; requires_approval é registrado mas não imposto por authorize() | Experimental, fora do fluxo verificado | Não tratar como barreira de autorização até haver enforcement e integração auditada |
| Desempenho | Métricas de latência/custo existem como primitivas | Não demonstrado | Falta baseline de workload, perfilamento, orçamento de latência/custo e relatório reproduzível |
| Operação empresarial | Há Docker, autenticação, healthcheck e documentação | Parcial | Runbooks, SLOs, backup/restore testado, rotação de segredos e resposta a incidentes precisam de evidência |

## 3. Achados prioritários

### E0-01 — Separar o audit store atual do log de transparência

**Fato verificado:** src/ayorai_attractor/audit_store.py declara expressamente que o SQLite não é inviolável contra edição direta por administrador com acesso de escrita. O módulo persiste resumos e digest de replay, não um log público/externamente testemunhado.

**Risco:** linguagem de produto ou documentação pode sugerir uma garantia mais forte que a implementação.

**Ação:** manter o audit store legado claramente rotulado; implementar ADR-010 em fases próprias, sem substituir nem alterar silenciosamente o legado.

### E0-02 — Fechar ADR-010 por decisão arquitetural antes de serviço de produção

**Fato verificado:** a ADR-010 já define perfil criptográfico e requisitos, mas mantém abertas as decisões sobre writer Python versus Tessera, testemunhas independentes e timestamps ICP-Brasil.

**Ação:** produzir comparação técnica e POC de interoperabilidade com especificações C2SP e verificadores de referência. Usar vetores públicos padronizados; não criar casos RGC, rótulos ou resultados artificiais. Não escolher tecnologia apenas por popularidade.

### E0-03 — Segurança operacional além de autenticação

**Fato verificado:** API auth valida chaves de alta entropia e falha fechada. A documentação de API declara que autenticação não substitui rate limiting, escopos de autorização e procedimentos de rotação. A policy experimental não impõe requires_approval em authorize().

**Ação:** threat model de endpoints e operações; confirmar isolamento multi-tenant e autorização; definir rate limits, rotação/revogação, auditoria de acesso e gestão de segredos. Não apresentar a policy experimental como controle efetivo.

### E0-04 — SBOM e proveniência ainda não formam cadeia completa

**Fato verificado:** Security workflow gera SBOM CycloneDX como artefato de CI. RELEASE-PROVENANCE registra hashes de v0.6.0, mas lista SLSA provenance, assinatura, SBOM anexada à release e prova temporal como controles futuros.

**Ação:** ligar commit, workflow, artefatos, hashes, SBOM e atestado verificável. Não afirmar build reproduzível sem duas construções independentes comparadas.

### E0-05 — Docker e cadeia de dependências

**Fato verificado:** Dockerfile usa python:3.12-slim sem digest explícito; o smoke verifica usuário não-root e autenticação. Dependency Review tem continue-on-error e warn-only.

**Ação:** avaliar pinagem por digest e política de atualização de base; decidir formalmente se severidade alta deve bloquear PR; medir impacto de segurança e manutenção antes de mudar.

### E0-06 — Observabilidade ainda não prova operação pronta

**Fato verificado:** existem métricas e adaptador OpenTelemetry, mas a documentação classifica o adaptador como experimental e prevê integração/exportação futura.

**Ação:** mapear pontos de instrumentação reais, garantir redaction e ausência de prompts/documentos/segredos, definir SLOs internos, alertas e runbooks.

## 4. Sequência recomendada após E0

1. **E1 — Confiabilidade e contratos:** revisar timeouts, cancelamento, concorrência, idempotência, recuperação e compatibilidade da API. Corrigir somente defeitos reproduzíveis.
2. **E2 — Segurança operacional:** threat model, autorização, tenancy, rate limiting, rotação/revogação, dependências, imagem e resposta a incidentes.
3. **E3 — ADR-010:** resolver decisões abertas; especificar schema e fluxo; construir serviço append-only com checkpoints e verificação independente.
4. **E4 — Supply chain:** SBOM por artefato, proveniência SLSA, assinatura e verificação de terceiros.
5. **E5 — Eficiência:** estabelecer baseline operacional antes de otimizar; medir latência, throughput, memória, CPU e custo por execução.
6. **E6 — Operação:** traces, métricas, logs minimizados, SLOs, alertas, backup/restore e runbooks.
7. **E7 — Prontidão:** documentação, checklist e evidências da versão.

Cada etapa deve ser uma PR isolada, sem sobrepor PRs abertas. Não iniciar uma mudança antes de verificar conflitos e contratos protegidos.

## 5. Restrições de dados e validação

- Nenhum caso RGC foi criado, alterado, rotulado ou executado nesta auditoria.
- Os 11 casos do Piloto 02 permanecem fora do escopo.
- Não usar dados fabricados para simular evidência de negócio ou benchmark.
- Para primitivas criptográficas, priorizar os vetores públicos independentes já versionados e especificações normativas.
- Qualquer novo teste que exija fixture adicional deve ser justificado tecnicamente e não pode representar caso de avaliação.
- Judge, Golden, manifests, hashes congelados e protocolo RGC permanecem intocados.

## 6. Conclusão E0

**E0 — inventário estático: concluído para a baseline indicada.**  
**E1–E7: não concluídas.** Esta auditoria identifica onde atuar; não declara o software pronto nem atribui percentual de conclusão sem critérios quantitativos acordados.

O próximo trabalho de implementação recomendado é E1, começando por uma matriz de contratos, falhas e concorrência, seguida de correções pequenas e comprováveis. Em paralelo, preparar a decisão arquitetural da ADR-010 como documento técnico, sem antecipar implementação de serviço ou integração com a API.

## 7. Evidências consultadas

- src/ayorai_attractor/auditlog/merkle.py
- src/ayorai_attractor/auditlog/commitment.py
- src/ayorai_attractor/audit_store.py
- src/ayorai_attractor/api/auth.py
- src/ayorai_attractor/security/policy.py
- tests/auditlog/test_merkle_vectors.py
- tests/auditlog/test_commitment.py
- tests/test_audit_store.py
- tests/test_api_auth.py
- docs/adr/ADR-010-verifiable-audit-log.md
- docs/release/RELEASE-PROVENANCE.md
- docs/security/API-AUTH.md
- docs/security/RED-TEAM.md
- docs/architecture/R14-OBSERVABILITY.md
- docs/observability/METRICS.md
- .github/workflows/ci.yml
- .github/workflows/security.yml
- .github/workflows/codeql.yml
- .github/workflows/docker.yml
- .github/workflows/dependency-review.yml
- .github/dependabot.yml
- docker/Dockerfile
- pyproject.toml
