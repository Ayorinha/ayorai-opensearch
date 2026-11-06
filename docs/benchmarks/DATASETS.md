# Datasets internacionais — licenças, proveniência e mapeamento

**Estado:** documentação pré-execução.  
**Revisão das fontes:** 2026-11-06.  
**Execução do ATTRACTOR sobre estes conjuntos:** NÃO REALIZADA.

Este documento registra as condições de uso e o mapeamento metodológico antes de qualquer execução. A Frente B é uma ferramenta técnica interna de medição; o benchmark brasileiro continua sendo o benchmark principal do projeto. Este registro não autoriza treinamento, fine-tuning, redistribuição de dados nem publicação de resultados.

## Regras gerais

1. **Avaliação, não treinamento.** Nesta frente, os conjuntos são usados somente para avaliar o motor atual. Não usar seus dados para pretraining, fine-tuning, ajuste de pesos, criação de exemplos de treinamento ou calibração de modelos.
2. **Sem redistribuição de dados.** Não versionar neste repositório arquivos brutos, amostras textuais, documentos, respostas, anotações, subconjuntos derivados ou caches que contenham conteúdo dos datasets. A licença do repositório que hospeda código ou metadados não substitui os direitos sobre textos de terceiros.
3. **Sem envio externo de conteúdo.** Não enviar documentos, perguntas, respostas ou trechos dos datasets a APIs de modelos externos. A avaliação deve ocorrer no ambiente local, salvo autorização específica posterior.
4. **Revisões imutáveis.** Antes de qualquer execução, registrar o commit/revision exato de cada fonte, data de obtenção, arquivos, tamanho, SHA-256, splits, contagens, esquema, transformações e termos aceitos. Não usar `main` como identificador de versão de uma execução.
5. **Sem equivalências artificiais.** Preservar os rótulos nativos. Os cinco vereditos do ATTRACTOR não mudam. Só calcular métricas comparáveis quando a unidade, a tarefa e a semântica dos rótulos forem suficientemente equivalentes.
6. **Sem agregação automática.** Reportar cada dataset e tarefa separadamente. Não somar amostras nem produzir uma média geral entre conjuntos com unidades, fontes ou critérios diferentes.
7. **Sem execução antes do gate.** O mapeamento abaixo, as revisões de licença, a fixação de versões e a auditoria de sobreposição devem estar registrados antes da primeira execução.

## Inventário dos conjuntos selecionados

