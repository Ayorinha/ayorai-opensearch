Estado: Atual · Referência: main @ 630b6d1 · Atualizado: 2026-11-16
Fontes de verdade: `docs/THREAT-MODEL.md`, `docs/security/API-AUTH.md`, `docs/security/RED-TEAM.md`, `src/ayorai_attractor/api/auth.py`, `src/ayorai_attractor/api/request_context.py`, `src/ayorai_attractor/api/app.py`, `src/ayorai_attractor/api/load_control.py`, `src/ayorai_attractor/audit_store.py`, `src/ayorai_attractor/verification/excerpt.py`, `src/ayorai_attractor/synthesis.py`, `src/ayorai_attractor/verification/judge2/gates.py`, `src/ayorai_attractor/redteam.py`, workflows `.github/workflows/security.yml`, `.github/workflows/codeql.yml`, `.github/workflows/dependency-review.yml`, `.github/workflows/docker.yml` and `.github/workflows/ci.yml`, testes `tests/test_api_auth.py`, `tests/test_api_request_context.py`, `tests/test_api_load_control.py`, `tests/test_audit_store.py`, `tests/test_audit_hmac.py`, `tests/test_verification_response_security.py` e testes de segurança do Judge.

# 06 — Segurança e limites de confiança

## Propósito

Este capítulo descreve controles de segurança que existem no código e nos workflows, bem como os limites explícitos do modelo de ameaças. O objetivo é tornar as fronteiras verificáveis; não é declarar o sistema certificado, imune a adulteração ou pronto para produção.

## Como funciona

### Autoridade do veredito e dados não confiáveis

O contrato de verificação separa o conteúdo que chega de usuários, documentos, citações e modelos da decisão factual final. Texto de documento com aparência de instrução continua sendo dado de evidência; não pode substituir o pedido estruturado nem alterar a autoridade do Judge determinístico. A produção de texto por um provider, a seleção de ferramentas e a coleta de evidências não constituem, por si só, um veredito.

O modelo de ameaças delimita o escopo: integridade de afirmações, evidências e proveniência, cálculo determinístico do veredito, integridade de replay, isolamento de conjuntos de avaliação, licenças e controles de CI/supply chain. Não promete provar a verdade de uma fonte externa, proteger a máquina/conta GitHub/rede/credenciais do operador, impedir comportamento malicioso de dependências comprometidas ou garantir generalização.

### Proveniência e citações

- O gate de síntese exige pelo menos um identificador de evidência conhecido para cada afirmação gerada; afirmações sem citação válida resultam em abstenção.
- O caminho de evidência pode localizar o trecho na fonte original, normalizando texto em NFC e preservando o mapeamento para offsets originais. Um trecho não encontrado é rejeitado em vez de ser aceito apenas porque um modelo o forneceu.
- Os contratos do Judge recebem entradas estruturadas. Stance, tradução, busca e texto gerado não substituem a autoridade do Judge determinístico.
- O corpus red-team cobre classes como prompt injection, envenenamento de evidência, manipulação de citação e payload com formato de segredo. O corpus é uma regressão determinística; não executa payloads, não chama ferramentas e não decide vereditos.

A existência de um identificador de citação ou de um hash não prova que a fonte externa seja verdadeira. O controle valida consistência com o material fornecido e a trilha registrada, dentro do escopo implementado.

### Autenticação HTTP

A autenticação por chave é habilitada por padrão. O middleware permite somente `/health` sem credenciais; as demais rotas HTTP são protegidas, incluindo documentação servida pela aplicação.

- O modo `api_key` exige um pepper de 32 bytes em hexadecimal e ao menos um digest HMAC-SHA-256 configurado.
- Chaves apresentadas com menos de 32 caracteres são rejeitadas.
- O cliente pode enviar `Authorization: Bearer` ou `X-API-Key`; cabeçalhos duplicados ou o uso simultâneo dos dois mecanismos são rejeitados para evitar ambiguidade.
- A comparação usa `hmac.compare_digest`. O pepper deve ser mantido separado da lista de digests, e a chave bruta não deve ser commitada ou escrita em logs.
- Configuração ausente ou malformada no modo `api_key` interrompe a inicialização. `ATTRACTOR_AUTH_MODE=off` só é permitido como escolha explícita em desenvolvimento local isolado.

Os procedimentos de geração e configuração de segredos estão em [API-AUTH.md](../security/API-AUTH.md). Exemplos versionados usam placeholders; nunca os substitua por segredos reais no repositório.

