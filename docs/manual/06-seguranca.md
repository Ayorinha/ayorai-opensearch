Estado: Atual · Referência: main @ 42b71a2 · Atualizado: 2026-10-21
Fontes de verdade: `docs/THREAT-MODEL.md`, `docs/security/API-AUTH.md`, `docs/security/RED-TEAM.md`, `src/ayorai_attractor/api/auth.py`, `src/ayorai_attractor/api/request_context.py`, `src/ayorai_attractor/api/app.py`, `src/ayorai_attractor/verification/excerpt.py`, `src/ayorai_attractor/synthesis.py`, `src/ayorai_attractor/verification/judge2/gates.py`, `src/ayorai_attractor/redteam.py`, workflows `.github/workflows/security.yml` and `.github/workflows/codeql.yml`, testes `tests/test_api_auth.py`, `tests/test_api_request_context.py`, `tests/test_verification_response_security.py` e testes de segurança do Judge.

# 06 — Segurança e limites de confiança

## Propósito

Este capítulo descreve controles de segurança que existem no código e nos workflows, bem como os limites explícitos do modelo de ameaças. O objetivo é tornar as fronteiras verificáveis; não é declarar o sistema certificado, imune a adulteração ou pronto para produção.

## Como funciona

### Autoridade do veredito e dados não confiáveis

O contrato de verificação separa o conteúdo que chega de usuários, documentos, citações e modelos da decisão factual final. Texto de documento com aparência de instrução continua sendo dado de evidência; não pode substituir o pedido estruturado nem alterar a autoridade do Judge determinístico. A produção de texto por um provider, a seleção de ferramentas e a coleta de evidências não constituem, por si só, um veredito.

O modelo de ameaças delimita o escopo: integridade de afirmações, evidências e proveniência, cálculo determinístico do veredito, integridade de replay, isolamento de conjuntos de avaliação, licenças e controles de CI/supply chain. Não promete provar a verdade de uma fonte externa, proteger a máquina/conta GitHub/rede/credenciais do operador, impedir comportamento malicioso de dependências comprometidas ou garantir generalização.

### Proveniência e citações

- O gate de síntese exige pelo menos um identificador de evidência conhecido para cada afirmação gerada; afirmações sem citação válida resultam em abstenção.
- O caminho de evidência pode localizar o trecho na fonte original, normalizando texto em NFC e preservando o mapeamento para offsets originais. Um trecho não encontrado é rejeitado em vez de ser aceito apenas porque um modelo o forneceu.
- Os contratos do Judge recebem entradas estruturadas. Stance, tradução, busca e texto gerado não substituem a autoridade do Judge determinístico.
- O corpus red-team cobre classes como prompt injection, envenenamento de evidência, manipulação de citação e payload com formato de segredo. O corpus é uma regressão determinística; não executa payloads, não chama ferramentas e não decide vereditos.

A existência de um identificador de citação ou de um hash não prova que a fonte externa seja verdadeira. O controle valida consistência com o material fornecido e a trilha registrada, dentro do escopo implementado.

### Autenticação HTTP

A autenticação por chave é habilitada por padrão. O middleware permite somente `/health` sem credenciais; as demais rotas HTTP são protegidas, incluindo documentação servida pela aplicação.

- O modo `api_key` exige um pepper de 32 bytes em hexadecimal e ao menos um digest HMAC-SHA-256 configurado.
- Chaves apresentadas com menos de 32 caracteres são rejeitadas.
- O cliente pode enviar `Authorization: Bearer` ou `X-API-Key`; cabeçalhos duplicados ou o uso simultâneo dos dois mecanismos são rejeitados para evitar ambiguidade.
- A comparação usa `hmac.compare_digest`. O pepper deve ser mantido separado da lista de digests, e a chave bruta não deve ser commitada ou escrita em logs.
- Configuração ausente ou malformada no modo `api_key` interrompe a inicialização. `ATTRACTOR_AUTH_MODE=off` só é permitido como escolha explícita em desenvolvimento local isolado.

Os procedimentos de geração e configuração de segredos estão em [API-AUTH.md](../security/API-AUTH.md). Exemplos versionados usam placeholders; nunca os substitua por segredos reais no repositório.

### Limite de entrada e logs

O middleware de corpo limita requisições HTTP a 2 MiB por padrão; `ATTRACTOR_MAX_BODY_BYTES` aceita somente inteiro positivo. O middleware de contexto gera ou valida `X-Request-ID`, devolve esse cabeçalho na resposta e emite um registro estruturado com identificador, método, rota normalizada, status e duração. O registro de acesso não inclui corpo, afirmações, trechos de evidência, prompts ou credenciais.

