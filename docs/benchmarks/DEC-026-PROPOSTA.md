# DEC-026 (PROPOSTA) — Elegibilidade por estados de exposição verificáveis

**Status:** PROPOSTA, não aprovada. Não altera nenhuma decisão aprovada, a matriz `configs/benchmarks/e3-eligibility-v0.8.json`, o ledger A4 ou resultados publicados. A aprovação depende de revisão independente e de decisão expressa do mantenedor, registrada antes de qualquer resultado confirmatório.  
**Autoria:** ANDERSON AYORA  
**Natureza:** emenda metodológica **posterior** à análise exploratória do E3 (run 42485634513).

## 1. Motivação

- O pré-registro do E3 torna inelegíveis as células com status desconhecido ou não verificado.
- O ledger A4 (`docs/benchmarks/CONTAMINATION-LEDGER-v0.8.md`) exige, para liberar uma célula, manifestos de treino com IDs, revisão imutável e deduplicação. Nenhum dos cinco modelos publica esses manifestos. Resultado: 0/55 células liberadas, sem caminho de mudança.
- Um critério inexequível impede qualquer conclusão confirmatória, inclusive sobre o baseline. A causa da emenda é essa inexequibilidade, constatada pelo ledger, e não o desempenho de qualquer configuração.

## 2. Estados propostos

| Estado | Definição operacional | Elegibilidade |
|---|---|---|
| 1. Exposição confirmada | Fonte primária documenta, no treino, a fonte ou o corpus da coorte | Bloqueada |
| 2. Exposição provável | Indício concreto sem confirmação documental (por exemplo, correspondência textual relevante no teste empírico) | Bloqueada |
| 3. Sem exposição detectada pelos testes realizados | Dados de fine-tuning públicos **e** teste empírico pré-especificado executado com resultado negativo | Elegível, com o rótulo "independência não demonstrada; sem exposição detectada pelos testes realizados" |
| 4. Independência não verificável | Teste ainda não executado, ou impossível por dados confidenciais | Bloqueada |

Regras complementares:

- **Backbone:** o pré-treinamento genérico em corpora web, comum a todos os modelos, é declarado como limitação universal. Só conta como exposição da célula quando uma fonte primária documenta o corpus da coorte na mistura de tarefas do backbone (caso FLAN: CNN/DailyMail e XSum).
- **Exposição de seleção** (por exemplo, FactCG §6.2: limiar ajustado no validation do LLM-AggreFact) é registrada separadamente da contaminação de pesos e declarada em todo resultado. Se ela deve bloquear células é um **ponto em aberto**.
- **Evidência nova** de exposição rebaixa a célula imediatamente, com errata datada.
- **Sem reclassificação retroativa:** o E3 exploratório continua exploratório.

## 3. Matriz anterior e matriz proposta

A matriz anterior (v0.8, sha256 `8b7becf74727a1ad1d52706760c9682b04bd1805476bf3c0c0adddefa1f569f4`) é preservada sem alteração. A comparação célula a célula, com fontes, está em `docs/benchmarks/ELIGIBILITY-RECONCILIATION-v0.9.md`.

**Transparência:** pelas regras acima, as células com exposição confirmada coincidem quase inteiramente com os bloqueios da v0.8 (Wice para MiniCheck-DeBERTa, MiniCheck-Flan-T5 e FactCG; CNN/XSum para Flan-T5; RAGTruth e demais coortes para HHEM). A diferença principal é que nenhuma célula fica elegível sem teste empírico executado. Hoje, portanto, nenhuma célula está no estado 3.

## 4. Investigação empírica proposta (não executada)

