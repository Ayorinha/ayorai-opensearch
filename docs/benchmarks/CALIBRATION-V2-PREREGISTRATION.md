# Pré-registro — Calibração v2 do AYORAI ATTRACTOR

**Status:** proposta pré-registrada; não congelada até aprovação explícita do mantenedor  
**Autoria:** ANDERSON AYORA  
**Escopo:** documentação exclusivamente. Nenhum código, execução de benchmark, inferência, alteração de dados ou avaliação TEST.

## 1. Objetivo e princípios

Este documento fixa, antes de qualquer execução, o protocolo de calibração v2 em três camadas: seleção de limiar, calibração probabilística e abstenção seletiva com controle estatístico de risco.

- O Judge determinístico mantém autoridade sobre o veredito. Probabilidades e métodos estatísticos são sinais de avaliação, não autorização para alterar contratos.
- A política oficial de decisão existente permanece preservada.
- A calibração e a certificação usam exclusivamente o split DEV.
- TEST permanece intocado, isolado e exclusivamente avaliativo. Não será usado para seleção, ajuste, escolha de limiar, combinação, depuração ou decisões metodológicas.
- Nenhum resultado, certificação, desempenho ou superioridade é alegado por este pré-registro.

## 2. Dados e população de calibração

### 2.1 DEV completo e pinagem

A calibração v2 utilizará o **DEV completo: 30.420 casos**, sem amostragem limitada a 500 casos por coorte.

| Campo | Valor fixado |
|---|---|
| Dataset | lytang/LLM-AggreFact |
| Split/arquivo | dev — data/dev-00000-of-00001.parquet |
| Total de casos | **30.420** |
| Revisão imutável do dataset | **981dfd0bd8e58e7238a9ab92b2e6ea44bce918e4** |
| Tamanho do shard | **35.453.136 bytes** |
| SHA-256 do shard DEV | **ca9a5bda9561bbc6f7327ef81ab41727fa10e96f96e9dc74ef32ba3af3c1d8a8** |
| Campo de coorte | dataset |
| Número de coortes | **11** |

A revisão, o arquivo, o tamanho e o SHA-256 acima correspondem ao pin DEV versionado em configs/benchmarks/llm-aggrefact-dev-pin.json e ao manifesto agregado do piloto. Não substituir o hash SHA-256 do arquivo por hash Git de blob, hash Xet ou ETag.

As 11 coortes são: AggreFact-CNN, AggreFact-XSum, ClaimVerify, ExpertQA, FactCheck-GPT, Lfqa, RAGTruth, Reveal, TofuEval-MediaS, TofuEval-MeetB e Wice. Os nomes nativos do campo dataset serão preservados.

**Justificativa para usar o DEV completo:** a certificação simultânea por coorte, com Bonferroni em nível δ/11, e a exigência de pelo menos 200 exemplos de calibração para IVAP/Mondrian por coorte precisam de uma base substancialmente maior do que uma amostra limitada a 250 casos por partição. O uso do DEV completo evita reduzir artificialmente a informação disponível. A elegibilidade Mondrian continuará condicionada à contagem efetiva de pelo menos 200 exemplos na partição de calibração de cada coorte; coortes abaixo do mínimo serão explicitamente marcadas como indisponíveis, sem agrupamento oportunista.

### 2.2 Separação DEV-A / DEV-B

O DEV completo será dividido em duas partições disjuntas, estratificadas por coorte, com a seed de divisão já registrada no protocolo:

| Partição | Proporção | Uso permitido |
|---|---:|---|
| DEV-A | 50% | Camadas 1 e 2: seleção de limiar e ajuste/avaliação probabilística por cross-fitting |
| DEV-B | 50% | Exclusivamente certificação LTT da Camada 3 |

