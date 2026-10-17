# Registro de fontes primárias — benchmark PT-BR

**Estado:** fontes capturadas byte a byte em 2026-10-13 por GitHub Actions ([execução 38449402582](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/38449402582)) e registradas com SHA-256 em `evals/ptbr/SOURCES-REGISTRY.json`, conforme a DEC-002. A integridade de cada artefato é verificada pelo teste `tests/test_source_artifacts.py`.  
**Escopo:** atos normativos oficiais e metadados de proveniência.  
**Limite:** este registro não interpreta a legislação, sua hierarquia, vigência, revogação ou aplicabilidade.

## Base legal para o tratamento de textos normativos

A Lei nº 9.610/1998, art. 8º, IV, exclui os textos de tratados ou convenções, leis, decretos, regulamentos, decisões judiciais e demais atos oficiais da proteção autoral prevista nessa lei. Essa referência não elimina a obrigação de registrar proveniência, origem, versão, data de coleta e hash, nem resolve eventuais direitos sobre compilações, comentários ou outros materiais não normativos.

Fonte primária: [Lei nº 9.610, de 19 de fevereiro de 1998 — Planalto](https://www.planalto.gov.br/ccivil_03/leis/l9610.htm).

## Candidatos de fonte

| ID proposto | Título | Órgão | URL oficial | Data de publicação | Estado de captura |
|---|---|---|---|---|---|
| `anatel-res-765-2023` | Resolução Anatel nº 765, de 6 de novembro de 2023 — aprova o Regulamento Geral de Direitos do Consumidor de Serviços de Telecomunicações (RGC) | Agência Nacional de Telecomunicações (Anatel) | [Página oficial da resolução](https://informacoes.anatel.gov.br/legislacao/resolucoes/2023/1900-resolucao-765) | 2023-11-06 | `verified`; ver hash e coleta no registro estruturado |
| `planalto-lei-9610-1998` | Lei nº 9.610, de 19 de fevereiro de 1998 | Presidência da República — Planalto | [Texto oficial](https://www.planalto.gov.br/ccivil_03/leis/l9610.htm) | 1998-02-19 | `verified`; ver hash e coleta no registro estruturado |
| `planalto-lgpd-13709-2018` | Lei nº 13.709, de 14 de agosto de 2018 — Lei Geral de Proteção de Dados Pessoais | Presidência da República — Planalto | [Texto oficial](https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm) | 2018-08-14 | `verified`; ver hash e coleta no registro estruturado |

As datas acima identificam a data do ato, não atestam a vigência atual. Na consulta à página oficial da Resolução 765/2023, a própria Anatel apresenta ressalva de vigência parcial e remissões a atos posteriores. Por isso, a situação temporal deve ser capturada por dispositivo e com referência à fonte primária pertinente; não inferir vigência ou situação consolidada apenas a partir desta tabela. A página e o conteúdo exato devem ser conferidos novamente no momento da captura.


## Capturas registradas (2026-10-13)

**Texto de referência do RGC:** a publicação no DOU de 10/11/2023, Seção 1, páginas 14 a 23 (Resolução nas páginas 14 a 18; Anexo — RGC — das páginas 18 a 23, terminando no art. 101), mais as retificações de 26/12/2023 e 12/01/2024. Os PDFs do DOU saíram com bytes idênticos em duas capturas independentes; as páginas HTML da Anatel e do Planalto variam a cada acesso e servem como referência, não como texto canônico.

| ID | Artefato | Publicação | Coleta (UTC) | SHA-256 |
|---|---|---|---|---|
| `anatel-res-765-2023` | `evals/ptbr/sources/raw/anatel-res-765-2023-pagina.html` | 2023-11-06 | 2026-10-13T18:46:02Z | `7f665980704bb49c…` |
| `planalto-lei-9610-1998` | `evals/ptbr/sources/raw/planalto-lei-9610-1998.html` | 1998-02-19 | 2026-10-13T18:46:06Z | `3d1b59c0b383d45e…` |
| `planalto-lgpd-13709-2018` | `evals/ptbr/sources/raw/planalto-lgpd-13709-2018.html` | 2018-08-14 | 2026-10-13T18:46:09Z | `587f8905e7df7d27…` |
| `anatel-res-765-2023-dou-2023-11-10-p14` | `evals/ptbr/sources/raw/dou-2023-11-10-p14.pdf` | 2023-11-10 | 2026-10-13T18:46:22Z | `d0f2b25bdb69e73a…` |
| `anatel-res-765-2023-dou-2023-11-10-p15` | `evals/ptbr/sources/raw/dou-2023-11-10-p15.pdf` | 2023-11-10 | 2026-10-13T18:46:25Z | `168a5594d31fa4f0…` |
| `anatel-res-765-2023-dou-2023-11-10-p16` | `evals/ptbr/sources/raw/dou-2023-11-10-p16.pdf` | 2023-11-10 | 2026-10-13T18:46:30Z | `d4edfb90ac185977…` |
| `anatel-res-765-2023-dou-2023-11-10-p17` | `evals/ptbr/sources/raw/dou-2023-11-10-p17.pdf` | 2023-11-10 | 2026-10-13T18:46:34Z | `6f7144bf17061f36…` |
| `anatel-res-765-2023-dou-2023-11-10-p18` | `evals/ptbr/sources/raw/dou-2023-11-10-p18.pdf` | 2023-11-10 | 2026-10-13T18:46:39Z | `e50a77f0bad39b0b…` |
| `anatel-res-765-2023-dou-2023-11-10-p19` | `evals/ptbr/sources/raw/dou-2023-11-10-p19.pdf` | 2023-11-10 | 2026-10-13T18:46:45Z | `8ed28a3054fcc983…` |
| `anatel-res-765-2023-dou-2023-11-10-p20` | `evals/ptbr/sources/raw/dou-2023-11-10-p20.pdf` | 2023-11-10 | 2026-10-13T18:46:49Z | `96c84cbe015e244a…` |
| `anatel-res-765-2023-dou-2023-11-10-p21` | `evals/ptbr/sources/raw/dou-2023-11-10-p21.pdf` | 2023-11-10 | 2026-10-13T18:46:52Z | `ba10ec11444103eb…` |
| `anatel-res-765-2023-dou-2023-11-10-p22` | `evals/ptbr/sources/raw/dou-2023-11-10-p22.pdf` | 2023-11-10 | 2026-10-13T18:46:56Z | `ebc8ebfb3c0eb06a…` |
| `anatel-res-765-2023-dou-2023-11-10-p23` | `evals/ptbr/sources/raw/dou-2023-11-10-p23.pdf` | 2023-11-10 | 2026-10-13T18:46:59Z | `95c65db254492695…` |
| `anatel-res-765-2023-dou-2023-12-26-p13-retificacao` | `evals/ptbr/sources/raw/dou-2023-12-26-p13-retificacao.pdf` | 2023-12-26 | 2026-10-13T18:46:12Z | `a5b75a048955b782…` |
| `anatel-res-765-2023-dou-2024-01-12-p4-retificacao` | `evals/ptbr/sources/raw/dou-2024-01-12-p4-retificacao.pdf` | 2024-01-12 | 2026-10-13T18:46:18Z | `efad54a3d9b91ee9…` |

**Vigência:** o texto capturado é o publicado. A vigência deve ser conferida por dispositivo durante a anotação: Acórdão Anatel nº 228/2024 (a maior parte em vigor a partir de 01/09/2025); Resolução Anatel nº 768/2024 revoga o § 2º do art. 39 do RGC a partir de 01/01/2026; Resolução Anatel nº 777/2025 revogou os arts. 2º a 79 da Resolução 765 (alterações a outros regulamentos). Esses atos posteriores ainda não foram capturados.

## Captura e aprovação de um registro

Antes de alterar o estado de `candidate` para `verified`:

1. Baixar ou capturar o conteúdo diretamente da URL oficial, registrando data/hora de coleta e ferramenta/método utilizado.
2. Registrar `capture_method` (ferramenta/método), `artifact_path` (local do artefato preservado) e `content_type` (tipo de conteúdo), além da data/hora de coleta. Preservar os bytes exatos do artefato capturado; calcular SHA-256 desses bytes sem normalização silenciosa.
3. Conferir título, órgão emissor, identificador do ato e data contra a própria fonte primária.
4. Registrar o artefato preservado e seu hash em manifesto versionado. Se for necessário converter PDF/HTML para texto, calcular e registrar também o hash do texto derivado, mantendo ligação explícita ao hash do original.
5. Atualizar o registro para `verified` somente depois da revisão. O arquivo estruturado `evals/ptbr/SOURCES-REGISTRY.json` registra os três itens acima como `verified`, com SHA-256 e data/hora de coleta preenchidos; este documento resume o estado e não substitui o registro estruturado. O esquema `evals/ptbr/SOURCES-REGISTRY.schema.json` exige hash SHA-256 de 64 caracteres hexadecimais, data de coleta, data de publicação e metadados de captura para registros `verified`; rejeita campos extras e exige hash próprio quando há texto derivado.
6. Se a fonte não estiver acessível, divergir ou não permitir confirmar um campo, manter `candidate` e registrar a lacuna.

## Exclusões

Material não normativo — por exemplo, comentários doutrinários, livros, notícias, páginas comerciais e bases privadas — não entra neste registro nem no corpus do benchmark sem licença ou permissão registrada, conforme a DEC-002 (aprovada em 2026-10-13). Nenhum texto desta página comprova apoio, revisão, parceria ou endosso da Anatel ou de qualquer universidade.

## Limitação

As fontes acima estão capturadas e verificadas quanto à identidade (título, órgão, data) e à integridade (SHA-256). Isso não significa que um corpus de avaliação foi montado: a criação de casos segue `docs/eval/PREREGISTRATION-RGC-v1.md` e `docs/eval/PROTOCOL-GOLDEN-V1.md`.