- **Método:** correspondência exata e sobreposição de n-gramas de 50 caracteres entre os dados de fine-tuning públicos de cada modelo e os documentos e afirmações de cada coorte, seguindo Vilar et al., *Benchmark Data Contamination in Underrepresented Languages: A Comprehensive Analysis Using Brazilian Data*, LREC 2026, pp. 4765–4777, DOI [10.63317/39wbjvajnh7t](https://aclanthology.org/2026.lrec-1.374/).
- **Dados de treino testáveis (públicos):** `lytang/C2D-and-D2C-MiniCheck` (MIT; 14,4 mil linhas, C2D e D2C); ANLI; MultiNLI, FEVER-NLI, LingNLI e WANLI (mDeBERTa); HotpotQA e MuSiQue (fontes do CG2C-MHQA do FactCG). A publicação dos dados gerados CG2C não foi verificada.
- **Somente DEV, somente contagens agregadas por célula.** O TEST nunca é lido. Texto obrigatório em toda comunicação: "A investigação empírica de contaminação foi realizada no DEV. Como DEV e TEST compartilham fontes, os resultados fornecem evidência auxiliar sobre exposição potencial, mas não constituem verificação direta de independência dos exemplos do TEST."
- **Protocolo a fixar ANTES de qualquer execução:** normalização do texto (por exemplo, minúsculas, espaços), tamanho do n-grama, unidade (documento, afirmação), limiar de "correspondência relevante", denominador, fonte e versão exata de cada corpus de treino, tratamento de corpus incompleto e risco de falso negativo (um teste negativo não prova independência).

### 4.1 Viabilidade por modelo (não é uniforme)

| Modelo | Dados de fine-tuning | Viabilidade do teste |
|---|---|---|
| MiniCheck-DeBERTa | ANLI + C2D/D2C (`lytang/C2D-and-D2C-MiniCheck`, MIT) | Viável: corpora públicos e pequenos |
| MiniCheck-Flan-T5 | Mesmo fine-tuning do MiniCheck; backbone com a coleção FLAN | Viável para o fine-tuning; para o backbone, a coleção FLAN é muito ampla e o teste pode ser impraticável — células podem continuar no estado 4 |
| FactCG | ANLI, C2D/D2C (públicos), CG2C-MHQA (de HotpotQA e MuSiQue, públicos) e CG2C-Doc (publicação dos dados gerados não verificada) | Parcial: viável nas fontes públicas; incompleto sem os dados gerados. E a exposição de **seleção** não é resolvida por este teste |
| mDeBERTa NLI | MultiNLI, FEVER-NLI, ANLI, LingNLI, WANLI, XNLI validation | Viável, mas volume grande (milhões de pares) |
| HHEM-2.1-Open | Parcialmente confidencial | Inviável: permanece no estado 4 |
- **Testes de memorização comportamental:** não adotados para classificadores encoder (MiniCheck, FactCG, mDeBERTa), por falta de método validado para essa classe de modelo. TS-Guessing não é adaptado automaticamente.
- **Avaliado e descartado:** Kernel Divergence Score (Choi et al., ICML 2025, PMLR 267:10666–10682), porque exige fine-tuning do modelo no próprio benchmark, o que é vedado pelos termos de uso do LLM-AggreFact e pela DEC-024.
- **`contamination_identifier`:** usado como canário de rotina para novos membros e versões; encontrá-lo num corpus é evidência de exposição; não encontrá-lo não prova independência.

## 5. Fontes primárias das exposições confirmadas

| Exposição | Fonte primária | Tipo de evidência |
|---|---|---|
| Wice × MiniCheck-DeBERTa e MiniCheck-Flan-T5 | MiniCheck, [arXiv:2404.10774](https://arxiv.org/abs/2404.10774), §3.3 e Apêndice D | Fonte da coorte no fine-tuning; identidade dos exemplos não demonstrada |
| Wice × FactCG | FactCG, [arXiv:2501.17144](https://arxiv.org/abs/2501.17144), §5 (uso do C2D do MiniCheck) | Idem |
| CNN e XSum × MiniCheck-Flan-T5 e HHEM | [FLAN tasks.py](https://github.com/google-research/FLAN/blob/main/flan/tasks.py) (`cnn_dailymail:3.1.0`, `huggingface:xsum`) | Corpus na mistura de tarefas do backbone; não identifica os exemplos vistos |
| RAGTruth × HHEM | [EMNLP Industry 2025](https://aclanthology.org/2025.emnlp-industry.54/), §3 | Conjunto de treino da fonte da coorte; demais dados confidenciais |
| Seleção × FactCG (10 coortes) | FactCG, [arXiv:2501.17144](https://arxiv.org/abs/2501.17144), §6.2 | Exposição de seleção, não de pesos |

As citações literais de cada célula estão no ledger A4.

## 6. Pontos em aberto para a revisão

1. A exposição de seleção do FactCG deve bloquear células? Enquanto não houver decisão, o FactCG não pode ser tratado como independente numa alegação confirmatória.
2. Qual critério de "correspondência relevante" no teste de n-gramas (proporção de documentos/afirmações com correspondência, por célula)?
3. A coleção FLAN deve ser testada por n-gramas, apesar do custo, ou o Flan-T5 permanece no estado 4?

## 7. O que esta proposta não faz

Não aprova nada, não executa testes, não altera a matriz v0.8, o ledger, pré-registros aprovados, resultados publicados ou qualquer artefato protegido, e não autoriza P1 nem TEST.
