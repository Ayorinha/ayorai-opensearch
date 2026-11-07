# Proveniência — DEV Calibration V2 (2026-11-07)

Este arquivo registra identificadores e hashes do agregado protegido. Os arquivos agregados originais estão nesta pasta (ver abaixo). Nenhum dado por instância é publicado.

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

Os arquivos originais do artefato foram adicionados sem modificação nesta pasta:

| Arquivo | SHA-256 |
|---|---|
| [`phase1b-aggregate.json`](phase1b-aggregate.json) | `106448dcee6dba1b9ae7075125d08a128cc7af19b7a490e0becdfb26bc1680fa` |
| [`PROVENANCE.json`](PROVENANCE.json) | `e124612af2c3b2e48c4426c8b1fe8e639692ed24d71349054b10d5d7570c3210` |

Conferência realizada: o SHA-256 do arquivo corresponde ao valor registrado; o campo `report_sha256` foi recalculado (JSON canônico do relatório sem esse campo) e confere; o arquivo não contém `record_id` nem `records`.

## Partição DEV (pin)

- Arquivo de pin: `configs/benchmarks/llm-aggrefact-dev-pin.json`.
- Dataset: `lytang/LLM-AggreFact`, arquivo `data/dev-00000-of-00001.parquet`.
- Revisão do dataset no Hugging Face: `981dfd0bd8e58e7238a9ab92b2e6ea44bce918e4`.
- SHA-256 do arquivo parquet DEV: `ca9a5bda9561bbc6f7327ef81ab41727fa10e96f96e9dc74ef32ba3af3c1d8a8` (35.453.136 bytes).

## Modelos (revisões fixadas em `scripts/benchmarks/phase1b/common.py`)

| Modelo | Repositório Hugging Face | Revisão |
|---|---|---|
| mDeBERTa | `MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7` | `b5113eb38ab63efdd7f280f8c144ea8b13f978ce` |
| MiniCheck | `lytang/MiniCheck-DeBERTa-v3-Large` | `2f2d01a54fa022a7ffadb76260e1ea8bc88c82bb` |
| FactCG | `yaxili96/FactCG-DeBERTa-v3-Large` | `0430e3509dbd28d2dff7a117c0eae25359ff3e80` |

## Pré-registro

- [CALIBRATION-V2-PREREGISTRATION.md](../../../docs/benchmarks/CALIBRATION-V2-PREREGISTRATION.md)

## Limite de proveniência

O artefato no GitHub Actions expira após 30 dias; os arquivos desta pasta são a cópia permanente. A conferência independente pode ser feita recalculando os SHA-256 acima. Nenhum dado por instância é publicado.
