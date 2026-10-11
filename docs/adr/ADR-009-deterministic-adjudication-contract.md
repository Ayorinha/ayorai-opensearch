# ADR-009 — Contrato determinístico de adjudicação e cobertura de claims

**Status:** Accepted — 2026-10-10, aprovado pelo mantenedor Anderson Leon Ayora  
**Data:** 2026-10-10  
**Escopo:** substitui ADR-002 §§1 e 4; o texto histórico de ADR-002 permanece preservado  
**Autoridade:** este contrato é normativo para a implementação Judge 2.0.0 após merge desta ADR e das PRs de implementação correspondentes.

## Explicação simples

O Judge determinístico é a única autoridade para o veredito factual.  
Cada afirmação composta é dividida em partes atômicas e avaliada por regras versionadas.  
Evidências só contam quando passam pelos critérios de admissibilidade e independência.  
O sistema registra razões, cobertura, robustez e hashes para permitir auditoria e reprodução.  
Abstenção e entrada inválida não são vereditos factuais.

## 1. Contexto e invariantes

LLMs podem extrair claims, propor relações de stance e redigir explicações, mas não decidem o veredito final. A decisão factual é produzida exclusivamente pelo Judge determinístico. Sinais probabilísticos podem justificar abstenção, nunca escolher ou substituir um veredito.

- **I1 — Estado/veredito:** `verdict != null` se e somente se `decision_state = DECIDED`.
- **I2 — Robustez:** robustez descreve a força e a independência da evidência; nunca altera o veredito.
- Regras executáveis são dados versionados, identificados por versão e `rules_sha256`.
- Operação bem-sucedida, confiança do modelo, quantidade bruta de documentos e explicação textual não constituem adjudicação factual.
- Nenhum componente fora do Judge pode construir ou emitir o veredito factual final.

## 2. Tipos normativos

`DecisionState = {DECIDED, ABSTAINED, INVALID_INPUT}`

`Verdict = {SUPPORTED, PARTIALLY_SUPPORTED, REFUTED, UNVERIFIED, CONFLICTING}`

`Robustness = {R0, R1, R2, R3}`, com `R0=NONE`, `R1=SINGLE_SOURCE`, `R2=INDEPENDENCE_UNKNOWN`, `R3=CORROBORATED`.

`VERIFIED` não faz parte do vocabulário de vereditos do Judge 2.0.0. O estado de decisão não é um veredito: `ABSTAINED` e `INVALID_INPUT` sempre produzem `verdict=null`.

## 3. Portão G — validação de entrada

Os códigos G abaixo são erros de entrada e levam a `INVALID_INPUT`, sem veredito factual:

- `SCHEMA_VIOLATION`: entrada incompatível com o esquema declarado.
- `EMPTY_CLAIM`: claim vazio ou composto somente por espaços.
- `NO_ATOMS`: claim composto sem átomos após a decomposição requerida.
- `DUPLICATE_ID`: identificador duplicado em qualquer coleção em que IDs devam ser únicos.
- `DANGLING_REFERENCE`: referência a claim, átomo, evidência ou stance inexistente.
- `DUPLICATE_STANCE`: mais de uma stance para a mesma relação que deve ser única.
- `ATOM_SPAN_OUT_OF_RANGE`: span do átomo fora dos limites do texto de origem.
- `UNSUPPORTED_PROTOCOL_VERSION`: versão do protocolo não suportada.

Cada código G deve ter teste negativo específico. A validação não pode converter entrada inválida em `UNVERIFIED` nem chamar o Judge como se a entrada fosse válida.

## 4. Abstenção

Os motivos abaixo levam a `ABSTAINED`, com `verdict=null`:

- `OUT_OF_SCOPE`
- `NON_FACTUAL_CLAIM`
- `MISSING_TEMPORAL_ANCHOR`
- `RETRIEVAL_FAILURE`
- `EVIDENCE_POOL_INTEGRITY_FAILURE`

Abstenção significa que não se emite veredito factual. Não é uma classe de veredito nem deve ser contada como `UNVERIFIED`.

