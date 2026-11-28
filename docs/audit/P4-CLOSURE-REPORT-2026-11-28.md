# P4 — Relatório de encerramento (2026-11-28)

Revisão por ferramenta automatizada, publicada pelo mantenedor.

| item | valor |
|---|---|
| `main` | `02a20a863c38f867ad084871a9025b0f37b6be29` (merge da #652) |
| Diagnóstico de partida | [P4-DIAGNOSIS-2026-11-28.md](P4-DIAGNOSIS-2026-11-28.md) |
| Escopo | engenharia, segurança, confiabilidade, reprodutibilidade e cadeia de dependências |
| Fora do escopo | Judge, Golden, RGC, thresholds e protocolos científicos; nenhuma execução DEV ou TEST |

**Rótulos:**
- **[FATO]**: verificado no código, por execução ou no GitHub;
- **[HIPÓTESE]**: não verificado.

Testes de software não são validação científica.

## 1. PRs integradas [FATO]

| PR | merge | conteúdo |
|---|---|---|
| #651 | `0ee163c2` | testes de processo morto (SIGKILL) no log de verificação e na fila de jobs; diagnóstico P4 |
| #645 | `d3197a16` | Schemathesis aceita o 413 documentado (P4-07) |
| #653 | `07480515` | atualizações do Dependabot numa só mudança, com a coautoria preservada (P4-08); #637 a #641 fechadas |
| #652 | `02a20a86` | inferência Phase 1b travada por hash, nltk embutido, torch 2.14 e transformers 5.24 com equivalência de escores (P4-01 a P4-04) |

A CI ficou verde no HEAD final de cada PR antes do merge.

## 2. Situação de cada achado

| id | situação | evidência |
|---|---|---|
| P4-01 | **resolvido** | jobs `shard` do minimal e do full instalam só `requirements-phase1b-torch-cpu.txt` e `requirements-phase1b-inference.txt`, com `--require-hashes --only-binary :all: --no-deps` e `pip check`; teste de contrato: todo job que recebe chave instala só de lock com hash |
| P4-02 | **resolvido** | `reproducibility/phase1b-dev-2026-11-07/MANIFEST.json` restaurado byte a byte da branch `0edc35b9` |
| P4-03 | **resolvido** | hash do `torch-2.7.1+cpu` lido do wheel oficial num runner (`8f8b3cfc…60947`) |
| P4-04 | **resolvido** | torch 2.14.0, transformers 5.24.0, nltk fora do ambiente (segmentação 3.9.4 embutida), pyarrow e pandas fora do lock; `pip-audit` sem alertas; `dependency-review` verde. Equivalência: [P4-INFERENCE-EQUIVALENCE-2026-11-28.md](P4-INFERENCE-EQUIVALENCE-2026-11-28.md) e [P4-NLTK-EQUIVALENCE-2026-11-28.md](P4-NLTK-EQUIVALENCE-2026-11-28.md) |
| P4-05 | **decisão do mantenedor** | `PHASE1B_GOLD_LABEL_ENCRYPTION_KEY` ainda precisa existir no Environment, com valor distinto da chave de artefato |
| P4-06 | **resolvido** | `tests/test_recovery_process_kill.py`; nesta etapa, o escritor passou a não sobreviver a uma rodada que falha (a suíte local travou uma vez por isso) |
| P4-07 | **resolvido** | #645 |
| P4-08 | **resolvido** | #653 |
| P4-09 | proposta | proveniência e SBOM atestados da imagem Docker exigem `attestations: write` num workflow que publique a imagem; hoje o `docker.yml` só constrói e testa |
| P4-10 | informativo | `mypy --strict` continua não bloqueante |
| P4-11 | decisão do mantenedor | revisão humana independente |

## 3. Equivalência de escores [FATO]

Workflow `phase1b-inference-equivalence.yml`, execução `46181650820`: o código do shard roda os três modelos em 90 pares sintéticos, no ambiente histórico (torch 2.7.1, transformers 4.55.4) e no novo.

| modelo | max \|Δ\| | decisões trocadas | mesma divisão |
|---|---|---|---|
| mDeBERTa | 2,56e-6 | 0 | sim |
| MiniCheck | 8,34e-7 | 0 | sim |
| FactCG | 1,37e-6 | 0 | sim |

- A primeira medição falhou (até 0,19). A causa foi localizada trocando um pacote por vez: o `AutoTokenizer` do transformers 5.x reconstrói o tokenizador DeBERTa-v2 a partir do `spm.model`.
- A correção lê o `tokenizer.json` da revisão fixada, como o 4.55.4 fazia. Nada no protocolo mudou.

## 4. O que continua pendente

**Decisões do mantenedor:**
1. Criar ou confirmar `PHASE1B_GOLD_LABEL_ENCRYPTION_KEY` no Environment (P4-05).
2. Autorizar o disparo do minimal na `main` atual, para validar os novos locks no job protegido. O minimal não calcula métricas.
3. Autorizar a execução DEV completa, a única que mede acurácia.
4. Decidir sobre a rota de acurácia: [../benchmarks/ACCURACY-PLAN-2026-11-28.md](../benchmarks/ACCURACY-PLAN-2026-11-28.md).
5. P4-09 (permissão de atestação) e P4-11 (revisão independente).

**Melhorias de engenharia propostas, sem urgência:**
- teste de contrato: reexecutar um shard não sobrescreve artefato (`overwrite: false`);
- teste de contrato: artefato expirado entre `plan` e `shard` leva a recusa clara;
- disco cheio no log de verificação em modo `local` e no `JobStore`.

## 5. Situação

**P4: CONCLUÍDA NA ENGENHARIA.**
- A cadeia de suprimentos do job que decifra o DEV está travada por hash, sem alertas conhecidos, e as pontuações são equivalentes às do ambiente histórico.
- A validação científica depende das decisões da seção 4.
