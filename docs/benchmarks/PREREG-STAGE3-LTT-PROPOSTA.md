# Etapa 3 — Certificação de risco por LTT (ESBOÇO de pré-registro)

**Status:** PROPOSTA em discussão, não aprovada. Não executa nada e não altera a Calibration V2, a Emenda 2 nem resultados publicados.  
**Autoria:** ANDERSON AYORA

## 1. Objetivo

Certificar, por coorte, que a taxa de erro entre as decisões aceitas não ultrapassa `R_max` com confiança `1−δ`, abstendo-se nos demais casos, com garantia que continue válida mesmo que o candidato (FactCG ou E3b-01) seja escolhido depois, nos mesmos dados.

## 2. Notação

- `R_max`: risco máximo de erro permitido entre as decisões aceitas.
- `δ`: probabilidade de falha da garantia; `1−δ`: nível de confiança.
- `p1`: taxa de erro real suposta no cálculo de poder.
- Poder **não** é acurácia: é a probabilidade de o procedimento certificar quando o erro real é `p1`, sob as hipóteses do teste.

## 3. Modelo congelado

Membros, revisões, regra de combinação, calibradores IVAP (ajustados só em DEV-A) e grade de limiares fixados antes de qualquer certificação. Qualquer mudança exige nova certificação.

## 4. Família de hipóteses e multiplicidade

- Família definida antes: {candidato ∈ {FactCG, E3b-01}} × {coorte} × {limiar da grade}.
- Dentro de cada par (candidato, coorte): sequência fixa nos limiares, do mais conservador para o menos (procedimento atual da Calibration V2, com a regra da Emenda 2).
- Entre pares: Bonferroni, `δ / (número de coortes × número de candidatos)`.
- **Argumento de validade (a ser conferido na revisão):** (i) dentro de cada par, o procedimento de sequência fixa sobre a grade ordenada controla o FWER no nível `δ_par` (cada hipótese só é testada se todas as anteriores foram rejeitadas, cada uma no nível `δ_par`); (ii) entre `K` pares, a desigualdade de Bonferroni dá P(alguma rejeição falsa) ≤ `K · δ_par` = `δ`. Logo o FWER na família inteira é ≤ `δ`. Sob controle simultâneo, todas as rejeições valem ao mesmo tempo, o que cobre a escolha posterior de **um candidato dentro da família pré-especificada**, inclusive com os mesmos dados (Angelopoulos et al., "Learn then Test"). Não cobre candidatos, coortes ou limiares fora da família, nem mudanças na grade depois de ver os dados.
- **Condição de implementação:** o argumento vale para a sequência fixa **com a regra da Emenda 2** (limiares inelegíveis por amostra mínima são pulados sem teste) somente se o pulo depender apenas de quantidades que não usam os rótulos de certificação. Verificação no código (`calibration_v2/selective_ltt.py`, linhas 96–102 e 182–187 na revisão desta PR): `n_accepted` é calculado só a partir das probabilidades e do limiar, sem rótulos, e o pulo usa apenas `n_accepted < 25`. A condição é atendida; a revisão independente deve conferir.
- Holm ou testes fechados (abordagem gráfica, Bretz et al., *Statistics in Medicine* 28(4):586–604, 2009, DOI 10.1002/sim.3495) só se a integração com a sequência fixa for demonstrada formalmente e pré-registrada; nunca apenas para recuperar poder.
- O teste de superioridade da P1 (BA) é separado e não entra nesta família.

## 5. Independência das observações

O teste binomial exato supõe casos independentes. Afirmações do mesmo documento não são independentes.

Proposta primária: a amostra de certificação contém **no máximo uma afirmação por documento**, sorteada com semente pré-registrada, antes de qualquer resultado, usando o `doc_id` do cache v2. Alternativas em discussão: risco definido no nível do documento (muda o estimando) ou limites para somas dependentes (menos auditável).

Consequência para resultados já publicados: as 4 certificações da Emenda 2 foram calculadas sem essa restrição. Proposta: não reescrever o histórico; acrescentar nota de limitação por errata datada, se o mantenedor autorizar.

## 6. Tamanhos amostrais (casos aceitos por coorte, pisos robustos)

Definição: teste binomial exato unilateral de H0: risco ≥ `R_max` contra H1: risco < `R_max`, no nível `δ_par`, sobre os `n` casos aceitos; rejeita-se H0 quando o número de erros `k` satisfaz P(Bin(`n`, `R_max`) ≤ `k`) ≤ `δ_par`. Poder com taxa real `p1`: P(Bin(`n`, `p1`) ≤ `k_crit(n)`). Piso robusto = menor `n` tal que o poder é ≥ à meta para todo `n' ≥ n` (a discretização faz o poder oscilar).

**Reprodução:** `python scripts/benchmarks/phase1b/ltt_power.py --r-max 0.10 --delta-family 0.05 --pairs 11 --p1 0.03 0.05 0.07 --power 0.8`. O teste `tests/test_phase1b_ltt_power.py` confirma 168 / 367 / 1108 para esse cenário. Os demais cenários da tabela são obtidos pelo mesmo script, variando `--r-max`, `--delta-family`, `--pairs` e `--power`. São números de **planejamento**, não regras de aceitação.

`p1` = 3% / 5% / 7% quando `R_max` = 10%; `p1` = 1% / 2% / 3% quando `R_max` = 5%:

| R_max | δ por par | Poder 80% | Poder 90% | Poder 95% |
|---|---|---|---|---|
| 10% | 0,05/11 | 168 / 367 / 1108 | 210 / 454 / 1378 | 237 / 527 / 1634 |
| 10% | 0,05/22 | 193 / 420 / 1258 | 222 / 507 / 1540 | 263 / 593 / 1808 |
| 10% | 0,01/22 | 247 / 530 / 1588 | 276 / 631 / 1917 | 318 / 718 / 2209 |
| 5% | 0,05/22 | 269 / 587 / 1413 | 332 / 693 / 1745 | 362 / 797 / 2025 |
| 5% | 0,01/22 | 345 / 728 / 1791 | 409 / 863 / 2149 | 440 / 968 / 2479 |

Com uma afirmação por documento, o número disponível por coorte cai para o número de documentos; o poder deve ser recalculado com as contagens do cache v2 antes de executar.

Cenário inicial proposto para uso financeiro (não é padrão regulatório): `R_max` = 5%, `1−δ` = 99%, poder 90%, com análise de sensibilidade de custo, cobertura e abstenção antes de virar política.

## 7. Coorte não estimável

Coorte sem casos suficientes para o poder pretendido, ou sem limiar elegível: **sem garantia**, sem fallback que misture coortes, sem imputação. Menos de 25 aceitas num limiar = limiar não testável (regra existente).

## 8. Escopo da garantia

A garantia vale apenas para dados intercambiáveis com a população certificada (coorte, fonte, período, idioma, versão do modelo). Não se transfere a outros domínios (bancário, jurídico, PT-BR). Cada novo domínio exige amostra própria, rótulos humanos com concordância medida, certificação própria, monitoramento e gatilhos de recertificação.

## 9. Referências regulatórias

Ainda **não verificadas** em fonte primária nesta revisão: Resolução CMN 4.557/2017, Resolução BCB 265/2022 e a orientação do Federal Reserve sobre risco de modelos (SR 11-7, 2011; suposta revisão de 2026 não confirmada). Não serão citadas em documento aprovado antes da conferência do texto original.
