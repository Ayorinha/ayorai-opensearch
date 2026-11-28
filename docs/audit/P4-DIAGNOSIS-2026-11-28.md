# P4 — Diagnóstico de maturidade de engenharia (2026-11-28)

Revisão por ferramenta automatizada, publicada pelo mantenedor.

| item | valor |
|---|---|
| `main` | `b0a280bb2d9f0c24db6e943c97d221cb12806423` (CI, CodeQL e Security verdes) |
| Escopo | engenharia, segurança, confiabilidade, reprodutibilidade, empacotamento e cadeia de dependências |
| Fora do escopo | Judge, Golden, RGC, thresholds e critérios científicos; nenhuma execução DEV ou TEST |

**Rótulos:**
- **[FATO]**: verificado no código, por execução ou no GitHub;
- **[HIPÓTESE]**: não verificável com o acesso desta revisão.

Testes de software não são validação científica.

## 1. Estado de partida [FATO]

- Suíte: 3.395 testes, verde em Python 3.11, 3.12 e 3.13. Golden smoke-v0, v0 e v0.1 inalterados.
- PRs abertas:
  - #646, #645 e #643: Drafts do mantenedor;
  - #637 a #641: Dependabot.
- Nenhum workflow em andamento.
- P3/A1 concluída com ressalvas (execução protegida `46153767025`).

## 2. Caminhos críticos

| caminho | componentes | proteção atual |
|---|---|---|
| Verificação | `/v1/verify`, `/v1/check`, `/v2/audit` → Judge 2.0 → resposta | autenticação por escopo, limites de corpo e taxa, Schemathesis, regressão Golden e Judge |
| Trilha | `audit_store` (SQLite), log de verificação Merkle assinado (`auditlog/store.py`) | integridade verificável, idempotência, backup com `integrity_check` |
| Jobs | `JobStore` com lease e fencing, `JobExecutor` | testes de lease, de concorrência e de processo morto (novo) |
| Benchmark Phase 1b | `plan` → `shard` (modelo) → `aggregate` | Environment com aprovador, artefatos cifrados, gold isolado, DEC-034 |
| Distribuição | sdist e wheel reprodutíveis, proveniência SLSA (Sigstore) | `build-distributions` com atestação |
| Imagem | `docker/Dockerfile` | base fixada por digest, lock com `--require-hashes` |

## 3. Pontos fortes verificados [FATO]

- Todas as ações dos 26 workflows estão fixadas por SHA.
- Todos os workflows declaram `permissions` no topo.
- Todo `actions/checkout` usa `persist-credentials: false`.
- O Dependabot cobre pip, GitHub Actions e Docker.
- Os jobs que têm chaves e não fazem inferência instalam `requirements-phase1b-protected.txt` com `--require-hashes`.
- A imagem Docker instala um lock com hashes, sobre uma base fixada por digest.
- `pip-audit` do lock Docker: nenhum alerta.

## 4. Riscos e lacunas

