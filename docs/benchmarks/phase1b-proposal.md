# Fase 1b — proposta de execução distribuída e avaliação

**Estado:** proposta em revisão (Draft). Nenhum workflow foi disparado; nenhum dataset ou modelo foi executado nesta fase.  
**Base:** `main` em `91977dc9494ae9507e8bdda3791ceba965b9fd6e`.  
**Objetivo:** tornar viável a avaliação internacional em shards, mantendo a comparabilidade com pesos originais FP32 e impedindo que qualquer anotação/saída por instância chegue a artefatos públicos.

## 1. Evidência de throughput preservada

O arquivo `baseline-throughput-pilot-aggregate.json` foi copiado do artefato do run `42288837777`, sem reserialização ou edição. SHA-256 do arquivo recuperado: `6eb18990fa652c3d521e627d593fc001bc71a552ec49bb9b0f522f5fd834c151`.

| Modelo | s/exemplo | RAM de pico |
|---|---:|---:|
| mDeBERTa | 1,8896 | 2,40 GB |
| MiniCheck | 4,2812 | 3,40 GB |
| FactCG | 4,3036 | 3,79 GB |
| HHEM | SKIPPED | — |

O relatório de throughput é DEV, 200 exemplos, 30.420 linhas; nele, RAGTruth tem 15.340 linhas. Separadamente, o relatório agregado do benchmark de 06/11 registra **contagens medidas do TEST**: 29.320 exemplos, dos quais 16.371 em RAGTruth. Esses números não são projeções nem extrapolações do DEV.

## 2. Particionamento determinístico

1. Validar um identificador estável e único por exemplo. Não usar índice incidental do DataFrame. Se o dataset não trouxer ID estável, criar um identificador determinístico a partir da identidade imutável da linha no arquivo pinado, documentando algoritmo e versão.
2. Ordenar todos os IDs em ordem lexicográfica estável e particionar em blocos consecutivos de **1.000 exemplos** (último shard menor). O manifesto registra apenas `shard_id`, intervalo/contagem, IDs ou seus digests, split, dataset revision/hash e code SHA; não contém texto, claims, notas nem rótulos.
3. Coorte não define o shard. A matriz é global e balanceia o trabalho; cada shard mantém a distribuição natural de coortes. Isso evita a cauda longa concentrada em RAGTruth.
4. Dentro de cada shard, calcular comprimento com o tokenizer pinado, ordenar por comprimento crescente e desempatar pelo ID. Formar batches após essa ordenação. Reassociar scores e predições ao ID original antes da agregação.
5. A ordenação por comprimento é uma otimização de execução, não uma transformação do conjunto. O A/B será executado uma única vez, em job próprio, com um único shard pequeno de 200 exemplos e um único modelo. Comparará ordem determinística por ID com ordenação por comprimento no mesmo subconjunto; verificará equivalência de scores/vereditos dentro de tolerância pré-registrada e publicará apenas tempos, throughput e ganho agregado. Os shards normais não executam A/B.

**Matriz:** `max-parallel: 20`; `timeout-minutes: 350` por worker/shard. `fail-fast: false`, para que uma falha isolada seja registrada e os demais shards concluam. O manifesto determina dinamicamente a quantidade de shards; não codificar 30/31 como número fixo. A contagem medida do TEST (29.320) implica 30 shards de tamanho máximo 1.000, com o último parcial.

## 3. Modelos e comparabilidade

- Fixar em manifesto versionado os commits completos já medidos: mDeBERTa `b5113eb38ab63efdd7f280f8c144ea8b13f978ce`; MiniCheck `2f2d01a54fa022a7ffadb76260e1ea8bc88c82bb`; FactCG `0430e3509dbd28d2dff7a117c0eae25359ff3e80`. Todos os shards e splits usam exatamente esses commits e os mesmos hashes de pesos/tokenizer. Qualquer atualização exige novo manifesto e nova comparação; nunca resolver `main` durante a execução. O pin de dataset também deve ser imutável e específico para cada split.
- Carregar os pesos originais em **FP32** (`torch.float32`), sem quantização, sem autocast e sem conversão para FP16/BF16. Validar dtype dos parâmetros antes da inferência e registrar versão de PyTorch/Transformers, hardware, threads e hashes.
- Manter `eval()` e `inference_mode()`. Não alterar chunking, agregação por exemplo, pré-processamento ou semântica de score durante a otimização de throughput.
- O pin imutável de TEST já existe em `main`: `configs/benchmarks/llm-aggrefact-pin.json`, revision `981dfd0bd8e58e7238a9ab92b2e6ea44bce918e4`, arquivo `data/test-00000-of-00001.parquet`, SHA-256 `ba6976c3da990a9d7b11670efaf4e3c93c1bd0530061ec742afd6b2d5bce698c`. Esse pin foi usado no benchmark de 06/11 sob o código `5f79290`. O workflow TEST deve validar diretamente esse arquivo versionado e conferir revision, caminho e hash antes de baixar ou processar dados.

## 4. Confidencialidade dos intermediários

**Regra absoluta:** notas, scores, predições, rótulos e qualquer registro por instância nunca serão anexados em texto claro a artefato, log, summary ou comentário público.