### Limite de entrada e logs

O middleware de corpo limita requisições HTTP a 2 MiB por padrão; `ATTRACTOR_MAX_BODY_BYTES` aceita somente inteiro positivo. O middleware de contexto gera `X-Request-ID` (um valor enviado pelo cliente é descartado), devolve esse cabeçalho na resposta e emite um registro estruturado com identificador, método, rota normalizada, status e duração. O registro de acesso não inclui corpo, afirmações, trechos de evidência, prompts ou credenciais.

Falhas de autenticação retornam HTTP 401 com mensagem genérica. O endpoint `/health` é público para probes, mas confirma somente que a rota respondeu; não demonstra a saúde de todas as dependências.

### Controle de concorrência e limitação de requisições

O middleware de admissão protege as rotas de trabalho intensivo (`/v1/check`, `/v1/fields`, `/v1/verify`, `/v1/audit` e `/v1/opensearch`). O limite padrão é de **2 requisições simultâneas por processo** (`ATTRACTOR_MAX_INFLIGHT_HEAVY`); excesso recebe HTTP 503 e `Retry-After: 1`. O limite pode ser configurado com inteiro positivo.

- `ATTRACTOR_INFLIGHT_SCOPE=process` é o padrão: cada worker tem seu próprio limite, portanto a capacidade agregada cresce com o número de workers.
- `ATTRACTOR_INFLIGHT_SCOPE=host` usa locks POSIX em arquivos para compartilhar slots entre processos do mesmo host. O diretório de locks precisa pertencer ao usuário do serviço e não pode ser gravável por grupo/outros. Essa opção não coordena hosts ou réplicas em máquinas diferentes; nesses cenários, imponha também limites no gateway/ingress.
- A autenticação ocorre antes da admissão e a admissão antes do buffer do corpo, evitando que chamadas sem credencial ocupem slots de processamento pesado.
- Há também limitação de taxa HTTP 429 por IP e por identidade HMAC da chave autenticada. O padrão documentado é 120 requisições por janela de 60 segundos e até 10.000 identidades IP em memória. É um limitador de janela fixa, em processo; perto da fronteira entre janelas, a rajada observada pode se aproximar de duas vezes o limite. A tabela IP usa LRU e pode admitir novamente uma identidade expulsa sob churn de alta cardinalidade. Não substitui proteção de borda contra abuso distribuído.

O limite de corpo HTTP é de 2 MiB por padrão (`ATTRACTOR_MAX_BODY_BYTES`). O middleware também conta o corpo efetivamente recebido, não confiando apenas em `Content-Length`; excesso retorna HTTP 413.

### Persistência, propriedade e integridade dos rastros

O `AuditTraceStore` usa SQLite local e grava um resumo operacional, não o conteúdo integral da interação. A versão atual do esquema é 3; novos rastros usam replay `r2-v3`, cujo digest cobre todos os campos persistidos do rastro, incluindo estado, contagens, proprietário, horário UTC e versão do software. A API associa o rastro ao principal autenticado; a consulta limita a leitura ao proprietário e responde como inexistente quando outro principal tenta acessá-lo.

- O armazenamento não persiste prompts crus, trechos de evidência, credenciais ou saídas do modelo.
- `ATTRACTOR_AUDIT_LEGACY_TRACES=hidden` é o padrão: rastros antigos sem proprietário ficam ocultos para clientes autenticados. `shared` permite leitura compartilhada desses rastros legados e deve ser uma decisão explícita de implantação.
- `ATTRACTOR_AUDIT_HMAC_KEYS` habilita MAC HMAC-SHA-256 fora do banco. Configure entradas `id:hex` separadas por vírgula; cada chave deve ter pelo menos 32 bytes e IDs únicos. A primeira chave é usada para novos registros; todas as chaves configuradas podem validar registros identificados. Ao ativar HMAC em uma base existente, o método `seal_unsealed()` sela apenas rastros r2-v3 cujo digest continua válido.
- Com chaves HMAC configuradas, um rastro r2-v3 sem MAC ou com identificador de chave desconhecido é considerado inválido. Sem `ATTRACTOR_AUDIT_HMAC_KEYS`, a verificação usa o digest de replay, sem autenticação criptográfica externa.

