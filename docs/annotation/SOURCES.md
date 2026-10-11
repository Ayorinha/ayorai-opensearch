# Registro de fontes primárias — benchmark PT-BR

**Estado:** inventário de candidatos; nenhum registro abaixo é evidência aprovada para o benchmark até que a captura exata seja preservada, validada e identificada por SHA-256.  
**Escopo:** atos normativos oficiais e metadados de proveniência.  
**Limite:** este registro não interpreta a legislação, sua hierarquia, vigência, revogação ou aplicabilidade.

## Base legal para o tratamento de textos normativos

A Lei nº 9.610/1998, art. 8º, IV, exclui os textos de tratados ou convenções, leis, decretos, regulamentos, decisões judiciais e demais atos oficiais da proteção autoral prevista nessa lei. Essa referência não elimina a obrigação de registrar proveniência, origem, versão, data de coleta e hash, nem resolve eventuais direitos sobre compilações, comentários ou outros materiais não normativos.

Fonte primária: [Lei nº 9.610, de 19 de fevereiro de 1998 — Planalto](https://www.planalto.gov.br/ccivil_03/leis/l9610.htm).

## Candidatos de fonte

| ID proposto | Título | Órgão | URL oficial | Data de publicação | Estado de captura |
|---|---|---|---|---|---|
| `anatel-res-765-2023` | Resolução Anatel nº 765, de 6 de novembro de 2023 — aprova o Regulamento Geral de Direitos do Consumidor de Serviços de Telecomunicações (RGC) | Agência Nacional de Telecomunicações (Anatel) | [Página oficial da resolução](https://informacoes.anatel.gov.br/legislacao/resolucoes/2023/1900-resolucao-765) | 2023-11-06 | Candidato; captura exata, data de coleta e SHA-256 pendentes |
| `planalto-lei-9610-1998` | Lei nº 9.610, de 19 de fevereiro de 1998 | Presidência da República — Planalto | [Texto oficial](https://www.planalto.gov.br/ccivil_03/leis/l9610.htm) | 1998-02-19 | Candidato; captura exata, data de coleta e SHA-256 pendentes |
| `planalto-lgpd-13709-2018` | Lei nº 13.709, de 14 de agosto de 2018 — Lei Geral de Proteção de Dados Pessoais | Presidência da República — Planalto | [Texto oficial](https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm) | 2018-08-14 | Candidato; captura exata, data de coleta e SHA-256 pendentes |

As datas acima identificam a data do ato, não atestam a vigência atual. Na consulta à página oficial da Resolução 765/2023, a própria Anatel apresenta ressalva de vigência parcial e remissões a atos posteriores. Por isso, a situação temporal deve ser capturada por dispositivo e com referência à fonte primária pertinente; não inferir vigência ou situação consolidada apenas a partir desta tabela. A página e o conteúdo exato devem ser conferidos novamente no momento da captura.

## Captura e aprovação de um registro

Antes de alterar o estado de `candidate` para `verified`:

1. Baixar ou capturar o conteúdo diretamente da URL oficial, registrando data/hora de coleta e ferramenta/método utilizado.
2. Preservar os bytes exatos do artefato capturado; calcular SHA-256 desses bytes sem normalização silenciosa.
3. Conferir título, órgão emissor, identificador do ato e data contra a própria fonte primária.
4. Registrar o artefato preservado e seu hash em manifesto versionado. Se for necessário converter PDF/HTML para texto, calcular e registrar também o hash do texto derivado, mantendo ligação explícita ao hash do original.
5. Atualizar o registro para `verified` somente depois da revisão. O esquema `evals/ptbr/SOURCES-REGISTRY.schema.json` exige hash de 64 caracteres hexadecimais, data de coleta e data de publicação para registros verificados.
6. Se a fonte não estiver acessível, divergir ou não permitir confirmar um campo, manter `candidate` e registrar a lacuna.

## Exclusões

Material não normativo — por exemplo, comentários doutrinários, livros, notícias, páginas comerciais e bases privadas — não entra neste registro nem no corpus do benchmark enquanto a DEC-002 permanecer bloqueada. Nenhum texto desta página comprova apoio, revisão, parceria ou endosso da Anatel ou de qualquer universidade.

## Limitação

Este documento é um inventário inicial. Ainda não há aqui artefatos de fonte capturados nem hashes conferidos. Portanto, nenhum dos candidatos está marcado como `verified`, e não se afirma que um corpus jurídico foi montado ou validado.
