# Roadmap de acurácia — AYORAI ATTRACTOR v0.8

**Status:** proposta de planejamento e pré-registro documental; não autoriza experimentos nem execução.  
**Autoria e responsabilidade:** ANDERSON AYORA.  
**Escopo desta alteração:** somente este documento. Nenhuma implementação, inferência, execução de benchmark, alteração de dados, dispatch de workflow, criação de secret, alteração de Judge/Golden/thresholds/RGC ou avaliação TEST.  
**Referência de estado:** `main` após o merge squash da PR #489: `f8895caab6f3d81fdfea0eaffa91a7a255477d36`. A PR #489 adicionou este roadmap. A PR #488, que propõe a Emenda 2 do LTT e retenção de sete dias, continua pendente e não é tratada como regra vigente até merge e revisão. O radar documental complementar está em `docs/benchmarks/RADAR-TECNOLOGICO-2026-11.md`.

## 1. Objetivo e limite científico

O objetivo é melhorar a acurácia verificadora do AYORAI ATTRACTOR por meio de infraestrutura reproduzível, calibração pós-hoc, combinação limitada de sinais, avaliação de verificadores adicionais e métodos de recuperação/decomposição de evidência — sem alterar a autoridade decisória do sistema.

**Princípio arquitetural:** inteligência ≠ autorização ≠ execução. Os modelos externos produzem sinais; o Judge 2.0 continua sendo a única autoridade de veredito. Nenhum experimento deste roadmap altera contratos, política de resposta ou regras determinísticas.

### 1.1 Ponto de partida registrado

O relatório DEV da Calibration V2, disponível em `reports/benchmarks/2026-11-07-dev-calibration-v2/README.md` e sua proveniência, registra os seguintes resultados informados para LLM-AggreFact DEV (30.420 casos, 11 coortes):

| Verificador | BA cross-fitted informada |
|---|---:|
| FactCG-DeBERTa-v3-Large | 74,68% |
| MiniCheck-DeBERTa-v3-Large | 72,87% |
| mDeBERTa-v3-base NLI | 62,57% |

ECE informado para a calibração reportada: 0,0054. A Camada 3 terminou em 0/11 coortes certificadas pela regra original do LTT. Esses números são resultados DEV, não TEST, não certificação e não evidência de superioridade geral. Antes de reutilizá-los em material público, conferir o relatório e a proveniência no SHA exato correspondente.

A consulta ao leaderboard oficial em 2026-11-07 confirmou, entre outros, MiniCheck-Flan-T5-L em 75,0, FactCG-DeBERTa-L em 75,6, Granite Guardian 3.3 em 76,5 e Bespoke-MiniCheck-7B em 77,4. A tabela também contém modelos com médias superiores a 77,4; portanto, Bespoke não é mais o primeiro colocado na página consultada. Esses números são referências externas, não resultados AYORAI nem baseline diretamente comparável: versão, prompt, modo, split e protocolo devem ser verificados. A auditoria e as fontes estão em `RADAR-TECNOLOGICO-2026-11.md`.

O possível ruído de rótulo de 6–16% é uma hipótese/estimativa de contexto, não uma medição confirmada neste conjunto. Não subtrair esse intervalo dos resultados nem apresentá-lo como limite empírico do LLM-AggreFact sem estudo específico.

## 2. Princípios inegociáveis e gates gerais

1. **Pré-registro antes da execução.** Cada experimento terá documento em `docs/` com hipótese, população/partição, variáveis, métrica primária e secundárias, procedimento, regra de decisão, tratamento de falhas, custo e critério de parada. O pré-registro deve ser revisado e aprovado pelo mantenedor antes de qualquer execução. Sem pré-registro aprovado, não executar.
2. **Separação de partições.**
   - DEV: desenvolvimento e diagnóstico.
   - DEV-A: seleção e ajuste por cross-fitting; cada previsão avaliada deve ser out-of-fold.
   - DEV-B: confirmação interna, sem retroalimentar escolhas de modelo, hiperparâmetros, método ou limiares.
   - TEST: avaliação final única, somente depois de configuração congelada por hash e aprovação explícita do mantenedor. Nunca usar TEST para depuração, seleção, calibração ou decisão metodológica.
