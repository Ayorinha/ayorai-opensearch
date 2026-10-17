**[RASCUNHO — revisão do autor pendente]**

# Proposta de colaboração em pesquisa

## Objetivo

Convidar uma instituição acadêmica, ainda a definir, a avaliar uma colaboração de pesquisa sobre rastreabilidade e verificação de afirmações produzidas por sistemas de inteligência artificial. Esta proposta não pressupõe parceria, apoio, validação ou compromisso de qualquer instituição. Escopo, responsabilidades e termos dependerão de discussão e aprovação formal.

**Estado do benchmark:** fontes oficiais capturadas ([#177](https://github.com/Ayorinha/ayorai-opensearch/issues/177)), texto derivado documentado ([#178](https://github.com/Ayorinha/ayorai-opensearch/issues/178)), executor [PROPOSTO](https://github.com/Ayorinha/ayorai-opensearch/issues/179). A DEC-010 foi aprovada na opção A (~1/3 de afirmações compostas): decisão [#204](https://github.com/Ayorinha/ayorai-opensearch/pull/204), executor `rgc-eval/0.2.0` com `atoms` [#203](https://github.com/Ayorinha/ayorai-opensearch/pull/203) e Emenda 3 [#205](https://github.com/Ayorinha/ayorai-opensearch/pull/205). O piloto exploratório de 20 casos foi concluído em 16/10/2026; os casos foram redigidos por um assistente de IA (Claude) e rotulados por Anderson. Distribuição: 9 SUPPORTED e 11 REFUTED. O piloto foi descartado, e o sistema não foi executado sobre os casos ([relatório proposto do piloto](../eval/PILOT-RGC-01-REPORT.md)). Seus achados estão na DEC-011, ainda pendente ([#206](https://github.com/Ayorinha/ayorai-opensearch/pull/206)); Anderson escolheu a opção A para a Parte 2 em 17/10/2026 ([#207](https://github.com/Ayorinha/ayorai-opensearch/pull/207)). O conjunto definitivo ainda não foi redigido nem rotulado. **Ainda não existe resultado de benchmark em português.**

## Contribuições solicitadas

### Segundo anotador independente

Solicita-se uma segunda pessoa para rotular independentemente os mesmos casos, sem ver os rótulos da primeira pessoa durante a anotação. O procedimento seguirá [PROTOCOL-GOLDEN-V1.md](../eval/PROTOCOL-GOLDEN-V1.md), fase de anotação independente, incluindo o cálculo de kappa de Cohen. O critério pré-definido é **kappa ≥ 0,6** antes de denominar o conjunto v1. Divergências serão resolvidas em conjunto e registradas caso a caso. Esse critério **ainda não foi medido nem alcançado**.

### Custódia do conjunto oculto

Solicita-se avaliar a custódia externa ao repositório público do conjunto de teste oculto, correspondente a **30% dos casos**, conforme o [protocolo](../eval/PROTOCOL-GOLDEN-V1.md). O arquivo não deverá ser publicado nem ficar acessível a quem executa ou ajusta o sistema antes da avaliação. Poderá ser divulgado o SHA-256, sem revelar o conteúdo. A forma de custódia, controle de acesso, retenção e descarte deverá ser acordada; esta proposta não presume que já exista custódia institucional.

### Revisão técnica externa

Solicita-se revisão independente do desenho experimental, critérios de inclusão e exclusão, qualidade da anotação, métricas, intervalos de confiança, baseline, tratamento de resultados negativos e reprodutibilidade. A revisão deverá distinguir falhas do método, limitações dos dados e questões ainda não avaliadas.

## Contribuições oferecidas

- **Coautoria em publicações**, condicionada à contribuição efetiva, à concordância das pessoas envolvidas e às regras editoriais aplicáveis.
- **Acesso ao código público**, no [repositório AYORAI ATTRACTOR](https://github.com/Ayorinha/ayorai-opensearch).
- **Acesso aos dados públicos e metadados de proveniência** que puderem ser redistribuídos conforme suas condições de uso.
- Transparência sobre método, decisões, limitações e resultados, inclusive negativos.

Dados ocultos, informações restritas e materiais com condições de uso não esclarecidas não serão tratados como dados públicos. O compartilhamento deverá ser acordado previamente.

## Governança e publicação

Antes do início, as partes deverão definir responsabilidades, autoria, supervisão, custódia, critérios de publicação, tratamento de divergências e registro de alterações ao protocolo. O sistema não deverá ser executado sobre os casos durante a anotação, para evitar influenciar os rótulos de referência.

A publicação deverá informar método, versões, hashes relevantes, resultados completos e limitações. Não deverá declarar generalização para todo o português, conformidade jurídica ou validação regulatória com base apenas neste estudo.

## Propriedade intelectual preexistente

Consultar o arquivo [NOTICE](../../NOTICE) e o [Registro de autoria e de propriedade intelectual pré-existente](../legal/PRIOR-IP-RECORD.md). São referências para discussão e análise pelas partes; esta proposta não interpreta juridicamente esses documentos nem antecipa a titularidade de resultados futuros.

Antes de qualquer atividade conjunta, recomenda-se que as partes e suas áreas competentes examinem os documentos e definam por escrito o tratamento da base preexistente e dos eventuais resultados novos. Esta seção não é aconselhamento jurídico nem substitui análise pelas assessorias competentes.

## Próxima etapa

Uma conversa exploratória poderá avaliar disponibilidade de anotador independente, custódia do conjunto oculto e revisão externa. Nenhuma instituição é nomeada ou apresentada como participante nesta versão.
