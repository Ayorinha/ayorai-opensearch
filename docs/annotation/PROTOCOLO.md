# Protocolo de anotação PT-BR — versão de trabalho

**Estado:** proposta de protocolo; não constitui resultado de anotação nem autorização para publicar um benchmark.  
**Responsável pelo projeto:** Anderson Leon Ayora.  
**Uso previsto:** preparar anotações humanas rastreáveis para avaliação futura do AYORAI ATTRACTOR.  
**Limite:** este documento define como registrar rótulos e evidências. Não interpreta normas, não estabelece hierarquia jurídica e não substitui revisão independente.

## 1. Princípios

1. **Separar anotação e adjudicação automática.** A anotação humana registra o que o protocolo e as fontes permitem observar. O Judge aplica regras determinísticas versionadas; um modelo probabilístico não decide o veredito final.
2. **Preservar a fonte.** Não corrigir silenciosamente ortografia, pontuação, numeração, datas, unidades ou redação da fonte. Qualquer normalização deve ser campo derivado, com regra e versão identificadas.
3. **Registrar proveniência.** Cada evidência precisa de identificador estável, URL ou identificador de origem, localização no documento, data de coleta, hash do conteúdo e offsets do trecho quando aplicáveis.
4. **Separar fatos, inferências e ausência de informação.** Não transformar falta de evidência em refutação. Não preencher lacunas por conhecimento externo não registrado.
5. **Manter trilha de adjudicação.** Discordâncias, alterações de rótulo e justificativas devem ser preservadas; nunca sobrescrever silenciosamente a anotação anterior.
6. **Não inferir validade jurídica.** Referências normativas, datas de publicação e vigência são metadados/âncoras temporais. A anotação estrutural não decide hierarquia, revogação, aplicabilidade ou interpretação.

## 2. Unidade de anotação

Cada caso deve identificar:

- `case_id`, versão do esquema e versão do protocolo;
- texto integral da afirmação original e idioma;
- origem da afirmação e data de referência, quando fornecidas;
- lista de átomos, cada qual ligado a um trecho da afirmação original;
- documentos-fonte e evidências candidatas;
- relações de stance por átomo e evidência;
- rótulo anotado, estado de decisão, códigos de motivo e justificativa baseada em evidência;
- anotadores, adjudicador quando houver, timestamps e histórico de mudanças.

A decomposição em átomos deve preservar o significado da afirmação original. Se não for possível decidir uma decomposição sem introduzir pressupostos, registrar a incerteza e encaminhar para adjudicação, em vez de inventar átomos.

## 3. Spans e offsets

- Registrar offsets como índices inteiros de início inclusivo e fim exclusivo, em relação ao texto-fonte exato e à codificação definida pelo esquema.
- O trecho citado deve ser reproduzível aplicando os offsets ao texto-fonte identificado.
- Início e fim precisam estar dentro dos limites do texto; o fim deve ser maior que o início.
- Não calcular offsets sobre texto normalizado quando o identificador de origem se refere ao texto original.
- Se houver conversão de PDF, OCR ou HTML para texto, preservar o artefato de origem, o método de extração e o hash do texto extraído. Marcar possíveis erros de extração.

## 4. Relação entre evidência e afirmação

Para cada par átomo–evidência, registrar exatamente uma relação primária:

- `SUPPORTS`: o trecho oferece suporte explícito ao átomo;
- `CONTRADICTS`: o trecho contradiz explicitamente o átomo;
- `NEUTRAL`: o trecho não estabelece suporte nem contradição suficiente.

A relação descreve o trecho e o átomo anotados, não a confiabilidade geral da fonte. Uma evidência neutra não deve ser contada como suporte ou contradição. Se um trecho contiver conteúdo misto, dividir a anotação em unidades menores quando isso puder ser feito sem perder contexto; caso contrário, registrar a ambiguidade para adjudicação.

## 5. Números, datas, unidades e condições

Preservar sempre o texto literal. Campos normalizados são complementares e devem incluir a regra de normalização utilizada.

Para números, registrar, quando presentes: valor literal, valor normalizado, separador decimal, separador de milhar, sinal, moeda ou unidade e intervalo de tolerância apenas quando o protocolo do caso o definir.

Para datas e prazos, registrar: texto literal, data normalizada quando inequívoca, granularidade (dia, mês, ano ou intervalo), fuso horário quando explícito, marco inicial e marco final quando informados. Não inferir prazo inicial, contagem de dias úteis ou fuso que a fonte não forneça.

Para unidades, preservar símbolo e escala originais. Conversões devem ser derivadas, reproduzíveis e nunca substituir o valor literal. Se duas leituras forem plausíveis, registrar ambiguidade em vez de escolher silenciosamente.

## 6. Vigência e referências normativas

Registrar separadamente, quando disponível:

- identificação literal da norma e referência estrutural (artigo, parágrafo, inciso, alínea ou caput);
- órgão emissor e URL da fonte primária;
- data de publicação, data de coleta e hash do conteúdo;
- início e fim de vigência somente quando constarem de fonte primária verificada;
- data de referência da afirmação avaliada.

A referência estrutural e a vigência são metadados. O protocolo não decide se uma norma prevalece sobre outra, se foi revogada, como deve ser interpretada ou se se aplica ao caso concreto. Quando a fonte primária ou a âncora temporal não puder ser verificada, marcar o campo como ausente/pendente e não completar por inferência.

## 7. Rótulo, estado de decisão e abstenção

Manter separados:

- **Veredito factual:** rótulo permitido pelo esquema de avaliação e sustentado pelas regras e evidências anotadas.
- **Estado de decisão:** informa se houve decisão, abstenção ou entrada inválida; não é um veredito factual.
- **Código de motivo:** identifica de forma estável por que houve rejeição de entrada, rejeição de evidência ou abstenção.
- **Justificativa:** explicação concisa que aponta para os IDs de átomos e evidências; não substitui o rastro estruturado.

Quando houver falta de evidência, fonte indisponível, ambiguidade não resolvida, escopo não suportado ou âncora temporal necessária ausente, seguir o código de motivo aplicável e abster-se quando as regras assim determinarem. Não usar `UNVERIFIED` como substituto genérico para todos os estados de abstenção ou de entrada inválida.

Os anotadores humanos devem usar os rótulos definidos na versão do esquema adotada pelo estudo. Não introduzir rótulos ad hoc. Se o protocolo e o esquema discordarem, suspender a anotação do caso e registrar a incompatibilidade para decisão do mantenedor.

## 8. Adjudicação entre anotadores

1. Cada anotador trabalha independentemente, sem consultar os rótulos dos demais antes de registrar a própria decisão.
2. Registrar rótulo, spans, relações, fontes e justificativa de cada anotador antes da adjudicação.
3. Calcular a concordância com a métrica e a unidade de análise pré-registradas. Informar quantidade de casos, dados ausentes, distribuição de rótulos e tratamento de categorias raras.
4. Toda discordância deve ser resolvida por adjudicador identificado, com justificativa e links para as evidências. Não apagar os rótulos originais.
5. Se a discordância depender de interpretação jurídica, validade da norma, hierarquia ou revogação, não resolver por inferência técnica: marcar como pendente e solicitar revisão qualificada.
6. A versão final adjudicada é um artefato derivado, com novo identificador, manifesto e hash; os rótulos originais permanecem preservados.

## 9. Exemplos ilustrativos — não são dados do benchmark

**Exemplo A — suporte explícito (texto fictício).**  
Afirmação: “O prazo indicado é de 10 dias.”  
Trecho fictício: “O prazo para resposta é de 10 dias.”  
Anotação possível: átomo sobre prazo; span correspondente ao trecho; relação `SUPPORTS`. O anotador ainda precisa verificar se o contexto, a unidade temporal e o marco inicial correspondem à afirmação completa.

**Exemplo B — informação insuficiente (texto fictício).**  
Afirmação: “A solicitação foi respondida dentro do prazo.”  
Trecho fictício: “A solicitação foi recebida em 3 de maio.”  
Anotação possível: `NEUTRAL` para o átomo sobre cumprimento do prazo, pois o trecho não informa a data de resposta nem o prazo aplicável. Não rotular como `CONTRADICTS`.

**Exemplo C — referência normativa sem âncora temporal (texto fictício).**  
Afirmação: “A regra estava em vigor na data do evento.”  
Documento fictício: contém o número de uma resolução, mas não a data de vigência nem histórico oficial suficiente.  
Anotação possível: registrar a referência literal e a fonte disponível; marcar a âncora temporal como ausente/pendente. Não inferir vigência a partir apenas do número da resolução.

## 10. Controle de qualidade e versões

Antes de aceitar um lote, verificar automaticamente:

- IDs únicos e referências sem destinos inexistentes;
- offsets válidos e trecho consistente com a origem;
- hashes e URLs/identificadores de fonte presentes conforme o esquema;
- valores de rótulo dentro do vocabulário permitido;
- separação entre veredito, estado de decisão e códigos de motivo;
- campos temporais ausentes identificados explicitamente;
- histórico de anotação e adjudicação preservado.

Toda alteração deste protocolo exige incremento de versão, changelog, justificativa, revisão independente e avaliação do impacto sobre a comparabilidade. Não reescrever silenciosamente rótulos ou relatórios antigos; gerar artefatos derivados com manifesto e hash.

## 11. Limitações e estado

Este documento é uma proposta de procedimento, não evidência de que o benchmark PT-BR foi anotado, adjudicado ou validado. Métricas de concordância, desempenho por estrato, intervalos de confiança e resultados estatísticos só poderão ser declarados após execução documentada sobre um conjunto identificado e congelado. O pré-registro e a eventual submissão ao OSF dependem do mantenedor.
