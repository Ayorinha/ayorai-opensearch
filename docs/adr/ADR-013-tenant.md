# ADR-013 — Tenant distinto de principal

- **Status:** Accepted. Decisão do mantenedor em 2026-11-22 (DEC-032), com as opções recomendadas.
- **Data:** 2026-11-22
- **Decisor:** Anderson Leon Ayora
- **Relaciona-se com:** ADR-012 (arquivo de chaves), ADR-010 (log de verificação), `ROADMAP.md` §2 e gate G2.
- **Não altera:** regras do Judge, Golden, RGC, o esquema assinado da trilha (`r2-v3`/`r2-v4`) nem as folhas do log Merkle.

## Contexto

Desde a #564, cada rastro de auditoria tem um dono, o principal da chave que o gravou, e só esse principal o lê. Isso isola chaves, mas não permite que uma equipe compartilhe a própria trilha. Também não separa organizações que dividem uma implantação. A ADR-012 deixou o tenant para esta ADR (DEC-031).

## Decisão

### 1. O tenant é um campo do arquivo de chaves

- Cada entrada do arquivo da ADR-012 aceita o campo opcional `tenant`, no formato `[a-z0-9][a-z0-9._-]{0,63}`.
- Sem o campo, a chave pertence ao tenant `default`. O esquema do arquivo continua `ayorai.api-keys.v1`: o campo é opcional, e arquivos sem ele continuam válidos.
- O tenant é resolvido pelo registro de chaves no momento de cada requisição. **A trilha não grava o tenant:**
  - o esquema assinado por HMAC não muda;
  - não há migração de banco.
- **Consequência aceita:** mudar o tenant de uma chave no arquivo muda, a partir da recarga, quem lê os rastros que ela gravou. Por isso, uma entrada revogada deve continuar no arquivo: assim os rastros dela continuam legíveis pelo tenant.

### 2. Leitura de rastros por tenant

- `GET /v1/audit/{trace_id}` devolve o rastro quando o dono dele pertence, no registro atual, ao mesmo tenant da chave que lê. A chave que lê precisa do escopo `audit:read` (ADR-012).
- O dono pode estar revogado ou expirado: a leitura depende da chave que lê, não da que gravou.
- Entre tenants, a resposta é sempre 404, igual à de um rastro inexistente.
- **Modo legado** (`ATTRACTOR_API_KEYS_HMAC_SHA256`, sem arquivo): não há informação de tenant, então cada chave lê só os próprios rastros, como hoje.
- Rastros sem dono continuam sob `ATTRACTOR_AUDIT_LEGACY_TRACES`.

### 3. Log de verificação: um log, tenant no registro

- O `/v1/verify` continua com um único log Merkle, com uma origem e uma chave de assinatura.
- O registro salgado passa a `ayorai.verify-record.v2`, que é o `v1` mais o campo `tenant`. O tenant nunca entra na folha pública.
- O recibo não muda de formato. Registros `v1` já gravados continuam válidos e verificáveis.
- A `Idempotency-Key` continua separada por cliente (principal), o que já a separa por tenant.

### 4. Fora desta ADR

Limite de requisições por tenant, cotas, bancos separados por tenant e administração de tenants por API.

## Consequências

- Uma equipe passa a compartilhar a trilha sem compartilhar chaves. Organizações diferentes ficam isoladas na mesma implantação.
- **O arquivo de chaves passa a definir também quem lê o quê.** O cuidado com ele, descrito na ADR-012, vale em dobro.
- A implantação compartilhada passa a ser suportada para a trilha e o log de verificação. Os limites de requisição continuam por chave e por IP.

## Critérios de aceite da implementação

1. Duas chaves do mesmo tenant leem os rastros uma da outra. Uma chave de outro tenant recebe 404 nos dois sentidos.
2. Sem `audit:read`, a resposta é 403, mesmo dentro do tenant.
3. O modo legado não muda: cada chave lê só os próprios rastros.
4. Uma chave revogada continua com os rastros legíveis pelo tenant, e mudar o tenant no arquivo vale sem reinício.
5. Os registros novos do log trazem `tenant` (`v2`), e os recibos `v1` e `v2` verificam.
6. O arquivo com `tenant` inválido é recusado. O arquivo sem `tenant` continua válido.
