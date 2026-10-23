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
