# Checkpoint metodológico — benchmark RGC PT-BR (2026-11-17)

**Base consultada:** `main` @ `73bf91cd7175bdf18edbeffa661ef12a5ddf7f56` ([commit](https://github.com/Ayorinha/ayorai-opensearch/commit/73bf91cd7175bdf18edbeffa661ef12a5ddf7f56)).
**Natureza:** revisão documental automatizada, interna e não independente. Não é validação científica, parecer jurídico, revisão externa, aprovação ou congelamento do protocolo.

## 1. Escopo e linhagem da revisão

- [PR #269](https://github.com/Ayorinha/ayorai-opensearch/pull/269) está fechada **sem merge**. O registro histórico identifica o head `f161c14b1bf196dd111e176ac04907d6eaa7f1f3`; os sete workflows desse head foram consultados e terminaram `success`. O endpoint legado de status não retornou registros.
- A conversa da #269 tem três comentários; não há reviews submetidas nem threads inline. Seu diff original incluía uma alteração incidental em `docs/ARCHITECTURE.md`, motivo registrado para a substituição.
- A #269 foi substituída pela #272, também fechada sem merge, e depois pela [#273](https://github.com/Ayorinha/ayorai-opensearch/pull/273), que foi integrada. A revisão metodológica incorporada não deve ser reiniciada.
- [PR #539](https://github.com/Ayorinha/ayorai-opensearch/pull/539) continua Draft, com head `5c27ed57d98fecde57924f934b9075edf880657c` e base histórica `9833d24f35e419117412ca557c51f4869de47e21`. A comparação com a main consultada confirmou **118 commits atrás e 3 à frente** (branches divergentes); GitHub reportou `mergeable=false`. Os sete workflows no head consultado passaram, mas esses checks não tornam a branch atualizada nem pronta para integração. Este checkpoint atualiza a evidência, não modifica nem fecha a #539.

## 2. Estado científico preservado

- O protocolo RGC PT-BR permanece **[PROPOSTO]**, sem congelamento e sem autorização de execução.
- Nenhum caso do Piloto 02 ou do conjunto definitivo foi criado, completado ou rotulado nesta revisão; nenhum arquivo de anotação humana real foi processado; o sistema/runner não foi executado sobre casos RGC; nenhuma métrica RGC foi produzida.
- Piloto 02, segunda anotação humana independente, adjudicação, revisão humana independente F-01, proveniência/vigência por dispositivo, isolamento real da partição oculta e decisão explícita sobre congelamento continuam gates humanos.
- Checks sintéticos não equivalem a validação científica independente ou externa.

## 3. Achados metodológicos revalidados

### M-12 — Identidade de componente DEC-023 inconsistente

**FATO VERIFICADO:** `docs/DECISIONS-PENDING.md`, DEC-023, define `component:` seguido dos IDs únicos de artigo ordenados lexicalmente e unidos por `+`. Já `docs/eval/STATISTICS.md` descreve JSON canônico UTF-8 e SHA-256, com prefixo `component:sha256:`, e proíbe a concatenação.

**Bloqueio:** são duas identidades incompatíveis atribuídas à mesma decisão aprovada. Não escolher uma no código ou na documentação por inferência. É necessária decisão/emenda datada explícita do mantenedor, seguida de reconciliação. A auditoria #539 já registra o problema, mas sua branch está desatualizada e não mergeável no retrato atual.

### M-13 — IC de kappa por componente ainda não reconciliado

DEC-022 aprova bootstrap de Cohen's kappa por componente. A Emenda 10 do `PROTOCOL-GOLDEN-V1.md` ainda especifica bootstrap por caso. `STATISTICS.md` registra a especificação por componente, mas também declara que `rgc_agreement.py` permanece com bootstrap por caso e que não há testes para o bootstrap por componente.

**Bloqueio:** protocolar a emenda/reconciliação antes de usar a ferramenta de concordância para o gate vigente. Nenhum kappa humano foi calculado neste checkpoint.

### M-14 — DEC-021/DEC-027 e implementação estatística incompleta

A Emenda 11 do pré-registro incorpora o sign-flip bilateral por componente como teste primário de H1 e o IC de acurácia por componente; McNemar e bootstrap por artigo/caso ficam como sensibilidades. Contudo:

- o protocolo ainda contém a Emenda 9 (bootstrap por artigo como primário) e a Emenda 10 (kappa por caso), sem uma emenda correspondente para reconciliar DEC-021/022/023;
- `STATISTICS.md` declara que o executor não constrói componentes conectados nem implementa sign-flip, e a ferramenta de concordância não implementa bootstrap de kappa por componente;
- a [PR #577](https://github.com/Ayorinha/ayorai-opensearch/pull/577) trata da resolução informativa de H1 (`K'`) e não é a implementação completa do teste sign-flip. O head atual `e61b66a0f9757f7f25b26d84dec93c550c5d4ce` não tem workflow runs retornados; resultados de head anterior não são transferíveis;
- a [PR #576](https://github.com/Ayorinha/ayorai-opensearch/pull/576) vincula parsing, métricas de concordância e hashes ao mesmo snapshot de bytes, mas não implementa DEC-022; seus oito workflows no head `2a24e864368db508cc95a25db78aa676c3393af0` passaram;
- a [PR #580](https://github.com/Ayorinha/ayorai-opensearch/pull/580) fecha a proveniência E5 com snapshots imutáveis, validações e publicação atômica sem sobrescrita; seus oito workflows no head `335136bbd8f773824c29ab32abae8c9e8ffbe92c` passaram. É uma melhoria de integridade de entradas, não implementação estatística nem resultado de benchmark. Permanece Draft e requer revisão humana independente.

### M-15 — Gate de inventário D7 ainda sem evidência

DEC-027 D7 exige `K ≥ 6` no inventário de componentes calculado antes da anotação de veredito. Nenhum inventário de casos elegíveis existe neste checkpoint; a regra não foi demonstrada por dados. A resolução informativa `K'` após os resultados, tratada pela #577, é distinta do gate de inventário pré-anotação. Não simular casos reais nem inferir que a meta de 300 (ou 90 ocultos) garante unidades suficientes.

### Item resolvido — baseline A/B

A Emenda 6 do pré-registro e DEC-014 definem B como baseline primária derivada somente dos rótulos humanos da partição pública de desenvolvimento, aplicada sem alteração; A é descritiva/oráculo da prevalência observada. M-11 está resolvido quanto à definição e não deve ser reaberto sem nova evidência.

## 4. Checks e limites de evidência (heads consultados)

- #575: 7/7 workflows `success` no head `f595b095f532f68a6d36c3b83b2f805e8e4d019e`.
- #576: 8/8 `success` no head `2a24e864368db508cc95a25db78aa676c3393af0`.
- #577: nenhum workflow run/status retornado no head atual `e61b66a0f9757f7f25b26d84dec93c550c5d4ce`.
- #580: 8/8 `success` no head `335136bbd8f773824c29ab32abae8c9e8ffbe92c`.
- #539: 7/7 `success` no head `5c27ed57d98fecde57924f934b9075edf880657c`, mas branch antiga e `mergeable=false`.
- #579 (atualização de status): head consultado `cd4c3e1abee3314d4cd497b179fcde9c2c88c87`; nenhum workflow run/status retornado neste head. A PR #579 informa 13/13 checks pós-merge para a main `73bf91cd...`, mas a consulta direta a workflows/status deste SHA main não retornou registros neste checkpoint; manter como **relatado, não revalidado independentemente**.

Links para as PRs e seus heads devem ser consultados novamente antes de qualquer ação; checks são específicos do SHA.

## 5. Próximos passos seguros

1. Manter M-12 pendente até decisão explícita de identidade canônica DEC-023.
2. Reconciliar DEC-021/022/023 com protocolo, pré-registro, estatísticas, runner e testes por emendas datadas, sem editar unilateralmente artefatos protegidos.
3. Implementar cada método estatístico em PR separada, com fixtures sintéticas, revisão metodológica humana e checks no head final; não executar sobre dados reais.
4. Verificar e implementar D7 somente com um inventário legítimo de citações, antes de qualquer anotação de veredito, e após os gates humanos.
5. Realizar Piloto 02 e segunda anotação exclusivamente por pessoas, sem IA e sem execução do sistema, mantendo os casos privados e descartados.

## 6. Escopo desta proposta

Este checkpoint é um novo documento de auditoria. Não altera código, decisões, pré-registro, protocolo, executor, testes, Judge, Golden, manifests/hashes, fontes capturadas, casos, rótulos, workflows, releases ou tags. Não mescla PR, não aprova, não congela, não executa sistema ou benchmark e não reivindica validação externa.



---

## Adendo de revalidação — 2026-11-18

Este adendo atualiza os fatos dinâmicos do checkpoint sem apagar o retrato de 17/11. Não altera decisões aprovadas, protocolo, pré-registro, código do Judge, Golden, manifestos, hashes, fontes ou dados do benchmark.

### 1. Main e PR #269

- A comparação direta de `main` com o commit `73bf91cd7175bdf18edbeffa661ef12a5ddf7f56` retornou `identical`: este é o HEAD confirmado da `main`. O commit corresponde à atualização documental da PR [#578](https://github.com/Ayorinha/ayorai-opensearch/pull/578).
- A consulta atual de workflow-runs e de status combinado para esse SHA não retornou objetos. Uma review anterior nas PRs #579/#581 registra 13/13 check-runs e três workflows aprovados, mas essa contagem fica **relatada, não revalidada independentemente nesta consulta**. Não transferir checks de outro SHA.
- [#269](https://github.com/Ayorinha/ayorai-opensearch/pull/269) permanece fechada sem merge, em Draft no registro do GitHub, head `f161c14b1bf196dd111e176ac04907d6eaa7f1f3`. A conversa contém três comentários; não há reviews submetidas nem threads inline. Os sete workflow runs associados ao head foram consultados e concluíram `success`; o endpoint legado de status não retornou registros.
- A linhagem #269 → #272 → #273 já está concluída na história do repositório. A revisão metodológica original não deve ser reiniciada.

### 2. Estado atual das PRs relevantes

Os resultados abaixo são específicos dos SHAs indicados. “Workflow runs” não deve ser confundido com “check-runs” ou com o endpoint legado de commit statuses.

| PR | HEAD consultado | Workflow runs | Estado / escopo |
|---|---|---:|---|
| [#553](https://github.com/Ayorinha/ayorai-opensearch/pull/553) | `4d980043b84b8ffc68559e87ea51cf1b8b959195` | 7/7 success | Draft; somente `docs/eval/STATISTICS.md`; 2 commits à frente e 105 atrás da main, branches divergentes |
| [#576](https://github.com/Ayorinha/ayorai-opensearch/pull/576) | `2a24e864368db508cc95a25db78aa676c3393af0` | 8/8 success | Draft; snapshot de bytes em `rgc_agreement.py` e testes sintéticos; não implementa DEC-022 |
| [#577](https://github.com/Ayorinha/ayorai-opensearch/pull/577) | `e61b66a0f9757f7f25b26d84dec93c550c5d4ce4` | 8/8 success | Draft; gate de resolução informativa de H1 e regressão sintética |
| [#580](https://github.com/Ayorinha/ayorai-opensearch/pull/580) | `d4800de68c4229c343737aa0b92d34a10d2aee73` | 8/8 success | Draft; runner/E5, testes e template de manifesto; não revisado nem alterado neste ciclo |
| [#579](https://github.com/Ayorinha/ayorai-opensearch/pull/579) | `cd4c3e1abee3314d4cd497b179fcde9c2c88c87b` | 7/7 success | Aberta, não Draft; diff somente em `docs/STATUS.md`; não mesclada |
| [#581](https://github.com/Ayorinha/ayorai-opensearch/pull/581) | `95367923ffc87dd3af798b69091fbe3a0c2cfe99` | 7/7 success antes deste adendo | Draft; este adendo é documental e será revalidado no novo HEAD |

O endpoint de status combinado não retornou registros para esses heads; os oito/sete resultados acima são os workflow runs consultados diretamente. Não há falha no conjunto de runs atual dessas PRs.

### 3. Revalidação metodológica — diferenças que permanecem

**M-12 — identidade DEC-023.** Na `main`, DEC-023 determina o identificador literal `component:` + IDs únicos ordenados por `+`, enquanto a seção ainda vigente de `STATISTICS.md` descreve `component:sha256:` sobre JSON canônico. A #553 propõe alinhar a documentação à DEC-023, mas sua branch está 105 commits atrás e não deve ser integrada sem reconciliação e novos checks no head atualizado. Nenhum identificador foi calculado com dados reais.

**M-13 — kappa por componente.** DEC-022 aprova bootstrap de Cohen's kappa por componente; a Emenda 10 do protocolo ainda especifica bootstrap por caso. `rgc_agreement.py` continua calculando o intervalo por caso. A #576 resolve a consistência entre bytes lidos e hashes das duas anotações, mas não implementa DEC-022 nem reconcilia a Emenda 10. A alteração metodológica da ferramenta permanece bloqueada até emenda/reconciliação autorizada; não foram lidas anotações reais.

**M-14 — H1 e documentação normativa.** O pré-registro contém a Emenda 11 (DEC-027 D4/D5), que substitui McNemar pelo sign-flip por componente e torna o IC por componente primário. O protocolo consultado ainda termina na Emenda 10; portanto, os dois documentos normativos não estão alinhados. O código em `rgc_eval.py` na main já constrói componentes para a partição `hidden` e calcula bootstrap por componente/sign-flip; a seção correspondente de `STATISTICS.md` ainda declara a implementação pendente e usa a identidade antiga de componente. A #577 acrescenta a barreira de `K′` informativo à decisão final de H1; permanece Draft e só usa regressões sintéticas. Nenhuma execução confirmatória foi feita.

**M-16 — resolução versus poder.** A observação já registrada na review COMMENTED da #581 permanece válida: D7 `K ≥ 6` é condição de resolução matemática prévia, não demonstra poder ou precisão. Para a decisão após os resultados, `K′` (componentes com diferença não nula) também importa. Não fragmentar componentes nem alterar limiares para buscar significância.

**D7 e dados.** Não foi produzido nem consultado inventário real de citações para calcular K. A existência de 300 casos-alvo ou de aproximadamente 90 casos ocultos não demonstra, por si só, número suficiente de componentes independentes.

### 4. Limite de escopo da PR #580

A #580 altera `evals/ptbr/rgc_eval.py`, testes, `RUNNER-RGC-v1.md` e `docs/eval/templates/PROTOCOL-FREEZE.template.json`. Embora os oito workflow runs do HEAD consultado tenham passado, a PR altera o esquema do template de freeze e o runner. Por isso, **nenhuma alteração, aprovação ou integração foi feita nela neste ciclo**, respeitando a restrição de não alterar manifestos/hashes nem congelar o protocolo.

### 5. Pendências e resultado desta revalidação

- Pendente de decisão/emenda autorizada: alinhar o protocolo com a Emenda 11 do pré-registro e DEC-021/027.
- Pendente de emenda/reconciliação: alinhar a Emenda 10 e DEC-022 antes de trocar o bootstrap de kappa por caso para componente.
- Pendente de atualização segura: reconciliar `STATISTICS.md` com DEC-023 e com o código já existente, após tratar a divergência de 105 commits da #553.
- Pendente de evidência humana: Piloto 02 manual sem IA, segunda anotação independente, adjudicação, F-01, proveniência/vigência e isolamento real da partição oculta.
- O protocolo permanece **[PROPOSTO]**. Nenhum caso foi criado/rotulado, nenhuma anotação real foi lida, nenhum runner foi executado sobre casos RGC e nenhuma métrica foi produzida.

**Alteração deste adendo:** somente este documento de checkpoint, na branch da PR #581. Nenhum arquivo protegido ou dado do benchmark foi alterado. Esta atualização é uma revisão interna, não independente e não externa.
