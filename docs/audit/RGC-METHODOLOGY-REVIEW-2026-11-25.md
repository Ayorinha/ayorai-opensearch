# Revisão metodológica de continuidade — benchmark RGC PT-BR (2026-11-25)

Revisão por ferramenta automatizada, publicada pelo mantenedor.

**Data do retrato:** 2026-11-25  
**Base Git:** `main` @ `3932d171fa5b4554684ec247555d3eaa8081e568`  
**Natureza:** revisão documental e estática de consistência entre decisões, pré-registro, protocolo, estatísticas, especificação do executor, implementação e testes sintéticos. Não é revisão humana independente, parecer jurídico, validação institucional, resultado experimental nem aprovação de congelamento.

## 1. Escopo e salvaguardas

Esta revisão retoma a linhagem já concluída da PR #269; não reinicia seus trabalhos. O objetivo é registrar o estado posterior às decisões DEC-021 a DEC-027 e às implementações integradas até `rgc-eval/0.14.0`.

Foram consultados metadados GitHub, documentos normativos e de apoio, especificação do executor, código e testes automatizados. A ficha consultada do Piloto 02 é o template público em branco. Não foram abertos arquivos de casos reais, anotações humanas, partições DEV/oculta ou conteúdo do corpus capturado.

Não foram executados testes locais, workflows de avaliação/benchmark, o Judge, o ATTRACTOR ou qualquer comando do executor. A CI padrão da PR é acionada automaticamente e seus checks são acompanhados separadamente. Nenhum caso foi criado, visto, completado ou rotulado; nenhuma anotação foi processada; nenhum K, kappa, intervalo, p-valor ou métrica real foi calculado.

Permanecem fora do escopo: alterações em Judge, Golden, manifests, hashes, fontes capturadas, pré-registro, protocolo normativo, decisões aprovadas e dados científicos; execução do sistema sobre o piloto ou benchmark; aprovação ou congelamento do protocolo.

## 2. Estado Git confirmado e linhagem

### `main`

- `main` está protegida e aponta para `3932d171fa5b4554684ec247555d3eaa8081e568`, commit de 2026-11-22 que integrou a PR #634 (P2).
- O ruleset `Protecao-main-ATTRACTOR` (ID `24996139`) foi consultado diretamente e está `active` no branch padrão. Exige PR, bloqueia deleção e non-fast-forward e exige os checks `test (3.11)`, `test (3.12)`, `test (3.13)`, `golden-regression`, `judge-regression` e `security`. A regra registra zero aprovações obrigatórias (configuração deliberada para o mantenedor único) e `current_user_can_bypass=never`, sem atores de bypass.
- Os 18 check runs associados a esse SHA estão concluídos: **18 success, 0 skipped, 0 falhas**. Isso é evidência de CI de engenharia, não validação científica RGC.
- A página atual de `docs/STATUS.md` ainda identifica a base anterior `a91da0f`. A PR #642, em Draft, atualiza o status para P3/A1 e não é uma continuação da revisão metodológica RGC; este documento não altera aquele arquivo.

### PR #269 e substituições

