**[RASCUNHO — revisão do autor pendente]**

> **Estado atual:** consulte a [fonte única de status](../STATUS.md). Este dossiê preserva seu contexto técnico e não é uma fonte independente de status de implementação.

# AYORAI ATTRACTOR — Dossiê técnico

## Problema

Sistemas generativos podem apresentar uma citação real que não sustenta a afirmação associada. A existência da fonte não basta: é necessário conferir se o trecho citado apoia, contradiz ou não permite concluir o que foi dito. O AYORAI ATTRACTOR procura tornar essa relação entre afirmação e evidência verificável e auditável. Seu escopo não garante detectar toda alucinação, não substitui interpretação jurídica e não constitui certificação ou garantia de exatidão. Consulte o [README](../../README.md).

## Arquitetura

O modelo pode ajudar a analisar afirmações e evidências, mas sua saída é apenas um sinal. O Judge determinístico aplica regras explícitas e versionadas e é a única autoridade do veredito final, conforme a [ADR-009](../adr/ADR-009-deterministic-adjudication-contract.md). A trilha de prova relaciona afirmação, trecho da fonte, localização e proveniência. SHA-256 identifica conteúdo específico e ajuda a detectar alterações; um hash não prova que uma afirmação é verdadeira.

A separação entre análise, autorização do veredito e execução pela aplicação reduz a possibilidade de tratar uma resposta fluente como decisão suficiente. O estado de cada requisito deve ser conferido na [matriz de rastreabilidade](../TRACEABILITY-MASTER.md), que alerta que a existência de arquivo ou teste, isoladamente, não prova o comportamento completo.

## Versões e evidência de engenharia