3. **Termos de uso do LLM-AggreFact.** O pin em `configs/benchmarks/llm-aggrefact-dev-pin.json` registra: “benchmark evaluation only; pretraining and fine-tuning prohibited”. É proibido treinar ou ajustar pesos de modelos com LLM-AggreFact. A possibilidade de calibração pós-hoc, ajuste de limiares e combinação de sinais precisa da decisão formal descrita na DEC proposta da seção 4 antes de qualquer ajuste. Na dúvida, parar.
4. **Gate de contaminação.** Antes de qualquer uso, verificar se o modelo, seu modelo-base, adapters, SFT/DPO, dados sintéticos/preferências ou corpora divulgados foram treinados/ajustados com LLM-AggreFact ou com qualquer dataset-fonte das 11 coortes. Treino direto no benchmark bloqueia todas as coortes; treino em uma coorte bloqueia aquela coorte; treino derivado/sintético herda a abrangência da fonte. Avaliação publicada pelos autores, sem treino conhecido no benchmark, não é automaticamente contaminação, mas nunca será apresentada como resultado independente do AYORAI. Proveniência insuficiente/oculta bloqueia resultado confirmatório; exploração só em dados externos comprovadamente não sobrepostos, com ressalva explícita. Registrar status por modelo e coorte em `RADAR-TECNOLOGICO-2026-11.md` e manter ledger de evidências.
5. **Licença e cadeia de suprimentos de modelos.** Antes de qualquer uso, verificar separadamente licença do checkpoint final, modelo-base, datasets, adapters, código remoto, tokenizer e dependências; registrar autor, URL, SHA imutável, licença, restrições e data. `trust_remote_code` exige revisão do código no SHA pinado. Licenças `other`, não comerciais ou incompatíveis bloqueiam uso em produto; não inferir licença pela família ou nome.
6. **Autoridade e artefatos protegidos.** Judge 2.0 permanece a única autoridade de veredito. Não alterar Judge, Golden, hashes/manifests congelados, thresholds do sistema, RGC, Piloto 02 ou ResponsePolicy.
7. **Privacidade.** Nenhum dado por instância, rótulo, score, predição ou trecho documental será publicado. Artefatos por instância, se autorizados, serão privados, cifrados, com acesso mínimo e retenção limitada. A publicação de experimentos conterá apenas agregados com proteção contra divulgação.
8. **Governança operacional.** Nenhum merge, dispatch, criação/migração de secret ou alteração de ambiente protegido sem autorização explícita do mantenedor. CI verde é específico ao SHA e não substitui revisão humana.
9. **Alegações públicas.** Toda alegação identificará partição (DEV ou TEST), população/coortes, cobertura quando houver modo seletivo, protocolo, versão/revisão dos modelos e que os verificadores são modelos de terceiros. Não alegar certificação, validação externa, superioridade geral ou acurácia em produção com base em DEV.

## 3. Pré-registro da regra final de escolha

Esta seção propõe a regra de seleção para a linha experimental v0.8. Deve ser tratada como pré-registro documental proposto e só será considerada operacional após revisão e aprovação explícita do mantenedor, antes de executar E3–E8.

### 3.1 Métrica primária

A métrica primária será a **média macro da Balanced Accuracy (BA) por dataset/coorte**, calculada a partir de predições out-of-fold em DEV-A. Cada dataset/coorte terá o mesmo peso no agregado, independentemente de seu número de exemplos. Publicar também resultados por coorte, tamanho amostral, intervalo de incerteza e métricas secundárias.

O protocolo de cálculo, a definição da unidade de agregação, o tratamento de classes ausentes, abstenções e previsões inválidas deverão ser fixados no pré-registro específico de cada experimento antes de executar. Não comparar configurações com denominadores ou populações diferentes sem declarar a diferença.

### 3.2 Procedimento de comparação

- Cada candidato será avaliado com cross-fitting em DEV-A; os dados do fold avaliado não poderão ajustar o calibrador, pesos, limiar ou qualquer parâmetro que produza sua predição.
- DEV-B será usado somente como confirmação interna da configuração selecionada, sem alterar a seleção. Divergência em DEV-B será reportada, não corrigida com ajustes retroativos.
- A seleção da configuração (E3–E7) usa BA macro com cobertura total (sem abstenção). O modo seletivo (E8) é uma camada posterior: para cada coorte, reporta acerto, cobertura e risco. `n ≥ 25` é condição mínima de elegibilidade, não garantia estatística. Acerto observado ≥ 90% é descritivo; certificação só ocorre se o teste LTT vigente satisfizer o limite de risco/nível de erro pré-registrado, com tratamento de múltiplas coortes e seleção de limiar corretamente aplicado. Com `n < 25`, não há certificação. **Não há piso de cobertura**; cobertura baixa é reportada, nunca escondida.
- O resultado de DEV-B é uma verificação interna de consistência, não certificação, teste independente externo ou resultado TEST.

