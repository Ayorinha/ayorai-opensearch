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
