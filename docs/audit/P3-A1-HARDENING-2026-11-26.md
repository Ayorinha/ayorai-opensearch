# P3/A1 — Auditoria adversarial e correções (2026-11-26)

Revisão por ferramenta automatizada, publicada pelo mantenedor.

| item | valor |
|---|---|
| `main` | `3932d171fa5b4554684ec247555d3eaa8081e568` |
| Base desta branch | #636 em `13d6ac81ee6987fb7497cf0a38088f3df0e02f6d`, que contém a #635 (`d22cb05387a7acccd8e63ec0ced71b44062c9afc`) |
| Branch | `fix/p3-a1-hardening` (PR Draft com base `main`) |
| Natureza | revisão de código, testes sintéticos e correções. Nenhuma execução DEV/TEST, nenhum dispatch de workflow, nenhum acesso a secrets |

Rótulos:
- **[FATO]**: verificado no código, por execução ou no GitHub;
- **[HIPÓTESE]**: não verificável com o acesso desta revisão.

## 1. Por que uma PR com base `main`

A #636 tem base na branch da #635. O `ci.yml` só dispara para pull requests com base `main`, por isso a #636 nunca teve CI [FATO]. Esta branch contém #635, #636 e as correções abaixo, numa PR Draft com base `main`, para que a CI rode no código completo.

As #635 e #636 continuam abertas. O mantenedor decide se esta PR as substitui.

## 2. Auditoria adversarial

**Ataques executados (sintéticos), todos recusados:**
- alteração de 1 bit no ciphertext, na tag GCM ou no nonce;
- envelope de outro papel, execução, revisão, commit ou shard;
- repetição de nonce em 2.000 cifragens;
- chave ausente, curta ou fora do Base64;
- gold no score;
- arquivo de inferência alterado entre jobs;
- junção de caches de execuções diferentes ou com cobertura diferente;
- manifesto adulterado;
- envelope gold disfarçado de cache de score.

[FATO] Esses casos estão em `tests/test_phase1b_adversarial.py`.

**Workflows [FATO]:**
- só `workflow_dispatch`;
- `contents: read` e `actions: read`;
- ações fixadas por SHA;
- entradas passadas por `env` e validadas (sem injeção de shell);
- o job `shard`, que roda os modelos, nunca recebe a chave gold;
- modelos com `revision` fixada, `local_files_only` e `trust_remote_code=False`. Os alertas B615 do Bandit são falsos positivos e já existiam na `main`.

**Vulnerabilidade comprovada que expõe gold ou secret:** nenhuma [FATO].

## 3. Achados e correções

