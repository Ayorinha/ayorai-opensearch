# AYORAI ATTRACTOR — Progress

**Estado atual:** Fase 0 concluída; R1 não iniciado.  
**Base verificada:** main em `b7df480a480c948a50341c34cb91d3a3a0af7a51`.  
**Ground Truth:** 34 casos / 52 documentos.  
**Baseline:** 43,3333%, igual à classe majoritária.

## Roadmap ponderado

| Item | Peso | Status | PRs | Data de conclusão |
|---|---:|---|---|---|
| Fase 0 — Fundação e ground truth | 10 | concluído | #7–#12 | 2026-09-30 |
| R1 — Motor de verificação | 15 | não iniciado | — | — |
| R2 — Audit Mode | 10 | não iniciado | — | — |
| R3 — Conselho de IAs | 10 | não iniciado | — | — |
| R4 — Proveniência e replay | 6 | não iniciado | — | — |
| R5 — Recuperação híbrida OpenSearch | 8 | não iniciado | — | — |
| R6 — Síntese fiel por construção | 6 | não iniciado | — | — |
| R7 — Segurança (MCP, OWASP ASI, red team) | 8 | não iniciado | — | — |
| R8 — Observabilidade e custo | 5 | não iniciado | — | — |
| R9 — Orquestração multi-agente durável | 7 | não iniciado | — | — |
| R10 — Arena comparativa | 5 | não iniciado | — | — |
| R11 — Aprendizado GEPA | 3 | não iniciado | — | — |
| R12 — Attractor Studio + MCP próprio | 5 | não iniciado | — | — |
| R13 — Escala, operação e governança | 2 | não iniciado | — | — |

### Justificativa dos pesos

- **Fase 0 (10):** cria o ground truth, medição e barreiras contra autoengano.
- **R1 (15):** é o núcleo técnico de verificação que transforma a fundação em capacidade real.
- **R2 (10):** torna a verificação auditável e operacional.
- **R3 (10):** adiciona deliberação multi-modelo controlada.
- **R4 (6):** garante proveniência e replay verificável.
- **R5 (8):** introduz recuperação híbrida em dados reais.
- **R6 (6):** reduz afirmações sem suporte na síntese.
- **R7 (8):** cobre segurança de agentes e red team.
- **R8 (5):** mede observabilidade, custo e latência.
- **R9 (7):** adiciona execução durável em fluxos longos.
- **R10 (5):** cria comparação reprodutível entre sistemas.
- **R11 (3):** adiciona otimização/aprendizado controlado.
- **R12 (5):** expõe o sistema como produto e servidor MCP.
- **R13 (2):** fecha operação, escala e governança.

## Progresso

**Fase 0:** 10/10 = 100%.  
**v1.0:** 10/100 = **10%**.

Barra: **[██░░░░░░░░░░░░░░░░░░] 10%**

### Marcos

| Marco | Fórmula | Progresso |
|---|---|---:|
| v0.1 | Fase 0 / 10 | **100%** |
| v0.5 | Fase 0 / (Fase 0 + R1 + R2) | **28,57%** |
| v0.7 | (Fase 0 + R1 + R2 + R3 + R4 + R5) / 59 | **16,95%** |
| v1.0 | todo roadmap | **10%** |

Não são previsões de prazo.

## Ritmo observado

PRs #7, #8, #9, #10 e #11 foram mergeados entre 16:50:30Z e 17:07:01Z em 2026-09-30; PR #12 foi mergeado às 18:33:31Z. Isso corresponde a 6 itens concluídos em aproximadamente 103 minutos entre o primeiro e o último merge. Esse ritmo é apenas histórico desta sessão e **não é uma estimativa de prazo**; a continuidade depende do tempo disponível do mantenedor.

## Trilha de colaboração GitHub

- **concluída no PR #21**, com CI verde antes do merge.
- CONTRIBUTING.md e CODE_OF_CONDUCT.md.
- Templates de bug, feature, golden case e pull request.
- Seis issues reais (#15–#20), com `good first issue` / `help wanted`.
- Discussions: **não ativadas pelo conector disponível**; a configuração requer ação no GitHub.

## Próximos 3 itens

1. README/portfólio do ATTRACTOR em PR próprio.
2. README do perfil Ayorinha em PR próprio.
3. R1-a — contrato de modelos e ADR do motor de verificação.

## Evidência

- PR #12 / Fase 0: https://github.com/Ayorinha/ayorai-opensearch/pull/12
- Baseline: https://github.com/Ayorinha/ayorai-opensearch/actions/runs/36759101933
- Green Wall: https://github.com/Ayorinha/ayorai-opensearch/actions/runs/36759109543