## 5. Admissibilidade E

Uma evidência só participa dos clusters se passar pelos critérios aplicáveis:

- **E1 — Offsets:** offsets válidos, não negativos, ordenados e dentro dos limites do documento.
- **E2 — Trecho:** quando existe hash de conteúdo normalizado, o trecho deve conferir com a fonte identificada por esse hash.
- **E3 — Relação:** deve existir aresta explícita `SUPPORTS` ou `CONTRADICTS` entre a evidência e o átomo avaliado.

Evidências rejeitadas não entram nos contadores decisórios e devem ser registradas com um motivo: `OFFSET_INVALID`, `EXCERPT_MISMATCH` ou `NEUTRAL_STANCE`. A rejeição de evidência não pode ser omitida do resultado técnico.

## 6. Independência, clusters e veredito atômico A

S e C representam, respectivamente, o número de clusters independentes admissíveis de suporte e contradição, segundo o contrato de independência de ADR-006. Republicações ou fontes dependentes não aumentam a contagem independente.

Para cada átomo:

- **A1:** S=0 e C=0 → `UNVERIFIED`.
- **A2:** S≥1 e C=0 → `SUPPORTED`.
- **A3:** S=0 e C≥1 → `REFUTED`.
- **A4:** S≥1 e C≥1 → `CONFLICTING`.

Um átomo nunca recebe `PARTIALLY_SUPPORTED`; esse veredito é reservado à agregação composta. A contagem de clusters afeta robustez, não altera a regra de veredito A.

## 7. Robustez R

A robustez é calculada no lado decisivo do átomo, isto é, suporte para `SUPPORTED`, contradição para `REFUTED`, ambos os lados para `CONFLICTING`, e nenhum lado para `UNVERIFIED`.

- **R0 / NONE:** nenhum cluster decisório admissível.
- **R1 / SINGLE_SOURCE:** exatamente um cluster decisório admissível.
- **R2 / INDEPENDENCE_UNKNOWN:** pelo menos dois clusters decisórios, com proveniência incompleta em uma ou mais evidências que impedem confirmar plenamente a independência.
- **R3 / CORROBORATED:** pelo menos dois clusters decisórios, todos com proveniência completa.

A robustez nunca promove nem rebaixa o veredito. Para resultado composto, a robustez é a menor robustez entre os átomos suportados, conforme a ordem R0 < R1 < R2 < R3; o resultado deve manter a cobertura que explica quais átomos contribuíram.

## 8. Agregação composta K

Para um claim composto, aplicar a seguinte precedência, nesta ordem:

- **K1:** se algum átomo for `REFUTED`, resultado `REFUTED`.
- **K2:** senão, se algum átomo for `CONFLICTING`, resultado `CONFLICTING`.
- **K3:** senão, se todos os átomos forem `SUPPORTED`, resultado `SUPPORTED`.
- **K4:** senão, se algum átomo for `SUPPORTED`, resultado `PARTIALLY_SUPPORTED`.
- **K5:** senão, resultado `UNVERIFIED`.

A regra K aplicada deve ser identificada em `rule_trace` com o `rule_id` correspondente e rotulada como `derived`. Os pesos dos átomos são iguais. Não há resolução automática de conflitos além da precedência K nesta versão 2.0.0. Qualquer política diferente exige nova decisão versionada.

A cobertura é um objeto com os contadores `supported`, `refuted`, `conflicting`, `unverified` e `total`. Ela descreve a distribuição dos vereditos atômicos e não pode ocultar átomos inválidos ou abstidos; esses estados são relatados no estado de decisão e nos motivos.

## 9. Identidade de regras e saída canônica

O resultado inclui `judge_rules_version`, `rules_sha256`, `input_sha256`, `decision_state`, `reason_codes`, `verdict`, `coverage`, `robustness`, `atoms`, `rule_trace` e `output_sha256`.