O repositório identifica as releases [v0.4.0](https://github.com/Ayorinha/ayorai-opensearch/releases/tag/v0.4.0) e [v0.5.0](https://github.com/Ayorinha/ayorai-opensearch/releases/tag/v0.5.0). Os depósitos correspondentes estão referenciados no [registro de propriedade intelectual preexistente](../legal/PRIOR-IP-RECORD.md): [DOI v0.4.0](https://doi.org/10.5281/zenodo.23300849), [DOI v0.5.0](https://doi.org/10.5281/zenodo.23344005) e [DOI de conceito](https://doi.org/10.5281/zenodo.23125082).

O [README](../../README.md) descreve a v0.4.0 como a fase da autoridade única do Judge determinístico, trilha de auditoria e erros estruturados; a v0.5.0 consolida o contrato Judge 2.0, adjudicação determinística, contratos de API, explicações e rastreabilidade gerada. Essas são descrições das versões publicadas, não validação independente nem prova de adequação a um uso institucional específico.

Há workflows configurados de [CI](https://github.com/Ayorinha/ayorai-opensearch/actions/workflows/ci.yml), [segurança](https://github.com/Ayorinha/ayorai-opensearch/actions/workflows/security.yml) e [CodeQL](https://github.com/Ayorinha/ayorai-opensearch/actions/workflows/codeql.yml). Para declarar um commit aprovado, deve-se conferir o job vinculado ao SHA exato; a existência do workflow ou de um badge não significa que uma execução atual esteja verde. Consulte também o [status de engenharia](../STATUS.md).

## Limitações

- Os Goldens são conjuntos sintéticos de desenvolvimento e não demonstram generalização para produção. As métricas e limitações por versão estão descritas em [F1.2-RESULTS.md](../eval/F1.2-RESULTS.md) e na [pré-inscrição do Golden v0.1](../eval/PREREGISTRATION-GOLDEN-v0.1.md). O Golden v0.1 foi reescrito após o autor ter visto resultados por caso; portanto, não é evidência confirmatória independente. Ao citar métricas, Golden v0 e Golden v0.1 devem aparecer lado a lado, conforme a tabela no [README](../../README.md).
- O detector lexical compara elementos como números, datas e sobreposição de palavras. Pode falhar diante de paráfrases fortes, negações implícitas e relações linguísticas complexas; consulte [RUNNER-RGC-v1.md](../eval/RUNNER-RGC-v1.md).
- **Ainda não existe nenhum resultado de benchmark em português.** O piloto exploratório não foi executado pelo sistema e não é um resultado de avaliação.
- Para o benchmark RGC, as fontes foram capturadas ([#177](https://github.com/Ayorinha/ayorai-opensearch/issues/177)) e o texto derivado foi documentado ([#178](https://github.com/Ayorinha/ayorai-opensearch/issues/178)). A DEC-010 foi aprovada na opção A, com meta de aproximadamente um terço de afirmações compostas: decisão [#204](https://github.com/Ayorinha/ayorai-opensearch/pull/204), executor `rgc-eval/0.2.0` com o campo `atoms` [#203](https://github.com/Ayorinha/ayorai-opensearch/pull/203) e Emenda 3 [#205](https://github.com/Ayorinha/ayorai-opensearch/pull/205). O piloto exploratório de 20 casos foi concluído em 16/10/2026: os casos foram redigidos com auxílio de IA e rotulados por Anderson; houve 9 SUPPORTED e 11 REFUTED. O piloto foi descartado e o sistema não foi executado sobre os casos. A DEC-011 foi aprovada em 17/10/2026 e sua Emenda 4 foi incorporada pela [PR #227](https://github.com/Ayorinha/ayorai-opensearch/pull/227). O segundo piloto humano isolado ainda está pendente; o protocolo não está congelado e o conjunto definitivo ainda não foi redigido nem rotulado. Consulte o [pré-registro RGC](../eval/PREREGISTRATION-RGC-v1.md) e o [relatório histórico do piloto descartado](../eval/PILOT-RGC-01-REPORT.md).
- A causa da [issue #182](https://github.com/Ayorinha/ayorai-opensearch/issues/182) foi confirmada e corrigida na [PR #192](https://github.com/Ayorinha/ayorai-opensearch/pull/192), com testes de regressão: o `HttpUrl` validado chegava ao serializador canônico, que rejeitava esse tipo. A URL canônica entra no hash na forma normalizada.
- O sistema não interpreta hierarquia normativa, vigência ou aplicabilidade de dispositivos e não substitui aconselhamento jurídico.

## Caminho até o primeiro resultado RGC

O caminho atual é: executar um segundo piloto exploratório de aproximadamente 10 casos novos com anotação humana isolada de ferramentas de IA; descartar os casos; revisar os achados; obter aprovação explícita para congelar o protocolo; redigir os 300 casos definitivos; obter uma segunda anotação independente e verificar Cohen's kappa ≥ 0,6; custodiar o conjunto oculto fora do repositório público; congelar a configuração; e executar o sistema uma única vez após os rótulos humanos completos. A DEC-011 foi aprovada em 2026-10-17 e a Emenda 4 foi mesclada pela PR #227. O protocolo ainda não está congelado e nenhum resultado de benchmark PT-BR foi validado. O método está descrito no [PROTOCOL-GOLDEN-V1.md](../eval/PROTOCOL-GOLDEN-V1.md) e o executor em [RUNNER-RGC-v1.md](../eval/RUNNER-RGC-v1.md), ainda **[PROPOSTO]**.

A captura das fontes e a existência do executor não significam que o conjunto definitivo tenha sido criado, que o sistema tenha sido executado ou que os resultados tenham sido validados. Não se afirma parceria, apoio ou validação por instituição alguma.

## Referências

[README](../../README.md) · [STATUS](../STATUS.md) · [TRACEABILITY-MASTER](../TRACEABILITY-MASTER.md) · [PREREGISTRATION-RGC-v1](../eval/PREREGISTRATION-RGC-v1.md) · [RUNNER-RGC-v1](../eval/RUNNER-RGC-v1.md)