**Limite de confiança:** SQLite e replay digest não são armazenamento imutável nem prova contra administrador ou processo com acesso de escrita. HMAC mantido fora do banco dificulta que alguém com acesso somente ao arquivo SQLite forje rastros válidos, mas não impede exclusão, rollback de cópias antigas, indisponibilidade ou comprometimento da chave. Proteja o banco, o host e as chaves separadamente; aplique controle de acesso, retenção e cópias de segurança conforme a política de dados.

O método de backup usa a API de backup online do SQLite, recusa sobrescrever um destino existente e executa `PRAGMA integrity_check` na cópia. Após restauração, execute a verificação de replay de todos os rastros (`verify_all()`) e preserve todas as chaves HMAC ainda referenciadas pelos rastros retidos. Remover uma chave histórica antes da expiração dos rastros correspondentes faz esses rastros falharem na verificação. Integridade estrutural do SQLite e validade do replay são verificações distintas.

### Análise de segurança e supply chain

Os workflows atuais se complementam, mas não se substituem:

- `.github/workflows/security.yml` executa `pip-audit`, gera um SBOM CycloneDX como artefato e executa Bandit sobre `src/ayorai_attractor`.
- `.github/workflows/codeql.yml` executa análise CodeQL para Python com o conjunto `security-extended`.
- O workflow de revisão de dependências verifica mudanças de dependências em pull requests.
- `.github/workflows/docker.yml` constrói a imagem e a varre com Grype (binário oficial conferido por SHA-256, sem action de terceiros). O check falha se houver vulnerabilidade de severidade alta ou crítica **com correção disponível**; o relatório CycloneDX completo fica como artefato. Vulnerabilidades sem correção publicada aparecem no relatório, mas não bloqueiam. Como a imagem-base é fixada por digest, o build aplica as atualizações de segurança do Debian publicadas depois dela (`apt-get upgrade`); uma falha ao baixar ou validar o índice do Debian interrompe o build, em vez de gerar uma imagem desatualizada.
- A imagem base Python é fixada por digest e as dependências Python são instaladas de um lock com hashes e apenas wheels. Entretanto, o Dockerfile executa `apt-get update` e `apt-get upgrade` contra os repositórios Debian disponíveis no momento do build; portanto, a camada de pacotes do sistema pode variar entre builds feitos em datas diferentes. O digest da imagem base, por si só, não torna o build inteiro bit a bit reproduzível. O trade-off atual prioriza incorporar correções Debian recentes; reprodutibilidade estrita exigiria snapshot/versionamento dos repositórios e um processo de atualização de snapshot deliberado.
- No push para `main`, o job `build-distributions` publica um atestado de proveniência SLSA, assinado via Sigstore, para o sdist e o wheel, e o verifica no mesmo job. Qualquer pessoa pode conferir um artefato baixado com `gh attestation verify <arquivo> --repo Ayorinha/ayorai-opensearch`.
- Os checks de CI incluem testes, regressões do Judge/Golden e contratos. Uma simulação RGC ignorada por condição de workflow não deve ser descrita como aprovada.

Esses controles são verificações pontuais no SHA avaliado. Um resultado verde não demonstra ausência de vulnerabilidades desconhecidas nem valida o ambiente de implantação.

## Contratos e parâmetros

