# Radar tecnológico — AYORAI ATTRACTOR
**Data da verificação:** 2026-11-07 (horário de São Paulo).  
**Responsável:** ANDERSON AYORA.  
**Base documental:** `main` após merge da PR #489, SHA `f8895caab6f3d81fdfea0eaffa91a7a255477d36`.  
**Natureza:** pesquisa documental e recomendações; não autoriza inferência, execução de benchmark, treinamento, calibração, alteração de código ou uso de modelos.

## 1. Conclusão executiva

O melhor caminho para o AYORAI não é copiar o primeiro colocado de um leaderboard nem aumentar o ensemble por quantidade. É construir uma avaliação reproduzível que prove, por coorte, que cada componente adiciona informação independente, respeita as licenças e não tem contaminação conhecida.

As conclusões práticas desta revisão são:

1. **O gate precisa cobrir treinamento, fonte de dados, licença e exposição ao benchmark.** O checkpoint, o modelo-base, o dataset de fine-tuning, os dados sintéticos, a calibração, a seleção de limiar e a exposição a DEV/TEST precisam de registros separados.
2. **A proposta inicial de cinco modelos CPU não é elegível como painel confirmatório homogêneo.** MiniCheck-Flan-T5 e HHEM têm sobreposições conhecidas com coortes; MiniCheck/FactCG também usam ANLI (CC BY-NC) e dados sintéticos derivados de fontes Wikipedia/Google News. Os modelos do baseline têm restrições de licença que precisam ser respeitadas.
3. **MiniCheck-Flan-T5-Large não é um candidato limpo para as 11 coortes nem para produto comercial.** Apesar dos pesos MIT e score publicado 75,0, o fine-tune usa 21K ANLI (CC BY-NC 4.0), o backbone FLAN-T5 foi instruído com CNN/DailyMail e XSum, e o C2D do MiniCheck usa claims da Wikipedia com citações, citando WiCE. No mínimo, bloquear CNN, XSum e WiCE; investigar REVEAL e notícias por deduplicação. EVAL_ONLY para produto.
4. **HHEM-2.1-Open não entra no agregado confirmatório:** treinado com RAGTruth train split e outros conjuntos confidenciais; usa base Flan-T5 (que também tem exposição a CNN/DailyMail e XSum). RAGTruth, CNN e XSum ficam bloqueados; as demais coortes continuam não verificadas.
5. **O baseline também precisa do gate, sem grandfathering.** mDeBERTa usa XNLI (CC BY-NC); MiniCheck-DeBERTa usa ANLI (CC BY-NC) e dados sintéticos MiniCheck; FactCG usa ANLI, C2D/D2C e faz threshold tuning por dataset no validation do LLM-AggreFact. São referências de pesquisa, não modelos comerciais limpos.
6. **Novo candidato CPU recomendado:** cross-encoder/nli-distilroberta-base, 82,1M, Apache-2.0, treinado em SNLI/MultiNLI; não há sobreposição direta conhecida com as 11 coortes. É um NLI genérico, não um detector específico, e precisa de piloto/avaliação própria.
7. **LettuceDetect é um candidato complementar para 10 coortes:** MIT, treinado em RAGTruth (Apache-2.0); bloquear RAGTruth. Saída token-level exige agregação claim-level e validação própria.
8. **HalluGuard permanece candidato posterior para produto/benchmark:** pesos e base Apache-2.0; 77,1% no artigo final e 84,4% em RAGTruth são resultados dos autores. Verificar Qwen3 base, SHA, FineWeb e protocolo; quantização GGUF é de terceiro.
9. **Granite Guardian 3.3 é condicional:** 8B, Apache-2.0, 76,5 no leaderboard; proveniência do dado sintético interno não está enumerada. Inglês e modo/prompt prescrito.
10. **Bespoke-MiniCheck é pesquisa não comercial; Paladin-mini deve ser removido.** Bespoke é CC BY-NC 4.0 e não é mais primeiro no leaderboard. Paladin lista LLM-AggreFact entre os dados de treino e licença other.
11. **Não perseguir cinco nomes; perseguir cinco sinais elegíveis e complementares.** Medir correlação de erros, dupla falha, ganho marginal, estabilidade por coorte e custo. Painéis com diferentes coortes elegíveis não podem ser comparados por uma média global com denominadores diferentes.
12. **RAIM e estratégias de prova são referências de método, não receitas para copiar.** O stacker RAIM usa rótulos; qualquer adaptação no LLM-AggreFact depende da DEC-024.

