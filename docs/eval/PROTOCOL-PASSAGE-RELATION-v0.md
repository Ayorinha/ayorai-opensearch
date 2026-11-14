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
  - Nenhum trecho citado abrange mais de um dispositivo, então o efeito não vem de trechos misturados.

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

## 4. Anotação de trechos (cega aos resultados)

1. Cada variante congelada produz um *run*. `metrics.py pool` reúne a união dos trechos citados por todas as variantes. O arquivo resultante contém só afirmação e texto do trecho, sem stance nem veredito.
2. Dois anotadores independentes classificam cada par afirmação–trecho:
   - **relação:** `direta`, `excecao_restricao`, `definicao_abrangencia`, `remissao` ou `sem_relacao`;
   - **efeito:** `supports`, `contradicts` ou `neutral`.
3. Divergências são resolvidas por adjudicação humana antes de qualquer resultado do sistema ser revelado. A concordância (kappa de Cohen da relação e do efeito) é reportada.
4. Cada par guarda `relation_a`, `relation_b`, `stance_a`, `stance_b`, os valores adjudicados `relation` e `stance`, e `adjudicated: true`.
   - O harness recusa caso ou par não adjudicado.
   - O harness recusa trecho citado que não foi anotado.

## 5. Métricas (`metrics.py score` e `compare`)

| Métrica | Definição |
|---|---|
| `recall_relevant_at_k` | trechos relevantes do pool citados ÷ trechos relevantes do pool (relevante = relação ≠ `sem_relacao`) |
| `relevance_precision_at_k` | trechos citados relevantes ÷ trechos citados |
| `false_contradicts_on_unrelated` | trechos `sem_relacao` com stance `contradicts` ÷ trechos `sem_relacao` citados |
| `contradicts_precision` / `contradicts_recall` | stance `contradicts` do sistema contra o efeito humano adjudicado, por trecho citado |
| `false_refuted_or_conflicting_on_supports` | afirmações `supports` com veredito `REFUTED` ou `CONFLICTING` ÷ afirmações `supports` |
| `contradiction_detected_on_contradicts` | afirmações `contradicts` com veredito `REFUTED` ou `CONFLICTING` ÷ afirmações `contradicts` |
| `abstention_rate` | veredito ausente ou `UNVERIFIED` ÷ afirmações |
| `contradicts_precision_<relação>` / `contradicts_recall_<relação>` | as mesmas medidas separadas por categoria de relação |

- **Intervalos:**
  - IC95% por bootstrap percentil reamostrando `cluster_id` inteiros;
  - 10.000 réplicas e seed 20261003 por padrão;
  - estatística de ordem sem interpolação, a mesma convenção de `evals/ptbr/rgc_eval.py`;
  - réplicas indefinidas são excluídas e contadas.
- **Comparação pareada (`compare`):**
  - diferença por métrica (segunda − primeira) com IC por cluster;
  - contagens discordantes por afirmação para veredito contraditório em `supports`, contradição detectada em `contradicts` e abstenção.

## 6. Regra de decisão (a definir pelo mantenedor antes do congelamento)

A melhoria só é real se reduzir contradições indevidas sem eliminar contradições juridicamente legítimas. Antes de qualquer execução, o mantenedor registra:

1. o desfecho primário (proposta: `false_refuted_or_conflicting_on_supports`);
2. a condição de não inferioridade sobre `contradiction_detected_on_contradicts` e `contradicts_recall_excecao_restricao`, com sua margem;
3. o tamanho mínimo do conjunto e de `cluster_id` distintos;
4. o tratamento de abstenções.

Este documento não escolhe esses valores.

## 7. Proibições

- Não executar nenhuma variante sobre o TEST do PT-CP. Não reutilizar os 70 casos DEV como confirmação.
- Não criar, completar, visualizar ou rotular casos do Piloto 02 ou do conjunto definitivo do RGC.
- Não criar nem rotular casos ou pares deste protocolo com IA.
- Não alterar Judge, Golden, `RuleStanceDetector`, limiares, manifests, hashes ou pré-registros.
- Não apresentar resultado exploratório como confirmatório.