- [PR #269](https://github.com/Ayorinha/ayorai-opensearch/pull/269): fechada em 2026-10-19, **sem merge**, ainda registrada como Draft. Head `f161c14b1bf196dd111e176ac04907d6eaa7f1f3`; base histórica `71e682c97bb12788ef95e799d889a2454bfdd0eb`.
- O diff da #269 tinha dois arquivos: `docs/ARCHITECTURE.md` (alteração incidental) e `docs/eval/METHODOLOGY-REVIEW-RGC-PTBR-2026-10-18.md`. A conversa tem três comentários do mantenedor; não há reviews submetidas nem threads inline.
- No head da #269, os 20 check runs terminaram: **19 success e 1 skipped** (`rgc-design-simulation`); nenhum falhou. O endpoint legado de commit statuses não tinha registros, o que não invalida os check runs.
- A #269 foi substituída pela [#272](https://github.com/Ayorinha/ayorai-opensearch/pull/272), também fechada sem merge, e depois pela [#273](https://github.com/Ayorinha/ayorai-opensearch/pull/273). A #273 foi mesclada em 2026-10-20; o merge commit [`5719db4`](https://github.com/Ayorinha/ayorai-opensearch/commit/5719db48fc82c726671af7c9c7f7ef386d161edb) alterou somente `docs/eval/METHODOLOGY-REVIEW-RGC-PTBR-2026-10-18.md`. Seus checks foram 19 success e 1 skipped. A revisão inicial está, portanto, preservada e concluída.

### Continuidade metodológica já integrada

- [#491](https://github.com/Ayorinha/ayorai-opensearch/pull/491), merge commit [`f8d4648`](https://github.com/Ayorinha/ayorai-opensearch/commit/f8d464841fc75dee68bb39217379a5d8550d1f71): adicionou a revisão de continuidade de 2026-11-07 e atualizou `STATISTICS.md`. O head teve 20/20 checks success. A review registrada foi COMMENTED, não APPROVED; não substitui F-01 nem revisão humana independente.
- [#598](https://github.com/Ayorinha/ayorai-opensearch/pull/598), merge commit `8b24ae8`: corrigiu o changelog da linha RGC e removeu de `STATISTICS.md` uma nota de estado já superada.
- [#600](https://github.com/Ayorinha/ayorai-opensearch/pull/600), merge commit `870ad5f`: implementou o IC de Cohen's kappa por componente (DEC-022), preservando o bootstrap por caso como sensibilidade.
- [#605](https://github.com/Ayorinha/ayorai-opensearch/pull/605), merge commit `221f82e`: tratou os dois comentários não bloqueantes da revisão da #600, acrescentou o texto integral proposto para a Emenda 12 no protocolo e um teste para componente composto inteiramente por pares `RULE_GAP`. A definição de K nesse texto foi identificada como redação nova que ainda requer confirmação explícita do mantenedor.
- [#609](https://github.com/Ayorinha/ayorai-opensearch/pull/609), merge commit `50ed1ce`: avançou o executor para `rgc-eval/0.14.0` e exclui da adjudicação trechos que o corpus marcar explicitamente como superados por retificação.
- [#610](https://github.com/Ayorinha/ayorai-opensearch/pull/610), merge commit `7ab841d`: alinhou o guia de anotação à Emenda 4 e saneou caminhos internos nos relatórios F1.2.

As alterações acima já estão na linhagem de `main`; não devem ser repetidas. As PRs abertas #635 e #636 são do trabalho P3/A1 de isolamento/integridade de artefatos DEV, não da avaliação RGC PT-BR.

## 3. Coerência entre decisões, documentos e implementação

| Tema | Regra vigente | Evidência estática encontrada | Avaliação |
|---|---|---|---|
| Baseline | DEC-014: B deriva somente dos rótulos humanos da partição pública de desenvolvimento; A é descritiva/oráculo na partição avaliada. | `rgc_eval.py` deriva B dos rótulos de desenvolvimento e não usa A para H1. | Coerente no código e na Emenda 6; a redação original do pré-registro permanece como histórico e deve ser lida com as emendas. |
| Partição confirmatória | DEC-018: H1 somente na partição oculta; desenvolvimento é descritivo/exploratório. | Runner exige declaração de partição e não apresenta H1 como testada em `development`; o protocolo exige isolamento real. | Controle implementado, mas a declaração do CLI não prova por si só que o arquivo é realmente a partição oculta. |
| Teste de H1 | DEC-021/DEC-027: sign-flip bilateral por componente; enumeração para K ≤ 20 e Monte Carlo com 10.000 sorteios para K > 20. McNemar e Obuchowski são sensibilidades. | `rgc_components.py` implementa o sign-flip; os testes sintéticos cobrem enumeração, Monte Carlo, simetria, ordenação e resolução por componentes informativos. | Coerente com DEC-027 e Emenda 11 do pré-registro. A Emenda 11 ainda falta no protocolo. |
| Resolução de H1 | D7 exige K ≥ 6 no inventário antes dos vereditos; K′ conta componentes com diferença não nula e determina a resolução efetiva. | `rgc_gate.py` calcula K a partir de `case_id` e `cited_article_ids`; testes cobrem K′ < 6. | K ≥ 6 é necessário, não suficiente. Sem inventário real não se conhece K, K′, a distribuição dos tamanhos nem a precisão possível. |
| IC de acurácia | DEC-027 D5: bootstrap primário por componente; cluster de artigo e caso são sensibilidades. | `bootstrap_metrics_by_component` usa RGC-PRNG-1, 10.000 réplicas e preserva a multiplicidade dos componentes sorteados. | Coerente na implementação e em `STATISTICS.md`; o protocolo ainda não recebeu a Emenda 11. |
| Concordância | DEC-020/022: Cohen's kappa não ponderado; gate pontual κ ≥ 0,6; IC por componente primário; caso como sensibilidade; pares RULE_GAP excluídos. | `rgc_agreement.py` vincula o arquivo de casos por SHA-256, deriva componentes por citações e publica ICs por componente e por caso. Testes sintéticos cobrem exclusões e réplicas indefinidas. | Cálculo implementado. A definição operacional de K após excluir componentes inteiramente RULE_GAP está no texto proposto da Emenda 12 e ainda requer decisão do mantenedor. |
| Componentes e IDs | DEC-023/DEC-027: conexão transitiva por qualquer artigo citado; IDs canônicos com gramática D1 e formato reversível `component:`. | `rgc_components.py` e `rgc_ids.py` implementam união transitiva e validação; testes cobrem transitividade, ordem de entrada e entradas inválidas. | Coerente em código e estatísticas; a completude das citações continua sendo responsabilidade de curadoria humana. |
| Reprodutibilidade | DEC-027 D2/D3: RGC-PRNG-1, seed 20261003, fluxos separados e quantil tipo 7 definido por fórmula. | `rgc_random.py` é usado pelo executor e pela concordância; os testes de referência cobrem vetores e rejeição. | Especificação e testes sintéticos coerentes. O PRNG é para reprodutibilidade estatística, não para segurança criptográfica. |
| Entrada e saída inválida | DEC-017: registro/label ausente, duplicado ou inconsistente interrompe; predição presente inválida vira `INVALID_PREDICTION`, permanece no denominador e conta como erro. | Runner separa falha de integridade de entrada de saída inválida por caso. | Coerente com a emenda e com `STATISTICS.md`. |
| Retificações | DEC-011/Emenda 4: texto superado não é evidência. | Desde #609, `superseded_spans` pode excluir trechos superados antes da adjudicação; o schema valida intervalos e referência ao texto vigente. | A capacidade está implementada. A PR #609 declara que o corpus existente não foi alterado para marcar esses intervalos; cobertura real depende de curadoria humana e não foi auditada aqui. |
| Gate de execução | Protocolo congelado, manifesto hash-bound, aprovação humana das anotações e adjudicação são pré-condições. | `rgc_eval.py` exige `PROTOCOL-FREEZE.json`, hashes e evidência de aprovação; o arquivo não existe em `main`. | Falha fechada: nenhuma execução confirmatória está habilitada no estado atual. |

### Evidência sintética consultada

Os arquivos de teste identificam explicitamente dados sintéticos: `tests/test_rgc_components.py`, `tests/test_rgc_agreement.py`, `tests/test_rgc_eval_runner.py` e `tests/test_rgc_rectification_properties.py`. Eles cobrem contratos algorítmicos, integridade, casos-limite e regressões. Não são amostras do RGC, não demonstram validade dos rótulos, independência entre anotadores, representatividade da amostra nem desempenho do sistema.

## 4. Lacuna normativa ainda aberta

O estado documental é o principal bloqueio remanescente de consistência:

1. `PREREGISTRATION-RGC-v1.md` contém a Emenda 11 (DEC-027 D4/D5), que substitui o McNemar primário pelo sign-flip por componente. O §5 original continua visível como histórico e precisa ser lido com a Emenda 11. A Emenda 12 de IC de kappa por componente ainda não foi inserida no pré-registro.
2. `PROTOCOL-GOLDEN-V1.md` termina na Emenda 10. Portanto, ainda descreve o bootstrap por caso para kappa e não contém as Emendas 11 e 12 que alinham o protocolo às decisões e à implementação atuais.
3. `STATISTICS.md`, `ANNOTATOR-AGREEMENT.md`, `RUNNER-RGC-v1.md` e o código já descrevem os métodos atualizados. O arquivo `AMENDMENT-PROPOSAL-2026-11-21-DEC-022.md` contém as redações propostas para Emenda 12 no pré-registro e Emendas 11/12 no protocolo.
4. A Emenda 12 proposta define K para o bootstrap de kappa como o número de componentes com pelo menos um par elegível após excluir pares RULE_GAP. O teste correspondente já fixa o comportamento. Contudo, essa definição é uma clarificação metodológica nova, não uma transcrição literal de DEC-022; a própria proposta a marca como dependente de confirmação explícita do mantenedor.
5. Os campos de data `AAAA-MM-DD` são placeholders. Nenhuma emenda foi inserida nesta tarefa.

**Não editar os dois documentos protegidos nem tratar a proposta como aprovada.** A inserção das emendas exige decisão explícita do mantenedor sobre a redação nova de K e autorização específica para editar os arquivos protegidos.

## 5. Gates humanos e limitações científicas

- **Piloto 02:** permanece trabalho humano, privado e sem IA. O guia operacional exige cópia local privada da ficha em branco, proíbe assistentes/modelos e execução do ATTRACTOR/Judge, determina descarte dos casos após a revisão e preservação apenas dos achados metodológicos agregados.
- **Segunda anotação:** deve ser produzida por outra pessoa, sem acesso aos rótulos da primeira. O cálculo de kappa só ocorre depois que os dois arquivos humanos independentes existirem. Integridade de hashes não prova a identidade nem a independência real das pessoas; isso requer atestação humana preservada fora do repositório público.
- **Adjudicação:** divergências devem ser justificadas contra fonte primária e registradas caso a caso em material privado, sem enviar conteúdo dos casos a chats, issues ou PRs.
- **F-01:** revisão humana independente continua pendente. Reviews COMMENTED por ferramenta e checks verdes não a substituem.
- **Proveniência e vigência:** cada dispositivo e retificação precisa de fonte primária e trilha verificável. O executor não pode provar que a lista de citações está completa nem que o inventário de casos é o universo elegível.
- **Inventário prévio:** D7 exige K ≥ 6 antes da anotação de veredito. O script verifica a estrutura recebida, mas a completude do inventário precisa de atestação humana contra a fonte de cadastro/proveniência. Nenhum K real foi calculado.
- **Dependência estatística:** o sign-flip pressupõe permutabilidade entre sistema e Baseline B dentro de cada componente sob H0; a construção do grafo não prova essa hipótese nem independência entre componentes. Tamanhos de todos os componentes e do maior componente devem ser reportados. Um componente grande pode dominar a soma de diferenças.
- **Amostra:** 300 casos é meta, não quota. Aproximadamente 90 casos ocultos não garantem K suficiente, cobertura por classe ou precisão dos intervalos. Não fabricar casos para preencher categorias.
- **IC da acurácia balanceada (métrica secundária):** `STATISTICS.md` define que, em cada réplica bootstrap, a média de recall considera apenas os rótulos de referência presentes naquela réplica; classes ausentes são omitidas. Assim, o conjunto de classes que compõe a acurácia balanceada pode variar entre réplicas, especialmente se houver classes raras na partição oculta (~90 casos). A regra está documentada e não é, por si só, um defeito confirmado; é uma ressalva de interpretação. Diagnóstico documental sugerido (não aprovado como novo gate): reportar suportes por classe na amostra completa e, se o relatório permitir sem alterar o estimador, a frequência com que cada classe fica ausente nas réplicas. Isso qualifica a métrica secundária e não altera o teste primário de H1, baseado em acurácia.
- **Retificação:** o suporte a `superseded_spans` não substitui a identificação humana dos trechos e atos vigentes. A cobertura do corpus não foi examinada nesta revisão.

A ausência de artefatos humanos no repositório não prova que nenhuma atividade tenha ocorrido fora dele; significa apenas que não há evidência pública suficiente para declarar esses gates concluídos.

## 6. Sequência segura recomendada

1. Manter pré-registro e protocolo **[PROPOSTO]**, sem congelamento e sem execução.
2. O mantenedor decide explicitamente se aprova a definição de K da Emenda 12 (componentes com pelo menos um par elegível após exclusões RULE_GAP) ou fornece outra redação.
3. Após essa decisão, o mantenedor autoriza separadamente a inserção das Emendas 11/12 no protocolo e da Emenda 12 no pré-registro, com datas efetivas e sem reescrever o histórico.
4. Pessoas realizam o piloto 02 em ambiente privado, sem IA e sem executar o sistema; descartam os casos e registram apenas achados metodológicos agregados.
5. Duas pessoas distintas produzem anotações independentes do conjunto definitivo somente depois dos gates de protocolo; divergências e adjudicação são documentadas em ambiente privado. A revisão F-01 deve ser humana e independente.
6. Responsáveis humanos atestam proveniência, vigência, completude do inventário, isolamento da partição oculta e identidade independente dos anotadores. O gate D7 é verificado antes de qualquer rótulo de veredito.
7. Só então o mantenedor decide, em atos separados, congelamento do protocolo e eventual autorização de execução única. Checks verdes não substituem nenhuma dessas decisões.

## 7. Ações não realizadas

- Nenhum arquivo protegido foi alterado.
- Nenhuma branch, PR, issue, aprovação ou merge foi usado para alterar o estado científico.
- Nenhum workflow ou teste foi disparado nesta revisão.
- Nenhum caso, anotação, fonte capturada, partição ou rótulo real foi aberto ou modificado.
- Nenhuma execução do ATTRACTOR/Judge ocorreu sobre o piloto ou benchmark.
- Nenhum resultado RGC, validação externa, parceria, certificação ou endosso é reivindicado.

## Conclusão

A linhagem iniciada pela #269 está concluída e não deve ser reiniciada. A engenharia posterior implementou os métodos DEC-021 a DEC-027 e elevou o runner a `rgc-eval/0.14.0`, com testes sintéticos e gates de falha fechada. O bloqueio atual não é falta de reiniciar a implementação: é alinhar os documentos normativos protegidos às decisões já aprovadas, resolver a clarificação nova de K para a Emenda 12 e concluir os gates humanos de anotação, proveniência, revisão independente e isolamento.

**Estado final desta revisão:** documentação de continuidade preparada; protocolo RGC permanece **[PROPOSTO]**, não congelado; nenhuma execução ou validação científica foi realizada.
