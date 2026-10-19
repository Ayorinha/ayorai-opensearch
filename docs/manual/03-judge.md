Estado: Atual · Referência: main @ 6f3588b · Atualizado: 2026-10-19
Fontes de verdade: `rules/judge-2.0.0.json`, `src/ayorai_attractor/verification/judge2/__init__.py`, `src/ayorai_attractor/verification/judge2/gates.py`, `src/ayorai_attractor/verification/judge2/adjudication.py`, `docs/judge2/TRUTH-TABLE.md`, `docs/judge2/TRACEABILITY.md`, testes em `tests/verification/test_judge2_*.py`.

# 03 — Judge determinístico

## Propósito

O Judge 2.0.0 aplica regras versionadas e determinísticas a entradas estruturadas. Ele não substitui a coleta de evidências, não descobre sozinho a posição semântica da evidência e não transforma sinais probabilísticos em autoridade de veredito. A autoridade declarada pelo contrato é `deterministic_judge_only`.

O contrato normativo está em `rules/judge-2.0.0.json`, cuja cópia empacotada em `src/ayorai_attractor/verification/judge2/rules/judge-2.0.0.json` tem o mesmo blob SHA do Git. O código de adjudicação declara como identidade canônica do contrato `493cce66ce45fcb432b8345e7567cfb39858492bfe46d5fa6b584991e79e9efc` (`EXPECTED_RULES_SHA256`). Esse valor é o hash canônico esperado pelo código, não deve ser confundido com o hash bruto dos bytes do arquivo JSON.

## Como funciona

### Invariantes

O contrato declara quatro invariantes:

- `verdict` é nulo se, e somente se, `decision_state` não for `DECIDED`.
- Robustez nunca altera o veredito.
- Sinais probabilísticos nunca selecionam o veredito.
- Átomos têm pesos iguais.

### Estados e vereditos

Estados possíveis de decisão:

- `DECIDED`
- `ABSTAINED`
- `INVALID_INPUT`

Vereditos definidos no contrato:

- `SUPPORTED`
- `PARTIALLY_SUPPORTED`
- `REFUTED`
- `UNVERIFIED`
- `CONFLICTING`

`VERIFIED` não faz parte do enum normativo do Judge 2.0.0. É um rótulo legado tratado no mapeamento de compatibilidade r1-a, no qual `VERIFIED` é convertido para `SUPPORTED` com robustez `R3`. O contrato de compatibilidade também preserva o contrato de transporte r1-a até a versão indicada no próprio arquivo de regras.

### Gates de entrada e abstenção

O gate G1 produz `INVALID_INPUT` para entradas inválidas. Os códigos definidos no arquivo normativo são:

- `SCHEMA_VIOLATION`
- `EMPTY_CLAIM`
- `NO_ATOMS`
- `DUPLICATE_ID`
- `DANGLING_REFERENCE`
- `DUPLICATE_STANCE`
- `ATOM_SPAN_OUT_OF_RANGE`
- `UNSUPPORTED_PROTOCOL_VERSION`

O gate G2 produz `ABSTAINED`, sem veredito factual, para:

- `OUT_OF_SCOPE`
- `NON_FACTUAL_CLAIM`
- `MISSING_TEMPORAL_ANCHOR`
- `RETRIEVAL_FAILURE`
- `EVIDENCE_POOL_INTEGRITY_FAILURE`

### Admissibilidade da evidência

A evidência só pode contribuir para a decisão depois dos gates de admissibilidade:

| Regra | Verificação | Código de rejeição |
|---|---|---|
| E1 | Fonte disponível e offsets válidos dentro da fonte | `SOURCE_UNAVAILABLE`, `OFFSET_INVALID` |
| E2 | Trecho igual à fatia da fonte normalizada; hash normalizado do conteúdo conferido quando presente | `EXCERPT_MISMATCH` |
| E3 | Aresta explícita `SUPPORTS` ou `CONTRADICTS` ligada ao átomo | `NEUTRAL_STANCE` |

Os offsets são avaliados em pontos de código Unicode, conforme os testes de fonte com caracteres acentuados. A normalização e a comparação de trechos são verificações de consistência textual; não inferem a posição semântica da evidência.

### Regras atômicas A1–A4

