# [PROPOSTA] Revisão do desenho estatístico do RGC antes do congelamento

**Estado:** proposta atualizada conforme a decisão DEC-014 e a Emenda 5; não congela o protocolo nem altera o pré-registro ou o Judge.
**Data:** 2026-10-18
**Origem:** rodada 3 da revisão independente (item E), com simulação reproduzível em scripts/simulate_rgc_design.py.
**Dados usados:** somente rótulos sintéticos aleatórios. Nenhum caso de piloto ou do benchmark foi lido; o sistema não foi executado.
**Limite de interpretação:** esta simulação de desenho não é resultado do benchmark RGC PT-BR. O protocolo não está congelado e não existe resultado de benchmark em português.

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
- **O desbalanceamento derruba o kappa com a mesma qualidade de anotação** (o "paradoxo do kappa", Feinstein e Cicchetti, 1990). O AC1 de Gwet (2008) é menos sensível à prevalência. A primeira composição observada no piloto 01 foi desbalanceada (9 SUPPORTED, 11 REFUTED, nenhum nas outras três classes).
- **Kappa, AC1 e alfa de Krippendorff não são intercambiáveis.** Medem acordo com modelos de acaso diferentes; trocar de métrica depois de ver o número seria desvio do pré-registro.
- Landis e Koch (1977) são uma referência histórica para interpretar coeficientes de concordância, não uma norma obrigatória nem um requisito universal. A decisão deve decorrer do protocolo aprovado e da finalidade do estudo.

**Opções para o mantenedor:**

- **A — manter como está e explicitar:** "kappa de Cohen, estimativa pontual ≥ 0,6; reportar IC95% bootstrap, AC1, concordância observada e matriz de confusão como descritivos".
- **B — limite inferior do IC95% ≥ 0,6:** mais rigoroso; pela simulação, provavelmente inatingível sem anotação muito consistente.
- **C — critério duplo:** estimativa pontual de kappa ≥ 0,6 **e** AC1 ≥ 0,6; reportar os dois e o IC95%.

**Recomendação técnica:** A, com os descritivos obrigatórios. Muda o mínimo, remove a ambiguidade e torna visível o efeito da prevalência sem trocar a métrica aprovada.

## 3. Achado 2 — baseline, dependência e poder de H1

O pré-registro reserva 30% dos casos como conjunto oculto (§3.3), mas o critério primário (§5) fala em "conjunto de avaliação definido", sem nomear a partição. Com 300 casos, o oculto tem **cerca de 90**.

### Correção do modelo de simulação

A simulação anterior escolhia a classe majoritária usando os rótulos da própria partição avaliada. A decisão DEC-014 define B como baseline primário operacional e A como baseline-oráculo descritivo. A simulação atualizada:

1. gera uma partição de desenvolvimento pública de 70% e uma partição de avaliação de 30%, ambas com a mesma prevalência populacional declarada;
2. deriva B exclusivamente dos rótulos de desenvolvimento e mantém essa classe constante em toda a avaliação, com desempate pela ordem de classes declarada; calcula A separadamente a partir da própria partição de avaliação, apenas para descrição;
3. modela a correção do sistema em dois cenários: indicadores de acerto independentes da baseline e indicadores com correlação phi positiva-alvo de 0,5. O valor conjunto é limitado aos limites matematicamente possíveis; portanto, a correlação efetiva pode ser inferior a 0,5;
4. calcula IC95% da acurácia do sistema por bootstrap pareado de casos com 10.000 reamostragens e seed 20261003, e calcula margem e McNemar exato bilateral usando as funções de src/ayorai_attractor/evaluation/stats.py, as mesmas usadas por evals/ptbr/rgc_eval.py;
5. declara H1 apoiada contra B somente se **todas** as condições do critério primário forem satisfeitas: margem de pelo menos 10 pontos percentuais, limite inferior do IC95% do sistema acima da acurácia de B e McNemar exato bilateral p < 0,05. A acurácia média de A é reportada ao lado, sem participar do teste H1.

