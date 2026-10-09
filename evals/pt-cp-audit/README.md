# PT-CP-Audit — simulação de auditoria sobre o Código Penal real

Cenário: um assistente jurídico com IA responde perguntas sobre a Parte Geral do Código Penal. O ATTRACTOR precisa dizer, para cada afirmação, se o trecho oficial recuperado **apoia**, **contradiz** ou **não decide** (neutro) a afirmação.

## Fonte

- Decreto-Lei 2.848/1940 (Código Penal), Parte Geral, arts. 1º a 120, texto compilado vigente do Planalto (`https://www.planalto.gov.br/ccivil_03/decreto-lei/del2848compilado.htm`), capturado em 2026-09-15 pelo dataset de domínio público `wagnermarques/legis-dados@3951145d42cce0f575a075551e239e2968e764dd`.
- `cp-parte-geral-dispositivos.json` SHA-256 `08a476e8130af71fd5b4bbf96a39481bece5715ed2b0d8c7e351895d2cd323cd`.
- Textos oficiais não têm proteção de direito autoral (Lei 9.610/1998, art. 8º, IV).

## Casos

- `hand_cases.jsonl`: 90 afirmações escritas como um assistente de IA responderia — 30 corretas (paráfrases), 30 alucinações típicas (número errado, regra antiga como "30 anos", negação, inversão, ator errado) e 30 com recuperação errada (o trecho é de outro dispositivo relacionado).
- Bloco mecânico: 62 casos que mutam números escritos como "N (extenso)" (o texto literal apoia a si mesmo; o texto mutado o contradiz).
- `cases.jsonl` (152 casos) SHA-256 `3aa702bc7bd04185389d9201e619ca7637508a5fb1aac774bdf642bf4362382c`, gerado por `build_cases.py`.
- Divisão dev/test por dispositivo (todos os casos de um mesmo trecho ficam do mesmo lado), seed 20261003: dev 84 casos, test 68.

## Limitações declaradas

- Autor dos casos e das melhorias: o mesmo (Claude). Mitigação: rótulos por construção contra o texto literal, divisão por dispositivo, teste reservado só medido em agregado, baseline congelado em commit antes de qualquer mudança (`e23732f`).
- É uma simulação de desenvolvimento em português real, não o Golden v1 (que exige anotação independente e kappa ≥ 0,6).

## Protocolo da medição v5 → v6 (registrado antes de medir o test)

- **Baseline:** `RuleStanceDetector` v5 (main `f6f0607`), já registrado em `reports/pt-cp-audit-baseline-v5-test.json` antes de qualquer mudança.
- **Candidato:** `RuleStanceDetector` v6 (esta branch). As mudanças foram desenvolvidas olhando **apenas** o split dev e testes unitários novos.
- **Medição única no test**, com o test só em agregado. Métricas, por test completo e por test só-manuais (`origin == hand`, a leitura principal):
  - **primária:** taxa de apoio falso (casos não-`supports` previstos como `supports`) — o erro mais caro para um auditor;
  - acurácia, macro-F1, taxa de contradição falsa, precisão/recall por classe;
  - McNemar exato pareado v5 × v6 por caso.
- **Regra de decisão:** v6 é **melhor** se reduzir a taxa de apoio falso no test só-manuais **sem** reduzir a acurácia; caso contrário, o resultado é publicado como está e v6 não é promovido.
- Nenhuma regra é alterada depois de ver o resultado do test. Uma nova rodada exigiria novos casos de test.
