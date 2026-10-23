# Classificação documental — v0.6.0

**Data da auditoria:** 2026-10-23  
**Base examinada:** árvore da PR #400 antes desta atualização, SHA `3aeaebbfecae8f1277b4737b074e42d1d95acefa`; inventário reconciliado com a árvore atual da mesma PR.  
**Cobertura:** os 119 arquivos Markdown sob `docs/` existentes antes desta auditoria, mais este próprio inventário recém-criado; total atual de 120 arquivos `.md`. A classificação é por estado documental, não por qualidade técnica nem aprovação científica.

**Definições:** **VIGENTE** = referência ativa ou artefato normativo/proposto ainda relevante (não significa aprovado/congelado); **HISTÓRICO** = registro de uma versão, auditoria, experimento ou snapshot anterior, preservado sem reescrever o passado; **DESATUALIZADO** = afirmação demonstravelmente superada e ainda não corrigida. Nenhum arquivo foi classificado DESATUALIZADO apenas por existir conteúdo sobre duplicatas: a rejeição de `source_id` duplicado já existia antes da PR #399, e a redação da PR foi corrigida. O DOI de conceito `10.5281/zenodo.23125082` é **VIGENTE**; não é um DOI histórico. A v0.5.0 continua sendo a última release publicada, enquanto a v0.6.0 é apenas um rascunho.

**Avisos históricos:** os documentos classificados HISTÓRICO devem conter, logo após o título, aviso datado de 2026-10-23 que identifique o registro como histórico e aponte para a referência vigente indicada na tabela. O aviso não altera nem reescreve os fatos do registro original.

