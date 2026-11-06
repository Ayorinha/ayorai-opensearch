# Piloto de throughput — baselines internacionais

**Estado:** PR em Draft; execução NÃO autorizada até aprovação do mantenedor após revisão do PR.  
**Escopo:** split `dev` do LLM-AggreFact; 200 exemplos; throughput e recursos, sem avaliação de qualidade comparativa.

## Decisões pré-registradas

- Coorte: campo `dataset` do LLM-AggreFact.
- Amostra: 200 exemplos, estratificados por coorte, seed fixa `20261106`; seleção determinística dentro de cada coorte.
- Modelos desta rodada: HHEM-2.1-Open (condicional ao acesso gated e revisão de `configuration_hhem_v2.py` e `modeling_hhem_v2.py`), mDeBERTa-v3-base NLI multilíngue, MiniCheck-DeBERTa-v3-Large e FactCG-DeBERTa-v3-Large (candidato experimental, somente DEV). LettuceDetect e LLM-as-judge estão excluídos.
- FactCG é candidato experimental: os dados de treino (CG2C; arXiv `2501.17144`) e possível contaminação precisam ser verificados antes de qualquer uso no split `test`; até essa verificação, seu uso fica restrito ao `dev`.
- SHA completo dos modelos: no piloto, resolver os prefixos `de9a5e6`, `b5113eb` e `2f2d01a` pela API do Hub; aceitar somente correspondência única. FactCG usa o SHA completo fixado `0430e3509dbd28d2dff7a117c0eae25359ff3e80` (revisão mais recente informada pelo mantenedor, de 21/02/2025), sem resolução por `main`. Registrar SHA completo e SHA-256 de cada arquivo de pesos e tokenizer. O congelamento oficial ocorrerá em PR próprio antes de qualquer uso do split `test`.
- HHEM: não executar até que o mantenedor confirme acesso gated e a revisão dos dois arquivos de custom code esteja registrada. Enquanto isso, registrar HHEM como `SKIPPED`, não como falha nem como resultado; os demais candidatos seguem independentemente.
- Formatos de pesos por modelo: mDeBERTa usa `safetensors`; MiniCheck usa exclusivamente `pytorch_model.bin` (exceção explícita, pois o repositório não publica `.safetensors`); FactCG usa `safetensors`. O harness verifica a presença do arquivo correspondente e falha aquele modelo com motivo claro se estiver ausente. O download usa os padrões comuns mais somente o padrão do formato declarado para cada modelo; nunca solicita `.safetensors` e `.bin` juntos.
- Para MiniCheck (`.bin`), o carregamento força `torch.load(weights_only=True)` por wrapper e `TORCH_FORCE_WEIGHTS_ONLY_LOAD=1`; se a versão do PyTorch não expuser `weights_only`, o modelo falha sem tentar carregar pesos não restritos.
- Isolamento por modelo: cada candidato recebe status `SUCCESS` ou `FAILED`, com motivo sem conteúdo do dataset; o processamento continua nos demais. HHEM permanece `SKIPPED` enquanto acesso gated e revisão do custom code não estiverem aprovados. O relatório agregado é preservado e o job termina com erro se houver qualquer `FAILED`.
- Split: somente `dev`; nenhum dado do split `test` será baixado, consultado ou usado.
- Limiar: sem seleção de modelo e sem métrica de qualidade nesta fase. Qualquer limiar de qualidade será pré-registrado e calibrado exclusivamente no `dev`, em etapa posterior autorizada.

## Política de chunking comum

Aplicar igualmente a todos os modelos que recebem documento × afirmação:

1. Tokenizar com o tokenizer específico do modelo, preservando sentenças.
2. Dividir o documento em blocos por sentença, limite máximo **384 tokens** por bloco.
3. Sobreposição fixa de **64 tokens** (aproximada por sentenças completas; se uma sentença exceder o limite, dividir por tokens).
4. Cada bloco é avaliado contra a mesma afirmação.
5. Registrar score por bloco sem publicar texto nem previsões por instância.
6. Agregação pré-registrada: **máximo dos scores dos blocos**. Para uma regra binária de suporte, `SUPPORTED` se pelo menos um bloco atingir o limiar previamente definido; caso contrário `NOT_SUPPORTED`. Não escolher limiar observando o split `test`.
7. Registrar média, mediana, p95 e máximo de blocos por exemplo. O número de blocos será considerado fator dominante de throughput.

**Nota:** a sobreposição por sentença pode variar ligeiramente em tokens para preservar limites semânticos; registrar tokens efetivos por bloco e overlap observado. Não alterar a política após observar resultados de qualidade.

## Saídas do piloto

- tempo de carregamento por modelo;
- throughput (exemplos/s, blocos/s e segundos/exemplo);
- RAM máxima observada;
- distribuição de tokens de documento, afirmação e pares;
- distribuição de blocos por exemplo;
- estimativa do test completo por coorte, baseada somente em contagem e throughput, com margem explícita;
- proposta de sharding por coorte e timeout;
- model revision SHA e SHA-256 dos arquivos de pesos/tokenizer;
- seed, seleção estratificada, code SHA, dataset dev revision/file/hash;
- indicação de modelos skipped e motivo.

Não publicar documentos, afirmações, respostas, amostras, predições ou resultados por instância. Artefatos somente agregados.

## Segurança e gate

- Workflow manual, environment `international-benchmark-maintainer-approval`, segredo `HF_TOKEN` no environment.
- Não dispatchar automaticamente em PR, push ou merge.
- Não usar API externa de LLM.
- Nenhum download ou execução durante a criação/revisão do PR.
- O workflow deve abortar se dataset revision/hash não corresponderem aos inputs.
- Não realizar qualquer acesso ao split test nesta etapa.
