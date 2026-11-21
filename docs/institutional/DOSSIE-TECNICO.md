**[RASCUNHO — revisão do autor pendente]**

> **Estado atual:** consulte a [fonte única de status](../STATUS.md). Este dossiê preserva seu contexto técnico e não é uma fonte independente de status de implementação.

# AYORAI ATTRACTOR — Dossiê técnico

## Problema

Sistemas generativos podem apresentar uma citação real que não sustenta a afirmação associada. A existência da fonte não basta: é necessário conferir se o trecho citado apoia, contradiz ou não permite concluir o que foi dito. O AYORAI ATTRACTOR procura tornar essa relação entre afirmação e evidência verificável e auditável. Seu escopo não garante detectar toda alucinação, não substitui interpretação jurídica e não constitui certificação ou garantia de exatidão. Consulte o [README](../../README.md).

## Arquitetura

O modelo pode ajudar a analisar afirmações e evidências, mas sua saída é apenas um sinal. O Judge determinístico aplica regras explícitas e versionadas e é a única autoridade do veredito final, conforme a [ADR-009](../adr/ADR-009-deterministic-adjudication-contract.md). A trilha de prova relaciona afirmação, trecho da fonte, localização e proveniência. SHA-256 identifica conteúdo específico e ajuda a detectar alterações; um hash não prova que uma afirmação é verdadeira.

A separação entre análise, autorização do veredito e execução pela aplicação reduz a possibilidade de tratar uma resposta fluente como decisão suficiente. O estado de cada requisito deve ser conferido no [status de engenharia](../STATUS.md) e, para o Judge 2.0, na [matriz de rastreabilidade gerada](../judge2/TRACEABILITY.md). O antigo `TRACEABILITY-MASTER.md` é um snapshot histórico, não a fonte normativa atual.

## Versões e evidência de engenharia

