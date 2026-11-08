# Pré-registro E3 — Ensemble de verificadores v0.8

**Status:** Aprovado pelo mantenedor em 2026-11-08 para execução exploratória em DEV (matriz exploratory_pre_ledger). Não autoriza TEST.
**Autoria:** ANDERSON AYORA  
**DEC aplicável:** DEC-024, Opção B (documentação da PR #493; calibração pós-hoc e combinação por regra fixa declarada previamente).  
**Escopo desta PR:** somente este documento. Não implementa código, workflow, cache A1, inferência, avaliação, ajuste ou publicação de resultados.

> **Regra temporal:** este pré-registro deve ser revisado e congelado antes de qualquer resultado E3 ser produzido ou consultado. Nenhum resultado é apresentado neste documento.

## 1. Objetivo e limites

Avaliar se ensembles com regra fixa de combinação de scores de verificadores congelados melhoram a Balanced Accuracy (BA) macro cross-fitted em DEV-A em relação ao baseline FactCG-DeBERTa-v3-Large, sem treinamento dos modelos nem pesos aprendidos.

O ensemble é apenas um sinal de avaliação. O Judge determinístico continua sendo a única autoridade de veredito. Este documento não altera contratos, Judge, Golden, thresholds de produção, ResponsePolicy ou protocolo RGC.

### 1.1 Autorizado pela DEC-024 Opção B

- Calibração pós-hoc IVAP com cross-fitting.
- Escolha de limiares em DEV-A, conforme protocolo Calibration V2.
- Combinação por regras aritméticas fixas, declaradas aqui antes de observar resultados.
- Comparação de E3a e E3b em DEV-A cross-fitted.

### 1.2 Fora do escopo / proibido

- Fine-tuning, treinamento, atualização de pesos ou adaptação dos modelos-base usando LLM-AggreFact.
- Pesos aprendidos, regressão logística, stacking, meta-modelos, voting ponderado ajustado ou qualquer função que aprenda coeficientes com rótulos.
- Ajustar, selecionar ou recalibrar qualquer coisa com DEV-B ou TEST.
- Usar DEV-B para escolher ensemble, membro, subconjunto, transformação, limiar, clipping ou regra.
- Usar TEST para desenvolvimento, depuração, seleção, calibração, ajuste ou decisão metodológica.
- Alterar a lista fechada de conjuntos candidatos ou qualquer regra depois de ver resultados.
- Inferir contaminação ausente a partir de falta de evidência. Coorte com status desconhecido/não verificado não é elegível até resolver o gate.
- Executar inferência, dispatch de workflow ou benchmark por meio desta PR.

## 2. População, modelos e gate de elegibilidade

### 2.1 Conjunto de candidatos

Os cinco membros candidatos para a próxima rodada DEV são, com seus identificadores de referência:

1. **mDeBERTa-v3-base NLI** — `MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7`
2. **MiniCheck-DeBERTa-v3-Large** — `lytang/MiniCheck-DeBERTa-v3-Large`
3. **FactCG-DeBERTa-v3-Large** — `yaxili96/FactCG-DeBERTa-v3-Large`
4. **MiniCheck-Flan-T5-Large** — `lytang/MiniCheck-Flan-T5-Large`
5. **HHEM-2.1-Open** — `vectara/hallucination_evaluation_model`

Os nomes e revisões imutáveis (SHA) efetivamente usados, tokenizer, configuração de inferência, direção do score e proveniência serão registrados no manifesto da execução. Alteração de revisão/modelo exige novo gate e novo pré-registro.

### 2.2 Matriz inicial de exclusão por coorte

Coortes do LLM-AggreFact: AggreFact-CNN, AggreFact-XSum, ClaimVerify, ExpertQA, FactCheck-GPT, LFQA, RAGTruth, REVEAL, TofuEval-MediaS, TofuEval-MeetB e WiCE.

A tabela abaixo transcreve os bloqueios conhecidos no radar tecnológico versionado em `docs/benchmarks/RADAR-TECNOLOGICO-2026-11.md`. **“Não bloqueada por sobreposição conhecida” não significa ausência comprovada de contaminação.** O ledger de proveniência deve confirmar elegibilidade antes de execução. Status desconhecido, fontes confidenciais sem detalhamento ou deduplicação pendente significam **BLOQUEADO**, não elegível por padrão.

| Modelo | Bloqueios explícitos no radar | Tratamento das demais coortes |
|---|---|---|
| mDeBERTa-v3-base NLI | Nenhuma sobreposição direta conhecida nas 11 coortes; XNLI CC BY-NC é restrição de licença/uso comercial, não por si só uma coorte contaminada | Candidata à avaliação de pesquisa somente após gate completo de fontes/licença; não produto comercial |
| MiniCheck-DeBERTa-v3-Large | **WiCE** até deduplicação por IDs | Outras coortes somente se o ledger verificar fontes e resolver risco de Google News/sintéticos; qualquer risco não resolvido bloqueia a coorte |
| FactCG-DeBERTa-v3-Large | **WiCE** até deduplicação por IDs; registrar separadamente exposição C5 por threshold tuning dos autores no validation LLM-AggreFact | Outras coortes somente após gate; a exposição publicada não deve ser confundida com contaminação de pesos, mas impede alegação de avaliação independente dos resultados dos autores |
| MiniCheck-Flan-T5-Large | **AggreFact-CNN, AggreFact-XSum, WiCE e REVEAL** até deduplicação/verificação; bloqueio adicional por coorte de notícias se o ledger identificar sobreposição | Restantes coortes somente após verificação de fontes e dados sintéticos; risco não resolvido = bloqueado |
| HHEM-2.1-Open | **RAGTruth, AggreFact-CNN e AggreFact-XSum** (RAGTruth train e exposição da base Flan-T5) | O radar indica outros datasets de treino confidenciais e as demais coortes como não verificadas. Portanto, **todas as coortes restantes ficam BLOQUEADAS até disclosure e auditoria**. Não presumir elegibilidade residual |

A matriz é conservadora e pode resultar em ausência de HHEM em algumas ou todas as coortes. Isso é uma consequência do gate, não um motivo para flexibilizá-lo após observar desempenho.

### 2.3 Regra de membro bloqueado numa coorte

- Em cada coorte, um membro bloqueado ou não verificado não participa da média daquela coorte.
- A média é calculada somente sobre membros elegíveis **dentro do conjunto candidato pré-registrado**.
- Não imputar score, não substituir membro, não buscar um modelo alternativo e não renormalizar pesos aprendidos: todos os membros presentes recebem peso aritmético igual.
- Se nenhum membro do conjunto candidato for elegível naquela coorte, o ensemble é **não avaliável** nessa coorte.
- FactCG é o comparador apenas nas coortes em que FactCG e o ensemble são elegíveis. Comparações devem usar denominador de coortes comum, fixado antes da execução. Não comparar BA macro com coortes/denominadores diferentes.
- Antes de executar, publicar no manifesto a matriz final de elegibilidade (modelo × coorte), fontes, status, evidência, data e SHA do radar/ledger. Mudança de elegibilidade após resultados exige novo pré-registro; não pode ser aplicada retroativamente para melhorar o resultado.

## 3. Lista FECHADA de configurações candidatas

A lista abaixo é exaustiva para este experimento. Não acrescentar, retirar ou substituir subconjuntos após consultar qualquer resultado E3. Um conjunto listado é aplicado por coorte aos seus membros elegíveis, conforme a seção 2.3.

| ID | Conjunto de membros pré-registrado |
|---|---|
| E3a-01 / E3b-01 | {FactCG-DeBERTa-v3-Large, MiniCheck-DeBERTa-v3-Large} |
| E3a-02 / E3b-02 | {FactCG-DeBERTa-v3-Large, MiniCheck-DeBERTa-v3-Large, MiniCheck-Flan-T5-Large} |
| E3a-03 / E3b-03 | {FactCG-DeBERTa-v3-Large, mDeBERTa-v3-base NLI} |
| E3a-04 / E3b-04 | {FactCG-DeBERTa-v3-Large, MiniCheck-DeBERTa-v3-Large, mDeBERTa-v3-base NLI} |
| E3a-05 / E3b-05 | {todos os cinco candidatos} |

Não serão testados outros pares, trios, quartetos, subconjuntos, ablações escolhidas pós-hoc ou variantes de combinação. O baseline FactCG sozinho é comparador, não candidato ensemble.

**Elegibilidade efetiva:** se um conjunto tiver membros bloqueados numa coorte, usar apenas os membros elegíveis daquele conjunto. A composição efetiva por coorte será reportada, mas não será usada para criar uma nova configuração ou selecionar a melhor combinação após ver resultados. Se um conjunto se reduzir a apenas FactCG, reportar como degenerado nessa coorte; não contar como ganho de ensemble.

## 4. Regras fixas de combinação

Todas as probabilidades individuais devem ser IVAP calibradas **cross-fitted** conforme Calibration V2, dentro de DEV-A. Para cada observação avaliada, nenhum rótulo dessa observação/fold pode participar do ajuste do IVAP que produz sua probabilidade.

Seja (p_{m,i}) a probabilidade IVAP cross-fitted do modelo (m) para caso (i). A elegibilidade por coorte determina o conjunto (M_{S,c}) de membros elegíveis de uma configuração (S) na coorte (c).

### 4.1 E3a — média aritmética de probabilidades

[
p^{(E3a)}_{i,S,c} = \frac{1}{|M_{S,c}|}\sum_{m\in M_{S,c}} p_{m,i}
]

Média simples, peso (1/|M_{S,c}|) para cada membro elegível. Nenhum peso é ajustado.

### 4.2 E3b — média de logits com clipping fixo

Antes de calcular o logit, aplicar clipping numérico fixo:

[
\tilde p_{m,i}=\min(1-10^{-6},\max(10^{-6},p_{m,i}))
]

[
z_{m,i}=\log\frac{\tilde p_{m,i}}{1-\tilde p_{m,i}}
]

[
p^{(E3b)}_{i,S,c}=\sigma\left(\frac{1}{|M_{S,c}|}\sum_{m\in M_{S,c}}z_{m,i}\right),\quad
\sigma(z)=\frac{1}{1+e^{-z}}
]

O clipping é exatamente ([10^{-6},1-10^{-6}]), aplicado somente para estabilidade numérica do logit. Não será ajustado por modelo, coorte, fold ou resultado. A sigmoid final converte o logit médio em probabilidade.

### 4.3 Sem parâmetros aprendidos

E3a e E3b são regras fixas. Não há intercepto, pesos treináveis, regressão logística, stacking, meta-modelo, otimização de coeficientes ou seleção de membros por correlação/resultado. Não usar rótulos para escolher uma das regras ou variantes depois da avaliação.

## 5. Métrica primária e regra de decisão

### 5.1 Métrica primária

**BA macro cross-fitted em DEV-A**, idêntica à métrica primária definida na Calibration V2:

- cross-fitting de 5 folds, estratificado por coorte e classe;
- seed e atribuição dos folds conforme Calibration V2 (`20261107`, ordenação determinística documentada no pré-registro V2);
- BA por coorte e média macro com peso igual por coorte;
- comparar ensemble e FactCG nas mesmas coortes elegíveis e nos mesmos folds;

**Comparador pareado:** FactCG pelo mesmo pipeline do ensemble (probabilidades IVAP cross-fitted + limiar por coorte cross-fitted, mesmos folds); o valor da Camada 1 da Calibration V2 (0,7468, limiar sobre score bruto) é reportado como referência.
- reportar BA por coorte, macro BA, quantidade de coortes e casos, elegibilidade, classes ausentes e limitações.

A métrica é cross-fitted: calibradores e probabilidades para cada fold são produzidos sem utilizar os rótulos do fold avaliado. Não reportar BA aparente como se fosse BA cross-fitted.

### 5.2 Regra de substituição do baseline

Um ensemble só substitui FactCG como candidato principal se:

[
BA_{macro}(ensemble)-BA_{macro}(FactCG)\geq 0{,}005
]

Isto é, ganho mínimo de **0,005 (0,5 ponto percentual)**, a mesma tolerância prática registrada na PR #477.

- A diferença deve ser calculada no mesmo conjunto pré-fixado de coortes elegíveis e mesmos folds.
- Se nenhum ensemble atingir +0,005, FactCG permanece baseline; não declarar vencedor.
- Se mais de um ensemble atingir a condição, selecionar o de maior BA macro cross-fitted. A regra de empate abaixo se aplica.
- **Empate:** se as diferenças entre candidatos elegíveis forem menores que 0,005, escolher o de menor custo operacional medido; se custo também empatar, escolher o ensemble com menos membros. Custos e desempate serão reportados. Não escolher por métrica secundária.
- O limiar de +0,005 é uma regra de decisão pré-fixada, não um intervalo de confiança nem garantia de superioridade estatística.

## 6. Incerteza — bootstrap pareado por cluster/coorte

A unidade de cluster será a **coorte/dataset**. O bootstrap será pareado: em cada reamostragem, a mesma lista de coortes sorteadas será aplicada ao ensemble e ao FactCG.

**Definição de K:** K = número de coortes comuns; com poucos clusters o IC é aproximado.

- Definir previamente **K** como o número de coortes elegíveis comuns ao ensemble e ao FactCG, usando o mesmo denominador fixado para a comparação primária. K será calculado antes de consultar os resultados do ensemble.
- Número de reamostragens: **2.000**.
- Seed: **20261108**.
- Gerador: **NumPy `Generator(PCG64(20261108))`**.
- Amostragem: sortear **K coortes com reposição** dentre as K coortes elegíveis comuns; manter cada coorte sorteada como cluster inteiro. Não usar 11 como tamanho fixo quando houver coortes bloqueadas.
- Estatística em cada réplica: diferença BA macro ensemble − FactCG, calculada como média aritmética das diferenças de BA por coorte nos clusters sorteados (com multiplicidade conforme a amostragem).
- Intervalo: IC95% percentil bilateral, quantis 2,5% e 97,5%, usando interpolação linear de quantis (`method="linear"` em NumPy). Reportar limites, estimativa pontual, K e distribuição das réplicas.
- Se alguma réplica não puder calcular BA por ausência de classe, aplicar a regra pré-registrada de excluir essa réplica e reportar quantidade/percentual excluído. Se mais de 5% das réplicas forem inválidas, IC95% será declarado **não estimável**; não alterar bootstrap ou denominador após observar os resultados.
- **Interpretação:** com poucos clusters/coortes, o IC95% bootstrap é **aproximado e potencialmente instável**. Reportar explicitamente K e essa limitação; não apresentar o intervalo como precisão garantida, prova de generalização ou inferência robusta para uma população de datasets. O IC95% não substitui a regra de +0,005.

## 7. DEV-A, DEV-B e TEST

| Partição | Uso nesta PR / E3 |
|---|---|
| DEV-A | Única partição para cross-fitting, calibração IVAP, BA macro primária e comparação/seleção segundo a regra fixada |
| DEV-B | **Proibido** para escolha de modelo, conjunto, regra, clipping, calibrador, limiar ou decisão de seleção. Não será usado para confirmar/ajustar E3 neste pré-registro |
| TEST | Intocado. Nenhuma consulta, execução, depuração, seleção ou ajuste. Uso futuro depende de configuração congelada, pré-registro próprio e autorização explícita |

Nenhum dado de DEV-B/TEST pode retroalimentar E3, inclusive após uma falha ou resultado abaixo da tolerância.

## 8. Relato obrigatório

O relatório futuro, se autorizado e executado, deverá incluir:

- SHA deste pré-registro e SHA do código/configuração executados;
- revisão de cada modelo, tokenizer e configuração de inferência;
- ledger e matriz modelo × coorte, bloqueios e justificativas;
- conjunto candidato exato e membros efetivos por coorte;
- resultados por coorte e BA macro cross-fitted;
- comparação pareada com FactCG, diferença absoluta, regra de +0,005;
- bootstrap: seed, PCG64, 2.000 réplicas, IC95%, clusters e réplicas inválidas;
- custo/latência e falhas, sem expor scores, rótulos ou registros por instância;
- limitações, coortes excluídas, status de licença e exposição a benchmark.

CI verde valida checks de software/documentação no SHA testado; não valida a hipótese científica nem autoriza executar o benchmark.

## 9. Política contra alterações pós-resultados

Depois de qualquer resultado E3 ser visto, é proibido:

- alterar a lista de subconjuntos;
- trocar E3a por E3b ou mudar clipping;
- modificar elegibilidade para melhorar BA;
- ajustar folds, seeds, métrica, tolerância ou bootstrap;
- selecionar modelo/coorte com base em DEV-B/TEST;
- omitir ensemble que perdeu, coorte bloqueada, custo ou resultado negativo.

Qualquer mudança exige nova versão de pré-registro, explicação do motivo, data e declaração de que a nova análise é exploratória; resultados antigos não podem ser reclassificados como confirmatórios.

## 10. Referências internas e decisão

- `docs/benchmarks/CALIBRATION-V2-PREREGISTRATION.md` — cross-fitting e BA macro.
- `docs/benchmarks/RADAR-TECNOLOGICO-2026-11.md` — proveniência, licença, exposição e gate por coorte.
- PR #493 — DEC-024, Opção B.
- PR #477 — tolerância prática de 0,005.

**Estado final:** aprovado pelo mantenedor em 2026-11-08 para uma execução exploratória do E3 em DEV-A, via workflow protegido, com saída somente agregada. Resultado não confirmatório até a matriz derivada do ledger A4 substituir configs/benchmarks/e3-eligibility-v0.8.json. Não autoriza TEST nem alteração de artefatos protegidos.
