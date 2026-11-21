# Proposta de emendas datadas — IC de kappa por componente (DEC-022) e H1 no protocolo (DEC-027)

**Estado:** PROPOSTA, para inserção pelo mantenedor. Este arquivo não altera `docs/eval/PREREGISTRATION-RGC-v1.md` nem `docs/eval/PROTOCOL-GOLDEN-V1.md`, que são artefatos protegidos (AGENTS.md §4) e só mudam por emenda datada inserida ou aprovada explicitamente pelo mantenedor.

## Por que estas emendas

- **DEC-022** (aprovada em 2026-11-07, opção A) definiu o IC95% de Cohen's kappa por bootstrap de componente. A Emenda 10, nos dois documentos, ainda descreve o bootstrap por caso. A DEC-027 exige que mudanças de texto no pré-registro e no protocolo sejam feitas por emenda datada própria.
- **DEC-027 D4 e D5** já estão no pré-registro (Emenda 11, 2026-11-14), mas o protocolo termina na Emenda 10.
- O código já implementa as duas decisões: `evals/ptbr/rgc_agreement.py` publica o IC por componente, e o executor `rgc-eval/0.13.0` o recalcula e o exige. As emendas abaixo apenas transcrevem decisões aprovadas e não acrescentam regra nova.

## Texto proposto 1 — fim de `docs/eval/PREREGISTRATION-RGC-v1.md`

Também acrescentar, na linha "Emendas vigentes para leitura conjunta" do início do arquivo, o link para a Emenda 12.

```markdown
## Emenda 12 (AAAA-MM-DD) — IC de kappa por componente (DEC-022)

Pela decisão do mantenedor registrada na DEC-022, opção A, aprovada em 2026-11-07, e especificada pela DEC-027 (D2 e D3, aprovada em 2026-11-14):

1. **IC95% de kappa.** O intervalo do item 2 da Emenda 10 passa a ser o percentil por bootstrap de componente conectado (DEC-023): 10.000 reamostragens, seed `20261003`, RGC-PRNG-1 com o fluxo `dec022-kappa-bootstrap` e quantil tipo 7 de Hyndman–Fan. Cada réplica sorteia K componentes com reposição e leva todos os casos elegíveis do componente sorteado, preservando a multiplicidade.
2. **Réplicas indefinidas.** Réplicas em que kappa é indefinido são excluídas do intervalo, contadas e reportadas com a proporção. Se a proporção passar de 5%, o intervalo é marcado como **instável**.
3. **Componentes.** Os componentes são construídos só com `case_id` e `cited_article_ids` do arquivo de casos aprovado, sem ler rótulos, previsões ou resultados. O relatório de concordância registra o SHA-256 desse arquivo. ID fora da gramática D1 ou lista de citações vazia interrompe o cálculo.
4. **Sensibilidade.** O IC por bootstrap de casos da Emenda 10 continua reportado, apenas como sensibilidade.
5. **Preservação.** O gate continua sendo a estimativa pontual `κ ≥ 0,6`; nenhum limite de intervalo é gate. Os demais itens da Emenda 10 não mudam. A redação original da Emenda 10 continua acima, como registro histórico.
6. **Limites.** Esta emenda não congela o protocolo, não cria nem rotula casos, não calcula concordância real e não autoriza execução do ATTRACTOR sobre casos RGC. A ferramenta que a implementa é `evals/ptbr/rgc_agreement.py`, verificada pelo executor `rgc-eval/0.13.0`.
```

## Texto proposto 2 — fim de `docs/eval/PROTOCOL-GOLDEN-V1.md`

Duas emendas, em ordem. A Emenda 11 reproduz a do pré-registro, que é a fonte.

```markdown
## Emenda 11 (AAAA-MM-DD) — teste de H1 e IC por componente (DEC-027, D4 e D5)

Registro neste protocolo da Emenda 11 do pré-registro (2026-11-14). Pela decisão do mantenedor registrada na DEC-027 (aprovada em 2026-11-14), que aplica DEC-021 e DEC-023:

1. **Teste primário de H1.** A terceira condição do §5 do pré-registro ("teste exato de McNemar bilateral contra a baseline com p < 0,05") passa a ser o teste sign-flip bilateral por componente da DEC-021, com p < 0,05. A estatística é T = Σ_k d_k, com d_k = a_k − b_k. Para K ≤ 20, enumeração completa; para K > 20, 10.000 vetores de sinais do RGC-PRNG-1 (fluxo `dec021-sign-flip`), em ordem lexical dos IDs de componente, com p = (1 + extremos)/(1 + 10.000).
2. **IC95% primário.** O limite inferior exigido pelo §5 vem do bootstrap percentil por componente conectado da DEC-023 (fluxo `dec023-accuracy-bootstrap`, quantil tipo 7, 10.000 reamostragens, seed `20261003`). O bootstrap por cluster de artigo da Emenda 9 (DEC-019) e o bootstrap por caso passam a ser análises de sensibilidade.
3. **Sensibilidade do teste.** O McNemar exato bilateral e o teste de Obuchowski (1998) por componente são sempre reportados, apenas como sensibilidade.
4. **Resolução.** Com K′ < 6 componentes informativos, H1 não pode receber suporte. O relatório informa `informative_component_count`, `minimum_attainable_p` e `significance_below_005_possible`. O gate prévio D7 (K ≥ 6) continua obrigatório.
5. **Preservação.** A condição de margem (≥ 10 p.p. sobre a baseline B) não muda.
6. **Limites.** Esta emenda não congela o protocolo, não cria nem rotula casos, não executa o ATTRACTOR sobre casos RGC e não produz métricas.

## Emenda 12 (AAAA-MM-DD) — IC de kappa por componente (DEC-022)

(Mesmo texto da Emenda 12 proposta para o pré-registro, acima.)
```

## Efeito no código

Nenhum. O código já segue estas decisões. Inserir as emendas alinha o texto normativo ao código e encerra os bloqueios M-13 e E-15 dos registros de auditoria.
