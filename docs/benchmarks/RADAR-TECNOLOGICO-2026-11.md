# Radar tecnológico — AYORAI ATTRACTOR
**Data da verificação:** 2026-11-07 (horário de São Paulo).  
**Responsável:** ANDERSON AYORA.  
**Base documental:** `main` após merge da PR #489, SHA `f8895caab6f3d81fdfea0eaffa91a7a255477d36`.  
**Natureza:** pesquisa documental e recomendações; não autoriza inferência, execução de benchmark, treinamento, calibração, alteração de código ou uso de modelos.

## 1. Conclusão executiva

O melhor caminho para o AYORAI não é copiar o primeiro colocado de um leaderboard nem aumentar o ensemble por quantidade. É construir uma avaliação reproduzível que prove, por coorte, que cada componente adiciona informação independente, respeita as licenças e não tem contaminação conhecida.

As conclusões práticas desta revisão são:

1. **Novo gate obrigatório de contaminação:** registrar origem dos dados de pré-treinamento, fine-tuning, dados sintéticos, preferências, avaliação e modelos-base. Avaliação anterior em um benchmark não é automaticamente contaminação de treinamento; treino no benchmark ou em uma coorte é.
2. **MiniCheck-Flan-T5-Large é a adição CPU prioritária:** 0,8B, MIT, 75,0 no leaderboard atual, e arquitetura T5 diferente dos três verificadores DeBERTa do baseline. O desempenho real e o throughput do AYORAI precisam ser medidos.
3. **HHEM-2.1-Open não pode entrar no agregado confirmatório das 11 coortes:** os autores declaram que foi treinado com o split de treino de RAGTruth e outros conjuntos cuja composição específica é confidencial. RAGTruth está bloqueado; as outras coortes não estão liberadas para confirmação até que as demais fontes sejam esclarecidas.
4. **HalluGuard merece avaliação posterior, não imediata:** os pesos existem, Apache-2.0 declarado; o paper final reporta 77,1% BAcc no LLM-AggreFact e 84,4% em RAGTruth, resultados dos autores. É um modelo generativo de 4B, com custo e parsing maiores; quantização GGUF de terceiros existe, mas precisa de auditoria independente.
5. **Granite Guardian 3.3 é condicional:** 8B, Apache-2.0, 76,5 no leaderboard; os dados de treino incluem HH-RLHF e dados sintéticos internos, mas a proveniência completa do conjunto sintético não está enumerada. É inglês e exige o modo/prompt prescrito.
6. **Bespoke-MiniCheck-7B é somente pesquisa não comercial:** CC BY-NC 4.0. O 77,4 do leaderboard não é mais o primeiro lugar na página consultada; há sistemas com pontuação superior. Não pode integrar produto comercial sem licença comercial separada.
7. **Paladin-mini deve ser removido:** o model card identifica LLM-AggreFact entre os datasets usados no treino e a licença é `other`.
8. **LettuceDetect só pode ser avaliado fora de RAGTruth:** seu paper declara treino no RAGTruth; é um modelo de classificação por token, não um classificador de sentença intercambiável sem camada de agregação.
9. **A principal descoberta metodológica é diversidade de erros, não diversidade nominal:** os três modelos atuais são da família DeBERTa; MiniCheck-Flan-T5-Large e HHEM são ambos T5/Flan-T5. Cinco nomes não significam cinco sinais independentes. Medir correlação de erros e ganho incremental é obrigatório.
10. **RAIM e as estratégias de prova são referências de método, não receitas para copiar:** os resultados publicados têm partições, métricas, custos e procedimentos diferentes. O stacker RAIM usa rótulos; qualquer adaptação no LLM-AggreFact depende da DEC-024.

## 2. Gate obrigatório: contaminação e proveniência

Antes de qualquer modelo entrar em um experimento, criar um registro por artefato e por revisão imutável. A auditoria deve cobrir: modelo final, modelo-base, adapters/LoRA, datasets de treino, dados sintéticos e de preferência, corpora de pré-treinamento quando divulgados, prompt/few-shot examples, código remoto e dependências.

### 2.1 Classes de contaminação

