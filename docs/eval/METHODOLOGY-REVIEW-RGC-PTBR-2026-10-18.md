# Revisão metodológica crítica — benchmark RGC PT-BR

**Estado:** proposta de revisão; não aprova nem congela o protocolo.  
**Data:** 2026-10-18  
**Escopo:** revisão documental do pré-registro, protocolo de anotação, plano estatístico e ficha do piloto 02.  
**Fora do escopo:** criar/rotular casos do piloto ou do conjunto definitivo, executar o sistema, alterar o Judge, alterar Golden, alterar hashes ou modificar decisões aprovadas.

## 1. Síntese executiva

A base existente é promissora: há pré-registro, proveniência da fonte oficial, regras de anotação, um piloto exploratório explicitamente descartado, uma ficha em branco para o piloto 02, isolamento proposto para o conjunto oculto e uma decisão explícita sobre o baseline primário (DEC-014).

**Recomendação:** não congelar ainda. Antes, resolver ou registrar formalmente os pontos de consistência abaixo, realizar o piloto humano 02 sem IA e sem executar o sistema, revisar os achados e só então tomar uma decisão explícita de congelamento.

Esta revisão é uma análise documental. Não constitui revisão jurídica, revisão estatística independente, validação institucional nem resultado experimental.

## 2. Documentos examinados

- `docs/eval/PREREGISTRATION-RGC-v1.md`
- `docs/eval/PROTOCOL-GOLDEN-V1.md`
- `docs/eval/STATISTICS.md`
- `docs/eval/PILOT-RGC-02-WORKSHEET.md`
- `docs/eval/PILOT-RGC-01-REPORT.md`
- `docs/DECISIONS-PENDING.md`
- `docs/STATUS.md`

As conclusões abaixo referem-se ao conteúdo desses documentos no estado consultado. Antes de qualquer aprovação final, confirmar que a revisão continua alinhada à `main` e a todas as decisões/PRs posteriores.

## 3. Achados prioritários

### M-01 — Escopo histórico da matriz 6×6 precisa ficar explícito (sem defeito RGC comprovado)

**Evidência:** `docs/eval/RUNNER-RGC-v1.md` já especifica o vocabulário `judge2` de cinco estados para RGC e reserva `adr002` de seis estados como alternativa histórica não usada no RGC. `docs/eval/STATISTICS.md` descreve a matriz 6×6 para os estados ADR-002. Portanto, a documentação consultada não demonstra, por si só, um defeito no RGC.

**Risco residual:** leitores podem interpretar a estatística 6×6 como universal se não notarem a distinção de vocabulário no executor.

**Recomendação:** tratar como esclarecimento de escopo, não como bug confirmado. Na revisão de implementação, conferir os testes de `evals/ptbr/rgc_eval.py` e `tests/test_rgc_eval_runner.py`; se confirmarem o contrato de cinco rótulos, explicitar em `STATISTICS.md` que a matriz 6×6 é legada e que RGC usa o vocabulário `judge2`. Não alterar Goldens históricos.

**Critério de encerramento:** escopo documentado e teste do executor confirmando o vocabulário de cinco estados no RGC.

### M-02 — Distinguir linha de previsão ausente de previsão inválida por caso

**Evidência:** `docs/eval/RUNNER-RGC-v1.md` já afirma que previsões `INVALID_PREDICTION` permanecem no denominador e contam como erro, enquanto casos sem rótulo, rótulos inexistentes e casos duplicados interrompem a execução. `docs/eval/STATISTICS.md` diz que previsões ausentes são rejeitadas, mas não define, nesse arquivo genérico, se “ausente” significa linha/registro faltante no arquivo ou saída inválida do Judge.

**Risco residual:** confundir erro de formato/integridade do conjunto com saída inválida por caso pode levar a regras distintas para denominador e falhas técnicas.

**Recomendação:** preservar a regra já declarada no executor: saída inválida por caso conta como erro no denominador; estrutura de entrada incompleta/inconsistente aborta a execução. Confirmar essa distinção nos testes e garantir que o relatório registre as contagens correspondentes. Não excluir casos ou repetir execução oportunisticamente.

**Critério de encerramento:** distinção entre falha de integridade de entrada e previsão inválida por caso está coberta por teste e descrita no relatório.

### M-03 — Alinhar o plano de IC entre executor, pré-registro e estatísticas gerais

