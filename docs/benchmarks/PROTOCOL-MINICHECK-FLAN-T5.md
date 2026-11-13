# Protocolo proposto — MiniCheck-Flan-T5-Large

**Status:** PROPOSTA documental; Draft; não aprovado para execução.  
**Data:** 2026-11-08.  
**Modelo:** `lytang/MiniCheck-Flan-T5-Large`.  
**Escopo:** especificação de integração, chunking, agregação, custo preliminar e piloto. Nenhum peso foi baixado e nenhuma inferência foi executada.

## 1. Identidade, revisão e licença

- **Repositório Hugging Face:** [lytang/MiniCheck-Flan-T5-Large](https://huggingface.co/lytang/MiniCheck-Flan-T5-Large).
- **Revisão imutável proposta para pin:** `f2ce59cdbbdbbed2a1dbbaf658a86f44416a55ac` ([árvore do modelo nessa revisão](https://huggingface.co/lytang/MiniCheck-Flan-T5-Large/tree/f2ce59cdbbdbbed2a1dbbaf658a86f44416a55ac)). A revisão é um commit específico do repositório do modelo, não a referência móvel `main`.
- **Identificador usado pelo pacote oficial:** `flan-t5-large`, que resolve para `lytang/MiniCheck-Flan-T5-Large`.
- **Arquitetura:** T5 encoder-decoder; classe documentada `AutoModelForSeq2SeqLM`; checkpoint com aproximadamente 770M parâmetros.
- **Licença declarada no card do checkpoint:** MIT. Antes de redistribuir pesos ou empacotar a dependência, registrar separadamente as condições/licença do backbone `google/flan-t5-large` e as dependências transitivas.
- **Card e código consultados:** 2026-11-08. Não baixar pesos como parte desta proposta.

## 2. Repositório oficial MiniCheck e revisão do código

- **Repositório:** [https://github.com/Liyan06/MiniCheck](https://github.com/Liyan06/MiniCheck).
- **Commit imutável consultado:** `b58b9fa69acbd1015ec970fa65dd752413a053d2` (commit publicado em 2025-08-27; mensagem “keep only code changes”).
- **Arquivos de referência nessa revisão:**
  - [minicheck/inference.py](https://github.com/Liyan06/MiniCheck/blob/b58b9fa69acbd1015ec970fa65dd752413a053d2/minicheck/inference.py)
  - [minicheck/minicheck.py](https://github.com/Liyan06/MiniCheck/blob/b58b9fa69acbd1015ec970fa65dd752413a053d2/minicheck/minicheck.py)
  - [minicheck/utils.py](https://github.com/Liyan06/MiniCheck/blob/b58b9fa69acbd1015ec970fa65dd752413a053d2/minicheck/utils.py)
  - [README oficial](https://github.com/Liyan06/MiniCheck/blob/b58b9fa69acbd1015ec970fa65dd752413a053d2/README.md)

O protocolo deve fixar simultaneamente a revisão do modelo e a revisão do código. Não usar `@main` para uma execução reprodutível.

## 3. Formato oficial de entrada

A interface pública recebe pares alinhados:

- `docs`: lista de documentos de evidência;
- `claims`: lista de afirmações;
- `len(docs) == len(claims)`.

Exemplo de contrato (não executado):

```python
scorer = MiniCheck(model_name="flan-t5-large", cache_dir="...")
pred_label, raw_prob, used_chunks, support_prob_per_chunk = scorer.score(
    docs=[document],
    claims=[claim],
)
```

Para o Flan-T5, o código oficial concatena documento e afirmação com o token EOS do tokenizer, na ordem **documento + EOS + claim**, e adiciona o prefixo textual `predict: ` antes da tokenização. O tokenizer usa padding por lote, truncamento ativado e `max_length=2048` por padrão. O documento é dividido antes da concatenação; a afirmação completa é repetida em cada chunk.

A unidade do protocolo é um par documento–afirmação. Não reescrever, resumir ou traduzir documento/claim antes de enviar ao modelo. Não dividir claims em sentenças por conta própria nesta primeira proposta: o código oficial verifica uma claim como uma unidade; para claims com várias sentenças, o próprio repositório recomenda que o usuário decida a estratégia de segmentação/agregação. Qualquer mudança futura deve ser registrada como nova versão do protocolo.

## 4. Chunking oficial

Para `flan-t5-large`, o MiniCheck oficial aplica:

1. Segmentação do documento em sentenças com NLTK (`sent_tokenize`), preservando separadores de nova linha por blocos.
2. Agrupamento sequencial de sentenças em chunks com limite padrão de **500 palavras** (`chunk_size=500`), contando palavras por `len(sentence.split())`.
3. Quando adicionar a próxima sentença ultrapassaria o limite, emite o chunk atual e inicia outro com a sentença seguinte.
4. Uma sentença individual maior que 500 palavras não é subdividida por essa rotina; o tokenizer ainda aplica truncamento no limite de entrada de 2048 tokens.
5. Cada chunk é pareado com a claim original completa; não há divisão automática da claim na implementação Flan-T5.
6. O processamento em lote usa `batch_size=16` por padrão na interface oficial; o valor pode ser reduzido por memória, sem alterar o chunking ou a regra de agregação.

A implementação proposta deve registrar para cada execução: revisão do modelo, revisão do código, versão do NLTK/tokenizer, chunk_size, max_model_len, batch_size, quantidade de chunks por caso e se houve truncamento. A rotina não deve criar ou publicar conteúdo por instância; somente contagens agregadas de chunks e métricas operacionais.

## 5. Score e agregação entre chunks

Para cada chunk, o Flan-T5 produz logits do primeiro token de saída. O código oficial seleciona os logits dos tokens correspondentes a **No** (índice 3) e **Yes** (índice 209), aplica softmax sobre esses dois valores e interpreta a probabilidade da classe Yes como probabilidade de suporte.

- **Score por chunk:** (p_i = P(\text{SUPPORTED} \mid chunk_i, claim)), em ([0,1]).
- **Agregação oficial por par documento–claim:** (max_i p_i), isto é, o maior suporte observado entre os chunks.
- **Saída `raw_prob`:** probabilidade agregada de suporte, não o rótulo binário.
- **Rótulo oficial:** 1 se `raw_prob > 0.5`; caso contrário 0.

Não usar média, mediana ou votação entre chunks: a regra oficial é máximo. O protocolo do ATTRACTOR deve armazenar o score contínuo agregado para calibração posterior, sem substituir o score por `pred_label`. A regra E3/IVAP, se algum dia autorizada, é uma etapa posterior e separada; não deve ser confundida com a agregação interna de chunks do MiniCheck.

## 6. Estimativa preliminar de custo em CPU

O card oficial reporta throughput superior a 500 documentos/minuto em uma NVIDIA A6000 de 48 GB para MiniCheck-Flan-T5-Large. Esse número é de GPU e **não pode ser convertido diretamente em throughput de CPU**.

Para planejamento inicial, adotar somente como hipótese orçamentária — não como medição — **15 a 60 segundos de CPU por par documento–claim**, em CPU x86_64 com 8 vCPUs, FP32, batch 1, documento de até aproximadamente 500 palavras (um chunk), sem incluir o carregamento frio do checkpoint. Casos com vários chunks podem consumir aproximadamente esse custo por chunk. O checkpoint tem cerca de 3,14 GB no Hub; planejar pelo menos 16 GB de RAM para pesos e overhead do runtime, sujeito a confirmação.

Para 200 casos, a faixa preliminar representa aproximadamente **0,8 a 3,3 horas de CPU de inferência**, sem contar carga inicial, tokenização/instalação e eventuais reprocessamentos. Essa faixa é uma hipótese conservadora para dimensionamento; não é resultado experimental, SLA nem promessa de throughput. O piloto deve medir wall-clock total, CPU-seconds por caso, p50/p95, chunks/caso, RAM máxima e taxa de falhas em ambiente CPU identificado.

## 7. Plano de piloto — 200 casos DEV

**Desenho proposto:** piloto operacional de 200 pares documento–claim em DEV-A, estratificados por coorte. A alocação será proporcional ao número de registros DEV-A disponíveis nas coortes que vierem a ser formalmente consideradas elegíveis, usando método de maiores restos para fechar exatamente 200. Registrar a contagem por coorte e a regra de seleção antes do piloto.

- O piloto mede formato, estabilidade, chunking, truncamento, custo, memória, throughput e falhas.
- Não calcular BA, AUROC, calibração, ganho contra FactCG ou qualquer métrica de qualidade; não comparar modelos nem selecionar configuração com esses 200 casos.
- Não consultar, pontuar ou usar DEV-B. O holdout de DEV-B reservado ao P1 permanece intocado.
- Não usar TEST.
- Publicar somente agregados operacionais, revisão do modelo/código, configuração de runtime e hashes dos artefatos de execução.
- O piloto exige aprovação explícita do mantenedor, matriz de elegibilidade aprovada e confirmação de que as células amostradas estão liberadas.

**Gate atual:** o ledger A4 v0.8 classifica todas as células MiniCheck-Flan-T5-Large × coorte como bloqueadas: três por exposição de fonte conhecida (AggreFact-CNN, AggreFact-XSum e WiCE) e as demais como UNVERIFIED. Portanto, **não existe atualmente uma coorte elegível para este piloto**. O plano de 200 casos é apenas um desenho futuro; não selecionar casos, baixar pesos ou executar inferência enquanto esse gate não mudar por evidência positiva e decisão formal.

## 8. Contaminação por coorte segundo o ledger A4

Fonte: [CONTAMINATION-LEDGER-v0.8.md, seção 4.2](CONTAMINATION-LEDGER-v0.8.md). O status é específico do par modelo × coorte.

| Coorte | Status no ledger | Implicação para MiniCheck-Flan-T5-Large |
|---|---|---|
| AggreFact-CNN | BLOCKED — exposição de fonte no backbone; deduplicação pendente | Bloqueada |
| AggreFact-XSum | BLOCKED — exposição de fonte no backbone; deduplicação pendente | Bloqueada |
| TofuEval-MediaS | UNVERIFIED — BLOQUEADO | Bloqueada |
| TofuEval-MeetB | UNVERIFIED — BLOQUEADO | Bloqueada |
| WiCE | BLOCKED — fonte WiCE no fine-tuning; deduplicação pendente | Bloqueada |
| REVEAL | UNVERIFIED — BLOQUEADO | Bloqueada |
| ClaimVerify | UNVERIFIED — BLOQUEADO | Bloqueada |
| FactCheck-GPT | UNVERIFIED — BLOQUEADO | Bloqueada |
| ExpertQA | UNVERIFIED — BLOQUEADO | Bloqueada |
| LFQA | UNVERIFIED — BLOQUEADO | Bloqueada |
| RAGTruth | UNVERIFIED — BLOQUEADO | Bloqueada |

O status UNVERIFIED significa que não há evidência suficiente para provar independência; não significa ausência de contaminação. A exposição FLAN a CNN/DailyMail e XSum é exposição de fonte/tarefa no backbone e não prova, por si só, identidade dos exemplos. O ledger mantém esses pares bloqueados até deduplicação por IDs/conteúdo e revisão verificável.

## 9. Limites

Este documento não aprova o modelo para benchmark, não altera o ledger ou qualquer matriz de elegibilidade, não autoriza execução, não baixa pesos e não produz resultados. Qualquer adoção exige revisão independente da licença e proveniência, elegibilidade positiva por coorte, aprovação do protocolo e autorização explícita do mantenedor.

**Conclusão:** MiniCheck-Flan-T5-Large tem interface e agregação oficiais suficientemente especificadas para uma proposta documental reproduzível. O risco de contaminação permanece bloqueador em todas as coortes; o piloto de 200 casos não pode ser executado no estado atual.
