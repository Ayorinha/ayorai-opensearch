Estado: Atual · Referência: main @ 73bf91c (base desta PR) · Atualizado: 2026-11-16
Fontes de verdade: `Makefile`, `pyproject.toml`, `src/ayorai_attractor/cli/main.py`, `src/ayorai_attractor/evaluation/golden.py`, `docs/providers.md`, `docker-compose.yml`, `docker/Dockerfile`, `docs/DOCKER.md`, `docs/security/API-AUTH.md`, `src/ayorai_attractor/api/app.py`, `src/ayorai_attractor/api/auth.py`, `src/ayorai_attractor/api/logging_config.py`, `src/ayorai_attractor/api/load_control.py`, `src/ayorai_attractor/audit_store.py`, testes `tests/test_cli_contract.py`, `tests/test_cli_module.py`, `tests/test_reproduce_script.py` e testes operacionais/API correspondentes.

# 05 — Operação e execução

## Propósito

Este capítulo reúne os procedimentos operacionais existentes para instalar, iniciar e verificar a API em ambiente local. Os arquivos de configuração e os scripts citados abaixo são a fonte de verdade; este texto não cria um perfil de produção nem substitui uma avaliação de segurança, capacidade, disponibilidade ou recuperação.

A configuração padrão exige autenticação por chave de API. Uma configuração ausente ou inválida no modo `api_key` impede a inicialização; isso é comportamento fail-closed, não uma falha a contornar desabilitando a proteção.

## Como funciona

### Pré-requisitos

- Python compatível com `pyproject.toml` (Python 3.11 ou superior).
- Dependências instaladas no ambiente virtual ou ambiente de desenvolvimento isolado.
- Para execução em contêiner: Docker com suporte ao comando `docker compose`.
- Credenciais de API geradas para o ambiente e armazenadas fora do repositório, em mecanismo de segredos apropriado.

Não versione arquivos `.env`, chaves brutas, pepper, digests reais ou dados de requisições. Use apenas os placeholders dos exemplos versionados.

### Instalação e execução local

Na raiz do repositório, instale o projeto com as dependências de desenvolvimento:

```bash
python -m pip install -e ".[dev]"
```

O Makefile oferece os atalhos `make install`, `make test`, `make lint`, `make typecheck` e `make security`. Para iniciar a API no modo de desenvolvimento, depois de configurar a autenticação e as variáveis necessárias:

```bash
make run
```

O alvo `run` usa Uvicorn com recarga automática, ciclo de vida habilitado e sem o access logger padrão. Ele é destinado ao desenvolvimento, não a uma implantação de produção. Consulte [autenticação da API](../security/API-AUTH.md) para gerar e configurar os segredos sem os registrar no terminal ou no Git.

### CLI e avaliação Golden de desenvolvimento

O projeto publica dois entrypoints de CLI em `pyproject.toml`: `attractor` oferece os comandos `search` e `eval`; `opensearch` aponta diretamente para a função `search`. A pesquisa cria um `SearchRequest`, chama `Attractor.run` e imprime JSON estruturado. O modo padrão é `balanced`, e `max_agents` é 5, salvo opções explícitas.

Consulte a ajuda antes de executar:

```bash
attractor --help
attractor search --help
attractor eval --help
```

Exemplo de pesquisa com o provider local padrão:

```bash
attractor search "consulta de exemplo" --mode balanced --max-agents 5
```

Códigos de saída de `search` (e do comando `opensearch`, que executa o mesmo comando): **0** quando a operação foi concluída, inclusive com `verdict_authority: not_adjudicated`, que descreve o resultado e não é erro; **1** quando `operation_status` é `failed` (por exemplo, provider indisponível), com o JSON impresso mesmo assim; **2** para entrada inválida, com a mensagem em stderr e nada em stdout.

A API valida a configuração de provider na inicialização e não sobe, como já faz com a autenticação, se `ATTRACTOR_PROVIDER` não for suportado, se `openai-compatible` estiver sem `OPENAI_API_KEY` ou sem URL HTTPS, se só um de `ATTRACTOR_OPENSEARCH_ENDPOINT`/`ATTRACTOR_OPENSEARCH_INDEX` estiver definido, ou se um endpoint de busca não usar HTTPS.