### 3.3 Regra determinística de escolha

1. A seleção principal compara as configurações de E3–E7 com cobertura total (sem abstenção). Excluir apenas candidatos que violem gates previamente registrados (licença, integridade, falha de execução ou protocolo).
2. Entre os candidatos elegíveis de E3–E7, selecionar o de maior BA macro cross-fitted em DEV-A. E8 não concorre nessa seleção: é uma camada seletiva posterior, avaliada separadamente por coorte.
3. Se a diferença absoluta de BA macro entre o primeiro colocado e outro candidato for **inferior a 0,005** (0,5 ponto percentual), considerar empate prático e escolher o candidato de menor custo operacional e menor complexidade; documentar a justificativa e os custos medidos.
4. Não escolher por resultado em DEV-B, por resultado TEST, por ranking externo não comparável ou por uma métrica secundária observada após a execução.
5. Se nenhum candidato satisfizer os gates, não declarar vencedor: manter o baseline e registrar a conclusão negativa.

A regra não garante ganho. Expectativas de ganho são hipóteses e não resultados.

## 4. DEC proposta — calibração pós-hoc versus fine-tuning

**PROPOSTA — NÃO APROVADA**

**Identificador sugerido:** DEC-024 — Limites de calibração e combinação de sinais no LLM-AggreFact.  
**Decisor:** Anderson Leon Ayora, mantenedor.  
**Estado:** aguardando decisão explícita. Esta minuta não autoriza ajuste, execução, inferência adicional ou publicação de resultados.

### 4.1 Questão a decidir

Os termos do dataset permitem “benchmark evaluation only” e proíbem “pretraining and fine-tuning”. É necessário decidir formalmente se operações pós-hoc sobre scores de modelos já executados — sem atualizar pesos do modelo-base — serão tratadas como calibração/avaliação permitida ou se exigem restrição adicional. A classificação técnica abaixo não substitui interpretação jurídica dos termos; em caso de ambiguidade, não executar até a decisão e eventual revisão apropriada.

### 4.2 Distinções operacionais propostas

- **Fine-tuning/treinamento de modelo-base (proibido):** atualizar pesos/parâmetros internos do verificador, continuar pré-treinamento, adaptar o encoder ou treinar um modelo com exemplos/rótulos do LLM-AggreFact.
- **Calibração pós-hoc (sujeita à decisão):** transformar scores/probabilidades já produzidos por modelos congelados, sem atualizar seus pesos, usando exclusivamente dados permitidos e cross-fitting. Exemplos propostos: IVAP, calibração de limiar e transformação monotônica.
- **Combinação de sinais (sujeita à decisão):** combinar saídas de modelos congelados por regra simples ou por um número muito pequeno de parâmetros externos. Isso não atualiza pesos dos verificadores, mas ainda ajusta parâmetros a partir dos rótulos e, por isso, não deve ser presumido permitido sem decisão.
- **Avaliação pura:** calcular métricas sobre scores já existentes sem escolher parâmetros com base nos rótulos. Permanece sujeita aos termos, à segregação de partições e aos controles de privacidade.

### 4.3 Opções para decisão do mantenedor

**Opção A — autorizar calibração e combinação limitadas, sob gates.**  
Autorizar apenas transformações pós-hoc sobre scores de modelos congelados: IVAP, seleção de limiares e combinação externa com no máximo cinco parâmetros; regressão logística limitada a até três pesos, sem intercepto ou parâmetros adicionais salvo se explicitamente pré-registrados. Exigir cross-fitting em DEV-A, nenhum acesso de ajuste a DEV-B/TEST, código e parâmetros versionados, proveniência completa e revisão dos termos/licenças. Nenhuma atualização de pesos do modelo-base. A autorização não abrange fine-tuning, treinamento de encoder ou aprendizado de representação.

**Opção B — autorizar somente calibração monotônica e limiares.**  
Autorizar IVAP e seleção de limiares, mas não regressão logística, pesos aprendidos ou votação ponderada ajustada por rótulos. Médias fixas de scores/probabilidades só poderiam ser comparadas se forem declaradas como regra fixa antes da avaliação. Nenhum ajuste de pesos dos modelos-base.

**Opção C — não autorizar ajustes com rótulos até esclarecimento adicional.**  
Permitir apenas avaliação descritiva de scores já produzidos e interromper IVAP, seleção de limiar, regressão logística e combinação ajustada até obter esclarecimento formal dos termos e uma nova decisão.

