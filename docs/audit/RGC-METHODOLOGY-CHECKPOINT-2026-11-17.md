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