## 2. Gate obrigatório: contaminação e proveniência

Antes de qualquer modelo entrar em um experimento, criar um registro por artefato e por revisão imutável. A auditoria deve cobrir: modelo final, modelo-base, adapters/LoRA, datasets de treino, dados sintéticos e de preferência, corpora de pré-treinamento quando divulgados, prompt/few-shot examples, código remoto e dependências.

### 2.1 Classes de contaminação

| Classe | Evidência | Regra |
|---|---|---|
| C0 — sem sobreposição direta conhecida | Treino divulgado e sem fonte coincidente conhecida | Elegível apenas para as coortes efetivamente verificadas; corpora-base opacos permanecem como risco residual |
| C1 — treino direto no LLM-AggreFact | Dataset/split completo usado para treino, SFT, DPO, distilação ou ajuste | BLOQUEADO para as 11 coortes |
| C2 — treino em dataset-fonte de coorte | RAGTruth, CNN/DailyMail, XSum, TofuEval, WiCE etc. usado no treino | BLOQUEAR a coorte afetada; liberar outras somente após inventário completo |
| C3 — derivação/sintetização de fonte | Claims, documentos, pares, preferências ou rótulos sintéticos derivados de um dataset-fonte | Herdar a restrição da fonte; se IDs não estiverem disponíveis, manter bloqueio preventivo |
| C4 — avaliação publicada | Autores avaliaram o modelo no benchmark, sem treino conhecido nele | Não prova treino; registrar split e protocolo, sem apresentar o score do autor como medição AYORAI |
| C5 — exposição de desenvolvimento/calibração | Limiar, hiperparâmetros, seleção de modelo ou stacker ajustados com rótulos DEV/validation do LLM-AggreFact | O split exposto não é confirmação independente. Usar somente como desenvolvimento/exploratório; reservar split não exposto para confirmação |
| C6 — proveniência insuficiente/oculta | Fontes task-specific incompletas, “other datasets” não identificados ou corpora de treino não auditáveis | BLOQUEADO para confirmação nas coortes que possam sobrepor; não declarar “limpo” sem evidência |
| C7 — licença/código incompatível | Dataset NC, licença other, código remoto não revisado ou dependência incompatível | BLOQUEADO para uso comercial/execução até solução documental e aprovação |

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