| Regra | Clusters de suporte | Clusters de contradição | Veredito |
|---|---:|---:|---|
| A1 | 0 | 0 | `UNVERIFIED` |
| A2 | pelo menos 1 | 0 | `SUPPORTED` |
| A3 | 0 | pelo menos 1 | `REFUTED` |
| A4 | pelo menos 1 | pelo menos 1 | `CONFLICTING` |

A contagem é feita sobre clusters de evidência admissível, não simplesmente sobre o número bruto de trechos enviados.

### Robustez R0–R3

- R0 — `NONE`: nenhum cluster decisório admissível.
- R1 — `SINGLE_SOURCE`: um cluster decisório no lado avaliado.
- R2 — `INDEPENDENCE_UNKNOWN`: dois ou mais clusters, mas alguma proveniência relevante está incompleta.
- R3 — `CORROBORATED`: dois ou mais clusters e toda a proveniência relevante está completa.

Robustez descreve proveniência e corroborabilidade segundo as regras do contrato; não substitui nem altera o veredito.

### Composição K1–K5

As regras são aplicadas nesta precedência:

1. K1: se qualquer átomo for `REFUTED`, o resultado composto é `REFUTED`.
2. K2: caso contrário, se algum átomo for `CONFLICTING`, o resultado é `CONFLICTING`.
3. K3: caso contrário, se todos os átomos forem `SUPPORTED`, o resultado é `SUPPORTED`.
4. K4: caso contrário, se algum átomo for `SUPPORTED`, o resultado é `PARTIALLY_SUPPORTED`.
5. K5: nos demais casos, o resultado é `UNVERIFIED`, com robustez `R0`.

A tabela de verdade publicada é gerada a partir do contrato e cobre combinações atômicas e composições ordenadas de um a quatro átomos.

## Contratos e parâmetros

O contrato define estes campos de saída:

- `judge_rules_version`
- `rules_sha256`
- `input_sha256`
- `decision_state`
- `reason_codes`
- `verdict`
- `coverage`
- `robustness`
- `atoms`
- `rule_trace`
- `output_sha256`

A saída canônica usa JSON UTF-8, chaves ordenadas, separadores compactos, `ensure_ascii=false` e valores nulos explícitos. O cálculo de `output_sha256` exclui o próprio campo `output_sha256`. Os identificadores de regra seguem o formato `2.0.0/<rule_id>`.

## Limites conhecidos

- As regras só adjudicam a entrada que passou pela validação e pelos gates; não demonstram que o material de origem é verdadeiro ou confiável por si só.
- E3 valida uma relação de stance explícita; não infere se uma evidência apoia ou contradiz uma afirmação.
- O contrato define compatibilidade com r1-a, incluindo conversão de rótulos legados; não se deve tratar `VERIFIED` como um veredito normativo do Judge 2.
- A existência de uma tabela de verdade exaustiva e de testes de regressão demonstra cobertura das regras codificadas, não certificação externa nem desempenho em benchmark PT-BR.

## Evidências

- Contrato normativo e códigos: `rules/judge-2.0.0.json`.
- Carregamento, versão e identidade canônica: `src/ayorai_attractor/verification/judge2/__init__.py`.
- Gates G1/G2 e E1/E2/E3: `src/ayorai_attractor/verification/judge2/gates.py`.
- Adjudicação atômica e composta: `src/ayorai_attractor/verification/judge2/adjudication.py`.
- Tabela de verdade gerada: `docs/judge2/TRUTH-TABLE.md`.
- Rastreabilidade regra–teste–caso: `docs/judge2/TRACEABILITY.md`.
- Testes de gates, adjudicação e saída canônica: `tests/verification/test_judge2_gates.py`, `tests/verification/test_judge2_adjudication.py` e `tests/verification/test_judge2_canonical_output.py`.

## Ver também

- [Visão geral](01-visao-geral.md)
- [Arquitetura](02-arquitetura.md)
- [Tabela de verdade do Judge 2](../judge2/TRUTH-TABLE.md)
- [Rastreabilidade do Judge 2](../judge2/TRACEABILITY.md)
- [ADR-009 — contrato de adjudicação determinística](../adr/ADR-009-deterministic-adjudication-contract.md)