A divisão permanece determinística e não poderá ser refeita em função dos resultados. DEV-B nunca orienta escolhas de modelo, método, limiar, combinação, bins, grade, regra de confiança ou qualquer parâmetro das Camadas 1 e 2. Se a certificação falhar, não será permitido ajustar a regra usando DEV-B; uma nova proposta exigirá novo pré-registro e uma fonte de certificação independente.

O cross-fitting interno às Camadas 1 e 2 tem seed própria e regras fixadas na seção 3. TEST não participa da divisão e permanece intocado.

## 3. Camada 1 — Limiar de decisão

### 3.1 Modos reportados

Serão reportados separadamente:

1. **Modo oficial dev_calibrated_by_cohort**
   - Grade de limiares de 0,01 a 0,99, em passos de 0,01.
   - Predição positiva quando score > threshold (comparação estrita).
   - Seleção por coorte maximizando balanced accuracy (BA).
   - Empate resolvido pelo menor limiar.
2. **Modo de referência fixed_0.5**
   - Predição positiva quando score > 0,5.
   - Sem calibração de limiar por coorte.

O modo oficial não será substituído por cross-fitting. O cross-fitting será uma avaliação adicional, honesta e pré-especificada da generalização do procedimento de escolha de limiar.

### 3.2 BA aparente e BA cross-fitted

Para cada coorte, reportar lado a lado:

- **BA aparente:** BA calculada nos mesmos dados DEV-A usados para selecionar o limiar por coorte. Identificar explicitamente como estimativa aparente e potencialmente otimista.
- **BA cross-fitted:** validação cruzada de **5 folds**, estratificada conjuntamente por coorte e classe. A seed é **20261107**. Dentro de cada coorte, os registros serão ordenados deterministicamente por record_id antes da atribuição dos folds; a implementação deverá preservar essa ordem como parte da reprodução.

Em cada rodada, selecionar o limiar apenas nos quatro folds de treino e avaliar no fold retido. Cada observação recebe uma predição out-of-fold; nenhum fold retido participa da escolha do limiar que o avalia. Não reduzir silenciosamente o número de folds. Se uma coorte não permitir cinco folds válidos contendo ambas as classes, registrar a limitação e não apresentar BA cross-fitted como estimativa válida para essa coorte.

Reportar BA aparente, BA cross-fitted, diferença entre ambas, tamanho amostral e resultados por coorte e agregados. O modo fixed_0.5 será avaliado nas mesmas divisões para comparação pareada.

## 4. Camada 2 — Probabilidade calibrada

### 4.1 IVAP e probabilidade combinada

Avaliar **Venn-Abers indutivo (IVAP)**, de Vovk et al., por modelo, com saída intervalar [p0, p1]. A probabilidade combinada fica fixada em:

**p = p1 / (1 − p0 + p1)**

Não serão avaliadas variantes alternativas de combinação nesta calibração v2. A fórmula acima é a regra única pré-registrada.

O ajuste e a avaliação da Camada 2 serão realizados por **cross-fitting dentro do DEV-A, com 5 folds e a mesma seed 20261107** da Camada 1. Os folds serão estratificados por coorte e classe, com ordenação determinística por record_id. Em cada rodada, ajustar o IVAP usando somente os quatro folds de treino e avaliar a probabilidade combinada no fold retido. Cada caso de DEV-A terá uma probabilidade out-of-fold; nenhum rótulo do fold avaliado poderá participar do ajuste do calibrador daquela rodada.

Avaliar a variante **Mondrian por coorte** somente quando houver **pelo menos 200 exemplos de calibração** efetivamente disponíveis para o ajuste correspondente. A contagem deve ser registrada por coorte e fold. Coortes ou ajustes abaixo de 200 não recebem estimativa Mondrian; reportar como indisponível, sem extrapolação, pooling oportunista ou relaxamento do mínimo.

DEV-B não será usado para escolher método, fórmula ou parâmetros da Camada 2.

### 4.2 Métricas probabilísticas

Reportar por modelo e coorte, com agregados claramente definidos:

