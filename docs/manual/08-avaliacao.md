Estado: Atual · Referência: main @ ed90cf6 · Atualizado: 2026-10-21
Fontes de verdade: `evals/ptbr/rgc_eval.py`, `tests/test_rgc_eval_runner.py`, `docs/eval/RUNNER-RGC-v1.md`, `docs/eval/STATISTICS.md`, `docs/eval/PREREGISTRATION-RGC-v1.md`, `docs/eval/PROTOCOL-GOLDEN-V1.md`, `docs/DECISIONS-PENDING.md`.

# 08 — Avaliação e limites de interpretação

## Propósito

Este capítulo descreve o executor de avaliação que existe no repositório e separa testes sintéticos, regressões Golden e o desenho ainda proposto do benchmark RGC PT-BR. A presença de código de avaliação não significa que um benchmark tenha sido executado, que o protocolo esteja congelado ou que exista validação institucional.

## Camadas de evidência

- **Testes unitários e sintéticos:** verificam contratos de funções, mapeamento de rótulos, entradas incompletas e regras estatísticas com dados sintéticos identificados. Não estimam desempenho sobre o RGC.
- **Regressão Golden:** protege o comportamento esperado do corpus Golden versionado. O lint e os testes de regressão são controles de engenharia; não constituem benchmark externo.
- **Executor RGC proposto:** `evals/ptbr/rgc_eval.py` aceita casos e rótulos fornecidos, valida correspondência entre IDs, exclui explicitamente rótulos de exclusão e calcula métricas. O fluxo exige rótulos humanos completos e metadados de desenvolvimento.
- **Relatório:** registra configuração, hashes dos arquivos de entrada, SHA do commit, métricas, matriz de confusão e comparação com baseline. Esses campos favorecem rastreabilidade; não demonstram que a partição declarada esteja realmente isolada.

## Baselines e hipótese

A baseline B é derivada dos rótulos humanos completos da partição pública de desenvolvimento, antes da avaliação. A baseline A é derivada da distribuição dos rótulos de avaliação e é somente descritiva; ela não participa da hipótese primária. A implementação de B aplica a ordem fixa do vocabulário para desempate, conforme o pré-registro.

A hipótese H1 contém critérios pré-especificados e não deve ser reconfigurada após observar resultados. A decisão do mantenedor registrada na DEC-018 restringe a análise confirmatória à partição oculta (~90 casos); a partição pública (~210 casos) serve apenas para desenvolvimento e descrição. O argumento `--partition` é metadado operacional, não evidência suficiente de isolamento. A execução confirmatória continua bloqueada pelos gates humanos e pelo estado [PROPOSTO] do protocolo.

## Interpretação das métricas

O executor calcula métricas classificatórias, intervalo de confiança bootstrap e teste exato de McNemar para a comparação pareada com a baseline B. As decisões de H1 usam valores não arredondados; o arredondamento ocorre no relatório. A matriz de confusão e a contagem de predições inválidas ajudam a explicar erros, mas uma métrica agregada não substitui análise por classe nem revisão humana.

Uma predição presente que não pode ser mapeada para o vocabulário é registrada como `INVALID_PREDICTION` e contabilizada como incorreta. Registro ausente, rótulo ausente, duplicata ou incompatibilidade entre arquivos deve interromper a execução, não ser removido silenciosamente.

## Reprodutibilidade mínima

Antes de interpretar qualquer relatório, confira:

1. SHA do commit e versão do executor;
2. hashes e contagens dos arquivos de casos, rótulos, desenvolvimento e documentos;
3. configuração de modo, vocabulário, partição e parâmetros estatísticos;
4. integridade dos rótulos e ausência de sobreposição entre desenvolvimento e avaliação;
5. proveniência humana e evidência de isolamento da partição;
6. resultado dos testes e limitações conhecidas.

Não use o executor sobre casos RGC reais enquanto os gates humanos e a decisão formal de congelamento permanecerem pendentes.

## Limites

- Nenhuma execução RGC ou métrica de benchmark é afirmada por este capítulo.
- O piloto 02 exige anotação humana sem IA; a segunda anotação deve ser realizada por outra pessoa.
- A revisão humana independente do achado F-01 permanece pendente.
- O protocolo continua [PROPOSTO]; este documento não o congela.
- Não há afirmação de certificação, validação institucional ou prontidão de produção.

## Referências internas

- `evals/ptbr/rgc_eval.py`
- `tests/test_rgc_eval_runner.py`
- `docs/eval/RUNNER-RGC-v1.md`
- `docs/eval/STATISTICS.md`
- `docs/eval/PREREGISTRATION-RGC-v1.md`
- `docs/eval/PROTOCOL-GOLDEN-V1.md`
- `docs/DECISIONS-PENDING.md`


**Nota de consistência (2026-10-21):** DEC-017, DEC-018, DEC-019 e DEC-020 estão aprovadas pelo mantenedor, conforme `docs/DECISIONS-PENDING.md` e as Emendas 7–10. A aprovação dessas decisões não congela o protocolo; os gates humanos continuam pendentes.
