Estado: Atual · Referência: main @ 64461fd · Atualizado: 2026-10-21
Fontes de verdade: `Makefile`, `pyproject.toml`, `docker-compose.yml`, `docker/Dockerfile`, `docs/DOCKER.md`, `docs/security/API-AUTH.md`, `src/ayorai_attractor/api/app.py`, `src/ayorai_attractor/api/auth.py`, `src/ayorai_attractor/api/logging_config.py` e testes operacionais/API correspondentes.

# 05 — Operação e execução

## Propósito e limites

Este capítulo reúne os procedimentos operacionais existentes para instalar, iniciar e verificar a API em ambiente local. Os arquivos de configuração e os scripts citados abaixo são a fonte de verdade; este texto não cria um perfil de produção nem substitui uma avaliação de segurança, capacidade, disponibilidade ou recuperação.

A configuração padrão exige autenticação por chave de API. Uma configuração ausente ou inválida no modo `api_key` impede a inicialização; isso é comportamento fail-closed, não uma falha a contornar desabilitando a proteção.

## Pré-requisitos

- Python compatível com `pyproject.toml` (Python 3.11 ou superior).
- Dependências instaladas no ambiente virtual ou ambiente de desenvolvimento isolado.
- Para execução em contêiner: Docker com suporte ao comando `docker compose`.
- Credenciais de API geradas para o ambiente e armazenadas fora do repositório, em mecanismo de segredos apropriado.

Não versione arquivos `.env`, chaves brutas, pepper, digests reais ou dados de requisições. Use apenas os placeholders dos exemplos versionados.

## Instalação e execução local

Na raiz do repositório, instale o projeto com as dependências de desenvolvimento:

```bash
python -m pip install -e ".[dev]"
```

O Makefile oferece os atalhos `make install`, `make test`, `make lint`, `make typecheck` e `make security`. Para iniciar a API no modo de desenvolvimento, depois de configurar a autenticação e as variáveis necessárias:

```bash
make run
```

O alvo `run` usa Uvicorn com recarga automática, ciclo de vida habilitado e sem o access logger padrão. Ele é destinado ao desenvolvimento, não a uma implantação de produção. Consulte [autenticação da API](../security/API-AUTH.md) para gerar e configurar os segredos sem os registrar no terminal ou no Git.

## Execução com Docker Compose

O procedimento detalhado está em [Docker deployment](../DOCKER.md). O fluxo resumido é:

1. Copie `.env.example` para `.env` localmente.
2. Configure `ATTRACTOR_AUTH_MODE=api_key`, o pepper de 32 bytes em hexadecimal e a lista de digests HMAC-SHA-256 válidos.
3. Construa e inicie o serviço:

   ```bash
   docker compose up --build -d
   docker compose ps
   ```

4. Confirme que o contêiner está ativo e que o processo não executa como root.
5. Verifique a rota pública de saúde e confirme que uma rota protegida rejeita uma chamada sem credenciais.

O Compose publica a porta do host em `127.0.0.1:8000`, não em todas as interfaces. Alterar esse vínculo amplia a exposição e exige uma avaliação deliberada dos controles de rede. O processo dentro do contêiner escuta em `0.0.0.0:8000` para permitir o encaminhamento da porta pelo Docker; isso não altera, por si só, o vínculo da porta no host.

## Verificações operacionais básicas

### Saúde e autenticação

```bash
curl -i http://127.0.0.1:8000/health
curl -i http://127.0.0.1:8000/v1/audit
```

Com a autenticação habilitada, a primeira chamada deve responder sem credenciais; a segunda deve retornar HTTP 401 quando enviada sem chave. Para chamar uma rota protegida, use uma chave configurada no ambiente por `Authorization: Bearer` ou `X-API-Key`. Não coloque a chave na URL.

`/health` comprova apenas que a rota respondeu. Não confirma a disponibilidade de todos os provedores, integrações, fontes externas ou dependências, nem mede desempenho ou capacidade.

### Testes e verificações de qualidade

Os alvos disponíveis no Makefile são:

| Comando | Finalidade |
|---|---|
| `make test` | Executar a suíte pytest |
| `make lint` | Verificar lint e formatação com Ruff |
| `make typecheck` | Verificar tipos com mypy |
| `make security` | Executar pip-audit e Bandit |
| `make reproduce-quick` | Executar o modo rápido do script de reprodução |
| `make reproduce` | Executar o fluxo completo definido pelo script de reprodução |

Execute os comandos no ambiente configurado para o commit que está sendo avaliado e preserve os resultados como evidência. Não trate uma execução local não realizada como aprovada; para mudanças via pull request, confira os checks do SHA exato da cabeça da PR e os gates obrigatórios do repositório.

## Logs e rastreabilidade de requisições

A API registra metadados estruturados por requisição: identificador de requisição, método, rota normalizada, status HTTP e duração. A resposta inclui `X-Request-ID`; um valor de entrada fora do padrão aceito é substituído por um identificador gerado. O nível é controlado por `ATTRACTOR_LOG_LEVEL`, com padrão `INFO`.

O logger de acesso da aplicação não deve registrar corpos, afirmações, trechos de evidência, credenciais ou query strings. Ao investigar incidentes, use o identificador de requisição e metadados operacionais; não copie dados sensíveis para logs, issues ou pull requests. O rastro consultável pela API tem seu próprio contrato e não deve ser confundido com o log de acesso.

## Parada, diagnóstico e recuperação

1. Registre o horário, ambiente, versão/commit e identificador de requisição pertinente, sem incluir segredos ou conteúdo sensível.
2. Verifique o estado do processo/contêiner e os logs operacionais disponíveis.
3. Confirme se a configuração de autenticação e as variáveis obrigatórias estão presentes, sem imprimir seus valores secretos.
4. Diferencie falha de inicialização, falha de autenticação, validação HTTP, limite de corpo e indisponibilidade de dependência.
5. Reproduza o problema em ambiente isolado com dados não sensíveis e testes direcionados.
6. Para mudança de código ou configuração, use revisão, checks obrigatórios e procedimento controlado de implantação; não edite artefatos congelados nem contorne testes para restaurar o serviço.

Este capítulo não define uma política de backup, restauração, alta disponibilidade, SLO, rotação automatizada de segredos ou rollback de produção. Esses procedimentos precisam ser definidos e validados para o ambiente concreto antes de alegar prontidão operacional.

## Limites conhecidos

- A autenticação por chave não substitui HTTPS em redes não confiáveis, controle de rede, autorização por escopo, limitação de taxa, rotação operacional de segredos ou resposta a incidentes.
- `/health` não é um teste abrangente de dependências.
- Uma suíte verde não é certificação nem prova de prontidão para produção.
- O modo de desenvolvimento com recarga automática não deve ser tratado como configuração de implantação.
- A operação de `/v1/opensearch` ou `/v1/audit` não substitui a verificação formal em `/v1/verify`.

## Referências

- [Docker deployment](../DOCKER.md)
- [Autenticação da API](../security/API-AUTH.md)
- [API HTTP e contratos](04-api.md)
- [Makefile](../../Makefile)
- [Configuração do projeto](../../pyproject.toml)