| id | gravidade | achado | evidência | ação |
|---|---|---|---|---|
| **P4-01** | **alto** | O job `shard` recebe a chave de artefato e decifra o DEV, mas instala dependências **sem hash**: PyTorch pelo índice `download.pytorch.org` só por versão, e as dependências transitivas de `requirements-benchmark-pilot.txt` (`tokenizers`, `regex`, `sympy` e outras) **sem versão fixada** | `phase1b-dev-minimal.yml` e `phase1b-dev-full.yml`, passo "Install pinned CPU dependencies" | lock de inferência com `--require-hashes` (seção 5). Bloqueio parcial: hash do PyTorch |
| **P4-02** | médio | O registro do ambiente histórico de inferência (versões exatas e hashes) existe, mas só na branch preservada `repro/phase1b-dev-env-2026-11-12` (head `0edc35b9`, PR #535 fechada). `docs/security/HISTORICAL-PINS.md` remete a `reproducibility/phase1b-dev-2026-11-07/`, que **não existe na `main`** | `git show 0edc35b9:reproducibility/phase1b-dev-2026-11-07/MANIFEST.json`; SHA-256 dos arquivos conferem com `docs/audit/PR-INVENTORY-2026-11-20.md` | trazer o registro para a `main`, sem alterar os bytes |
| P4-03 | médio | O hash do wheel `torch-2.7.1+cpu` está `PENDING` no próprio registro histórico | `MANIFEST.json`: `"torch_wheel_sha256": "PENDING"` | ler o `#sha256` do índice oficial. Bloqueado nesta sessão (seção 6) |
| P4-04 | médio | Pins históricos com alertas publicados, usados no job que tem a chave: `transformers` 4.55.4 (13 alertas), `pyarrow` 21.0.0 (PYSEC-2026-113), `accelerate` 1.10.1 (1) | `pip-audit -r requirements-benchmark-pilot.txt --no-deps` | aceitos pela decisão de 2026-11-21 (HISTORICAL-PINS). Revisitar é **decisão humana** |
| P4-05 | médio | A execução DEV completa precisa de `PHASE1B_GOLD_LABEL_ENCRYPTION_KEY`, que não está no Environment | print das configurações do Environment (2026-11-28) | **decisão humana**: criar ou confirmar o secret, distinto da chave de artefato |
| P4-06 | médio | Morte do processo no meio da escrita só era testada na trilha (`audit_store`), não no log de verificação nem na fila de jobs | `tests/test_audit_store_durability.py` | **corrigido**: `tests/test_recovery_process_kill.py` |
| P4-07 | baixo | Schemathesis instável quando o fuzzing gera 413 | falhas em #647 e #638; correção na #645 (base desatualizada) | **decisão humana**: revisar e integrar a #645 |
| P4-08 | baixo | Atualizações pendentes do Dependabot (#637 a #641) | lista de PRs | **decisão humana**, PR a PR. A #641 (`transformers` 5.24) afeta o produto, não os pins históricos |
| P4-09 | baixo | A imagem Docker não tem proveniência nem SBOM atestados (as distribuições Python têm SLSA) | `docker.yml` sem `attest` | proposta de melhoria. Exige `attestations: write` num workflow de push, ou seja, mudança de permissão a autorizar |
| P4-10 | informativo | `mypy --strict` tem cerca de 117 erros no job não bloqueante | `typecheck-strict` | catraca gradual por módulo, como já é feito com `evidence` |
| P4-11 | informativo | Não houve revisão humana independente da P3 | relatórios da P3 | só o mantenedor pode obtê-la |

## 5. Plano de correção

**Feito nesta PR (seguro, só testes e documentação):**
- **P4-06:** dois testes de processo morto com SIGKILL, três rodadas cada:
  - log de verificação: o log continua íntegro (`verify_log()` válido), aceita um novo evento e devolve um recibo que verifica offline, inclusive na repetição idempotente;
  - fila de jobs: `integrity_check` ok, nenhum job fica preso em `RUNNING` depois de `reclaim_expired`, e um job devolvido à fila pode ser concluído.
- Estáveis em cinco repetições locais.
- Este diagnóstico.

**Próximo passo, mudança estrutural que pede aprovação (P4-01, P4-02, P4-03):**
1. Trazer `reproducibility/phase1b-dev-2026-11-07/` da branch preservada para a `main`, com os mesmos bytes e SHA-256 conferidos.
2. Obter o SHA-256 oficial do wheel `torch-2.7.1+cpu` (cp312, linux x86_64) e preencher o `PENDING` num arquivo novo, sem reescrever o registro histórico.
3. Criar `requirements-phase1b-inference.txt` com hashes:
   - as versões exatas do ambiente histórico, inclusive as transitivas;
   - `cryptography` 50.0.2, já decidida para os jobs com chave;
   - o PyTorch CPU com hash.
4. Nos jobs `shard` do minimal e do full, trocar a instalação por `--require-hashes --only-binary :all:`, mantendo o índice CPU do PyTorch.
5. Teste de contrato: todo job que recebe chave instala só de lock com hashes.
6. Validar com uma nova execução minimal autorizada. O minimal não calcula métricas, então a troca não toca resultado científico.

Efeito: fecha a lacuna de cadeia de suprimentos no job que decifra o DEV e torna a inferência reprodutível de fato. Hoje as dependências transitivas flutuam [HIPÓTESE: a execução #11 pode ter instalado versões transitivas diferentes das históricas; os logs do shard dizem quais].

**Testes de falha propostos (próximas PRs):**
- **Repetição de um shard:** reexecutar só o job que falhou numa execução DEV não pode sobrescrever nem duplicar artefatos (`overwrite: false`). O teste é de contrato sobre o workflow.
- **Interrupção entre `plan` e `shard`:** artefatos expirados (1 dia) devem levar a uma recusa clara, não a uma agregação parcial. Já é coberto por `incomplete_model_count`; falta o teste de contrato.
- **Disco cheio** no log de verificação em modo `local` e no `JobStore`. O modo `required` já é testado.

## 6. Bloqueio desta revisão

O host `download.pytorch.org` foi liberado na rede do ambiente de trabalho, com aprovação do mantenedor. A leitura do índice, porém, foi recusada pelo controle de permissões da sessão, e a recusa não foi contornada.

Alternativas:
- **(a)** o mantenedor autoriza essa leitura na sessão;
- **(b)** um passo de CI imprime o SHA-256 do wheel baixado no runner do GitHub, e o valor entra no lock por revisão.

## 7. Decisões humanas pendentes

1. Aprovar a estratégia da seção 5, que muda os workflows DEV de forma estrutural.
2. Escolher (a) ou (b) da seção 6 para o hash do PyTorch.
3. Manter ou revisitar os pins históricos com alertas (P4-04).
4. Configurar a chave gold (P4-05) antes de qualquer execução DEV completa.
5. Integrar ou não a #645 e as PRs do Dependabot (P4-07, P4-08).
6. Proveniência da imagem Docker (P4-09), que muda permissões de workflow.