| Conjunto | Papel nesta frente | Fonte e formato | Licença / acesso | Restrição operacional |
|---|---|---|---|---|
| **LLM-AggreFact** | Principal | [Hugging Face: lytang/LLM-AggreFact](https://huggingface.co/datasets/lytang/LLM-AggreFact). Inglês; splits `dev` e `test`; campos `dataset`, `doc`, `claim`, `label`, `contamination_identifier`. A página informa 30.420 linhas em dev e 29.320 em test. | Metadado do Hub: **CC-BY-ND-4.0**. Repositório **gated**: é necessário solicitar/aceitar o acesso e as condições apresentadas pelo mantenedor. | Permitido como benchmark de avaliação. O aviso de acesso proíbe usar os dados em pretraining ou fine-tuning de modelos NLP. Não publicar subconjuntos transformados ou derivados sem verificar a restrição NoDerivatives e os direitos das fontes subjacentes. |
| **RAGTruth** | Secundário, sempre separado do principal | [GitHub: ParticleMedia/RAGTruth](https://github.com/ParticleMedia/RAGTruth). Corpus em JSONL: `response.jsonl` e `source_info.jsonl`, ligados por `source_id`. O README informa 17.790 respostas, 2.965 instâncias de origem e 14.289 spans anotados. | O arquivo LICENSE do repositório declara **MIT** para o conteúdo coberto pelo repositório. Isso **não** concede automaticamente direitos sobre textos de notícias, documentos ou corpora subjacentes. | Uso secundário apenas para avaliação e com as restrições não comerciais dos corpora subjacentes quando aplicáveis. Não redistribuir respostas, fontes ou derivados. A sobreposição com LLM-AggreFact e HaluBench precisa ser tratada explicitamente (ver seção própria). |
| **HaluBench** | Pesquisa exploratória isolada; nunca agregado aos dois anteriores | [Hugging Face: PatronusAI/HaluBench](https://huggingface.co/datasets/PatronusAI/HaluBench). Inglês; um split `test`, com 14.900 linhas; campos `id`, `passage`, `question`, `answer`, `label`, `source_ds`. | Metadado do Hub: **CC-BY-NC-2.0**. | **Somente pesquisa não comercial**, com atribuição. Não usar em produto, serviço ou atividade comercial; não treinar modelos; não redistribuir dados ou derivados. Se o uso futuro for comercial, excluir este conjunto até obter autorização/licença compatível. As licenças das fontes incorporadas também precisam ser respeitadas. |

### 1. LLM-AggreFact — proveniência e condições

A ficha do conjunto agrega 11 fontes: **AggreFact-CNN, AggreFact-XSum, TofuEval-MediaSum, TofuEval-MeetingBank, WiCE, REVEAL, ClaimVerify, FactCheck-GPT, ExpertQA, LFQA e RAGTruth**. Os documentos incluem textos de fontes variadas (por exemplo, Wikipedia, entrevistas e conteúdo da web); as afirmações são, em sua maioria, geradas por modelos, com exceção de um conjunto de afirmações humanas.

A ficha declara que o campo `label` vale **1 quando a afirmação é supported** e **0 caso contrário**. Também informa que o RAGTruth foi incorporado em uma atualização de 08/09/2024: seus dados foram convertidos ao formato comum, afirmações consideradas não verificáveis/checkworthy foram removidas, e uma amostra aleatória do split de treino do RAGTruth foi incluída na validação do benchmark.

**Limite de proveniência/licença:** a ficha do agregado informa CC-BY-ND-4.0, mas não fornece uma matriz completa de licenças para cada uma das 11 fontes subjacentes. A licença do agregado não deve ser interpretada como uma relicença irrestrita de artigos, documentos ou corpora de terceiros. Acesso gated e uso exclusivamente para avaliação devem ser mantidos. Registrar a revisão exata do Hub e os termos exibidos no momento do acesso.

**Inconsistência de metadados:** a descrição do campo `dataset` menciona “10 datasets”, enquanto a lista nominal da própria ficha contém 11 fontes. Preservar os valores originais e registrar essa divergência; não corrigir a contagem por suposição.

### 2. RAGTruth — proveniência e condições

O README oficial descreve três tarefas: QA, sumarização e data-to-text. O arquivo de respostas contém spans com `text`, `start`, `end` e `label_type`, além de atributos como `due_to_null`, `implicit_true` e `meta`. O campo `quality` registra problemas como `incorrect_refusal` e `truncated`; esses indicadores de qualidade não são, por si, vereditos de factualidade.

O README identifica fontes subjacentes como **MARCO**, **Yelp**, **CNN/DM** e **Recent News**. As condições relevantes incluem:

- **MS MARCO:** os termos oficiais limitam o uso a pesquisa não comercial e dizem expressamente que a disponibilização não concede licença ou direitos de propriedade intelectual sobre os documentos subjacentes. [Termos oficiais](https://microsoft.github.io/msmarco/Notice.html).
- **Yelp Open Dataset:** o acordo de dados limita o uso a fins acadêmicos ou não comerciais e estabelece restrições de redistribuição, sublicenciamento e uso em nome de terceiros. [Yelp Dataset Terms of Use](https://s3-media3.fl.yelpcdn.com/assets/srv0/engineering_pages/bea5c1e92bf3/assets/vendor/yelp-dataset-agreement.pdf).
- **CNN/DailyMail:** a cópia do dataset disponível no Hub exibe metadado Apache-2.0, mas isso não comprova que os direitos autorais dos artigos de CNN e Daily Mail tenham sido transferidos ou liberados para redistribuição. Não redistribuir o texto jornalístico com base apenas na licença do repositório espelho.
- **Recent News:** o README do RAGTruth não identifica de forma suficiente os veículos, URLs, datas de captura ou termos aplicáveis. Proveniência e direitos permanecem **não esclarecidos** até auditoria do registro de origem.

Por conter material derivado de fontes com restrições não comerciais e material cujo titular/licença não está suficientemente identificado, tratar o RAGTruth como **não comercial para esta frente** e não redistribuir seus dados. O MIT do repositório não elimina as restrições das fontes originais.

### 3. HaluBench — proveniência e condições

A ficha oficial informa que os exemplos foram reunidos a partir de **FinanceBench, PubMedQA, CovidQA, HaluEval, DROP e RAGTruth**. A licença agregada indicada no Hub é CC-BY-NC-2.0. A ficha não apresenta uma matriz completa de direitos por fonte nem detalha a licença de cada documento subjacente; portanto, a licença agregada não substitui a verificação das fontes.

| Fonte subjacente indicada pela ficha | Licença/condição identificada | Ressalva |
|---|---|---|
| FinanceBench | O Hub de [PatronusAI/financebench](https://huggingface.co/datasets/PatronusAI/financebench) informa **CC-BY-NC-4.0**. | O conjunto completo inclui documentos financeiros vinculados; a amostra aberta e os documentos referenciados não devem ser tratados como uma licença irrestrita sobre todos os documentos corporativos. |
| PubMedQA | O [repositório oficial](https://github.com/pubmedqa/pubmedqa) contém licença **MIT**. | A licença do repositório/código não resolve automaticamente os direitos de cada abstract publicado no PubMed; manter a proveniência dos artigos e não redistribuir abstracts sem base própria. |
| CovidQA | A ficha do HaluBench não fixa um identificador ou revision inequívoco para esta fonte. O repositório [deepset-ai/COVID-QA](https://github.com/deepset-ai/COVID-QA) declara Apache-2.0. | Não presumir que esse repositório é necessariamente a versão incorporada pelo HaluBench. O corpus associado a artigos científicos pode ter direitos e termos próprios. Confirmar a origem exata antes do uso. |
| HaluEval | O [repositório oficial RUCAIBox/HaluEval](https://github.com/RUCAIBox/HaluEval) declara **MIT**. | Preservar citação e versão; verificar a proveniência de materiais de terceiros incorporados. |
| DROP | A [página original do dataset mantida pela Ai2](https://github.com/allenai/allennlp-website/blob/master/drop.html) informa **CC-BY-SA-4.0**. O [AWS Open Data Registry](https://registry.opendata.aws/allenai-drop/) exibe a indicação mais genérica CC BY. | Há diferença entre as indicações públicas. Adotar provisoriamente a condição mais restritiva **CC-BY-SA-4.0** até resolver a divergência com a fonte oficial. |
| RAGTruth | Repositório **MIT**, com restrições adicionais das fontes subjacentes descritas na seção anterior. | A licença MIT não elimina as condições do MS MARCO, Yelp, textos jornalísticos ou fontes não identificadas. |

HaluBench possui apenas o split `test` na ficha consultada. Não há split de desenvolvimento documentado ali. Portanto, não selecionar modelos, limiares, prompts ou variantes com base em resultados repetidos desse conjunto. Usá-lo somente após congelar a configuração, como avaliação externa isolada; se for reutilizado para comparar variantes, classificar os resultados como **EXPLORATÓRIOS**, nunca como confirmação independente.

## Registro de versões e hashes — estado pré-download

Este quadro é parte do gate. **Nenhum arquivo de dados foi baixado nesta PR**, conforme o escopo. Por isso, SHA-256 de conteúdo ainda não existe e não pode ser declarado sem calcular o hash dos bytes efetivamente obtidos. Não substituir esse valor por hash do commit, hash Git de blob, ETag ou checksum publicado de outro arquivo: são identificadores diferentes.

| Conjunto / arquivo que poderá ser usado | Fonte/revisão identificada em 2026-11-06 | Estado da versão para uso | SHA-256 do arquivo |
|---|---|---|---|
| LLM-AggreFact — arquivos de dados dos splits `dev` e `test` (Parquet; nomes exatos a confirmar na listagem da revisão aprovada) | [Repositório oficial gated](https://huggingface.co/datasets/lytang/LLM-AggreFact); ficha consultada informa atualização em 20/12/2024. A revisão completa do Hub não foi confirmada nesta etapa. | **PENDENTE**: solicitar/aceitar acesso, obter o SHA completo da revisão aprovada e registrar os caminhos exatos dos shards antes de baixar. Não usar `main` como pin. | **PENDENTE — não calculado; download proibido nesta PR.** |
| RAGTruth — `dataset/response.jsonl` | [ParticleMedia/RAGTruth](https://github.com/ParticleMedia/RAGTruth), commit `c103204b9ce28d6bbad859304bf30de72b8ed8fe` (02/12/2024), usado como revisão documental candidata. | **CANDIDATA, não congelada**: confirmar que os arquivos e a licença correspondem à revisão selecionada; revisar fontes subjacentes e termos antes de obter dados. | **PENDENTE — não calculado; download proibido nesta PR.** |
| RAGTruth — `dataset/source_info.jsonl` | Mesma revisão candidata do repositório RAGTruth: `c103204b9ce28d6bbad859304bf30de72b8ed8fe`. | **CANDIDATA, não congelada**. | **PENDENTE — não calculado; download proibido nesta PR.** |
| HaluBench — arquivos do split `test` (Parquet; nomes exatos a confirmar na revisão aprovada) | [PatronusAI/HaluBench](https://huggingface.co/datasets/PatronusAI/HaluBench); histórico público consultado mostra o commit mais recente `5966a87` (11/07/2024), abreviado pela interface. | **PENDENTE**: resolver e registrar o SHA completo do commit antes de qualquer obtenção; confirmar arquivos e licença vigente. Uso isolado e não comercial. | **PENDENTE — não calculado; download proibido nesta PR.** |

### Revisões das fontes subjacentes de HaluBench

Os commits abaixo identificam repositórios públicos consultados para verificar proveniência/licenças; **não provam** que HaluBench incorporou exatamente esses commits. O mapeamento de versão entre HaluBench e cada fonte continua pendente de confirmação pelo mantenedor ou por metadados de origem.

| Fonte | Revisão documental consultada | Limite |
|---|---|---|
| FinanceBench | [PatronusAI/financebench](https://huggingface.co/datasets/PatronusAI/financebench); ficha atualizada em 17/11/2024. | Revisão completa e associação exata com os registros de HaluBench não confirmadas. |
| PubMedQA | [pubmedqa/pubmedqa](https://github.com/pubmedqa/pubmedqa), commit `1cbae8e92f72f20c8d3747cbb3bf5bc53554d997` (18/04/2023). | Revisão documental do repositório; artigos/abstracts mantêm direitos próprios. |
| COVID-QA | [deepset-ai/COVID-QA](https://github.com/deepset-ai/COVID-QA), commit `fb2eb5e249618457e5359806601086c635c8eb8f` (22/06/2020). | Não confirmado como a versão incorporada pelo HaluBench. |
| HaluEval | [RUCAIBox/HaluEval](https://github.com/RUCAIBox/HaluEval), commit `b7253db3cdaa0ab2c382f92b26b390109174f77e` (12/02/2024). | Não confirmado como a versão incorporada pelo HaluBench. |
| DROP | Página de licença e ficha pública consultadas; revisão completa dos dados não fixada nesta etapa. | Resolver divergência de licença e versão antes de qualquer uso. |
| RAGTruth | [ParticleMedia/RAGTruth](https://github.com/ParticleMedia/RAGTruth), commit documental candidato `c103204b9ce28d6bbad859304bf30de72b8ed8fe`. | Não confirmado como a versão incorporada pelo HaluBench. |

**Critério para fechar este quadro:** após autorização separada para obtenção dos dados, resolver o SHA completo de cada repositório, baixar somente os arquivos selecionados, calcular SHA-256 localmente sobre cada arquivo sem transformação, registrar tamanho em bytes e então congelar o manifesto. Qualquer alteração de arquivo ou revisão exige novo hash e novo registro. Até lá, os três conjuntos permanecem **não executados** e os hashes ficam explicitamente pendentes, sem valores inventados.

## Sobreposição entre conjuntos

A sobreposição é conhecida no nível de proveniência:

1. **LLM-AggreFact contém RAGTruth** como uma de suas fontes. A atualização de 08/09/2024 declara que o corpus foi convertido e que uma amostra aleatória do treino do RAGTruth foi incorporada à validação do LLM-AggreFact.
2. **HaluBench também incorpora RAGTruth** entre suas fontes.
3. Portanto, LLM-AggreFact, RAGTruth e HaluBench **não são três amostras independentes**. Não agregar seus resultados como se fossem observações independentes nem somar seus denominadores.

A documentação pública consultada não demonstra uma chave de origem comum preservada em todos os três esquemas. Antes de qualquer execução, a auditoria local deve:

- preservar IDs originais e os campos `dataset` (LLM-AggreFact) e `source_ds` (HaluBench);
- comparar registros de origem por identificadores disponíveis e, quando necessário, por fingerprint determinístico dos campos de contexto/documento + pergunta/claim + resposta;
- registrar método de normalização, hashes, correspondências exatas, correspondências prováveis e casos não resolvidos;
- manter os resultados por dataset e por coorte, excluindo duplicatas da comparação independente quando a correspondência for comprovada;
- se a sobreposição exata não puder ser quantificada, declarar a dependência e não apresentar o conjunto como replicação independente.

## Mapeamento prévio dos rótulos para os cinco vereditos

Os vereditos do ATTRACTOR permanecem **SUPPORTED, PARTIALLY_SUPPORTED, UNVERIFIED, REFUTED e CONFLICTING**. O mapeamento abaixo não altera o Judge nem cria rótulos sintéticos.

| Dataset / rótulo nativo | Significado documentado | Mapeamento permitido | Classe ausente ou limite |
|---|---|---|---|
| LLM-AggreFact `1` | Afirmação supported pelo documento. | **Equivalência direta com SUPPORTED**, limitada à tarefa binária claim-document do dataset. | Não informa intensidade, parcialidade ou conflito. |
| LLM-AggreFact `0` | Afirmação não supported; a ficha não discrimina a causa. | **Não mapeável com segurança** para um único veredito negativo. Manter como classe binária nativa “not supported”. | Pode reunir casos que exigiriam PARTIALLY_SUPPORTED, UNVERIFIED, REFUTED ou CONFLICTING; não converter automaticamente para REFUTED ou UNVERIFIED. |
| RAGTruth: span de alucinação anotado | Trecho da resposta marcado por anotadores; preservar `label_type`, `start`, `end`, `due_to_null` e `meta`. | Usar a anotação nativa de span e, se necessário, uma métrica binária derivada de presença de span, identificada como derivada. | Unidade é span/resposta, não claim individual; não há equivalência direta com um dos cinco vereditos. |
| RAGTruth: `implicit_true` | Informação verdadeira, mas não mencionada no contexto. | Não contar como span de alucinação. | Não equivale automaticamente a SUPPORTED: a informação não está sustentada pelo contexto fornecido. |
| RAGTruth: ausência de span de alucinação | Nenhum span de alucinação foi anotado. | Manter como “sem alucinação anotada” na métrica nativa. | Não converter automaticamente para SUPPORTED. |
| HaluBench `PASS` | Resposta fiel ao documento/contexto. | **Equivalência parcial com SUPPORTED**, no nível da resposta inteira e da tarefa de faithfulness. | Não garante que cada claim possa ser classificado individualmente; manter também a métrica binária nativa. |
| HaluBench `FAIL` | Resposta não fiel / com alucinação em relação ao contexto. | Manter como classe binária nativa “hallucination / not faithful”. | **Não mapeável com segurança** a um único veredito negativo; não distinguir REFUTED, UNVERIFIED, PARTIALLY_SUPPORTED ou CONFLICTING sem anotação própria. |

Nenhum dos três conjuntos representa de forma separada e suficiente as cinco classes do ATTRACTOR. Em particular, **PARTIALLY_SUPPORTED, UNVERIFIED, REFUTED e CONFLICTING não podem ser artificialmente preenchidos** a partir de uma única classe negativa binária. Reportar métricas nativas e, somente onde houver equivalência metodológica suficiente, métricas comparáveis explicitamente identificadas.

## Gate de reprodutibilidade antes da primeira execução

Para cada dataset e revisão efetivamente usada, registrar em manifesto fora do repositório público:

- URL oficial, identificador do dataset, commit/revision imutável e data de acesso;
- licença exibida, termos aceitos, restrições não comerciais e revisão das licenças subjacentes;
- nomes e hashes SHA-256 dos arquivos efetivamente usados;
- split, contagem de linhas, esquema e unidade estatística;
- fontes subjacentes e resultado da auditoria de sobreposição;
- mapeamento de rótulos aplicado, versão deste documento e justificativa;
- exclusões, transformações, tratamento de spans e dados ausentes;
- configuração congelada do motor atual, seed e parâmetros da execução.

A primeira medição deve usar o **RuleStanceDetector atual, sem ajuste**. Dev/test devem permanecer separados: iterações e escolhas somente em dev; test somente para avaliação confirmatória. Para HaluBench, que só apresenta test na ficha consultada, não realizar seleção ou ajuste nesse conjunto. Resultados negativos e falhas devem ser mantidos e reportados, nunca descartados silenciosamente.

## Fontes oficiais consultadas

- [LLM-AggreFact — ficha e licença no Hugging Face](https://huggingface.co/datasets/lytang/LLM-AggreFact)
- [MiniCheck: Efficient Fact-Checking of LLMs on Grounding Documents](https://arxiv.org/abs/2404.10774)
- [RAGTruth — repositório, README e LICENSE](https://github.com/ParticleMedia/RAGTruth)
- [RAGTruth — artigo na ACL Anthology](https://aclanthology.org/2024.acl-long.585/)
- [MS MARCO — termos oficiais](https://microsoft.github.io/msmarco/Notice.html)
- [Yelp — Dataset Terms of Use](https://s3-media3.fl.yelpcdn.com/assets/srv0/engineering_pages/bea5c1e92bf3/assets/vendor/yelp-dataset-agreement.pdf)
- [HaluBench — ficha e licença no Hugging Face](https://huggingface.co/datasets/PatronusAI/HaluBench)
- [Lynx — prompt e definição de PASS/FAIL](https://huggingface.co/PatronusAI/Llama-3-Patronus-Lynx-8B-Instruct)
- [FinanceBench — ficha e licença no Hugging Face](https://huggingface.co/datasets/PatronusAI/financebench)
- [PubMedQA — repositório oficial](https://github.com/pubmedqa/pubmedqa)
- [COVID-QA — repositório deepset](https://github.com/deepset-ai/COVID-QA)
- [HaluEval — repositório oficial](https://github.com/RUCAIBox/HaluEval)
- [DROP — página original do dataset com CC-BY-SA-4.0](https://github.com/allenai/allennlp-website/blob/master/drop.html) e [AWS Open Data Registry](https://registry.opendata.aws/allenai-drop/)

**Estado final deste registro:** proveniência e restrições documentadas para planejamento; revisão de versões imutáveis, hashes e sobreposição por instância permanece pendente antes de qualquer execução. Nenhum dataset foi executado nesta etapa.
