# Pré-registro — Calibração v2 do AYORAI ATTRACTOR

**Status:** proposta pré-registrada; não congelada até aprovação explícita do mantenedor  
**Autoria:** ANDERSON AYORA  
**Escopo desta PR:** documentação exclusivamente. Nenhum código, execução de benchmark, inferência, alteração de dados ou avaliação TEST.

## 1. Objetivo e princípios

Este documento pré-registra uma avaliação em três camadas para calibração de limiares, calibração probabilística e abstenção seletiva.

- O Judge determinístico mantém autoridade sobre o veredito; probabilidades e métodos estatísticos são sinais de avaliação, não autorização para alterar contratos.
- A política oficial de decisão existente permanece preservada.
- DEV é o único conjunto permitido para desenvolvimento e calibração.
- TEST permanece intocado, isolado e exclusivamente avaliativo. Não será usado para seleção, ajuste, escolha de limiar, combinação, depuração ou decisões metodológicas.
- Nenhuma execução, resultado, métrica ou limiar empírico é alegado neste pré-registro.

## 2. Separação pré-registrada de DEV

Antes de qualquer análise da calibração v2, a amostra DEV elegível será dividida em duas partes disjuntas:

| Partição | Proporção | Uso permitido |
|---|---:|---|
| DEV-A | 50% | Seleção de modelo, limiar, combinação e decisões de desenvolvimento das Camadas 1 e 2 |
| DEV-B | 50% | Exclusivamente certificação da regra de abstenção da Camada 3 |

A divisão será **estratificada por coorte**, com seed fixa **20261106**. O procedimento, a unidade de amostragem, a lista de coortes, o manifesto de entrada e o hash do manifesto deverão ser registrados antes da execução. A divisão deve ser reproduzível e não poderá ser refeita em função de resultados.

**DEV-B nunca orienta escolhas.** Não será utilizado para escolher modelo, método, limiar, combinação, bins, grade, regra de confiança ou qualquer parâmetro. DEV-B só poderá ser consultado para a certificação pré-especificada da Camada 3. Se a certificação falhar, não se poderá ajustar a regra usando DEV-B; uma nova proposta exigirá novo pré-registro e uma fonte de certificação independente.

TEST não participa dessa divisão e permanece intocado.

## 3. Camada 1 — Limiar de decisão

### 3.1 Modos de decisão

Serão reportados separadamente:

1. **Modo oficial dev_calibrated_by_cohort:**
   - grade de limiares de 0,01 a 0,99, em passos de 0,01;
   - predição positiva quando score > threshold (comparação estrita);
   - seleção por coorte maximizando balanced accuracy (BA);
   - empate resolvido pelo menor limiar.
2. **Modo de referência fixed_0.5:**
   - predição positiva quando score > 0.5;
   - sem calibração de limiar por coorte.

O modo oficial não será substituído por cross-fitting. O cross-fitting será uma avaliação adicional de generalização do procedimento de escolha de limiar.

### 3.2 BA aparente e BA cross-fitted

Para cada coorte, reportar lado a lado:

- **BA aparente:** BA calculada sobre os mesmos dados DEV-A usados para selecionar o limiar por coorte. Identificar explicitamente como estimativa aparente, potencialmente otimista.
- **BA cross-fitted (honesta):** validação cruzada estratificada de **5 folds por coorte**, com seed fixa pré-especificada. Em cada rodada, selecionar o limiar apenas nos quatro folds de treino e avaliar no fold retido. Cada observação recebe predição out-of-fold. Nenhum fold retido participa da escolha do limiar que o avalia.

A seed exata do cross-fitting, o algoritmo de estratificação, a ordem determinística dos registros e o tratamento de coortes pequenas deverão ser registrados antes da execução, sem escolha baseada em resultados. Se não for possível formar cinco folds válidos contendo ambas as classes em cada coorte, reportar a limitação e não reduzir folds silenciosamente.

Reportar BA aparente e BA cross-fitted, diferença entre elas, tamanho amostral e resultados por coorte e agregados. O modo fixed_0.5 será avaliado nas mesmas divisões para comparação pareada.

## 4. Camada 2 — Probabilidade calibrada

### 4.1 Método

Avaliar **Venn-Abers indutivo (IVAP)** por modelo, com saída intervalar **[p0, p1]** e probabilidade combinada conforme a definição do método. A implementação e a fórmula de combinação deverão ser identificadas e versionadas antes da execução; não se escolherá a variante após observar resultados.

Avaliar também a variante **Mondrian por coorte** quando a coorte tiver **pelo menos 200 exemplos de calibração**. A contagem se refere exclusivamente à partição de calibração permitida. Coortes abaixo desse mínimo não recebem estimativa Mondrian por coorte; reportar como indisponível, sem extrapolação ou agrupamento oportunista.

O protocolo deverá esclarecer que IVAP/Mondrian é ajustado somente com dados permitidos de calibração DEV-A e que qualquer avaliação de desempenho deve ser feita em dados não usados no ajuste, por procedimento pré-especificado. DEV-B não poderá ser usado para escolher métodos ou parâmetros das Camadas 1 e 2.

### 4.2 Métricas threshold-free

Reportar:
- AUROC;
- AUPRC, informando a prevalência da classe positiva;
- Brier score;
- log-loss;
- ECE adaptativo com **15 bins definidos por quantis**;
- diagrama de confiabilidade agregado.

