Estado: Atual · Referência: main @ 3c1ba4f · Atualizado: 2026-10-18
Fontes de verdade: `src/ayorai_attractor/api/app.py`, `src/ayorai_attractor/verification/api_models.py`, `src/ayorai_attractor/verification/judge2/gates.py`, `src/ayorai_attractor/orchestrator.py`, `src/ayorai_attractor/verification/extraction.py`, `src/ayorai_attractor/verification/claim_pipeline.py`, `src/ayorai_attractor/evaluation/golden.py`, testes em `tests/verification/`.

# 01 — Visão geral

## Propósito

O AYORAI ATTRACTOR reúne uma camada de serviço para pesquisa e auditoria operacional e contratos de verificação de afirmações com um Judge determinístico. O problema tratado é separar a produção de respostas e a coleta de evidências da decisão explícita sobre afirmações: uma resposta gerada, uma referência ou um rótulo atribuído pelo cliente não devem ser confundidos com uma verificação independente.

Princípio de desenho: **Inteligência ≠ Autorização ≠ Execução**. A produção de conteúdo ou a seleção de ferramentas não equivale à autorização para executar ações; execução e coleta de evidências também não equivalem a um veredito factual.

## Como funciona

A API expõe operações distintas:

- `POST /v1/opensearch` executa a orquestração de pesquisa configurada.
- `POST /v1/audit` executa a mesma base operacional e retorna achados de auditoria e um identificador de rastreamento.
- `POST /v1/verify` recebe dados estruturados de verificação. Aceita os contratos `r1-a` e `r2-a`, que têm responsabilidades diferentes.

Em `r1-a`, o corpo é um `VerificationRequest`, com `schema_version`, `claims`, `evidence` e `stances`. O serviço entrega as afirmações, as evidências e as relações de posição fornecidas pelo cliente ao Judge legado. A API não descobre, por conta própria, se uma evidência apoia ou contradiz uma afirmação.

Em `r2-a`, o corpo é um `Judge2VerificationRequest`, que também inclui `source_texts`, átomos, evidências e relações de posição explícitas. Os gates do Judge 2 verificam a disponibilidade do texto-fonte e a validade dos offsets (E1), comparam o trecho indicado com o texto-fonte normalizado em Unicode NFC e, quando fornecido, conferem o hash do conteúdo normalizado (E2). A relação de posição continua vindo do cliente; E3 rejeita relações neutras ou ausentes como suporte/contradição admissível. Esses controles verificam os dados recebidos, mas não inferem a posição semântica por conta própria.

A API não extrai afirmações de respostas nem infere stances. Há componentes de extração e pipeline como biblioteca, e a avaliação Golden usa esses componentes em um fluxo de avaliação local: `verification/extraction.py`, `verification/claim_pipeline.py` e `evaluation/golden.py`. Isso não significa que tais etapas façam parte do contrato público de `POST /v1/verify`.

`POST /v1/opensearch` e `POST /v1/audit` não emitem veredito factual: suas respostas definem `verification = null` e `verdict_authority = not_adjudicated`. A resposta de auditoria operacional não deve ser confundida com um registro de auditoria verificável criptograficamente já implantado.

## Contratos e parâmetros

| Superfície | Entrada principal | Responsabilidade | Limite importante |
|---|---|---|---|
| `POST /v1/opensearch` | `SearchRequest` | Orquestra pesquisa e devolve resultado operacional | Não adjudica afirmações |
| `POST /v1/audit` | `SearchRequest` | Produz achados e persiste metadados de rastreamento | `verification = null`; `verdict_authority = not_adjudicated` |
| `POST /v1/verify` r1-a | `VerificationRequest` | Julga afirmações, evidências e stances enviados pelo cliente | Não valida trecho contra texto-fonte fornecido por um campo `source_texts` |
| `POST /v1/verify` r2-a | `Judge2VerificationRequest` | Aplica gates de admissibilidade de evidência e o Judge 2 versionado | Stances são explícitos na entrada; não são inferidos pela API |

Os nomes e a validação dos campos são definidos em `verification/api_models.py`; o despacho entre os dois contratos está em `api/app.py`.

## Limites conhecidos

- A API de verificação recebe afirmações, evidências e stances já estruturados; extração de afirmações e inferência de stance não são etapas automáticas dessa rota.
- O caminho `r2-a` confere offsets, trechos e metadados disponíveis, mas não transforma por si só uma relação de stance fornecida pelo cliente em uma inferência semântica independente.
- A camada de pesquisa usa provedores configurados. A existência de uma chamada a um provedor não é, por si, evidência de que o conteúdo resultante esteja correto.
- Não foi demonstrado resultado de benchmark PT-BR. Os artefatos Golden existentes são sintéticos e em inglês (`en-US`); consulte `docs/STATUS.md` para o estado e os resultados atuais.
- Não há certificação externa demonstrada.
- Um log de auditoria verificável criptograficamente não está implantado como serviço completo. A persistência de metadados de auditoria existente não deve ser descrita como prova de integridade à prova de adulteração.

## Evidências

- Contratos, despacho e rotas: `src/ayorai_attractor/api/app.py` e `src/ayorai_attractor/verification/api_models.py`.
- Validação de evidência r2-a: `src/ayorai_attractor/verification/judge2/gates.py`.
- Respostas operacionais sem veredito: `src/ayorai_attractor/orchestrator.py` e `src/ayorai_attractor/api/app.py`.
- Componentes de biblioteca e avaliação: `src/ayorai_attractor/verification/extraction.py`, `src/ayorai_attractor/verification/claim_pipeline.py` e `src/ayorai_attractor/evaluation/golden.py`.

## Ver também

- [Arquitetura](02-arquitetura.md)
- [Judge determinístico](03-judge.md)
- [API](04-api.md)
- [Status atual](../STATUS.md)