| Parâmetro/controle | Comportamento |
|---|---|
| `ATTRACTOR_AUTH_MODE` | `api_key` por padrão; `off` apenas por escolha explícita em desenvolvimento local isolado. |
| `ATTRACTOR_API_KEY_PEPPER` | Segredo de 32 bytes codificado como 64 caracteres hexadecimais. |
| `ATTRACTOR_API_KEYS_HMAC_SHA256` | Lista separada por vírgulas de digests HMAC-SHA-256 de 64 caracteres hexadecimais. |
| `ATTRACTOR_MAX_BODY_BYTES` | Limite de corpo HTTP inteiro positivo; padrão 2 MiB. |
| `ATTRACTOR_LOG_LEVEL` | `DEBUG`, `INFO`, `WARNING`, `ERROR` ou `CRITICAL`; padrão `INFO`. |
| `X-Request-ID` | Sempre gerado pelo servidor (32 caracteres hexadecimais); o valor enviado pelo cliente é descartado. |
| HTTP 401 / 413 / 422 | Falha de autenticação / corpo acima do limite / falha de validação, respectivamente. |
| HTTP 429 / 503 | Limite de taxa por IP/chave / limite de concorrência das rotas pesadas; ambos incluem `Retry-After`. |
| `ATTRACTOR_MAX_INFLIGHT_HEAVY` | Máximo de requisições pesadas simultâneas; padrão 2 por processo. |
| `ATTRACTOR_INFLIGHT_SCOPE` | `process` (padrão) ou `host` (locks POSIX compartilhados no mesmo host). |
| `ATTRACTOR_AUDIT_DB` | Caminho do arquivo SQLite de auditoria; padrão `.attractor/audit.sqlite3`. |
| `ATTRACTOR_AUDIT_HMAC_KEYS` | Chaves HMAC externas para integridade criptográfica dos rastros r2-v3; vazio/desconfigurado desabilita MAC. |
| `ATTRACTOR_AUDIT_LEGACY_TRACES` | `hidden` (padrão) ou `shared` para rastros legados sem proprietário. |
| `ATTRACTOR_RATE_LIMIT_REQUESTS` | Requisições por janela fixa; padrão 120. |
| `ATTRACTOR_RATE_LIMIT_WINDOW_SECONDS` | Duração da janela fixa em segundos; padrão 60. |
| `ATTRACTOR_RATE_LIMIT_MAX_CLIENTS` | Capacidade da tabela de identidades IP; padrão 10.000. |
| `ATTRACTOR_INFLIGHT_LOCK_DIR` | Diretório de locks POSIX quando `ATTRACTOR_INFLIGHT_SCOPE=host`; deve ser privado e pertencer ao usuário do serviço. |

## Limites conhecidos

- A autenticação por chave não implementa autorização por escopos, gestão completa do ciclo de vida de identidades, rotação automatizada de segredos ou resposta a incidentes. Há limitadores HTTP 429 por IP e por chave, mas são controles fixos e locais ao processo; não substituem proteção de borda nem coordenação distribuída.
- A proteção depende também de HTTPS quando a rede não é confiável, controles de rede, configuração segura do host, gestão de segredos e atualização de dependências.
- O corpus red-team contém expectativas determinísticas de tratamento; não é, isoladamente, uma prova end-to-end de que todo payload sensível jamais será persistido.
- O runtime não prova a veracidade de fontes externas, não substitui avaliação jurídica de licenças e não garante generalização além dos dados avaliados.
- Hashes, logs estruturados, CI e autenticação não constituem certificação, parceria institucional, garantia contra adulteração ou evidência de prontidão para produção.
- O conjunto Golden v1 oculto deve permanecer fora do desenvolvimento. Nenhum caso de piloto, desenvolvimento ou avaliação confirmatória RGC deve ser enviado a assistentes/modelos ou executado no ATTRACTOR sem os gates explícitos definidos pelo mantenedor.
- **Limite de isolamento do Golden v1:** o controle atual é parcialmente procedimental. `.gitignore` e `tests/test_golden_v1_isolation.py` impedem que arquivos ocultos sejam adicionados ao repositório, mas o repositório não fornece controle técnico de acesso que impeça um desenvolvedor ou job autorizado a ler o material de consultá-lo ou usá-lo no desenvolvimento. A lacuna está registrada no modelo de ameaças e exige controles operacionais de acesso/execução; não deve ser descrita como isolamento técnico completo.

## Evidências

- `docs/THREAT-MODEL.md`: escopo, ativos, ameaças, controles e não objetivos.
- `docs/security/API-AUTH.md` e `src/ayorai_attractor/api/auth.py`: configuração fail-closed e autenticação.
- `src/ayorai_attractor/verification/excerpt.py` e `src/ayorai_attractor/synthesis.py`: revalidação de trecho e gate de citação.
- `docs/security/RED-TEAM.md` e `src/ayorai_attractor/redteam.py`: corpus determinístico e escopo da regressão adversarial.
- `src/ayorai_attractor/api/request_context.py` e `src/ayorai_attractor/api/app.py`: correlação, logging e limite de corpo.
- `.github/workflows/security.yml`, `.github/workflows/codeql.yml` e `.github/workflows/dependency-review.yml`: controles de supply chain.
- `tests/test_api_auth.py`, `tests/test_api_request_context.py`, `tests/test_verification_response_security.py` e testes de verificação do Judge.

## Ver também

- [04 — API HTTP e contratos](04-api.md)
- [05 — Operação e execução](05-operacao.md)
- [Autenticação da API](../security/API-AUTH.md)
- [Modelo de ameaças](../THREAT-MODEL.md)
- [Regressão red-team](../security/RED-TEAM.md)
- [Docker](../DOCKER.md)
