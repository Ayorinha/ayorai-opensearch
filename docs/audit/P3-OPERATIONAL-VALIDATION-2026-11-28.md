# P3/A1 — Validação operacional protegida (2026-11-28)

Revisão por ferramenta automatizada, publicada pelo mantenedor.

| item | valor |
|---|---|
| Workflow | `.github/workflows/phase1b-dev-minimal.yml`, `mode=minimal` |
| Execução válida | `46153767025` (#11), `main` @ `5fe34da8758858095d20082544d63a8fdbdd0b38` |
| Environment | `international-benchmark-maintainer-approval`, aprovado pelo mantenedor em cada etapa |
| Resultado | `success`: `plan`, `shard (dev-0000)`, `shard (dev-0001)` e `aggregate` |
| Decisão aplicada | DEC-034, opção A (#649) |

**Rótulos:**
- **[FATO]**: verificado nos logs e na API do GitHub;
- **[HIPÓTESE]**: não verificável com o acesso desta revisão.

## 1. Environment [FATO, conferido pelo mantenedor nas configurações]

- Aprovador obrigatório: o mantenedor. Sem "Prevent self-review", sem wait timer, sem bypass de administrador.
- Só a branch `main` pode implantar; nenhuma tag.
- Secrets do Environment: `HF_TOKEN` e `PHASE1B_ARTIFACT_ENCRYPTION_KEY`.
- A aprovação foi exigida antes de cada job. Nenhum job rodou sem ela.

## 2. Histórico das execuções

| execução | resultado | causa |
|---|---|---|
| #9 (`46144910039`) | cancelada sem rodar | a aprovação não foi registrada; disparada com "Prevent self-review" ainda ativo |
| #10 (`46151543376`) | parou no manifesto, por desenho | `46 identities repeated (50 extra rows), 5 with conflicting labels`. Nenhuma chave usada para cifrar, nenhum artefato |
| #11 (`46153767025`) | sucesso | depois da DEC-034 |

## 3. Evidência da execução #11 [FATO]

**Plano:**
- secret validado sem impressão (`VALID (value not displayed)`);
- parquet DEV conferido pelo SHA-256 fixado (`dev_shard_verified`);
- dependências instaladas com `--require-hashes` (`cryptography` 50.0.2, `pyarrow` 23.0.1).

**Resolução de identidades (DEC-034), só contagens:**

| contagem | valor |
|---|---|
| linhas de origem | 30.420 |
| identidades repetidas | 46 |
| cópias com rótulo igual removidas | 45 |
| identidades com rótulos divergentes excluídas | 5 (10 linhas) |
| identidades únicas mantidas | 30.365 |

**Isolamento gold:**
- `gold_labels_discarded: true`;
- `gold_labels_encrypted: false`;
- `labels_in_inference_input: false`;
- nenhum job recebeu a chave gold.

**Shards:** cada shard decifrou o manifesto e a entrada de inferência dentro do job protegido, rodou o mDeBERTa de revisão fixada sobre 5 exemplos e cifrou a saída antes do upload.

**Agregado:**
- `status: complete`, `model_count: 1`, `incomplete_model_count: 0`;
- `quality_metrics: not_computed_minimal_run`;
- `instance_level_output_published: false`.

**Artefatos e retenção:**

| artefato | conteúdo | expira |
|---|---|---|
| `phase1b-dev-minimal-manifest-encrypted` | cifrado | 1 dia |
| `phase1b-dev-minimal-inference-data-encrypted` | cifrado | 1 dia |
| `phase1b-dev-minimal-encrypted-dev-0000`, `-0001` | cifrados | 1 dia |
| `phase1b-dev-minimal-aggregate` | só agregados operacionais, sem dados por instância | 14 dias |

**Limpeza:** arquivos locais removidos em cada job, inclusive na execução #10, que falhou.

## 4. Limites

- **Não é validação científica.** O minimal não calcula métricas de qualidade e usa 10 exemplos.
- **Execução DEV completa:** a chave `PHASE1B_GOLD_LABEL_ENCRYPTION_KEY` não está no Environment. Antes do workflow full, ela precisa existir no Environment ou no repositório, com valor distinto da chave de artefato [HIPÓTESE: pode estar no repositório; não verificável com este acesso].
- **Riscos residuais do relatório de encerramento:**
  - PyTorch fixado só por versão;
  - nenhuma revisão humana independente.

## 5. Situação

**P3/A1: CONCLUÍDA COM RESSALVAS.**
- O isolamento dos rótulos gold está em código, testes e governança, e foi observado funcionando sobre o dado real, com o Environment protegido.
- Ressalvas: validação científica (execução DEV completa) e os riscos residuais da seção 4.
