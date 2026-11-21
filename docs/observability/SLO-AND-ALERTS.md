# SLOs, métricas, alertas e recuperação

**Estado:** proposta operacional para uma implantação controlada (POC ou homologação). Os alvos abaixo são pontos de partida, a confirmar com a medição de capacidade (`docs/benchmarks/CAPACITY-2026-11-21.md`) e com o tráfego real; não são compromissos de serviço.

## Sondas

| Rota | Autenticação | Uso | Resposta |
|---|---|---|---|
| `GET /health` | não | **liveness**: o processo responde. Usada pelo `HEALTHCHECK` da imagem | `200 {"status":"ok",…}` |
| `GET /ready` | não | **readiness**: o banco da trilha responde e tem as tabelas `audit_traces` e `audit_chain`. Use no balanceador ou no orquestrador para tirar a réplica do tráfego | `200 {"status":"ready"}` ou `503 {"status":"not_ready"}`, sem detalhes |
| `GET /metrics` | **sim**, a mesma chave da API | coleta do Prometheus (`Authorization: Bearer <chave>`). Use uma chave só para isso | texto Prometheus 0.0.4 |

`/ready` e `/metrics` ficam fora do OpenAPI: são rotas de operação, não de produto.

## Métricas (`/metrics`)

| Métrica | Tipo | Rótulos |
|---|---|---|
| `attractor_http_requests_total` | counter | `route`, `method`, `status` |
| `attractor_http_request_duration_seconds` | histogram (5 ms a 10 s) | `route` |
| `attractor_audit_record_failures_total` | counter | — |
| `attractor_build_info` | gauge | `version` |
| `attractor_process_start_time_seconds` | gauge | — |

- **Rótulos limitados:** `route` é a rota normalizada (`/v1/audit/{trace_id}`, nunca o ID). Caminho desconhecido vira `unmatched`. Nenhum conteúdo, chave, principal ou trace ID vira rótulo.
- **Contadores por processo:** com vários workers ou réplicas, agregue no Prometheus (`sum by (route)`). Um reinício zera os contadores; use `rate()` e `increase()`.

## SLOs propostos

| SLI | Alvo | Janela | Consulta |
|---|---|---|---|
| Disponibilidade: respostas não 5xx, excluindo o 503 de carga | 99,5% | 30 dias | `1 - sum(rate(attractor_http_requests_total{status=~"5..",status!="503"}[30d])) / sum(rate(attractor_http_requests_total[30d]))` |
| Latência do `/v1/check` | p95 ≤ 2,5 s | 30 dias | `histogram_quantile(0.95, sum by (le) (rate(attractor_http_request_duration_seconds_bucket{route="/v1/check"}[30d])))` |
| Integridade da trilha | 0 falhas de gravação; `verify_all()` com `invalid = 0` e `verify_chain(checkpoint)` íntegro na conferência diária | contínuo e diário | `attractor_audit_record_failures_total` e o job diário de verificação |

O 503 entra como saturação, não como indisponibilidade: é o limite de rotas pesadas recusando trabalho de propósito (`ATTRACTOR_MAX_INFLIGHT_HEAVY`).

## Alertas

As regras estão em [`docker/observability/prometheus-alerts.yml`](../../docker/observability/prometheus-alerts.yml), validadas por `tests/test_observability_alerts.py`.

| Alerta | Severidade | Ação |
|---|---|---|
| `AttractorDown` (coleta falha por 2 min) | page | Ver "Recuperação", passos 1 a 3 |
| `AttractorHigh5xxRate` (> 1% por 10 min) | page | Logs por `request_id`; reverter a última mudança se coincidir |
| `AttractorAuditRecordFailures` (qualquer falha em 10 min) | page | Disco, permissões e bloqueio do SQLite; a trilha está incompleta até resolver |
| `AttractorSaturated` (> 5% de 503 por 10 min) | ticket | Aumentar réplicas ou `ATTRACTOR_MAX_INFLIGHT_HEAVY`, conforme a medição de capacidade |
| `AttractorRateLimited` (> 10% de 429 por 15 min) | ticket | Distinguir abuso de limite mal dimensionado no gateway |
| `AttractorCheckLatencyHigh` (p95 > 2,5 s por 15 min) | ticket | Tamanho dos documentos recebidos e CPU da réplica |

## Recuperação

1. **Liveness falha** (`/health`): o contêiner é reiniciado pelo `HEALTHCHECK` ou pelo orquestrador. Se reiniciar em ciclo, confira a configuração. A inicialização falha de propósito sem chave, pepper ou, com `ATTRACTOR_AUDIT_HMAC_REQUIRED=true`, sem chaves HMAC.
2. **Readiness falha** (`/ready` 503): tire a réplica do tráfego. Confira o volume da trilha (`attractor-audit`), as permissões e o espaço em disco.
3. **Banco da trilha corrompido ou perdido:** pare o serviço, restaure o último backup (`docs/manual/05-operacao.md`, "Persistência, backup e restauração") e rode `verify_all()` e `verify_chain(checkpoint)` com o checkpoint guardado fora do host. Só então volte a réplica ao tráfego.
4. **Depois de qualquer incidente:** registre horário, versão, `request_id` e o checkpoint mais recente, sem segredos nem conteúdo.

## Limites

- Não há painel pronto nem integração com uma plataforma específica.
- As métricas são por processo, e o SQLite atende um host só (ver `ROADMAP.md`, §4).
- Os alvos são propostas até a medição em ambiente real.