**Evidência:** o pré-registro e `docs/eval/RUNNER-RGC-v1.md` já indicam bootstrap percentil com 10.000 reamostragens e seed `20261003` para accuracy, balanced accuracy e macro-F1; o executor documenta usar a mesma sequência de reamostragem para as três métricas. `docs/eval/STATISTICS.md` é mais genérico e só descreve explicitamente o IC de accuracy.

**Risco residual:** a documentação estatística genérica pode não refletir o contrato RGC; ainda é preciso confirmar implementação, tratamento de classes ausentes em reamostragens e cobertura dos testes.

**Recomendação:** não inventar um novo método nem alterar o plano aprovado nesta revisão. Comparar implementação e testes com o executor/pré-registro; documentar os detalhes efetivamente implementados (incluindo comportamento com classes ausentes) e deixar qualquer mudança metodológica para emenda prévia explícita.

**Critério de encerramento:** código, testes, pré-registro e relatório concordam sobre métricas, número de reamostragens, seed, método percentil e tratamento de casos-limite; simulações sintéticas não são apresentadas como resultados RGC.

### M-04 — Cohen's kappa não basta como resumo da qualidade da anotação

**Evidência:** o protocolo exige uma segunda anotação independente e Cohen's kappa ≥ 0,6, mas o conjunto pode ter classes desbalanceadas e inclui regras específicas para afirmações compostas, retificações e `RULE_GAP`.

**Risco:** kappa é sensível à prevalência dos rótulos; um único número pode ocultar divergências sistemáticas ou classes com concordância ruim. O marcador exploratório `RULE_GAP` não deve ser misturado aos cinco vereditos definitivos.

**Recomendação:** preservar o limiar aprovado de kappa ≥ 0,6. Antes do congelamento, definir a variante (kappa de Cohen não ponderado para rótulos nominais), a unidade de cálculo, o tratamento de rótulos ausentes e como reportar divergências. Publicar matriz de confusão entre anotadores, concordância observada, concordância por classe quando interpretável e distribuição dos rótulos. Pode-se estudar uma medida complementar de sensibilidade (por exemplo, Gwet AC1), mas ela não deve substituir o critério aprovado nem ser escolhida depois de observar o resultado.

**Critério de encerramento:** plano de concordância pré-especificado; divergências documentadas caso a caso; não promover um conjunto que falhe no critério já aprovado.

### M-05 — Viés potencial entre autoria dos casos, primeira anotação e adjudicação

**Evidência:** DEC-008 atribui ao mantenedor a redação e rotulagem dos casos definitivos; o protocolo pede segunda anotação independente sem acesso aos rótulos da primeira e resolução conjunta das divergências.

**Risco:** o autor da afirmação e da seleção do trecho pode favorecer involuntariamente uma interpretação. A segunda anotação reduz, mas não elimina, esse risco; a resolução conjunta também pode ser influenciada pela autoria.

**Recomendação:** não mudar DEC-008 unilateralmente. Documentar como limitação e definir antes da coleta um procedimento de adjudicação: ambos os anotadores registram seus rótulos e justificativas antes de ver o rótulo do outro; divergências são listadas; a justificativa final deve citar a fonte oficial; mudanças de rótulo ficam registradas com motivo. Se houver disponibilidade de um terceiro adjudicador independente, avaliar como melhoria opcional, sujeita a decisão explícita do mantenedor.

**Critério de encerramento:** fluxo de anotação e adjudicação documentado antes do conjunto definitivo; independência da segunda anotação demonstrável.

### M-06 — Meta de 300 casos e estratos: viabilidade e precisão não estão demonstradas apenas pelo número

**Evidência:** o pré-registro propõe 300 casos, aproximadamente um terço composto, e resultados por categoria/estado quando o tamanho permitir. Há cinco rótulos e categorias sobrepostas.

**Risco:** com 300 casos, alguns rótulos ou estratos podem ficar raros; intervalos e comparações por subgrupo podem ser instáveis. Cotas rígidas também podem incentivar casos artificiais, contrariando o protocolo.

**Recomendação:** manter 300 como meta, não como quota. Depois do piloto e antes de criar o conjunto definitivo, preparar uma tabela de cobertura planejada (categorias, rótulos e tipos de dificuldade) com regras para casos elegíveis e limites de interpretação. Usar a simulação sintética existente somente como análise de desenho, declarando hipóteses e limitações; ela não prova que a amostra real terá potência ou precisão adequadas. Se o número de casos elegíveis for insuficiente, registrar a limitação antes de executar o sistema.