O provider `mock` não exige rede nem credenciais e marca a saída como não independente. O adaptador OpenAI-compatível requer `ATTRACTOR_PROVIDER=openai-compatible` e `OPENAI_API_KEY`; `OPENAI_BASE_URL` e `ATTRACTOR_MODEL` são opcionais conforme `docs/providers.md`. Um provider de execução não é, por si só, fonte de evidência.

A CLI de avaliação aceita somente `golden-v0`, `golden-v0.1` e `smoke-v0`. Exemplo para uma suíte Golden de desenvolvimento:

```bash
attractor eval --suite golden-v0 --out reports/eval-golden-v0.json
```

O comando grava um relatório JSON e imprime nome da suíte, caminho, acurácia global e baseline majoritária. Registre SHA do commit, suíte, hashes das entradas, versão do Python, comando e provider, sem registrar segredos. Não altere Goldens congelados para obter um resultado desejado. Métricas de desenvolvimento não demonstram generalização em produção.

**Restrição RGC:** não execute a CLI nem outro caminho do ATTRACTOR sobre casos de piloto, partição pública de desenvolvimento ou avaliação confirmatória do RGC PT-BR. A avaliação Golden documentada aqui não autoriza execução RGC.

### Execução com Docker Compose

O procedimento detalhado está em [Docker deployment](../DOCKER.md). O fluxo resumido é:

1. Copie `.env.example` para `.env` localmente.
2. Configure `ATTRACTOR_AUTH_MODE=api_key`, o pepper de 32 bytes em hexadecimal e a lista de digests HMAC-SHA-256 válidos.
3. Construa e inicie o serviço:

   ```bash
   docker compose up --build -d
   docker compose ps
   ```

4. Confirme que o contêiner está ativo e que o processo não executa como root.
5. Verifique a rota pública de saúde e confirme que uma rota protegida rejeita uma chamada sem credenciais.

O Compose publica a porta do host em `127.0.0.1:8000`, não em todas as interfaces. Alterar esse vínculo amplia a exposição e exige uma avaliação deliberada dos controles de rede. O processo dentro do contêiner escuta em `0.0.0.0:8000` para permitir o encaminhamento da porta pelo Docker; isso não altera, por si só, o vínculo da porta no host.

### Verificações operacionais básicas

#### Saúde e autenticação

```bash
curl -i http://127.0.0.1:8000/health
curl -i http://127.0.0.1:8000/v1/audit
```

Com a autenticação habilitada, a primeira chamada deve responder sem credenciais; a segunda deve retornar HTTP 401 quando enviada sem chave. Para chamar uma rota protegida, use uma chave configurada no ambiente por `Authorization: Bearer` ou `X-API-Key`. Não coloque a chave na URL.

`/health` comprova apenas que o processo respondeu (liveness). Não confirma provedores, integrações, fontes externas nem dependências, e não mede desempenho ou capacidade.

`/ready` (readiness, sem chave) responde 200 só quando o banco da trilha de auditoria responde, e 503 sem detalhes no caso contrário; use-o para tirar uma réplica do tráfego. `/metrics` (com a chave da API) expõe métricas Prometheus por rota e status. Métricas, SLOs propostos, alertas e o roteiro de recuperação estão em [SLO-AND-ALERTS.md](../observability/SLO-AND-ALERTS.md).

#### Testes e verificações de qualidade

Os alvos disponíveis no Makefile são:

| Comando | Finalidade |
|---|---|
| `make test` | Executar a suíte pytest |
| `make lint` | Verificar lint e formatação com Ruff |
| `make typecheck` | Verificar tipos com mypy |
| `make security` | Executar pip-audit e Bandit |
| `make reproduce-quick` | Executar o modo rápido do script de reprodução |
| `make reproduce` | Executar o fluxo completo definido pelo script de reprodução |

Execute os comandos no ambiente configurado para o commit que está sendo avaliado e preserve os resultados como evidência. Não trate uma execução local não realizada como aprovada; para mudanças via pull request, confira os checks do SHA exato da cabeça da PR e os gates obrigatórios do repositório.

### Logs e rastreabilidade de requisições

A API registra metadados estruturados por requisição: identificador de requisição, método, rota normalizada, status HTTP e duração. A resposta inclui `X-Request-ID`, sempre gerado pelo servidor; um valor enviado pelo cliente é descartado. O nível é controlado por `ATTRACTOR_LOG_LEVEL`, com padrão `INFO`.