Cada átomo contém `atom_id`, `verdict`, `support_clusters`, `contradiction_clusters`, `robustness`, `rule_id`, `admitted_evidence` e `excluded_evidence` (com `id` e `reason`). `rule_id` usa o formato `2.0.0/A2`, `2.0.0/K4` ou `2.0.0/G1:DUPLICATE_ID`, conforme aplicável.

A serialização canônica usa UTF-8, chaves ordenadas, separadores compactos, `ensure_ascii=False` e representação explícita de `null`. A definição implementada deve ser consistente em todos os caminhos e coberta por teste byte a byte. `output_sha256` é calculado sobre a representação canônica do conteúdo de saída antes da inclusão do próprio campo `output_sha256`, evitando autorreferência. Hashes identificam conteúdo e não provam, isoladamente, a verdade de uma afirmação.

## 10. Migração de regras 1.x e goldens derivados

As regras 1.x permanecem executáveis e historicamente preservadas até a v0.5.0. O caminho `r1-a` mantém o contrato de fio existente, sem alteração de comportamento ou serialização.

A migração derivada de goldens usa uma tabela de mapeamento versionada:

- `VERIFIED` → `SUPPORTED` + R3.
- `SUPPORTED` → `SUPPORTED` + R2.
- `PARTIALLY_SUPPORTED` com regra S=1 → `SUPPORTED` + R1.
- Demais rótulos atômicos permanecem inalterados.
- O rótulo composto é recalculado segundo K.

Os arquivos derivados são `evals/golden/v0-r2.jsonl` e `evals/golden/v0.1-r2.jsonl`, cada um com manifesto próprio que registra origem, método, versão de regras, commit e hashes. Os arquivos originais, manifestos existentes, thresholds e hashes congelados não podem ser alterados. Casos não migráveis devem ser listados com motivo, não descartados silenciosamente.

## 11. Testes normativos

A implementação deve cobrir T1–T11:

- **T1:** tabela atômica exaustiva para S∈{0..3}, C∈{0..2} e estados de proveniência.
- **T2:** tabela composta exaustiva para multiconjuntos de vereditos até n=4.
- **T3:** átomo único nunca retorna `PARTIALLY_SUPPORTED`.
- **T4:** aumentar S mantendo S≥1 e C=0 não muda o veredito atômico.
- **T5:** republicação não aumenta a contagem de clusters independentes.
- **T6:** invariância à ordem onde o contrato declarar ordem irrelevante.
- **T7:** serialização canônica determinística byte a byte.
- **T8:** I1 em todos os caminhos de decisão, abstenção e erro.
- **T9:** execução offline, sem rede.
- **T10:** regras 1.x reproduzem os resultados de v0.3.0 sem alteração dos artefatos congelados.
- **T11:** cada código G tem teste específico.

As tabelas de verdade publicadas devem ser geradas do arquivo versionado de regras, não mantidas manualmente em duplicidade. A rastreabilidade deve mapear cada regra normativa a testes e, quando aplicável, a casos de golden.

## 12. Explicações e limitações

Toda resposta documentada deve ter explicação simples com no máximo cinco linhas e explicação técnica. A explicação técnica inclui versão e hash das regras, decomposição, evidências admitidas/excluídas, IDs das regras, estado de decisão, cobertura, robustez, hashes e limitações. Explicações não constituem canal alternativo de decisão e não podem transformar abstenção ou entrada inválida em veredito.

## 13. Compatibilidade e rollout

Esta ADR substitui ADR-002 §§1 e 4; o texto original dessas seções é preservado como histórico. Outras seções de ADR-002 permanecem vigentes, salvo substituição explícita por decisão posterior. A implementação deve ocorrer em PRs isoladas, com CI verde, revisão independente do SHA exato e hashes dos artefatos congelados inalterados. A aceitação desta ADR não autoriza alterar goldens ou publicar release automaticamente.

## Aprovação

**Decisão do mantenedor:** ACEITO em 2026-10-10.  
**Revisão independente e integração documental:** pendentes na PR correspondente.  
**Implementação:** pendente das PRs da Fase 2; a presença desta ADR não deve ser descrita como implementação concluída.