- Cada worker produz um pacote intermediário local e efêmero. Antes do upload, criptografar o pacote com **AES-256-GCM** usando `cryptography.hazmat.primitives.ciphers.aead.AESGCM`, nonce aleatório de 96 bits e AAD contendo run ID, split, model revision, shard ID, dataset revision e code SHA. Fixar a dependência `cryptography==46.0.3`; não usar `openssl enc`.
- A chave de 32 bytes, codificada em Base64, fica exclusivamente no secret `PHASE1B_ARTIFACT_ENCRYPTION_KEY` do environment `international-benchmark-maintainer-approval`. Nunca passar chave em argumento, output, cache, arquivo versionado ou log.
- O upload recebe somente ciphertext, nonce e metadados não sensíveis. `retention-days: 1` para todos os artefatos intermediários criptografados.
- O job agregador, também protegido pelo mesmo environment, baixa ciphertext, autentica/descriptografa em diretório temporário, valida integridade e agrega em memória. Publica apenas métricas agregadas e remove arquivos temporários ao terminar. Não publica pacotes descriptografados.
- Logs devem conter somente `run_id`, `shard_id`, `model_id`, `failure_stage` e classe/tipo de erro sanitizado. Nunca incluir `str(exception)`, payloads, textos ou notas.
- Permissões mínimas: `contents: read`; sem token de escrita no repositório. O relatório agregado passa por revisão/PR separado.

## 5. Calibração exclusivamente em DEV

- Para cada par `(modelo, coorte)`, selecionar amostra estratificada de até **500 exemplos por coorte**, com seed fixa e manifesto pré-registrado. Se a coorte tiver menos de 500 exemplos, usar todos; registrar a contagem efetiva.
- Escolher limiar usando apenas rótulos e scores DEV. Critério candidato para aprovação: maximizar balanced accuracy; desempate determinístico pelo limiar mais próximo de 0,5 e depois menor limiar. O critério e a grade/resolução de busca devem ser aprovados e congelados antes da execução.
- Versionar `configs/benchmarks/phase1b-thresholds.json` em PR próprio, contendo modelo, coorte, limiar, direção do score, classe positiva, seed, contagens, critério, dataset/model pins, code SHA e hash da amostra.
- O workflow de test deve falhar fechado se esse arquivo não existir, se seu hash não coincidir com o SHA explicitamente aprovado, ou se a proveniência não apontar exclusivamente para DEV. O workflow de test será separado do workflow DEV: não pode calibrar e testar no mesmo run.
- Nenhuma alteração de limiar após abrir/consultar resultados de test. Mudança exige nova versão, nova calibração DEV e novo protocolo.

## 6. Métricas e incerteza

Publicar, para cada modelo:
- balanced accuracy (BA) e macro-F1;
- matriz de confusão 2×2 com ordem de classes explicitada;
- recall de cada classe;
- métricas globais e por coorte;
- agregados com todas as coortes e sem RAGTruth;
- IC de 95% por bootstrap, com seed fixa e reamostragem estratificada por classe dentro de coorte; registrar número de réplicas (proposta: 10.000).

A matriz 2×2 pressupõe mapeamento binário documentado e congelado. Se uma classe estiver ausente numa amostra/coorte, não inventar valor: marcar métrica/IC como não estimável e explicar a causa. Os resultados sem RAGTruth são uma análise de sensibilidade adicional, nunca substituem o resultado completo.

## 7. Ordem de implementação e gates

1. Confirmar IDs estáveis, schema/labels e pins imutáveis de DEV/test/modelos.
2. Implementar e testar manifesto determinístico, amostragem DEV pré-registrada (até 500 por coorte, seed `20261106`), sharding e registro da contagem efetiva por coorte.
3. Implementar criptografia autenticada, retenção de um dia, agregador e testes negativos de vazamento.
4. Executar o A/B uma única vez em job próprio (um shard de 200 exemplos, um modelo) e registrar o ganho medido; não repetir A/B nos shards normais.
5. Executar calibração DEV; revisar e versionar limiares.
6. Antes de qualquer matriz real, executar teste mínimo obrigatório (1 shard, 10 exemplos) para verificar se o environment `international-benchmark-maintainer-approval` exige nova aprovação do revisor para cada job da matriz. Se exigir, parar e submeter alternativa para decisão do mantenedor: job único de aprovação + distribuição de chave de dados via criptografia de envelope (workers recebem somente chave pública; cada shard usa AES-GCM com chave aleatória; somente agregador aprovado recebe a chave privada). Não adotar essa alternativa sem decisão explícita.
7. Somente após aprovação do pin de test, do arquivo de limiares e do comportamento do environment, habilitar workflow separado de test.

## 8. Fora do escopo deste PR

Este PR contém apenas a evidência agregada original, o desenho técnico e os YAMLs propostos em `docs/`. Não instala workflows ativos em `.github/workflows`, não cria/assume o pin de test, não altera Judge/Golden/RGC, não escolhe limiares reais, não executa modelo, não dispara Actions e não publica resultados de qualidade. O YAML em `docs/` é uma especificação revisável, não um workflow executável até a implementação aprovada.
