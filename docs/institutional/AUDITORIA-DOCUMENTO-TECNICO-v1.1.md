Revisão por ferramenta automatizada, publicada pelo mantenedor.

# Auditoria do Documento Técnico Público — v1.0 → v1.1

- **Documento auditado:** `docs/institutional/AYORAI-ATTRACTOR-Documento-Tecnico-v1.0.pdf` (commit `9be3a38`, preservado sem alteração).
- **Versão revisada:** `docs/institutional/AYORAI-ATTRACTOR-Documento-Tecnico-v1.1.pdf`.
- **Base de conferência:** `main` no commit `ae44c2380d07635966ba036563681f151cd5a937` (18/10/2026).
- **Data da auditoria:** 18/10/2026.
- **Escopo:** somente documentação. Nenhum código, regra, Golden, manifesto, hash, pré-registro, ADR ou release foi alterado.

## 1. Método

1. Leitura do código que implementa cada afirmação técnica do documento: `api/app.py`, `api/auth.py`, `verification/api_models.py`, `verification/models.py`, `verification/clusters.py`, `verification/judge2/gates.py`, `verification/judge2/adjudication.py`, `verification/nli.py`, `replay_store.py`, `auditlog/`.
2. Conferência dos números contra `docs/eval/F1-RESULTS.md`, `docs/eval/F1.2-RESULTS.md`, `docs/eval/PREREGISTRATION-RGC-v1.md`, `docs/eval/PROTOCOL-GOLDEN-V1.md` (Emenda 5), `docs/legal/MODEL-LICENSE-POLICY.md`, `docs/legal/PRIOR-IP-RECORD.md` e `docs/STATUS.md`.
3. Execução do exemplo do capítulo 6 na rota `POST /v1/verify` (r2-a), com `TestClient` e autenticação desligada apenas no ambiente local de teste.
4. Execução da suíte de testes e consulta dos check-runs do GitHub Actions no mesmo SHA.
5. Consulta das fontes oficiais citadas (CNJ, Anatel, Planalto, Câmara dos Deputados) em 18/10/2026.

## 2. Achados

Classificação: **E** = erro comprovado; **P** = afirmação que precisava de delimitação ou de evidência adicional; **Ed** = melhoria editorial. Gravidade: Alta, Média, Baixa.