| Classe | Evidência | Regra |
|---|---|---|
| C0 — sem sobreposição direta conhecida | Fontes de treino divulgadas e sem correspondência conhecida com o benchmark/coorte | Elegível, mantendo a ressalva sobre corpora de pré-treinamento opacos |
| C1 — treino direto no LLM-AggreFact completo | Dataset ou split do benchmark usado para treino, SFT, DPO, distilação ou ajuste | BLOQUEADO para as 11 coortes |
| C2 — treino em uma coorte-fonte | RAGTruth, AggreFact-CNN/XSum, TofuEval, WiCE etc. usado no treino | BLOQUEADO apenas na coorte sobreposta; outras coortes somente se a proveniência restante estiver verificada |
| C3 — derivação/sintetização de benchmark | Dados sintéticos, preferências, pares ou rótulos gerados a partir de itens/labels do benchmark | Mesma regra de C1/C2, conforme a abrangência |
| C4 — avaliação publicada, sem treino conhecido no benchmark | O autor avaliou o modelo no LLM-AggreFact, mas não declara treino nesses dados | Não é, por si só, contaminação de treino. Registrar a avaliação dos autores e nunca apresentá-la como medição independente do AYORAI |
| C5 — proveniência insuficiente/oculta | Fontes de treino incompletas, “other datasets” não identificados, corpora não auditáveis | BLOQUEADO para resultado confirmatório no conjunto afetado. Só permitir exploração em dados externos comprovadamente não sobrepostos, com rótulo de incerteza |
| C6 — licença ou código incompatível | Licença não comercial, “other” sem termos claros, código remoto não revisado | BLOQUEADO até solução documental e aprovação |

**Distinção crítica:** um artigo dizer que avaliou seu modelo no LLM-AggreFact não prova que o treinou nele. Por outro lado, um model card dizer “dados sintéticos” não prova ausência de contaminação: é necessário identificar a origem dos documentos, prompts, rótulos e critérios usados para gerar os exemplos.

### 2.2 Auditoria de corpus e risco residual

- Conferir separadamente o checkpoint final e o modelo-base. A licença Apache-2.0 do fine-tune não substitui a verificação da licença e das condições do modelo-base.
- Quando o pré-treinamento tiver corpus amplo e opaco, registrar **“sobreposição não verificável”**, não “livre de contaminação”. A ausência de um dataset listado não é prova de ausência.
- Fazer deduplicação exata e aproximada entre exemplos de avaliação e qualquer corpus de treino disponível; registrar método, hashes, normalização e limites. Deduplicação não prova ausência de memorização ou exposição prévia.
- Manter um ledger versionado com: `model_id`, revisão SHA, base model e SHA, autores, licença, dataset IDs, splits, origem de dados sintéticos, evidência/URL, data de verificação, coortes proibidas, status e responsável.
- Repetir o gate quando a revisão do modelo, dataset, tokenizer, código remoto ou dependência mudar. Não herdar aprovação entre revisões.

### 2.3 Coortes do LLM-AggreFact que precisam ser mapeadas

O benchmark agrega 11 conjuntos: AggreFact-CNN, AggreFact-XSum, TofuEval-MediaS, TofuEval-MeetB, RAGTruth, ClaimVerify, LFQA, ExpertQA, REVEAL, FactCheck-GPT e WiCE. A matriz de contaminação deve ser preenchida por coorte, não apenas por benchmark global.

## 3. Radar de modelos

Os resultados abaixo são referências publicadas. Não são medições do AYORAI e não devem ser tratados como comparação perfeitamente pareada: leaderboard, paper, split, prompt, modo de geração, limiar e agregação podem diferir.

