# Protocolo de anotação do Golden v1 (português)
Status: em revisão pós-piloto; ainda não congelado. Alterações só por emenda datada no fim deste arquivo.

## Objetivo
Conjunto de avaliação em português brasileiro, com meta de 300 casos, para medir o desempenho do AYORAI ATTRACTOR em português.

## Rótulos
O benchmark RGC usa os cinco vereditos de `rules/judge-2.0.0.json` (`SUPPORTED`, `REFUTED`, `UNVERIFIED`, `PARTIALLY_SUPPORTED`, `CONFLICTING`), conforme a Emenda 2 e a semântica da ADR-009 (K1–K5). Não reutilizar automaticamente os rótulos do Golden v0/v0.1; esses conjuntos históricos permanecem inalterados.

## Fontes
Somente documentos com licença conhecida que permita uso, ou textos oficiais sem proteção autoral (Lei 9.610/98, art. 8º, IV: textos de leis e atos oficiais). A licença de cada documento é registrada. Licença desconhecida = documento excluído.
Domínios: legislação e regulação (incluindo LGPD), finanças e dados públicos, comunicados institucionais.

## Tipos de dificuldade
Cada caso é marcado com pelo menos um tipo: número, data, negação, paráfrase, apoio parcial, entidade trocada.

## Fases
1. **Piloto exploratório 01 — concluído e descartado:** 20 casos redigidos com auxílio de IA e rotulados por um único anotador. O sistema não foi executado; os casos não são evidência de desempenho.
2. **Piloto exploratório 02 — pendente:** aproximadamente 10 casos novos, anotação humana sem consulta a assistentes/modelos de IA, fontes oficiais conferidas e rastreabilidade por caso. Após revisão, descartar os casos e registrar os achados; não executar o sistema sobre eles nem incorporá-los ao conjunto definitivo. A composição proposta na Emenda 4 é uma meta condicionada à existência de casos elegíveis, não uma quota que justifique fabricar exemplos.
3. **Gate de congelamento:** após revisar o segundo piloto, registrar explicitamente a aprovação e o congelamento do protocolo. Até esse gate, não iniciar os 300 casos definitivos.
4. **Anotação definitiva:** somente após o congelamento, o mantenedor redige casos novos com afirmação, trecho da fonte, rótulo e justificativa curta. O conjunto permanece `v1-draft` enquanto houver um único anotador; resultados de anotador único não são resultado principal.
5. **Anotação independente:** uma segunda pessoa rotula os mesmos casos sem ver os rótulos da primeira. Calcular Cohen's kappa; só com kappa >= 0,6 o conjunto pode ser promovido a v1. Divergências são resolvidas em conjunto e registradas caso a caso.

Relatório histórico do piloto exploratório concluído em 2026-10-16: [PILOT-RGC-01-REPORT.md](PILOT-RGC-01-REPORT.md). O piloto foi descartado e o sistema não foi executado sobre seus casos; não constitui resultado de benchmark.

## Separação oculta
Antes de qualquer modelo ser rodado, 30% dos casos são sorteados (seed 20261003) para um conjunto oculto. Esse arquivo nunca entra no repositório; só o seu SHA-256 é publicado.

## Regras de isolamento
- Durante a anotação, o anotador não roda o sistema nos casos nem vê saídas de modelos sobre eles.
- Nenhum caso do Golden v1 é usado para treinar ou ajustar limiares.
- Os resultados seguem as regras da F1: accuracy, balanced accuracy, macro-F1, IC95% por bootstrap (10.000, seed 20261003) e publicação de resultados negativos.

## Emenda 1 (2026-10-04)
As fontes ficam em um arquivo separado, uma linha por documento, com os campos source_id, source_url, source_license, retrieved_at e text (texto completo). O sistema avaliado recebe o documento completo, nunca o trecho, o rótulo ou a justificativa do caso. Todo source_excerpt deve aparecer literalmente no texto da sua fonte; caso contrário, o caso é inválido.

## Emenda 2 (2026-10-15)

1. O benchmark RGC usa os cinco vereditos de `rules/judge-2.0.0.json` (`enums.verdict`), com a semântica da ADR-009 (K1–K5), não a da ADR-002. Esta emenda substitui, somente para o RGC, a regra “os mesmos rótulos do v0.1”; o Golden v0/v0.1 não é alterado.
2. `PARTIALLY_SUPPORTED` significa uma afirmação com mais de uma parte, com pelo menos uma parte confirmada, nenhuma contradita e alguma sem confirmação. Não significa “fonte única” (sentido da ADR-002, linha S=1).
3. `VERIFIED` não é rótulo de referência. Corroboração (R0–R3) é um eixo separado e não é anotada no v1.
4. Golden v0, v0.1 e derivados r2 permanecem intocados; nenhum rótulo histórico é convertido.
5. `RULE_GAP` (“regra insuficiente”) só pode ser usado no piloto, como marcador de ambiguidade das regras, nunca como veredito. No conjunto definitivo, é proibido no campo `label`: caso indecidível deve ser reescrito ou excluído antes do congelamento, com o motivo registrado no log de exclusões. A taxa de `RULE_GAP` é reportada separadamente; não entra no kappa nem nas métricas do sistema.
6. `ABSTAINED` do Judge é avaliado como `UNVERIFIED` (DEC-009).

