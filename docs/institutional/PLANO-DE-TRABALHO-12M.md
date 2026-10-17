**[RASCUNHO — revisão do autor pendente]**

# Plano de trabalho — ciclo de pesquisa de 12 meses

## Objetivo e ponto de partida

Organizar a preparação, anotação, avaliação e documentação do benchmark RGC em português brasileiro, além de uma demonstração e publicação técnica. O cronograma depende da disponibilidade de pessoas, aprovação do protocolo, decisões do mantenedor e recursos.

As fontes foram capturadas ([#177](https://github.com/Ayorinha/ayorai-opensearch/issues/177)) e o texto derivado está documentado ([#178](https://github.com/Ayorinha/ayorai-opensearch/issues/178)); o executor continua [PROPOSTO](https://github.com/Ayorinha/ayorai-opensearch/issues/179). A DEC-010 foi aprovada na opção A (~1/3 de afirmações compostas): decisão [#204](https://github.com/Ayorinha/ayorai-opensearch/pull/204), executor `rgc-eval/0.2.0` com `atoms` [#203](https://github.com/Ayorinha/ayorai-opensearch/pull/203) e Emenda 3 [#205](https://github.com/Ayorinha/ayorai-opensearch/pull/205). O piloto exploratório de 20 casos foi concluído em 16/10/2026; os casos foram redigidos por um assistente de IA (Claude) e rotulados por Anderson, com distribuição de 9 SUPPORTED e 11 REFUTED. O piloto foi descartado, e o sistema não foi executado sobre os casos. Os achados estão na DEC-011 pendente ([#206](https://github.com/Ayorinha/ayorai-opensearch/pull/206)); a opção A para a Parte 2 foi escolhida em 17/10/2026 ([#207](https://github.com/Ayorinha/ayorai-opensearch/pull/207)). O conjunto definitivo ainda não foi redigido nem rotulado. **Ainda não existe nenhum resultado de benchmark em português.**

## Metas trimestrais

| Período | Metas | Entregáveis verificáveis | Critério de conclusão |
|---|---|---|---|
| **T1** | **Piloto exploratório de 20 casos concluído (16/10/2026; descartado);** aprovar integralmente a DEC-011; preparar Emenda 4; executar segundo piloto de aproximadamente 10 casos; congelar o protocolo; depois redigir o corpus definitivo de 300 casos e concluir os rótulos humanos antes da primeira execução. | Registro do piloto e ambiguidades; decisão DEC-011; protocolo versionado e congelado; corpus definitivo, manifesto e hashes; relatório da execução com commit, parâmetros e limitações. | O piloto exploratório não conta como avaliação do sistema. Não executar o sistema antes dos gates de protocolo e rotulagem. A execução confirmatória só ocorre uma vez, depois dos rótulos humanos completos. |
| **T2** | Segundo anotador independente; anotação independente; cálculo de concordância; resolução documentada de divergências; versão v1 e relatório. | Registros por anotador; cálculo de kappa; divergências e resoluções; conjunto v1; relatório com métricas e resultados negativos. | Alcançar o critério do protocolo (**kappa ≥ 0,6**) antes de chamar o conjunto v1. Se não alcançado, documentar o resultado e não reclassificar o conjunto. |
| **T3** | Pesquisar melhoria do detector de posição lexical em português, respeitando a ADR-008 e o escopo aprovado. | Plano experimental prévio; mudança em fluxo separado; testes; comparação com baseline; relatório de erros e regressões. | Não alterar retrospectivamente o benchmark congelado; identificar claramente qualquer nova avaliação. |
| **T4** | Preparar demonstração reproduzível e publicação técnica. | Instruções de reprodução; demonstração com dados permitidos; pacote de resultados, hashes e versões; manuscrito ou relatório submetido à revisão. | Outra pessoa consegue seguir o procedimento; o texto distingue resultados observados de hipóteses e não sugere endosso institucional. |

## Salvaguardas

- O conjunto oculto ficará fora do repositório público; divulgar somente hash e metadados permitidos.
- Não executar o sistema sobre casos antes de concluir os rótulos humanos.
- Congelar protocolo e critérios antes da execução confirmatória; alterações posteriores precisam de registro datado e justificativa.
- Publicar resultados negativos, inconclusivos e limitações.
- Identificar a primeira execução em v1-draft como preliminar, com anotador único.
- Nenhuma etapa pressupõe parceria, apoio ou validação externa.

## Orçamento — preencher pelo autor

Valores intencionalmente em branco para preenchimento pelo autor.

| Categoria | Premissa/unidade | Valor estimado (R$) |
|---|---|---|
| Coordenação e autoria técnica | __________ | __________ |
| Anotador independente | __________ | __________ |
| Revisão técnica externa | __________ | __________ |
| Custódia e controle de acesso do conjunto oculto | __________ | __________ |
| Infraestrutura e armazenamento | __________ | __________ |
| Preparação da demonstração | __________ | __________ |
| Preparação editorial/publicação | __________ | __________ |
| Despesas adicionais | __________ | __________ |
| **Total estimado** | | **__________** |

## Riscos e respostas

- **Atraso na anotação:** ajustar cronograma e registrar a causa, sem reduzir critérios silenciosamente.
- **Concordância insuficiente:** revisar instruções e ambiguidades, documentando a decisão.
- **Resultado abaixo da baseline ou inconclusivo:** publicar e investigar sem alterar retroativamente casos ou critérios.
- **Limitações do detector:** separar melhorias de engenharia da avaliação congelada e medir regressões em conjunto de desenvolvimento apropriado.
- **Sem custódia independente:** não chamar o conjunto de oculto até haver solução acordada.

## Referências

[Protocolo Golden v1](../eval/PROTOCOL-GOLDEN-V1.md) · [Pré-registro RGC](../eval/PREREGISTRATION-RGC-v1.md) · [Executor proposto](../eval/RUNNER-RGC-v1.md) · [Status](../STATUS.md)
