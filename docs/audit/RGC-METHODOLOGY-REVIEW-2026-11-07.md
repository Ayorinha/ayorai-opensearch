# Revisão metodológica de continuidade — benchmark RGC PT-BR

**Data do retrato:** 2026-11-07 (horário local de São Paulo)  
**Base Git consultada:** `main` em `f8895caab6f3d81fdfea0eaffa91a7a255477d36`  
**Natureza:** revisão documental interna de consistência e prontidão metodológica. Não é revisão humana independente, parecer jurídico, validação institucional, resultado experimental ou aprovação de congelamento.

## 1. Estado confirmado do repositório

### `main`

- Branch padrão protegida; SHA consultado: [`f8895ca`](https://github.com/Ayorinha/ayorai-opensearch/commit/f8895caab6f3d81fdfea0eaffa91a7a255477d36), commit da PR #489.
- Os 13 check runs associados a esse SHA terminaram com `success`: testes Python 3.11/3.12/3.13, build, typecheck não bloqueante, golden regression/lint/smoke, namespace compatibility, workflow lint, judge regression, analyze e security. [Execução CI](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/42433845495) · [Security](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/42433845496) · [Analyze](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/42433845516).
- O endpoint legado de commit statuses retornou zero registros e estado `pending`; isso não contradiz os 13 check runs concluídos. A evidência de CI usada aqui é a lista de check runs, não o campo legado vazio.
- Mudanças recentes observadas na ponta de `main`: #489 (roadmap v0.8), #485 (DOI v0.7.0), #484 (preparação v0.7.0), #483 (README/resultados DEV), #482 (resultado agregado DEV Calibration V2), #481 (correção do agregador) e #480 (workflow DEV completo). Essas mudanças não alteram o gate científico do RGC.

### PR #269 e linhagem já concluída

- [PR #269](https://github.com/Ayorinha/ayorai-opensearch/pull/269) está **fechada sem merge**, ainda marcada Draft no registro consultado. Head: `f161c14b1bf196dd111e176ac04907d6eaa7f1f3`; base histórica: `71e682c97bb12788ef95e799d889a2454bfdd0eb`.
- O diff da #269 continha `docs/ARCHITECTURE.md` e `docs/eval/METHODOLOGY-REVIEW-RGC-PTBR-2026-10-18.md`; a alteração incidental de arquitetura foi a razão registrada para substituí-la.
- Conversa: três comentários do mantenedor. Revisões submetidas: zero. Threads inline: zero.
- Os sete workflows do head da #269 terminaram com sucesso: [CI](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/39241516692), [CodeQL](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/39241516946), [Security](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/39241516787), [Dependency Review](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/39241516590), [API Contract Guard](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/39241516739), [Schemathesis](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/39241517114) e [Golden r2 Migration](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/39241516646). Checks verdes não transformam a PR fechada em mergeada nem constituem validação científica.
- A #269 foi substituída pela #272; a #272, por sua vez, foi substituída pela [#273](https://github.com/Ayorinha/ayorai-opensearch/pull/273), que foi mesclada e incorporou somente a revisão metodológica. A [#275](https://github.com/Ayorinha/ayorai-opensearch/pull/275) também foi mesclada, alterando somente a ficha em branco do piloto 02. Nenhuma dessas tarefas precisa ser reiniciada.

### Mudanças documentais recentes

- [PR #468](https://github.com/Ayorinha/ayorai-opensearch/pull/468), merge commit `b358b4de532022fd4b3009e6bd3462d345103a0b`, registrou DEC-021, DEC-022 e DEC-023 em `docs/DECISIONS-PENDING.md`. O diff foi somente documental; não alterou executor, pré-registro ou protocolo.
- [PR #490](https://github.com/Ayorinha/ayorai-opensearch/pull/490) permanece Draft e independente do RGC; altera apenas o radar tecnológico e o roadmap v0.8. O head consultado `133f337aeedde240c667b7a3c9d1c2abffee4135` tem sete workflows concluídos com sucesso e não apresenta comentários, reviews ou threads inline. Não foi alterada nesta tarefa.
- As PRs #486, #487 e #488 também permanecem abertas em Draft no retrato consultado. Não foram modificadas.

## 2. Estado científico e gates RGC

- `PREREGISTRATION-RGC-v1.md` permanece **[PROPOSTO]**; `PROTOCOL-GOLDEN-V1.md` permanece em revisão pós-piloto; `RUNNER-RGC-v1.md` permanece **[PROPOSTO]**.
- `docs/eval/PROTOCOL-FREEZE.json` não existe na `main` consultada. O executor falha fechado sem manifesto de congelamento e evidências de aprovação das anotações.
- A ficha pública `PILOT-RGC-02-WORKSHEET.md` está em branco e proíbe consulta a IA e execução do ATTRACTOR durante o piloto.
- Não foram encontrados casos reais do piloto 02 ou do conjunto definitivo nesta revisão. Nenhum caso foi criado, completado ou rotulado; o sistema não foi executado sobre casos RGC; nenhuma métrica RGC foi calculada.
- Permanecem pendentes: piloto 02 manual sem IA e sem execução do sistema; segunda anotação humana independente; divergências/adjudicação documentadas; proveniência e vigência por dispositivo; isolamento real da partição oculta; revisão humana independente F-01; e decisão separada do mantenedor sobre congelamento.
- A meta de 300 casos não é quota. A partição oculta proposta de aproximadamente 90 casos não garante número suficiente de componentes independentes.

## 3. Decisões metodológicas preservadas

As decisões aprovadas anteriores permanecem como registradas:

- **DEC-014:** Baseline B é derivada somente dos rótulos humanos da partição pública de desenvolvimento e aplicada sem alteração à avaliação; Baseline A é apenas descritiva.
- **DEC-017:** falha de integridade de registros interrompe a execução; predição presente inválida permanece no denominador como erro.
- **DEC-018:** H1 usa somente a partição oculta; a partição pública é descritiva/exploratória.
- **DEC-019:** `bootstrap_cluster_id` identifica a unidade inicial por artigo ou `bundle:`; bootstrap por caso é sensibilidade.
- **DEC-020:** Cohen's kappa não ponderado; gate pela estimativa pontual `κ ≥ 0,6`; reportar concordância observada, matriz e marginais; `RULE_GAP` fica fora do kappa.
- **DEC-021 (aprovada em 2026-11-07):** sign-flip bilateral por componente; enumeração completa para `K <= 20`, Monte Carlo de 10.000 sorteios para `K > 20`, seed `20261003`; McNemar por caso e Obuchowski (1998) somente como sensibilidades.
- **DEC-022 (aprovada em 2026-11-07):** IC95% percentil de kappa por bootstrap de componente; 10.000 reamostragens, seed `20261003`; indefinidas excluídas e contabilizadas; intervalo instável se >5%; gate pontual de 0,6 preservado.
- **DEC-023 (aprovada em 2026-11-07):** componentes conectados por qualquer artigo compartilhado em `cited_article_ids`, com transitividade; ID determinístico `component:` + IDs únicos ordenados; reportar unidades antes/depois e tamanhos.

## 4. Achados da revisão metodológica

### R-01 — Conflito entre DEC-021 e o critério confirmatório ainda escrito no pré-registro

**Evidência:** o §5 de `PREREGISTRATION-RGC-v1.md` ainda exige McNemar exato bilateral com (p<0,05) como condição de sucesso de H1. DEC-021 define o sign-flip por componente como teste confirmatório primário e relega McNemar à análise de sensibilidade. A própria aprovação de DEC-021 declara que não altera o pré-registro.

**Risco:** existem duas regras concorrentes para a condição inferencial de H1. Não é seguro executar nem declarar sucesso até uma emenda datada resolver a precedência e alinhar pré-registro, estatísticas, protocolo, executor e relatório.

**Estado:** pendente de emenda/decisão documental explícita. Nenhuma redação normativa foi alterada aqui.

### R-02 — DEC-022 conflita com a unidade de bootstrap ainda descrita em DEC-020/Emenda 10

**Evidência:** `PROTOCOL-GOLDEN-V1.md` e a seção DEC-020 de `STATISTICS.md` descrevem IC de kappa por bootstrap de casos. DEC-022 aprova bootstrap de componentes e preserva apenas o gate pontual de 0,6.

**Risco:** a ferramenta atual pode produzir um IC por caso que não corresponde à especificação aprovada mais recente.

**Estado:** especificação registrada em `STATISTICS.md` nesta PR; o protocolo e o executor continuam sem alteração. É necessária reconciliação datada antes de processar qualquer anotação humana como evidência final.

### R-03 — DEC-023 amplia a unidade além do `bootstrap_cluster_id` isolado

**Evidência:** DEC-019 mantém `bootstrap_cluster_id` por artigo/`bundle:`; DEC-023 forma componentes pela interseção de qualquer artigo citado, inclusive por conexão transitiva. Um caso que cita artigos secundários pode unir clusters que antes seriam separados.

**Risco:** usar diretamente `bootstrap_cluster_id` como unidade final ignora conexões transitivas e pode subestimar dependência. O tamanho do conjunto em casos não substitui o número de componentes.

**Estado:** pendente de implementação. A regra documental é registrada nesta PR; não se calcula número de componentes sem casos elegíveis.

### R-04 — O código atual ainda não implementa DEC-021 a DEC-023

**Evidência de código e testes em `main`:**
- `rgc_eval.py` calcula o bootstrap por `bootstrap_cluster_id` e valida `cited_article_ids`, mas não constrói componentes conectados nem contém o teste sign-flip.
- `rgc_agreement.py` amostra casos individualmente e publica `ci95_case_bootstrap`; não faz bootstrap de componente.
- `test_rgc_eval_runner.py` cobre o bootstrap por cluster de artigo e regras anteriores; `test_rgc_agreement.py` cobre bootstrap por caso. Não há testes de componentes transitivos, sign-flip ou kappa por componente.
- A PR #468 registrou as decisões, mas declarou expressamente que não implementou os métodos.

**Estado:** implementação não autorizada pela decisão registrada na #468 nem por esta tarefa. Qualquer implementação exige PR separada, testes sintéticos e autorização explícita; não executar sobre casos reais.

### R-05 — A hipótese de permutabilidade do sign-flip precisa ser tratada como hipótese

DEC-021 declara que sistema e Baseline B são permutáveis dentro de cada componente sob H0. A construção do grafo por artigo não prova essa permutabilidade nem independência entre componentes. O relatório deverá declarar a hipótese e não apresentar o p-valor como garantia mecânica de validade.

A estatística `T_obs = sum_k d_k` pondera implicitamente componentes pelo número de casos. Uma componente muito grande pode dominar o resultado; por isso, os tamanhos de todas as componentes e da maior componente são essenciais.

### R-06 — Baixo número de componentes pode tornar o critério inatingível

Com resolução mínima `2 / 2^K`, para `K < 6` não é possível obter `p < 0,05`. A partição oculta proposta (~90 casos) pode resultar em poucas componentes após a união transitiva. Como não há casos elegíveis, `K`, a distribuição de tamanhos e o poder efetivo são desconhecidos. Não reduzir o nível, trocar o teste ou fragmentar componentes para obter significância.

### R-07 — O bootstrap de kappa precisa explicitar detalhes operacionais

DEC-022 fixa 10.000 reamostragens, seed, exclusão de kappa indefinido e marcação de instabilidade acima de 5%, mas não detalha a convenção de quantis nem o sorteio operacional de componentes. O código atual usa bootstrap por caso e seleciona estatísticas de ordem sem interpolação. Antes da implementação, registrar a convenção de quantis e preservar a multiplicidade de componentes sorteados; publicar sempre número e proporção de réplicas válidas/indefinidas. O gate continua sendo a estimativa pontual, não o limite inferior do IC.

### R-08 — IDs canônicos e proveniência dos artigos são pré-condições

O executor atual exige, na partição oculta, `cited_article_ids` como lista não vazia, única e sem espaços externos, e confere a consistência do `bootstrap_cluster_id`. Ainda assim, a gramática canônica dos IDs e a evidência de que a lista contém todas as citações relevantes precisam ser auditáveis. A união de componentes não deve normalizar IDs de modo oportunista nem completar citações por inferência. Casos sem proveniência suficiente não podem entrar no cálculo.

### R-09 — Referência de Obuchowski verificada; escopo limitado

A referência aprovada corresponde a Nancy A. Obuchowski (1998), “On the comparison of correlated proportions for clustered data”, *Statistics in Medicine*, 17(13), 1495–1507, DOI [10.1002/(SICI)1097-0258(19980715)17:13<1495::AID-SIM863>3.0.CO;2-I](https://doi.org/10.1002/(SICI)1097-0258(19980715)17:13%3C1495::AID-SIM863%3E3.0.CO;2-I), PMID [9695194](https://pubmed.ncbi.nlm.nih.gov/9695194/). O método estende a comparação de proporções pareadas para dados agrupados. Sua presença no plano não transforma a análise de sensibilidade em teste confirmatório nem valida o benchmark.

### R-10 — Trechos históricos ainda podem induzir leitura errada

`PREREGISTRATION-RGC-v1.md` e `PROTOCOL-GOLDEN-V1.md` ainda preservam notas antigas que dizem que DEC-017/DEC-018 permaneciam pendentes, embora notas posteriores e os registros de aprovação indiquem que foram superadas. `STATISTICS.md` já tem aviso editorial explícito para o bloco histórico de DEC-018. Esta PR não reescreve documentos normativos protegidos; recomenda-se apenas uma futura limpeza editorial com avisos inequívocos, sem alterar o texto histórico ou a regra aprovada.

## 5. Escopo desta atualização documental

Esta PR atualiza somente `docs/eval/STATISTICS.md` e acrescenta este relatório. Não altera:

- Judge, regras, Golden v0/v0.1, fixtures ou thresholds;
- `PROTOCOL-GOLDEN-V1.md`, `PREREGISTRATION-RGC-v1.md`, `RUNNER-RGC-v1.md` ou `PROTOCOL-FREEZE.json`;
- manifestos, hashes, capturas de fontes ou qualquer arquivo de caso/rótulo;
- código, testes, workflows, releases ou tags.

Nenhum caso foi criado, completado ou rotulado por IA. O sistema não foi executado sobre o piloto nem sobre o benchmark. Nenhuma concordância, métrica RGC, p-valor ou IC real foi calculado. Esta revisão não é independente e não constitui validação externa.

## 6. Sequência segura a partir daqui

1. Manter o protocolo **[PROPOSTO]** e o executor bloqueado.
2. Resolver por emenda datada a divergência entre o critério de McNemar do pré-registro e o sign-flip aprovado em DEC-021; alinhar DEC-022/023 com DEC-019/020 nos documentos normativos.
3. Somente após autorização específica, implementar DEC-021–023 em PR separada, com testes exclusivamente sintéticos para união transitiva, sign-flip exato/Monte Carlo, resolução (K<6), bootstrap de kappa e tratamento de réplicas indefinidas.
4. Não produzir casos nem rótulos de piloto com IA. O piloto 02 continua humano, privado e sem execução do sistema.
5. Obter a segunda anotação humana independente, registrar divergências/adjudicação e concluir F-01.
6. Confirmar proveniência e isolamento da partição oculta antes de qualquer decisão de congelamento.
7. Exigir decisão explícita e separada do mantenedor para congelar o protocolo e, depois, autorizar eventual execução confirmatória.

**Conclusão:** a linhagem da PR #269 está encerrada e preservada; a revisão metodológica avançou para as decisões aprovadas em 2026-11-07. A principal pendência agora não é reiniciar a revisão antiga: é reconciliar formalmente DEC-021–DEC-023 com o pré-registro/protocolo e implementar os métodos somente após autorização. Até lá, não há base para executar o benchmark ou alegar resultado/validação externa.