| Modelo | Tamanho / licença | Evidência de treino e contaminação | Referência pública | Decisão recomendada |
|---|---|---|---|---|
| MiniCheck-Flan-T5-Large — `lytang/MiniCheck-Flan-T5-Large` | 0,8B; MIT | Treino declarado de 35K exemplos: 21K ANLI + 14K sintéticos gerados de forma estruturada; os autores apresentam LLM-AggreFact como benchmark não visto no treino. Modelo T5. | 75,0 BAcc média no leaderboard atual | **PRIORIDADE ALTA.** Piloto CPU de 200 itens, depois avaliação full DEV se throughput e revisão SHA forem aceitáveis |
| HHEM-2.1-Open — `vectara/hallucination_evaluation_model` | 109,6M; Apache-2.0; base Flan-T5-base | Treinado com RAGTruth train split e outros datasets; Vectara declara que detalhes específicos de treino são confidenciais. Usa `trust_remote_code=True`. | Não aparece como linha própria comparável no leaderboard atual consultado; resultados Vectara antigos usam subconjuntos/protocolos diferentes | **BLOQUEADO para confirmação no LLM-AggreFact** até esclarecer os outros datasets. RAGTruth sempre bloqueado. Só piloto de throughput com dados sintéticos, sem pontuação de benchmark |
| HalluGuard-Qwen3-4B — `lrsbrgrn/HalluGuard-Qwen3-4B` | 4B; Apache-2.0; base Qwen3-4B Apache-2.0 | Fine-tune LoRA+ORPO em 76.708 preferências sintéticas derivadas de FineWeb. Não declara treino direto em LLM-AggreFact; o corpus-base do Qwen3 mantém risco residual não auditável por completo. | Preprint: 75,7%; artigo final ACL Findings 2026: 77,1% no LLM-AggreFact e 84,4% em RAGTruth | **PRIORIDADE POSTERIOR.** Avaliar com GPU ou quantização validada, depois de fixar SHA, base, dependências, licença e protocolo de inferência. Resultados são dos autores |
| Granite Guardian 3.3 — `ibm-granite/granite-guardian-3.3-8b` | 8B; Apache-2.0 | Treino declarado com HH-RLHF, anotações humanas e dados sintéticos de red-team; fontes completas do material sintético não enumeradas. Inglês. | 76,5 BAcc no leaderboard; 76,5 em modo think e 76,1 em no-think na página de referência | **CONDICIONAL.** Solicitar proveniência adicional; não usar em confirmação enquanto fontes sintéticas não forem esclarecidas. GPU. Fixar think/no-think e prompt |
| Bespoke-MiniCheck-7B — `bespokelabs/Bespoke-MiniCheck-7B` | 7B/8B conforme contagem do card; CC BY-NC 4.0 | 21K ANLI + 14K sintéticos; autores dizem que as fontes foram curadas independentemente do benchmark. | 77,4 no leaderboard consultado; não é mais o primeiro colocado na página atual | **PESQUISA NÃO COMERCIAL.** Não integrar produto nem redistribuir sem licença comercial escrita. Não perseguir como solução de produto |
| Paladin-mini — `qualifire/context-grounding-paladin-mini` | 3,8B; licença `other`; gated | O card lista explicitamente `lytang/LLM-AggreFact` entre os datasets de treino | Resultados não são elegíveis como avaliação limpa | **REMOVER DO RADAR DE CANDIDATOS.** Contaminação direta + licença sem clareza |
| LettuceDetect — `KRLabsOrg/lettucedect-large-modernbert-en-v1` | 395,8M; MIT; ModernBERT | O artigo declara treino no RAGTruth | 79,22% F1 example-level no RAGTruth, resultado dos autores | **CONDICIONAL POR COORTE.** Bloquear RAGTruth; outras coortes somente se não houver sobreposição. Saída token-level exige agregação e validação separadas |

### 3.1 Interpretação por modelo

**MiniCheck-Flan-T5-Large.** É a melhor próxima adição de baixo custo relativo. Os três verificadores atuais do AYORAI são DeBERTa; este checkpoint acrescenta uma família T5. A licença MIT e o resultado 75,0 são confirmados nas fontes consultadas. O modelo ocupa aproximadamente 3,14 GB no repositório de pesos; isso não impede CPU, mas tampouco prova throughput adequado. Medir RAM, tempo e timeout no hardware real. O modelo e suas dependências devem ser pinados.

**HHEM-2.1-Open.** A aparente vantagem operacional — 109,6M parâmetros, menos de 600 MB de RAM e cerca de 1,5 s por entrada de 2K tokens em CPU x86 segundo a documentação Vectara — não elimina a contaminação. O artigo de 2025 afirma explicitamente que HHEM-2.1-Open usou RAGTruth train split e outros conjuntos, cujos detalhes são confidenciais. O model card exige `trust_remote_code=True`. Não permitir que rapidez operacional se sobreponha ao gate científico. A revisão do código remoto e a fixação SHA são obrigatórias mesmo para teste de engenharia.

**HalluGuard.** O repositório oficial contém pesos Safetensors e declara Apache-2.0; o Qwen3-4B base também declara Apache-2.0. O paper final ACL Findings 2026 é a referência principal; 75,7% é o valor do preprint, substituído no artigo final por 77,1%. A quantização GGUF de mradermacher existe e declara Apache-2.0, com Q4_K_M em torno de 2,5 GB, mas é conversão de terceiro: verificar SHA, lineage, qualidade da quantização e equivalência do template de chat. Não assumir que quantização mantém o score dos autores.

