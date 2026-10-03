# Pre-registration — Golden v0.1

Status: frozen before any evaluation run.
Date: 2026-10-03
Base: Golden v0 (`evals/golden/v0.jsonl`, SHA-256 2613aefccf232989833b80c0d23257e6e9f312e0f6b720801a0658407b2f1c75), unchanged.
New file: `evals/golden/v0.1.jsonl`, SHA-256 a7076512196c1ee9670478f036f7a3996fe89a483efad140ec7b985a54846fb9.

## 1. Problem

In 16 of the 34 Golden v0 cases the claim text describes the expected reasoning of the Judge (for example, "the documents form a single cluster") instead of a factual proposition about the world. A claim verifier checks claims against documents; the documents describe latency, revenue, dates and approvals, not clusters. These cases therefore measure an artifact of the test, not the verifier.

## 2. Rewrite rules (fixed before writing any claim)

1. Only cases whose claim describes Judge reasoning or a meta-property of the evidence are rewritten.
2. The new claim is the factual proposition investigated by the case query, stated as an assertion in Portuguese.
3. In conflict cases the asserted value is always the value of the first document in `evidence_pool`.
4. Case ids, queries, categories, documents, evidence pools and ALL expected verdicts are unchanged.
5. The rule is applied to every qualifying case, including cases the current system already gets right (c03).
6. Numeric values are written in pt-BR notation (decimal comma).

## 3. Disclosure

The author of the rewrite (Claude) had seen per-case results of path C on Golden v0 before writing this file. Mitigation: the mechanical rules above, unchanged verdicts, and no evaluation of any path on v0.1 before this file and its hash were frozen.

## 4. Invariants (verified)

- v0.1 is byte-identical to v0 except for the 17 claim texts listed below.
- Same 34 cases, same order, same expected verdicts, same evidence pools.
- Golden v0 remains frozen and is always reported alongside v0.1.

## 5. Changes

| Case | Expected verdict | v0 claim | v0.1 claim |
|---|---|---|---|
| c01 | CONFLICTING | O relatório anual informa USD 120 milhões. | A receita da AtlasGrid no ano fiscal de 2025 foi USD 120 milhões. |
| c01 | CONFLICTING | A apresentação de investidores informa USD 130 milhões. | A receita da AtlasGrid no ano fiscal de 2025 foi USD 130 milhões. |
| c03 | UNVERIFIED | Uma resposta isolada de LLM/mock não constitui fonte independente e não pode elevar o claim acima de UNVERIFIED. | A OrionCloud tem foco em APIs interativas. |
| x01 | CONFLICTING | Uma fonte informa USD 120 milhões e outra informa USD 130 milhões para o mesmo período. | A receita da AtlasGrid no ano fiscal de 2025 foi USD 120 milhões. |
| x02 | CONFLICTING | Uma fonte informa 2,0 milhões e outra 2,3 milhões. | A NovaBank tinha 2,0 milhões de clientes de varejo ativos no fim de 2025. |
| r01 | PARTIALLY_SUPPORTED | Os documentos 007, 008 e 031 reproduzem a mesma origem e formam um único cluster, portanto não constituem três fontes independentes. | A latência mediana da API da OrionCloud é 120 ms. |
| r02 | PARTIALLY_SUPPORTED | Não; os três documentos compartilham o mesmo origin_id e não satisfazem duas fontes independentes. | A latência mediana da API da OrionCloud é 120 ms. |
| h01 | PARTIALLY_SUPPORTED | Não; o conteúdo é idêntico, portanto os documentos formam um único cluster mesmo com domínios e origin_id diferentes. | A API da AtlasGrid usa HTTPS para transporte e exige um token de API para requisições autenticadas. |
| ch01 | PARTIALLY_SUPPORTED | Não; 008 cita 007 e compartilha o mesmo origin_id, portanto a cadeia permanece em um único cluster. | A latência mediana da API da OrionCloud é 120 ms. |
| p01 | VERIFIED | A afirmação é sustentada por duas fontes independentes, ambas com retrieved_at e offsets válidos. | A VectorLabs bloqueia artefatos de modelo não assinados antes da implantação. |
| p02 | SUPPORTED | A afirmação continua apoiada, mas a proveniência incompleta impede VERIFIED e limita o estado a SUPPORTED. | A VectorLabs bloqueia artefatos de modelo não assinados antes da implantação. |
| x04 | CONFLICTING | Há duas datas conflitantes para o mesmo atributo: 2026-03-10 e 2026-03-12. | O AG-001 foi corrigido em produção em 2026-03-10. |
| x05 | CONFLICTING | Há afirmações incompatíveis: uma fonte diz que aprovou e outra diz que não aprovou. | A AtlasGrid aprovou o rollout de produção do AG-002 em 2026-04-01. |
| x06 | CONFLICTING | Há afirmações incompatíveis sobre a mesma entidade e atributo: São Paulo versus Santiago. | A região primária de nuvem da AtlasGrid é São Paulo. |
| nt01 | VERIFIED | As duas fontes reportam a mesma taxa de 3,1% (3,10% é representação equivalente). | A taxa anual reportada para o serviço da AtlasGrid é 3,1%. |
| nt02 | VERIFIED | Os valores 1.000 e 1.004 não constituem conflito numérico porque a diferença relativa é 0,4%. | O serviço da AtlasGrid reportou o valor 1,000 para o atributo medido. |
| nt03 | CONFLICTING | Os valores 1.000 e 1.020 constituem conflito numérico porque a diferença relativa é aproximadamente 1,96%. | O serviço da AtlasGrid reportou o valor 1,000 para o atributo medido. |

## 6. Analysis plan

- Paths A, B and C are evaluated on v0 and v0.1 with the same code, seed 20261003 and 10,000 bootstrap iterations.
- Primary metric: balanced accuracy. Secondary: accuracy, macro-F1, ECE, latency p50/p95, abstention.
- Paired comparison v0 vs v0.1 per path with exact McNemar on the same case ids.
- Results are reported per category and per expected state.
- No threshold, rule or model is changed between the v0 and v0.1 runs.
- v0.1 is a development set. It is not used to claim generalization; that requires the hidden Golden v1.
