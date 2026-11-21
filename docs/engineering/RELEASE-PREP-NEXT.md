# Preparação da próxima release (proposta: v0.9.0)

**Estado:** preparação técnica concluída em 2026-11-21 sobre a `main` @ `a91da0f`. **Nenhuma tag, release, notas oficiais (`docs/release/`) nem DOI foram criados:** isso é decisão e ato do mantenedor (AGENTS.md §§1 e 4). Este documento reúne o que entra, a compatibilidade, as evidências e os passos restantes.

## 1. Número da versão

Desde a v0.8.0 (tag `92ea5eb`, 2026-11-13) entraram mais de 70 PRs na `main`. Há rotas novas (`POST /v2/audit`, `GET /ready`, `GET /metrics`) e mudanças de comportamento no `/v1/check` (ver §3). Pela convenção do projeto (0.x, com mudanças de comportamento documentadas), **propõe-se v0.9.0**. A decisão é do mantenedor.

## 2. O que entra

Resumo do `[Unreleased]` do `CHANGELOG.md`, que é a fonte completa:

| Área | Principais mudanças |
|---|---|
| Verificação | Todo documento relevante chega à adjudicação (document-check-3); cópias e quase-duplicatas não contam como fontes independentes (document-check-4); texto do cliente não chega a `verified` (document-check-5); detector de stance por regras v9 a v13; ADR-011 fixa a família de regras do Judge por rota |
| API | `POST /v2/audit`; rastro `r2-v4` com `adjudication_sha256`; erros de provider sem URL interna; limite de requisições pesadas (503), opcionalmente por host; `GET /ready` e `GET /metrics` |
| Trilha de auditoria | Dono por rastro, `r2-v3`, HMAC externo exigível, rotação de chave, retenção, cadeia de sequência com checkpoint externo, transação desfeita em erro |
| RGC (sem resultado) | Runner `rgc-eval/0.14.0`: snapshots E5, interpretador isolado, IC e teste de H1 por componente, IC de kappa por componente (DEC-022), texto superado por retificação excluído |
| AYORAI-PT-NLI | Integração de inferência EuroBERT com falha fechada (ADR-008); sem modelo treinado, sem ligação com a API |
| Operação | Compose endurecido; métricas, alertas, SLOs propostos; homologação local; medição de capacidade |

## 3. Compatibilidade: o que muda para quem já usa

| Mudança | Efeito para o cliente |
|---|---|
| `/v1/check` limitado a `supported` (document-check-5) | Texto enviado pelo cliente nunca chega a `verified`; só `server_retrieved` pode |
| Independência por conteúdo normalizado (document-check-4) | Documentos copiados contam como uma fonte: resultados antes `supported` podem virar `partially_supported` |
| Todos os documentos relevantes adjudicados (document-check-3) | Contradições antes ignoradas passam a aparecer: alguns `verified`/`supported` viram `conflicting` ou `refuted` |
| Detector v13 | Escala sem moeda é lida ("1,2 bilhão"); muda um caso do Golden v0.1 (11/30, referência aprovada) |
| Rastros `r2-v3`/`r2-v4` com dono | Rastro de outra chave devolve 404 |
| Rotas novas | Aditivas; `/ready` e `/metrics` ficam fora do OpenAPI |

## 4. Evidências já registradas

| Gate | Evidência | Estado |
|---|---|---|
| CI na `main` | CI, Security, CodeQL, API Contract, Schemathesis, Dependency Review | Verde em cada merge deste ciclo |
| Testes | `pytest` no CI em Python 3.11, 3.12 e 3.13 | Verde; localmente 2.629 passaram, sem `xfail` |
| Golden | `scripts/reproduce.py` | v0 7/30 e v0.1 11/30, referências aprovadas; Judge 6/6 |
| Segurança estática | Bandit, pip-audit, Grype, CodeQL | Sem achados no ambiente do produto |
| Build reproduzível no CI | Dupla build idêntica no job `build-distributions` | Passa em cada execução |
| **Reprodução independente** | §5 abaixo | Confirmada para `main` @ `f1c7621` |
| Proveniência SLSA | Atestações assinadas pelo CI e registradas no Rekor | Existem para os digests de §5 |
| Homologação local | [audit/HOMOLOGATION-LOCAL-2026-11-21.md](../audit/HOMOLOGATION-LOCAL-2026-11-21.md) | 16/16, reinício, restauração, detecção de adulteração |
| Capacidade | [benchmarks/CAPACITY-2026-11-21.md](../benchmarks/CAPACITY-2026-11-21.md) | Medida localmente |
| Observabilidade | [observability/SLO-AND-ALERTS.md](../observability/SLO-AND-ALERTS.md) | Métricas, alertas e SLOs propostos |

