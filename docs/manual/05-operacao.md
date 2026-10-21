Estado: Atual · Referência: main @ 64461fd · Atualizado: 2026-10-21
Fontes de verdade: `src/ayorai_attractor/cli/main.py`, `pyproject.toml`, `docs/providers.md`, `docs/DOCKER.md`, `docker-compose.yml`, `.env.example`, `src/ayorai_attractor/api/app.py`, `src/ayorai_attractor/orchestrator.py`, `src/ayorai_attractor/evaluation/golden.py`, testes `tests/test_cli_contract.py`, `tests/test_cli_module.py`, `tests/test_reproduce_script.py` e `tests/test_api_uvicorn_body_limit.py`.

# 05 — Operação e execução

## Propósito

Este capítulo descreve os caminhos operacionais existentes para instalar o projeto, consultar a CLI, executar uma suíte Golden de desenvolvimento e iniciar a API em ambiente local ou via Docker. Ele não é uma autorização para executar o ATTRACTOR em dados do piloto, desenvolvimento ou avaliação confirmatória do RGC PT-BR.

## Como funciona

O projeto publica dois entrypoints de CLI em `pyproject.toml`:

- `attractor` abre a aplicação Typer e oferece os comandos `search` e `eval`.
- `opensearch` aponta diretamente para a função `search`.

A CLI `search` cria um `SearchRequest`, chama `Attractor.run` e imprime a resposta estruturada em JSON. O modo padrão é `balanced` e `max_agents` é 5, salvo opções explícitas. O resultado de pesquisa não equivale a um veredito factual; consulte o capítulo [04 — API HTTP e contratos](04-api.md).

### Preparação local

Em um clone local, use um ambiente virtual e instale o conjunto de desenvolvimento:

```bash
python -m venv .venv
# Ative o ambiente virtual pelo mecanismo do seu sistema operacional.
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
attractor --help
```

A instalação `.[dev]` fornece testes, lint, tipagem estrita e ferramentas de segurança. O extra opcional `[nli]` instala dependências grandes de modelos; não é necessário para consultar a ajuda nem para o caminho de provider local.

### Comandos disponíveis

Consulte a ajuda antes de executar:

```bash
attractor --help
attractor search --help
attractor eval --help
```

Exemplo de pesquisa usando o provider local padrão:

```bash
attractor search "consulta de exemplo" --mode balanced --max-agents 5
```

O provider padrão `mock` não exige rede ou credenciais e marca a saída como não independente. Para usar um adaptador OpenAI-compatível, configure `ATTRACTOR_PROVIDER=openai-compatible` e `OPENAI_API_KEY`; `OPENAI_BASE_URL` e `ATTRACTOR_MODEL` são opcionais conforme `docs/providers.md`. Um provider de execução não é, por si só, uma fonte de evidência.

### Avaliação Golden de desenvolvimento

A CLI aceita somente as suítes `golden-v0`, `golden-v0.1` e `smoke-v0`. Exemplo:

```bash
attractor eval --suite golden-v0 --out reports/eval-golden-v0.json
```

O comando grava um relatório JSON no caminho informado (o diretório é criado quando necessário) e imprime um resumo com nome da suíte, caminho, acurácia global e baseline majoritária. A seleção do arquivo Golden e a interpretação da suíte estão implementadas em `src/ayorai_attractor/cli/main.py`; não presuma que uma suíte não documentada seja aceita.

Relatórios devem ser tratados como artefatos de execução: registre o SHA do commit, versão da suíte, hashes dos arquivos de entrada, versão do Python, comando completo e configuração do provider sem registrar segredos. Não altere os Goldens congelados para obter um resultado desejado. Métricas de desenvolvimento não demonstram generalização em produção.

**Restrição RGC:** não execute a CLI ou qualquer outro caminho do ATTRACTOR sobre casos de piloto, partição pública de desenvolvimento ou avaliação confirmatória do RGC PT-BR. O runner RGC tem contrato próprio; esta seção descreve apenas a CLI e as suítes Golden existentes.

### Execução da API via Docker