| Modelo | Tamanho / licença dos pesos | Treino, licença dos dados e exposição | Referência pública | Decisão recomendada |
|---|---|---|---|---|
| mDeBERTa-v3-base NLI — `MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7` | ~0,3B; MIT | Fine-tune XNLI; dataset XNLI CC BY-NC 4.0. Sem sobreposição direta conhecida com as 11 coortes | Baseline interno histórico | **EVAL_ONLY.** Pode ser referência de pesquisa; não produto comercial |
| MiniCheck-DeBERTa-v3-Large — `lytang/MiniCheck-DeBERTa-v3-Large` | ~0,4B; MIT | 21K ANLI (CC BY-NC 4.0) + 14K sintéticos. C2D usa claims da Wikipedia com citações (cita WiCE); D2C usa Google News. Possível sobreposição em WiCE e fonte de notícias | 74,1 no paper FactCG sob protocolo/limiares dos autores; não é score AYORAI | **EVAL_ONLY.** Bloquear WiCE até deduplicação por IDs; investigar notícias; não produto |
| FactCG-DeBERTa-v3-Large — `yaxili96/FactCG-DeBERTa-v3-Large` | ~0,4B; MIT | Treino em ANLI subset (CC BY-NC), MiniCheck C2D/D2C, HotpotQA e Musique. C2D deriva de claims Wikipedia citadas; D2C de Google News. Paper ajusta limiar por dataset no validation do LLM-AggreFact | 77,2 no paper, com threshold tuning por dataset; não comparável a limiar fixo/OOF | **EVAL_ONLY e exposição C5.** Bloquear WiCE até deduplicação; resultados de DEV do paper são benchmark-exposed; não produto |
| MiniCheck-Flan-T5-Large — `lytang/MiniCheck-Flan-T5-Large` | ~0,8B; pesos MIT; base Flan-T5-Large Apache-2.0 | 21K ANLI (CC BY-NC) + 14K sintéticos; base FLAN-T5 foi instruído em CNN/DailyMail e XSum; C2D usa claims Wikipedia citadas (cita WiCE) e D2C Google News | 75,0 BAcc no leaderboard; score dos autores | **EVAL_ONLY.** Bloquear AggreFact-CNN e XSum; bloquear WiCE e REVEAL até deduplicação; investigar coortes de notícias. Não usar como full-11 nem em produto |
| MiniCheck-RoBERTa-Large — `lytang/MiniCheck-RoBERTa-Large` | ~0,4B; MIT | Base AlignScore; código de treino do AlignScore lista CNN/DailyMail, XSum e ANLI, além de outros datasets. Também usa dados sintéticos MiniCheck | 74,4 no paper FactCG; protocolo dos autores | **EVAL_ONLY.** Bloquear CNN/XSum e WiCE até deduplicação. A classificação comercial atual em MODEL-LICENSE-POLICY.md precisa ser revista |
| HHEM-2.1-Open — `vectara/hallucination_evaluation_model` | 109,6M; Apache-2.0; base Flan-T5-base | Treinado com RAGTruth train split e outros datasets confidenciais; base Flan-T5 também tem exposição a CNN/DailyMail e XSum. Usa trust_remote_code=True | Não há linha comparável no leaderboard atual; resultados Vectara antigos usam subsets/protocolos diferentes | **BLOQUEADO para confirmação** em RAGTruth, CNN e XSum; demais coortes não liberadas até disclosure dos outros datasets. Só throughput com dados sintéticos |
| cross-encoder NLI DistilRoBERTa — `cross-encoder/nli-distilroberta-base` | 82,1M; Apache-2.0 | Fine-tune SNLI + MultiNLI; sem sobreposição direta conhecida com as 11 coortes; base DistilRoBERTa | Sem score LLM-AggreFact publicado comparável; MNLI mismatched 83,98% na documentação Sentence Transformers | **PRIORIDADE CPU/PRODUTO.** Candidato independente e pequeno; pin SHA, validar licenças de SNLI/MultiNLI e executar piloto |
| HalluGuard-Qwen3-4B — `lrsbrgrn/HalluGuard-Qwen3-4B` | 4B; Apache-2.0; base Qwen3-4B Apache-2.0 | LoRA+ORPO em 76.708 preferências sintéticas derivadas de FineWeb. Não declara treino direto no benchmark; corpus-base Qwen3 mantém risco residual | Preprint 75,7%; ACL Findings 2026: 77,1% LLM-AggreFact e 84,4% RAGTruth, resultados dos autores | **PRIORIDADE POSTERIOR.** GPU/GGUF auditado, SHA, base e protocolo fixados |
| Granite Guardian 3.3 — `ibm-granite/granite-guardian-3.3-8b` | 8B; Apache-2.0 | HH-RLHF, anotações humanas e dados sintéticos internos; fontes completas do sintético não enumeradas. Inglês | 76,5 BAcc leaderboard; 76,5 think e 76,1 no-think | **CONDICIONAL.** Proveniência adicional antes de confirmação; GPU |
| Bespoke-MiniCheck-7B — `bespokelabs/Bespoke-MiniCheck-7B` | 7B/8B conforme card; CC BY-NC 4.0 | 21K ANLI + 14K sintéticos; autores dizem que fontes foram curadas independentemente do benchmark | 77,4 leaderboard; não é mais primeiro | **PESQUISA NÃO COMERCIAL.** Bloqueado para produto sem licença comercial |
| Paladin-mini — `qualifire/context-grounding-paladin-mini` | 3,8B; licença other; gated | Card lista explicitamente LLM-AggreFact entre datasets de treino | Score não elegível como avaliação limpa | **REMOVER.** Contaminação direta + licença sem clareza |
| LettuceDetect — `KRLabsOrg/lettucedect-large-modernbert-en-v1` | 395,8M; MIT; ModernBERT | Treinado no RAGTruth (dataset Apache-2.0); token classification, inglês | 79,22% F1 example-level RAGTruth, resultado dos autores | **CANDIDATO CPU por coorte.** Bloquear RAGTruth; outras 10 coortes após verificação. Exige agregação token→claim |


### 3.1 Interpretação por modelo

