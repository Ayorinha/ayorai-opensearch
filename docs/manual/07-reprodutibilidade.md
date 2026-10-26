Estado: Atual · Referência: main @ 2dc089f · Atualizado: 2026-10-25
Fontes de verdade: `scripts/reproduce.py`, `src/ayorai_attractor/evaluation/report_manifest.py`, `tests/test_evaluation_report_manifest.py`, `tests/test_golden_digest.py`, `tests/test_golden_git_sha.py`, `evals/ptbr/rgc_eval.py`, `docs/eval/RUNNER-RGC-v1.md`, `docs/eval/STATISTICS.md`, `docs/eval/PREREGISTRATION-RGC-v1.md`, `docs/eval/PROTOCOL-GOLDEN-V1.md` e `docs/DECISIONS-PENDING.md`.

# 07 — Reprodutibilidade e proveniência de avaliação

## Propósito

Este capítulo define quais evidências devem acompanhar uma execução e distingue a reprodução das suítes Golden de desenvolvimento do fluxo proposto para o benchmark RGC PT-BR. Reprodutibilidade exige identificar os bytes e a configuração usados; não é prova de verdade factual, validade jurídica ou generalização.

## Como funciona

### Identidade da execução

Uma execução reprodutível deve registrar, no mínimo:

- SHA exato do commit avaliado;
- versão do Python, dependências resolvidas e ambiente de execução;
- nome e versão da suíte, comando completo e parâmetros;
- SHA-256 dos arquivos de casos, rótulos de referência, documentos-fonte e demais entradas;
- configuração efetiva, seed e parâmetros estatísticos;
- resultados brutos, relatório derivado e manifesto dos artefatos finais;
- desvios, erros, casos excluídos e justificativa de cada exclusão permitida pelo contrato.

O manifesto de artefatos calcula hashes sobre os bytes finais e registra tamanho e caminho relativo dos artefatos. A função de manifesto exige um identificador de commit conhecido; quando `GITHUB_SHA` não existe, uma execução fora do CI pode usar `commit: "unknown"` somente se estiver marcada explicitamente como `non_ci_run: true`. Esse marcador informa que a execução não foi identificada por um SHA de CI; não identifica o código por si só.

### Reprodução das suítes Golden existentes

O script `scripts/reproduce.py` foi criado para reproduzir os artefatos congelados e gravar relatórios em `reports/`. O modo rápido, disponível por `make reproduce-quick`, pula a execução completa de pytest; `make reproduce` usa o fluxo completo definido no script. Antes de interpretar a saída:

1. confira o SHA do checkout e os hashes esperados no script/testes;
2. verifique se os artefatos Golden e o corpus correspondem às versões referenciadas;
3. preserve a saída original e o comando usado;
4. compare valores observados com os valores congelados; divergências devem falhar e ser investigadas, não corrigidas editando fixtures;
5. registre ambiente, versão da suíte e limitações.

O script de reprodução declara que lê artefatos congelados e escreve relatórios; não deve editar Goldens, manifestos ou hashes. Resultados de desenvolvimento devem continuar identificados como desenvolvimento.

### Contrato proposto do runner RGC PT-BR

O executor em `evals/ptbr/rgc_eval.py` é marcado **[PROPOSTO]**. O documento `docs/eval/RUNNER-RGC-v1.md` define o contrato e seus parâmetros; a implementação registra o commit, versão do executor, configuração, hashes de casos/rótulos/documentos, previsões e `output_sha256` do Judge. O runner exige arquivos de casos e rótulos de avaliação e, para a baseline B, os arquivos separados de desenvolvimento e seus rótulos humanos. Ele verifica que os IDs correspondam e recusa sobreposição entre desenvolvimento e avaliação.

O desenho proposto usa seed `20261003` e 10.000 reamostragens de bootstrap. A Emenda 6 define B como classe majoritária derivada dos rótulos humanos da partição pública de desenvolvimento (70%), aplicada sem alteração à avaliação confirmatória; A é somente descritiva e deriva dos rótulos da partição avaliada. Empates de B seguem a ordem fixa do vocabulário `judge2`.

**Limite de execução:** esta documentação não autoriza rodar o executor RGC. Não execute o ATTRACTOR sobre casos de piloto, desenvolvimento ou avaliação confirmatória; não crie, complete ou rotule esses casos; não produza números de benchmark RGC PT-BR. Os testes do runner devem usar somente dados sintéticos claramente identificados dentro de `tests/`. O protocolo permanece **[PROPOSTO]** até a revisão do piloto humano 02 e uma decisão explícita separada de congelamento.

### Decisões metodológicas pendentes