A versão publicada vigente é a [v0.8.0](https://github.com/Ayorinha/ayorai-opensearch/releases/tag/v0.8.0), com data oficial de 2026-11-13 e tag no commit `92ea5eb86b69724b05834d98c326e8315bb6b655`. Os workflows CI, Security e CodeQL da tag concluíram com sucesso. A release acrescentou, entre outros itens, `POST /v1/check` para verificação de afirmações contra documentos enviados, `POST /v1/fields` para comparação de campos documentais e vínculos de rastreabilidade com páginas/trechos; também consolidou auditoria estrita de dependências, ambiente NLI separado, SBOM CycloneDX e permissões mínimas nos workflows. A descrição e os limites exatos estão na [release v0.8.0](https://github.com/Ayorinha/ayorai-opensearch/releases/tag/v0.8.0) e no [CHANGELOG](../../CHANGELOG.md).

**Identificadores persistentes:** DOI de conceito (todas as versões): [10.5281/zenodo.23125082](https://doi.org/10.5281/zenodo.23125082). DOI de versão v0.7.0: [10.5281/zenodo.24045951](https://doi.org/10.5281/zenodo.24045951). O DOI específico da v0.8.0 ainda estava pendente de registro no Zenodo em 2026-11-21; não deve ser inferido a partir do DOI de conceito. A [CITATION.cff](../../CITATION.cff) e o [registro de autoria e propriedade intelectual](../legal/PRIOR-IP-RECORD.md) preservam essa distinção.

A versão de pacote `0.8.0` não significa que a validação científica ou a prontidão operacional estejam concluídas. O [status de engenharia](../STATUS.md) é a fonte única para a situação atual, e as evidências de cada release são específicas da tag e do SHA testado.


## Limitações

- Os Goldens são conjuntos sintéticos de desenvolvimento e não demonstram generalização para produção. As métricas e limitações por versão estão descritas em [F1.2-RESULTS.md](../eval/F1.2-RESULTS.md) e na [pré-inscrição do Golden v0.1](../eval/PREREGISTRATION-GOLDEN-v0.1.md). O Golden v0.1 foi reescrito após o autor ter visto resultados por caso; portanto, não é evidência confirmatória independente. Ao citar métricas, Golden v0 e Golden v0.1 devem aparecer lado a lado, conforme a tabela no [README](../../README.md).
- O detector lexical compara elementos como números, datas e sobreposição de palavras. Pode falhar diante de paráfrases fortes, negações implícitas e relações linguísticas complexas; consulte [RUNNER-RGC-v1.md](../eval/RUNNER-RGC-v1.md).
- **Avaliação em português:** existe o PT-CP-Audit, uma avaliação interna sobre um corpus do Código Penal brasileiro (152 casos). No split test só-manuais (n=40), v5→v6 apresentou acurácia de 65,0%→72,5% e apoio falso de 25,9%→14,8%, sem significância estatística pelo McNemar exato pareado (p=0,453125). O resultado é específico do corpus e não prova generalização externa. **Benchmark RGC PT-BR validado ainda não existe**; o piloto exploratório RGC não foi executado pelo sistema e não é resultado de avaliação. Consulte [PT-CP-Audit](../../evals/pt-cp-audit/RESULTS.md).
- Para o benchmark RGC, as fontes foram capturadas ([#177](https://github.com/Ayorinha/ayorai-opensearch/issues/177)) e o texto derivado foi documentado ([#178](https://github.com/Ayorinha/ayorai-opensearch/issues/178)). A DEC-010 foi aprovada na opção A, com meta de aproximadamente um terço de afirmações compostas: decisão [#204](https://github.com/Ayorinha/ayorai-opensearch/pull/204), executor `rgc-eval/0.2.0` com o campo `atoms` [#203](https://github.com/Ayorinha/ayorai-opensearch/pull/203) e Emenda 3 [#205](https://github.com/Ayorinha/ayorai-opensearch/pull/205). O piloto exploratório de 20 casos foi concluído em 16/10/2026: os casos foram redigidos com auxílio de IA e rotulados por Anderson; houve 9 SUPPORTED e 11 REFUTED. O piloto foi descartado e o sistema não foi executado sobre os casos. A DEC-011 foi aprovada em 17/10/2026 e sua Emenda 4 foi incorporada pela [PR #227](https://github.com/Ayorinha/ayorai-opensearch/pull/227). O segundo piloto humano isolado ainda está pendente; o protocolo não está congelado e o conjunto definitivo ainda não foi redigido nem rotulado. Consulte o [pré-registro RGC](../eval/PREREGISTRATION-RGC-v1.md) e o [relatório histórico do piloto descartado](../eval/PILOT-RGC-01-REPORT.md).
- A causa da [issue #182](https://github.com/Ayorinha/ayorai-opensearch/issues/182) foi confirmada e corrigida na [PR #192](https://github.com/Ayorinha/ayorai-opensearch/pull/192), com testes de regressão: o `HttpUrl` validado chegava ao serializador canônico, que rejeitava esse tipo. A URL canônica entra no hash na forma normalizada.
- O sistema não interpreta hierarquia normativa, vigência ou aplicabilidade de dispositivos e não substitui aconselhamento jurídico.

## Caminho até o primeiro resultado RGC

O caminho atual é: executar um segundo piloto exploratório de aproximadamente 10 casos novos com anotação humana isolada de ferramentas de IA; descartar os casos; revisar os achados; obter aprovação explícita para congelar o protocolo; redigir os 300 casos definitivos; obter uma segunda anotação independente e verificar Cohen's kappa ≥ 0,6; custodiar o conjunto oculto fora do repositório público; congelar a configuração; e executar o sistema uma única vez após os rótulos humanos completos. A DEC-011 foi aprovada em 2026-10-17 e a Emenda 4 foi mesclada pela PR #227. O protocolo ainda não está congelado e nenhum resultado de benchmark PT-BR foi validado. O método está descrito no [PROTOCOL-GOLDEN-V1.md](../eval/PROTOCOL-GOLDEN-V1.md) e o executor em [RUNNER-RGC-v1.md](../eval/RUNNER-RGC-v1.md), ainda **[PROPOSTO]**.

A captura das fontes e a existência do executor não significam que o conjunto definitivo tenha sido criado, que o sistema tenha sido executado ou que os resultados tenham sido validados. Não se afirma parceria, apoio ou validação por instituição alguma.

## Referências

[README](../../README.md) · [STATUS](../STATUS.md) · [Judge 2.0 Traceability](../judge2/TRACEABILITY.md) · [TRACEABILITY-MASTER histórico](../TRACEABILITY-MASTER.md) · [PREREGISTRATION-RGC-v1](../eval/PREREGISTRATION-RGC-v1.md) · [RUNNER-RGC-v1](../eval/RUNNER-RGC-v1.md)