O logger de acesso da aplicação não deve registrar corpos, afirmações, trechos de evidência, credenciais ou query strings. Ao investigar incidentes, use o identificador de requisição e metadados operacionais; não copie dados sensíveis para logs, issues ou pull requests. O rastro consultável pela API tem seu próprio contrato e não deve ser confundido com o log de acesso.

### Parada, diagnóstico e recuperação

1. Registre o horário, ambiente, versão/commit e identificador de requisição pertinente, sem incluir segredos ou conteúdo sensível.
2. Verifique o estado do processo/contêiner e os logs operacionais disponíveis.
3. Confirme se a configuração de autenticação e as variáveis obrigatórias estão presentes, sem imprimir seus valores secretos.
4. Diferencie falha de inicialização, falha de autenticação, validação HTTP, limite de corpo e indisponibilidade de dependência.
5. Reproduza o problema em ambiente isolado com dados não sensíveis e testes direcionados.
6. Para mudança de código ou configuração, use revisão, checks obrigatórios e procedimento controlado de implantação; não edite artefatos congelados nem contorne testes para restaurar o serviço.

### Registro verificável do `/v1/verify` (ADR-010)

Com `ATTRACTOR_VERIFY_LOG_MODE=local` ou `required`, cada decisão `r2-a` do `/v1/verify` entra num log Merkle (RFC 6962) com checkpoints assinados em Ed25519 (formato C2SP), e a resposta ganha `audit_status` e `audit_receipt`. O recibo traz a folha, a prova de inclusão, o checkpoint assinado, o sal e o registro. O cliente o verifica sem o servidor, com a chave pública publicada em `GET /v1/verify/log`.

| Variável | Uso |
|---|---|
| `ATTRACTOR_VERIFY_LOG_MODE` | `off` (padrão; nada muda), `local` (grava; se falhar, devolve o veredito com `audit_status = "not_recorded"`) ou `required` (sem registro, sem veredito: HTTP 503) |
| `ATTRACTOR_VERIFY_LOG_KEY` | Semente Ed25519 de 32 bytes em hex, vinda de um gerenciador de segredos. Obrigatória fora do `off`; sem ela, o serviço não sobe |
| `ATTRACTOR_VERIFY_LOG_ORIGIN` | Nome do log, impresso em todo checkpoint (por exemplo `attractor.suaempresa.com.br/verify-log`). Um banco fica preso à origem e à chave com que foi criado |
| `ATTRACTOR_VERIFY_LOG_DB` | Banco SQLite do log; padrão `.attractor/verify-log.sqlite3`, no mesmo volume da trilha |

- **Gerar a chave:** `python -c "import secrets; print(secrets.token_hex(32))"`. Guarde-a fora do host. Perder a chave impede novos checkpoints com a mesma identidade; vazá-la permite que outros assinem checkpoints em nome do log.
- **Reenvio:** o cabeçalho `Idempotency-Key` (1 a 128 caracteres visíveis) faz a mesma chave e a mesma entrada devolverem o mesmo recibo. A mesma chave com outra entrada devolve 409. As chaves são separadas por cliente.
- **Verificação do servidor:** `VerificationLog.verify_log()` recalcula a árvore e confere todos os checkpoints guardados. Rode diariamente e guarde o checkpoint mais recente (`GET /v1/verify/log`) fora do host.
- **Apagamento (LGPD):** `VerificationLog.erase(indice, data)` apaga o sal e o registro de um evento e grava um **evento de apagamento** na árvore (`ayorai.verify-erasure.v1`: índice apagado, data e motivo, sem dados pessoais), sob um novo checkpoint assinado. A árvore continua válida, e o recibo que o cliente guardou continua verificável. `verify_log()` acusa qualquer registro apagado ou removido sem o evento correspondente.
- **Backup e restauração:** `VerificationLog.backup(destino)` faz uma cópia consistente com `integrity_check`. Depois de restaurar, rode `verify_log()` e confira o último checkpoint guardado fora do host com `matches_checkpoint(nota)`: uma cópia mais antiga ou uma história reescrita devolve `False`.
- **Limites:** sem testemunhas nem carimbo do tempo (ADR-010, decisões 6 e 7), quem controla o banco e a chave pode reescrever o log. Recibos e checkpoints guardados fora do host são o que permite detectar isso. O armazenamento é SQLite com um escritor por vez (vários processos no mesmo host podem compartilhar o banco). Ainda não há publicação no formato de tiles nem prova de consistência servida por HTTP; `consistency()` existe na biblioteca.

