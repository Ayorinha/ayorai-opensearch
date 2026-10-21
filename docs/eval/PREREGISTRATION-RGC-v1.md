# [PROPOSTO] Pré-registro — benchmark PT-BR do RGC (v1)

**Estado:** [PROPOSTO] — DEC-011 aprovada; o protocolo ainda aguarda revisão do segundo piloto e congelamento formal  
**Data da proposta:** 2026-10-13  
**Responsável proposto:** Anderson Leon Ayora  
**Repositório:** `Ayorinha/ayorai-opensearch`  
**Escopo:** desenho de avaliação; nenhum caso, dado, fixture ou resultado foi criado por este documento.

**Leitura vigente (2026-10-21):** os §§ 1, 4 (itens 6–7) e 5 devem ser lidos em conjunto com a [Emenda 6 ao final deste documento](#emenda-6-2026-10-21--baseline-primária-e-descritiva-dec-014-aprovada-pelo-mantenedor). A redação original desses parágrafos é preservada como registro histórico; a emenda explicita a interpretação vigente para a baseline primária e descritiva.

## 1. Objetivo e hipótese

O objetivo é medir, de forma reproduzível, a capacidade do AYORAI ATTRACTOR de verificar afirmações em português brasileiro contra o texto oficial do Regulamento Geral de Direitos do Consumidor de Serviços de Telecomunicações (RGC), aprovado pela Resolução Anatel nº 765/2023.

**Hipótese principal (H1):** em um conjunto de avaliação definido e anotado antes da execução, o sistema alcançará acurácia superior à baseline de classe majoritária. A hipótese será avaliada somente após a aprovação deste pré-registro, a liberação da coleta e a conclusão das etapas de proveniência e anotação.

Este estudo é independente. Não implica nem afirma parceria, apoio, revisão, endosso ou validação da Anatel, nem de qualquer universidade ou outra instituição.

## 2. Fonte e proveniência

- **ID de fonte existente:** `anatel-res-765-2023`, registrado em `docs/annotation/SOURCES.md`.
- **Página de referência oficial capturada:** https://informacoes.anatel.gov.br/legislacao/resolucoes/2023/1900-resolucao-765
- **Limite de uso:** a página informa ressalvas sobre vigência e remete a atos posteriores; a vigência aplicável deve ser conferida por dispositivo com fontes primárias pertinentes, não inferida apenas desta página.
- **Ato:** Resolução Anatel nº 765, de 6 de novembro de 2023.
- **Captura exata dos bytes:** concluída e registrada em #177; texto derivado determinístico documentado em #178.
- **Data, método, metadados e SHA-256:** registrados nos artefatos de proveniência de #177; não recalculados por este documento.
- **Estado do registro:** fonte capturada; os portões posteriores de protocolo, anotação, execução e relatório continuam pendentes.

### Autorização de coleta (DEC-002)

A coleta e a captura foram autorizadas pela decisão DEC-002 (#176), e a captura byte a byte da fonte oficial foi registrada em #177; a derivação determinística do texto está documentada em #178. Isso não inicia a anotação nem autoriza alterar os critérios do protocolo. Nenhum material de terceiros com condições de uso não esclarecidas poderá ser incorporado a fixtures públicos.

## 3. Desenho do estudo

### 3.1 Unidade e composição

A unidade de avaliação será uma afirmação factual atômica, acompanhada do contexto documental necessário para julgá-la. A meta proposta é de **300 casos elegíveis**, sujeita à viabilidade da fonte, à DEC-002 e à qualidade da anotação. Se não for possível atingir esse número sem comprometer a validade ou a proveniência, o tamanho final e a razão serão declarados antes de executar o sistema; não haverá preenchimento artificial de casos.

Categorias de afirmações, definidas antes da coleta:
- prazos e datas;
- direitos do consumidor;
- obrigações da prestadora;
- exceções, condições, limites e hipóteses de inaplicabilidade.

**Nota datada (2026-10-17):** a expressão “afirmação factual atômica” acima é a redação original de 2026-10-13. Desde a Emenda 3 (DEC-010, opção A), a unidade de avaliação é a afirmação simples ou composta; afirmações compostas trazem átomos anotados (§3.2). A redação original é preservada como histórica.

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

**Nota datada (2026-10-16) — Emenda 3 / DEC-010:** conforme a decisão do mantenedor, opção A, afirmações compostas serão anotadas com o campo `atoms`, incluindo `start_offset` e `end_offset` relativos ao texto da afirmação; o campo `text` é opcional e, quando presente, deve corresponder exatamente ao trecho. Afirmações simples não levam `atoms`. Todo caso `PARTIALLY_SUPPORTED` deve ser composto e conter `atoms`; casos compostos podem receber qualquer um dos cinco vereditos. A meta é que cerca de um terço dos casos definitivos seja composto, e a proporção efetiva será relatada. Os átomos são anotados antes do rótulo, e a execução exige casos rotulados. Ver [Emenda 3 do protocolo](PROTOCOL-GOLDEN-V1.md#emenda-3-2026-10-16--afirmações-compostas-dec-010-opção-a). Esta nota não altera o estado **[PROPOSTO]** do pré-registro.

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

**Nota datada (2026-10-21) — DEC-017:** a redação acima é preservada como registro histórico. A interpretação vigente está na [Emenda 7](#emenda-7-2026-10-21--registros-ausentes-e-predições-inválidas-dec-017-opção-a).

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

**Nota histórica (2026-10-21) — PR #326:** a redação original de H1 foi marcada como histórica e a Emenda 8 foi apresentada como aprovada. A nota corretiva vigente abaixo esclarece que essa aprovação não é operativa nesta execução.

**Nota corretiva vigente (2026-10-21) — DEC-018 permanece pendente:** o Prompt Mestre vigente exige manter decisões científicas não decididas pelo mantenedor como pendentes. O texto de Emenda 8 ao final é uma proposta não normativa até decisão explícita; a redação original de H1 e §5 permanece preservada.

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

**Registro histórico de estado (2026-10-14; atualizado pelas notas datadas abaixo):** portão 1 — DEC-002 — cumprido (#176); portão 2 — captura e proveniência da fonte — cumprido (#177; texto derivado determinístico em #178). O piloto exploratório inicial de 20 casos foi concluído em 2026-10-16, descartado e não executado pelo sistema. A DEC-011 foi aprovada em 2026-10-17 e a Emenda 4 foi incorporada pela PR #227. Permanecem pendentes o segundo piloto humano isolado, a revisão pós-piloto, o congelamento formal do protocolo, a anotação definitiva, a separação dos conjuntos, a execução única e o relatório. O executor permanece **[PROPOSTO]** (#179). Nenhuma validação, parceria ou resultado experimental é reivindicado.


**Nota datada (2026-10-17) — DEC-011 aprovada, execução ainda condicionada aos gates:** Anderson aprovou as três partes da DEC-011. Aplicam-se as regras da [Emenda 4 do protocolo](PROTOCOL-GOLDEN-V1.md#emenda-4-2026-10-17--regras-de-anotação-após-o-piloto-dec-011-aprovada): ausência de evidência implica `UNVERIFIED`; `REFUTED` exige contradição explícita; para texto retificado, seguir o texto vigente, ignorar texto superado e marcar `rectified: true`; excluir do v1 afirmações que convertam “preferencialmente” em obrigação sem suporte textual explícito. O segundo piloto será exploratório, terá cerca de 10 casos novos, será anotado sem ferramentas de IA e será descartado. O protocolo não está congelado, os 300 casos definitivos não foram redigidos e nenhum resultado de benchmark PT-BR é reivindicado.


**Nota corretiva datada (2026-10-21) — restauração do histórico do pré-registro:** a PR #274 (merge commit `c639d0fda7a6fb8ab29bb438611ee536b1f3ddc2`) alterou a redação de H1 e dos §§4–5 deste arquivo sem registrar aqui uma emenda datada aprovada, apesar de a DEC-014 e a Emenda 5 do protocolo afirmarem que a decisão de baseline não altera este pré-registro. Esta correção restaura nesses trechos a redação existente imediatamente antes da PR #274; não apaga nem reescreve o histórico Git, e não invalida a implementação técnica da baseline B. A divergência entre o pré-registro restaurado e a Emenda 5 do protocolo permanece explicitamente pendente de uma decisão documental própria, datada e aprovada antes de qualquer avaliação confirmatória. Nenhuma execução é autorizada por esta nota.

Atualização datada (2026-10-21) — resolução documental: a Emenda 6 foi incorporada pela PR #288 (merge SHA `5a587ecb64abc6359c8fe36b8194b67dee3edda9`). A pendência citada na nota corretiva anterior é histórica e foi resolvida quanto à definição B/A: a Emenda 6 acrescenta a interpretação aprovada, preservando a redação original. Permanecem [PROPOSTO] o protocolo e a decisão separada de congelamento; nenhum piloto ou benchmark foi executado por esta atualização.


## Emenda 6 (2026-10-21) — baseline primária e descritiva (DEC-014, aprovada pelo mantenedor)

 para a hipótese H1 e a avaliação confirmatória, a baseline B é a classe majoritária derivada exclusivamente dos rótulos humanos de referência da partição pública de desenvolvimento (70%). O rótulo majoritário deve ser determinado e registrado antes de qualquer execução na partição oculta, e aplicado sem alteração aos mesmos casos avaliados. A baseline A, calculada a partir dos rótulos da própria partição avaliada, é somente uma referência descritiva da prevalência observada; não é classificador operacional e não fundamenta H1. Em caso de empate na baseline B, aplicar a ordem fixa do vocabulário `judge2` implementada por `majority_label` em `evals/ptbr/rgc_eval.py`; não introduzir desempate manual. Esta emenda preserva como registro histórico a redação original dos §§1, 4 e 5 acima e define a interpretação aplicável ao plano confirmatório daqui em diante. O documento e o protocolo permanecem **[PROPOSTO]**; esta emenda não congela o protocolo, não autoriza criar/rotular casos nem executar o sistema, e não produz resultados de benchmark.


## Emenda 7 (2026-10-21) — registros ausentes e predições inválidas (DEC-017, opção A)

Por aprovação explícita do mantenedor em 2026-10-21, o contrato de avaliação distingue integridade da entrada e qualidade da saída por caso:

1. O arquivo de rótulos humanos deve conter exatamente um rótulo para cada caso elegível; caso sem rótulo, rótulo para caso inexistente, caso duplicado, registro ausente ou estrutura inconsistente interrompe a execução. Não descartar, imputar nem remover silenciosamente esses registros.
2. Quando existe uma predição para o caso, mas seu estado/valor não pode ser mapeado para o vocabulário RGC `judge2`, registrar `INVALID_PREDICTION`, manter o caso no denominador e contar a predição como incorreta.
3. O relatório deve informar a contagem de `INVALID_PREDICTION`. A baseline e o denominador não podem ser ajustados após observar resultados confirmatórios.
4. Esta emenda prevalece sobre a interpretação da redação histórica do §4; a redação anterior permanece intacta acima para rastreabilidade.

O executor já implementa o mapeamento de saída inválida e a validação de rótulos completos; os testes sintéticos verificam ambos os lados da distinção. Esta emenda não altera o estado geral **[PROPOSTO]**, não congela o protocolo, não cria nem rotula casos, não autoriza o piloto 02 ou execução do ATTRACTOR sobre casos RGC e não produz métricas RGC.


## Proposta de Emenda 8 (2026-10-21) — escopo confirmatório de H1 (DEC-018, opção A; PENDENTE)

Texto proposto para decisão explícita do mantenedor; DEC-018 permanece **PENDENTE**. Se aprovada futuramente, a regra proposta será:

1. **Partição oculta (~90 casos):** é a única partição primária para testar H1 e aplicar o critério confirmatório pré-registrado.
2. **Partição pública (~210 casos):** uso somente para desenvolvimento e métricas descritivas/exploratórias; não entra no teste confirmatório de H1 e seus resultados devem ser apresentados separadamente.
3. O relatório deve identificar explicitamente a partição avaliada e preservar os hashes/contagens das entradas. O executor deve exigir a declaração `hidden` ou `development` e não calcular/relatar H1 como testada quando a partição declarada for `development`.
4. Esta emenda não altera os critérios numéricos de H1, não congela o protocolo e não autoriza executar o sistema em casos RGC. O protocolo permanece **[PROPOSTO]**; o piloto 02 humano e os demais gates seguem pendentes.