**Recomendação técnica para deliberação:** Opção B é a alternativa mais conservadora diante da redação atual dos termos. A Opção A pode oferecer maior flexibilidade experimental, mas exige que o mantenedor aceite explicitamente o risco interpretativo de calibradores/combinações ajustados por rótulos. Esta recomendação não equivale a aprovação.

### 4.4 Registro da decisão

O mantenedor deverá registrar a opção escolhida, data, fundamento, limites, partições autorizadas e se é necessária revisão jurídica/licenciamento. Até esse registro, **E3(c) e qualquer ajuste de parâmetros por rótulos ficam bloqueados**; por prudência, todo o E3 que dependa de calibração ou seleção com rótulos aguarda a decisão. Uma eventual aprovação não autoriza TEST nem execução automática.

## 5. Fase A — robustez da infraestrutura

Cada item será tratado em PR própria, com pré-registro/escopo, testes e evidência no SHA exato. A implementação só começa após revisão e autorização específica.

### A1. Cache privado cifrado de scores por instância

- Fazer o agregador produzir um artefato **privado e cifrado de predições**, sem rótulos gold: `record_id`, coorte, split/fold, score, status e metadados mínimos de inferência. Manter rótulos gold em artefato separado, com acesso restrito ao avaliador autorizado; a junção ocorre apenas na etapa de avaliação, nunca no processo de inferência.
- Restringir leitura/decifragem a workflow protegido e ambiente autorizado; não disponibilizar o artefato em releases, páginas públicas, logs ou artefatos públicos.
- Cada score deve ser acompanhado de `model_id`, revisão SHA, tokenizer, hash do input, hash da configuração, direção/semântica do score, precisão, chunking, timestamp, runtime e checksum. Exigir chave idempotente, detecção de duplicatas, retomada, escrita atômica e falha fechada. O workflow consome o cache e publica apenas agregados.
- Definir retenção pelo menor prazo operacional possível, limitado à política do repositório e do provedor; o prazo de sete dias proposto na PR #488 só será considerado vigente se aquela PR for mesclada e sua política se aplicar a estes artefatos.
- Testar com dados sintéticos, controle de acesso, falhas de chave, ausência/expiração do cache e caminho real do CLI, no padrão de cobertura de caminho de `test_phase1b_aggregate_cli.py`.
- Critério de parada: qualquer exposição de dados por instância, decifragem fora do ambiente autorizado ou inconsistência de integridade interrompe a fase.

### A2. Criptografia assimétrica para shards

- Propor cifragem no shard com chave pública e decifragem somente no agregador com chave privada, usando X25519 para acordo de chave e AES-GCM para cifragem autenticada, por meio da biblioteca `cryptography` já pinada.
- O desenho deve incluir derivação de chave, nonce único, identificação de versão/formato, autenticação de metadados, rotação e falha fechada.
- **Pré-requisitos bloqueantes:** DEC de segurança aprovada pelo mantenedor, plano de migração/rotação de secrets executado pelo mantenedor e teste de recuperação. Shards não receberão secret privado.
- Não criar, copiar, migrar ou modificar secrets como parte deste roadmap.

### A3. Teste de determinismo de scores

- Reexecutar uma amostra pré-registrada de 200 casos DEV, com modelo, revisão, tokenizer, bibliotecas, hardware/precisão e parâmetros fixados.
- Critério proposto: scores idênticos dentro da tolerância absoluta de `1e-6`; registrar também diferenças máximas, distribuição das diferenças e causas conhecidas de não determinismo.
- Se o critério falhar, não mascarar diferenças com arredondamento. Investigar e registrar; não avançar para comparação de modelos dependente de determinismo até decisão.

### A4. Auditoria agregada de erros E2b

- Produzir apenas tabelas agregadas por coorte/modelo: matriz de confusão, erros por faixas pré-definidas de comprimento do documento e da afirmação, incidência de truncamento e discordância entre modelos.
- Pré-registrar as faixas, denominadores, tratamento de valores ausentes e supressão de células pequenas.
- Usar os resultados de ExpertQA e AggreFact-CNN como diagnóstico de onde os verificadores falham, não como prova de causa ou de melhoria.
- Proibir exportação de linhas por instância, exemplos textuais, IDs, rótulos ou scores individuais.

## 6. Fase B — experimentos de acurácia em DEV

Cada experimento abaixo exige pré-registro próprio e aprovação antes da execução. Métrica primária: BA macro por dataset, cross-fitted em DEV-A, conforme a seção 3. Resultados por coorte e custos são obrigatórios.

### E3. Ensemble calibrado dos três verificadores já executados