**Família MiniCheck.** O model card declara 21K exemplos ANLI + 14K sintéticos para MiniCheck-DBTA/FT5; ANLI é CC BY-NC 4.0, portanto os pesos MIT não tornam esses modelos comerciais. O paper MiniCheck informa que C2D parte de cerca de 400 claims da Wikipedia com documentos citados (citando Kamoi et al./WiCE) e D2C de cerca de 300 artigos Google News. A sobreposição com WiCE é, no mínimo, provável; bloquear WiCE até deduplicação por IDs. A exposição a fontes de notícias também exige auditoria.

**MiniCheck-Flan-T5-Large.** Além do treino ANLI/NC, o backbone google/flan-t5-large foi instruído em tarefas FLAN que incluem CNN/DailyMail e XSum, fontes diretas de duas coortes do benchmark. Portanto, bloquear AggreFact-CNN e AggreFact-XSum; bloquear WiCE e REVEAL até deduplicação de claims/fontes; não usar como modelo full-11. O resultado 75,0 é dos autores/leaderboard, não medição independente AYORAI. CPU é tecnicamente possível, mas throughput deve ser medido apenas nas coortes elegíveis. EVAL_ONLY para produto.

**HHEM-2.1-Open.** A aparente vantagem operacional — 109,6M parâmetros e latência inferior a 1,5 s em CPU Intel Xeon w7-3445 para premissa + hipótese com 2K tokens, segundo a Vectara — não elimina a contaminação. O artigo de 2025 afirma treino em RAGTruth train split e outros conjuntos confidenciais. A base Flan-T5 também tem exposição a CNN/DailyMail e XSum. Bloquear ao menos RAGTruth, AggreFact-CNN e AggreFact-XSum; os demais conjuntos permanecem não verificados. O model card exige `trust_remote_code=True`; revisão de código remoto e SHA pin são obrigatórios.

**HalluGuard.** O repositório oficial contém pesos Safetensors e declara Apache-2.0; o Qwen3-4B base também declara Apache-2.0. O paper final ACL Findings 2026 é a referência principal; 75,7% é o valor do preprint, substituído no artigo final por 77,1%. A quantização GGUF de mradermacher existe e declara Apache-2.0, com Q4_K_M em torno de 2,5 GB, mas é conversão de terceiro: verificar SHA, lineage, qualidade da quantização e equivalência do template de chat. Não assumir que quantização mantém o score dos autores.

**Granite Guardian 3.3.** A página oficial declara que deve ser usado no modo de scoring prescrito e que foi treinado/testado apenas em inglês. O modo think e no-think produz resultados diferentes; não misturar pontuações. A licença Apache-2.0 está declarada, mas a proveniência do dado sintético de treino não é suficientemente detalhada para certificar ausência de sobreposição com todas as coortes.

**Bespoke-MiniCheck-7B.** O card informa 21K exemplos ANLI e 14K sintéticos, com curadoria independente do benchmark. Porém a licença é explicitamente CC BY-NC 4.0; a página indica contato para licença comercial. O leaderboard atual já contém sistemas com médias superiores a 77,4. Manter apenas como referência acadêmica não comercial, isolada de qualquer produto ou pacote distribuído.

**Paladin-mini.** O card lista LLM-AggreFact como dataset usado no treinamento e a licença é `other`. Não há justificativa para mantê-lo como candidato limpo.

**LettuceDetect.** O artigo declara que foi treinado no RAGTruth, cujo dataset card declara Apache-2.0. Não pontuar no RAGTruth. Em outras coortes, converter tokens em spans/claims requer regra própria, com offsets do original e métrica de nível de instância compatível; não comparar F1 token-level com BA claim-level.

**FactCG.** O paper usa ANLI subset (CC BY-NC), MiniCheck C2D/D2C, HotpotQA e Musique. O C2D parte de claims Wikipedia citadas e o D2C de Google News; bloquear WiCE até deduplicação e investigar fontes de notícias. O paper ajusta limiar por dataset no validation do LLM-AggreFact, portanto seus scores publicados têm exposição C5 e não são comparação de limiar fixo/OOF.

**MiniCheck-RoBERTa/AlignScore.** O código de treinamento do AlignScore lista CNN/DailyMail, XSum e ANLI entre as fontes. Isso contradiz a classificação comercial atual de MiniCheck-RoBERTa em docs/legal/MODEL-LICENSE-POLICY.md; não confiar nela até revisão. A mesma política não inclui FactCG, que também usa ANLI; uma atualização separada deve corrigir o registro.