| # | Tipo | Gravidade | Trecho da v1.0 | Evidência | Correção na v1.1 |
|---|---|---|---|---|---|
| 1 | E | Alta | Cap. 14: “com n = 30, uma melhora pareada significativa sobre 43,33% (p < 0,05) exigiria cerca de 60% de acurácia”. | Cálculo exato (seção 3): 18/30 = 60% dá p = 0,0625 mesmo no melhor arranjo. Mínimo possível: 19/30 (63,3%), só se o sistema acertar todos os casos que a baseline acerta; pior arranjo: 24/30 (80%). | Afirmação substituída pela derivação, com a observação de que a significância depende dos pares discordantes. |
| 2 | E | Alta | Cap. 9: exemplo de requisição com `claims[]`, `source_texts` como lista, `start`/`end`, stance sem `id`. | `Judge2VerificationRequest` em `verification/api_models.py`: uma afirmação por requisição (`claim_id`, `claim_text`), `atoms` com `text`, `source_texts` como objeto, evidências com `claim_id`, `source_location`, `retrieved_at`, `start_offset`, `end_offset`, `origin_id` ou `canonical_url`; stances com `id`. | Exemplo reescrito com os campos reais. |
| 3 | P | Alta | Cap. 1: “dada a mesma entrada e a mesma versão das regras, o resultado é sempre o mesmo, byte a byte”. | O determinismo testado (T7, `tests/verification/test_judge2_canonical_output.py`) é do Judge 2.0 sobre entrada estruturada. Extração, NLI e tradução dependem de modelos. | Garantia delimitada ao Judge e ao contrato r2-a; pipeline completo descrito como dependente de versões fixadas. |
| 4 | P | Alta | Cap. 14: tabela Golden sem indicar regras nem versão. | `F1-RESULTS.md`: medição no commit `c4b73f4` com Judge 1.x (seis estados, incluindo VERIFIED). `F1.2-RESULTS.md`: caminho C mede 23,33% no Golden v0 com o código atual (26,67% era do commit `c4b73f4`). | Tabela rotulada (Judge 1.x, commit, Golden v0.1 via E1), IC95% incluídos, nota sobre o caminho C. Valores históricos preservados. |
| 5 | E | Média | Cap. 6, etapa 2: “o Judge se abstém” quando a afirmação está fora de escopo etc. | `gates.py`, `_abstention_codes`: os motivos vêm de sinalizadores booleanos enviados pelo chamador (`out_of_scope`, `factual_claim`, `temporal_anchor_present`, `retrieval_succeeded`, `evidence_pool_integrity_ok`). | Texto corrigido; a figura 4 passou a dizer “sinalizadores do chamador”. |
| 6 | E | Média | Cap. 6, etapa 4: três motivos de rejeição. | `IMPLEMENTED_E_REJECTIONS` inclui `SOURCE_UNAVAILABLE`. Evidência sem stance para o átomo é rejeitada como `NEUTRAL_STANCE`. | Motivo acrescentado; avaliação por par evidência × átomo explicada. |
| 7 | E | Média | Cap. 6, etapa 1: `NO_ATOMS` = “afirmação composta sem átomos”. | `_validate_g1`: qualquer requisição r2-a sem átomos é rejeitada; o texto do átomo deve coincidir com o trecho declarado. | Descrições de `NO_ATOMS` e `ATOM_SPAN_OUT_OF_RANGE` corrigidas. |
| 8 | P | Média | Cap. 6, etapa 5 e figura 5: evidência “sem metadados” como UNKNOWN; clusters chamados de “independentes”. | `Evidence` exige `origin_id` ou `canonical_url`. `clusters.py` separa evidências sem dependência conhecida; isso não prova independência. | Figura 5 e texto refeitos: clusters distintos = nenhuma dependência detectada. |
| 9 | P | Média | Cap. 6, etapa 7: escala R0–R3 sem explicação. | `adjudication.py`, `_robustness`: R2/R3 dependem de `provenance_complete`, declarado pelo chamador, com padrão `true`. | Nota explicando a ordem (R2 entre R1 e R3 por informação incompleta) e a dependência do campo declarado. Contrato não alterado (ver seção 5). |
| 10 | Ed | Média | Cap. 6: exemplo ilustrativo com offsets inventados. | Exemplo executado na API em `ae44c23`: `DECIDED`, `REFUTED` por `2.0.0/K1`, átomos `2.0.0/A2` e `2.0.0/A3`, robustez R1, `output_sha256 = a1a38fe0…a4c5c6`, igual em duas execuções. | Exemplo substituído pela execução real. |
| 11 | E | Média | Cap. 11: paráfrase do art. 27 da Res. CNJ 615 como “controle de versão e registros de auditoria para preservar integridade e rastreabilidade dos dados”, ligada a regras do Judge. | Texto oficial: o caput trata de impedir a alteração dos dados recebidos antes do uso no desenvolvimento de soluções de IA (datasets), por controle de versões, tokens e registros. | Paráfrase corrigida; relação descrita como analogia de prática, não obrigação. |
| 12 | P | Média | Cap. 11: art. 21, §2º, como “produtos de IA identificados nos logs” ligados ao “registro previsto na ADR-010”. | Texto oficial: produtos gerados por IA devem registrar o uso de IA nos logs, com rótulos, para estatística, monitoramento e auditoria. ADR-010 não está implantada. | Redação ajustada para “aplicação potencial”. |
| 13 | P | Média | Cap. 11: sem menção a alterações da Res. CNJ 615. | Res. CNJ 674/2026 alterou o art. 15 (composição do comitê), não citado no documento. | Nota acrescentada. |
| 14 | P | Média | Cap. 10: RGC sem situação de vigência. | Página oficial da Anatel (atualizada em 06/07/2026): vigência principal desde 01/09/2025, exceções do Acórdão nº 228/2024, arts. 2º a 79 revogados pela Res. 777/2025. | Nota de vigência com data de consulta; benchmark não interpreta vigência. |
| 15 | P | Média | Cap. 5, 13 e 16: “autenticação fechada por padrão”. | `api/auth.py`: modo `api_key` por padrão, falha fechada se mal configurado, desligável por `ATTRACTOR_AUTH_MODE=off`; `/health` público; limite de corpo configurável; sem rate limiting nem TLS próprio. | Controles e ausências descritos; serviço não descrito como pronto para produção. |
| 16 | P | Média | Cap. 14: protocolo RGC sem baseline primária nem critério primário. | `PREREGISTRATION-RGC-v1.md` §4–5 e Emenda 5 / DEC-014. | Baseline B (partição pública de 70%), critério primário de três condições, kappa entre dois anotadores, estado PROPOSTO, execução única. |
| 17 | E | Baixa | Cap. 7: caminho B “EVAL_ONLY”. | `MODEL-LICENSE-POLICY.md`: tradução EVAL_ONLY por precaução; NLI de B COMMERCIAL_DEFAULT. | Linha corrigida. |
| 18 | P | Baixa | Cap. 12: “o núcleo executa sem rede (T9)”. | T9 cobre a adjudicação do Judge 2.0. | “O Judge 2.0 executa sem acesso à rede”. |
| 19 | P | Baixa | Cap. 4: “testes AST bloqueiam outros módulos”. | `TRACEABILITY-MASTER.md`: as guardas AST restringem, mas não provam todo comportamento em execução. | Redação ajustada. |
| 20 | P | Baixa | Cap. 18: “o autor permanece titular dos direitos”; documentação “licenciada”. | `LICENSE`, `NOTICE`, `TRADEMARKS.md`, `CONTRIBUTING.md` (DCO), `PRIOR-IP-RECORD.md` (sem pedido no INPI). | Titularidade de contribuições de terceiros, seção 4(d), ausência de registro de marca e aviso de que não é parecer jurídico. |
| 21 | P | Baixa | Cap. 2: frase sobre o que “Anderson identificou”. | Não havia fonte no repositório para a formulação. | Reescrita com base em `docs/INVESTIDORES.md`. |
| 22 | Ed | Baixa | Indicadores: “800+ commits”, “1.057 testes” sem SHA, “4 releases com DOI”. | API do GitHub: 903 commits na `main` em 18/10/2026; releases v0.1.0 a v0.5.0 e baseline-legacy-v0; DOIs de v0.2.0 a v0.5.0 e do baseline. | Números com SHA e data; DOIs nomeados. |