### Persistência, backup e restauração dos rastros de auditoria

Os rastros de `POST /v1/audit` ficam no arquivo indicado por `ATTRACTOR_AUDIT_DB`. Sem um volume montado nesse caminho, eles se perdem quando o contêiner é recriado. Exemplo com volume nomeado (o diretório precisa pertencer ao usuário do contêiner, uid 999):

```bash
docker volume create ayorai-audit
docker run --rm --user root --entrypoint sh -v ayorai-audit:/v <imagem> -c 'chown 999:999 /v'
docker run ... -v ayorai-audit:/app/.attractor <imagem>
```

Backup online, com o serviço em execução, pela API de backup do SQLite. A cópia é conferida (`integrity_check`) e o comando recusa sobrescrever um arquivo existente:

```python
from ayorai_attractor.audit_store import AuditTraceStore

with AuditTraceStore("/app/.attractor/audit.sqlite3") as store:
    print(store.backup("/backups/audit-AAAAMMDD.sqlite3"))  # número de rastros copiados
```

Restauração:

1. Pare o serviço.
2. Copie o arquivo de backup para o caminho de `ATTRACTOR_AUDIT_DB`.
3. Com as mesmas `ATTRACTOR_AUDIT_HMAC_KEYS` da produção, execute `AuditTraceStore(caminho).verify_all()`; o esperado é `invalid` igual a 0.
4. Execute `verify_chain(checkpoint)` com o último checkpoint guardado fora do host (ver "Cadeia de sequência" abaixo). Um backup é mais antigo que o checkpoint mais recente; nesse caso, `checkpoint_mismatch` é esperado e deve ser conferido com o checkpoint da data do backup.
5. Suba o serviço.

Com HMAC, mantenha as chaves em custódia separada do backup do banco: quem tem as duas coisas pode reselar registros. Rastros gravados antes de configurar as chaves podem ser selados uma vez com `seal_unsealed()`, que só sela rastros cujo digest ainda confere. A rotina cobre r2-v1, r2-v2, r2-v3 e r2-v4 e preserva a versão de replay. Ao habilitar HMAC em uma base existente, execute-a com a lista completa de chaves antes de usar `verify_all()` como gate: com HMAC configurado, todas as versões suportadas precisam ter MAC válido. Se o banco já contém rastros selados, o armazenamento não abre sem `ATTRACTOR_AUDIT_HMAC_KEYS`, evitando continuar gravando sem autenticação criptográfica. A selagem valida o digest existente e autentica o estado atual do rastro; não prova retroativamente que um rastro legado não foi adulterado antes da ativação do HMAC. Retirar uma chave da lista invalida os rastros assinados por ela; para aposentá-la, faça a rotação abaixo.

Cadeia de sequência (detecção de exclusão):

- Todo rastro gravado pela API também entra em `audit_chain`, uma sequência com elos encadeados por HMAC (SHA-256 sem chave). `verify_all()` confere cada rastro; `verify_chain()` confere o conjunto e reporta:
  - `missing_traces`: rastro apagado sem registro de purga;
  - `broken_links`: entrada da cadeia removida, renumerada ou reescrita;
  - `digest_mismatches`: digest do rastro diferente do encadeado;
  - `unsequenced_traces`: rastros sem entrada na cadeia (anteriores a ela, ou inseridos fora da API).
- `intact` é verdadeiro sem nenhum dos três primeiros; `complete` exige também zero rastros sem sequência.
- A retenção (`ATTRACTOR_AUDIT_RETENTION_DAYS`) e `purge_recorded_before()` gravam um registro de purga na cadeia, com as sequências apagadas. Uma purga não cobre rastros gravados depois dela.
- **Checkpoint externo:** guarde `store.checkpoint()` (`{"seq", "link"}`) fora do host, por exemplo junto com o hash do backup diário. `verify_chain(checkpoint)` acusa `checkpoint_mismatch` se as entradas mais recentes tiverem sido removidas ou se o banco tiver voltado a uma cópia antiga. Sem checkpoint externo, essas duas situações **não** são detectáveis localmente.
- Base criada antes da cadeia: execute `sequence_unsequenced()` uma vez (depois de `seal_unsealed()`, se usar HMAC). Ela encadeia os rastros válidos em ordem de `trace_id` e estabelece uma linha de base; não prova o que aconteceu antes.