- AUROC;
- AUPRC, informando a prevalência da classe positiva;
- Brier score;
- log-loss;
- ECE adaptativo com **15 bins por quantis da probabilidade calibrada**;
- diagrama de confiabilidade.

### 4.3 Regra fixa do ECE

A construção dos 15 bins fica definida da seguinte forma:

1. Calcular os quantis sobre as probabilidades calibradas out-of-fold.
2. Probabilidades empatadas permanecem no mesmo bin; um valor repetido nunca será separado entre bins apenas para atingir tamanhos iguais.
3. Bins vazios serão descartados do cálculo do ECE e sua quantidade será registrada explicitamente.
4. Se os empates impedirem a formação de 15 bins não vazios, usar os bins não vazios resultantes, sem dividir empates artificialmente.
5. Reportar, para cada bin não vazio, tamanho, confiança média e frequência observada; reportar também o número de bins vazios descartados.

Não comparar ECE entre populações sem reportar prevalência e composição dos dados.

## 5. Camada 3 — Abstenção seletiva com garantia LTT

### 5.1 Probabilidade, confiança e regra de decisão

A Camada 3 utiliza a probabilidade calibrada p produzida pela Camada 2 e calcula a confiança:

**c = max(p, 1 − p)**

Para cada limiar t, aplicar exatamente:

- **SUPPORTED** se p ≥ t;
- **NOT_SUPPORTED** se p ≤ 1 − t;
- **abstenção** nos demais casos.

A abstenção será mapeada para ResponsePolicy abstain, sem alterar o contrato de resposta, o esquema de saída ou a autoridade do Judge.

No único ponto de sobreposição das desigualdades — p = 0,5 quando t = 0,50 — aplicar a regra conservadora de desempate: **abster-se**. Essa exceção evita emitir qualquer um dos dois vereditos quando a probabilidade é exatamente neutra.

### 5.2 Grade e sequência de testes

A grade de confiança fica fixada em:

**t ∈ {0,99; 0,98; 0,97; …; 0,51; 0,50}**

Os limiares serão testados exatamente nessa ordem, do mais conservador ao menos conservador. Um caso é aceito quando c ≥ t, respeitada a regra de desempate acima.

Aplicar Learn then Test (LTT) por fixed-sequence testing:

- Para cada t, testar a hipótese nula de que a taxa de erro entre respostas aceitas é maior que 10%.
- Calcular o p-valor binomial exato correspondente.
- Nível familiar δ = **0,05**.
- Aplicar Bonferroni para as **11 coortes**, com nível por coorte **δ/11 = 0,05/11**.
- Exigir **mínimo de 25 respostas aceitas** na coorte para que o teste naquele limiar seja elegível.
- Prosseguir para o próximo limiar somente quando a hipótese nula for rejeitada no limiar corrente.
- **Parar na primeira não rejeição**. Não testar limiares menos conservadores depois da primeira não rejeição.
- Se nenhum limiar for certificado para uma coorte, registrar a coorte como **não certificada**. Não haverá contorno, relaxamento do critério, agregação substitutiva ou seleção de outro limiar fora da sequência.

A certificação será executada exclusivamente em DEV-B. DEV-B não poderá ser usado para ajustar p, recalibrar IVAP, alterar a grade, escolher o método ou modificar qualquer decisão acima.

### 5.3 Relato por coorte

Para cada uma das 11 coortes, reportar:

- número total de exemplos em DEV-B;
- número de respostas aceitas e cobertura em cada limiar efetivamente testado;
- número de erros entre as respostas aceitas;
- taxa de erro e acerto observados;
- p-valor binomial exato;
- nível de significância ajustado δ/11;
- limiar certificado ou status **não certificada**;
- motivo de inelegibilidade, se houver menos de 25 respostas aceitas;
- status e limitações da certificação.

Não agregar coortes não certificadas para sugerir garantia individual. A curva acerto × cobertura pode exibir todos os limiares como descrição, mas os pontos após a primeira não rejeição não serão tratados como certificados.