As prevalências de referência são: equilibrada (20/20/20/20/20%), desbalanceada (40/30/15/10/5%) e muito desbalanceada (55/25/10/6/4%). A acurácia de B é a proporção de rótulos da avaliação que coincidem com a classe escolhida independentemente na partição de desenvolvimento. A acurácia de A é a proporção da classe majoritária observada na própria avaliação; por usar os rótulos avaliados para escolher a classe, A é um baseline-oráculo descritivo da prevalência observada, nunca um classificador operacional e nunca a base do teste H1.

### Poder simulado com prevalência desbalanceada (40/30/15/10/5%)

Resultados de 200 repetições Monte Carlo por célula. A partição de desenvolvimento contém 70% do total correspondente (210 para avaliação n=90; 700 para avaliação n=300); ambas as partições são amostradas da mesma prevalência populacional. B é escolhido na partição de desenvolvimento; A é calculado na avaliação e reportado apenas como descritivo. As probabilidades são sintéticas e não são resultados do benchmark PT-BR.

| n avaliação | n desenvolvimento | Acurácia-alvo do sistema | Acurácia média B | Acurácia média A (descritiva) | P(H1 contra B), independência | P(H1 contra B), phi-alvo 0,5 |
|---:|---:|---:|---:|---:|---:|---:|
| 90 | 210 | 0,50 | 0,393 | 0,401 | 0,230 | 0,370 |
| 90 | 210 | 0,55 | 0,405 | 0,411 | 0,445 | 0,675 |
| 90 | 210 | 0,60 | 0,399 | 0,409 | 0,735 | 0,905 |
| 90 | 210 | 0,70 | 0,392 | 0,403 | 0,975 | 1,000 |
| 300 | 700 | 0,50 | 0,400 | 0,400 | 0,510 | 0,475 |
| 300 | 700 | 0,55 | 0,397 | 0,397 | 0,915 | 0,920 |
| 300 | 700 | 0,60 | 0,399 | 0,399 | 0,995 | 0,995 |
| 300 | 700 | 0,70 | 0,400 | 0,401 | 1,000 | 1,000 |

### Sensibilidade à prevalência

| Prevalência | n avaliação | n desenvolvimento | Acurácia-alvo | Acurácia média B | Acurácia média A (descritiva) | P(H1 contra B), independência | P(H1 contra B), phi-alvo 0,5 |
|---|---:|---:|---:|---:|---:|---:|---:|
| equilibrada (20% por classe) | 90 | 210 | 0,50 | 0,204 | 0,259 | 0,960 | 0,990 |
| equilibrada (20% por classe) | 90 | 210 | 0,55 | 0,204 | 0,261 | 0,995 | 1,000 |
| equilibrada (20% por classe) | 90 | 210 | 0,60 | 0,205 | 0,258 | 1,000 | 1,000 |
| equilibrada (20% por classe) | 90 | 210 | 0,70 | 0,199 | 0,260 | 1,000 | 1,000 |
| equilibrada (20% por classe) | 300 | 700 | 0,50 | 0,205 | 0,231 | 1,000 | 1,000 |
| equilibrada (20% por classe) | 300 | 700 | 0,55 | 0,199 | 0,231 | 1,000 | 1,000 |
| equilibrada (20% por classe) | 300 | 700 | 0,60 | 0,201 | 0,231 | 1,000 | 1,000 |
| equilibrada (20% por classe) | 300 | 700 | 0,70 | 0,199 | 0,231 | 1,000 | 1,000 |
| muito desbalanceada (55/25/10/6/4%) | 90 | 210 | 0,50 | 0,551 | 0,551 | 0,005 | 0,005 |
| muito desbalanceada (55/25/10/6/4%) | 90 | 210 | 0,55 | 0,551 | 0,551 | 0,020 | 0,040 |
| muito desbalanceada (55/25/10/6/4%) | 90 | 210 | 0,60 | 0,551 | 0,551 | 0,085 | 0,135 |
| muito desbalanceada (55/25/10/6/4%) | 90 | 210 | 0,70 | 0,545 | 0,545 | 0,520 | 0,745 |
| muito desbalanceada (55/25/10/6/4%) | 300 | 700 | 0,50 | 0,550 | 0,550 | 0,000 | 0,000 |
| muito desbalanceada (55/25/10/6/4%) | 300 | 700 | 0,55 | 0,550 | 0,550 | 0,015 | 0,015 |
| muito desbalanceada (55/25/10/6/4%) | 300 | 700 | 0,60 | 0,549 | 0,549 | 0,115 | 0,085 |
| muito desbalanceada (55/25/10/6/4%) | 300 | 700 | 0,70 | 0,552 | 0,552 | 0,875 | 0,930 |