**Critério de encerramento:** plano de cobertura e justificativa estatística aprovados antes da coleta definitiva; sem fabricação de exemplos para preencher cotas.

### M-07 — Divisão público/oculto e baseline devem ter procedimento reprodutível sem vazamento

**Evidência:** o protocolo propõe 70% de desenvolvimento público e 30% oculto, com seed 20261003; DEC-014 fixa o baseline B com base somente na partição pública e define o baseline A como descritivo da prevalência observada na avaliação.

**Risco:** uma divisão feita antes de congelar os rótulos, um sorteio não reproduzível ou o uso de rótulos ocultos na seleção do baseline pode vazar informação para o desenvolvimento.

**Recomendação:** documentar o algoritmo de divisão, a unidade de estratificação, o tratamento de afirmações compostas/átomos, a ordem dos dados e a política de acesso. Derivar e registrar B apenas a partir do conjunto público, antes da avaliação oculta; manter A apenas como referência descritiva. Publicar metadados e hash do arquivo oculto, nunca seu conteúdo. Testar o procedimento apenas com dados sintéticos ou fixtures não confidenciais antes de aplicá-lo aos casos definitivos.

**Critério de encerramento:** script e protocolo concordantes; nenhum caso oculto ou rótulo oculto exposto no repositório público ou usado para ajustar o sistema.

### M-08 — Fontes oficiais, retificações e vigência exigem trilha por dispositivo

**Evidência:** o pré-registro alerta que a página oficial pode conter ressalvas de vigência e remeter a atos posteriores. A Emenda 4 determina considerar o texto vigente após retificações, marcar `rectified: true` e reportar esse estrato separadamente.

**Risco:** confundir texto publicado, texto retificado e texto vigente pode criar rótulos incorretos; a captura de uma página oficial isolada não resolve toda questão de vigência.

**Recomendação:** para cada caso, preservar identificador do documento, URL oficial, hash do artefato capturado, dispositivo exato, data relevante e referência oficial da retificação quando aplicável. Se a vigência ou a relação entre atos não puder ser verificada com fonte primária suficiente, excluir o caso ou registrá-lo como limitação conforme regra congelada; não improvisar interpretação jurídica.

**Critério de encerramento:** todo caso definitivo tem proveniência e trecho verificáveis; retificações são identificadas e reportadas separadamente.

### M-09 — Alegações de contaminação e robustez precisam de escopo realista

**Evidência:** o conjunto oculto reduz exposição pública, mas não prova ausência de contaminação em modelos pré-treinados. As categorias de dificuldade incluem números, datas, negação, paráfrase, apoio parcial e troca de entidade.

**Risco:** afirmar que o conjunto é “à prova de contaminação” ou que mede robustez geral sem experimentos próprios seria excessivo.

**Recomendação:** descrever o conjunto oculto como controle de exposição e vazamento durante o desenvolvimento, não como prova de ausência de contaminação prévia. Relatar desempenho por tipo de dificuldade quando o tamanho permitir. Não criar variantes contrafactuais ou executar testes adicionais sem protocolo definido; futuras avaliações de robustez devem ser pré-especificadas e não misturadas ao resultado confirmatório principal.

**Critério de encerramento:** limites de generalização e contaminação descritos no pré-registro e no relatório.

### M-10 — Separação entre resultado confirmatório e análises exploratórias

**Evidência:** o pré-registro define H1, métricas, baseline e critérios de sucesso, além de exigir publicação de resultados negativos. O piloto 02 é explicitamente exploratório e deve ser descartado.

**Risco:** misturar decisões surgidas no piloto, análises posteriores ou ajustes no sistema com a execução confirmatória comprometeria a interpretação do resultado.

**Recomendação:** manter o piloto fora do conjunto definitivo e não executar o sistema sobre ele. Após o piloto, documentar achados metodológicos sem publicar casos/rótulos como benchmark. Congelar o protocolo por decisão explícita. Registrar commit, configuração e ambiente da execução confirmatória; qualquer desvio deve ser reportado e não corrigido silenciosamente após observar os resultados.

**Critério de encerramento:** gate de congelamento explícito e registro completo da execução confirmatória.

### M-11 — Definição da baseline no pré-registro conflita com a DEC-014 aprovada

