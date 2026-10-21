# Desvios de processo — mensagens de squash

**Data do registro:** 2026-10-21  
**Escopo:** registrar os três desvios de formato de mensagem de commit identificados na revisão do histórico; não reescrever commits, não alterar a árvore histórica e não atribuir revisão independente.  
**Revisão:** automatizada, não independente (F-01 permanece aberto).

## Desvios conhecidos

| PR | Commit de merge | Mensagem registrada | Desvio de formato |
|---|---|---|---|
| [#270](https://github.com/Ayorinha/ayorai-opensearch/pull/270) | [`6f3588ba9e34036e1d788f48aff7910a2a3dd3cf`](https://github.com/Ayorinha/ayorai-opensearch/commit/6f3588ba9e34036e1d788f48aff7910a2a3dd3cf) | `docs: corrigir corte dos rótulos no diagrama de verificação` | Não inclui o sufixo `(#270)` nem a linha final de autorização exigida no ciclo atual. |
| [#274](https://github.com/Ayorinha/ayorai-opensearch/pull/274) | [`c639d0fda7a6fb8ab29bb438611ee536b1f3ddc2`](https://github.com/Ayorinha/ayorai-opensearch/commit/c639d0fda7a6fb8ab29bb438611ee536b1f3ddc2) | `fix: enforce RGC baseline B from public development partition` | Não inclui o sufixo `(#274)` nem a linha final de autorização exigida no ciclo atual. A questão de conteúdo do pré-registro é tratada separadamente pelas PRs #284 e #288. |
| [#281](https://github.com/Ayorinha/ayorai-opensearch/pull/281) | [`f61830624180f6efb122816260ff062908895934`](https://github.com/Ayorinha/ayorai-opensearch/commit/f61830624180f6efb122816260ff062908895934) | `docs(eval): clarify RGC statistics and pending amendment` | Não inclui o sufixo `(#281)` nem a linha final de autorização exigida no ciclo atual. |

## Tratamento

- Os três commits permanecem intactos; nenhuma alteração de histórico ou force-push foi realizada.
- Os desvios são registrados como ocorrências históricas, não como justificativa para repetir o padrão.
- A partir da autorização DEC-016, as novas PRs são mescladas por squash com o título `<título> (#n)`, uma ou duas linhas de descrição e a linha final exata definida na DEC-016.
- A lista acima registra os três desvios apontados pela revisão; não afirma que todos os commits históricos do repositório foram auditados exaustivamente.