**cross-encoder/nli-distilroberta-base.** É um NLI genérico de 82,1M parâmetros, Apache-2.0, treinado em SNLI e MultiNLI. Não tem score LLM-AggreFact comparável, mas é pequeno, CPU-friendly e não tem sobreposição direta conhecida com as 11 coortes. É a alternativa mais limpa para um novo sinal CPU/produto; validar SHA, licença dos dados e comportamento claim-document.

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

RAIM estuda um painel de dez juízes open-weight de 4B–9B, de famílias distintas. Combina votos por regressão logística empilhada (stacking), treinada com rótulos e cross-fitting de cinco folds; compara com maioria simples, média, melhor membro e juiz frontier. Usa bootstrap pareado por clusters (2.000 reamostragens, IC 95%) e argumenta que o painel só agrega valor quando existem membros competentes com erros suficientemente descorrelacionados.

Os autores reportam 69,5 BAcc na média dos quatro conjuntos LLM-AggreFact incluídos na análise (WiCE, XSum, CNN e ExpertQA) e 73,0 na suíte de oito conjuntos; 50–100 rótulos são o orçamento de calibração explorado. Não é comparação direta com o leaderboard completo: os quatro conjuntos são subconjuntos do split de teste e o protocolo/seleção/denominadores diferem. **Contra o juiz frontier**, o painel melhora claramente em um benchmark, piora em três e deixa quatro sem resolução estatística. **Contra seu próprio melhor membro**, melhora nos quatro conjuntos grounded centrais, mas apenas um contraste é estatisticamente resolvido. São comparações diferentes. Aumentar a quantidade de modelos não garante ganho.

**Aplicação recomendada ao AYORAI:**
- calcular correlação de erros, dupla falha, desacordo e ganho incremental de cada modelo em predições OOF;
- comparar cada candidato com o melhor modelo individual, não apenas com a média dos membros;
- avaliar ablações por família: DeBERTa, T5/Flan-T5 e generativos;
- não adicionar modelo se apenas repetir os erros de um modelo existente;
- usar bootstrap pareado por unidade de origem/documento quando houver clusters, não bootstrap ingênuo de linhas independentes;
- qualquer stacking ajustado com rótulos do LLM-AggreFact depende da DEC-024; não copiar o código RAIM, pois os repositórios consultados declaram licença `other`/NOASSERTION.

## 7. Consequências para o ensemble CPU

Não existe, com a lista original, um painel confirmatório de cinco modelos elegíveis para as 11 coortes. O plano correto é separar modelos por coorte e por uso comercial.

### 7.1 Painel de pesquisa CPU

- Manter mDeBERTa, MiniCheck-DeBERTa e FactCG como referências históricas, com status de licença e exposição registrados; não chamá-los de modelos comerciais limpos.
- Adicionar cross-encoder/nli-distilroberta-base como candidato CPU prioritário: 82,1M, Apache-2.0, SNLI/MultiNLI, sem sobreposição direta conhecida com as 11 coortes.
- Adicionar LettuceDetect como sinal complementar nas 10 coortes fora de RAGTruth, depois de pré-registrar agregação token→claim.
- MiniCheck-Flan-T5-Large pode ser avaliado apenas nas coortes que sobreviverem à auditoria: excluir CNN/XSum e bloquear WiCE/REVEAL até deduplicação. É EVAL_ONLY por ANLI.
- FactCG e MiniCheck-DeBERTa devem bloquear WiCE até deduplicação e permanecer EVAL_ONLY por ANLI. mDeBERTa permanece EVAL_ONLY por XNLI.
- Não calcular uma única média macro comparando modelos em denominadores diferentes. Publicar BA por coorte e macro somente sobre a interseção comum de coortes elegíveis, explicitando a cobertura do benchmark.

### 7.2 Trilha de produto comercial

Priorizar checkpoints com pesos e dados permissivos, sem NC declarado e sem sobreposição direta conhecida:
- cross-encoder/nli-distilroberta-base (CPU; NLI genérico);
- LettuceDetect fora de RAGTruth (CPU; token-level; validar uso comercial e dados);
- HalluGuard-Qwen3-4B (GPU/quantizado; Apache-2.0; base Qwen3 auditada);
- Granite Guardian 3.3 somente após esclarecer a proveniência sintética.