## 3. Cálculo estatístico (achado 1)

Teste exato de McNemar bilateral. A baseline de classe majoritária acerta m = 13 de n = 30 casos. Para um sistema com k acertos e sobreposição o com os acertos da baseline, os pares discordantes são b = k − o e c = 13 − o, e p = min(1, 2·P[Bin(b+c, 1/2) ≤ min(b, c)]).

```python
from math import comb


def exact_mcnemar(b, c):
    n = b + c
    if n == 0:
        return 1.0
    return min(1.0, 2 * sum(comb(n, i) for i in range(min(b, c) + 1)) / 2**n)


n, m = 30, 13
for k in range(m, n + 1):
    best = exact_mcnemar(k - min(k, m), m - min(k, m))
    worst = exact_mcnemar(k - max(0, k + m - n), m - max(0, k + m - n))
    print(k, round(k / n, 4), round(best, 4), round(worst, 4))
```

Resultado relevante:

| Acertos | Acurácia | p (melhor arranjo) | p (pior arranjo) |
|---|---|---|---|
| 18/30 | 60,00% | 0,0625 | 0,4583 |
| 19/30 | 63,33% | 0,0312 | 0,3449 |
| 24/30 | 80,00% | 0,0010 | 0,0347 |

A mesma afirmação de “aproximadamente 60%” aparece em `docs/adr/ADR-005-hybrid-multilingual-stance.md` e em `docs/eval/F1-RESULTS.md`. Esses arquivos são registros aceitos e não foram alterados (ver seção 5).

