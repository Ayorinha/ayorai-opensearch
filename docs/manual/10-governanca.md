Estado: Atual · Referência: main @ 1579041 · Atualizado: 2026-10-21

# 10 — Governança, decisões e mudanças controladas

## Objetivo

Este capítulo descreve como o projeto registra decisões técnicas e científicas, valida mudanças e distingue evidência automatizada de decisões humanas. A governança não congela o protocolo por inferência nem transforma uma suíte verde em validação independente.

## Autoridade e separação de responsabilidades

- O mantenedor decide o escopo, aprova decisões científicas e controla a autoridade final de merge.
- Ferramentas automatizadas podem propor alterações, executar testes e identificar inconsistências; não são revisores humanos independentes.
- O Judge determinístico é a autoridade do veredito formal no contrato de verificação. Texto gerado por LLM, stance, busca ou síntese não autoriza execução nem substitui o veredito.
- A revisão humana independente F-01 permanece distinta de CI, revisão automatizada e autoavaliação do autor.

## Registros de decisão

Use os artefatos versionados como fontes de verdade, mantendo o histórico:

| Artefato | Finalidade |
|---|---|
| [DECISIONS-PENDING.md](../DECISIONS-PENDING.md) | Estado das decisões, opções, justificativas, aprovações e pendências |
| Diretório de ADRs | Decisões arquiteturais, alternativas e consequências |
| Pré-registro RGC | Hipóteses, métricas, critérios e emendas datadas |
| Protocolo RGC | Regras operacionais e científicas, mantendo o estado explícito |
| Revisão metodológica | Achados, evidências e o que continua aberto |
| STATUS.md | Snapshot datado de SHA, CI, PRs e dependências humanas |
| CHANGELOG.md | Mudanças planejadas e implementadas por versão |

Uma aprovação deve registrar quem decidiu, a data, a opção selecionada, os arquivos alterados e os limites que permanecem. Não reescreva silenciosamente o texto anterior: acrescente uma emenda datada e deixe claro qual redação é histórica e qual está vigente.

## Estado científico em 2026-10-21

As opções A de DEC-017, DEC-018, DEC-019 e DEC-020 foram explicitamente aprovadas e registradas em PRs separadas. Em resumo:

- DEC-017 diferencia falha de integridade (interromper) de predição presente inválida (conta como erro no denominador).
- DEC-018 limita H1 confirmatória à partição oculta; a partição pública é apenas descritiva.
- DEC-019 usa bootstrap por cluster de artigo como primário e bootstrap por caso como sensibilidade, com regra explícita para bundles multiartigo.
- DEC-020 usa kappa de Cohen não ponderado, gate pela estimativa pontual de pelo menos 0,6, IC95%, matriz/marginais e exclusão auditável de RULE_GAP.

Essas aprovações definem regras; **não congelam o protocolo**. O estado geral permanece [PROPOSTO]. Nenhuma decisão autoriza criar, completar ou rotular casos de piloto/benchmark, executar o ATTRACTOR sobre casos RGC ou alegar resultados confirmatórios.

## Processo de pull request

1. Uma PR deve tratar de um assunto delimitado; decisões científicas distintas ficam em PRs separadas.
2. Rebaseie na main atual antes do merge quando necessário e verifique os checks do SHA final da cabeça da PR.
3. Os gates incluem a suíte pytest, lint e formatação Ruff, tipagem estrita aplicável, regressões Golden/Judge, segurança e contratos HTTP/OpenAPI conforme as regras do repositório.
4. Não contorne checks obrigatórios nem declare aprovado um job ignorado por condição de workflow.
5. Use squash com mensagem manual e a linha final de governança definida pela DEC-016. Preserve a autoria do mantenedor e não acrescente créditos promocionais de ferramentas ou linhas automáticas de coautoria.
6. Após o merge, registre SHA e evidência CI no snapshot de status. Fechar uma PR como duplicada/superada deve incluir comentário com a substituta.

## Evidência, releases e comunicação

- Relate os comandos que realmente rodaram, a versão de Python/dependências, o SHA e os resultados observados.
- Distinga teste sintético, regressão determinística, experimento exploratório e avaliação confirmatória.
- Não chame uma revisão automatizada de independente nem use percentuais sintéticos como evidência de benchmark.
- Atualize a seção Unreleased do CHANGELOG e mantenha um rascunho de notas para a próxima versão. Não crie tag nem publique release sem autorização explícita.
- Não alegue certificação, validação institucional, parceria ou prontidão de produção sem evidência externa verificável.

## Dependências humanas que permanecem

- Anotação humana do piloto 02, sem IA.
- Segunda anotação realizada por outra pessoa e cálculo de concordância somente depois de concluída.
- Revisão humana independente F-01.
- Decisão futura de congelamento do protocolo e aprovação da partição definitiva.
- Verificação humana da proveniência/isolamento dos casos antes de qualquer avaliação confirmatória.

## Referências

- [Decisões pendentes e aprovadas](../DECISIONS-PENDING.md)
- [Pré-registro RGC](../eval/PREREGISTRATION-RGC-v1.md)
- [Protocolo RGC](../eval/PROTOCOL-GOLDEN-V1.md)
- [Revisão metodológica](../eval/METHODOLOGY-REVIEW-RGC-PTBR-2026-10-18.md)
- [Modelo de ameaças](../THREAT-MODEL.md)
- [Auditoria e rastreabilidade](09-auditoria.md)