| Estado | Arquivo | Justificativa / referência vigente |
|---|---|---|
| VIGENTE | `docs/ARCHITECTURE.md` | Descreve a arquitetura geral e as fronteiras entre os componentes do ATTRACTOR, servindo como mapa estrutural do sistema. |
| VIGENTE | `docs/AUTHORSHIP.md` | Registra autoria e atribuição do projeto, orientando como reconhecer contribuições sem confundir autoria com ferramentas usadas. |
| VIGENTE | `docs/CONFORMIDADE-BRASIL.md` | Documenta o enquadramento brasileiro considerado pelo projeto e delimita as afirmações de conformidade que exigem evidência. |
| VIGENTE | `docs/DECISIONS-APPROVED.md` | Consolida decisões aceitas pelo mantenedor; é a referência para distinguir regras aprovadas de propostas ainda abertas. |
| VIGENTE | `docs/DECISIONS-PENDING.md` | Lista decisões ainda pendentes, permitindo acompanhar o que não deve ser tratado como regra aprovada. |
| VIGENTE | `docs/DOCKER.md` | Orienta a execução e configuração em contêiner, incluindo as premissas operacionais que precisam ser conferidas antes de implantar. |
| VIGENTE | `docs/EXPERIMENTAL-MODULES.md` | Identifica módulos experimentais e seus limites, evitando apresentar funcionalidades exploratórias como parte estável do produto. |
| VIGENTE | `docs/GLOSSARIO.md` | Padroniza o significado dos termos técnicos usados na documentação e reduz ambiguidades entre conceitos do domínio. |
| VIGENTE | `docs/GUIA-PASSO-A-PASSO.md` | Oferece uma sequência prática de uso do projeto, útil para seguir o fluxo documentado sem substituir os contratos normativos. |
| VIGENTE | `docs/INDEX.md` | Funciona como índice de navegação da documentação e encaminha cada assunto à sua referência especializada. |
| VIGENTE | `docs/INVESTIDORES.md` | Organiza informações voltadas a potenciais apoiadores; deve ser lido como material informativo, não como validação técnica independente. |
| VIGENTE | `docs/MILESTONES.md` | Registra marcos e etapas planejadas do projeto para acompanhar progresso e escopo sem inferir conclusão além do que está registrado. |
| VIGENTE | `docs/PROGRESS.md` | Mantém o acompanhamento do progresso declarado e ajuda a diferenciar trabalho concluído de itens ainda em andamento. |
| VIGENTE | `docs/PROVENANCE-MODEL.md` | Define o modelo de proveniência para relacionar artefatos, fontes e transformações, apoiando rastreabilidade e reprodução. |
| VIGENTE | `docs/SPONSOR_CANDIDATES.md` | Registra candidatos a apoio ou patrocínio e o estado dessa prospecção; não constitui compromisso ou endosso institucional. |
| VIGENTE | `docs/audit/DOC-CLASSIFICATION-v0.6.0.md` | Este próprio inventário é o registro vigente da classificação documental. |
| VIGENTE | `docs/STATUS.md` | É o ponto de consulta do estado atual do repositório, das versões publicadas e das pendências explicitamente registradas. |
| VIGENTE | `docs/STYLE-GUIDE.md` | Estabelece convenções de escrita e apresentação documental para manter consistência entre os arquivos do projeto. |
| VIGENTE | `docs/THREAT-MODEL.md` | Identifica ameaças e pressupostos de segurança considerados pelo projeto, servindo de base para revisar controles e riscos residuais. |
| VIGENTE | `docs/TRACEABILITY-MASTER.md` | Centraliza referências de rastreabilidade entre decisões, mudanças e evidências para permitir auditoria do histórico do projeto. |
| VIGENTE | `docs/adr/ADR-001-namespace.md` | Registra a decisão arquitetural sobre namespaces e sua função na organização e identificação dos elementos do domínio. |
| VIGENTE | `docs/adr/ADR-002-judge-rules.md` | Registra a decisão sobre regras do Judge, delimitando o papel determinístico dessas regras na adjudicação. |
| VIGENTE | `docs/adr/ADR-003-three-state-stance.md` | Formaliza a representação de stance em três estados, evitando reduzir estados semanticamente distintos a uma decisão binária. |
| VIGENTE | `docs/adr/ADR-004-claim-as-input.md` | Documenta a decisão de tratar claims como entrada explícita do fluxo, separando fornecimento de alegações de sua avaliação. |
| VIGENTE | `docs/adr/ADR-005-hybrid-multilingual-stance.md` | Registra a abordagem híbrida e multilíngue para stance e suas premissas de tratamento de idioma. |
| VIGENTE | `docs/adr/ADR-006-metadata-judge-rules.md` | Define a decisão sobre metadados usados pelas regras do Judge e a separação entre dados de entrada e autoridade decisória. |
| VIGENTE | `docs/adr/ADR-009-deterministic-adjudication-contract.md` | Especifica o contrato de adjudicação determinística e preserva a autoridade exclusiva do Judge sobre o veredito. |
| VIGENTE | `docs/adr/ADR-010-verifiable-audit-log.md` | Registra a proposta de log de auditoria verificável e distingue a decisão arquitetural da existência de integração operacional na API. |
| VIGENTE | `docs/adr/README.md` | Indexa os registros de decisão arquitetural (ADRs) e orienta a consulta ao histórico das escolhas de projeto. |
| VIGENTE | `docs/agents.md` | Documenta o papel e as restrições dos agentes no fluxo de trabalho, incluindo os limites de atuação sobre decisões e artefatos. |
| VIGENTE | `docs/annotation/PROTOCOLO.md` | Define o protocolo de anotação e as regras que orientam a produção consistente de rótulos para avaliação. |
| VIGENTE | `docs/annotation/SOURCES.md` | Registra fontes usadas ou admitidas no processo de anotação e orienta a verificação de sua proveniência. |
| VIGENTE | `docs/api/CHANGELOG-API.md` | Descreve mudanças de contrato e operação da API entre versões, apoiando a análise de compatibilidade dos clientes. |
| VIGENTE | `docs/architecture.md` | Apresenta a visão arquitetural complementar e os limites funcionais entre os componentes do sistema. |
| VIGENTE | `docs/architecture/MCP.md` | Documenta a integração MCP e os limites de exposição de ferramentas e recursos por esse protocolo. |
| VIGENTE | `docs/architecture/R13-TENANCY.md` | Especifica o desenho de tenancy e os limites de isolamento considerados para separar contextos de uso. |
| VIGENTE | `docs/architecture/R14-OBSERVABILITY.md` | Define a abordagem de observabilidade e os sinais operacionais destinados a apoiar diagnóstico e acompanhamento. |
| VIGENTE | `docs/architecture/R15-DURABLE-WORKER.md` | Descreve a arquitetura de workers duráveis e as garantias esperadas para execução resiliente de tarefas. |
| VIGENTE | `docs/architecture/R9-DURABLE-ORCHESTRATION.md` | Registra o desenho de orquestração durável e como coordenar etapas sem depender apenas de execução transitória. |
| VIGENTE | `docs/architecture/VERIFICATION-PIPELINE.md` | Explica o pipeline de verificação e a sequência entre entrada, processamento e avaliação determinística. |
| VIGENTE | `docs/assets/brand/README.md` | Define orientações para os ativos de marca do repositório e mantém sua utilização alinhada aos materiais oficiais do projeto. |
| HISTÓRICO | `docs/audit/AUDIT-SINCE-v0.5.0.md` | Registro de auditoria datado, mantido como evidência histórica; consultar docs/STATUS.md para o estado atual. |
| HISTÓRICO | `docs/audit/BRANCH-CLEANUP-2026-10-21.md` | Registro de auditoria datado, mantido como evidência histórica; consultar docs/STATUS.md para o estado atual. |
| VIGENTE | `docs/audit/CORRECTIONS.md` | Mantém o registro de correções documentais e técnicas, permitindo localizar o que foi corrigido e por qual motivo. |
| VIGENTE | `docs/audit/PHASE0.md` | Documenta a auditoria da fase zero e suas constatações como base rastreável para etapas posteriores. |
| HISTÓRICO | `docs/audit/PROCESS-DEVIATIONS-2026-10-21.md` | Registro de auditoria datado, mantido como evidência histórica; consultar docs/STATUS.md para o estado atual. |
| VIGENTE | `docs/eval/ADR-007.md` | Registra a decisão de avaliação correspondente ao ADR-007 e explicita as premissas metodológicas que permanecem aplicáveis. |
| VIGENTE | `docs/eval/ADR-008.md` | Registra a decisão de avaliação correspondente ao ADR-008 e preserva a justificativa para o desenho metodológico adotado. |
| VIGENTE | `docs/eval/AMENDMENT-PROPOSAL-2026-10-20-INVALID-PREDICTION.md` | Documenta uma proposta de emenda para o tratamento de previsões inválidas; permanece referência proposta, não aprovação automática. |
| VIGENTE | `docs/eval/ANNOTATOR-AGREEMENT.md` | Define métricas e procedimentos para medir concordância entre anotadores, incluindo os limites da interpretação estatística. |
| HISTÓRICO | `docs/eval/BASELINE-v0.md` | Resultado/snapshot de avaliação de etapa anterior, preservado para reprodutibilidade; consultar docs/STATUS.md e o pré-registro vigente da avaliação pertinente. |
| HISTÓRICO | `docs/eval/F1-RESULTS.md` | Resultado/snapshot de avaliação de etapa anterior, preservado para reprodutibilidade; consultar docs/STATUS.md e o pré-registro vigente da avaliação pertinente. |
| HISTÓRICO | `docs/eval/F1.2-RESULTS.md` | Resultado/snapshot de avaliação de etapa anterior, preservado para reprodutibilidade; consultar docs/STATUS.md e o pré-registro vigente da avaliação pertinente. |
| VIGENTE | `docs/eval/GOLDEN-NAMING.md` | Padroniza a nomenclatura dos artefatos Golden, apoiando identificação consistente e comparação reprodutível. |
| VIGENTE | `docs/eval/JUDGE-EVAL.md` | Descreve a avaliação do Judge e os critérios usados para analisar seus resultados sem confundir teste com validação externa. |
| VIGENTE | `docs/eval/LOCAL-EVALUATION.md` | Orienta a execução local de avaliações e a interpretação dos resultados reproduzidos no ambiente do projeto. |
| HISTÓRICO | `docs/eval/METHODOLOGY-REVIEW-RGC-PTBR-2026-10-18.md` | Resultado/snapshot de avaliação de etapa anterior, preservado para reprodutibilidade; consultar docs/STATUS.md e o pré-registro vigente da avaliação pertinente. |
| HISTÓRICO | `docs/eval/P0C-RESULTS.md` | Resultado/snapshot de avaliação de etapa anterior, preservado para reprodutibilidade; consultar docs/STATUS.md e o pré-registro vigente da avaliação pertinente. |
| HISTÓRICO | `docs/eval/PHASE-1-CLOSURE.md` | Resultado/snapshot de avaliação de etapa anterior, preservado para reprodutibilidade; consultar docs/STATUS.md e o pré-registro vigente da avaliação pertinente. |
| HISTÓRICO | `docs/eval/PILOT-RGC-01-REPORT.md` | Registro de piloto exploratório descartado, não é benchmark nem resultado vigente; consultar docs/STATUS.md e docs/eval/PREREGISTRATION-RGC-v1.md. |
| VIGENTE | `docs/eval/PILOT-RGC-02-OPERATIONS.md` | Define a operação planejada do piloto RGC 02 e seus pré-requisitos, sem afirmar que o piloto já foi executado. |
| VIGENTE | `docs/eval/PILOT-RGC-02-WORKSHEET.md` | Fornece a planilha de trabalho do piloto RGC 02 para organização controlada de anotações e evidências. |
| VIGENTE | `docs/eval/PREREGISTRATION-E3-LETTUCEDETECT.md` | Registra o pré-registro específico da avaliação E3 LettuceDetect e fixa o escopo metodológico antes da execução. |
| VIGENTE | `docs/eval/PREREGISTRATION-F1.2.md` | Define previamente o protocolo da avaliação F1.2, preservando critérios anteriores à leitura dos resultados. |
| VIGENTE | `docs/eval/PREREGISTRATION-GAP-B.md` | Estabelece o pré-registro do estudo GAP-B e delimita o desenho que deve orientar a avaliação. |
| VIGENTE | `docs/eval/PREREGISTRATION-GOLDEN-v0.1.md` | Preserva o pré-registro do conjunto Golden v0.1 e seus critérios de avaliação reproduzível. |
| VIGENTE | `docs/eval/PREREGISTRATION-H1.md` | Registra a hipótese H1 e as condições confirmatórias planejadas para evitar ajustes posteriores orientados pelos resultados. |
| VIGENTE | `docs/eval/PREREGISTRATION-RGC-v1.md` | Define o pré-registro do protocolo RGC v1; seu estado proposto deve ser respeitado até congelamento formal. |
| VIGENTE | `docs/eval/PREREGISTRATION.md` | Estabelece as regras gerais de pré-registro das avaliações, separando planejamento metodológico de resultados observados. |
| VIGENTE | `docs/eval/PROPOSAL-RGC-STATISTICAL-DESIGN.md` | Apresenta a proposta de desenho estatístico RGC, incluindo escolhas que ainda dependem de aprovação e congelamento. |
| VIGENTE | `docs/eval/PROTOCOL-GOLDEN-V1.md` | Descreve o protocolo Golden v1 e as regras para preparar e avaliar o conjunto de referência. |
| HISTÓRICO | `docs/eval/RESULTS-GAP-B.md` | Resultado/snapshot de avaliação de etapa anterior, preservado para reprodutibilidade; consultar docs/STATUS.md e o pré-registro vigente da avaliação pertinente. |
| VIGENTE | `docs/eval/RUNNER-RGC-v1.md` | Especifica o executor RGC v1, suas entradas e saídas e os controles de execução reprodutível. |
| VIGENTE | `docs/eval/SEMANTIC-DIGEST-V1-REFERENCE.md` | Define a referência do digest semântico v1 para comparar conteúdo normalizado de forma determinística. |
| VIGENTE | `docs/eval/SQLITE-SCHEMA-V2-MIGRATION.md` | Documenta a migração do esquema SQLite v2 e os cuidados para preservar integridade e compatibilidade dos dados. |
| VIGENTE | `docs/eval/STATISTICS.md` | Explica os métodos estatísticos empregados nas avaliações e os limites de interpretação dos intervalos e estimativas. |
| VIGENTE | `docs/eval/TRACEABILITY.md` | Descreve como rastrear avaliações, entradas, versões e resultados para permitir reprodução e auditoria. |
| VIGENTE | `docs/evolution.md` | Resume a evolução técnica do projeto e relaciona as mudanças de arquitetura e capacidades ao longo do tempo. |
| HISTÓRICO | `docs/history/PROGRESS-2026-10-03.md` | Snapshot histórico preservado; não representa o estado atual. Consultar docs/STATUS.md e docs/TRACEABILITY-MASTER.md. |
| HISTÓRICO | `docs/history/STATUS-SNAPSHOTS.md` | Snapshot histórico preservado; não representa o estado atual. Consultar docs/STATUS.md e docs/TRACEABILITY-MASTER.md. |
| VIGENTE | `docs/institutional/AUDITORIA-DOCUMENTO-TECNICO-v1.1.md` | Registra a auditoria do documento técnico v1.1, permitindo rastrear suas verificações e ressalvas. |
| VIGENTE | `docs/institutional/DOSSIE-TECNICO.md` | Consolida o dossiê técnico institucional e reúne referências para avaliar escopo, arquitetura e evidências declaradas. |
| VIGENTE | `docs/institutional/PLANO-DE-TRABALHO-12M.md` | Organiza o plano de trabalho de 12 meses e suas etapas propostas, sem presumir aprovação ou execução futura. |
| VIGENTE | `docs/institutional/PROPOSTA-UNIVERSIDADE.md` | Apresenta a proposta de colaboração universitária e o escopo a discutir, sem representar parceria já formalizada. |
| VIGENTE | `docs/judge2/IN-PROCESS-OBJECT-FORGERY.md` | Documenta os riscos e controles de falsificação de objetos em processo no Judge 2, com foco na integridade do fluxo. |
| VIGENTE | `docs/judge2/TRACEABILITY.md` | Especifica a rastreabilidade interna do Judge 2 entre entradas, regras aplicadas e resultado adjudicado. |
| VIGENTE | `docs/judge2/TRUTH-TABLE.md` | Expõe a tabela-verdade do Judge 2 para tornar explícitas as combinações de estados e seus resultados determinísticos. |
| HISTÓRICO | `docs/launch/POST-v0.2.0-draft.md` | Rascunho de comunicação de versão anterior, não aprovado para publicação; revisar contra a release alvo e consultar docs/STATUS.md. |
| VIGENTE | `docs/legal/CLA-DRAFT.md` | Mantém o rascunho do acordo de licença de contribuidor para revisão; não deve ser interpretado como instrumento assinado. |
| VIGENTE | `docs/legal/LICENSING-OPTIONS.md` | Compara opções de licenciamento consideradas pelo projeto e registra alternativas para decisão futura. |
| VIGENTE | `docs/legal/MODEL-LICENSE-POLICY.md` | Define a política proposta para licenças de modelos e critérios de uso e proveniência associados. |
| VIGENTE | `docs/legal/PRIOR-IP-RECORD.md` | Registra a declaração de propriedade intelectual prévia para fins de histórico e governança documental. |
| VIGENTE | `docs/manual/01-visao-geral.md` | Apresenta a visão geral do produto, seus objetivos, componentes e limites de uso. |
| VIGENTE | `docs/manual/02-arquitetura.md` | Explica a arquitetura do produto e as relações entre seus componentes principais. |
| VIGENTE | `docs/manual/03-judge.md` | Descreve o Judge, sua autoridade determinística e a separação entre sugestão do modelo e veredito. |
| VIGENTE | `docs/manual/04-api.md` | Documenta endpoints, autenticação e contratos de uso da API para consumidores e operadores. |
| VIGENTE | `docs/manual/05-operacao.md` | Orienta configuração, inicialização e operação do serviço nos ambientes suportados. |
| VIGENTE | `docs/manual/06-seguranca.md` | Reúne os controles e procedimentos de segurança documentados para implantação e manutenção. |
| VIGENTE | `docs/manual/07-reprodutibilidade.md` | Explica como reproduzir experimentos e resultados com versões, entradas e configurações identificadas. |
| VIGENTE | `docs/manual/08-avaliacao.md` | Descreve os procedimentos de avaliação e como interpretar métricas sem extrapolar as evidências disponíveis. |
| VIGENTE | `docs/manual/09-auditoria.md` | Orienta a auditoria de registros e artefatos para reconstruir decisões e verificar rastreabilidade. |
| VIGENTE | `docs/manual/10-governanca.md` | Expõe os papéis, aprovações e limites de governança para alterações e decisões do projeto. |
| VIGENTE | `docs/manual/README.md` | Indexa os capítulos do manual técnico e orienta a leitura por assunto. |
| VIGENTE | `docs/observability/METRICS.md` | Define as métricas de observabilidade e o propósito operacional de cada sinal registrado. |
| VIGENTE | `docs/optimization/R11-GEPA.md` | Registra a abordagem experimental R11-GEPA de otimização e seu contexto técnico dentro do projeto. |
| VIGENTE | `docs/provider-contract.md` | Define o contrato esperado dos provedores integrados, incluindo comportamento e compatibilidade de interface. |
| VIGENTE | `docs/providers.md` | Lista e explica os provedores suportados e as responsabilidades de integração de cada um. |
| VIGENTE | `docs/release/RELEASE-PROVENANCE.md` | Documenta como registrar proveniência de builds e releases para relacionar artefatos a seus commits de origem. |
| HISTÓRICO | `docs/release/v0.3.0.md` | Notas de uma versão anterior já publicada; consultar docs/STATUS.md para a versão publicada vigente e docs/release/v0.6.0.md para o rascunho não publicado. |
| HISTÓRICO | `docs/release/v0.4.0.md` | Notas de uma versão anterior já publicada; consultar docs/STATUS.md para a versão publicada vigente e docs/release/v0.6.0.md para o rascunho não publicado. |
| HISTÓRICO | `docs/release/v0.5.0.md` | Notas de uma versão anterior já publicada; consultar docs/STATUS.md para a versão publicada vigente e docs/release/v0.6.0.md para o rascunho não publicado. |
| VIGENTE | `docs/release/v0.6.0.md` | Notas da v0.6.0 em preparação, com data oficial 2026-10-23 e publicação autorizada pelo mantenedor; ainda não publicada. |
| VIGENTE | `docs/reports/JUDGE-2.0.0-GATES-REPORT.md` | Registra os resultados e limites dos gates do Judge 2.0.0, como evidência técnica de execução identificada. |
| VIGENTE | `docs/research-contract.md` | Define os limites e compromissos do processo de pesquisa para distinguir método, evidência e conclusão. |
| VIGENTE | `docs/research/README.md` | Indexa os documentos de pesquisa e orienta a consulta ao estado e escopo de cada linha de investigação. |
| VIGENTE | `docs/research/RN-001-second-layer-questioning.md` | Registra a nota de pesquisa RN-001 sobre questionamento em segunda camada e suas hipóteses exploratórias. |
| VIGENTE | `docs/research/STATE-OF-THE-ART.md` | Sintetiza o estado da arte pesquisado e serve como referência para situar o projeto frente ao conhecimento publicado. |
| VIGENTE | `docs/research/TECH-RADAR-2026-10.md` | Registra o radar técnico de outubro de 2026 e as tecnologias ou tendências consideradas nessa data. |
| VIGENTE | `docs/security/API-AUTH.md` | Define o contrato normativo de autenticação da API, os cabeçalhos aceitos e as variáveis de configuração relevantes. |
| VIGENTE | `docs/security/RED-TEAM.md` | Documenta o escopo e os procedimentos de testes adversariais, distinguindo exercícios realizados de riscos ainda não avaliados. |

## Resultado de cobertura

Inventário gerado a partir da árvore Git recursiva: 119 arquivos preexistentes mais este próprio documento, totalizando **120 arquivos** listados uma única vez. Nenhum arquivo fora de `docs/` faz parte deste inventário. A classificação deve ser atualizada quando novos arquivos Markdown forem adicionados ou quando uma decisão do mantenedor tornar um artefato vigente, histórico ou comprovadamente desatualizado.