Comparar, sob a decisão da seção 4:

1. Média de probabilidades calibradas por IVAP.
2. Média de logits, com definição de transformação e tratamento numérico fixados antes da execução.
3. Regressão logística externa com até três pesos, cross-fitted, somente se expressamente autorizada pela DEC.
4. Votação ponderada, com pesos fixos definidos previamente ou procedimento de ajuste explicitamente autorizado.

O cache A1 deverá ser usado para evitar nova inferência. Cada fold retido será avaliado com calibradores/pesos ajustados somente nos folds de treino. Não usar DEV-B para selecionar a variante. A referência RAIM sugere testar correlação de erros, dupla falha e ganho incremental contra o melhor membro; não copiar seu código (repositórios com licença `other`/NOASSERTION). O stacking RAIM ajusta um meta-modelo com rótulos e depende da DEC-024. Comparar custo, estabilidade e BA macro; expectativa de ganho de 1–2,5 pontos é apenas hipótese de planejamento, não promessa nem resultado.

### E4. Verificadores adicionais

A lista, o status de contaminação e as fontes verificadas estão em `docs/benchmarks/RADAR-TECNOLOGICO-2026-11.md`. E4 não deve tratar todos os modelos como elegíveis para as 11 coortes.

**Prioridade CPU — MiniCheck-Flan-T5-Large (`lytang/MiniCheck-Flan-T5-Large`).** O Hub declara MIT, arquitetura T5 e aproximadamente 0,8B parâmetros; o leaderboard consultado reporta 75,0 de média. O model card declara 35K exemplos de treino: 21K ANLI e 14K sintéticos gerados de forma estruturada; os autores afirmam que LLM-AggreFact não foi visto no treino. É a primeira adição recomendada ao baseline DeBERTa, sujeita a pin SHA, auditoria do modelo-base/dependências e piloto real de CPU. Não presumir throughput com base apenas no tamanho.

**HHEM-2.1-Open (`vectara/hallucination_evaluation_model`).** O Hub declara Apache-2.0, 109,6M parâmetros, base Flan-T5-base e `trust_remote_code=True`. A documentação Vectara indica execução em CPU de consumo, mas o artigo EMNLP Industry 2025 afirma que HHEM-2.1-Open foi treinado com RAGTruth train split e outros datasets cujos detalhes são confidenciais. **RAGTruth fica bloqueado. O modelo não entra no agregado confirmatório das 11 coortes enquanto as outras fontes não forem esclarecidas.** Um piloto de throughput pode usar apenas dados sintéticos fora do benchmark. Revisar e pin-ar o código remoto antes de qualquer execução.

**HalluGuard-Qwen3-4B (`lrsbrgrn/HalluGuard-Qwen3-4B`).** Os pesos Safetensors estão publicados; o card declara Apache-2.0 e fine-tuning LoRA+ORPO sobre 76.708 preferências sintéticas derivadas de FineWeb, com base Qwen3-4B. O artigo final Findings of ACL 2026 reporta 77,1% BAcc no LLM-AggreFact e 84,4% no RAGTruth; o preprint reportava 75,7%. Esses números são dos autores. A avaliação dos autores no mesmo benchmark é C4 (avaliação, não prova de treino no benchmark); a proveniência do modelo-base ainda exige ressalva. Prioridade posterior, com SHA imutável, licença do Qwen3-4B e dependências arquivadas. Há GGUF de terceiro; validar lineage, SHA, licença, template e perda por quantização. Não assumir equivalência com Safetensors.

**Granite Guardian 3.3 8B (`ibm-granite/granite-guardian-3.3-8b`).** Apache-2.0, 8B, 76,5 no leaderboard. O card declara treino com HH-RLHF, anotações humanas e dados sintéticos internos; não enumera toda a proveniência do material sintético. É inglês e exige uso no modo/prompt de scoring prescrito; think/no-think não são intercambiáveis. Status: proveniência insuficiente para confirmação até esclarecimento. GPU.

**Bespoke-MiniCheck-7B.** O card declara 21K ANLI e 14K dados sintéticos com fontes curadas independentemente do benchmark; licença CC BY-NC 4.0. O leaderboard consultado mostra 77,4, mas já existem modelos acima desse valor. Permitido apenas como referência de pesquisa não comercial; bloqueado para produto e distribuição comercial sem licença escrita da Bespoke.

**Paladin-mini (`qualifire/context-grounding-paladin-mini`).** Remover da lista de candidatos: o model card lista explicitamente `lytang/LLM-AggreFact` entre os datasets de treino e a licença é `other`. Contaminação direta e licença sem clareza.

