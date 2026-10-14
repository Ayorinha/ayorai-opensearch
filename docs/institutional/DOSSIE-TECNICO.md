**[RASCUNHO — revisão do autor pendente]**

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
- **Ainda não existe nenhum resultado de benchmark em português.** O pré-registro e o executor proposto não são resultados experimentais.
- Para o benchmark RGC, as fontes foram capturadas ([#177](https://github.com/Ayorinha/ayorai-opensearch/issues/177)) e o texto derivado foi documentado ([#178](https://github.com/Ayorinha/ayorai-opensearch/issues/178)); o executor continua [PROPOSTO](https://github.com/Ayorinha/ayorai-opensearch/issues/179) e a anotação não foi iniciada. O estado consta no [pré-registro RGC](../eval/PREREGISTRATION-RGC-v1.md).
- A [issue #182](https://github.com/Ayorinha/ayorai-opensearch/issues/182) registra que uma requisição válida com `evidence[].canonical_url` pode retornar `INVALID_INPUT / SCHEMA_VIOLATION`. A causa indicada é provável, não confirmada independentemente. A correção afeta o hash canônico e exige decisão do mantenedor.
- O sistema não interpreta hierarquia normativa, vigência ou aplicabilidade de dispositivos e não substitui aconselhamento jurídico.

## Caminho até o primeiro resultado RGC

O caminho proposto é: realizar o piloto humano; revisar e congelar as regras de anotação; criar o conjunto inicial com rótulos e justificativas; obter uma segunda anotação independente; medir concordância e registrar divergências; separar e custodiar o conjunto oculto fora do repositório público; congelar a configuração; executar apenas com rótulos humanos completos; publicar métricas, intervalos de confiança, baseline, resultados negativos e limitações. O método está descrito no [PROTOCOL-GOLDEN-V1.md](../eval/PROTOCOL-GOLDEN-V1.md) e o executor em [RUNNER-RGC-v1.md](../eval/RUNNER-RGC-v1.md), ainda **[PROPOSTO]**.

A captura das fontes e a existência do executor não significam que a anotação, a execução ou a validação tenham ocorrido. Não se afirma parceria, apoio ou validação por instituição alguma.

## Referências

[README](../../README.md) · [STATUS](../STATUS.md) · [TRACEABILITY-MASTER](../TRACEABILITY-MASTER.md) · [PREREGISTRATION-RGC-v1](../eval/PREREGISTRATION-RGC-v1.md) · [RUNNER-RGC-v1](../eval/RUNNER-RGC-v1.md)