### 5.4 Curva acerto × cobertura e AURC

Reportar a curva acerto × cobertura nos limiares pré-registrados, identificando claramente os pontos meramente descritivos e os pontos efetivamente certificados. Reportar AURC (Area Under the Risk-Coverage Curve), com definição de integração, normalização e tratamento dos empates documentados antes da execução.

AURC é métrica descritiva de seletividade e **não substitui** a certificação LTT. Não interpretar a curva ou AURC como garantia de risco.

## 6. Custo computacional e execução em shards

A estimativa utiliza os tempos por exemplo observados no artefato agregado do piloto DEV de 06/11/2026:

| Baseline do piloto | Segundos por exemplo (medido) | Valor arredondado para planejamento |
|---|---:|---:|
| mDeBERTa-v3-base NLI | 1,8896 s | ≈ 1,9 s |
| MiniCheck-DeBERTa-v3-Large | 4,2812 s | ≈ 4,3 s |
| FactCG-DeBERTa-v3-Large | 4,3036 s | ≈ 4,3 s |

Esses valores são medições de throughput forward-pass do piloto, não métricas de qualidade nem garantia de duração. O piloto executou 200 exemplos DEV; HHEM permaneceu SKIPPED. A extrapolação para 30.420 exemplos é planejamento, sujeita à distribuição de blocos, hardware, memória, aquecimento, falhas e contenção.

Para planejamento de capacidade:

- shard fixo de **1.000 exemplos**;
- **até 20 shards em paralelo**;
- 30.420 exemplos correspondem a **31 shards** (30 shards completos e um shard final de 420);
- considerando os três baselines em sequência, a soma dos tempos medidos é 10,4744 s por exemplo; extrapolação serial aproximada de **318.631 s (88,5 h)** para os três baselines sobre DEV completo;
- divisão aritmética ideal por 20 daria cerca de **4,4 h**, mas esse valor é apenas limite teórico de paralelização linear. Não é SLA nem previsão garantida. Duas ondas de shards, overhead de orquestração, contenção de CPU/RAM e diferenças entre coortes podem elevar o tempo real.

Registrar tempo real por shard e baseline, falhas, retries, recursos máximos e desvios. Não alterar tamanho do shard ou concorrência acima do teto sem novo registro e autorização do mantenedor. Nenhum workflow será dispatchado por esta PR.

## 7. Suposição de distribuição e limites

A validade da garantia depende da suposição de que DEV e TEST provêm da mesma distribuição, incluindo prevalência, coortes, condições de coleta e relação entre sinais e rótulos. Essa suposição não é demonstrada pelo procedimento. Drift, mudança de prevalência, alteração de coleta ou degradação da anotação podem invalidar a garantia e degradar cobertura e risco.

A certificação LTT é restrita à população, coortes, protocolo, limiar, dados e condições efetivamente registrados. Não extrapolar a garantia para populações ou distribuições diferentes. Qualquer avaliação futura em TEST deverá ser posterior, isolada e expressamente autorizada; TEST não poderá retroalimentar escolhas.

## 8. Política de alegações

Somente após certificação efetiva será permitida uma alegação que informe conjuntamente acerto, cobertura, coorte/população e nível de garantia. Formato recomendado:

> “Entre as respostas aceitas da coorte/população identificada, foi certificado erro de no máximo 10% (acerto de pelo menos 90%), com cobertura de X%, sob garantia estatística 1 − δ e o protocolo pré-registrado.”

Substituir X e δ apenas por valores efetivamente calculados e certificados. É proibido afirmar simplesmente “90% de acurácia” quando o resultado se refere apenas às respostas aceitas por um sistema com abstenção. Não usar “garantido” sem indicar o nível de confiança, a população coberta, as hipóteses e o procedimento estatístico.

Nenhum resultado, certificação, desempenho ou superioridade é afirmado por este documento.

