# Protocolo — relação entre trecho recuperado e afirmação em `/v1/check` (v0)

**Estado: [PROPOSTO].** Não congelado. Nenhum caso de avaliação existe. Nada aqui altera o Judge, o Golden, o `RuleStanceDetector`, limiares, pré-registros ou decisões aprovadas.

## 1. Observação exploratória que motiva o protocolo

**[FATO, exploratório]** Reproduzível com `python -m evals.passage_relation.exploratory_ptcp_dev` (somente o split DEV de `evals/pt-cp-audit`, já usado no desenvolvimento das regras; o TEST não é lido).

- Documento: texto vigente de todos os dispositivos da Parte Geral do Código Penal, um por linha.
- Casos: os 70 casos DEV rotulados `supports` ou `contradicts`.
- Resultados:
  - O dispositivo correto está entre os trechos citados em 68/70 casos.
  - Afirmações falsas (`contradicts`): 33/36 terminam `REFUTED`.
  - Afirmações verdadeiras (`supports`): 13/34 terminam `PARTIALLY_SUPPORTED`, que é o máximo possível com um único documento sob o ADR-002 (que exige duas fontes independentes para `SUPPORTED`). Outras 17 terminam `REFUTED` (10) ou `CONFLICTING` (7).
  - Entre os trechos de outros dispositivos citados para afirmações verdadeiras, 20 recebem `contradicts`.
  - Nenhum trecho citado abrange mais de um dispositivo (0/210). Isso é exploratório: exclui trechos misturados como causa neste conjunto, mas não prova que os trechos de outros dispositivos sejam juridicamente irrelevantes.

**[HIPÓTESE]** Trechos sem relação material com a afirmação produzem contradições indevidas que derrubam afirmações verdadeiras.

**[LIMITE]** Um dispositivo diferente pode conter uma exceção, restrição, definição ou remissão que contradiz legitimamente a afirmação. A contradição não pode ser descartada só por vir de outro artigo. Os 70 casos permanecem como evidência exploratória e não confirmam nenhuma variante.

## 2. Variantes a comparar

- **Atual:** `current`, o `check_documents` da `main` no momento do congelamento.
- **Alternativa A (seleção de evidências):** selecionar e ordenar trechos considerando a relação material entre a afirmação e o trecho.
- **Alternativa B (`ConservativeStanceDetector`, `document_check.py`):** distinguir contradição direta de exceção, definição, remissão e ausência de relação.

Cada variante entra em `evals/passage_relation/run_system.py` (`VARIANTS`) por uma mudança revisada própria. Ela é congelada antes de qualquer caso de avaliação ser executado: nome, commit e `engine` registrados. Nenhuma variante é ajustada depois de ver resultados de avaliação.

## 3. Conjunto de avaliação

- **Autoria:** casos escritos por pessoas, sem IA, sem reutilizar afirmações ou exemplos do PT-CP.
- **Documentos:**
  - de domínio público, com proveniência registrada;
  - sempre que possível, instrumentos normativos distintos dos usados no desenvolvimento;
  - um instrumento não aparece em desenvolvimento e avaliação ao mesmo tempo.
- **Caso:** `case_id`, `cluster_id`, `claim`, `label` (`supports`, `contradicts` ou `neutral`), `document_ids` e `adjudicated: true`.
  - `cluster_id` é o instrumento ou dispositivo e define a unidade de reamostragem.
  - `label` é o rótulo da afirmação em relação aos documentos.
- **Reserva:** os casos de avaliação ficam fora do repositório público até a execução única autorizada.

## 4. Dois conjuntos de trechos, anotados sem ver resultados

**Universo independente.** É o único conjunto que mede recall absoluto.
- Para cada afirmação, pessoas leem os documentos e marcam todos os trechos candidatos, de qualquer relação, antes de existir qualquer *run* e sem consultar as variantes.
- Quando o documento é curto, o universo pode ser formado por todas as unidades estruturais (artigos, parágrafos, incisos), anotadas uma a uma.
- Toda afirmação precisa ter ao menos uma linha no universo; o harness recusa o arquivo se faltar alguma.

**Pool das variantes.** Serve à comparação relativa.
- `metrics.py pool` reúne a união dos trechos citados pelas variantes congeladas.
- O arquivo contém só afirmação, texto do trecho, offsets, `passage_sha256` e `documents_sha256`, sem stance nem veredito.
- Recall sobre o pool é condicionado às variantes e nunca é apresentado como recall absoluto.

**Anotação, igual para os dois conjuntos:**
1. Dois anotadores independentes classificam cada par afirmação–trecho:
   - **relação:** `direta`, `excecao_restricao`, `definicao_abrangencia`, `remissao` ou `sem_relacao`;
   - **efeito:** `supports`, `contradicts` ou `neutral`.
