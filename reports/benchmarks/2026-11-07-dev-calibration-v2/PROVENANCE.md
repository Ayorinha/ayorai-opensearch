# Proveniência — DEV Calibration V2 (2026-11-07)

Este arquivo registra identificadores e hashes fornecidos pelo mantenedor para conferência do agregado protegido. Não contém nem reconstrói os artefatos JSON, e não contém dados por instância.

## Execuções

| Etapa | Run | Código / head | Resultado |
|---|---|---|---|
| Inferência DEV completa | [42389121599](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/42389121599) | `34b7ccd654896890ab0197bffd6c607fbc3f729e` | Plan e 93 shards (3 modelos × 31) concluíram; aggregate falhou com `ModuleNotFoundError` antes de decifrar qualquer artefato. |
| Re-agregação | [42418593837](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/42418593837) | `c3946aec35eeb32551c92f97472308ccdd20a744` (PR #481) | Agregação somente; origem verificada, artefatos decifrados no ambiente protegido e validações aprovadas. Não houve reexecução de inferência. |

## Hashes do artefato protegido

- Nome do artefato: `phase1b-dev-full-aggregate` (retenção de 30 dias).
- SHA-256 do arquivo `phase1b-aggregate.json`: `106448dcee6dba1b9ae7075125d08a128cc7af19b7a490e0becdfb26bc1680fa`.
- Campo `report_sha256`: `d411741824a86ac7cfba0471a8fa71cd89919f13a4e50243e11d0cf1e65e37f2`.
- Campo `manifest_sha256`: `deb3ef389553a03bb840e03a1e314e3f4d02dac50f4aa3d1c713c88a9dd55a74`.

O mantenedor adicionará os arquivos `phase1b-aggregate.json` e `PROVENANCE.json` a partir do artefato original, após conferência. Este documento não os substitui.

## Pin da partição DEV

- Arquivo de pin: `configs/benchmarks/llm-aggrefact-dev-pin.json`.
- SHA-256 do pin: `ca9a5bda9561bbc6f7327ef81ab41727fa10e96f96e9dc74ef32ba3af3c1d8a8`.
- Revisão do pin: `981dfd0bd8e58e7238a9ab92b2e6ea44bce918e4`.

## Pré-registro

- [CALIBRATION-V2-PREREGISTRATION.md](../../../docs/benchmarks/CALIBRATION-V2-PREREGISTRATION.md)

## Limite de proveniência

Os hashes acima foram transcritos do registro fornecido pelo mantenedor. A conferência independente deve ser feita contra os arquivos originais do artefato protegido, que não foram acessados nem incluídos nesta PR. Nenhum dado por instância é publicado.