A definição de ECE (incluindo regra para empates nos quantis, bins vazios e probabilidades repetidas) deverá ser congelada antes da execução. Informar tamanho de cada bin, frequência observada e confiança média. A agregação do diagrama deverá ser descrita, sem ocultar diferenças entre coortes.

Métricas probabilísticas serão apresentadas por modelo e coorte, com agregados claramente definidos. Não comparar ECE entre populações sem reportar prevalência e composição dos dados.

## 5. Camada 3 — Abstenção seletiva com garantia

### 5.1 Objetivo e método

Objetivo de certificação: **erro ≤ 10% entre as respostas aceitas**, equivalente a pelo menos 90% de acerto nas respostas dadas, com garantia estatística pré-especificada.

Aplicar **Learn then Test (LTT)**, conforme Angelopoulos et al., *Learn then Test: A Simple Framework for Risk Control*, arXiv:2110.01052:

- definir previamente a grade de limiares de confiança;
- para cada limiar, calcular o p-valor binomial exato para a hipótese de que a taxa de erro entre respostas aceitas é **maior que 10%**;
- executar fixed-sequence testing, do limiar mais conservador ao menos conservador, conforme ordem pré-registrada;
- nível de significância **δ = 0,05**;
- exigir **mínimo de 25 casos aceitos por limiar** para que o teste seja elegível;
- selecionar a maior cobertura entre os limiares certificados pelo procedimento, respeitando integralmente a sequência e as regras de parada.

A grade, a ordenação, a regra de parada, o tratamento de p-valores iguais e o comportamento quando nenhum limiar é certificado deverão ser fixados antes da execução. Não se poderá alterar a sequência ou o conjunto de limiares após observar DEV-B.

### 5.2 Certificação por coorte

A garantia será avaliada por coorte (Mondrian). Para a afirmação simultânea entre coortes, aplicar correção de **Bonferroni** sobre o número de coortes incluídas na família de hipóteses, com δ familiar = 0,05. O conjunto de coortes e o número de testes da família deverão ser congelados antes da certificação.

Para cada coorte, reportar:
- número de exemplos;
- número e proporção de respostas aceitas (cobertura);
- número de erros entre aceitas;
- taxa de erro observada e acerto observado;
- p-valor exato;
- limiar selecionado ou indicação de ausência de certificação;
- nível de significância ajustado;
- status da certificação e limitações.

Coortes sem pelo menos 25 respostas aceitas em um limiar não podem ser declaradas certificadas nesse limiar. Não agregar coortes não certificadas para sugerir garantia individual.

### 5.3 Curva acerto × cobertura e AURC

Reportar a curva **acerto × cobertura** em todos os limiares pré-registrados, incluindo pontos não certificados, identificando-os visualmente como descritivos. Reportar AURC (Area Under the Risk-Coverage Curve), com definição de integração, normalização e tratamento dos empates pré-especificados.

AURC é uma métrica descritiva de seletividade e **não substitui** a certificação LTT. Não interpretar a curva ou AURC como garantia de risco.

### 5.4 Integração com a política de resposta

A decisão de abstenção será mapeada para **ResponsePolicy abstain**, sem alteração do contrato de resposta, do esquema de saída ou da autoridade do Judge. A camada de calibração não poderá emitir um veredito alternativo nem contornar a política existente.

## 6. Suposição de distribuição

A validade da garantia e a interpretação dos resultados dependem da suposição de que **DEV e TEST provêm da mesma distribuição** (incluindo prevalência, coortes, condições de coleta e relação entre sinais e rótulos).

Essa suposição não é demonstrada pelo procedimento. Mudanças de distribuição, drift, diferenças de prevalência ou mudança na qualidade da anotação podem invalidar a garantia e degradar cobertura e risco. A eventual avaliação TEST, se autorizada em etapa futura, deverá ser estritamente posterior, isolada e não poderá retroalimentar escolhas.

## 7. Política de alegações e comunicação

A alegação permitida, quando efetivamente certificada, deverá explicitar conjuntamente acerto, cobertura e garantia. Formato recomendado:

> “Entre as respostas dadas, foi certificado acerto de pelo menos 90%, com cobertura de X% e garantia 1−δ, sob as hipóteses e o protocolo pré-registrados.”

Substituir **X** e **δ** somente por valores efetivamente calculados e certificados, com identificação da população, coorte ou conjunto de coortes e método de correção.

É proibido afirmar simplesmente **“90% de acurácia”** quando o resultado se refere apenas às respostas aceitas por um sistema com abstenção. A cobertura deve acompanhar sempre a taxa de acerto seletivo. Não usar “garantido” sem indicar o nível de confiança, a unidade/população coberta, as hipóteses e o procedimento estatístico.

Nenhum resultado, certificação, desempenho ou superioridade é afirmado por este documento.

## 8. Registro de execução futura

Antes de qualquer execução futura, registrar:
- aprovação e versão deste pré-registro;
- hashes dos manifests e artefatos de dados DEV usados;
- seeds e versões de bibliotecas;
- modelos e versões;
- definições finais das grades, folds, bins e regras de parada;
- código e ambiente reprodutível;
- desvios do protocolo, justificativa e impacto;
- resultados e limitações, sem exposição de casos ou rótulos TEST.

Qualquer mudança metodológica após a observação de resultados deverá ser documentada como nova versão, sem reescrever retroativamente este pré-registro.

## Referência

Angelopoulos, A. N. et al. **Learn then Test: A Simple Framework for Risk Control.** arXiv:2110.01052. https://arxiv.org/abs/2110.01052