## 4. Testes e verificações executados

| Verificação | Resultado |
|---|---|
| `pytest` no commit `ae44c23` (Python 3.13, ambiente local) | 1.057 aprovados, 1 falha: `tests/test_namespace.py::test_official_sdk_namespaces_are_not_shadowed`, porque o Python do Debian instala pacotes em `dist-packages` e o teste espera `site-packages`. |
| Check-runs do GitHub Actions no commit `ae44c23` | Todos concluídos com sucesso, incluindo `test (3.11)`, `test (3.12)`, `test (3.13)`, `golden-regression`, `judge-regression`, `security`, `namespace-compatibility`, `analyze`; `rgc-design-simulation` pulado por desenho. |
| Check-runs no commit `9be3a38` (PR do PDF v1.0) | Todos concluídos com sucesso. |
| Exemplo do capítulo 6 em `POST /v1/verify` (r2-a) | HTTP 200, `DECIDED`, `REFUTED` (`2.0.0/K1`), mesmo `output_sha256` em duas execuções. |
| Busca por menções a ferramentas no PDF v1.1 | Nenhuma ocorrência. |

## 5. Pontos abertos que exigem decisão do mantenedor

Nenhum destes itens foi alterado nesta revisão.

1. **ADR-005 e `F1-RESULTS.md`** contêm a afirmação dos 60% (achado 1). Proposta: nota datada de correção em cada arquivo, sem reescrever o texto original.
2. **`README.md`** ainda apresenta 26,67% como valor do caminho C no Golden v0 sem a nota de `F1.2-RESULTS.md`. Proposta: acrescentar a nota de que o código atual mede 23,33%.
3. **Semântica de robustez (achados 8 e 9).** R3 depende de `provenance_complete`, declarado pelo chamador e com padrão `true`; clusters distintos significam apenas ausência de dependência detectada. Proposta para avaliação em ADR: tornar `provenance_complete` obrigatório no r2-a, ou derivá-lo dos critérios da ADR-006 §2, e registrar a justificativa da ordem R1 < R2 < R3. Qualquer mudança exige nova versão das regras.
4. **Origem do projeto (capítulo 2).** O relato pessoal do autor não está documentado no repositório; pode ser acrescentado pelo autor numa revisão futura.
5. **CPC art. 369 e CPP arts. 158-A a 158-F.** As páginas do Planalto vieram truncadas no acesso desta revisão; os dispositivos devem ser conferidos no texto oficial antes de qualquer uso jurídico do documento.
6. **Descrição da PR.** O rodapé adicionado automaticamente à descrição da PR deve ser removido manualmente pelo mantenedor.
7. **DCO.** Os commits desta PR não têm linha `Signed-off-by`; cabe ao mantenedor decidir se a regra se aplica aos próprios commits.

## 6. Recomendação

**Pronto para divulgação com ressalvas.** A v1.1 corrige os erros comprovados e delimita as afirmações que dependiam de contexto. Antes de usar o documento em contexto jurídico, conferir os dispositivos do item 5.5. Os itens 5.1 a 5.3 não impedem a divulgação, porque a v1.1 já apresenta a informação correta, mas mantêm divergência entre o documento e arquivos do repositório até serem tratados.