| id | gravidade | achado | correção nesta branch |
|---|---|---|---|
| S-01 | alto | teste da #636 fora do `ruff format`: a CI reprovaria | reformatado (`bfb3a834`) |
| S-05 | médio | a re-agregação reenviava os caches gold e score com 30 dias novos; a vida dos rótulos podia passar de 30 dias (até 7 a mais, a janela dos shards de origem) | os caches reenviados herdam o que resta da janela de 30 dias da execução de origem; origem expirada é recusada (`ecefbdce`) |
| S-06 | médio | a origem de re-agregação e experimento era aceita só por `head_branch == "main"`, o que uma tag chamada `main` também satisfaz | exige origem neste repositório e commit contido na `main` (`compare/<sha>...main` igual a `identical` ou `ahead`) (`ecefbdce`) |
| S-08 | médio | caminhos de recusa sem teste; cobertura em processo baixa | 51 testes adversariais e 6 de CLI em processo. Cobertura em processo: `inference_artifact` 70%→89%, `manifest_artifact` 59%→87%, `prepare_dev_artifacts` 56%→87%, `encrypt_artifact` 49%→66%. `aggregate_dev` (42%) e `score_cache` (64%) têm o CLI coberto só por testes em subprocesso |
| S-12 | baixo | `shard_id` sem formato, usado em nomes de artefato e caminhos | só `dev-NNNN`, sem duplicatas, no validador do manifesto e no gerador da matriz (`bbcd61b6`) |
| S-13 | baixo | campo parecido com rótulo (`label`) no registro de score era descartado em silêncio | recusado; o registro gold também exige exatamente os seus 3 campos (`8abbd144`) |
| S-15 | baixo | no job `plan`, a chave gold estava no passo que também montava o manifesto e cifrava a inferência | passo dividido; só a separação dos rótulos (e a checagem das chaves) recebe a chave gold (`0e15281f`) |
| S-16 | baixo | `SCORE_SCHEMA_VERSION_V2..V4` guardavam as versões v4..v6 | renomeadas para `SCORE_CACHE_SCHEMA_V3..V6` (`8abbd144`) |
| S-07 | médio | os jobs com as chaves instalavam `cryptography` 46.0.3 (7 alertas publicados, corrigidos até a 50.0.0, inclusive o OpenSSL embutido nas wheels), enquanto o produto e os testes usam a 50.x. O job `plan`, que agora tem a chave gold, instalava os pins históricos (`pyarrow` 21.0.0, PYSEC-2026-113) sem conferência de hash | `plan`, `aggregate`, re-agregação e experimento instalam `requirements-phase1b-protected.txt` com `--require-hashes --only-binary :all:` (`cryptography` 50.0.2, `pyarrow` 23.0.1; `pip-audit` sem alertas; instalação testada em Python 3.12). O job de inferência mantém os pins históricos, pela reprodução numérica, e recebe `cryptography` 50.0.2 (`d25bd828`). Ver `docs/security/HISTORICAL-PINS.md` |
| S-04 | médio | colisão de identidade no DEV aborta a execução sem dizer o tamanho do problema | o construtor do manifesto informa só contagens: identidades repetidas, linhas extras, conflitos de rótulo. Nenhum conteúdo aparece (`91691caa`) |
| S-19 | médio | o workflow minimal pedia a chave gold e gerava o cache gold cifrado no runner. O cache era apagado na limpeza, sem upload nem consumidor, porque o `aggregate` minimal não calcula qualidade (achado de revisão na PR #644) | `prepare_dev_artifacts.py --discard-gold-labels` grava só a entrada de inferência, sem ler a chave gold. O minimal não referencia mais a chave nem o artefato gold, e os testes de contrato garantem isso |
| T-1/T-2 | médio | a auditoria de `9321fdc2` mostrou que os contratos não detectavam exposição indireta de secrets (`toJSON(secrets)`, `secrets[format(...)]`) nem download de artefatos de outra execução | `tests/test_phase1b_workflow_secrets.py` analisa cada expressão `${{ }}`. Aceita só `secrets.NOME` de uma lista permitida por workflow (minimal: chave de artefato e `HF_TOKEN`) e recusa `secrets: inherit`. Download de outra execução só na re-agregação e no experimento, e só pela entrada verificada. As 6 mutações de regressão agora são detectadas (antes, 3 escapavam) |
| T-3, E-1, E-2 | baixo | faltavam testes do modo descarte; havia limpeza vestigial de gold no minimal; `gold_rows` era montado sem uso | testes de rótulo inválido, digest e destino sem chave no descarte. Limpeza removida do minimal e o teste ajustado. Linhas gold montadas só quando são mantidas |
| S-14 | baixo | gold e score decifram com o próprio metadado como AAD | **sem mudança.** O AAD é autenticado pelo GCM, e os campos são comparados antes da junção (`aggregate_dev.py`, `score_cache.main`) com o manifesto e entre si. Equivale a passar o AAD esperado |

## 4. O que depende do mantenedor

| id | gravidade | pendência | por que não foi resolvida aqui |
|---|---|---|---|
| S-02 | alto | a guarda `github.ref == 'refs/heads/main'` está no próprio workflow; a barreira real é a política do Environment `international-benchmark-maintainer-approval` | configuração do GitHub, que exige acesso de administrador. Verificar: só a branch `main` (sem tags), aprovador obrigatório, dois secrets distintos [HIPÓTESE até a confirmação] |
| S-03 | alto | a `main` atual roda o desenho anterior à P3 (manifesto em claro, gold junto com score) | **não disparar workflows phase1b na `main` até a P3 entrar** |
| S-04 | médio | só o dado real diz se há colisões | o DEV é restrito no Hugging Face e não foi baixado nesta revisão. A primeira execução autorizada informa as contagens antes de usar qualquer chave. Se houver conflitos de rótulo, a política é decisão metodológica |
| S-07 (residual) | baixo | o PyTorch do job de inferência continua por versão, sem hash | `download.pytorch.org` estava bloqueado pela rede deste ambiente |
| S-09 | médio | a retenção de 30 dias foi registrada como "delegada" em comentário de ferramenta | registrada como **proposta DEC-033** em `docs/DECISIONS-PENDING.md`; aguarda a decisão do mantenedor |
| S-10 | médio | a #642 cita HEADs antigos | atualizar ou fechar a #642; este documento a substitui tecnicamente |
| S-11 | médio | não há revisão humana independente | só o mantenedor pode obtê-la |

## 5. Validação local

Ambiente: Python 3.13.18, Ruff 0.17.5.

| verificação | resultado |
|---|---|
| suíte completa | ver a PR (atualizado a cada push) [FATO] |
| testes phase1b | 321 aprovados (antes: 255) [FATO] |
| lock protegido em Python 3.12 limpo (`--require-hashes`) | instalação ok; 101 testes phase1b ok nesse ambiente [FATO] |
| Ruff check e format, mypy, Bandit (`src/`) | limpos [FATO] |
| Golden smoke-v0, v0, v0.1 | `969ec61a…`, `21abb816…`, `1fd6fdb7…`: inalterados [FATO] |
| arquivos protegidos (Judge, Golden, `evals/`, `rules/`, ADRs, decisões, `configs/`) | nenhum alterado [FATO] |
| actionlint | **não executado localmente**: a instalação foi bloqueada pelo controle de permissões do ambiente. Fica a cargo do job `workflow-lint` da CI |

Testes sintéticos não são validação científica. Nenhum resultado DEV/TEST foi produzido.
