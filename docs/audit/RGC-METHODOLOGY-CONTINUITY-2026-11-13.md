# Continuidade da revisão metodológica — benchmark RGC PT-BR

**Data do retrato:** 2026-11-13  
**Base Git consultada:** `main` em `9833d24f35e419117412ca557c51f4869de47e21`  
**PR de implementação em análise:** [#532](https://github.com/Ayorinha/ayorai-opensearch/pull/532), Draft, head `0d92f37d29e36e475a5c88977438c69d7f07bb39`.  
**Natureza:** auditoria documental e de código, interna e não independente. Não é validação científica, parecer jurídico, aprovação de protocolo ou resultado experimental.

## 1. Estado científico preservado

- O pré-registro, o protocolo e o runner RGC permanecem **[PROPOSTO]**; não há manifesto de congelamento aprovado.
- A meta de aproximadamente 300 casos é uma meta condicionada à elegibilidade, não uma quota. A divisão planejada de aproximadamente 210 casos públicos e 90 ocultos não garante número suficiente de componentes independentes.
- O piloto 02 continua humano, privado e exploratório. A ficha versionada permanece em branco. A orientação proíbe assistência de IA na criação/rotulagem e proíbe executar ATTRACTOR/Judge sobre os casos.
- Não foram criados, completados ou rotulados casos do piloto ou do benchmark nesta revisão. Não foram processados casos reais, calculadas métricas RGC ou executados o ATTRACTOR/Judge sobre dados RGC.
- Permanecem necessários: piloto 02 humano, segunda anotação independente, registro/adjudicação das divergências, revisão humana independente F-01, evidência de proveniência e isolamento da partição oculta e decisão separada do mantenedor sobre eventual congelamento.

Fontes internas: `docs/eval/PREREGISTRATION-RGC-v1.md`, `docs/eval/PILOT-RGC-02-OPERATIONS.md`, `docs/eval/PILOT-RGC-02-WORKSHEET.md`, `docs/eval/RUNNER-RGC-v1.md` e `docs/STATUS.md`.

## 2. Bloqueio confirmado: duas identidades canônicas para DEC-023

**[FATO VERIFICADO]** O registro aprovado da DEC-023 em `docs/DECISIONS-PENDING.md` especifica:

- reunir IDs únicos de artigos por componente;
- ordenar lexicalmente e uni-los com `+`;
- formar o identificador como `component:` seguido dos IDs unidos por `+`.

Já `docs/eval/STATISTICS.md`, na seção que também se declara DEC-023, especifica outra identidade:

- serializar a lista lexicalmente ordenada em JSON compacto UTF-8, com Unicode NFC e `ensure_ascii=False`;
- calcular SHA-256 dessa serialização;
- usar `component:sha256:<digest>`;
- não usar concatenação com `+`, por ser ambígua.

A revisão documental de 2026-11-07 também descreve a identidade baseada em SHA-256. Portanto, o próprio repositório contém duas definições incompatíveis sob o mesmo número de decisão.

**[FATO VERIFICADO]** A implementação proposta na #532 usa a segunda definição: JSON compacto de IDs ordenados, SHA-256 e prefixo `component:sha256:`. O código não corresponde literalmente à identidade escrita no registro aprovado em `docs/DECISIONS-PENDING.md`.

**[CONCLUSÃO]** A #532 não deve ser integrada enquanto a identidade normativa não for resolvida. A correção não deve ser escolhida silenciosamente pelo implementador. É necessária uma emenda/decisão datada que estabeleça qual definição prevalece e reconcilie os documentos. Tecnicamente, JSON canônico + SHA-256 evita colisões de concatenação, mas adotá-lo exige corrigir explicitamente o registro da decisão aprovada; não basta a implementação já o utilizar.

Referências:
- `docs/DECISIONS-PENDING.md`, seção DEC-023.
- `docs/eval/STATISTICS.md`, seção “Unidade final de reamostragem e permutação — DEC-023”.
- `docs/audit/RGC-METHODOLOGY-REVIEW-2026-11-07.md`, seção de decisões aprovadas.
- [PR #532](https://github.com/Ayorinha/ayorai-opensearch/pull/532), `evals/ptbr/rgc_components.py`.

## 3. Outros conflitos normativos ainda abertos

1. **DEC-021 versus pré-registro:** DEC-021 define sign-flip por componente como teste confirmatório primário e McNemar como sensibilidade. O §5 de `PREREGISTRATION-RGC-v1.md` ainda apresenta McNemar como condição confirmatória de H1.
2. **DEC-022 versus protocolo/DEC-020:** a especificação aprovada passa o IC95% de kappa para bootstrap por componente; o protocolo e a redação anterior da DEC-020 ainda descrevem bootstrap por caso.
3. **DEC-023 versus DEC-019:** DEC-019 usa `bootstrap_cluster_id` por artigo/`bundle:`; DEC-023 agrega casos por qualquer artigo citado, com união transitiva. A unidade final não pode ser tratada como sinônimo do cluster inicial.
4. **Permutabilidade:** o sign-flip depende da permutabilidade sistema/Baseline B dentro de componente sob H0. A construção do grafo não prova essa hipótese nem independência entre componentes.
5. **Resolução:** para K < 6, a enumeração exata não alcança p < 0,05. A meta de 90 casos ocultos não resolve isso por si só; é necessário conhecer K após a anotação legítima, sem fabricar ou simular casos reais.

Esses conflitos já estão registrados na seção de alinhamento documental de `docs/eval/STATISTICS.md`. Não foram alterados o pré-registro, o protocolo, o runner ou as decisões aprovadas.

## 4. Revisão técnica limitada da proposta #532

**[FATO VERIFICADO]** No head consultado da #532:

- `build_article_components` constrói conexões transitivas por IDs compartilhados;
- rejeita IDs de artigo vazios, duplicados, com espaços periféricos ou não normalizados em NFC;
- ordena os IDs e calcula o hash JSON descrito acima;
- `exact_sign_flip` implementa enumeração exata para K ≤ 20 e PCG64/NumPy 2.3.3 para K > 20;
- `bootstrap_cohen_kappa_by_component` preserva multiplicidade dos componentes sorteados, exclui pares `RULE_GAP`, contabiliza réplicas indefinidas e marca instabilidade acima de 5%;
- os testes fornecidos usam dados sintéticos.

**[FATO VERIFICADO — LACUNA]** `build_article_components` só adiciona `bootstrap_cluster_id` a `original_cluster_count` quando o valor é uma string não vazia. Valores ausentes, vazios ou de tipo incorreto são silenciosamente ignorados. Como DEC-023 exige reportar as unidades anteriores à união e DEC-019 exige o campo nos casos ocultos elegíveis, a integração precisa definir uma precondição explícita ou reportar a contagem de valores ausentes/inválidos; não deve apresentar uma contagem parcial como completa.

**Limite:** esta leitura de código não executou testes, não acessou casos reais e não constitui aprovação da implementação. A PR continua Draft e fora da `main`.

## 5. Próximas decisões e gates

- Resolver formalmente a identidade canônica da DEC-023 antes de qualquer merge da #532.
- Reconciliar, por emendas datadas aprovadas, pré-registro, protocolo, estatísticas, runner, código e testes para DEC-021/022/023. Os documentos normativos protegidos permanecem inalterados nesta revisão.
- Manter o piloto 02 sob responsabilidade humana, privado, sem IA e sem execução do sistema.
- Obter a segunda anotação humana independente, adjudicação e revisão F-01.
- Confirmar proveniência e isolamento da partição oculta antes de qualquer decisão de congelamento.
- Exigir autorização explícita separada para congelamento e, posteriormente, para eventual execução confirmatória.

**Estado final:** protocolo **[PROPOSTO]**; nenhuma execução RGC; nenhum resultado ou validação externa alegado; #532 bloqueada pela divergência de identidade canônica e pelos alinhamentos normativos pendentes.


---

## Adendo de revalidação — 2026-11-13, após avanço da `main`

Este adendo atualiza a fotografia do repositório após a auditoria original. É documental: não altera decisões, protocolo, pré-registro, runner, executor, testes, Judge, Golden, manifestos, hashes, casos ou rótulos. Não autoriza implementação, execução, aprovação ou congelamento.

### 1. `main` e verificações

- HEAD confirmado: [`ec7b8243fb8b87c433950dfb269ada795e763e3c`](https://github.com/Ayorinha/ayorai-opensearch/commit/ec7b8243fb8b87c433950dfb269ada795e763e3c), commit de 2026-11-13 17:01:27 UTC, PR #520 (`actions/download-artifact` 8.0.2 nos quatro produtores DEV da Phase 1b).
- No SHA exato foram consultados **13 check-runs; 13/13 concluídos com `success`**. Incluem testes Python 3.11/3.12/3.13, build, Golden smoke/lint/regression, namespace compatibility, workflow lint, Judge regression, CodeQL/analyze e Security.
- A comparação entre a base original deste relatório (`9833d24f35e419117412ca557c51f4869de47e21`) e o HEAD atual mostra seis commits à frente e nenhum atrás. As mudanças desse intervalo estão em workflows, CHANGELOG, README, `docs/STATUS.md` e dois testes de governança de workflows. **Nenhum arquivo metodológico RGC, executor, ferramenta de concordância ou teste metodológico RGC foi alterado nesse intervalo.**
- Portanto, a análise metodológica abaixo continua aplicável ao conteúdo RGC da `main`. A branch desta auditoria permanece seis commits atrás da `main`; este adendo registra explicitamente essa diferença, sem afirmar sincronização de branch.

### 2. PR #269 e linhagem — estado confirmado

- [PR #269](https://github.com/Ayorinha/ayorai-opensearch/pull/269): **fechada sem merge**, fechada em 2026-10-19; o metadata ainda a marca como Draft. Head `f161c14b1bf196dd111e176ac04907d6eaa7f1f3`, cinco commits e dois arquivos no diff.
- A conversa contém três comentários do mantenedor; há **zero reviews submetidas e zero threads inline**.
- No head histórico da #269 foram consultados 20 check-runs: **19 `success`, 1 `skipped`** (`rgc-design-simulation`) e nenhuma falha. Esses resultados pertencem exclusivamente ao head histórico da PR, não à `main` atual.
- [PR #272](https://github.com/Ayorinha/ayorai-opensearch/pull/272) também foi fechada sem merge. A revisão metodológica foi incorporada pela [#273](https://github.com/Ayorinha/ayorai-opensearch/pull/273), merge commit `5719db48fc82c726671af7c9c7f7ef386d161edb`. A linhagem antiga está encerrada; não reiniciar a revisão já incorporada.

### 3. PRs metodológicas/documentais ainda abertas

- [#531](https://github.com/Ayorinha/ayorai-opensearch/pull/531): aberta, metadata atual `draft=false`; head `316ca507e4d0322909aaa3566849de3373d0e3ef`; diff de dois arquivos, ambos documentais (`docs/eval/STATISTICS.md` e o relatório de auditoria). Os 20/20 check-runs desse head terminaram em `success`. Há uma review `COMMENTED` do próprio mantenedor e nenhuma thread inline; isso não é revisão humana independente nem aprovação. A comparação com a `main` atual indica três commits próprios e nove commits atrás. A alteração proposta em `STATISTICS.md` corrige a identidade de componente para a redação literal da DEC-023 e deixa PRNG/versão/ordem/interpolação como detalhes pendentes de confirmação.
- [#532](https://github.com/Ayorinha/ayorai-opensearch/pull/532): aberta em Draft; head `0d92f37d29e36e475a5c88977438c69d7f07bb39`; quatro arquivos alterados, incluindo módulo e testes sintéticos de componentes, `pyproject.toml` e workflow de smoke. Os 22/22 check-runs desse head terminaram em `success`, inclusive `nli-dependency-smoke`. Há comentários e uma review `COMMENTED` do próprio mantenedor; não equivalem a revisão independente. A comparação com a `main` atual indica 17 commits próprios e nove commits atrás; o metadata informa `mergeable=false`. O módulo permanece fora do executor e da ferramenta de concordância. Checks verdes não resolvem os bloqueios normativos.
- [#539](https://github.com/Ayorinha/ayorai-opensearch/pull/539): aberta em Draft; antes deste adendo, head `631651084a321d5eed9cf44c87c413e833dba3ba`, um commit próprio e seis commits atrás da `main`. Os 20/20 check-runs desse head anterior terminaram em `success`; não havia comentários, reviews ou threads. **A atualização deste documento cria um novo head; os checks do head anterior não são transferíveis.** O novo SHA e seus checks devem ser consultados separadamente.

### 4. Revalidação metodológica

**DEC-021 — teste de H1.** O registro aprovado em `docs/DECISIONS-PENDING.md` fixa sign-flip bilateral por componente; enumeração completa para `K <= 20`; para `K > 20`, 10.000 sorteios, seed `20261003` e correção de Monte Carlo. McNemar e Obuchowski são sensibilidades, não testes primários. O registro decisório não fixa biblioteca/versão, PRNG ou ordem de consumo.

**DEC-022 — IC de kappa.** O registro aprovado fixa bootstrap percentil por componente, 10.000 reamostragens, seed `20261003`, contabilização de réplicas indefinidas, instabilidade acima de 5% e gate pontual `κ >= 0,6`. Não fixa biblioteca/versão, PRNG, ordem de consumo ou interpolação dos quantis.

**Detalhes operacionais sem aprovação explícita.** A versão atual de `docs/eval/STATISTICS.md` ainda apresenta NumPy 2.3.3/PCG64, ordenação de consumo e quantil linear como parâmetros fixados. Esses detalhes não aparecem como requisitos nas entradas aprovadas de DEC-021/022. A correção proposta na #531 os marca como pendentes, sem escolher silenciosamente uma implementação. Até decisão humana, não os tratar como requisitos aprovados.

**DEC-023 — identidade incompatível.** `docs/DECISIONS-PENDING.md` define o ID como `component:` seguido dos IDs únicos ordenados lexicalmente e unidos por `+`. A versão atual de `docs/eval/STATISTICS.md` descreve JSON canônico + SHA-256 + prefixo `component:sha256:`; o módulo da #532 implementa essa segunda forma. A #531 propõe alinhar a documentação à redação aprovada, mas a gramática ainda precisa de decisão humana: o helper da #532 aceita IDs contendo `+`, de modo que a concatenação literal pode ser ambígua. Não inventar escape, restrição de caracteres ou nova codificação nesta revisão.

**Conflito H1 ainda presente na `main`.** O §5 do pré-registro e o runner ainda descrevem McNemar como condição confirmatória; `evals/ptbr/rgc_eval.py` calcula McNemar e usa `mcnemar_p_below_0_05` em `h1_supported`. Isso diverge de DEC-021, que coloca sign-flip por componente no papel confirmatório e McNemar na sensibilidade. Nenhum documento normativo foi alterado.

**Conflito de concordância ainda presente na `main`.** A Emenda 10/DEC-020 e `evals/ptbr/rgc_agreement.py` ainda usam bootstrap por caso (`ci95_case_bootstrap`); DEC-022 aprova bootstrap por componente. A ferramenta e os testes existentes continuam cobrindo o método por caso. Não processar anotações humanas como evidência final sob essa especificação conflitante.

**Unidade transitiva ainda não integrada.** O executor principal continua usando `bootstrap_cluster_id` como unidade inicial, sem construir a união transitiva por todos os `cited_article_ids`. A #532 contém um helper isolado, mas não o integra ao executor/concordância. Além da divergência do ID, `build_article_components` só adiciona à contagem original os valores de `bootstrap_cluster_id` que sejam strings não vazias; ausentes, vazios ou de tipo incorreto são omitidos sem contagem separada ou erro. Antes de integração, a precondição de DEC-019 e o relatório obrigatório de DEC-023 precisam ser tratados sem apresentar uma contagem parcial como completa.

**Limites estatísticos.** Para `K < 6`, a resolução exata não permite `p < 0,05`; a meta de aproximadamente 90 casos ocultos não garante número suficiente de componentes. A permutabilidade sistema/Baseline B dentro de cada componente é hipótese metodológica, não consequência automática do algoritmo; a construção do grafo tampouco prova independência entre componentes.

### 5. Estado humano e salvaguardas

- Pré-registro, protocolo e runner continuam **[PROPOSTO]**; não há congelamento aprovado.
- Piloto 02 permanece humano, privado e exploratório, sem assistência de IA para criar/rotular e sem executar ATTRACTOR/Judge sobre os casos.
- Segunda anotação humana independente, registro/adjudicação de divergências, revisão humana independente F-01, proveniência por dispositivo e evidência de isolamento da partição oculta permanecem gates pendentes.
- Nesta revalidação não foram acessados casos privados, criados/completados/rotulados casos, executado o sistema ou calculadas métricas RGC.

### 6. Decisões humanas ainda necessárias

1. Resolver a gramática do ID de componente da DEC-023, inclusive o tratamento de `+` dentro de IDs, por decisão datada; não alterar unilateralmente a decisão.
2. Decidir se PRNG/biblioteca/versão/ordem de consumo e interpolação de quantis serão fixados além do que já consta em DEC-021/022.
3. Autorizar, por emendas datadas, a reconciliação de H1 no pré-registro/runner e do bootstrap de kappa no protocolo/ferramenta de concordância.
4. Autorizar separadamente qualquer implementação em branch/PR, limitada a fixtures sintéticas até nova autorização; nenhuma execução real decorre dessa autorização documental.
5. Concluir os gates humanos do piloto 02, segunda anotação, adjudicação, F-01, proveniência e isolamento antes de qualquer decisão separada sobre congelamento.

**Conclusão:** a revisão antiga da #269 não precisa ser reiniciada. A `main` atual passou nos 13 check-runs consultados, mas os conflitos metodológicos RGC permanecem. #531 é documental e propõe correções relevantes; #532 continua bloqueada por divergência com DEC-023 e reconciliação normativa pendente; #539 recebe apenas esta atualização de continuidade. Nenhuma PR foi aprovada ou mesclada, o protocolo não foi congelado, nenhum caso foi criado/rotulado por IA, nenhum piloto foi executado e nenhuma validação externa é alegada.
