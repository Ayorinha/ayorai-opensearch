Estado: Atual · Referência: main @ 34c53b2 · Atualizado: 2026-10-21

# 09 — Auditoria e rastreabilidade

## Objetivo

A auditoria do AYORAI ATTRACTOR expõe sinais verificáveis sobre evidências, proveniência, falhas e rastreabilidade. Ela não altera um veredito nem substitui a autoridade do Judge determinístico. Este capítulo descreve os contratos existentes, não promete imutabilidade absoluta nem certificação.

Fontes principais: o módulo de auditoria, a API HTTP, o contexto de requisição, a configuração de logs e o histórico técnico em [AUDIT-SINCE-v0.5.0.md](../audit/AUDIT-SINCE-v0.5.0.md).

## O que o relatório de auditoria contém

O relatório de auditoria derivado de uma resposta inclui:

- identificador de rastreamento;
- estado de verificação explicitamente marcado como não adjudicado;
- quantidade total de evidências, quantidade marcada como independente e quantidade marcada como verificada;
- quantidade de falhas e achados categorizados por código e severidade.

Achados típicos incluem ausência de evidências, independência fraca, ausência de evidência verificada e falhas reportadas por componentes. Falhas recuperáveis são sinalizadas como aviso; falhas não recuperáveis são sinalizadas como erro. Esses níveis resumem sinais do contrato, não constituem uma pontuação de verdade.

## O que auditoria não significa

- Um relatório de auditoria não é o veredito factual final.
- Duas evidências marcadas como independentes não provam independência epistemológica ou ausência de uma fonte comum.
- Um campo de evidência verificada não prova que a fonte externa seja verdadeira.
- A presença de um request ID ou hash não torna o armazenamento imutável.
- A ausência de achados não é prova de ausência de risco.
- O endpoint de auditoria não executa nem substitui o endpoint formal de verificação.

A API diferencia a busca, a auditoria e a verificação formal. O contrato de /v1/opensearch e /v1/audit não adjudica a afirmação; a verificação formal é feita pelo caminho definido em /v1/verify.

## Correlação de requisições

O middleware de contexto gera ou valida o cabeçalho X-Request-ID, devolve o identificador na resposta e o associa a metadados estruturados de acesso. O log registra campos operacionais como método, rota normalizada, status e duração. Isso permite correlacionar a chamada com o registro correspondente sem copiar o conteúdo integral da requisição.

Um identificador fornecido pelo cliente pode ser substituído se não obedecer ao formato aceito. Não use o request ID como segredo, token de autorização ou prova criptográfica de integridade.

## Logs de acesso e trilha de auditoria

O log de acesso e o relatório de auditoria são artefatos distintos:

| Artefato | Finalidade | Limite |
|---|---|---|
| Log de acesso estruturado | Diagnóstico operacional e correlação por request ID | Não é, por si só, uma trilha imutável ou um histórico completo da decisão |
| Relatório de auditoria | Resumir evidências, sinais de verificação e falhas presentes na resposta | Não adjudica a afirmação nem prova a verdade da fonte |
| Evidência/proveniência | Identificar a fonte, localização e suporte usado pelo fluxo de verificação | A validade externa da fonte continua fora do alcance do runtime |

Não registre corpos, prompts, afirmações, trechos de evidência, credenciais ou query strings em logs de acesso. Para investigar um incidente, use o request ID, o SHA da aplicação, horário, rota normalizada e status, evitando replicar conteúdo sensível em issues ou pull requests.

## Como interpretar os achados

1. Preserve o SHA, ambiente, horário e request ID relacionados ao caso.
2. Verifique a evidência e sua proveniência no artefato original; não confie apenas em uma explicação textual.
3. Diferencie falha de entrada, ausência de evidência, evidência não verificada e falha operacional.
4. Se houver conflito, não transforme o relatório de auditoria em decisão automática. Encaminhe a questão ao fluxo formal de verificação e aos controles humanos aplicáveis.
5. Registre correções de contrato e testes em PRs separadas por assunto.

## Retenção e limites operacionais

O repositório não define sozinho a retenção legal, backup, restauração, armazenamento externo imutável, sincronização de relógio, monitoramento contínuo ou resposta a incidentes. Esses requisitos devem ser definidos para o ambiente concreto. O logger local não equivale a um SIEM nem a uma trilha inviolável.

A revisão de segurança e a execução de CI são evidências do SHA avaliado, não validação independente. Não alegue certificação, parceria institucional ou prontidão de produção a partir dos relatórios.

## Referências

- [Histórico técnico desde v0.5.0](../audit/AUDIT-SINCE-v0.5.0.md)
- [Modelo de ameaças](../THREAT-MODEL.md)
- [Autenticação da API](../security/API-AUTH.md)
- [Segurança e modelo de ameaças](06-seguranca.md)
- [Operação e execução](05-operacao.md)
- [API HTTP e contratos](04-api.md)
