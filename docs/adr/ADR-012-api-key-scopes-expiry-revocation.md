# ADR-012 — Escopos, expiração e revogação sem reinício das chaves de API

- **Status:** Accepted. Decisão do mantenedor em 2026-11-21 (DEC-031), com as opções recomendadas.
- **Data:** 2026-11-21
- **Decisor:** Anderson Leon Ayora
- **Relaciona-se com:** `ROADMAP.md` §2 (antiga #434), gate G2; `api/auth.py`; isolamento por principal (#564).
- **Não altera:** regras do Judge, Golden, RGC, ADR-009 nem ADR-010. O tenant fica para uma ADR própria.

## Contexto

Hoje (`main` @ `aff55ceb`), `ATTRACTOR_API_KEYS_HMAC_SHA256` traz uma lista de digests HMAC-SHA-256 (com pepper) das chaves aceitas. Isso tem três limites:

1. Toda chave aceita dá acesso a todas as rotas protegidas, inclusive `GET /metrics` e a leitura de rastros.
2. Nenhuma chave expira.
3. Revogar uma chave exige tirar o digest da variável e reiniciar o processo. Fora do histórico da configuração, nada registra quem revogou.

O principal de cada chave (`principal_for_digest`) já é estável e é o dono dos rastros (#564). Esse vínculo não pode mudar.

## Decisão

### 1. Registro de chaves em arquivo, recarregado sem reinício

Uma variável nova, `ATTRACTOR_API_KEYS_FILE`, aponta para um arquivo JSON:

```json
{
  "schema": "ayorai.api-keys.v1",
  "keys": [
    {
      "id": "ops-2026-11",
      "digest": "<HMAC-SHA-256 hex da chave com o pepper>",
      "scopes": ["verify", "audit:read"],
      "expires_at": "2027-01-01T00:00:00Z",
      "revoked_at": null,
      "revoked_by": null
    }
  ]
}
```

- **Campos de cada chave:**
  - `id`: rótulo único, `[a-z0-9][a-z0-9._-]{0,63}`;
  - `digest`: 64 caracteres hex, único no arquivo;
  - `scopes`: lista não vazia de escopos conhecidos;
  - `expires_at`: data UTC em RFC 3339 terminada em `Z`, ou `null` (sem expiração);
  - `revoked_at` e `revoked_by`: os dois `null`, ou os dois preenchidos.
- **Campos desconhecidos ou duplicados tornam o arquivo inválido.**
- **O arquivo nunca contém chaves**, só digests. O principal continua sendo `principal_for_digest(digest)`: trocar o `id` ou os escopos não muda o dono dos rastros.
- **Recarga:**
  - o serviço confere a data de modificação, o tamanho e o inode do arquivo no máximo uma vez a cada `ATTRACTOR_API_KEYS_RELOAD_SECONDS` (padrão 1 s);
  - quando algo muda, relê e valida o arquivo inteiro antes de trocar a configuração.
- **Rastro da revogação:** a cada recarga, o log registra quantas chaves estão ativas e o `id` e o `revoked_by` de cada revogação nova, nunca digests. Quem revogou fica no arquivo e nesse log.
- **Compatibilidade:** sem `ATTRACTOR_API_KEYS_FILE`, `ATTRACTOR_API_KEYS_HMAC_SHA256` funciona como hoje: todos os escopos, sem expiração. Usar as duas variáveis juntas é erro de configuração na subida, para não haver duas fontes de verdade.

### 2. Arquivo inválido durante a operação: mantém o último válido

- **Na subida,** um arquivo ausente, ilegível ou inválido impede o serviço de iniciar (falha fechada).
- **Depois da subida,** se uma recarga encontrar um arquivo inválido, o serviço:
  - continua com a última versão válida;
  - registra o erro (só o tipo e a posição, nunca o conteúdo);
  - incrementa `attractor_api_keys_reload_failures_total`, com o alerta `AttractorApiKeysReloadFailing`.
- **Consequência aceita:** uma revogação só vale quando o arquivo que a contém for válido. O alerta é o que torna visível uma revogação que não entrou em vigor.

### 3. Escopos por rota

| Escopo | Rotas |
|---|---|
| `verify` | `POST /v1/check`, `POST /v1/fields`, `POST /v1/verify`, `POST /v1/opensearch` |
| `audit:write` | `POST /v1/audit`, `POST /v2/audit` |
| `audit:read` | `GET /v1/audit/{trace_id}`, `GET /v1/verify/log` |
| `metrics` | `GET /metrics` |

- **Rotas sem escopo:** `/health` e `/ready` continuam sem chave. As demais rotas, como a documentação OpenAPI e caminhos desconhecidos, exigem uma chave válida e não exigem escopo; caminhos desconhecidos continuam com 404.
- **Respostas:**
  - chave ausente, desconhecida, expirada ou revogada: **401** `Unauthorized`, igual para todos os casos, para não revelar qual chave existe;
  - chave válida sem o escopo da rota: **403** `Forbidden`.
- **Expiração:** comparada com o relógio UTC do servidor a cada requisição. A chave vale até o instante `expires_at`, exclusive.
- **Limite por chave:** continua por digest. O número máximo de identidades do limitador acompanha o número de chaves do arquivo a cada recarga.

### 4. Ferramenta de emissão

`python -m ayorai_attractor.api.keys new --id ... --scope ... [--expires ...]`:
- gera uma chave com `secrets.token_urlsafe(32)` e calcula o digest com o pepper;
- mostra a chave uma única vez e imprime a entrada JSON pronta para o arquivo.

`revoke --id ... --by ...` marca a chave como revogada no arquivo. A gravação é atômica, por arquivo temporário e `os.replace`.

### 5. Tenant: fora desta ADR

O tenant distinto de principal fica para uma ADR própria. Até lá, a implantação suportada continua sendo de um único tenant, como já documentado no `ROADMAP.md` §2.

## Consequências

- O mantenedor pode emitir chaves só de leitura de métricas ou só de verificação, com prazo, e revogar uma chave sem derrubar o serviço.
- **O arquivo vira ativo sensível:** quem altera o arquivo concede acesso. Ele deve ter permissão restrita e ficar fora do volume de dados, de preferência montado só para leitura no contêiner. Os digests sozinhos não permitem testar chaves sem o pepper.
- Uma revogação entra em vigor em até `ATTRACTOR_API_KEYS_RELOAD_SECONDS` mais a duração das requisições em curso.
- Implantação com vários processos ou réplicas: cada processo relê o arquivo por conta própria. Todos convergem quando o arquivo é o mesmo, por exemplo num volume compartilhado.

## Critérios de aceite da implementação

1. Testes negativos para cada escopo (403), chave expirada (401), chave revogada (401) e chave desconhecida (401).
2. Uma revogação gravada no arquivo vale sem reinício, dentro do intervalo de recarga.
3. Um arquivo inválido na subida impede o início. Inválido depois da subida, mantém o último válido e incrementa a métrica.
4. O modo legado (só a variável) não muda: os testes existentes de autenticação continuam passando sem alteração.
5. O principal de uma chave é o mesmo nos dois modos, e o rastro gravado com uma chave continua legível por ela depois da migração para o arquivo.
6. Nenhum digest, chave ou pepper aparece em log, métrica ou resposta.
