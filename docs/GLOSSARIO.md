# Glossário do AYORAI ATTRACTOR

**[RASCUNHO — revisão do autor pendente]**

Este glossário apresenta, em linguagem introdutória, termos usados na documentação técnica e de avaliação do AYORAI ATTRACTOR. As definições resumem os documentos-fonte vinculados; em caso de divergência, prevalece o documento normativo indicado.

## Judge (juiz determinístico)

Componente que aplica regras versionadas e determinísticas para produzir o veredito factual final a partir de afirmações e evidências admissíveis. Modelos probabilísticos podem auxiliar etapas anteriores, mas não escolhem nem substituem o veredito. Fonte: [ADR-009 — contrato determinístico de adjudicação](adr/ADR-009-deterministic-adjudication-contract.md) e [regras Judge 2.0.0](../rules/judge-2.0.0.json).

## Afirmação (*claim*)

Proposição factual que pode ser examinada à luz de um documento e de evidências identificáveis. Exemplo inventado e neutro: “A biblioteca abre às 8h.” Fonte: [ADR-009](adr/ADR-009-deterministic-adjudication-contract.md) e [protocolo Golden v1](eval/PROTOCOL-GOLDEN-V1.md).

## Átomo

Parte factual verificável de uma afirmação composta. Conforme a Emenda 3, cada átomo é registrado com offsets de início e fim relativos ao texto da afirmação; os trechos devem estar ordenados, não se sobrepor e não ser vazios. Uma afirmação simples, sem `atoms`, é avaliada como um único átomo. Fontes: [Emenda 3 do protocolo Golden v1](eval/PROTOCOL-GOLDEN-V1.md) e [executor RGC, seção 2](eval/RUNNER-RGC-v1.md).

## Evidência

Documento ou trecho documental usado para avaliar uma afirmação. Para participar da decisão, a evidência precisa cumprir os critérios aplicáveis de admissibilidade, como offsets válidos, correspondência com a fonte e uma relação de apoio ou contradição registrada. Fonte: [ADR-009, seção 6 — Admissibilidade](adr/ADR-009-deterministic-adjudication-contract.md).

## Cluster (grupo de evidências dependentes)

Conjunto de evidências tratadas como uma única fonte porque dependem umas das outras, por exemplo por terem a mesma URL canônica, a mesma origem declarada ou o mesmo conteúdo. O Judge conta clusters, e não itens de evidência, para que republicações e cópias não sejam contadas como confirmação independente; proveniência ausente não é tratada como prova de independência. Fontes: [ADR-006](adr/ADR-006-metadata-judge-rules.md), [ADR-009, seção 7](adr/ADR-009-deterministic-adjudication-contract.md) e [implementação](../src/ayorai_attractor/verification/clusters.py).

## Stance (posição da evidência)

Relação atribuída entre uma evidência e a afirmação ou átomo: pode indicar apoio (SUPPORTS), contradição (CONTRADICTS) ou uma relação neutra que não sustenta o veredito. A posição é um sinal de entrada; a decisão factual final continua sob responsabilidade do Judge determinístico. Fonte: [ADR-009](adr/ADR-009-deterministic-adjudication-contract.md) e [executor RGC](eval/RUNNER-RGC-v1.md).

## Vereditos do Judge

O Judge 2.0.0 define cinco vereditos factuais. Eles são diferentes do estado de decisão (DECIDED, ABSTAINED ou INVALID_INPUT); VERIFIED não pertence ao vocabulário de vereditos do Judge 2.0.0. Fontes: [ADR-009, seção 2](adr/ADR-009-deterministic-adjudication-contract.md), [regras Judge 2.0.0](../rules/judge-2.0.0.json) e [Emenda 2 do protocolo Golden v1](eval/PROTOCOL-GOLDEN-V1.md).

### SUPPORTED

A afirmação ou átomo tem pelo menos um cluster admissível de apoio e nenhum cluster admissível de contradição. Em uma afirmação composta, o veredito global SUPPORTED exige que todos os átomos sejam SUPPORTED. Fonte: [ADR-009, seções 7 e 9](adr/ADR-009-deterministic-adjudication-contract.md).

### PARTIALLY_SUPPORTED

Veredito reservado a uma afirmação composta: pelo menos uma parte está apoiada, nenhuma parte está refutada ou em conflito e pelo menos uma parte permanece sem confirmação suficiente. Não é um veredito para um átomo isolado. Fonte: [ADR-009, seção 9](adr/ADR-009-deterministic-adjudication-contract.md) e [Emenda 2 do protocolo](eval/PROTOCOL-GOLDEN-V1.md).

### REFUTED

Há pelo menos um cluster admissível de contradição e nenhum cluster admissível de apoio para o átomo. Em uma afirmação composta, a regra de precedência determina REFUTED se algum átomo receber esse veredito. Fonte: [ADR-009, seções 7 e 9](adr/ADR-009-deterministic-adjudication-contract.md).

### UNVERIFIED

Não há clusters admissíveis de apoio nem de contradição para o átomo. Em uma afirmação composta, o resultado global será UNVERIFIED quando, após aplicar a precedência definida, nenhum átomo estabelecer apoio, refutação ou conflito. Fonte: [ADR-009, seções 7 e 9](adr/ADR-009-deterministic-adjudication-contract.md).

### CONFLICTING

Existem evidências admissíveis tanto de apoio quanto de contradição para o átomo. Em uma afirmação composta, o veredito global será CONFLICTING se houver átomo em conflito e nenhum átomo REFUTED tiver acionado a regra de maior precedência. Fonte: [ADR-009, seções 7 e 9](adr/ADR-009-deterministic-adjudication-contract.md).

## ABSTAINED e mapeamento DEC-009