**Evidência:** a seção 4 do pré-registro diz que a baseline de classe majoritária é calculada exclusivamente a partir dos rótulos de referência da partição avaliada. Já a DEC-014, registrada em `docs/STATUS.md`, define a baseline B como primária, derivada somente dos 70% públicos de desenvolvimento e fixada antes da avaliação; a baseline A é uma baseline-oráculo descritiva calculada na partição de avaliação e não fundamenta H1. O próprio texto do pré-registro menciona a baseline de classe majoritária sem distinguir claramente A e B, enquanto os critérios de sucesso de H1 usam “a baseline” no singular.

**Risco:** se a redação atual for seguida literalmente, a baseline usada para testar H1 pode ser calculada com rótulos do conjunto avaliado, contrariando a DEC-014 e contaminando a comparação confirmatória. Também fica ambíguo qual baseline define a margem de 10 pontos percentuais, o IC e o teste de McNemar.

**Recomendação:** antes do congelamento, harmonizar o pré-registro com a DEC-014 sem alterar a decisão aprovada: identificar explicitamente B como baseline primária operacional, calculada apenas no conjunto público e congelada antes da avaliação; identificar A como análise descritiva/oráculo, calculada no conjunto de avaliação e claramente excluída da hipótese H1 e dos critérios de sucesso. Especificar como as previsões de cada baseline são aplicadas aos mesmos casos avaliados, e verificar o protocolo, o executor, os testes e o plano estatístico em conjunto. Qualquer mudança de definição deve exigir emenda explícita do mantenedor antes de observar resultados.

**Critério de encerramento:** pré-registro, DEC-014, executor e relatório nomeiam e usam A/B de forma consistente; H1 compara o sistema apenas com B; A é reportada como descritiva e nunca apresentada como baseline primária.

## 4. Sequência recomendada

1. **Revisão documental:** resolver M-01 a M-03 e M-11 e registrar decisão para M-04 a M-10; preservar todas as decisões aprovadas até que uma emenda seja explicitamente aceita.
2. **Piloto humano 02:** o mantenedor realiza cerca de 10 casos novos usando a ficha existente, sem ferramentas de IA e sem executar o sistema. Não versionar a ficha preenchida nem compartilhar os casos com assistentes.
3. **Revisão pós-piloto:** registrar somente achados metodológicos necessários; não incorporar os casos do piloto ao conjunto definitivo.
4. **Gate de congelamento:** o mantenedor aprova explicitamente o protocolo revisado. Se houver mudança de regra, registrar emenda datada e justificativa antes de coletar casos definitivos.
5. **Plano do conjunto definitivo:** definir cobertura e divisão antes da coleta; manter 300 como meta condicionada à elegibilidade e qualidade.
6. **Anotação e controle de qualidade:** primeira anotação, segunda anotação independente, concordância e adjudicação segundo o protocolo congelado.
7. **Execução confirmatória:** executar somente após todos os gates; preservar saídas, falhas, configuração e commit.
8. **Relatório:** publicar resultados positivos, negativos ou inconclusivos, com incerteza, distribuição dos rótulos, métricas por estrato e limitações.

## 5. Não fazer

- Não criar agora os 300 casos definitivos.
- Não gerar nem rotular casos do piloto 02 com IA.
- Não executar o sistema sobre casos do piloto.
- Não alterar DEC-008, DEC-011, DEC-014 ou outras decisões aprovadas sem emenda/decisão explícita.
- Não alterar Judge, Golden v0/v0.1, manifestos, hashes congelados ou capturas de fonte.
- Não tratar a simulação sintética como desempenho do sistema.
- Não afirmar que o benchmark PT-BR já tem resultados, que está congelado ou que recebeu validação externa.
- Não mesclar esta revisão documental automaticamente: ela deve passar pelos checks e pelo fluxo normal de PR.

## 6. Decisão solicitada ao mantenedor após a revisão

Esta revisão não pede aprovação imediata do congelamento. O gate correto, após os ajustes documentais e a conclusão do piloto 02, é uma decisão explícita entre:

- **Congelar:** somente se os pontos críticos estiverem resolvidos, o piloto não revelar ambiguidades materiais e os critérios forem operacionalmente verificáveis; ou
- **Revisar novamente:** se houver ambiguidade, inconsistência de implementação ou risco de validade ainda não resolvido.

**Conclusão:** o protocolo possui uma base responsável, mas o estado científico correto continua sendo “em revisão pós-piloto, não congelado”. A qualidade deve ser demonstrada por coerência entre protocolo, código, anotação e relatório — não presumida a partir do tamanho do conjunto ou da sofisticação da arquitetura.
