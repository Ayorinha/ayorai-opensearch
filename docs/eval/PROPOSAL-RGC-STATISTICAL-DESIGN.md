# [PROPOSTA] Revisão do desenho estatístico do RGC antes do congelamento

**Estado:** proposta para decisão do mantenedor. **Não altera** o pré-registro, o protocolo, as decisões DEC-007 a DEC-011, o executor nem o Judge.
**Data:** 2026-10-17
**Origem:** rodada 3 da revisão independente (item E), com simulação reproduzível em `scripts/simulate_rgc_design.py`.
**Dados usados:** somente rótulos sintéticos aleatórios. Nenhum caso de piloto ou do benchmark foi lido; o sistema não foi executado.

## 1. Por que decidir agora

O pré-registro (§5) proíbe mudar critérios depois de ver os dados. Três pontos do desenho atual têm leitura ambígua ou consequência pouco visível e precisam ser fixados **antes do congelamento**.

## 2. Achado 1 — o que significa "kappa ≥ 0,6"

O protocolo (fase 5) exige "kappa ≥ 0,6" para promover o conjunto a v1, sem dizer se vale a **estimativa pontual** ou o **limite inferior do IC95%**.

Simulação com dois anotadores, cinco classes, 200 repetições por cenário. "Acurácia" é a chance de cada anotador dar o rótulo de referência.

| Prevalência das classes | Acurácia de cada anotador | n | kappa (mediana) | AC1 (mediana) | P(kappa ≥ 0,6) | P(limite inferior IC95% ≥ 0,6) |
|---|---|---|---|---|---|---|
| equilibrada | 0,85 | 300 | 0,66 | 0,66 | 0,98 | 0,43 |
| desbalanceada (40/30/15/10/5%) | 0,85 | 300 | 0,64 | 0,67 | 0,85 | 0,17 |
| muito desbalanceada (55/25/10/6/4%) | 0,85 | 300 | 0,59 | 0,67 | 0,41 | 0,01 |
| desbalanceada | 0,90 | 300 | 0,74 | 0,77 | 1,00 | 0,99 |

Leituras:

- **Exigir o limite inferior ≥ 0,6 só é realista com anotadores muito consistentes (cerca de 90% de acerto cada).** Com 85%, a meta falha na maior parte das vezes.
- **O desbalanceamento derruba o kappa com a mesma qualidade de anotação** (o "paradoxo do kappa", Feinstein e Cicchetti, 1990). O AC1 de Gwet (2008) é muito menos sensível à prevalência. A primeira composição observada no piloto 01 já foi desbalanceada (9 SUPPORTED, 11 REFUTED, nenhum nas outras três classes).
- **Kappa, AC1 e alfa de Krippendorff não são intercambiáveis.** Medem acordo descontado do acaso com modelos diferentes de acaso; trocar de métrica depois de ver o número seria desvio do pré-registro.

**Opções para o mantenedor:**

- **A — manter como está e explicitar:** "kappa de Cohen, estimativa pontual ≥ 0,6; reportar IC95% bootstrap, AC1, concordância observada e matriz de confusão como descritivos".
- **B — limite inferior do IC95% ≥ 0,6:** mais rigoroso; pela simulação, provavelmente inatingível sem anotação muito consistente.
- **C — critério duplo:** estimativa pontual de kappa ≥ 0,6 **e** AC1 ≥ 0,6; reportar os dois e o IC95%.

**Recomendação técnica:** A, com os descritivos obrigatórios. Muda o mínimo, remove a ambiguidade e torna visível o efeito da prevalência sem trocar a métrica aprovada.

## 3. Achado 2 — em qual partição H1 é avaliada, e com que poder

O pré-registro reserva 30% dos casos como conjunto oculto (§3.3), mas o critério primário (§5) fala em "conjunto de avaliação definido", sem nomear a partição. Com 300 casos, o oculto tem **cerca de 90**.

Probabilidade de H1 ser declarada apoiada pelas três condições do §5 (margem ≥ 10 pp, limite inferior do IC95% acima da baseline, McNemar exato p < 0,05). Baseline com 40% de acerto; sistema e baseline com erros independentes (premissa da simulação); 2.000 repetições.

| Casos avaliados | Acurácia real do sistema | P(H1 apoiada) |
|---|---|---|
| 90 (só o oculto) | 0,55 (+15 pp) | 0,49 |
| 90 | 0,60 (+20 pp) | 0,72 |
| 210 (só o público) | 0,55 | 0,86 |
| 300 (todos) | 0,55 | 0,90 |
| 300 | 0,60 | 1,00 |

Leituras:

- **Se a avaliação confirmatória for só nos ~90 ocultos, um sistema realmente 15 pp melhor que a baseline tem cerca de 50% de chance de ser declarado sem suporte.** O estudo teria pouco poder para efeitos moderados.
- **O Judge é determinístico e não é treinado nem ajustado com o benchmark.** O 70% "de desenvolvimento" não alimenta nenhum ajuste. Isso enfraquece o motivo clássico para avaliar só no oculto, mas não elimina o risco de contaminação de quem desenvolve olhando casos públicos.

**Opções para o mantenedor:**

- **A — H1 no conjunto oculto (~90), declarando o poder limitado:** mais protegido contra vazamento; pouco poder.
- **B — H1 nos 300 casos e análise de sensibilidade no oculto:** mais poder; exige garantir que nenhum ajuste do sistema use os 210 públicos entre o congelamento e a execução única.
- **C — aumentar a meta de casos** para que o oculto tenha poder adequado (por exemplo, ~150 ocultos): mais trabalho de anotação.

**Recomendação técnica:** B. O sistema fica congelado por commit antes da execução, e o executor já registra o SHA. Isso protege contra ajuste e preserva o poder. O oculto continua útil como verificação de vazamento: uma diferença grande entre público e oculto seria sinal de alerta.

## 4. Achado 3 — independência entre casos

Todos os trechos vêm de um único ato normativo, e vários casos podem tratar do mesmo artigo. O bootstrap atual reamostra casos como se fossem independentes, o que tende a **estreitar** os intervalos quando há casos correlacionados do mesmo dispositivo.

**Proposta (implementável sem mudar o critério primário):** registrar em cada caso o artigo de origem e reportar, como **análise secundária**, um bootstrap por agrupamento (reamostrando artigos). Se o intervalo agrupado for muito mais largo, isso entra como limitação. Exige um campo novo no esquema dos casos, que precisa estar definido antes do congelamento. **Depende de decisão do mantenedor.**

## 5. Pontos verificados que não exigem mudança

- **Baseline:** calculada com os rótulos da própria partição avaliada (§4 item 6). Isso favorece a baseline, porque ela "conhece" a classe majoritária real, o que torna o teste de H1 conservador. Aceitável e já declarado.
- **Comparações múltiplas:** o pré-registro só testa H1. Métricas por classe, por categoria e o estrato `rectified` são descritivas e não geram teste de hipótese, então não precisam de correção. Recomenda-se escrever isso explicitamente no relatório para impedir leitura de "significância" em estratos.
- **McNemar exato bilateral** é adequado para comparar dois classificadores nos mesmos casos (Dietterich, 1998). BCa ou testes de permutação não mudariam a conclusão de forma material com n ≥ 90; não se recomenda trocar o método aprovado.
- **Compromisso do conjunto oculto:** publicar o SHA-256 do arquivo é suficiente para provar depois que ele não mudou. Ele **não** protege contra vazamento de conteúdo; isso depende de controle de acesso (quem guarda o arquivo, onde, com que backup), que deve ser registrado em procedimento escrito antes da separação.

## 6. Decisões pedidas ao mantenedor

1. Leitura do critério de concordância: A, B ou C da seção 2.
2. Partição do critério primário H1: A, B ou C da seção 3.
3. Incluir o campo de artigo de origem para o bootstrap agrupado (seção 4): sim ou não.

Depois da decisão, as escolhas entram como **Emenda 5** do protocolo e nota datada no pré-registro, antes do congelamento.

## Referências

- Cohen, J. (1960). A coefficient of agreement for nominal scales. *Educational and Psychological Measurement*, 20(1), 37–46.
- Feinstein, A. R.; Cicchetti, D. V. (1990). High agreement but low kappa: I. The problems of two paradoxes. *Journal of Clinical Epidemiology*, 43(6), 543–549.
- Gwet, K. L. (2008). Computing inter-rater reliability and its variance in the presence of high agreement. *British Journal of Mathematical and Statistical Psychology*, 61(1), 29–48.
- Krippendorff, K. (2018). *Content Analysis: An Introduction to Its Methodology*, 4ª ed. SAGE.
- Dietterich, T. G. (1998). Approximate statistical tests for comparing supervised classification learning algorithms. *Neural Computation*, 10(7), 1895–1923.
- Landis, J. R.; Koch, G. G. (1977). The measurement of observer agreement for categorical data. *Biometrics*, 33(1), 159–174.

## Reprodução

```bash
python scripts/simulate_rgc_design.py
```

Semente fixa `20261003`; cerca de três minutos. A saída completa da execução usada neste documento está na descrição da PR.