ABSTAINED é um estado de decisão, não um dos cinco vereditos: o Judge não emite veredito factual e mantém verdict=null. Para a pontuação do benchmark RGC, a DEC-009 determina o mapeamento de ABSTAINED para UNVERIFIED; esse mapeamento de avaliação não transforma abstenção em veredito interno do Judge. Fontes: [ADR-009, seção 4](adr/ADR-009-deterministic-adjudication-contract.md), [protocolo Golden v1, Emenda 2](eval/PROTOCOL-GOLDEN-V1.md) e [executor RGC](eval/RUNNER-RGC-v1.md).

## RULE_GAP

Marcador de que as regras de anotação não permitem decidir um caso com clareza; não é um veredito do Judge. Conforme o protocolo, seu uso fica restrito ao piloto exploratório, e sua frequência é reportada separadamente, sem entrar no kappa nem nas métricas do sistema. Fonte: [Emenda 2 do protocolo Golden v1](eval/PROTOCOL-GOLDEN-V1.md) e [relatório do piloto exploratório](eval/PILOT-RGC-01-REPORT.md).

## Robustez R0–R3

Robustez descreve a força e a independência da evidência e não altera o veredito. Os níveis são: **R0** — nenhum cluster decisório admissível; **R1** — um único cluster; **R2** — dois ou mais clusters, mas a independência não pode ser plenamente confirmada por proveniência incompleta; **R3** — dois ou mais clusters com proveniência completa. Fonte: [ADR-009, seção 8 — Robustez](adr/ADR-009-deterministic-adjudication-contract.md).

## Hash de entrada e hash de saída (RFC 8785)

Os campos input_sha256 e output_sha256 são hashes SHA-256 calculados sobre representações canônicas do JSON, usando a RFC 8785 (JSON Canonicalization Scheme), para que o mesmo conteúdo possa ser identificado de modo consistente. O hash identifica conteúdo e auxilia a rastreabilidade; isoladamente, não prova que uma afirmação seja verdadeira. O hash de saída é calculado antes de inserir o próprio campo output_sha256. Fonte: [ADR-009, seção 10 e emenda de 2026-10-12](adr/ADR-009-deterministic-adjudication-contract.md).

## Golden

Conjunto de avaliação com casos e rótulos de referência usados para comparar as previsões de um sistema com a anotação de referência. No projeto, os Goldens v0 e v0.1 são conjuntos sintéticos de desenvolvimento e não demonstram generalização; o benchmark RGC em português é um conjunto distinto, ainda em preparação, e não tem resultado. As versões e os conjuntos derivados têm escopos próprios e não devem ser misturados nem alterados fora das regras de governança aplicáveis. Fontes: [protocolo Golden v1](eval/PROTOCOL-GOLDEN-V1.md), [dossiê técnico](institutional/DOSSIE-TECNICO.md) e [ADR-009](adr/ADR-009-deterministic-adjudication-contract.md).

## Pré-registro

Documento que especifica antecipadamente o desenho proposto, as fontes, as métricas, os critérios de análise e os limites de uma avaliação. O pré-registro do benchmark RGC está marcado como [PROPOSTO] e não deve ser confundido com protocolo formalmente congelado ou com resultado experimental. Fonte: [pré-registro RGC v1](eval/PREREGISTRATION-RGC-v1.md) e [protocolo Golden v1](eval/PROTOCOL-GOLDEN-V1.md).

## Emenda

Registro datado de uma alteração ou esclarecimento do protocolo, preservando a sequência de decisões e o histórico do desenho de avaliação. O protocolo prevê que alterações sejam documentadas por emenda, em vez de introduzidas silenciosamente. Fonte: [protocolo Golden v1](eval/PROTOCOL-GOLDEN-V1.md).

## Piloto exploratório

Etapa limitada usada para identificar ambiguidades nas instruções de anotação antes de preparar o conjunto definitivo. O piloto exploratório de 20 casos foi concluído em 16/10/2026, foi descartado e o sistema não foi executado sobre esses casos; portanto, não é resultado de benchmark. Fonte: [relatório do piloto RGC PT-BR 01](eval/PILOT-RGC-01-REPORT.md).

## Conjunto oculto

Partição de avaliação mantida fora do repositório público e protegida contra acesso por quem desenvolve ou ajusta o sistema antes da avaliação. O protocolo prevê 30% dos casos como conjunto oculto e permite publicar seu hash sem divulgar seu conteúdo. Fonte: [protocolo Golden v1, seção “Separação oculta”](eval/PROTOCOL-GOLDEN-V1.md) e [pré-registro RGC v1](eval/PREREGISTRATION-RGC-v1.md).

## Cohen's kappa e limite 0,6

O kappa de Cohen mede a concordância entre dois anotadores levando em conta a concordância esperada ao acaso. O protocolo define o limiar de **kappa ≥ 0,6** para que o conjunto passe a ser denominado v1; esse valor ainda precisa ser medido no processo de anotação independente. Fonte: [protocolo Golden v1, fase de anotação 2](eval/PROTOCOL-GOLDEN-V1.md) e [proposta de colaboração universitária](institutional/PROPOSTA-UNIVERSIDADE.md).

## Execução única

Execução do sistema realizada uma única vez após a conclusão dos rótulos humanos e o congelamento dos critérios, sem usar os casos de teste para ajustar regras, limiares ou o sistema. O objetivo é preservar a separação entre anotação de referência e avaliação; qualquer desvio precisa ser documentado. Fonte: [protocolo Golden v1, fases e regras de isolamento](eval/PROTOCOL-GOLDEN-V1.md) e [pré-registro RGC v1](eval/PREREGISTRATION-RGC-v1.md).
