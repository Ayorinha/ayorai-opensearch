**[RASCUNHO — revisão do autor pendente]**

# Plano de trabalho — ciclo de pesquisa de 12 meses

## Objetivo e ponto de partida

Organizar a preparação, anotação, avaliação e documentação do benchmark RGC em português brasileiro, além de uma demonstração e publicação técnica. O cronograma depende da disponibilidade de pessoas, aprovação do protocolo, decisões do mantenedor e recursos.

As fontes foram capturadas ([#177](https://github.com/Ayorinha/ayorai-opensearch/issues/177)) e o texto derivado está documentado ([#178](https://github.com/Ayorinha/ayorai-opensearch/issues/178)); o executor continua [PROPOSTO](https://github.com/Ayorinha/ayorai-opensearch/issues/179); a anotação não foi iniciada. **Ainda não existe nenhum resultado de benchmark em português.**

## Metas trimestrais

| Período | Metas | Entregáveis verificáveis | Critério de conclusão |
|---|---|---|---|
| **T1** | Piloto de anotação; congelamento do protocolo; corpus v1-draft com 300 casos; primeira execução após rótulos humanos completos. | Registro do piloto e ambiguidades; protocolo versionado; corpus, manifesto e hashes; relatório da execução com commit, parâmetros e limitações. | Artefatos revisados e reproduzíveis. O v1-draft será identificado como anotação de uma pessoa, não como resultado principal. |
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