**Granite Guardian 3.3.** A página oficial declara que deve ser usado no modo de scoring prescrito e que foi treinado/testado apenas em inglês. O modo think e no-think produz resultados diferentes; não misturar pontuações. A licença Apache-2.0 está declarada, mas a proveniência do dado sintético de treino não é suficientemente detalhada para certificar ausência de sobreposição com todas as coortes.

**Bespoke-MiniCheck-7B.** O card informa 21K exemplos ANLI e 14K sintéticos, com curadoria independente do benchmark. Porém a licença é explicitamente CC BY-NC 4.0; a página indica contato para licença comercial. O leaderboard atual já contém sistemas com médias superiores a 77,4. Manter apenas como referência acadêmica não comercial, isolada de qualquer produto ou pacote distribuído.

**Paladin-mini.** O card lista LLM-AggreFact como dataset usado no treinamento e a licença é `other`. Não há justificativa para mantê-lo como candidato limpo.

**LettuceDetect.** O artigo declara que foi treinado no RAGTruth e avalia detecção token-level. Não pontuar no RAGTruth. Em outras coortes, converter tokens em spans/claims requer regra própria, com offsets do original e métrica de nível de instância compatível; não comparar F1 token-level com BA claim-level.

## 4. O que o leaderboard realmente diz

Na página oficial consultada em 2026-11-07, o leaderboard lista 47 modelos disponíveis e exibe 19 selecionados. A tabela atual mostra:
- nimble-v4-max: 79,5;
- Clef: 79,0;
- Decider v1.2 e Jev 1.13.0: 78,7;
- d1-ultra: 78,5;
- nimble-v4: 77,8;
- Bespoke-MiniCheck-7B: 77,4;
- Granite Guardian 3.3: 76,5;
- FactCG-DeBERTa-L: 75,6;
- MiniCheck-Flan-T5-L: 75,0.

Logo, **Bespoke 77,4 não é mais o primeiro lugar** no leaderboard consultado. O topo atual contém modelos comerciais/proprietários e não deve ser confundido com uma comparação de modelos abertos elegíveis a produto. A média do leaderboard também não é automaticamente a mesma métrica macro, partição, modo de inferência e protocolo do experimento interno do AYORAI.

Não usar o ranking como critério de seleção da v0.8. Ele serve para descobrir candidatos e formular hipóteses; a decisão do AYORAI vem de DEV-A cross-fitted, gates de contaminação/licença, DEV-B e, por último, TEST único congelado.

## 5. Ideia E6 — estratégias humanas de prova

Referência: Ye, Santos-Rodriguez e Simpson, “Teaching Language Models to Check Grounded Claim Factuality with Human Test-Taking Strategies”, ACL 2026, DOI/URL: https://aclanthology.org/2026.acl-long.1468/.

O artigo divide a afirmação em fatos atômicos e verifica cada fato sequencialmente contra o documento:
1. C1 — sujeito e objeto aparecem no documento;
2. C2 — descrições de sujeito e objeto são explicitamente apoiadas;
3. C3 — a relação entre sujeito e objeto é explicitamente apoiada;
4. C4 — o que ainda não foi explicitamente verificado pode ser inferido do documento.

No LLM-AggreFact, o pipeline com Qwen3-30B-A3B-Instruct reporta 76,3 ± 0,4 BAcc; a versão Qwen3-4B reporta 75,6 ± 0,4. O artigo também relata redução superior a 80% no uso de tokens contra raciocínio aberto não guiado. Esses valores são dos autores e não são comparáveis diretamente aos resultados internos sem reproduzir o protocolo.

**Restrição de contaminação:** o artigo também treina modelos pequenos por SFT/DPO com dados de destilação derivados de LLM-AggreFact. Não usar esses checkpoints nem resultados dos modelos destilados como evidência independente do AYORAI, pois os termos do benchmark proíbem fine-tuning. A ideia de prompt/estratégia aplicada a um modelo geral congelado pode ser estudada separadamente, sem treino e após pré-registro.