A configuração de Docker documentada publica a porta do host somente em `127.0.0.1:8000`, habilita autenticação por chave por padrão e lê as variáveis de um arquivo local `.env`. O arquivo versionado `.env.example` contém valores vazios para segredos; no modo `api_key`, a aplicação não inicia até que pepper e digest válidos sejam configurados.

Fluxo documentado em `docs/DOCKER.md`:

```bash
cp .env.example .env
# Preencha localmente os segredos necessários; não versione .env.
docker compose up --build -d
docker compose ps
docker compose exec attractor id
curl -i http://127.0.0.1:8000/health
curl -i http://127.0.0.1:8000/v1/audit
```

A resposta de `/health` não exige credenciais. Com autenticação ativa, a chamada sem credenciais a `/v1/audit` deve receber HTTP 401. A identidade do processo no container deve ser não privilegiada. O bind interno do container em `0.0.0.0:8000` não autoriza publicar a porta do host em todas as interfaces; mantenha o mapeamento de loopback salvo decisão operacional explícita e controles de rede adequados.

## Contratos e parâmetros

| Parâmetro | Efeito documentado |
|---|---|
| `ATTRACTOR_PROVIDER` | `mock` é o provider local padrão; `openai-compatible` seleciona o adaptador OpenAI-compatível. |
| `OPENAI_API_KEY` | Credencial do adaptador OpenAI-compatível; não deve ser commitada nem impressa em logs. |
| `OPENAI_BASE_URL` | URL-base opcional para endpoint OpenAI-compatível. |
| `ATTRACTOR_MODEL` | Seleção opcional do modelo no adaptador compatível. |
| `ATTRACTOR_AUTH_MODE` | `api_key` por padrão; `off` somente para desenvolvimento local isolado. |
| `ATTRACTOR_API_KEY_PEPPER` e `ATTRACTOR_API_KEYS_HMAC_SHA256` | Material necessário para autenticação por chave; veja o capítulo 04 e `docs/security/API-AUTH.md`. |
| `ATTRACTOR_LOG_LEVEL` | Nível de logging estruturado; padrão `INFO`. |
| `ATTRACTOR_MAX_BODY_BYTES` | Limite inteiro positivo para o corpo HTTP; padrão de 2 MiB. |

A lista completa de variáveis de exemplo está em `.env.example`; os contratos e limites da API estão no capítulo 04. Não copie valores de segredo para esta tabela ou para documentação versionada.

## Limites conhecidos

- A CLI de pesquisa pode invocar providers configurados; não é um executor offline por definição. Use `ATTRACTOR_PROVIDER=mock` para a saída local determinística descrita no contrato.
- O provider `mock` não é independente nem constitui evidência factual.
- A avaliação Golden executa somente as suítes explicitamente implementadas. Ela não substitui o pré-registro nem autoriza a execução do RGC PT-BR.
- Os módulos de estado durável e armazenamento de jobs não significam que exista uma API pública de fila de jobs ou um worker implantado; verifique os entrypoints e rotas atuais antes de assumir uma operação assíncrona.
- A documentação Docker não constitui validação de segurança, certificação ou garantia de prontidão para produção.

## Evidências

- `pyproject.toml`: entrypoints `attractor` e `opensearch`, dependências e extras.
- `src/ayorai_attractor/cli/main.py`: comandos, suítes permitidas, arquivos de entrada e formato do resumo.
- `docs/providers.md` e `docs/DOCKER.md`: configuração de providers, container, segredos e logs.
- `tests/test_cli_contract.py` e `tests/test_cli_module.py`: contrato de ajuda, seleção de suíte e gravação do relatório.
- `tests/test_reproduce_script.py`: contrato do caminho de reprodução documentado.
- `docker-compose.yml` e `.env.example`: bind de loopback e variáveis de ambiente.

## Ver também

- [04 — API HTTP e contratos](04-api.md)
- [06 — Segurança](06-seguranca.md)
- [07 — Reprodutibilidade](07-reprodutibilidade.md)
- [Providers](../providers.md)
- [Docker](../DOCKER.md)
