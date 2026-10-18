# Guia de estilo do Manual Técnico

## Evidência e confirmação

- Toda afirmação técnica sobre o sistema deve apontar para uma evidência verificável: arquivo, teste, workflow ou SHA.
- Antes de incorporar um fato informado fora do código, confirme-o na `main` atual. Se houver divergência, prevalece o código e a diferença deve ser registrada.
- Não apresente como implementado algo que exista apenas como proposta, plano ou módulo sem integração demonstrada.

## Idioma e identificadores

- Escreva em português do Brasil.
- Preserve exatamente os nomes de campos, rotas, enums, parâmetros, arquivos e comandos usados no código.
- Use datas no formato ISO `AAAA-MM-DD`.

## Estrutura dos capítulos

Cada capítulo começa com estas duas linhas, preenchidas com os valores verificados no momento da atualização:

```text
Estado: Atual · Referência: main @ <SHA curto> · Atualizado: <AAAA-MM-DD>
Fontes de verdade: <arquivos e testes>
```

Use, nesta ordem, as seções: **Propósito → Como funciona → Contratos e parâmetros → Limites conhecidos → Evidências → Ver também**.

## Regras editoriais e tabelas

- Use tom técnico e sóbrio.
- Não use as expressões “garante”, “certificado”, “à prova de adulteração” ou “pronto para produção” para descrever o sistema.
- Prefira “implementado”, “implementado como biblioteca”, “proposto” e “não implementado”, conforme a evidência.
- Toda tabela deve ter o mesmo número de células em cada linha que o número de células do cabeçalho.
- Apresente **Golden v0** e **Golden v0.1** sempre lado a lado quando ambos forem discutidos ou comparados.
- Números mutáveis de status, progresso, métricas correntes ou contagens devem ficar somente em `docs/STATUS.md`; nos capítulos, mantenha fatos estáveis e referências para o status.
