# AYORAI ATTRACTOR — continuidade verificada (2026-10-22)

## Escopo deste registro

Este documento registra uma leitura de continuidade da branch padrão em 2026-10-22. Não substitui `docs/STATUS.md`, decisões aprovadas, ADRs, pré-registro ou artefatos metodológicos; serve para apontar a diferença entre o snapshot histórico de status e o HEAD consultado nesta data.

## Estado observado

- Repositório: `Ayorinha/ayorai-opensearch`.
- HEAD da `main` consultado: `a1fe33e7025204d4f345c8e21faeaed53ab2de5f`.
- Mensagem do commit: `test(audit): cover report findings and failure severity`.
- O commit declara alterações de testes, sem mudança no comportamento de produção, protocolo RGC, dados do benchmark ou metadados de release.
- PR aberta identificada na consulta: [#391 — test(extraction): cover provenance and adapter contracts](https://github.com/Ayorinha/ayorai-opensearch/pull/391). A descrição declara escopo de testes e ausência de mudanças de produção, contrato API, protocolo RGC, dados do benchmark ou metadados de release.
- A consulta ao endpoint de workflow runs associado ao SHA retornou zero execuções acionadas por PR. Esse endpoint filtra workflows de PR; portanto, o resultado **não confirma nem nega** o estado dos checks de push da `main`. Nenhum status de CI para o HEAD é afirmado neste registro.

## Divergência documental a resolver

`docs/STATUS.md` contém snapshots de 2026-10-21 e registra como referência anterior `620e39f7e2fb7437b576d7dc935cab6ffcbe08b0`. O HEAD consultado é posterior. Não atualizar retroativamente o SHA histórico como se tivesse sido validado; a reconciliação do status atual deve citar o novo SHA e evidências de CI específicas desse commit quando disponíveis.

## Estado científico preservado

- O protocolo RGC PT-BR permanece `[PROPOSTO]`, não congelado.
- DEC-017 a DEC-020 permanecem decisões metodológicas aprovadas, não autorização para congelamento ou execução.
- O piloto 02, a segunda anotação humana independente e a revisão humana independente F-01 continuam pendentes.
- Não criar, completar ou rotular casos do piloto/benchmark com IA.
- Não executar o ATTRACTOR sobre casos de piloto ou benchmark.
- Não alterar Judge, Golden, manifests, hashes, capturas de fonte, pré-registro ou artefatos protegidos.
- Não publicar métricas RGC nem alegações de validação externa, certificação ou revisão independente sem evidência correspondente.
- A possível inclusão de identificadores pseudônimos distintos de anotadores no esquema é uma decisão do mantenedor pendente; este registro não a implementa.

## Próximos passos seguros

1. Obter e registrar checks específicos do SHA atual da `main`; não inferir o estado do CI a partir de workflows de PR ausentes.
2. Revisar a PR #391 sem aprová-la nem mesclá-la, verificando o diff e os checks efetivamente associados ao head da PR.
3. Em trabalho documental separado, atualizar o snapshot de status somente com fatos confirmados e preservar os registros históricos.
4. Aguardar trabalho humano do piloto 02, segunda anotação independente e F-01 antes de qualquer decisão de congelamento ou execução confirmatória.

## Limites

Este registro é uma reconciliação operacional baseada em metadados do GitHub e documentação do repositório. Não é revisão científica independente e não representa resultados de benchmark.