mDeBERTa, MiniCheck (variantes ANLI), FactCG e Bespoke não devem ser promovidos como componentes comerciais sob a política atual; pesos MIT não removem restrições NC dos dados de treino.

### 7.3 HHEM: trilha isolada

- RAGTruth, AggreFact-CNN e AggreFact-XSum: bloqueados por treino direto/base FLAN.
- Outras coortes: não liberar para confirmação até a Vectara esclarecer os outros datasets de treino.
- Piloto de throughput: apenas dados sintéticos fora do benchmark, sem pontuação de acurácia.
- trust_remote_code=True: revisar código no SHA pinado antes de qualquer execução.

### 7.4 Regras de diversidade

Não presumir independência pelo número de checkpoints. O baseline tem três DeBERTa; MiniCheck-Flan e HHEM são T5/Flan-T5; DistilRoBERTa e LettuceDetect trazem arquiteturas/tarefas distintas. Para cada sinal, reportar correlação de scores/erros, dupla falha, ganho OOF marginal, estabilidade por coorte, custo, latência, memória, truncamento e comprimento.

O objetivo do ensemble é melhorar erros difíceis e generalização entre coortes, não aumentar o número de membros.

## 8. Plano operacional recomendado

A ordem que preserva o trabalho já feito e reduz retrabalho é:

1. **A1 — cache privado cifrado antes de qualquer nova inferência DEV.** O cache de predições não deve conter rótulos gold. Guardar scores e metadados de inferência; manter labels em artefato separado, com junção somente no avaliador autorizado. Incluir hash do input, model ID/SHA, tokenizer, configuração, score direction, status, runtime e checksum. Exigir idempotência, retomada, detecção de duplicatas e escrita atômica.
2. **A4 — auditoria agregada dos erros atuais.** Usar somente agregados e métricas de erro por coorte/comprimento/truncamento. Nenhum dado por instância em artefato público.
3. **E3 — somente depois da DEC-024.** Reutilizar cache; comparação OOF e sem acesso a DEV-B/TEST durante ajuste.
4. **Decisão de GPU/custo.** Só então apresentar alternativas e aguardar decisão do mantenedor.
5. **E4 — pilotos de throughput.** Depois de A1, rodar 200 casos DEV-A para cross-encoder/nli-distilroberta-base; testar LettuceDetect apenas em coortes fora de RAGTruth, com protocolo de agregação pré-registrado. MiniCheck-Flan-T5 pode ser testado apenas em coortes elegíveis após excluir CNN/XSum e resolver WiCE/REVEAL. HHEM usa somente dados sintéticos fora do benchmark para throughput. Registrar p50/p95, RAM/VRAM, tempo, timeouts, falhas, truncamento e consumo.
6. **DEV completo:** painel por coorte com elegibilidade individual. Não executar cinco modelos como um agregado homogêneo. Usar DistilRoBERTa como novo candidato geral; LettuceDetect em 10 coortes; MiniCheck/FactCG/mDeBERTa como comparadores de pesquisa sob suas restrições. Publicar macro apenas na interseção comum de coortes elegíveis e sempre declarar o denominador.
7. **E5, E5b, E6, E7 e E8:** experimentos independentes, cada um com pré-registro e autorização. E5b deve ser comparado diretamente com E5; E6 pode usar a ideia de estratégias de prova, sem código de terceiros e sem SFT/DPO no benchmark.
8. **C — TEST único:** congelar configuração e hashes; executar uma única vez somente após aprovação explícita.

**Urgência operacional:** a PR #488 continua sendo dependência separada para a Emenda 2 do LTT e retenção de sete dias. Não tratar a proposta como regra vigente até merge. A re-agregação indicada pelo mantenedor deve ocorrer dentro da janela operacional declarada (até 2026-11-08 13:00 BRT), mas este radar não autoriza merge da #488 nem dispatch. A autorização específica é necessária antes dessas ações.

## 9. Outras frentes para excelência e robustez

Estas frentes são oportunidades de pesquisa para versões futuras. Não alteram a ordem A1 → A4 → E3 → decisão de GPU → E4 → E5–E8 → C, não autorizam implementação e exigem pré-registro/decisão próprios.