> **Atualização editorial (2026-10-25):** o título e o bloco abaixo preservam o estado anterior à aprovação e são históricos. DEC-017–DEC-020 foram aprovadas pelo mantenedor em 2026-10-21 e formalizadas nas Emendas 7–10. As opções listadas abaixo não são decisões pendentes; o protocolo continua **[PROPOSTO]**, não congelado, e os portões humanos continuam abertos. Consulte `docs/eval/STATISTICS.md`, `docs/eval/RUNNER-RGC-v1.md` e `docs/STATUS.md` para o estado vigente.

As seguintes decisões continuam abertas e não podem ser resolvidas implicitamente pelo executor ou por um relatório:

- **DEC-017:** registro ausente versus `INVALID_PREDICTION`;
- **DEC-018:** escopo confirmatório de H1 (~90 casos ocultos versus outro escopo);
- **DEC-019:** bootstrap por caso versus bootstrap agrupado por artigo;
- **DEC-020:** operacionalização do limiar de concordância entre anotadores.

Cada item contém opções, prós/contras e recomendação, mas permanece pendente de decisão explícita do mantenedor. Se uma decisão alterar o pré-registro ou protocolo, deve ser incorporada por nota/emenda datada antes de qualquer avaliação confirmatória.

## Contratos e parâmetros

| Elemento | Regra de reprodutibilidade |
|---|---|
| Commit | Registrar o SHA completo. `unknown` é permitido apenas com `non_ci_run: true` em execução fora do CI. |
| Hashes | Calcular SHA-256 sobre os bytes finais de cada entrada/artefato; não substituir o hash por nome de arquivo ou URL. |
| Seed | Registrar o valor e o método que o usa; não alterar depois de observar resultados. |
| Partições RGC | Manter os arquivos públicos de desenvolvimento separados dos casos ocultos; nunca colocar o conjunto oculto no repositório público. |
| Baseline B | Derivar somente dos rótulos humanos da partição pública de desenvolvimento e registrar rótulos, contagens e hash antes da avaliação oculta. |
| Baseline A | Reportar apenas como referência descritiva da prevalência avaliada; não usar para H1. |
| Manifesto | Registrar os hashes e tamanhos dos artefatos finais, as suítes selecionadas e a procedência CI/não-CI. |
| Divergências | Preservar resultado negativo, inconclusivo ou erro; não remover casos nem alterar parâmetros para melhorar métricas. |

## Limites conhecidos

- Um hash identifica os bytes verificados; não demonstra que a fonte seja verdadeira, que a anotação seja correta ou que o artefato seja imune a adulteração em todos os ambientes.
- Um commit e uma seed fixos não bastam se dependências, entradas, parâmetros, fonte capturada ou versão da suíte forem diferentes.
- A reprodução de Golden v0/v0.1 não é avaliação confirmatória do RGC PT-BR.
- **Atualização editorial (2026-10-25):** a frase seguinte é um registro histórico anterior às aprovações DEC-017–DEC-020; essas decisões estão aprovadas, enquanto os gates humanos continuam pendentes.
- O runner RGC está proposto; as decisões DEC-017 a DEC-020 e o gate humano de piloto 02 permanecem pendentes.
- Não existe resultado de benchmark RGC PT-BR nesta etapa. Nenhuma métrica pode ser inferida deste capítulo.
- A ausência de um SHA de CI deve ser explícita no manifesto; não atribua a uma execução local a identidade de um commit não verificado.

## Evidências

- `scripts/reproduce.py`: verificações dos artefatos congelados e relatórios de reprodução.
- `src/ayorai_attractor/evaluation/report_manifest.py` e `tests/test_evaluation_report_manifest.py`: integridade dos manifestos e marcador `non_ci_run`.
- `tests/test_golden_digest.py` e `tests/test_golden_git_sha.py`: hashes e identidade do commit para Golden.
- `evals/ptbr/rgc_eval.py`, `docs/eval/RUNNER-RGC-v1.md` e `docs/eval/STATISTICS.md`: contrato proposto do runner e estatísticas.
- `docs/eval/PREREGISTRATION-RGC-v1.md`, `docs/eval/PROTOCOL-GOLDEN-V1.md` e `docs/DECISIONS-PENDING.md`: gates, emendas e decisões ainda pendentes.

## Ver também

- [04 — API HTTP e contratos](04-api.md)
- [05 — Operação e execução](05-operacao.md)
- [06 — Segurança](06-seguranca.md)
- [Pré-registro RGC](../eval/PREREGISTRATION-RGC-v1.md)
- [Protocolo Golden v1](../eval/PROTOCOL-GOLDEN-V1.md)
- [Executor RGC](../eval/RUNNER-RGC-v1.md)
- [Estatísticas](../eval/STATISTICS.md)
- [Guia de fontes](../annotation/SOURCES.md)
