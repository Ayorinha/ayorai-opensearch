# Roteiro de longo prazo

**Atualizado:** 2026-11-21. Estado atual: [STATUS.md](STATUS.md).

Este roteiro substitui as issues de planejamento #433, #434 e #435, fechadas em 2026-11-21. Cada item diz o que já existe na `main`, o que falta e o critério objetivo de conclusão. Nada aqui é defeito aberto: são etapas futuras. Quando uma etapa for iniciada, ela ganha uma PR própria e, se mudar contrato, uma ADR.

## 1. Trilha de auditoria verificável (antiga #433; ADR-010)

| Etapa | Estado | Critério de conclusão |
|---|---|---|
| HMAC com chave fora do banco, rotação e selagem de bases antigas | Implementado (#564, #575, #594) | — |
| Rastro do `/v2/audit` vinculado à adjudicação (`r2-v4`) | Implementado (#590) | — |
| Detecção de exclusão no meio da trilha, de inserção fora da API e, com checkpoint externo, de truncamento e rollback (`verify_chain`) | Implementado (#602) | — |
| Persistir o veredito do `/v1/verify` (`audit_status`, `audit_receipt`, `Idempotency-Key`, ADR-009 §15.1) | Não implementado | Evento gravado na mesma operação; falha de gravação bloqueia o veredito no modo obrigatório (DEC-012, decisão 3); testes de contrato |
| Log Merkle (C2SP tlog-tiles) e checkpoints assinados (ADR-010, fases 2 e 3) | Biblioteca isolada da fase 1 em `src/ayorai_attractor/auditlog/` | Escritor escolhido por prova de conceito (decisão aberta da ADR-010); verificação de prova de inclusão por terceiro |
| Testemunhas independentes e carimbo do tempo ICP-Brasil | Decisão aberta (ADR-010, decisões 5 a 7) | Decisão do mantenedor registrada |

Limite permanente: quem controla o banco e a chave ativa pode reescrever a cadeia local. Só um checkpoint guardado fora do controle desse operador permite detectar isso.

## 2. Autorização por principal e tenant (antiga #434)

| Etapa | Estado | Critério de conclusão |
|---|---|---|
| Chave guardada só como HMAC com pepper | Implementado (`api/auth.py`) | — |
| Cada chave mapeada a um principal estável; rastro com dono; leitura de rastro de outro principal devolve 404 (sem IDOR) | Implementado (#564) | — |
| Revogação individual | Parcial: retirar o digest de `ATTRACTOR_API_KEYS_HMAC_SHA256` e reiniciar revoga a chave | Revogação sem reinício, com registro de quem revogou |
| Escopos (ler rastro, verificar, administrar) e expiração por chave | Não implementado | ADR aprovada; testes negativos por escopo, chave expirada e chave revogada |
| Tenant distinto de principal e implantação compartilhada | Não implementado | ADR aprovada; testes entre tenants; até lá, a implantação suportada é de um único tenant |

## 3. Plano mestre de prontidão (antiga #435)

| Gate | Estado em 2026-11-21 | Falta |
|---|---|---|
| G0 — Baseline e governança | `STATUS.md` reflete a `main`; workflows com actions fixadas por SHA; matriz Python 3.11–3.13 no CI | Avaliar 3.14 em job de compatibilidade antes de declarar suporte |
| G1 — Integridade de código e contratos | PRs antigas encerradas; gates RGC integrados (#580, #584, #576, #577, #600); contratos por rota registrados (ADR-011) | Marcar `superseded_spans` nas fontes retificadas do corpus, por curadoria humana; o runner já exclui o texto superado (#609) |
| G2 — Segurança | Itens 1 e 2 acima; CodeQL, Bandit, pip-audit, Grype, Dependency Review e secret scanning no CI | Escopos, expiração e tenant; política de divulgação coordenada revisada por pessoa |
| G3 — Observabilidade e operação | Logs estruturados sem conteúdo; backup, restauração e rotação documentados (`docs/manual/05-operacao.md`); imagem sem root | Métricas e alertas ligados a uma plataforma; testes de carga e soak |
| G4 — Cadeia de suprimentos e releases | SBOM CycloneDX, proveniência SLSA assinada, locks com hash | Build reprodutível comparado de forma independente; checklist de release executado na próxima versão |
| G5 — RGC científico | Runner com snapshots, interpretador isolado, IC e testes por componente (DEC-021 a DEC-023, DEC-027) | Somente humano: piloto 02, segunda anotação, revisão F-01, inserção das emendas propostas em `docs/eval/AMENDMENT-PROPOSAL-2026-11-21-DEC-022.md`, congelamento e execução única |
| G6 — Prontidão para produção | Proposta de POC em `docs/poc/POC-PROPOSAL.md` | Implantação real de homologação com gateway, TLS e backup testados; avaliação externa |

## 4. Prontidão para POC e para produção (avaliação de 2026-11-21)

O que a `main` tem hoje e o que falta, tema por tema. "Existe" quer dizer código na `main` com teste; nenhuma linha é prova de operação real, porque não houve implantação. A POC é planejada em [poc/POC-PROPOSAL.md](poc/POC-PROPOSAL.md).

| Tema | Existe | Falta para a POC | Falta para produção |
|---|---|---|---|
| Autenticação | Chave por HMAC com pepper (`api/auth.py`); limite por IP e por chave | — | Revogação sem reinício |
| Autorização e escopos | Dono por rastro; 404 para rastro de outro principal | — | Escopos e expiração por chave (§2) |
| Multi-tenancy e isolamento | Isolamento por principal no `GET /v1/audit/{id}` | Usar um único tenant | Tenant distinto de principal, com ADR e testes entre tenants (§2) |
| Trilha de auditoria | HMAC, rotação, retenção, `verify_all`, cadeia `verify_chain` e `checkpoint` (#602; transação corrigida na #604 e na #611) | `checkpoint()` diário guardado fora do host | Persistir o veredito do `/v1/verify`; log Merkle; checkpoints assinados; testemunhas; carimbo do tempo (§1) |
| Rastreabilidade do veredito | `trace_id` determinístico no `/v1/check`; `adjudication_sha256` no `/v2/audit` (`r2-v4`) | — | Veredito do `/v1/verify` persistido (ADR-009 §15.1) |
| Evidências | Trechos com offsets e proveniência `client_supplied`/`server_retrieved` | Documentos com `url` ou origem declarada | Armazenamento verificável das evidências, não só dos digests |
| Logs | Logs estruturados sem conteúdo, com `request_id` (`api/request_context.py`) | — | Envio a uma plataforma, com retenção definida |
| Métricas e alertas | `GET /metrics` (Prometheus, com chave), regras de alerta e SLOs propostos ([observability/SLO-AND-ALERTS.md](observability/SLO-AND-ALERTS.md)) | Ligar a coleta e os alertas na plataforma da POC | Painel e SLOs confirmados com tráfego real |
| Carga e concorrência | Controle de requisições pesadas; medição local de 2026-11-21 ([benchmarks/CAPACITY-2026-11-21.md](benchmarks/CAPACITY-2026-11-21.md)): cerca de 55 req/s de `/v1/check` por processo, 503 imediato acima do limite, memória estável de cerca de 50 MiB | Repetir a medição no ambiente da POC | Testes de carga e soak; banco que aceite várias réplicas |
| TLS e gateway | Guia e exemplo nginx ([security/EDGE-RATE-LIMIT.md](security/EDGE-RATE-LIMIT.md)), testados só localmente | Gateway com TLS na POC | Gateway com contador compartilhado entre instâncias |
| Backup e recuperação | `backup()` com `integrity_check`; restauração documentada | Teste de restauração antes do início | Plano de recuperação com RPO e RTO definidos e testados |
| Build e cadeia de suprimentos | Imagem por digest, lock com hashes, SBOM, SLSA, Grype, pip-audit | — | Build reprodutível comparado de forma independente; alertas do Dependabot ligados |
| Segredos | Variáveis de ambiente; `ATTRACTOR_AUDIT_HMAC_REQUIRED` | Gerenciador de segredos para pepper e chaves HMAC | Rotação periódica documentada para o pepper |
| Monitoramento de falhas | `HEALTHCHECK` (liveness `/health`), readiness `/ready`, alerta `AttractorAuditRecordFailures` | — | — |
| Contêiner | Usuário sem privilégios; Compose com raiz só de leitura, `cap_drop: ALL` e `no-new-privileges`, validados na homologação local ([audit/HOMOLOGATION-LOCAL-2026-11-21.md](audit/HOMOLOGATION-LOCAL-2026-11-21.md)) | — | — |