## 9. Tabela — decisões fixadas neste pré-registro

| Decisão | Valor fixado |
|---|---|
| Dataset e split | LLM-AggreFact / DEV completo |
| Tamanho da população | 30.420 casos |
| Revisão do dataset | 981dfd0bd8e58e7238a9ab92b2e6ea44bce918e4 |
| SHA-256 do shard DEV | ca9a5bda9561bbc6f7327ef81ab41727fa10e96f96e9dc74ef32ba3af3c1d8a8 |
| Coortes | 11, identificadas pelo campo dataset |
| Separação de dados | DEV-A 50% para Camadas 1–2; DEV-B 50% exclusivamente para Camada 3 |
| Cross-fitting | 5 folds, estratificados por coorte e classe |
| Seed do cross-fitting | **20261107** |
| Ordem dos registros | Determinística por record_id |
| Camada 1 | dev_calibrated_by_cohort; grade 0,01–0,99; score > threshold; empate pelo menor limiar |
| Baseline de comparação | fixed_0.5; score > 0,5 |
| Camada 2 | IVAP de Vovk et al.; intervalo [p0, p1] |
| Probabilidade combinada | p = p1 / (1 − p0 + p1) |
| Cross-fitting da Camada 2 | Ajuste e avaliação dentro de DEV-A; 5 folds; mesma seed 20261107 |
| Mondrian | Por coorte somente com ≥200 exemplos de calibração efetivos |
| ECE | 15 bins por quantis da probabilidade calibrada |
| Empates no ECE | Permanecem no mesmo bin; nunca dividir empates |
| Bins vazios | Descartar do cálculo e contabilizar |
| Confiança LTT | c = max(p, 1 − p) |
| Regra SUPPORTED | p ≥ t |
| Regra NOT_SUPPORTED | p ≤ 1 − t |
| Regra de abstenção | Demais casos; p = 0,5 em t = 0,50 também abstém |
| Grade LTT | 0,99; 0,98; …; 0,50 |
| Ordem LTT | Mais conservador primeiro |
| Parada LTT | Primeira não rejeição; sem contorno |
| Risco-alvo | Erro ≤10% entre respostas aceitas |
| Teste LTT | Binomial exato; fixed sequence |
| Nível familiar | δ = 0,05 |
| Correção por coorte | Bonferroni δ/11, 11 coortes |
| Mínimo aceito por limiar | 25 casos |
| Falha de certificação | Coorte marcada “não certificada” |
| Fonte de certificação | DEV-B exclusivamente |
| Custo por exemplo | ≈1,9 / 4,3 / 4,3 s para os três baselines do piloto |
| Sharding | 1.000 exemplos por shard |
| Paralelismo | Até 20 shards simultâneos |
| TEST | Intocado; não usado para calibração, seleção ou ajuste |
| Escopo da PR | Somente documentação; nenhum código ou execução |

## 10. Registro de execução futura

Antes de qualquer execução futura, registrar aprovação e versão deste pré-registro, hashes do manifesto de dados, seeds, versões de bibliotecas, modelos e revisões, código e ambiente reprodutível, resultados agregados, recursos, desvios e limitações. Não publicar documentos, afirmações, respostas, rótulos, previsões ou resultados por instância de TEST.

Qualquer mudança metodológica após observar resultados deverá ser documentada em nova versão, sem reescrever retroativamente este pré-registro.

## Referências

1. Angelopoulos, A. N.; Bates, S.; Candès, E. J.; Jordan, M. I.; Lei, L. **Learn then Test: Calibrating Predictive Algorithms to Achieve Risk Control.** arXiv:2110.01052. https://arxiv.org/abs/2110.01052
2. Vovk et al. Método Venn-Abers indutivo (IVAP); a implementação e a referência bibliográfica completa deverão constar do manifesto técnico da execução, sem alterar a fórmula de combinação fixada neste pré-registro.