Falhas de autenticação retornam HTTP 401 com mensagem genérica. O endpoint `/health` é público para probes, mas confirma somente que a rota respondeu; não demonstra a saúde de todas as dependências.

### Análise de segurança e supply chain

Os workflows atuais se complementam, mas não se substituem:

- `.github/workflows/security.yml` executa `pip-audit`, gera um SBOM CycloneDX como artefato e executa Bandit sobre `src/ayorai_attractor`.
- `.github/workflows/codeql.yml` executa análise CodeQL para Python com o conjunto `security-extended`.
- O workflow de revisão de dependências verifica mudanças de dependências em pull requests.
- Os checks de CI incluem testes, regressões do Judge/Golden e contratos. Uma simulação RGC ignorada por condição de workflow não deve ser descrita como aprovada.

Esses controles são verificações pontuais no SHA avaliado. Um resultado verde não demonstra ausência de vulnerabilidades desconhecidas nem valida o ambiente de implantação.

## Contratos e parâmetros

| Parâmetro/controle | Comportamento |
|---|---|
| `ATTRACTOR_AUTH_MODE` | `api_key` por padrão; `off` apenas por escolha explícita em desenvolvimento local isolado. |
| `ATTRACTOR_API_KEY_PEPPER` | Segredo de 32 bytes codificado como 64 caracteres hexadecimais. |
| `ATTRACTOR_API_KEYS_HMAC_SHA256` | Lista separada por vírgulas de digests HMAC-SHA-256 de 64 caracteres hexadecimais. |
| `ATTRACTOR_MAX_BODY_BYTES` | Limite de corpo HTTP inteiro positivo; padrão 2 MiB. |
| `ATTRACTOR_LOG_LEVEL` | `DEBUG`, `INFO`, `WARNING`, `ERROR` ou `CRITICAL`; padrão `INFO`. |
| `X-Request-ID` | Aceita identificador ASCII com 1–64 caracteres alfanuméricos/hífens; valor inválido é substituído. |
| HTTP 401 / 413 / 422 | Falha de autenticação / corpo acima do limite / falha de validação, respectivamente. |

## Limites conhecidos

- A autenticação por chave não implementa autorização por escopos, limitação de taxa, gestão de identidade completa, rotação automatizada de segredos ou resposta a incidentes.
- A proteção depende também de HTTPS quando a rede não é confiável, controles de rede, configuração segura do host, gestão de segredos e atualização de dependências.
- O corpus red-team contém expectativas determinísticas de tratamento; não é, isoladamente, uma prova end-to-end de que todo payload sensível jamais será persistido.
- O runtime não prova a veracidade de fontes externas, não substitui avaliação jurídica de licenças e não garante generalização além dos dados avaliados.
- Hashes, logs estruturados, CI e autenticação não constituem certificação, parceria institucional, garantia contra adulteração ou evidência de prontidão para produção.
- O conjunto Golden v1 oculto deve permanecer fora do desenvolvimento. Nenhum caso de piloto, desenvolvimento ou avaliação confirmatória RGC deve ser enviado a assistentes/modelos ou executado no ATTRACTOR sem os gates explícitos definidos pelo mantenedor.

## Evidências

- `docs/THREAT-MODEL.md`: escopo, ativos, ameaças, controles e não objetivos.
- `docs/security/API-AUTH.md` e `src/ayorai_attractor/api/auth.py`: configuração fail-closed e autenticação.
- `src/ayorai_attractor/verification/excerpt.py` e `src/ayorai_attractor/synthesis.py`: revalidação de trecho e gate de citação.
- `docs/security/RED-TEAM.md` e `src/ayorai_attractor/redteam.py`: corpus determinístico e escopo da regressão adversarial.
- `src/ayorai_attractor/api/request_context.py` e `src/ayorai_attractor/api/app.py`: correlação, logging e limite de corpo.
- `.github/workflows/security.yml`, `.github/workflows/codeql.yml` e `.github/workflows/dependency-review.yml`: controles de supply chain.
- `tests/test_api_auth.py`, `tests/test_api_request_context.py`, `tests/test_verification_response_security.py` e testes de verificação do Judge.

## Ver também

- [04 — API HTTP e contratos](04-api.md)
- [05 — Operação e execução](05-operacao.md)
- [Autenticação da API](../security/API-AUTH.md)
- [Modelo de ameaças](../THREAT-MODEL.md)
- [Regressão red-team](../security/RED-TEAM.md)
- [Docker](../DOCKER.md)