**LettuceDetect (`KRLabsOrg/lettucedect-large-modernbert-en-v1`).** MIT, aproximadamente 396M parâmetros, token-classification; o paper declara treinamento no RAGTruth. Bloquear a coorte RAGTruth; outras coortes só após auditoria de sobreposição. Exige agregação token→claim/response e avaliação própria, sem comparar diretamente F1 token-level com BA claim-level.

**Critério de execução:** começar com piloto de 200 casos para throughput, memória, p50/p95, timeouts, falhas, truncamento e custo. Para MiniCheck-Flan-T5-Large, piloto em DEV-A após A1. Para HHEM, somente dados sintéticos fora do benchmark enquanto persistir a lacuna de proveniência. Não executar o painel de cinco modelos como agregado homogêneo. O painel confirmatório full DEV proposto é os três modelos existentes + MiniCheck-Flan-T5-Large; HHEM permanece isolado. A escolha é por elegibilidade e diversidade parcial de família, não por promessa de ganho: os três existentes são DeBERTa e o novo MiniCheck é T5. Medir correlação/dupla falha antes de qualquer ensemble. O ganho incremental mínimo de 1 ponto percentual é critério de triagem proposto, não garantia nem obrigação de obter ganho. A subamostra é exploratória; a comparação final usa o protocolo aprovado.

### E5. Seleção de evidência em documentos longos

Comparar o chunking oficial com recuperação dos `k` trechos mais relevantes, usando BM25 e embeddings, para reduzir truncamento e melhorar cobertura de evidência em ExpertQA, Lfqa e AggreFact-CNN. Pré-registrar `k`, tamanho/overlap dos trechos, modelo de embeddings, licença, estratégia de ranking, custo e fallback. Não alterar offsets do documento original nem a semântica dos contratos. A recuperação é um sinal de seleção, não prova de sustentação.

### E5b. Resolução de correferência antes do chunking/decomposição

**Hipótese:** resolver pronomes e outras expressões correferenciais para seus antecedentes antes do chunking e da decomposição reduz contradições falsas causadas por antecedentes distantes que ficam separados dos pronomes quando o documento é cortado. Alvos: ExpertQA, Lfqa e AggreFact-CNN.

