# Pins históricos com alertas conhecidos (P3-1)

**Decisão registrada em 2026-11-21:** os pins de `requirements-benchmark-pilot.txt` ficam como estão e isolados. Esta página registra o porquê, o isolamento verificado e o critério para revisitar a decisão.

## O que é

`requirements-benchmark-pilot.txt` fixa as versões usadas nos experimentos históricos da fase 1b, cujos hashes estão registrados em `reproducibility/phase1b-dev-2026-11-07/`. Três pins têm alertas no OSV (`pip-audit --vulnerability-service osv`, 2026-11-21):

| Pacote | Versão | Alertas | Primeira versão corrigida |
|---|---|---|---|
| `transformers` | 4.55.4 | PYSEC-2025-214 a 218, PYSEC-2026-2288, 2289, 2290, 3929, 4174 | 5.x (alguns sem correção publicada) |
| `pyarrow` | 21.0.0 | PYSEC-2026-113 | 23.0.1 |
| `accelerate` | 1.10.1 | PYSEC-2026-3804 | sem correção publicada |

## Por que não atualizar

As correções exigem trocar de versão maior (`transformers` 5.x, `pyarrow` 23). Isso muda o resultado numérico dos experimentos e quebra a reprodução de um registro já publicado com hash. Atualizar exigiria um novo experimento, não uma correção do antigo.

## Isolamento verificado

- **Fora do produto:** nenhum desses pacotes está em `docker/requirements.lock`, na imagem do serviço ou nas dependências instaladas pelo CI de PRs. O `security.yml` audita o ambiente do produto com `pip-audit --strict`, e esse ambiente não tem alertas.
- **Só por disparo manual:** o arquivo é instalado apenas por três workflows com `workflow_dispatch` e `permissions: contents: read`:
  - `baseline-throughput-pilot.yml`;
  - `phase1b-dev-full.yml`;
  - `phase1b-dev-minimal.yml`.

  Nenhum roda em `push`, `pull_request` ou agenda. Uma PR de terceiros não os aciona.
- **Entrada fixa:** modelo e conjunto de dados são baixados por revisão imutável (`--model-revision` e `--dataset-revision` vindos do manifesto). Os alertas de `transformers` e `accelerate` dependem, em geral, de carregar arquivo de modelo ou checkpoint não confiável; aqui a revisão é fixa e conferida.
- **Segredos expostos ao job:** `HF_TOKEN` e `PHASE1B_ARTIFACT_ENCRYPTION_KEY`. É o risco residual: um pacote vulnerável explorado durante a execução manual poderia ler esses segredos.

## Regras

1. Não usar `requirements-benchmark-pilot.txt` em workflow com gatilho automático, nem no produto.
2. Antes de disparar um dos três workflows, conferir que o manifesto de revisões é o registrado.
3. Usar um `HF_TOKEN` só de leitura e exclusivo desses experimentos.
4. Rever esta decisão quando:
   - um alerta passar a ser explorável com entrada fixa;
   - um novo experimento for planejado, que já deve nascer com versões atuais;
   - ou os segredos expostos mudarem.

## Revisão de 2026-11-26 (P3/A1): segredos expostos mudaram

A P3/A1 acrescentou a chave `PHASE1B_GOLD_LABEL_ENCRYPTION_KEY` ao job `plan` do workflow full, que instalava estes pins. O workflow minimal não recebe essa chave (S-19). É o terceiro gatilho de revisão da regra 4.

**Decisão técnica aplicada:** os jobs que **não rodam inferência** passam a instalar só `requirements-phase1b-protected.txt`:
- `plan` e `aggregate` (full e minimal);
- re-agregação;
- experimento de cache.

**Características do novo lock:**
- travado por SHA-256, instalado com `--require-hashes --only-binary :all:`;
- `cryptography` 50.0.2, a mesma linha 50.x do produto (`pyproject.toml`);
- `pyarrow` 23.0.1, com o PYSEC-2026-113 corrigido;
- `numpy` 2.2.6 e `huggingface-hub` 0.34.4;
- `pip-audit` sem alertas.

**Job de inferência (`shard`):**
- continua com `requirements-benchmark-pilot.txt`, para preservar a reprodução numérica dos modelos;
- não recebe a chave gold;
- só troca `cryptography` 46.0.3 por 50.0.2. Os alertas da 46.0.3 incluem a cópia do OpenSSL embutida nas wheels (GHSA-537c-gmf6-5ccf). `cryptography` não afeta os escores.
- O PyTorch continua vindo do índice oficial de CPU, por versão. Não foi possível gerar hash dele neste ambiente, porque `download.pytorch.org` estava bloqueado pela rede. Fica como risco residual.

**Testes:** `tests/test_phase1b_protected_dependencies.py`.

## Revisão de 2026-11-28 (P4-01): inferência travada por hash

**Registro histórico na `main`:** `reproducibility/phase1b-dev-2026-11-07/` foi restaurado byte a byte da branch preservada `repro/phase1b-dev-env-2026-11-12` (head `0edc35b9`). Os SHA-256 conferem com `docs/audit/PR-INVENTORY-2026-11-20.md`. A referência do início desta página volta a existir.

**Job de inferência (`shard`):**
- instala `requirements-phase1b-torch-cpu.txt` (índice oficial de CPU) e `requirements-phase1b-inference.txt` (PyPI), os dois com `--require-hashes --only-binary :all: --no-deps`, seguidos de `pip check`;
- as versões são as do ambiente histórico, inclusive as transitivas, que antes não tinham versão fixada; só `cryptography` vai para 50.0.2;
- o hash do `torch-2.7.1+cpu` (`8f8b3cfc…60947`) foi lido do wheel oficial baixado num runner do GitHub e revisado antes de ser fixado; o job de CI `phase1b-inference-lock` reinstala os dois locks a cada PR.

**nltk:** o `nltk` 3.9.4 tem 31 alertas altos ou críticos, corrigidos na 3.10.4. A 3.10.4, porém, segmenta de forma diferente (`docs/audit/P4-NLTK-EQUIVALENCE-2026-11-28.md`). Por isso, o job deixa de instalar o nltk e usa a segmentação da 3.9.4 embutida em `scripts/benchmarks/phase1b/vendor_nltk/`:
- o pacote embutido tem só o código de `sent_tokenize` e `word_tokenize`, com a licença Apache-2.0;
- o resultado é idêntico ao do nltk 3.9.4 oficial em 25.185 textos;
- a CI confere a cada PR o resultado contra a referência fixada;
- `click` e `joblib`, que só o nltk usava, saíram do lock.

**Pacotes sem uso no job:**
- O `pyarrow` 21.0.0 (GHSA-rgxp-2hwp-jwgg, alto) e o `pandas`, com `python-dateutil`, `pytz` e `tzdata`, também saíram do lock. O job lê só o JSONL decifrado e nunca os importa; um teste de contrato garante isso.
- O `setuptools` vai de 78.1.0 para 84.2.1, com 5 alertas corrigidos. Ele é só requisito de instalação do torch.
- Nenhum desses pacotes participa da tokenização ou dos escores.

**Registro histórico:** na `main` fica o `MANIFEST.json`. Os três locks históricos, que fixam o nltk 3.9.4 e a cryptography 46.0.3, continuam na branch preservada, referenciados por SHA-256 em `reproducibility/phase1b-dev-2026-11-07/README.md`.

**Testes:** `tests/test_phase1b_protected_dependencies.py` (hash em todo pacote, igualdade com o ambiente histórico, instalação só por lock com hash em todo job que recebe chave).