**Interpretação importante:** o poder depende da prevalência e da diferença real entre a acurácia do sistema e a classe majoritária. Com prevalência 55/25/10/6/4%, uma acurácia de 0,60 não supera a baseline majoritária esperada de 0,55 em 10 pontos percentuais; não se deve esperar que H1 passe. Os valores de sensibilidade não autorizam escolher a prevalência depois de ver resultados reais.

Leituras:

- **Se a avaliação confirmatória usar só os ~90 ocultos, um sistema com acurácia-alvo de 0,55 na distribuição 40/30/15/10/5 tem cerca de 45% de chance de satisfazer H1 no cenário independente.** O estudo tem poder limitado para efeitos moderados.
- O cenário positivamente correlacionado não significa que a acurácia do sistema aumente: a acurácia-alvo permanece fixa. A dependência muda a quantidade de discordâncias pareadas entre sistema e baseline e, portanto, a probabilidade de McNemar atingir o limiar.
- O Judge é determinístico e não é treinado nem ajustado com o benchmark. Isso não elimina o risco de contaminação de quem desenvolve olhando casos públicos.

**Opções para o mantenedor:**

- **A — H1 no conjunto oculto (~90), declarando o poder limitado:** mais protegido contra vazamento; pode não detectar melhorias moderadas.
- **B — H1 nos 300 casos e análise de sensibilidade no oculto:** maior poder em cenários relevantes; exige garantir que nenhum ajuste do sistema use os 210 públicos entre o congelamento e a execução única.
- **C — aumentar a meta de casos** para que o oculto tenha poder adequado (por exemplo, ~150 ocultos): mais trabalho de anotação.

**Recomendação técnica:** B, mantendo o conjunto oculto como análise de sensibilidade e alerta de possível contaminação. O sistema deve ficar congelado por commit antes da execução, e a execução deve registrar o SHA. A decisão continua pendente do mantenedor; esta proposta não emenda o protocolo nem o pré-registro.

**Atualização datada (2026-10-21) — baseline B/A:** a decisão sobre a definição B primária e A descritiva foi aprovada pelo mantenedor e incorporada pela Emenda 6 na PR #288. A frase acima registra o estado da proposta em 2026-10-18 e permanece como histórico, não como status atual da decisão de baseline. Esta atualização não resolve o escopo confirmatório de H1, o bootstrap agrupado, o critério de concordância nem a regra de registros ausentes versus predições inválidas; esses itens permanecem decisões científicas separadas. O protocolo continua [PROPOSTO], sem congelamento ou execução autorizada.

## 4. Achado 3 — independência entre casos

Todos os trechos vêm de um único ato normativo, e vários casos podem tratar do mesmo artigo. O bootstrap atual reamostra casos como se fossem independentes, o que pode estreitar os intervalos quando há casos correlacionados do mesmo dispositivo.

**Proposta (implementável sem mudar o critério primário):** registrar em cada caso o artigo de origem e reportar, como **análise secundária**, um bootstrap por agrupamento (reamostrando artigos). Se o intervalo agrupado for muito mais largo, isso entra como limitação. Exige um campo novo no esquema dos casos, que precisa estar definido antes do congelamento. **Depende de decisão do mantenedor.**

## 5. Pontos verificados que não exigem mudança

- **Baseline primário B (DEC-014):** a classe majoritária é derivada exclusivamente da partição pública de desenvolvimento (70%), registrada antes de qualquer execução no conjunto oculto, e aplicada sem alteração à avaliação confirmatória. A definição é operacional e não usa rótulos avaliados para escolher a classe.
- **Baseline descritivo A:** a classe majoritária calculada na partição avaliada é reportada somente como “baseline-oráculo descritivo da prevalência observada”; nunca é apresentada como classificador nem usada como base do teste H1.
- **Comparações múltiplas:** o pré-registro só testa H1. Métricas por classe, por categoria e o estrato rectified são descritivos e não geram teste de hipótese; recomenda-se declarar isso no relatório para impedir leitura de "significância" em estratos.
- **McNemar exato bilateral** é adequado para comparar classificadores nos mesmos casos; a implementação usada é mcnemar_exact_pvalue em src/ayorai_attractor/evaluation/stats.py. Não se recomenda trocar o método aprovado nesta proposta.
- **Compromisso do conjunto oculto:** publicar o SHA-256 do arquivo ajuda a demonstrar depois que ele não mudou. Isso **não** protege contra vazamento de conteúdo; isso depende de controle de acesso e procedimento documentado.