**Base metodológica:** Oukelmoun, Semmar e De Chalendar, “Decomposed Entailment for Factuality Checking and Hallucination Detection”, [arXiv:2608.05823 (6 ago. 2026)](https://arxiv.org/abs/2608.05823). Os autores identificam a correferência durante a extração como gargalo: pronomes separados de antecedentes distantes pelo chunking podem propagar contradições espúrias. O trabalho também declara limitações relevantes: execuções únicas sem estimativa de variância ou testes de significância; ausência de comparação controlada com MiniCheck; ausência de avaliação no LLM-AggreFact; e escopo restrito a alucinações intrínsecas, sem verificação de alegações extrínsecas dependentes de conhecimento externo. O código disponibilizado é declarado “research use only” e não apresenta licença de reutilização identificável nesta consulta. **Não reutilizar, copiar ou adaptar o código dos autores.** Qualquer implementação do AYORAI deverá ser feita do zero, usando ferramenta/biblioteca de correferência cuja licença e revisão tenham sido verificadas e registradas.

**Pré-registro obrigatório antes da execução:**
- Identificar a ferramenta/modelo de correferência, autor, URL, revisão imutável (SHA), licença, restrições, dependências e data da verificação. Sem licença clara e compatível, não usar.
- Comparar E5 sem correferência com E5b com correferência, mantendo iguais os demais parâmetros, conjuntos, partições, chunking, decomposição e configuração do verificador.
- Preservar integralmente o documento original. A substituição de pronomes por antecedentes gera somente uma **visão auxiliar** para recuperação/chunking/verificação; offsets, spans de evidência, citações e referências auditáveis continuam apontando para o texto original. Registrar o mapeamento entre a visão auxiliar e os offsets originais; nunca apresentar texto reescrito como citação literal da fonte.
- Métrica primária: a mesma da seção 3 — BA macro por dataset/coorte, cross-fitted em DEV-A. Reportar também, por coorte, taxa de contradições falsas atribuíveis à quebra de correferência, cobertura, erros, custo e falhas de resolução.
- Critério de decisão, ablações, tratamento de pronomes sem antecedente inequívoco, entidades ambíguas e erros do resolvedor devem ser fixados no pré-registro. Se a resolução alterar o sentido, perder o antecedente ou não puder ser alinhada ao original, usar fallback para o texto original e contabilizar a falha.

### E6. Decomposição e estratégias sequenciais de prova

Avaliar decomposição em fatos atômicos e verificação sequencial inspirada em Ye, Santos-Rodriguez e Simpson, “Teaching Language Models to Check Grounded Claim Factuality with Human Test-Taking Strategies”, ACL 2026, https://aclanthology.org/2026.acl-long.1468/.

O método verifica, em sequência: (C1) sujeito e objeto aparecem no documento; (C2) suas descrições são explicitamente apoiadas; (C3) a relação entre eles é explicitamente apoiada; (C4) o que ainda não foi verificado pode ser inferido do documento. O paper reporta 76,3 ± 0,4 BAcc no LLM-AggreFact com Qwen3-30B-A3B-Instruct e 75,6 ± 0,4 com Qwen3-4B. São números dos autores, não resultados AYORAI.

**Limite de contaminação:** o mesmo paper treina SLMs por SFT/DPO com dados de destilação derivados de LLM-AggreFact. Não usar esses checkpoints, nem reutilizar seus resultados como avaliação independente, pois o benchmark proíbe fine-tuning. Avaliar apenas a estratégia/prompt com modelo geral congelado, sem treino, após pré-registro e verificação de licença/revisão. O repositório de código não declara licença; não reutilizar código.

Pré-registrar decomposição, critérios C1–C4, agregação, falha/ambiguidade e custo. Preservar negação, sujeito, objeto, relação, números, datas, quantificadores e modalidade. Cada fato atômico deve manter vínculo com o texto e evidência originais. Se a decomposição omitir ou alterar informação, falhar de modo conservador e registrar. O LLM continua sendo apenas um sinal; Judge 2.0 permanece autoridade única.

### E7. RuleStance como veto experimental

Avaliar se contradições explícitas detectadas por RuleStance — negação, número ou data — podem funcionar como veto experimental para NOT_SUPPORTED. Medir ganho, falsos vetos, cobertura e custo. RuleStance continua sendo sinal de experimento; nenhum veto será integrado à autoridade do Judge ou à ResponsePolicy sem decisão e PR separadas, expressamente autorizadas.

### E8. Modo seletivo e cobertura

Comparar limiares Mondrian por coorte com limiar global e produzir curva acerto × cobertura por coorte. **Objetivo: maximizar a cobertura sujeita a acerto ≥ 90% (risco observado ≤ 10%) entre as respostas aceitas em cada coorte**, aplicando a regra LTT vigente. Para cada coorte, reportar quantidade aceita (n), acertos, erros, abstenções, acerto entre aceitas, cobertura, risco observado e incerteza. Uma coorte só conta como atingindo o alvo quando houver n ≥ 25 respostas aceitas e acerto observado ≥ 90%; com n < 25, o alvo não é certificado. **Não há piso de cobertura**: a cobertura que resultar deve ser publicada, inclusive quando baixa. Se uma coorte não alcançar o alvo, reportar o resultado sem ocultá-la ou declarar sucesso global.

A regra LTT deverá corresponder exatamente à versão aprovada e mesclada do pré-registro. A Emenda 2 proposta na PR #488 — pular limiares inelegíveis com menos de 25 aceitas, sem certificá-los, testar o primeiro limiar elegível e parar na primeira não rejeição — **não será tratada como vigente enquanto a PR não estiver mesclada e revisada**. Se a PR for alterada ou não for mesclada, reconciliar este roadmap com a regra efetivamente aprovada antes do pré-registro de E8. Nenhum resultado exploratório de DEV-B será descrito como confirmação independente.

## 7. Fase C — congelamento e avaliação TEST

TEST será executado uma única vez, no final, depois de todos os gates. Não há autorização de execução nesta PR.

### C1. Congelamento prévio

Antes de qualquer acesso a TEST, criar e mesclar documento que fixe: modelos e revisões; licenças; protocolo e pré-registros aprovados; ensemble; calibradores; limiares; regra LTT vigente; código e SHA; ambiente/dependências; hashes dos dados e artefatos; métricas e regras de publicação. O congelamento deve anteceder a execução TEST.

### C2. Workflow TEST protegido

Preparar workflow protegido equivalente ao DEV, com aprovação explícita do mantenedor e execução única. Verificar isolamento, permissões, retenção, logs e publicação exclusivamente agregada. Não automatizar dispatch nesta fase. Resultado negativo, inconclusivo ou com falha deverá ser publicado honestamente, sem retuning nem segunda tentativa sobre TEST.

### C3. Release e publicação científica

Após revisão do resultado e autorização do mantenedor, avaliar release v0.8.0 com DOI e preprint metodológico no arXiv, descrevendo calibração, seleção pré-registrada, controles estatísticos e limitações. Solicitar inclusão em ranking externo somente se houver contribuição própria identificável (método/ensemble), comparação metodologicamente compatível e créditos claros aos modelos de terceiros. Não reivindicar posição em ranking sem confirmação da fonte e protocolo.

## 8. Fase D — diferencial brasileiro

### D1. RGC em português

Manter o fluxo RGC independente: Piloto 02 manual, sem IA; segunda anotação humana independente; revisão humana independente; conjunto definitivo planejado de 300 casos; pré-registro, proveniência, isolamento e congelamento aprovados antes de qualquer execução. O protocolo RGC continua no estado registrado em `docs/STATUS.md`; este roadmap não o congela, não cria casos, não rotula casos e não autoriza execução.

### D2. Avaliação multilíngue em português

Avaliar mDeBERTa e o verificador que eventualmente vencer E4 em português com protocolo próprio, fontes e licenças verificadas, pré-registro e partições DEV/TEST separadas. Não extrapolar resultados do LLM-AggreFact para português brasileiro. Reportar limitações linguísticas, domínio, prevalência, cobertura e proveniência.

## 9. Ordem operacional proposta e dependências

A ordem operacional prioritária, após aprovação do mantenedor, é:

1. **A1** — implementar e testar cache privado cifrado antes de qualquer nova inferência DEV. Predições e labels ficam separados; nenhum label é acessível ao processo de inferência.
2. **A4** — auditoria agregada de erros do baseline atual, reutilizando artefatos existentes e sem exportar linhas por instância.
3. **E3** — somente após DEC-024 aprovada; reutilizar cache e usar OOF. Incluir análise de correlação/dupla falha e comparação com o melhor membro.
4. **Decisão de GPU/custo** — apresentar alternativas e aguardar escolha explícita antes de E4.
5. **E4** — piloto de 200 casos para throughput após A1; MiniCheck-Flan-T5-Large em DEV-A. HHEM somente em dados sintéticos para throughput enquanto a proveniência não for esclarecida. O painel confirmatório full DEV proposto é baseline de três modelos + MiniCheck-Flan-T5-Large; HHEM não entra no agregado de 11 coortes.
6. **DEV completo** — só após gates de contaminação/licença, throughput, pin SHA e pré-registro; resultados por coorte e macro, com intervalos de incerteza.
7. **E5, E5b, E6–E8** — cada experimento com PR/pré-registro e autorização próprios; E5b comparado diretamente com E5; E6 pode testar estratégias sequenciais de prova sem reutilizar código ou checkpoints treinados no LLM-AggreFact.
8. **A2/A3** — permanecem tarefas de robustez antes de TEST: A2 depende da DEC de segurança e migração de secrets pelo mantenedor; A3 exige protocolo de determinismo pré-registrado. Não bloquear A4 enquanto essas dependências não forem necessárias.
9. **C1–C3** — congelamento e TEST único, após todos os gates e autorização específica.
10. **D1–D2** — trilha brasileira paralela, sujeita aos gates humanos e de protocolo já existentes.

A ordem não autoriza execução automática. Cada PR de implementação terá escopo único e não poderá alterar artefatos protegidos.

## 10. Política de reporte e encerramento

Para cada experimento, publicar: hipótese; pré-registro e versão; partição; SHA do código; hashes de dados/configuração; modelos/revisões/licenças; métrica primária e secundárias; cobertura; custo; falhas/desvios; limitações; e decisão de avançar ou parar. Somente agregados serão públicos.

Se um resultado não superar o baseline, se o alvo seletivo de acerto não for atingido em uma coorte, se a licença for incompatível, se a reprodução divergir ou se o protocolo não puder ser cumprido, registrar o resultado observado (incluindo cobertura, mesmo que baixa) e interromper ou reavaliar o caminho correspondente. Não alterar retroativamente hipótese, métrica ou critério de parada.

**Estado final deste documento:** roadmap e regra de escolha propostos; DEC-024 não aprovada; nenhum código implementado; nenhum novo benchmark executado por esta alteração; TEST intocado; nenhuma alteração em Judge, Golden, hashes, thresholds do sistema, RGC, Piloto 02 ou ResponsePolicy. O radar documental complementar está em `docs/benchmarks/RADAR-TECNOLOGICO-2026-11.md`.
