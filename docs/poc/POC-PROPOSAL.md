# Proposta de POC institucional controlada

**Estado:** PROPOSTO. Nenhuma POC foi executada. Este documento não declara validação, certificação, homologação, parceria nem endosso de qualquer instituição.

## 1. Objetivo

Demonstrar, num ambiente controlado e com documentos escolhidos pela instituição parceira, que o AYORAI ATTRACTOR consegue mostrar para cada afirmação:

1. o que foi afirmado;
2. quais evidências foram encontradas e de onde vieram;
3. como cada evidência se relaciona com a afirmação (apoia, contradiz, neutra), com trecho e posição exatos;
4. por que o Judge determinístico chegou ao resultado (contagem de fontes independentes que apoiam e que contradizem);
5. quando ele se abstém, e por quê;
6. como reproduzir a análise depois;
7. como verificar que o histórico não foi alterado.

A POC demonstra o funcionamento e a rastreabilidade. **Não mede acurácia de forma científica**; isso exige o benchmark com anotação humana e protocolo congelado (ver `docs/STATUS.md`).

## 2. Escopo recomendado

Um caso de uso só, com documentos fornecidos pelo parceiro, para que a recuperação não seja uma variável:

- **Recomendado:** conferência de afirmações sobre documentos (por exemplo, números, datas e valores em relatórios financeiros ou institucionais) com `POST /v1/check` e `POST /v1/fields`. O cliente envia os documentos; nada é buscado fora.
- **Opcional, numa segunda etapa:** `POST /v2/audit` sobre um índice OpenSearch montado só com os documentos do parceiro.

**Fora de escopo:**
- documentos sigilosos ou com dados pessoais sem acordo específico;
- decisões automatizadas sobre pessoas;
- qualquer uso do resultado como prova jurídica;
- casos do benchmark RGC;
- divulgação pública de resultados sem aprovação do mantenedor.

## 3. Pré-requisitos de engenharia

Estes itens precisam estar integrados na `main`, cada um com autorização do mantenedor:

| Item | PR ou decisão | Por que é necessário na POC |
|---|---|---|
| Todo documento relacionado chega à adjudicação | #589 (integrada) | Sem isso, uma contradição pode ser ignorada e o resultado sair `verified` |
| Rastro do `/v2/audit` vincula a adjudicação | #590 | Prova que a resposta guardada é a que foi entregue |
| Uma fonte por resultado de busca | #591 | Necessário só se o `/v2/audit` entrar no escopo |
| Falsos apoios (pergunta, condição, meta, retificação) | #592 | Reduz apoios indevidos |
| Erros de provider sem URL interna | #593 | Evita expor a topologia do parceiro |
| Rotação de chave HMAC | #594 | Operação segura da trilha durante a POC |
| Independência por conteúdo normalizado (P1-1) | Decisão do mantenedor | Sem ela, cópias quase idênticas contam como fontes distintas; na POC, os documentos devem ser revisados para evitar duplicatas |
| Proveniência exigida para o veredito mais forte (P1-2) | Decisão do mantenedor | Sem ela, texto sem URL chega a `verified`; na POC, cada documento deve ter `url` ou origem declarada |

## 4. Infraestrutura

- Um host Linux com Docker. A imagem do projeto roda como usuário sem privilégios, com o volume `attractor-audit` para a trilha.
- Gateway nginx com TLS e o limite de `docs/security/EDGE-RATE-LIMIT.md`; `FORWARDED_ALLOW_IPS` apontando só para o gateway.
- `ATTRACTOR_AUTH_MODE=api_key`, uma chave por usuário da POC (cada rastro tem dono).
- `ATTRACTOR_AUDIT_HMAC_KEYS` vindo de um gerenciador de segredos e `ATTRACTOR_AUDIT_HMAC_REQUIRED=true`.
- Retenção definida com o parceiro (`ATTRACTOR_AUDIT_RETENTION_DAYS`).
- Backup diário com `AuditTraceStore.backup()` e um teste de restauração antes do início.
- Provider de LLM desligado (`ATTRACTOR_PROVIDER=mock`) quando o escopo for só `/v1/check` e `/v1/fields`: nenhum texto vai para fora.