### 9.1 Testes de invariância e adversariais

Criar uma suíte sintética independente do LLM-AggreFact para medir se os verificadores respondem ao conteúdo relevante, e não a artefatos de apresentação:
- inversão controlada de negação, números, datas, unidades, nomes, quantificadores e modalidade;
- troca de entidade/sujeito/objeto mantendo o restante;
- mudança da ordem dos parágrafos, sentenças e documentos;
- adição de contexto irrelevante, duplicado, contraditório ou desatualizado;
- truncamento em início/meio/fim, fronteira de chunk e antecedente de pronome;
- paráfrase que preserva sentido versus paráfrase que muda uma relação factual;
- texto de prompt injection dentro do documento-fonte, explicitamente tratado como dado não confiável e nunca como instrução ao verificador;
- respostas em português brasileiro, inglês e mistura de idiomas, com métricas separadas.

Critérios esperados: alterações irrelevantes não devem causar mudança material; uma contradição factual controlada deve alterar o score na direção prevista; falhas de parsing/ambiguidade devem ser registradas, nunca convertidas silenciosamente em rótulo favorável. Não misturar esta suíte com DEV/TEST do LLM-AggreFact.

### 9.2 Qualidade da trilha de evidência

A acurácia binária não basta para um sistema de auditoria. Em amostra anotada independentemente, avaliar se cada afirmação aponta para o trecho exato e suficiente da fonte:
- precisão e cobertura de spans;
- offsets corretos no texto original após chunking, correferência ou normalização;
- citações literais sem reescrita;
- separação entre “contradito”, “não localizado/não sustentado” e “fonte insuficiente”;
- preservação de negação, números, datas, unidades, sujeitos, objetos e relações;
- taxa de alegações sem span, span errado e span apenas parcialmente sustentador.

Quando o benchmark não tiver gold de span, declarar avaliação qualitativa ou anotação humana de amostra; não fabricar uma métrica automática de localização.

### 9.3 Robustez operacional e cadeia de suprimentos

Antes de considerar qualquer verificador para produto:
- gerar SBOM e fixar versões de runtime, tokenizer, bibliotecas, código remoto e quantização;
- executar revisão de segurança em `trust_remote_code` e pin de commit SHA;
- testar offline/reprodutibilidade, timeout, OOM, corrupção de cache, saída malformada e falha parcial;
- medir latência p50/p95/p99, throughput, RAM/VRAM, energia/custo por mil claims e custo de manutenção;
- verificar licença do modelo, base, datasets, adapters, tokenizer, código e conversão quantizada;
- definir fallback determinístico e registrar falhas como indisponibilidade/abstenção, nunca como sustentação.

### 9.4 Validação humana e qualidade dos rótulos

Para auditorias de erro, usar amostra estratificada por coorte, classe, comprimento e discordância entre modelos; anotadores cegos à previsão do sistema; segunda anotação independente e adjudicação de divergências. O objetivo é caracterizar erros e possíveis ambiguidades, não alterar retroativamente os rótulos oficiais do benchmark nem treinar modelos com LLM-AggreFact.

### 9.5 Generalização e mudança de distribuição

Além da média macro, estudar leave-one-cohort-out como diagnóstico de transferência, sem usar a coorte retida para seleção. Reportar calibração e desempenho por coorte, comprimento, tipo de tarefa e idioma. Mudança de distribuição deve gerar sinal de incerteza/abstenção ou necessidade de revisão, não uma alegação de validade universal.

## 10. Controles estatísticos adicionais recomendados

- Reportar BA por coorte e macro média; também sensibilidade, especificidade, precisão, F1, MCC, ECE/Brier quando aplicável. Não selecionar pela métrica secundária.
- Usar intervalos de confiança pareados e bootstrap por cluster/documento quando houver dependência entre exemplos. Informar unidade de reamostragem, número de replicações e seed.
- Corrigir multiplicidade quando várias configurações/modelos forem comparados; pré-registrar a família de hipóteses. Distinguir diferença estatística de diferença prática.
- Mostrar resultados absolutos e diferenças pareadas contra o baseline, com intervalo. Não usar sobreposição de intervalos marginais como substituto de teste pareado.
- Separar métricas de classificação de métricas seletivas. A meta de 90% entre aceitas não é piso global nem garantia estatística por si só; certificação depende do teste LTT, nível de erro e correção por múltiplas coortes definidos no protocolo vigente.
- Não permitir que DEV-B retroalimente a escolha; não tocar TEST até congelamento.
- Se houver ruído de rótulo, investigar por amostragem humana independente e protocolo cego; não supor percentual de ruído nem descontá-lo aritmeticamente do score.

