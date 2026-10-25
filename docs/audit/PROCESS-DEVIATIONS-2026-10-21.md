# Desvios de processo — mensagens de squash

> **Aviso histórico — 2026-10-23:** este documento registra uma versão, auditoria, avaliação ou rascunho anterior; preserve-o como evidência histórica e não o trate como estado atual nem como resultado de benchmark vigente. Consulte docs/STATUS.md.


**Data do registro:** 2026-10-21  
**Escopo:** registrar os três desvios de formato de mensagem de commit identificados na revisão do histórico; não reescrever commits, não alterar a árvore histórica e não atribuir revisão independente.  
**Revisão:** automatizada, não independente (F-01 permanece aberto).

## Desvios conhecidos

| PR | Commit de merge | Mensagem registrada | Desvio de formato |
|---|---|---|---|
| [#270](https://github.com/Ayorinha/ayorai-opensearch/pull/270) | [`6f3588ba9e34036e1d788f48aff7910a2a3dd3cf`](https://github.com/Ayorinha/ayorai-opensearch/commit/6f3588ba9e34036e1d788f48aff7910a2a3dd3cf) | `docs: corrigir corte dos rótulos no diagrama de verificação` | Não inclui o sufixo `(#270)` e não segue o padrão de mensagem adotado atualmente na DEC-016; não se presume que a linha final fosse exigida à época. |
| [#274](https://github.com/Ayorinha/ayorai-opensearch/pull/274) | [`c639d0fda7a6fb8ab29bb438611ee536b1f3ddc2`](https://github.com/Ayorinha/ayorai-opensearch/commit/c639d0fda7a6fb8ab29bb438611ee536b1f3ddc2) | `fix: enforce RGC baseline B from public development partition` | Não inclui o sufixo `(#274)` e não segue o padrão de mensagem adotado atualmente na DEC-016; não se presume que a linha final fosse exigida à época. A questão de conteúdo do pré-registro é tratada separadamente pelas PRs #284 e #288. |
| [#281](https://github.com/Ayorinha/ayorai-opensearch/pull/281) | [`f61830624180f6efb122816260ff062908895934`](https://github.com/Ayorinha/ayorai-opensearch/commit/f61830624180f6efb122816260ff062908895934) | `docs(eval): clarify RGC statistics and pending amendment` | Não inclui o sufixo `(#281)` e não segue o padrão de mensagem adotado atualmente na DEC-016; não se presume que a linha final fosse exigida à época. |

## Tratamento

- Os três commits permanecem intactos; nenhuma alteração de histórico ou force-push foi realizada.
- Os desvios são registrados como ocorrências históricas, não como justificativa para repetir o padrão.
- A partir da autorização DEC-016, as novas PRs são mescladas por squash com o título `<título> (#n)`, uma ou duas linhas de descrição e a linha final exata definida na DEC-016.
- A lista acima registra os três desvios apontados pela revisão; não afirma que todos os commits históricos do repositório foram auditados exaustivamente.


## Desvios adicionais identificados no fechamento final

| PR | Commit de merge | Mensagem registrada | Desvio de formato |
|---|---|---|---|
| [#369](https://github.com/Ayorinha/ayorai-opensearch/pull/369) | [`1e77df724d432b05d230b112afd3ca6ff83eb3b0`](https://github.com/Ayorinha/ayorai-opensearch/commit/1e77df724d432b05d230b112afd3ca6ff83eb3b0) | `test(rgc): prevent approved amendment contradictions` | O título do squash não contém `(#369)` e a mensagem não termina com a linha exigida pela DEC-016. O commit histórico permanece intacto. |

### Duplicação por execução paralela

- **PRs #362 e #369:** ambas implementaram guardas de consistência para DEC-017–DEC-020 e as Emendas 7–10. A #362 já estava mesclada quando a #369 também foi mesclada; a consolidação em `tests/test_rgc_decision_consistency.py` e a remoção de `tests/test_approved_amendment_consistency.py` foram feitas na PR #375.
- **PRs #372 e #373:** ambas tratavam das justificativas para supressões `# nosec`. A #372 foi fechada sem merge e a #373 acabou mesclada. A #373 foi mesclada com a mensagem e a linha DEC-016 corretas; este registro não reescreve o histórico nem altera o resultado real.
- A abertura concorrente dessas PRs foi um desvio do requisito de execução estritamente sequencial. O registro é retrospectivo e não transforma a revisão automatizada em revisão independente.


## Desvios adicionais registrados — 2026-10-25

**Escopo:** registro retrospectivo dos merges das PRs #388, #389, #390, #391, #393, #394, #395, #396, #397, #398 e #399. Os commits permanecem intactos; este registro não reescreve o histórico. A conferência foi automatizada e não independente.

| PR | Commit de merge | Título/mensagem registrada | Desvio de processo |
|---|---|---|---|
| [#388](https://github.com/Ayorinha/ayorai-opensearch/pull/388) | [`620e39f7e2fb7437b576d7dc935cab6ffcbe08b0`](https://github.com/Ayorinha/ayorai-opensearch/commit/620e39f7e2fb7437b576d7dc935cab6ffcbe08b0) | `docs(manual): align chapter index with current status` | O título não contém `(#388)`; a mensagem não termina com a linha exigida pela DEC-016. |
| [#389](https://github.com/Ayorinha/ayorai-opensearch/pull/389) | [`2708ce5299eedbb2184f1ea10f635f601459ff38`](https://github.com/Ayorinha/ayorai-opensearch/commit/2708ce5299eedbb2184f1ea10f635f601459ff38) | `docs(status): record manual index reconciliation` | O título não contém `(#389)`; a mensagem não termina com a linha exigida pela DEC-016. |
| [#390](https://github.com/Ayorinha/ayorai-opensearch/pull/390) | [`a1fe33e7025204d4f345c8e21faeaed53ab2de5f`](https://github.com/Ayorinha/ayorai-opensearch/commit/a1fe33e7025204d4f345c8e21faeaed53ab2de5f) | `test(audit): cover report findings and failure severity` | O título não contém `(#390)`; a mensagem não termina com a linha exigida pela DEC-016. |
| [#391](https://github.com/Ayorinha/ayorai-opensearch/pull/391) | [`bf49dba9e7e66bdc0af0203845547b8541e81cca`](https://github.com/Ayorinha/ayorai-opensearch/commit/bf49dba9e7e66bdc0af0203845547b8541e81cca) | `test(extraction): cover provenance and adapter contracts` | O título não contém `(#391)`; a mensagem não termina com a linha exigida pela DEC-016. |
| [#393](https://github.com/Ayorinha/ayorai-opensearch/pull/393) | [`a44d0564d429d956898e819721299f715b46bda2`](https://github.com/Ayorinha/ayorai-opensearch/commit/a44d0564d429d956898e819721299f715b46bda2) | `fix(extraction): validate NLI payloads and source offsets` | O título não contém `(#393)`; a mensagem não termina com a linha exigida pela DEC-016. |
| [#394](https://github.com/Ayorinha/ayorai-opensearch/pull/394) | [`f94e86db89eb000c4764c49b949a30d65e63e421`](https://github.com/Ayorinha/ayorai-opensearch/commit/f94e86db89eb000c4764c49b949a30d65e63e421) | `docs(status): record extraction fixes and current PR state` | O título não contém `(#394)`; a mensagem não termina com a linha exigida pela DEC-016. |
| [#395](https://github.com/Ayorinha/ayorai-opensearch/pull/395) | [`bd99f4b3e25a785cdcc08172d860a317532e6d90`](https://github.com/Ayorinha/ayorai-opensearch/commit/bd99f4b3e25a785cdcc08172d860a317532e6d90) | `docs(status): clarify snapshot timestamp and follow-up merge` | O título não contém `(#395)`; a mensagem não termina com a linha exigida pela DEC-016. |
| [#396](https://github.com/Ayorinha/ayorai-opensearch/pull/396) | [`f7277d3e00a0efb8c47d8a5366bc9eba0db38778`](https://github.com/Ayorinha/ayorai-opensearch/commit/f7277d3e00a0efb8c47d8a5366bc9eba0db38778) | `docs(status): record PR #395 merge and main reference` | O título não contém `(#396)`; a mensagem não termina com a linha exigida pela DEC-016. |
| [#397](https://github.com/Ayorinha/ayorai-opensearch/pull/397) | [`33393f84da6c2ade4c40f628c683dd793a5dfa02`](https://github.com/Ayorinha/ayorai-opensearch/commit/33393f84da6c2ade4c40f628c683dd793a5dfa02) | `docs(status): record PR #396 merge and checks` | O título não contém `(#397)`; a mensagem não termina com a linha exigida pela DEC-016. |
| [#398](https://github.com/Ayorinha/ayorai-opensearch/pull/398) | [`641591973da25ede8234958b0a36b62423476630`](https://github.com/Ayorinha/ayorai-opensearch/commit/641591973da25ede8234958b0a36b62423476630) | `fix(rgc): validate gold label JSONL strictly` | O título não contém `(#398)`; a mensagem não termina com a linha exigida pela DEC-016. |
| [#399](https://github.com/Ayorinha/ayorai-opensearch/pull/399) | [`3f12d54f89da938deb50b6ef58396c7b29efbb86`](https://github.com/Ayorinha/ayorai-opensearch/commit/3f12d54f89da938deb50b6ef58396c7b29efbb86) | `chore(rgc): align runner version and process updates` | O título não contém `(#399)`; a mensagem não termina com a linha exigida pela DEC-016. |

A partir deste registro, novas mesclagens devem usar squash com título `<título> (#n)`, uma ou duas linhas de descrição e terminar exatamente com: “Mesclada sob a autorização DEC-016 do mantenedor; revisão automatizada, não independente (F-01 permanece aberto).” Nenhuma mensagem histórica foi alterada.