O repositório público `Haruhi07/Test-Taking` não declara licença no metadado GitHub consultado. Não copiar nem reutilizar código. Implementação própria somente após pré-registro, mantendo fatos atômicos ligados ao texto original, preservando negação, números, datas, quantificadores e entidades, e falhando de forma conservadora quando a decomposição perder informação.

## 6. Referência E3 — RAIM e ensembles robustos

Referência: “RAIM: Robust Aggregation of Inexpensive Models for Hallucination Detection”, arXiv:2609.39229, https://arxiv.org/abs/2609.39229.

RAIM estuda um painel de dez juízes open-weight de 4B–9B, de famílias/desenvolvedores distintos. Combina votos por regressão logística empilhada (stacking), treinada com rótulos e cross-fitting de cinco folds; compara com maioria simples, média, melhor membro e referência de fronteira. Usa bootstrap pareado por clusters e argumenta que o painel só agrega valor quando existem membros competentes com erros suficientemente descorrelacionados.

Os autores reportam 69,5 BAcc no subconjunto de quatro conjuntos LLM-AggreFact, 73,0 na suíte de oito conjuntos e 50–100 rótulos para calibração de domínio. Não é comparação direta com o leaderboard completo: os quatro conjuntos LLM-AggreFact são subconjuntos do split de teste e o protocolo/seleção/denominadores diferem. O próprio paper relata que o painel pode perder para o melhor membro em vários conjuntos; aumentar a quantidade de modelos não garante ganho.

**Aplicação recomendada ao AYORAI:**
- calcular correlação de erros, dupla falha, desacordo e ganho incremental de cada modelo em predições OOF;
- comparar cada candidato com o melhor modelo individual, não apenas com a média dos membros;
- avaliar ablações por família: DeBERTa, T5/Flan-T5 e generativos;
- não adicionar modelo se apenas repetir os erros de um modelo existente;
- usar bootstrap pareado por unidade de origem/documento quando houver clusters, não bootstrap ingênuo de linhas independentes;
- qualquer stacking ajustado com rótulos do LLM-AggreFact depende da DEC-024; não copiar o código RAIM, pois os repositórios consultados declaram licença `other`/NOASSERTION.

## 7. Consequências para o ensemble CPU

O plano inicial de cinco modelos CPU precisa ser dividido em dois níveis:

### 7.1 Painel confirmatório recomendado para DEV completo

Manter os três verificadores já avaliados:
- mDeBERTa-v3-base NLI;
- MiniCheck-DeBERTa-v3-Large;
- FactCG-DeBERTa-v3-Large.

Adicionar como prioridade:
- MiniCheck-Flan-T5-Large.

Esse painel tem quatro verificadores elegíveis segundo as informações divulgadas, sujeito à auditoria do SHA, dados-base e dependências. É uma comparação mais defensável do que incluir HHEM no agregado completo.

### 7.2 HHEM: trilha isolada

- RAGTruth: bloqueado por treino direto no split de treino.
- Outras coortes LLM-AggreFact: não liberar para confirmação até que a Vectara esclareça os outros datasets de treino. Se não houver esclarecimento, manter fora do agregado confirmatório.
- Piloto de throughput: pode usar exemplos sintéticos fora do benchmark, sem rótulos LLM-AggreFact, apenas para medir consumo, latência e estabilidade do código remoto.
- Se surgir documentação suficiente, registrar exatamente quais coortes são elegíveis antes de executar.

### 7.3 Regras de diversidade

Não presumir independência pelo número de checkpoints. MiniCheck-Flan-T5-Large e HHEM são ambos Flan-T5/T5; os três verificadores atuais pertencem à família DeBERTa. Para cada novo sinal, reportar:
- correlação de scores e de erros;
- matriz de dupla falha por coorte;
- ganho OOF marginal ao adicioná-lo ao melhor modelo;
- estabilidade do ganho por fold e por coorte;
- custo/latência/memória por mil exemplos;
- impacto de truncamento e comprimento.

O objetivo do ensemble é melhorar erros difíceis e generalização entre coortes, não aumentar o número de membros.

## 8. Plano operacional recomendado

A ordem que preserva o trabalho já feito e reduz retrabalho é:

1. **A1 — cache privado cifrado antes de qualquer nova inferência DEV.** O cache de predições não deve conter rótulos gold. Guardar scores e metadados de inferência; manter labels em artefato separado, com junção somente no avaliador autorizado. Incluir hash do input, model ID/SHA, tokenizer, configuração, score direction, status, runtime e checksum. Exigir idempotência, retomada, detecção de duplicatas e escrita atômica.
2. **A4 — auditoria agregada dos erros atuais.** Usar somente agregados e métricas de erro por coorte/comprimento/truncamento. Nenhum dado por instância em artefato público.
3. **E3 — somente depois da DEC-024.** Reutilizar cache; comparação OOF e sem acesso a DEV-B/TEST durante ajuste.
4. **Decisão de GPU/custo.** Só então apresentar alternativas e aguardar decisão do mantenedor.
5. **E4 — pilotos de throughput.** Rodar 200 casos DEV-A para MiniCheck-Flan-T5-Large depois de A1; testar HHEM apenas com dados sintéticos para throughput enquanto o gate de contaminação permanecer aberto. Registrar p50/p95, RAM/VRAM, tempo total, timeouts, falhas, truncamento e consumo.
6. **DEV completo:** quatro verificadores no painel confirmatório de 11 coortes, se os gates finais forem aprovados. HHEM não entra no agregado até liberação documental. Se a proveniência de qualquer novo modelo não puder ser confirmada, excluir ou separar por coorte antes de pontuar.
7. **E5, E5b, E6, E7 e E8:** experimentos independentes, cada um com pré-registro e autorização. E5b deve ser comparado diretamente com E5; E6 pode usar a ideia de estratégias de prova, sem código de terceiros e sem SFT/DPO no benchmark.
8. **C — TEST único:** congelar configuração e hashes; executar uma única vez somente após aprovação explícita.

**Urgência operacional:** a PR #488 continua sendo dependência separada para a Emenda 2 do LTT e retenção de sete dias. Não tratar a proposta como regra vigente até merge. A re-agregação indicada pelo mantenedor deve ocorrer dentro da janela operacional declarada (até 2026-11-08 13:00 BRT), mas este radar não autoriza merge da #488 nem dispatch. A autorização específica é necessária antes dessas ações.

## 9. Controles estatísticos adicionais recomendados

- Reportar BA por coorte e macro média; também sensibilidade, especificidade, precisão, F1, MCC, ECE/Brier quando aplicável. Não selecionar pela métrica secundária.
- Usar intervalos de confiança pareados e bootstrap por cluster/documento quando houver dependência entre exemplos. Informar unidade de reamostragem, número de replicações e seed.
- Corrigir multiplicidade quando várias configurações/modelos forem comparados; pré-registrar a família de hipóteses. Distinguir diferença estatística de diferença prática.
- Mostrar resultados absolutos e diferenças pareadas contra o baseline, com intervalo. Não usar sobreposição de intervalos marginais como substituto de teste pareado.
- Separar métricas de classificação de métricas seletivas. A meta de 90% entre aceitas não é piso global nem garantia estatística por si só; certificação depende do teste LTT, nível de erro e correção por múltiplas coortes definidos no protocolo vigente.
- Não permitir que DEV-B retroalimente a escolha; não tocar TEST até congelamento.
- Se houver ruído de rótulo, investigar por amostragem humana independente e protocolo cego; não supor percentual de ruído nem descontá-lo aritmeticamente do score.

## 10. Decisões recomendadas ao mantenedor

1. Aprovar MiniCheck-Flan-T5-Large como próximo candidato CPU, sujeito a pin/licença e piloto.
2. Não incluir HHEM no agregado confirmatório das 11 coortes enquanto a proveniência adicional não for divulgada; RAGTruth é inelegível.
3. Manter HalluGuard para rodada posterior, com revisão SHA e orçamento GPU/quantização.
4. Manter Granite como candidato condicional, bloqueado até esclarecimento da proveniência dos dados sintéticos.
5. Excluir Paladin-mini do radar de candidatos.
6. Restringir Bespoke-MiniCheck a pesquisa não comercial; não usar no produto.
7. Permitir LettuceDetect apenas fora de RAGTruth, após avaliação de compatibilidade da tarefa.
8. Adotar análise de correlação/dupla falha e bootstrap pareado por cluster como exigências do relatório E3/E4.
9. Manter stacking com rótulos bloqueado até DEC-024.
10. Não alterar Judge 2.0, Golden, hashes, thresholds do sistema, RGC, Piloto 02 ou ResponsePolicy.

## 11. Fontes oficiais e primárias consultadas

