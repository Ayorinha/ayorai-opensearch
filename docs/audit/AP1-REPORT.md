# AP1 — Consolidação do AYORAI ATTRACTOR

| item | valor |
|---|---|
| Data da auditoria | 2026-11-22 |
| SHA de referência da `main` (base da AP1) | `0acc7dc9540048d8340347655a62d7fa7b156741` |
| Branch de trabalho | `ap1-consolidation` (publicada no GitHub) |
| Commit da correção funcional P2 | `5c4448f6` |
| Commit da validação final de código/documentação | `e8b5a650b7795f131d8f5649a0cffaf0e18079f7` |
| PR de integração | [#632](https://github.com/Ayorinha/ayorai-opensearch/pull/632), aberta contra `main` |
| Último HEAD com CI integral concluído | `b57392cbfc65b2c8ce6241494af8e45e579a8b54` |
| Estado de integração | PR aberta; ainda não mesclada |

**Escopo deste relatório:** consolidação técnica AP1 e registro de sua revisão/integração. Não houve release, tag ou DOI nesta etapa. O SHA de referência acima identifica a `main` usada como base; os SHAs de validação e da PR identificam commits posteriores distintos.

**Normas lidas:**
- `AGENTS.md`;
- ADR-002, 003, 004, 005, 006, 009 (com as emendas de 2026-10-12 e 2026-10-17) e 011.

**Artefatos protegidos** (AGENTS.md §4):
- `rules/`, `src/ayorai_attractor/verification/judge2/`, `evals/` e ADRs aceitas;
- foram **auditados, não alterados**;
- os achados que exigiriam alterá-los estão em "Pendências".

## 1. Resumo

| escopo | resultado |
|---|---|
| Judge 1.x (`verification/judge.py`, `clusters.py`) | Conforme ADR-002 §1–§3 e ADR-006 §1–§2. Sem falha. |
| Judge 2.0 (`judge2/`, `rules/judge-2.0.0.json`) | Conforme ADR-009 nas partes verificadas (G, E, A, R, K, I1, saída canônica). Sem falha. Protegido. |
| Contratos `r1-a` / `r2-a` (`POST /v1/verify`) | Conformes à ADR-009 §15. Sem falha. |
| Rotas (ADR-011) | 1 divergência documental: `/v1/fields` não usa nenhum Judge. Fixada em teste; a ADR protegida não foi alterada. |
| Detector numérico P1–P9 | 1 falha corrigida (P2 incompleto); 1 melhoria bloqueada por alterar o Golden (ms × segundos); P9 e duas limitações seguem pendentes. |
| Testes normativos T1–T11 (ADR-009 §12) | Todos cobertos; mapeamento na seção 4. |

## 2. Achados

### A1 — P2 incompleto: valor do ano afirmado não ficava ligado ao atributo (corrigido)

- **Classificação:** [FATO VERIFICADO], contradição perdida.
- **Sintoma:** na v15, "A receita da Vértice foi de 40 milhões em 2024." contra "A receita da Vértice foi de 40 milhões em 2023 e de 55 milhões em 2024." gerava abstenção. O esperado é `refuted`: o valor de 2024 é 55.
- **Causa:**
  - `_keep_claimed_period` apagava só os números da oração do outro ano.
  - O valor restante (55) ficava a mais de 8 tokens de "receita".
  - `_attribute` devolvia `unknown`, e o fato não era comparado.
- **Correção** (`verification/stance.py`, `_keep_claimed_period`):
  - a oração do outro ano é descartada;
  - se ela abre a frase, as palavras antes do primeiro valor que não é ano ficam (sujeito e atributo), sem o ano dela;
  - assim, "Em 2023, a receita foi de 40 milhões; em 2024, de 55 milhões." também preserva "a receita".
- **Versão:** o detector sobe de 15 para 16. Os asserts de versão nos testes passam a aceitar "16".
- **Testes:**
  - `test_stance_unanchored_year.py::test_a_value_of_another_year_in_the_same_sentence_does_not_support` deixa de ser `xfail` estrito e passa a exigir `refuted`;
  - `test_stance_cross_domain.py::test_p2_value_of_another_year_does_not_support` passa a exigir `refuted`;
  - novos: `test_ap1_claimed_year_value_is_bound_to_the_subject` (3 casos) e `test_ap1_dropped_clause_keeps_no_year_of_its_own`;
  - os 4 testes afetados falham no código anterior e passam no novo.

### A2 — `/v1/fields` não usa nenhum Judge; a tabela do ADR-011 diz o contrário (documental; ADR protegida)

- **Classificação:** [FATO VERIFICADO].
- **Divergência:**
  - o ADR-011 lista `/v1/fields` com "ADR-002 (1.x), por `document_check`" e o vocabulário `verified`/`supported`/…;
  - no código, `app.fields` chama `field_check.check_fields`, que não importa `judge`, `judge2` nem `document_check`;
  - a rota devolve `conforme`/`divergente`/`ambiguo`/`ausente`/`invalido`.
- **Impacto:** nenhum no comportamento. O ADR-011 está aceito e é protegido, por isso não foi alterado.
- **Testes** (`tests/test_judge_family_per_route.py`):
  - `test_fields_route_uses_no_judge` fixa que `field_check` não importa nenhum Judge;
  - `test_fields_outcome_vocabulary_is_closed` fixa o vocabulário da rota;
  - o comentário que repetia a afirmação errada foi corrigido.
- **Pendência:** emenda datada do ADR-011, a decidir pelo mantenedor (seção 6).

### A3 — Melhoria P1 bloqueada: "ms" e "segundos" não se comparam (não aplicada)

- **Classificação:** [FATO VERIFICADO].
- **Sintoma:** milissegundos têm a unidade própria `ms`, que não se compara com a família de tempo. "50 ms" contra "50 segundos" gera abstenção, não refutação.
- **Teste da correção:** tratar `ms` como `duration:seconds:0.001` foi implementado e medido, depois **revertido**, porque altera os hashes semânticos congelados do Golden:

  | suíte | hash atual | hash com a mudança | acertos |
  |---|---|---|---|
  | Golden v0 | `21abb816…` | `5d47bf56…` | 7/30 → 8/30 (c02) |
  | Golden v0.1 | `1fd6fdb7…` | `8c77356c…` | 11/30 → 15/30 (c02, r01, r02, ch01) |
  | smoke-v0 | inalterado | inalterado | — |

  Todos os casos alterados passam de errado para certo; nenhum piora.
- **Pendência:** a mudança exige decisão do mantenedor e atualização de referência registrada, como foi feito na v13 em `docs/eval/SEMANTIC-DIGEST-V1-REFERENCE.md`.

### A4 — Contratos e rotas: verificações sem falha

[FATO VERIFICADO], por sonda e teste:

- **Despacho de `schema_version`:**
  - valores desconhecidos ou variantes (`r3-z`, `""`, `R2-A`, `r2-a ` com espaço) recebem 422;
  - nenhum valor inválido cai silenciosamente no caminho `r1-a`.
- **`r1-a`:** `UNVERIFIED` vira `abstain/no_answer` com `verdict=null` (ADR-002 §5). Entradas inválidas do Judge 1.x viram 422 com código (`DUPLICATE_ID`, `DANGLING_REFERENCE`, `DUPLICATE_STANCE`).
- **`r2-a`:**
  - `UNVERIFIED` fica `DECIDED` com `response_policy=null`;
  - `ABSTAINED` devolve `response_policy` separado do veredito (ADR-009 §15);
  - o recibo de auditoria fica fora de `result`.
- **`/v1/check` e `/v2/audit`:**
  - usam o Judge 1.x via `document_check`;
  - `UNVERIFIED` vira abstenção;
  - texto enviado pelo cliente nunca chega a `verified`.
- **Observação** [INFERÊNCIA]: em `app.verify`, o ramo `if not request.claims` do `r1-a` é inalcançável, porque `VerificationRequest.claims` tem `min_length=1`. Não foi removido: o contrato de fio `r1-a` é congelado.

## 3. Judge 1.x e Judge 2.0 — conformidade

[FATO VERIFICADO], por leitura de código.

**Judge 1.x (ADR-002, ADR-006):**
- a tabela S/C/P bate linha a linha com ADR-002 §1;
- P é calculado só sobre a evidência de suporte e exige `provenance_complete`, offsets válidos, trecho não vazio e `origin_id` ou URL canônica;
- clusters transitivos por URL canônica, `origin_id`, `source_id`, hash de conteúdo e cadeia de citação;
- a precedência global segue ADR-002 §4.

**Judge 2.0 (ADR-009):**
- regras A1–A4 e K1–K5 lidas do arquivo versionado;
- `rules_sha256` fixado (`493cce66…9efc`);
- robustez R pelo lado decisivo; `CONFLICTING` usa o mínimo dos lados;
- K usa a menor robustez dos átomos do lado da regra aplicada;
- portões G1/G2 e admissibilidade E1–E3 com motivo de rejeição registrado;
- I1 em todos os estados;
- saída canônica RFC 8785, com `output_sha256` calculado sem o próprio campo.

## 4. Testes normativos T1–T11 (ADR-009 §12)

| teste | onde está coberto |
|---|---|
| T1 | `tests/verification/test_judge2_adjudication.py::test_t1_*` |
| T2 | `test_judge2_adjudication.py::test_t2_composite_truth_table_exhaustive_for_multisets_up_to_four_atoms` |
| T3 | `test_judge2_adjudication.py::test_t3_*` |
| T4 | `test_judge2_adjudication.py::test_t4_*` |
| T5 | `test_judge2_adjudication.py::test_t5_*` |
| T6 | `test_judge2_adjudication.py::test_t6_*` (3 testes) e `test_judge2_property_invariants.py` |
| T7 | `test_judge2_canonical_output.py::test_t7_*` e `test_three_fixed_output_sha256_vectors` |
| T8 | `test_judge2_canonical_output.py::test_t8_*` |
| T9 | `test_judge2_canonical_output.py::test_t9_*` |
| T10 | `tests/test_legacy_baseline.py` (baseline legado, manifesto e digests semânticos das 3 suítes) e job `golden-regression` do CI |
| T11 | `test_judge2_gates.py::test_t11_*` (cada código G1 e cada motivo de rejeição E) |

- A tabela de verdade publicada é gerada do arquivo de regras: `test_judge2_truth_table_generation.py`.
- A rastreabilidade tem paridade testada: `test_judge2_explanations.py::test_traceability_*`.
- Resultado: **221 passed** no conjunto Judge, rotas, baseline e API, antes das alterações.

## 5. Resultados depois da correção

Os resultados abaixo foram reportados pela execução local em Python 3.13. A correção funcional foi introduzida em `5c4448f6`; a validação final após a remoção do comentário incorreto foi repetida no commit `e8b5a650b7795f131d8f5649a0cffaf0e18079f7`. O CI da PR foi executado separadamente no HEAD documental `b57392cbfc65b2c8ce6241494af8e45e579a8b54` (detalhado na seção 6).

| verificação | resultado |
|---|---|
| suíte completa | **3013 passed**, nenhuma falha, nenhum `xfail` |
| `ruff check .` (0.17.5) | All checks passed |
| `ruff format --check .` | 555 arquivos formatados (o relatório dizia 554; ver seção 5.1) |
| `mypy src/ayorai_attractor` | sem problemas (105 arquivos) |
| `bandit -r src/ayorai_attractor` | No issues identified |
| Golden smoke-v0 | `969ec61a4aee4e4426f5d217819bd185ebba248743e7721714a3123f5df67c3d` (inalterado) |
| Golden v0 | `21abb816facce73fc924842d12b373b8792abc2e7389e129c35bb58bab806632` (inalterado) |
| Golden v0.1 | `1fd6fdb75fabcf95b81c0657053a6ba570f97abde96b9dbf5cdda554bf0a9180` (inalterado) |
| Validação C2 original (15 casos) | idêntica byte a byte |
| Validação temporal C2 (14 casos) | X2 passa de `partially_supported` a `refuted`, como esperado; 13/13 |
| Caminhos protegidos | nenhum alterado (`rules/`, `judge2/`, `evals/`, `docs/eval/`, `docs/adr/`, decisões, `docs/release/`) |

**Bateria sintética multidomínio** (600 casos, rótulos de contrato definidos pelo autor, sem anotação humana; não mede acurácia científica):

| métrica | v15 (`main`) | v16 (AP1) |
|---|---|---|
| acertos | 545/600 (90,8%) | **566/600 (94,3%)** [92,2–95,9] |
| falso `refuted` | 0/480 | 0/480 |
| falso apoio | 0/480 | 0/480 |
| contradição perdida | 20,8% | **6,2%** [3,3–11,5] |
| abstenção indevida | 14,8% | **6,8%** [4,4–10,5] |

- Os 21 casos alterados passam todos para o rótulo esperado; nenhum piora.
- Duas execuções dão resultado idêntico byte a byte.
- Casos escritos depois das correções da v15: 30/32 → **31/32**.
- Sondas adversariais: 17/22, sem regressão.

### 5.1 Correção final (autorizada pelo mantenedor)

- **Comentário falso removido.** Em `src/ayorai_attractor/verification/stance.py`, no ramo de `_MILLISECOND_WORDS`, ficou um comentário da tentativa A3 revertida. Ele dizia que "50 ms" e "0,05 segundos" são a mesma quantidade, mas o código continua com `unit = "ms"` e não compara milissegundos com segundos. O comentário foi removido. Não houve mudança de lógica.
- **Contagem do Ruff corrigida.** A primeira versão deste relatório registrou "554 arquivos formatados"; a validação final reportou 555 arquivos já formatados.
- **Validação depois da correção:**
  - suíte completa: 3013 aprovados, 0 falhas, 0 `xfail`;
  - `ruff check .`: sem problemas;
  - `ruff format --check .`: 555 arquivos já formatados;
  - mypy: sem problemas (105 arquivos);
  - bandit: nenhum problema;
  - hashes do Golden inalterados: smoke-v0 `969ec61a…7c3d`, v0 `21abb816…6632`, v0.1 `1fd6fdb7…9180`.

## 6. Pendências (dependem do mantenedor)

1. **A3 — `ms` como tempo.**
   - Melhora o Golden v0 em 1 caso e o v0.1 em 4, sem piora.
   - Exige atualização registrada da referência semântica do Golden.
   - O código e a medição estão descritos em A3.
2. **A2 — emenda datada do ADR-011:** corrigir a linha de `/v1/fields` (rota sem Judge, vocabulário próprio).
3. **P9 — "37" contra "37 mil" sem moeda.** Segue em abstenção por decisão técnica: torná-los comparáveis faria "40" refutar "40 milhões" em textos que omitem a escala.
4. **Quantidades equivalentes escritas com números diferentes** ("2,5 km" × "2.500 m", "2 anos" × "24 meses").
   - Abstêm porque a camada conservadora (`document_check`) exige o número afirmado no trecho.
   - Afrouxar essa garantia é decisão de política.
5. **Substantivo comum que abre as duas frases e nunca aparece em minúscula** ("Inauguração foi em 1990." × "… em 1992.") é tratado como nome. O resultado é abstenção, não refutação. Limitação conhecida, registrada no CHANGELOG-API.
6. **Publicação, CI e integração (estado verificado em 2026-11-22):**
   - a branch `ap1-consolidation` está publicada no GitHub e a PR [#632](https://github.com/Ayorinha/ayorai-opensearch/pull/632) está aberta contra `main`;
   - o HEAD do snapshot de CI conferido antes das atualizações documentais finais é `b57392cbfc65b2c8ce6241494af8e45e579a8b54`; a base da PR permanece `0acc7dc9540048d8340347655a62d7fa7b156741`;
   - no HEAD `b57392cb...`, a API do GitHub retornou **37 check-runs concluídos com sucesso, 0 falhas e 0 pendentes**. A matriz incluiu CI Python 3.11/3.12/3.13, Judge/Golden regression, segurança, CodeQL, Dependency Review, Schemathesis, compatibilidade FastAPI/Pydantic, migração Golden e guardas OpenAPI;
   - a PR foi reportada como `open`, `mergeable=true`, com 9 arquivos alterados. O diff permaneceu restrito ao escopo AP1;
   - após essa conferência, foi criado um commit exclusivamente documental para corrigir o cabeçalho e a seção de publicação deste relatório. **Os 37 checks acima pertencem ao SHA `b57392cb...`, não devem ser atribuídos automaticamente ao novo HEAD**; o CI precisa concluir novamente no commit desta atualização;
   - **não houve merge nesta conferência**. A integração permanece condicionada ao CI do HEAD final e à autorização condicional do mantenedor, registrada na conversa. Não houve release, tag ou DOI.

## 7. Evidências

Os arquivos de trabalho abaixo foram reportados como existentes no diretório de sessão da execução que realizou a validação; não fazem parte do repositório e sua disponibilidade não é garantida fora daquela sessão. Portanto, os resultados resumidos na seção 5 devem ser tratados como evidência de execução reportada, enquanto os checks da PR na seção 6 são verificáveis diretamente no GitHub:

| arquivo | conteúdo |
|---|---|
| `ap1/validation.txt` | saída integral da validação final |
| `ap1/g0_base.json`, `ap1/g0_ms.json`, `ap1/g01_base.json`, `ap1/g01_ms.json` | Golden com e sem a mudança A3 |
| `ap1/run_final.jsonl`, `ap1/run_final2.jsonl`, `ap1/ap1_metrics.md` | bateria e métricas |

**Comandos para reproduzir:**

```bash
python -m pytest -o addopts="" -q
uvx ruff@0.17.5 check . && uvx ruff@0.17.5 format --check .
python -m mypy src/ayorai_attractor
bandit -r src/ayorai_attractor -c pyproject.toml
attractor eval --suite golden-v0 --out g0.json   # e golden-v0.1, smoke-v0
```
