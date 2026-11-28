# P3/A1 — Relatório de encerramento (2026-11-28)

Revisão por ferramenta automatizada, publicada pelo mantenedor.

| item | valor |
|---|---|
| Entrega | PR #644, squash `ef5679c063ffbb325f8fa119d74553c3f8ee1ac0` na `main` (2026-11-28) |
| Substituídas | #635, #636, #642, fechadas sem merge |
| Decisão | DEC-033, opção A (retenção), aprovada em 2026-11-28 |
| Detalhes técnicos | [P3-A1-HARDENING-2026-11-26.md](P3-A1-HARDENING-2026-11-26.md) |

**Rótulos:**
- **[FATO]**: verificado no código, por execução ou no GitHub;
- **[HIPÓTESE]**: não verificável com o acesso desta revisão.

## 1. Escopo

O A1 do roadmap v0.8 exige que os rótulos gold do DEV da Phase 1b não entrem na inferência nem sejam guardados junto das predições.

O documento do roadmap v0.8 não está no repositório. Este relatório cobre o A1, que é o único item da P3 com registro no repositório (#635, #636, #642 e #644) [FATO].

## 2. O que está na `main` [FATO]

**Inferência sem gold:**
- a entrada de inferência só tem `record_id`, documento, afirmação e coorte;
- o `record_id` não depende do rótulo;
- o job que roda os modelos nunca recebe a chave gold.

**Avaliação separada:**
- caches gold e score cifrados (AES-256-GCM) com chaves distintas;
- junção só na avaliação, conferindo execução, manifesto, cobertura e coorte.

**Transporte:**
- manifesto e entrada de inferência cifrados;
- SHA-256 da entrada conferido antes de cifrar e depois de decifrar.

**Execução minimal:** não recebe a chave gold nem guarda rótulos gold.

**Workflows:**
- só `workflow_dispatch`, com permissões mínimas;
- Environment protegido;
- re-agregação e experimento aceitam só origem deste repositório com commit na `main`;
- contrato de lista permitida de secrets por workflow.

**Retenção, pela DEC-033:**
- caches: 30 dias a partir da origem, sem renovação;
- manifesto, inferência e shards: 7 dias;
- agregados: 30 dias.

**Dependências:** os jobs com chaves e sem inferência instalam pacotes travados por hash (`cryptography` 50.0.2, `pyarrow` 23.0.1).

## 3. Validação [FATO]

| verificação | resultado |
|---|---|
| CI no HEAD da PR (`95d1bfcc`) | 38/38 verde |
| CI na `main` depois do merge (`ef5679c0`) | CI, CodeQL e Security verdes |
| suíte local na `main` (Python 3.13) | 3.392 aprovados |
| testes phase1b | 341 (antes da P3: 243) |
| mutação dos contratos de workflow | 6/6 regressões detectadas |
| Golden smoke-v0, v0, v0.1 | `969ec61a…`, `21abb816…`, `1fd6fdb7…`, inalterados |
| componentes protegidos | Judge, Golden, RGC, `rules/`, `evals/` e thresholds inalterados |

**Limite:** tudo é evidência de software. **Não há validação científica.** Nenhum workflow DEV ou TEST foi executado, e o comportamento sobre o dado real não foi observado.

## 4. Pendências do mantenedor

1. **Environment `international-benchmark-maintainer-approval`.** Confirmar em Settings → Environments:
   - só a branch `main`, sem tags;
   - aprovador obrigatório;
   - `PHASE1B_ARTIFACT_ENCRYPTION_KEY` e `PHASE1B_GOLD_LABEL_ENCRYPTION_KEY` com valores distintos.

   Sem isso, a guarda de branch dentro dos workflows não é uma fronteira de segurança [HIPÓTESE até a confirmação].
2. **Primeiro disparo.** O recomendado é o workflow minimal. Ele valida a operação, não usa rótulos gold e informa por contagem se o DEV fixado tem identidades duplicadas.
3. **Conflitos de rótulo.** Se o manifesto acusar conflitos de rótulo, a política metodológica é decisão sua.
4. **Revisão humana independente.** Não foi feita; o merge foi autorizado ciente disso.

## 5. Riscos residuais

| risco | gravidade | observação |
|---|---|---|
| Configuração do Environment não verificada | alto até a confirmação | item 4.1 |
| PyTorch do job de inferência fixado só por versão, sem hash | baixo | `download.pytorch.org` estava bloqueado na revisão |
| `scripts/benchmarks/phase1b/` fora do gate de cobertura da CI | baixo | preexistente; a cobertura foi medida manualmente |
| Artefatos antigos (manifesto v1, score-cache v3/v4) não reaproveitáveis | informativo | exigem nova execução |

## 6. Situação

**A P3/A1 está concluída em código, testes, documentação e governança.** O merge foi feito e a decisão de retenção está aprovada.

A **prontidão operacional** depende dos itens 4.1 e 4.2, que são do mantenedor. A **validação científica** depende de uma execução DEV autorizada.
