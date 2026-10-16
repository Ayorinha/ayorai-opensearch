# [PROPOSTO] Pré-registro — benchmark PT-BR do RGC (v1)

**Estado:** [PROPOSTO] — aguarda decisão do mantenedor  
**Data da proposta:** 2026-10-13  
**Responsável proposto:** Anderson Leon Ayora  
**Repositório:** `Ayorinha/ayorai-opensearch`  
**Escopo:** desenho de avaliação; nenhum caso, dado, fixture ou resultado foi criado por este documento.

## 1. Objetivo e hipótese

O objetivo é medir, de forma reproduzível, a capacidade do AYORAI ATTRACTOR de verificar afirmações em português brasileiro contra o texto oficial do Regulamento Geral de Direitos do Consumidor de Serviços de Telecomunicações (RGC), aprovado pela Resolução Anatel nº 765/2023.

**Hipótese principal (H1):** em um conjunto de avaliação definido e anotado antes da execução, o sistema alcançará acurácia superior à baseline de classe majoritária. A hipótese será avaliada somente após a aprovação deste pré-registro, a liberação da coleta e a conclusão das etapas de proveniência e anotação.

Este estudo é independente. Não implica nem afirma parceria, apoio, revisão, endosso ou validação da Anatel, nem de qualquer universidade ou outra instituição.

## 2. Fonte e proveniência

- **ID de fonte existente:** `anatel-res-765-2023`, registrado em `docs/annotation/SOURCES.md`.
- **Fonte oficial candidata:** https://informacoes.anatel.gov.br/legislacao/resolucoes/2023/1900-resolucao-765
- **Ato:** Resolução Anatel nº 765, de 6 de novembro de 2023.
- **Captura exata dos bytes:** concluída e registrada em #177; texto derivado determinístico documentado em #178.
- **Data, método, metadados e SHA-256:** registrados nos artefatos de proveniência de #177; não recalculados por este documento.
- **Estado do registro:** fonte capturada; os portões posteriores de protocolo, anotação, execução e relatório continuam pendentes.

### Bloqueio obrigatório de coleta

