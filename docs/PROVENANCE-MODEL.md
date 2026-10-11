# AYORAI ATTRACTOR — Modelo de proveniência (mapeamento proposto)

**Status:** documentação de desenho; não declara implementação integral de W3C PROV-O nem certificação.  
**Referência primária:** W3C, [PROV-O: The PROV Ontology](https://www.w3.org/TR/prov-o/).  
**Escopo:** modelo de proveniência para decisões reproduzíveis, evidência, regras e relatórios do AYORAI ATTRACTOR.

## Explicação simples

O modelo distingue os dados usados, as atividades que os processam e os agentes responsáveis.  
Cada resultado deve apontar para a versão das regras e para os hashes dos conteúdos relevantes.  
A proveniência ajuda a reconstruir como o resultado foi produzido; não prova que uma afirmação é verdadeira.  
Dados pessoais, segredos e conteúdo sem permissão de retenção não devem ser registrados apenas para aumentar a rastreabilidade.  
Este documento é uma proposta de mapeamento, não uma declaração de conformidade formal.

## Mapeamento conceitual

| Conceito PROV-O | Uso proposto no ATTRACTOR | Exemplos de identificadores/atributos |
|---|---|---|
| `prov:Entity` | Conteúdo ou artefato usado/gerado por uma atividade | ID do claim/átomo; referência de evidência; hash do documento normalizado; JSON de regras; entrada e saída canônicas; relatório de avaliação; manifesto de golden |
| `prov:Activity` | Processo que consome entidades e gera outras entidades | recuperação; normalização; validação de offsets; admissibilidade; clustering de independência; execução do Judge; migração versionada; avaliação |
| `prov:Agent` | Pessoa, organização ou agente de software responsável por uma atividade | mantenedor; revisor independente; processo de CI; serviço de execução; componente determinístico do Judge |
| `prov:used` | Relação entre atividade e entidade de entrada | execução do Judge usa entrada canônica, evidências admitidas e arquivo de regras |
| `prov:wasGeneratedBy` | Relação entre entidade gerada e atividade que a produziu | resultado de Judge gerado pela execução identificada |
| `prov:wasAssociatedWith` | Relação entre atividade e agente responsável | execução de CI associada ao workflow; revisão associada ao revisor |
| `prov:wasDerivedFrom` | Derivação de uma entidade a partir de outra | golden derivado ligado ao golden de origem e à tabela de migração |
| `prov:wasInformedBy` | Dependência entre atividades | avaliação que usa resultado de uma execução anterior identificada |
| `prov:wasAttributedTo` | Atribuição de uma entidade a um agente | revisão atribuída ao revisor que a realizou; release atribuída ao mantenedor que a publicou |
| `prov:wasRevisionOf` | Revisão versionada de uma entidade | nova versão de regras ligada à versão anterior sem sobrescrever seu histórico |

Os termos acima são conceitos de modelagem. A existência desta tabela não significa que o software já emita registros PROV-O serializados.

## Campos de proveniência recomendados

| Campo no ATTRACTOR ou artefato | Conceito PROV-O relacionado | Regra |
|---|---|---|
| `entity_id` / identificador estável | `prov:Entity` | Identificador estável dentro do escopo definido; não usar dados pessoais como identificador |
| `content_sha256` | atributo de uma entidade | Hash calculado sobre bytes ou serialização canônica documentada |
| `activity_id` | `prov:Activity` | Identifica uma execução específica, não apenas o nome do tipo de atividade |
| `activity_type` | tipo de atividade | Nome controlado e versionado, por exemplo `judge.evaluate` |
| `started_at`, `ended_at` | atributos temporais da atividade | Timestamp com fuso/UTC definido; ausência não deve ser preenchida por inferência |
| `agent_id`, `agent_type` | `prov:Agent` | Distinguir pessoa, serviço e processo automatizado |
| `judge_rules_version`, `rules_sha256` | entidade de regras usada | Identificar exatamente o conjunto de regras aplicado |
| `input_sha256`, `output_sha256` | entidades de entrada/saída | Calcular pela serialização canônica definida no contrato |
| `source_id`, URL, offsets, hash do trecho | entidade de evidência | Registrar somente metadados necessários e autorizados; manter referência de origem |
| `derived_from` / referência de origem | `prov:wasDerivedFrom` | Obrigatório para artefatos derivados, incluindo goldens migrados |
| `review_status`, `reviewed_sha` | atividade de revisão | A aprovação vale apenas para o SHA efetivamente revisado |
| `workflow_run_id`, commit SHA | atividade de CI | Registrar links e resultado observados; não inferir sucesso antes do término |

Os nomes da coluna de campos são recomendações de mapeamento, não uma declaração de que todos esses campos já existam no schema atual.

## Regras de integridade e auditoria

1. A proveniência de uma decisão deve identificar a entrada, a versão/hash das regras, as referências de evidência admitidas, a versão do software quando disponível e o resultado canônico.
2. Um hash identifica conteúdo, mas não autentica sozinho a identidade do autor, a data, a licença ou a veracidade do conteúdo.
3. Uma atividade deve distinguir entidades usadas de entidades geradas e preservar relações de derivação.
4. Alterações em regras, protocolo ou golden geram novas versões/artefatos; não sobrescrever o histórico congelado.
5. A verificação de integridade deve revelar divergências. Migrações não devem recalcular digests históricos para fazê-los passar.
6. Revisão independente, CI e decisão do mantenedor são eventos distintos e devem ser atribuídos a quem realmente os executou.
7. A retenção de dados deve respeitar finalidade, minimização, permissões e avaliação de LGPD. Não guardar prompts brutos, segredos ou trechos integrais por padrão quando metadados/hashes bastarem.

## Limitações e evidência necessária

Este documento define um mapeamento conceitual para orientar implementação e auditoria. Ele não prova que o repositório já emite PROV-O, que todos os eventos são capturados, que a proveniência é completa ou que o sistema atende a requisitos legais específicos. A implementação futura deve adicionar esquema versionado, testes de serialização e integridade, exemplos de registros e verificação independente. Qualquer afirmação de conformidade deve ser avaliada separadamente com evidência primária e escopo explícito.

## Referência

W3C. *PROV-O: The PROV Ontology*. W3C Recommendation. https://www.w3.org/TR/prov-o/
