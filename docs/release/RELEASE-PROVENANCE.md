# Proveniência de artefatos de release

Este documento distingue os controles configurados no repositório das evidências que só existirão depois de uma execução de CI e de uma publicação autorizada. A preparação da v0.6.0 não constitui uma release publicada.

## Build de distribuição no CI

A workflow de CI inclui um job de empacotamento que constrói o source distribution (sdist) e o wheel a partir do checkout testado, calcula SHA-256 para cada artefato e publica os arquivos e o manifesto de hashes como artefatos da execução de CI. Os hashes demonstram a integridade dos arquivos daquele build; por si só, não constituem assinatura, atestado de proveniência ou prova de publicação.

Para cada execução, a evidência esperada é:

- SHA do commit testado e URL da execução de CI;
- arquivo sdist e arquivo wheel gerados pelo comando python -m build;
- SHA256SUMS.txt com os hashes SHA-256 dos dois artefatos;
- artefatos retidos na execução de CI, identificados pelo SHA do commit.

Nenhum hash de artefato é declarado neste documento antes de o job executar. O build do CI não cria tag, GitHub Release, publicação em índice de pacotes ou registro DOI.

## Controles adicionais de endurecimento de release

Os itens seguintes continuam sendo requisitos futuros e não são declarados como implementados por esta PR:

1. SLSA provenance: integrar workflow geradora apropriada e publicar os hashes dos artefatos como subjects do atestado.
2. OpenTimestamps: gerar prova .ots do conjunto de artefatos e anexá-la à release autorizada.
3. SBOM: gerar e anexar SBOM para cada conjunto de artefatos.
4. Assinaturas: assinar os artefatos e publicar metadados de verificação.
5. Replayabilidade: manter commit de origem, hashes, SBOM, proveniência e provas temporais juntos para verificação independente.

## Estado atual

Estado em 2026-10-25: o mantenedor escolheu a data oficial `2026-10-25`, autorizou preparar e publicar após verificar os artefatos e confirmou preservar o DOI de conceito `10.5281/zenodo.23125082`. `CITATION.cff`, `CHANGELOG.md` e as notas de release estão sendo alinhados nesta branch; essa alteração ainda não está na `main`.

A publicação continua bloqueada até que uma execução de CI associada ao commit candidato final produza sdist, wheel e `SHA256SUMS.txt`, e os arquivos sejam baixados e verificados. O artefato consultado na execução 39760225707 pertence ao SHA antigo `33393f84da6c2ade4c40f628c683dd793a5dfa02` e não comprova um build da versão candidata `0.6.0` no commit de merge `6fcdb7d5e5ad1df19aa1d531fec07805b0c5545a`. Não foi confirmada nesta etapa a existência de tag `v0.6.0` ou GitHub Release; nenhum hash de distribuição é declarado como verificado.