A coleta e a captura foram autorizadas pela decisão DEC-002 (#176), e a captura byte a byte da fonte oficial foi registrada em #177; a derivação determinística do texto está documentada em #178. Isso não inicia a anotação nem autoriza alterar os critérios do protocolo. Nenhum material de terceiros com condições de uso não esclarecidas poderá ser incorporado a fixtures públicos.

## 3. Desenho do estudo

### 3.1 Unidade e composição

A unidade de avaliação será uma afirmação factual atômica, acompanhada do contexto documental necessário para julgá-la. A meta proposta é de **300 casos elegíveis**, sujeita à viabilidade da fonte, à DEC-002 e à qualidade da anotação. Se não for possível atingir esse número sem comprometer a validade ou a proveniência, o tamanho final e a razão serão declarados antes de executar o sistema; não haverá preenchimento artificial de casos.

Categorias de afirmações, definidas antes da coleta:
- prazos e datas;
- direitos do consumidor;
- obrigações da prestadora;
- exceções, condições, limites e hipóteses de inaplicabilidade.

As categorias podem se sobrepor; a regra de anotação deverá definir uma categoria principal e registrar categorias secundárias quando necessário. Os rótulos de referência serão atribuídos por pessoas, com justificativa rastreável ao texto-fonte. O sistema avaliado não poderá gerar ou alterar os rótulos de referência.

### 3.2 Estados de veredito — registro histórico da proposta

A lista abaixo registra a proposta original de 2026-10-13 e não representa o vocabulário aprovado para o benchmark RGC:

- `UNVERIFIED`
- `SUPPORTED`
- `PARTIALLY_SUPPORTED`
- `VERIFIED`
- `CONFLICTING`
- `REFUTED`

**Nota datada (2026-10-15):** conforme a Emenda 2 de `docs/eval/PROTOCOL-GOLDEN-V1.md`, o benchmark RGC usa os cinco vereditos de `rules/judge-2.0.0.json` (`enums.verdict`) com a semântica da ADR-009 (K1–K5), e não a semântica da ADR-002. `VERIFIED` não é rótulo de referência no RGC; corroboração R0–R3 é eixo separado e não é anotada no v1. O mapeamento `ABSTAINED` → `UNVERIFIED` segue a DEC-009 aprovada. A proposta e o estado geral deste documento permanecem **[PROPOSTO]** até o congelamento formal pelo mantenedor.

Casos ambíguos, sem contexto suficiente ou com referência normativa não verificável deverão seguir a regra de `RULE_GAP` do piloto ou ser reescritos/excluídos antes do congelamento, com o motivo registrado no log de exclusões; nunca receber um rótulo por conveniência.

### 3.3 Anotação e isolamento

O protocolo seguirá `docs/eval/PROTOCOL-GOLDEN-V1.md`, incluindo regras de fonte, anotação independente, resolução de divergências, registro de limitações e isolamento dos casos ocultos. A meta de 300 casos não substitui os critérios de qualidade de anotação do protocolo. Se a segunda anotação independente e a concordância mínima especificada no protocolo não forem obtidas, os resultados serão identificados como preliminares e não serão apresentados como avaliação principal.

**Regra de ouro:** casos de teste ocultos NUNCA ficam no repositório público. O conjunto oculto será armazenado fora do repositório público, com acesso controlado. A divisão proposta é 70% desenvolvimento público e 30% avaliação oculta, definida por procedimento reproduzível antes de executar o sistema. Somente metadados permitidos, como tamanho e hash do artefato oculto, poderão ser publicados; nunca os casos, afirmações, trechos, rótulos ou fixtures ocultos.

Não usar casos ocultos para desenvolvimento, ajuste de limiares, seleção de regras ou depuração. O benchmark não será usado para treinar o sistema.

## 4. Métricas e plano estatístico pré-definidos

Relatar, para o conjunto completo elegível e por categoria quando o tamanho permitir:

1. **Acurácia** (accuracy).
2. **Acurácia balanceada** (balanced accuracy).
3. **Macro-F1**.
4. **Tamanho amostral (`n`)**, total e por estado de referência; informar explicitamente estados ausentes.
5. **Intervalos de confiança de 95%** para acurácia, acurácia balanceada e macro-F1. Usar bootstrap percentil com 10.000 reamostragens e seed fixa `20261003`; registrar método e seed no relatório.
6. **Baseline de classe majoritária**, calculada exclusivamente a partir dos rótulos de referência da partição avaliada, com sua acurácia e métricas correspondentes. A baseline não poderá ser usada para alterar o conjunto.
7. **Comparação pareada por McNemar**, teste exato bilateral, comparando as previsões do sistema e da baseline nos mesmos casos, conforme `docs/eval/STATISTICS.md`. Informar o número de pares discordantes e o valor-p; não interpretar significância estatística como prova de validade jurídica.

A ordem dos casos, a versão do conjunto, o SHA do commit do sistema, as configurações, as versões de dependências e os artefatos necessários à reprodução deverão constar no relatório. Previsões ausentes ou inválidas serão reportadas como falha de execução conforme regra congelada antes da avaliação; não serão silenciosamente removidas do denominador nem convertidas em acertos.

Golden v0 e Golden v0.1 são conjuntos de desenvolvimento existentes e deverão ser reportados lado a lado sempre que números dessas avaliações forem citados. Eles não serão misturados ao conjunto RGC nem tratados como evidência de generalização para documentos em português.

## 5. Critérios de sucesso e falha — fixados antes dos dados

Os critérios abaixo são propostos antes da coleta e não poderão ser alterados após a observação dos resultados. Qualquer emenda deverá ser datada, justificada e aprovada antes de uma nova execução; a análise original será preservada.

### Sucesso no critério primário

Declarar que H1 recebeu suporte **somente se todas** as condições forem satisfeitas no conjunto de avaliação definido:
- acurácia do sistema pelo menos **10 pontos percentuais** acima da acurácia da baseline de classe majoritária;
- limite inferior do IC95% da acurácia do sistema acima do valor pontual da acurácia da baseline;
- teste exato de McNemar bilateral contra a baseline com p < 0,05.

Acurácia balanceada e macro-F1 são métricas secundárias obrigatórias; nota: a acurácia balanceada da baseline de classe majoritária equivale a 1/K, onde K é o número de estados presentes na partição avaliada.

Além disso, publicar sempre acurácia, macro-F1, IC95%, matriz de confusão e resultados por categoria/estado, independentemente do sucesso primário. Se a baseline não permitir uma comparação informativa para determinada métrica ou houver estado ausente, declarar a limitação explicitamente.

### Falha, resultado inconclusivo ou regressão

- **Critério primário não satisfeito:** H1 não recebeu suporte; não reclassificar o resultado como sucesso com base em uma métrica secundária.
- **Intervalos largos, amostra insuficiente ou categorias sub-representadas:** resultado inconclusivo para essas dimensões.
- **Erros de proveniência, quebra de isolamento, alteração não autorizada do conjunto ou falha de integridade:** invalidar a execução afetada, documentar a ocorrência e não apresentar seus números como resultado válido.
- **Regressão ou desempenho abaixo da baseline:** publicar os resultados negativos e as limitações; não ocultar, excluir ou substituir casos para melhorar as métricas.

A publicação do resultado é obrigatória mesmo se for negativo, inconclusivo ou contrário à hipótese. Não haverá mudança de regra, limiar, modelo, partição ou caso em resposta aos resultados dentro deste estudo.

## 6. Limitações e afirmações proibidas

O benchmark medirá desempenho somente no escopo, versão da fonte, conjunto de afirmações e procedimento de anotação documentados. Não demonstrará, por si só, capacidade de interpretar toda a legislação brasileira, aconselhar consumidores, determinar direitos em casos concretos ou substituir revisão humana.

Não afirmar:
- certificação, conformidade jurídica ou validação regulatória;
- parceria, apoio, patrocínio, revisão ou endosso da Anatel;
- generalização para todos os documentos em português ou para outros domínios;
- validade jurídica de um veredito apenas porque uma métrica foi alcançada;
- independência ou qualidade de anotação sem evidência correspondente.

A Resolução e suas alterações, ressalvas de vigência, remissões ou consolidação devem ser verificadas contra fontes oficiais no momento da captura. Este documento não interpreta a vigência, a hierarquia ou a aplicabilidade de dispositivos.

## 7. Portões de aprovação e execução

1. Anderson decide explicitamente a DEC-002.
2. A fonte é capturada, preservada, conferida e registrada com metadados e SHA-256, conforme `docs/annotation/SOURCES.md`.
3. O protocolo e as regras de anotação são revistos e aprovados antes de criar casos.
4. A anotação e a separação entre desenvolvimento e teste oculto são concluídas, com trilha de auditoria e critérios de qualidade registrados.
5. O sistema é executado uma vez conforme o plano congelado; configurações, commit e resultados são preservados.
6. O relatório publica métricas, IC95%, baseline, comparação pareada, limitações e qualquer desvio, inclusive resultados negativos.

**Estado atual (2026-10-14):** portão 1 — DEC-002 — cumprido (#176); portão 2 — captura e proveniência da fonte — cumprido (#177; texto derivado determinístico em #178). Portões 3–6 permanecem pendentes: aprovação do protocolo/regras, anotação e separação dos conjuntos, execução congelada e relatório. O executor permanece **[PROPOSTO]** (#179), e só roda com rótulos humanos completos. O piloto humano de 20 casos ainda não foi iniciado. Nenhuma validação, parceria ou resultado experimental é reivindicado.