**Data de verificação: 2026-11-07.** Os links abaixo são a base de evidência desta versão; revalidar antes de fixar revisões ou executar.

### Benchmark e MiniCheck
- [LLM-AggreFact Leaderboard](https://llm-aggrefact.github.io/) — 11 conjuntos e tabela atual de modelos/BA.
- [MiniCheck paper, arXiv:2404.10774](https://arxiv.org/abs/2404.10774) — dados sintéticos, 770M e benchmark.
- [MiniCheck-Flan-T5-Large model card](https://huggingface.co/lytang/MiniCheck-Flan-T5-Large) — MIT e arquitetura T5.
- [Bespoke-MiniCheck-7B model card](https://huggingface.co/bespokelabs/Bespoke-MiniCheck-7B) — treino, alegação de fontes independentes e licença CC BY-NC 4.0.

### HHEM e contaminação
- [HHEM-2.1-Open model card](https://huggingface.co/vectara/hallucination_evaluation_model) — Apache-2.0, Flan-T5-base, código remoto.
- [Benchmarking LLM Faithfulness in RAG with Evolving Leaderboards, EMNLP Industry 2025](https://aclanthology.org/2025.emnlp-industry.54/) — declaração explícita de treino com RAGTruth train split e outros conjuntos confidenciais.
- [HHEM-2.1 blog da Vectara](https://www.vectara.com/blog/hhem-2-1-a-better-hallucination-detection-model) — benchmark antigo, subsets e velocidade/CPU.

### HalluGuard, Granite, Paladin e LettuceDetect
- [HalluGuard preprint, arXiv:2510.00880](https://arxiv.org/abs/2510.00880) — resultado histórico do preprint.
- [HalluGuard final, Findings of ACL 2026](https://aclanthology.org/2026.findings-acl.835/) — 77,1% LLM-AggreFact e 84,4% RAGTruth.
- [HalluGuard model card](https://huggingface.co/lrsbrgrn/HalluGuard-Qwen3-4B) — pesos, Safetensors, Apache-2.0, dataset sintético, base Qwen3-4B.
- [Qwen3-4B model card](https://huggingface.co/Qwen/Qwen3-4B) — licença Apache-2.0 do modelo-base.
- [HalluGuard GGUF de terceiro](https://huggingface.co/mradermacher/HalluGuard-Qwen3-4B-GGUF) — conversão quantizada; verificar revisão e integridade antes de usar.
- [Granite Guardian 3.3 model card](https://huggingface.co/ibm-granite/granite-guardian-3.3-8b) — Apache-2.0, dados de treino, modos e escopo inglês.
- [Granite Guardian docs oficiais](https://www.ibm.com/granite/docs/models/guardian) — modo de scoring e escopo de uso.
- [Paladin-mini model card](https://huggingface.co/qualifire/context-grounding-paladin-mini) — dataset LLM-AggreFact e licença `other`.
- [LettuceDetect paper, arXiv:2502.17125](https://arxiv.org/abs/2502.17125) — treino no RAGTruth e detecção por token.
- [LettuceDetect model card](https://huggingface.co/KRLabsOrg/lettucedect-large-modernbert-en-v1) — MIT e checkpoint.

### Estratégias de prova e ensemble
- [Ye et al., ACL 2026, 2026.acl-long.1468](https://aclanthology.org/2026.acl-long.1468/) — quatro critérios sequenciais, Qwen3-30B-A3B 76,3 ± 0,4 e Qwen3-4B 75,6 ± 0,4; inclui também SLMs treinados com dados derivados do benchmark, que não devem ser reutilizados.
- [Repositório Test-Taking](https://github.com/Haruhi07/Test-Taking) — sem licença declarada no metadado consultado; não reutilizar código.
- [RAIM, arXiv:2609.39229](https://arxiv.org/abs/2609.39229) — stacking, cross-fitting, bootstrap pareado por cluster, resultados e limitações.
- [RAIM verdicts repository](https://github.com/eOnofri04/raim-verdicts) e [RAIM analysis repository](https://github.com/eOnofri04/raim-analysis) — licença GitHub `other`/NOASSERTION; não reutilizar código sem autorização/licença clara.

**Estado final:** radar documental; nenhum modelo executado; nenhum score novo produzido; nenhum dado por instância exportado; nenhuma alteração de código; nenhum ajuste/calibração autorizado; DEC-024 continua pendente.
