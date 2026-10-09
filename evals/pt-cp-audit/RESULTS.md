# PT-CP-Audit — resultados v5 → v6

Medição única no split **test** (reservado), conforme o protocolo em `README.md` (commit `4d30582`), depois do baseline congelado (`e23732f`) e do código v6 (`edae41b`).

Relatório: `reports/pt-cp-audit-v5-vs-v6-test.json`.

| Split | Casos | Métrica | v5 | v6 |
|---|---:|---|---:|---:|
| test só-manuais (leitura principal) | 40 | **Apoio falso (primária)** | 25.9% | 14.8% |
| test só-manuais (leitura principal) | 40 | Acurácia | 65.0% | 72.5% |
| test só-manuais (leitura principal) | 40 | Macro-F1 | 0.6479 | 0.7250 |
| test só-manuais (leitura principal) | 40 | Contradição falsa | 17.2% | 17.2% |
| test completo (inclui mutações) | 68 | **Apoio falso (primária)** | 17.1% | 9.8% |
| test completo (inclui mutações) | 68 | Acurácia | 76.5% | 83.8% |
| test completo (inclui mutações) | 68 | Macro-F1 | 0.7508 | 0.8183 |
| test completo (inclui mutações) | 68 | Contradição falsa | 11.6% | 11.6% |

McNemar exato pareado (por caso):
- test só-manuais: v5 certo/v6 errado = 2; v6 certo/v5 errado = 5; p = 0.453125
- test completo: v5 certo/v6 errado = 2; v6 certo/v5 errado = 7; p = 0.179688

## Veredito pela regra registrada

- v6 **reduz o apoio falso** (25,9% → 14,8% nos casos manuais) **sem reduzir a acurácia** (65,0% → 72,5%). Pela regra do protocolo, v6 é **melhor** e é promovido.
- A diferença **não é estatisticamente significativa** com 40 casos (McNemar p ≈ 0,45). É uma melhora direcional, não uma prova.
- A taxa de contradição falsa ficou igual (17,2%).
- O ganho no dev (manuais: 62% → 86%) foi maior que no test (65% → 72,5%). A diferença é o esperado quando as regras são desenvolvidas olhando o dev, e mostra por que o test reservado é necessário.

## Erros que regras não resolvem (dev)

- Negação semântica: "não respondem criminalmente" ≈ "são inimputáveis".
- Condições diferentes no mesmo esquema: "superior a doze → vinte anos" contra "superior a oito e até doze → dezesseis anos".
- Distinções lexicais finas: "regime aberto" contra "regime semi-aberto".

Esses casos pedem um classificador semântico em português (AYORAI-PT-NLI, ADR-008), mantendo o Judge determinístico como autoridade final.
