# Proveniência de artefatos de release

Este documento distingue controles configurados de evidências observadas. A v0.6.0 foi publicada; o registro abaixo identifica os artefatos do CI e a relação declarada com a tag e o depósito Zenodo.

## Verificação registrada da v0.6.0 — 2026-10-25

- **Versão e origem:** tag `v0.6.0`, commit de origem `6fcdb7d5e5ad1df19aa1d531fec07805b0c5545a`.
- **Execução CI:** [run 40022675628](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/40022675628).
- **Artefato CI:** `distributions-6fcdb7d5e5ad1df19aa1d531fec07805b0c5545a`; o manifesto `SHA256SUMS.txt` foi verificado localmente com `sha256sum -c SHA256SUMS.txt`, e ambos os arquivos retornaram `OK`.
- **Source distribution:** `ayorai_opensearch-0.6.0.tar.gz` — SHA-256 `bc375060cdefcfcdba0a21c9255b1896d20c837d02502fb0f3073e4070fc1614`.
- **Wheel:** `ayorai_opensearch-0.6.0-py3-none-any.whl` — SHA-256 `e9b453765c77103273b3d41465025476e29bbee1458d2addd28ef1c728b9466c`.
- **ZIP do Zenodo:** MD5 `84d6957c27c827db2740ca53eae2a03f`; a revisão automatizada registrada em 2026-10-25 informa correspondência com o zipball da tag `v0.6.0`. Essa conferência é automatizada e não independente.
- **GitHub Release:** publicada em 2026-10-24T00:41Z (data oficial da versão: 2026-10-23); não possui arquivos anexados. Nenhum arquivo foi anexado por este trabalho.
- **Retenção do artefato de CI:** expiração informada em 2027-01-22 UTC.

A frase histórica de que o artefato consultado pertencia a um SHA antigo não se aplica a este registro: o artefato identificado acima foi gerado no run indicado para o SHA exato da tag `v0.6.0`. Os hashes do sdist e do wheel foram recalculados contra o manifesto baixado. A conferência do MD5 do ZIP do Zenodo permanece atribuída à revisão automatizada indicada, não a uma auditoria independente.

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

A v0.6.0 está publicada e a tag `v0.6.0` aponta para o SHA de origem registrado acima. O artefato CI e o manifesto de hashes foram baixados e verificados. O DOI de versão e o DOI de conceito estão registrados em `CITATION.cff`; não houve criação ou alteração de tag, release ou DOI nesta atualização.
