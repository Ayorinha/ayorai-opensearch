# Protocolo de anotação do Golden v1 (português)
Status: pré-registrado antes de qualquer caso ser escrito. Alterações só por emenda datada no fim deste arquivo.

## Objetivo
Conjunto de avaliação em português brasileiro, com meta de 300 casos, para medir o desempenho do AYORAI ATTRACTOR em português.

## Rótulos
Os mesmos rótulos usados em evals/golden/v0.1.jsonl. Nenhum rótulo novo.

## Fontes
Somente documentos com licença conhecida que permita uso, ou textos oficiais sem proteção autoral (Lei 9.610/98, art. 8º, IV: textos de leis e atos oficiais). A licença de cada documento é registrada. Licença desconhecida = documento excluído.
Domínios: legislação e regulação (incluindo LGPD), finanças e dados públicos, comunicados institucionais.

## Tipos de dificuldade
Cada caso é marcado com pelo menos um tipo: número, data, negação, paráfrase, apoio parcial, entidade trocada.

## Fases
1. Piloto: 20 casos para testar estas regras. Depois do piloto, as regras são congeladas e os 20 casos são descartados.
2. Anotação 1: o autor escreve cada caso com afirmação, trecho da fonte, rótulo e justificativa curta. Enquanto houver um só anotador, o conjunto se chama v1-draft e seus resultados são marcados "anotador único, não usar como resultado principal".
3. Anotação 2: uma segunda pessoa rotula os mesmos casos sem ver os rótulos da primeira. Calcula-se o Cohen's kappa. Só com kappa >= 0,6 o conjunto passa a se chamar v1. Divergências são resolvidas em conjunto e registradas, caso a caso.

Relatório proposto do piloto exploratório concluído em 2026-10-16: [PILOT-RGC-01-REPORT.md](PILOT-RGC-01-REPORT.md) (**[PROPOSTO]**). O piloto foi descartado e o sistema não foi executado sobre seus casos; não constitui resultado de benchmark.

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

A presente emenda documenta a decisão DEC-010, opção A. O protocolo e o pré-registro permanecem **[PROPOSTO]** até aprovação e congelamento formais pelo mantenedor.
