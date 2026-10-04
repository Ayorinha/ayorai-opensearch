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

## Separação oculta
Antes de qualquer modelo ser rodado, 30% dos casos são sorteados (seed 20261003) para um conjunto oculto. Esse arquivo nunca entra no repositório; só o seu SHA-256 é publicado.

## Regras de isolamento
- Durante a anotação, o anotador não roda o sistema nos casos nem vê saídas de modelos sobre eles.
- Nenhum caso do Golden v1 é usado para treinar ou ajustar limiares.
- Os resultados seguem as regras da F1: accuracy, balanced accuracy, macro-F1, IC95% por bootstrap (10.000, seed 20261003) e publicação de resultados negativos.

## Emenda 1 (2026-10-04)
As fontes ficam em um arquivo separado, uma linha por documento, com os campos source_id, source_url, source_license, retrieved_at e text (texto completo). O sistema avaliado recebe o documento completo, nunca o trecho, o rótulo ou a justificativa do caso. Todo source_excerpt deve aparecer literalmente no texto da sua fonte; caso contrário, o caso é inválido.