Rotação de chave HMAC:

1. Gere a nova chave (32 bytes, hex) e coloque-a **primeiro** em `ATTRACTOR_AUDIT_HMAC_KEYS`, mantendo as antigas depois dela (`k2:<nova>,k1:<antiga>`). Reinicie o serviço: novos rastros passam a usar a chave nova.
2. Faça um backup (`store.backup(...)`).
3. Execute `AuditTraceStore(caminho).reseal_with_active_key()`. Cada rastro assinado por outra chave é verificado com as chaves configuradas e, se válido, assinado de novo com a chave ativa. O retorno é `{"resealed": n, "skipped_invalid": m}`. Rastros inválidos **não** são re-selados, para que uma adulteração nunca vire um rastro válido; com `m > 0`, investigue antes de seguir.
4. Confirme `verify_all()` com `invalid` igual a 0 (ou igual aos `m` já investigados) e `verify_chain()` com `intact` verdadeiro. A mesma chamada reassina a cadeia com a chave ativa, mas só se ela estiver íntegra; uma cadeia com problema continua com a chave antiga e precisa ser investigada antes de aposentar a chave.
5. Só então retire a chave antiga da lista e reinicie. Destrua-a depois que nenhum backup retido depender dela.

A rotação autentica o estado atual de cada rastro com a nova chave; ela não substitui a custódia das chaves nem cria armazenamento imutável.

Em ambientes que exigem HMAC sem depender dos metadados do banco, configure `ATTRACTOR_AUDIT_HMAC_REQUIRED=true` juntamente com `ATTRACTOR_AUDIT_HMAC_KEYS`. A opção obrigatória faz a inicialização falhar se as chaves não estiverem disponíveis, inclusive quando todos os campos MAC do SQLite forem removidos. Mantenha essa política fora do arquivo do banco (por exemplo, na configuração protegida do serviço) e as chaves em um gerenciador de segredos. O padrão `false` preserva o modo local sem HMAC; portanto, a implantação precisa ativar explicitamente a política quando esse nível de proteção for requerido.

Retenção: com `ATTRACTOR_AUDIT_RETENTION_DAYS` (inteiro de 1 a 36500), o serviço apaga automaticamente os rastros mais antigos que o prazo: na inicialização e, depois, no máximo uma vez por hora, durante as gravações. Sem a variável (padrão), nada é apagado. Para expurgo manual, `purge_recorded_before(data_com_fuso)` remove rastros gravados antes da data e devolve quantos removeu. Rastros antigos sem `recorded_at` nunca são removidos, porque a idade deles é desconhecida. O prazo de retenção e a base legal são decisões do controlador dos dados e não estão definidos no repositório.

Testes: `tests/test_audit_store_durability.py` cobre backup durante escrita contínua, restauração, queda por SIGKILL durante gravação e quatro processos gravando ao mesmo tempo.

Este capítulo não define alta disponibilidade, SLO, rotação automatizada de segredos ou rollback de produção. Esses procedimentos precisam ser definidos e validados para o ambiente concreto antes de alegar prontidão operacional.

## Contratos e parâmetros

