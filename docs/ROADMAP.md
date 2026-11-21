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
| G1 — Integridade de código e contratos | PRs antigas encerradas; gates RGC integrados (#580, #584, #576, #577, #600); contratos por rota registrados (ADR-011) | Retificação normativa: o `xfail` em `tests/test_rgc_rectification_properties.py` (texto superado ainda pode apoiar) depende de decisão metodológica |
| G2 — Segurança | Itens 1 e 2 acima; CodeQL, Bandit, pip-audit, Grype, Dependency Review e secret scanning no CI | Escopos, expiração e tenant; política de divulgação coordenada revisada por pessoa |
| G3 — Observabilidade e operação | Logs estruturados sem conteúdo; backup, restauração e rotação documentados (`docs/manual/05-operacao.md`); imagem sem root | Métricas e alertas ligados a uma plataforma; testes de carga e soak |
| G4 — Cadeia de suprimentos e releases | SBOM CycloneDX, proveniência SLSA assinada, locks com hash | Build reprodutível comparado de forma independente; checklist de release executado na próxima versão |
| G5 — RGC científico | Runner com snapshots, interpretador isolado, IC e testes por componente (DEC-021 a DEC-023, DEC-027) | Somente humano: piloto 02, segunda anotação, revisão F-01, inserção das emendas propostas em `docs/eval/AMENDMENT-PROPOSAL-2026-11-21-DEC-022.md`, congelamento e execução única |
| G6 — Prontidão para produção | Proposta de POC em `docs/poc/POC-PROPOSAL.md` | Implantação real de homologação com gateway, TLS e backup testados; avaliação externa |