2. Divergências são resolvidas por adjudicação humana antes de qualquer resultado do sistema ser revelado. O kappa de Cohen da relação e do efeito é reportado separadamente por conjunto.
3. Cada linha guarda `relation_a`, `relation_b`, `stance_a`, `stance_b`, os valores adjudicados `relation` e `stance`, `adjudicated: true` e `passage_sha256`.
4. O harness recusa:
   - linha não adjudicada;
   - `passage_sha256` diferente do texto nos documentos;
   - offsets fora do documento;
   - trecho citado por um run que não foi anotado no pool.

## 5. Rastreabilidade

Cada run registra:
- variante e commit completo (40 caracteres), e se a árvore de trabalho estava limpa (uma árvore suja é recusada, salvo uso explícito de desenvolvimento, que fica registrado);
- metadados da engine;
- SHA-256 do arquivo de casos e do arquivo de documentos;
- documento e offsets de cada trecho citado.

O harness recusa:
- run produzido para outros casos ou outros documentos;
- comparação entre runs com documentos diferentes;
- anotação cujo trecho não corresponda byte a byte ao documento usado.

Os relatórios repetem a identidade completa de cada run.

## 6. Métricas (`metrics.py score` e `compare`)

| Métrica | Conjunto | Definição |
|---|---|---|
| `recall_relevant_independent` | universo | unidades relevantes do universo sobrepostas por um trecho citado ÷ unidades relevantes do universo (relevante = relação ≠ `sem_relacao`; sobreposição ≥ 1 caractere no mesmo documento) |
| `retrieval_coverage_independent` | universo | afirmações com ao menos uma unidade relevante citada ÷ afirmações com unidade relevante |
| `recall_relevant_in_pool` | pool | trechos relevantes do pool citados ÷ trechos relevantes do pool (condicionado às variantes) |
| `relevance_precision_at_k` | pool | trechos citados relevantes ÷ trechos citados |
| `false_contradicts_on_unrelated` | pool | trechos `sem_relacao` com stance `contradicts` ÷ trechos `sem_relacao` citados |
| `contradicts_precision` / `contradicts_recall` | pool | stance `contradicts` do sistema contra o efeito humano adjudicado, total e por relação (`_<relação>`) |
| `false_refuted_or_conflicting_on_supports` | afirmações | afirmações `supports` com `REFUTED` ou `CONFLICTING` ÷ afirmações `supports` |
| `contradiction_detected_on_contradicts` (A) | afirmações | afirmações `contradicts` com `REFUTED` ou `CONFLICTING` ÷ afirmações `contradicts` |
| `decisive_refutation_on_contradicts` (B) | afirmações | afirmações `contradicts` com `REFUTED` ÷ afirmações `contradicts` |
| `conflicting_on_contradicts` | afirmações | afirmações `contradicts` com `CONFLICTING` ÷ afirmações `contradicts` |
| `abstention_rate` | afirmações | veredito ausente ou `UNVERIFIED` ÷ afirmações |

- **Desfecho para afirmações verdadeiras:** `REFUTED` e `CONFLICTING` contam juntos como resultado contraditório.
- **Afirmações falsas:** detecção (A) e refutação decisiva (B) são reportadas separadamente. `REFUTED` e `CONFLICTING` não são tratados como equivalentes em qualidade.
- **Sem universo independente:** as métricas de universo saem como "não medidas", nunca estimadas pelo pool.
- **Intervalos:**
  - IC95% por bootstrap percentil reamostrando `cluster_id` inteiros;
  - 10.000 réplicas e seed 20261003 por padrão;
  - estatística de ordem sem interpolação, a mesma convenção de `evals/ptbr/rgc_eval.py`;
  - réplicas indefinidas são excluídas e contadas.
- **Comparação pareada (`compare`):**
  - diferença por métrica (segunda − primeira) com IC por cluster;
  - contagens discordantes por afirmação para veredito contraditório em `supports`, detecção e refutação decisiva em `contradicts`, e abstenção.

## 7. Regra de decisão (a definir pelo mantenedor antes do congelamento)

A melhoria só é real se reduzir contradições indevidas sem eliminar contradições juridicamente legítimas. Antes de qualquer execução, o mantenedor registra:

1. o desfecho primário (proposta: `false_refuted_or_conflicting_on_supports`, com `REFUTED` e `CONFLICTING` contando como resultado contraditório);
2. a condição de não inferioridade sobre `decisive_refutation_on_contradicts`, `contradiction_detected_on_contradicts`, `contradicts_recall_excecao_restricao` e `recall_relevant_independent`, com suas margens;
3. o tamanho mínimo do conjunto e de `cluster_id` distintos;
4. o tratamento de abstenções.

Este documento não escolhe esses valores.

## 8. Proibições

- Não executar nenhuma variante sobre o TEST do PT-CP. Não reutilizar os 70 casos DEV como confirmação.
- Não criar, completar, visualizar ou rotular casos do Piloto 02 ou do conjunto definitivo do RGC.
- Não criar nem rotular casos ou pares deste protocolo com IA.
- Não alterar Judge, Golden, `RuleStanceDetector`, limiares, manifests, hashes ou pré-registros.
- Não apresentar resultado exploratório como confirmatório.