## 5. Critérios de aceitação

Todos são verificáveis por quem não escreveu o código:

1. **Rastreabilidade:** para cada resultado, o relatório mostra afirmação, documento, trecho com offsets exatos (o trecho é igual a `texto[início:fim]`), página e postura.
2. **Explicabilidade:** cada veredito pode ser recalculado à mão pela regra do ADR-002 a partir das posturas listadas.
3. **Abstenção:** em pelo menos 10 afirmações sem suporte nos documentos, o sistema se abstém; nenhuma recebe apoio.
4. **Contradição:** em pelo menos 10 afirmações com valor, data ou ano trocados, o resultado é `refuted` ou `conflicting`; nenhuma é `verified`.
5. **Reprodução:** reenviar a mesma requisição dá o mesmo `trace_id` (`chk_…`) e o mesmo resultado.
6. **Integridade:** `verify_all()` dá `invalid = 0`. Uma adulteração feita de propósito numa cópia do banco (alterar uma contagem, um dono ou o digest da adjudicação) resulta em `invalid`.
7. **Recuperação:** depois de reiniciar o container e restaurar o backup, os rastros continuam `valid`.
8. **Isolamento:** a chave de um usuário não lê o rastro de outro (404).
9. **Segurança operacional:** os logs não contêm conteúdo, afirmações nem segredos; erros não expõem endereços internos.

O conjunto de afirmações usado nos critérios 3 e 4 é preparado e rotulado **por pessoas do parceiro**, antes da execução, e guardado com hash. O resultado é relatado como demonstração, com a contagem de acertos e erros, sem ser apresentado como acurácia geral.

## 6. Riscos

| Risco | Mitigação |
|---|---|
| Baixa cobertura: o sistema se abstém muito (o Golden atual mostra muitos `UNVERIFIED` onde a referência espera apoio) | Apresentar a abstenção como comportamento conservador, mostrar a taxa e não prometer cobertura |
| Duplicatas contadas como fontes independentes (P1-1) | Curadoria dos documentos; decisão do mantenedor sobre P1-1 antes da POC |
| Expectativa de "certificação" | Este documento e a política de alegações do `CONTRIBUTING.md` |
| Perda de chave HMAC | Custódia em gerenciador de segredos; rotação com `reseal_with_active_key()` |
| Exclusão silenciosa de rastros (P2-1) | Backups com hash registrados fora do host até a decisão de desenho |
| Dados pessoais | Escopo sem dados pessoais; retenção acordada; nenhuma conformidade legal declarada |

## 7. Plano de avaliação

1. **Preparação (parceiro):** escolher os documentos e escrever as afirmações com o rótulo esperado; registrar o hash do conjunto.
2. **Homologação:** subir a infraestrutura da seção 4 e rodar os critérios 5 a 9.
3. **Execução:** uma rodada única sobre o conjunto registrado, guardando requisições, respostas e o banco da trilha.
4. **Verificação:** uma pessoa que não escreveu o código confere os critérios 1 a 4 com o relatório e os documentos.
5. **Relatório:** o que funcionou, o que falhou e as abstenções, com todos os erros listados e sem números fora desse contexto.

## 8. Aplicações possíveis, por ordem de adequação ao estado atual

1. Conferência de números, datas e valores em documentos financeiros ou institucionais (`/v1/check`, `/v1/fields`): é o caminho mais testado.
2. Auditoria de respostas de sistemas de IA contra documentos de referência fornecidos (`/v1/check` com `answer`).
3. Análise de documentos regulatórios: exige cuidado com vigência e retificações, que o sistema não resolve sozinho.
4. Verificação aberta com busca (`/v2/audit`): depende da qualidade do índice e das PRs #590 e #591 (a #589 já está integrada).