## Emenda 3 (2026-10-16) — Afirmações compostas (DEC-010, opção A)

1. **Afirmação simples:** contém um único fato verificável e não leva o campo `atoms`.
2. **Afirmação composta:** contém dois ou mais fatos verificáveis na mesma frase. O anotador marca cada fato como um átomo no campo `atoms`, com `start_offset` e `end_offset` relativos ao texto da afirmação. O campo `text` do átomo é opcional; quando presente, deve ser idêntico ao trecho correspondente da afirmação. Os átomos devem estar em ordem, sem sobreposição e sem trechos vazios.
3. Todo caso rotulado `PARTIALLY_SUPPORTED` deve ser composto e trazer `atoms`. Um caso composto pode receber qualquer um dos cinco rótulos do RGC.
4. Os átomos são marcados **antes** do rótulo e não podem ser ajustados para alterar o resultado do sistema. O sistema nunca é executado sobre casos sem rótulo.
5. **Meta de composição:** cerca de um terço dos casos definitivos será composto. A proporção final será declarada no relatório.
6. Anotação de átomos inválida interrompe a execução, conforme o executor `rgc-eval/0.2.0`, mesclado na [PR #203](https://github.com/Ayorinha/ayorai-opensearch/pull/203) em 2026-10-16. A mesclagem não equivale à validação do executor no benchmark definitivo.

A presente emenda documenta a decisão DEC-010, opção A. **Nota histórica:** à data desta emenda, o protocolo e o pré-registro ainda aguardavam aprovação e congelamento formais; a Emenda 4 (2026-10-17) registra a aprovação da DEC-011. O protocolo continua sem congelamento formal até a conclusão e revisão do segundo piloto.


## Emenda 4 (2026-10-17) — Regras de anotação após o piloto (DEC-011, aprovada)

Esta emenda registra a aprovação explícita do mantenedor. O segundo piloto continua exploratório e seus casos serão descartados; esta emenda não declara o protocolo congelado nem constitui resultado de benchmark.

1. **Ausência não é contradição.** Atribuir `UNVERIFIED` quando as evidências não abordam a afirmação. Atribuir `REFUTED` somente quando uma frase da evidência for explicitamente incompatível com a afirmação. A justificativa de todo `REFUTED` deve citar a frase incompatível. Pergunta de controle: “Consigo apontar a frase do trecho que diz o contrário?” Se não, não usar `REFUTED`.
2. **Texto retificado — opção A.** Para o rótulo de referência, considerar o texto vigente após aplicar as retificações oficiais. Texto superado reproduzido em “Onde se lê” ou em redação original retificada não conta como evidência de apoio. Marcar casos que envolvam dispositivo retificado com `rectified: true` e reportar esse estrato separadamente, com a limitação explícita. Não alterar o Judge nem suas regras nesta versão.
3. **Valores, quantificadores e modalidade.** Valores diferentes para o mesmo prazo, período, percentual ou data são `REFUTED` quando o texto fornece um valor incompatível. Afirmações “exclusivamente/somente X” são `REFUTED` quando a fonte admite ou prefere meio/condição incompatível; se a fonte não tratar do ponto, usar `UNVERIFIED`. Afirmações de integralidade são `REFUTED` quando o texto delimita expressamente um alcance menor. Trocas entre dever e faculdade, ou entre permissão e proibição, são `REFUTED` quando o texto é explicitamente incompatível.
4. **Limite de interpretação.** Excluir do v1 afirmações que transformem “preferencialmente” em obrigação sem suporte textual explícito. Não inferir obrigação nem contradição apenas por interpretação jurídica do anotador.
5. **Isolamento e proveniência.** O segundo piloto deve usar casos novos, trechos conferidos literalmente contra fontes oficiais registradas e anotação humana sem consulta a assistentes/modelos de IA. Registrar a fonte, o trecho exato, o rótulo e uma justificativa rastreável. Os casos do piloto são descartados e não integram o conjunto definitivo.
6. **Composição do segundo piloto.** Alvo aproximado de 10 casos: incluir pelo menos 3 casos compostos com uma parte confirmada e outra sem confirmação (`PARTIALLY_SUPPORTED`), 1 caso com fontes divergentes (`CONFLICTING`), 1 caso envolvendo dispositivo retificado e 2 casos de ausência de evidência (`UNVERIFIED`). A seleção final depende de fontes elegíveis e de conferência humana; não fabricar casos para satisfazer cotas.
7. **Gate posterior.** Após o piloto, revisar ambiguidades e documentar o resultado. Congelar o protocolo somente por registro explícito do mantenedor depois dessa revisão. Só então iniciar a redação dos 300 casos definitivos. Não alterar código, regras do Judge, Golden históricos, manifestos ou hashes congelados nesta emenda.

A decisão foi aprovada por Anderson Leon Ayora em 2026-10-17 e a Emenda 4 foi incorporada pela PR #227, mesclada pelo mantenedor. O protocolo continua sem congelamento formal: depende da revisão do segundo piloto exploratório e de registro explícito de congelamento. O benchmark PT-BR não tem resultado validado neste estágio.
