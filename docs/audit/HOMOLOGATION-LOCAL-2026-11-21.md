# Homologação local controlada — 2026-11-21

**Escopo:** implantação da imagem real do serviço num contêiner local, com configuração de produção, e verificação de segurança e operação. **Não substitui** a homologação num ambiente real com gateway, TLS, gerenciador de segredos e rede de produção (`docs/poc/POC-PROPOSAL.md`).

## Configuração

| Item | Valor |
|---|---|
| Código | `main` @ `bffc341` e branch da #620 (`f38436f`, integrada depois) |
| Imagem | `docker/Dockerfile`. Os contêineres deste ambiente não confiam no certificado do proxy de rede, então as 33 wheels de `docker/requirements.lock` foram baixadas no host, conferidas por hash (`pip download --require-hashes`), e instaladas na build sem rede (`--no-index`). O conjunto instalado é exatamente o do lock |
| Execução | usuário `attractor` (uid 999); `--read-only`; `/tmp` em tmpfs `noexec,nosuid` de 64 MiB; `--cap-drop ALL`; `--security-opt no-new-privileges`; volume nomeado para `/app/.attractor` |
| Segurança | `ATTRACTOR_AUTH_MODE=api_key`, pepper e duas chaves geradas na hora (nunca impressas); `ATTRACTOR_AUDIT_HMAC_KEYS` com uma chave; `ATTRACTOR_AUDIT_HMAC_REQUIRED=true` |

## Verificações

Script: `scripts/ops/homologation_smoke.py`. Saídas em [`reports/ops/2026-11-21/`](../../reports/ops/2026-11-21/).

| Verificação | Resultado |
|---|---|
| A imagem sobe com raiz só de leitura e sem capacidades | PASS, contêiner `healthy` em 6 s |
| Liveness `/health` e readiness `/ready` | PASS |
| Rota protegida sem chave, com chave errada e `/metrics` sem chave → 401 | PASS |
| `/v1/check` com `trace_id` determinístico (`chk_…`, igual em duas chamadas) | PASS |
| `X-Request-ID` gerado pelo servidor | PASS |
| `/v1/audit` grava; o dono lê com `replay_integrity=valid`; outra chave recebe 404 | PASS |
| Corpo vazio → 422; corpo acima de 2 MiB recusado (413) | PASS. O serviço responde 413 pelo `Content-Length` e fecha sem ler o corpo; um cliente que ainda está enviando pode ver o reset da conexão em vez do 413. O script aceita as duas formas e registra qual ocorreu |
| `/metrics` com chave, sem trace ID nem credencial nos rótulos | PASS |
| `verify_all()` e `verify_chain(checkpoint)` no contêiner | `{"valid": 1, "invalid": 0}`; cadeia `intact` e `complete` |
| Reinício do contêiner: o rastro anterior continua `valid` | PASS (16/16) |
| Backup com `AuditTraceStore.backup()`, restauração no volume com o serviço parado, nova subida | `verify_all` 1/1 válido; cadeia íntegra e igual ao checkpoint guardado fora do contêiner; smoke 16/16 em três execuções seguidas |
| Adulteração numa cópia do banco (um rastro apagado no meio) | `verify_all()` continua `{"valid": 7, "invalid": 0}`, mas `verify_chain()` acusa `intact=false`, `missing_traces=1` |
| Logs sem chaves, pepper nem texto das requisições | PASS: nenhuma das chaves, nem o pepper, nem o texto sintético aparece nas 43 linhas de log |

## Resultado

- **Aprovado localmente:** a imagem roda endurecida, a autenticação e o isolamento por dono funcionam, a trilha sobrevive a reinício e a restauração, e a adulteração é detectada.
- **Mudança decorrente:** o `docker-compose.yml` passa a usar o mesmo endurecimento validado (`read_only`, `tmpfs` em `/tmp`, `cap_drop: ALL`, `no-new-privileges`).
- **Capacidade:** [docs/benchmarks/CAPACITY-2026-11-21.md](../benchmarks/CAPACITY-2026-11-21.md).

## O que esta homologação não cobre

- TLS e gateway reais.
- Gerenciador de segredos.
- Várias réplicas, rede externa, OpenSearch real.
- Teste de longa duração.
- Revisão de segurança independente.

Esses itens continuam em `docs/ROADMAP.md` §4 e na proposta de POC.