## 6. Estado das decisões

A decisão sobre baseline foi tomada pelo mantenedor em 2026-10-18 e registrada em [DEC-014](../DECISIONS-PENDING.md#dec-014--baseline-primário-e-descritivo-do-rgc). A Emenda 5 registra apenas essa definição no protocolo; não congela o protocolo nem resolve as decisões pendentes sobre concordância, partição confirmatória ou bootstrap agrupado. Os demais itens desta proposta continuam sujeitos a decisões próprias.

## Referências

- Cohen, J. (1960). A coefficient of agreement for nominal scales. *Educational and Psychological Measurement*, 20(1), 37–46. DOI: https://doi.org/10.1177/001316446002000104
- Feinstein, A. R.; Cicchetti, D. V. (1990). High agreement but low kappa: I. The problems of two paradoxes. *Journal of Clinical Epidemiology*, 43(6), 543–549. DOI: https://doi.org/10.1016/0895-4356(90)90058-8
- Gwet, K. L. (2008). Computing inter-rater reliability and its variance in the presence of high agreement. *British Journal of Mathematical and Statistical Psychology*, 61(1), 29–48. DOI: https://doi.org/10.1348/000711006X126600
- Krippendorff, K. (2018). *Content Analysis: An Introduction to Its Methodology*, 4ª ed. SAGE. Página da editora: https://us.sagepub.com/en-us/nam/content-analysis/book258450
- Dietterich, T. G. (1998). Approximate statistical tests for comparing supervised classification learning algorithms. *Neural Computation*, 10(7), 1895–1923. DOI: https://doi.org/10.1162/089976698300017197
- Landis, J. R.; Koch, G. G. (1977). The measurement of observer agreement for categorical data. *Biometrics*, 33(1), 159–174. DOI: https://doi.org/10.2307/2529310. Referência histórica, não norma obrigatória.

## Reprodução

Comando: `python scripts/simulate_rgc_design.py`.

Execução registrada no GitHub Actions: run [39090642680](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/39090642680), SHA `4454e8faa7dd19ade429adcd6578663af2060056`, Python 3.12 e NumPy 2.3.3. O artefato `rgc-design-simulation-8edecc64a710be1818321185c8f29637ee939e1d` preserva a saída completa. Seed 20261003; 200 repetições por célula; IC95% com 10.000 reamostragens pareadas. Os valores são exclusivamente sintéticos e não são resultado de benchmark. e seed 20261003. NumPy é usado apenas como aceleração opcional; sem ele, o script usa diretamente o bootstrap em Python do executor. A saída completa da execução que fundamenta esta tabela deve ser anexada à PR após executar o script no ambiente de desenvolvimento. Não houve execução local deste arquivo nesta sessão; os valores da tabela foram produzidos por uma simulação independente com a mesma sequência de índices bootstrap e o mesmo modelo declarado, e precisam ser confirmados executando o arquivo atualizado antes de aprovar a PR.


**Atualização datada (2026-10-21) — DEC-019 aprovada, opção A:** a recomendação histórica das linhas acima que classificava o bootstrap por artigo como análise secundária é superada pela decisão explícita do mantenedor. A Emenda 9 do pré-registro e do protocolo define o bootstrap por cluster de artigo como primário e o bootstrap por caso como sensibilidade. O campo operacional é `bootstrap_cluster_id`; casos que dependem conjuntamente de múltiplos artigos sem um artigo principal usam uma chave `bundle:` com IDs canônicos únicos em ordem lexical, separados por `+`. Esta nota não reescreve a proposta histórica, não congela o protocolo e não autoriza execução RGC.