| Parâmetro/comando | Efeito documentado |
|---|---|
| `ATTRACTOR_PROVIDER` | `mock` é o provider local padrão; `openai-compatible` seleciona o adaptador OpenAI-compatível. |
| `OPENAI_API_KEY` | Credencial do adaptador compatível; nunca deve ser commitada ou impressa em logs. |
| `OPENAI_BASE_URL`, `ATTRACTOR_MODEL` | Parâmetros opcionais do adaptador, conforme `docs/providers.md`. |
| `ATTRACTOR_AUTH_MODE` | `api_key` por padrão; `off` apenas para desenvolvimento local isolado. |
| `ATTRACTOR_API_KEY_PEPPER`, `ATTRACTOR_API_KEYS_HMAC_SHA256` | Segredos/digests exigidos no modo `api_key`; consulte `docs/security/API-AUTH.md`. |
| `ATTRACTOR_LOG_LEVEL` | `DEBUG`, `INFO`, `WARNING`, `ERROR` ou `CRITICAL`; padrão `INFO`. |
| `ATTRACTOR_MAX_BODY_BYTES` | Limite inteiro positivo do corpo HTTP; padrão 2 MiB. |
| `ATTRACTOR_MAX_INFLIGHT_HEAVY` | Máximo de requisições `POST /v1/*` em execução simultânea; padrão 2. Acima disso a API responde HTTP 503 com `Retry-After: 1`. Inteiro positivo; valor inválido impede a inicialização. |
| `ATTRACTOR_INFLIGHT_SCOPE` | `process` (padrão): o limite vale por worker. `host`: o limite é compartilhado por todos os workers do mesmo host, com locks de arquivo (`flock`) liberados pelo kernel se o processo morrer; exige POSIX. Entre réplicas em hosts diferentes, aplique também um limite global no gateway. |
| `ATTRACTOR_INFLIGHT_LOCK_DIR` | Diretório dos arquivos de vaga no escopo `host`; padrão por usuário: `$XDG_RUNTIME_DIR/ayorai-attractor-inflight` ou, sem essa variável, o diretório temporário do sistema seguido de `ayorai-attractor-inflight-<uid>`. O diretório precisa pertencer ao usuário do processo e não pode ter escrita para grupo ou outros; caso contrário, a API não inicia. Todos os workers do host devem rodar com o mesmo usuário e usar o mesmo diretório. |
| `ATTRACTOR_AUDIT_DB` | Arquivo SQLite dos rastros de auditoria; padrão `.attractor/audit.sqlite3` (no contêiner, `/app/.attractor/audit.sqlite3`). |
| `ATTRACTOR_AUDIT_LEGACY_TRACES` | `hidden` (padrão) ou `shared`: visibilidade, pela API, de rastros antigos sem dono. Outro valor impede a inicialização. |
| `ATTRACTOR_AUDIT_HMAC_KEYS` | Opcional. Chaves HMAC dos rastros, `id:hex` (32 bytes), separadas por vírgula; a primeira assina os rastros novos e as demais só verificam (rotação). Segredo: guarde fora do repositório e fora do backup do banco. |
| `ATTRACTOR_AUDIT_HMAC_REQUIRED` | `true` exige `ATTRACTOR_AUDIT_HMAC_KEYS` na inicialização, mesmo com o banco vazio; padrão `false`. Recomendado em produção. |
| `ATTRACTOR_AUDIT_RETENTION_DAYS` | Opcional. Prazo de retenção automática dos rastros, em dias inteiros (1 a 36500). Vazio ou ausente (padrão): nada é apagado. Valor inválido impede a inicialização. |
| `make test` | Executa pytest. |
| `make lint` | Executa `ruff check .` e `ruff format --check .`. |
| `make typecheck` | Executa mypy sobre `src/ayorai_attractor`. |
| `make security` | Executa `pip-audit` e Bandit. |
| `make reproduce-quick` / `make reproduce` | Executa o script de reprodução em modo rápido/completo. |

Os alvos de Makefile são conveniências operacionais; antes de declarar um check aprovado, confirme que o comando foi realmente executado e confira o SHA avaliado.

## Limites conhecidos

- A autenticação por chave não substitui HTTPS em redes não confiáveis, controle de rede, autorização por escopo, limitação de taxa, rotação operacional de segredos ou resposta a incidentes.
- `/health` não é um teste abrangente de dependências.
- Uma suíte verde não é certificação nem prova de prontidão para produção.
- O modo de desenvolvimento com recarga automática não deve ser tratado como configuração de implantação.
- A operação de `/v1/opensearch` ou `/v1/audit` não substitui a verificação formal em `/v1/verify`.

## Evidências

- `Makefile` e `pyproject.toml`: alvos operacionais e entrypoints de CLI.
- `src/ayorai_attractor/cli/main.py`: comandos, suítes permitidas e formato do resumo.
- `docs/providers.md`, `docs/DOCKER.md`, `docker-compose.yml` e `.env.example`: providers, segredos e execução em contêiner.
- `tests/test_cli_contract.py`, `tests/test_cli_module.py` e `tests/test_reproduce_script.py`: contratos da CLI e reprodução.
- `tests/test_api_uvicorn_body_limit.py`, `tests/test_api_auth.py` e `tests/test_api_uvicorn_access_log.py`: limites e comportamento operacional da API.

## Ver também

- [Docker deployment](../DOCKER.md)
- [Autenticação da API](../security/API-AUTH.md)
- [API HTTP e contratos](04-api.md)
- [Providers](../providers.md)
- [Makefile](../../Makefile)
- [Configuração do projeto](../../pyproject.toml)
