# Ficha em branco — piloto exploratório RGC PT-BR 02

**Uso:** formulário vazio para preenchimento manual pelo anotador humano. Este arquivo não contém casos, afirmações, trechos, rótulos ou exemplos produzidos por IA.

## Regras antes de começar

- Preencher e rotular os casos sem consultar assistentes ou modelos de IA.
- Não executar o AYORAI ATTRACTOR sobre os casos do piloto.
- Usar apenas fontes oficiais elegíveis e conferir literalmente cada trecho contra o artefato preservado.
- Não copiar casos do piloto 01 nem reutilizá-los no conjunto definitivo.
- Após a revisão, descartar os casos do piloto e registrar apenas os achados metodológicos necessários.
- Não inventar exemplos para cumprir uma quota. Se uma categoria não puder ser sustentada por fonte elegível, registrar a limitação.
- Esta ficha não congela o protocolo. O congelamento depende de revisão do piloto e aprovação explícita posterior do mantenedor.

## Meta orientativa de composição

O protocolo propõe aproximadamente 10 casos, procurando incluir, quando fontes elegíveis sustentarem os exemplos, pelo menos 3 casos compostos parcialmente apoiados, 1 caso com fontes divergentes (`CONFLICTING`), 1 caso que envolva retificação e 2 casos sem evidência suficiente (`UNVERIFIED`). Isso é uma meta condicionada, não uma quota: não fabricar casos, forçar rótulos nem usar fonte cuja vigência/proveniência não possa ser conferida. Registre limitações na revisão final.

## Valores permitidos

**Rótulo de referência:** `SUPPORTED`, `REFUTED`, `UNVERIFIED`, `PARTIALLY_SUPPORTED`, `CONFLICTING`.

**Marcador exclusivo do piloto:** `RULE_GAP` pode ser usado quando as regras de anotação não permitem uma decisão consistente. Ele não é um veredito do Judge, não entra em métricas nem no cálculo de concordância e deve ser resolvido por revisão metodológica; os casos do piloto serão descartados.

**Tipos de dificuldade:** número, data, negação, paráfrase, apoio parcial, entidade trocada (marcar os aplicáveis).

## Ficha de anotação — preencher manualmente

Repita a ficha abaixo para cada caso. Não compartilhe os casos com assistentes/modelos de IA durante o piloto.

### Caso 01

- Identificador:
- Afirmação redigida pelo anotador:
- Fonte oficial (URL):
- Identificador da fonte / caminho do artefato capturado:
- Órgão emissor e ato:
- Dispositivo exato (artigo/parágrafo/inciso):
- Data de publicação e data relevante para vigência:
- Trecho literal exato:
- Hash do artefato-fonte, se registrado:
- A fonte foi conferida literalmente? Sim / Não
- Há retificação aplicável? Sim / Não
- Se sim, referência oficial da retificação e dispositivo vigente:
- Campo `rectified`: `true` / `false`
- Afirmação simples ou composta?
- Se composta, transcrever os átomos e registrar `start_offset`/`end_offset` manualmente:
- Rótulo de referência:
- Justificativa rastreável ao texto:
- Se `REFUTED`, frase literal incompatível que demonstra a contradição:
- Se `CONFLICTING`, fonte primária A, trecho A, fonte primária B e trecho B:
- Tipo(s) de dificuldade:
- Ambiguidade ou limitação identificada:
- Decisão final do anotador e motivo:

### Caso 02

- Identificador:
- Afirmação redigida pelo anotador:
- Fonte oficial (URL):
- Identificador da fonte / caminho do artefato capturado:
- Órgão emissor e ato:
- Dispositivo exato (artigo/parágrafo/inciso):
- Data de publicação e data relevante para vigência:
- Trecho literal exato:
- Hash do artefato-fonte, se registrado:
- A fonte foi conferida literalmente? Sim / Não
- Há retificação aplicável? Sim / Não
- Se sim, referência oficial da retificação e dispositivo vigente:
- Campo `rectified`: `true` / `false`
- Afirmação simples ou composta?
- Se composta, transcrever os átomos e registrar `start_offset`/`end_offset` manualmente:
- Rótulo de referência:
- Justificativa rastreável ao texto:
- Se `REFUTED`, frase literal incompatível que demonstra a contradição:
- Se `CONFLICTING`, fonte primária A, trecho A, fonte primária B e trecho B:
- Tipo(s) de dificuldade:
- Ambiguidade ou limitação identificada:
- Decisão final do anotador e motivo:

### Casos 03–10

Copie a ficha completa do Caso 01 para cada caso restante e altere apenas o identificador. Não use a ficha para registrar previsões do sistema.

## Conferência mecânica opcional (sem IA, sem executar o sistema)

Depois de preencher uma cópia local desta ficha, o anotador pode rodar no próprio computador:

```bash
python scripts/check_pilot_worksheet.py minha-ficha.md
```

O script só confere regras mecânicas: trecho literal presente no artefato capturado (Emenda 1), rótulo dentro dos cinco vereditos (Emenda 2), frase incompatível literal em todo `REFUTED` (Emenda 4), coerência de `rectified` e átomos em `PARTIALLY_SUPPORTED` (Emendas 3 e 4). Não sugere nem avalia rótulos, não usa rede nem modelos, não importa o ATTRACTOR e imprime apenas identificadores e a regra violada, nunca o conteúdo dos casos. Não versionar a ficha preenchida.

## Revisão após a anotação

- Total de casos elegíveis efetivamente encontrados:
- Casos descartados e motivo (sem reproduzir desnecessariamente o conteúdo):
- Regras que geraram dúvida:
- Fontes ou dispositivos cuja vigência não pôde ser confirmada:
- Categorias previstas que não puderam ser cobertas sem fabricar exemplos:
- Confirmação de que nenhum assistente/modelo de IA foi consultado durante a criação e rotulagem:
- Confirmação de que o sistema não foi executado sobre os casos:
- Data da revisão humana:
- Próxima decisão necessária do mantenedor:

**Aviso:** esta ficha não substitui a fonte oficial, não constitui aconselhamento jurídico, não representa validação externa e não é um benchmark. O resultado do piloto não deve ser apresentado como métrica de desempenho do sistema.