## 5. Reprodução independente da distribuição (2026-11-21)

O objetivo foi confirmar que os artefatos do CI podem ser reconstruídos fora do CI, byte a byte.

1. **Alvo:** `main` @ `f1c76214e311341b330a6edac1504dff152b99eb`, execução de CI `44937661768`, job `build-distributions`, `SOURCE_DATE_EPOCH=1795287001`.
2. **Reconstrução:** checkout limpo do mesmo commit, em outra máquina; Python 3.12; `python -m build --sdist --wheel` com o mesmo `SOURCE_DATE_EPOCH` (setuptools 84.2.1 resolvido pelo isolamento de build); sdist normalizado com `scripts/normalize_sdist.py`.
3. **Resultado:** SHA-256 idênticos aos registrados no log do CI.

   | Artefato | SHA-256 (CI e reconstrução) |
   |---|---|
   | `ayorai_opensearch-0.8.0-py3-none-any.whl` | `cee8057c89916acdf4797ac90ffefb3d33b41d0ae9bd73da80a00e30d5fe613f` |
   | `ayorai_opensearch-0.8.0.tar.gz` | `376b1529cc04fb1d21142fa3f1891fe9096ad44c7188b52de3f734ff0399c4c3` |

4. **Proveniência:** a API do GitHub tem uma atestação in-toto de build provenance para cada um dos dois digests, assinada no CI (Sigstore público) e registrada no Rekor. A verificação criptográfica local com `gh attestation verify` não completou porque o ambiente usado não alcança os servidores do Sigstore. Ela deve ser repetida pelo mantenedor ou por quem consumir os artefatos:

```bash
gh attestation verify ayorai_opensearch-<versão>-py3-none-any.whl \
  --repo Ayorinha/ayorai-opensearch \
  --signer-workflow Ayorinha/ayorai-opensearch/.github/workflows/ci.yml
```

Para reconstruir e comparar qualquer versão:

```bash
git checkout <commit da tag>
export SOURCE_DATE_EPOCH="$(git log -1 --format=%ct)"
python -m build --sdist --wheel --outdir raw
python scripts/normalize_sdist.py raw/*.tar.gz out/$(basename raw/*.tar.gz)
cp raw/*.whl out/ && sha256sum out/*
```

## 6. Passos para publicar (mantenedor)

1. Decidir o número da versão (§1).
2. Rever com uma pessoa as PRs integradas sem revisão humana independente (`docs/STATUS.md`).
3. PR de versão: `pyproject.toml`, `src/ayorai_attractor/__init__.py`, `CITATION.cff`, cabeçalho datado do `CHANGELOG.md` e notas em `docs/release/v<versão>.md`, que é arquivo protegido e escrito ou aprovado pelo mantenedor.
4. Depois do merge e do CI verde no commit da versão: criar a tag assinada e a GitHub Release com os artefatos do job `build-distributions` e o `SHA256SUMS.txt`.
5. Verificar as atestações (§5) e anexar o resultado.
6. Registrar o DOI de versão no Zenodo e atualizar `CITATION.cff` e o `STATUS.md`.

## 7. O que esta release não afirma

- Nenhuma acurácia validada: o Golden está abaixo do baseline de classe majoritária e o RGC não está congelado.
- Nenhuma implantação de produção ou homologação real.
- Nenhuma certificação ou conformidade legal.
- O AYORAI-PT-NLI não tem modelo treinado.
