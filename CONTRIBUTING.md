# Contributing to AYORAI ATTRACTOR

Obrigado por contribuir. O projeto prioriza evidência verificável, segurança e reprodutibilidade.

## Fluxo

1. Abra uma issue quando a mudança não for trivial.
2. Crie uma branch curta a partir de `main`.
3. Adicione ou atualize testes para comportamento alterado.
4. Rode os checks do CI; resultados de execução válidos são os do GitHub Actions.
5. Abra um Pull Request descrevendo motivação, mudança, testes e riscos.
6. Não altere `evals/golden/v0.jsonl` após o congelamento; correções do gabarito devem virar uma nova versão.

## Golden / avaliação

Mudanças no motor de verificação devem preservar o contrato do ADR-002. Casos novos devem declarar `evidence_pool`, proveniência e estado esperado. Não use dados reais, segredos ou informações pessoais nos fixtures.

## Segurança

Não envie credenciais, tokens, dados pessoais, financeiros ou material confidencial. Para vulnerabilidades, consulte `SECURITY.md` em vez de abrir uma issue pública.

## Qualidade

PRs devem manter CI, segurança e CodeQL verdes. Resultados de benchmark/eval só devem ser publicados com o run do GitHub Actions que os produziu.