## 11. Decisões recomendadas ao mantenedor

1. Priorizar cross-encoder/nli-distilroberta-base como candidato CPU comercial, sujeito a pin e piloto.
2. Avaliar LettuceDetect em coortes não-RAGTruth, com agregação token→claim.
3. Não usar MiniCheck-Flan-T5 como full-11 nem produto; bloquear CNN/XSum e WiCE/REVEAL até deduplicação; ANLI torna-o EVAL_ONLY.
4. Não promover MiniCheck-DeBERTa, FactCG ou mDeBERTa a produto; ANLI/XNLI os deixam EVAL_ONLY. Auditar a exposição por coorte e a calibração prévia de FactCG.
5. Não incluir HHEM no agregado confirmatório enquanto a proveniência adicional não for divulgada; RAGTruth/CNN/XSum inelegíveis.
6. Manter HalluGuard para rodada posterior, com revisão SHA e orçamento GPU/quantização.
7. Manter Granite como candidato condicional, bloqueado até esclarecimento da proveniência dos dados sintéticos.
8. Excluir Paladin-mini; restringir Bespoke-MiniCheck a pesquisa não comercial.
9. Corrigir em PR separada docs/legal/MODEL-LICENSE-POLICY.md: reavaliar MiniCheck-RoBERTa à luz do AlignScore base (ANLI/CNN/XSum) e adicionar FactCG (ANLI); não alterar essa política nesta PR.
10. Adotar análise de correlação/dupla falha e bootstrap pareado por cluster como exigências do relatório E3/E4; stacking com rótulos bloqueado até DEC-024.
11. Não alterar Judge 2.0, Golden, hashes, thresholds do sistema, RGC, Piloto 02 ou ResponsePolicy.

## 12. Fontes oficiais e primárias consultadas

**Data de verificação: 2026-11-07.** Os links abaixo são a base de evidência desta versão; revalidar antes de fixar revisões ou executar.

### Benchmark e MiniCheck
- [LLM-AggreFact Leaderboard](https://llm-aggrefact.github.io/) — 11 conjuntos e tabela atual de modelos/BA.
- [MiniCheck paper, arXiv:2404.10774](https://arxiv.org/abs/2404.10774) — dados sintéticos, 770M e benchmark.
- [MiniCheck-Flan-T5-Large model card](https://huggingface.co/lytang/MiniCheck-Flan-T5-Large) — MIT e arquitetura T5.
- [Bespoke-MiniCheck-7B model card](https://huggingface.co/bespokelabs/Bespoke-MiniCheck-7B) — treino, alegação de fontes independentes e licença CC BY-NC 4.0.

- [ANLI dataset card](https://huggingface.co/datasets/facebook/anli) — licença CC BY-NC 4.0.
- [FLAN-T5-Large model card](https://huggingface.co/google/flan-t5-large) e [FLAN task registry](https://github.com/google-research/FLAN/blob/main/flan/tasks.py) — base instruída com tarefas que incluem CNN/DailyMail e XSum.
- [MiniCheck Appendix D](https://aclanthology.org/2024.emnlp-main.499.pdf) — C2D com ~400 claims Wikipedia citadas (refs. Kamoi/WiCE) e D2C com ~300 artigos Google News.
- [FactCG paper](https://arxiv.org/abs/2501.17144) — ANLI subset, MiniCheck C2D/D2C, HotpotQA/Musique e threshold tuning por dataset no validation do LLM-AggreFact.
- [AlignScore training data script](https://github.com/yuh-zha/AlignScore/blob/main/generate_training_data.py) — inclui CNN/DailyMail, XSum e ANLI; relevante para o backbone MiniCheck-RoBERTa.
- [cross-encoder/nli-distilroberta-base](https://huggingface.co/cross-encoder/nli-distilroberta-base) — 82,1M, Apache-2.0, treino SNLI/MultiNLI.
- [RAGTruth dataset card](https://huggingface.co/datasets/leobianco/ragtruth) — Apache-2.0.

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
