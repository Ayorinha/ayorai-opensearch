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

A PR prepara os metadados da versão 0.6.0 e adiciona o build sdist/wheel com SHA-256 ao CI. A data de release continua pendente. A publicação, a criação de tag, a alteração do DOI em CITATION.cff e a criação da release exigem decisão e autorização separadas do mantenedor.
