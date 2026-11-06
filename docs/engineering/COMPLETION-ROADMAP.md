# AYORAI ATTRACTOR — Plano de conclusão da engenharia de software

- **Baseline auditada:** `main` em `0b2d92f4a55cfe3090d2affba2d86c17221ff6ed` (06/11/2026).
- **Escopo:** maturidade do software, excluindo a conclusão científica do benchmark RGC PT-BR.
- **Status:** plano de execução; nenhum item é declarado concluído apenas por estar listado.
- **Governança:** cada etapa será implementada em PR isolada, com diff revisado e CI no SHA exato. Nenhum merge, tag, release, DOI, alteração de Judge/Golden ou mudança de protocolo ocorre sem autorização explícita do mantenedor.

## Objetivo

Concluir o escopo de engenharia necessário para uma versão profissional, segura, eficiente, observável e verificável do AYORAI ATTRACTOR. “100%” significa cumprir os critérios de aceitação acordados para esse escopo, não ausência de manutenção ou evolução futura.

## Estado de partida verificado

- A versão publicada registrada no repositório é a v0.6.0.
- O projeto já possui API FastAPI, modelos Pydantic, autenticação, testes automatizados, workflows de CI, segurança, CodeQL, análise de dependências, Docker e instrumentação de observabilidade.
- A biblioteca `auditlog` contém hashing Merkle, compromissos e vetores de referência; a ADR-010 ainda descreve lacunas de serviço persistente, integração com `/v1/verify`, checkpoints, custódia de chaves, testemunhas externas, recuperação e medição operacional.
- A documentação de proveniência registra hashes de distribuição verificados para v0.6.0, mas lista SBOM, proveniência SLSA, assinaturas e provas temporais como controles futuros.
- `docs/STATUS.md` contém snapshots históricos e declara como referência uma data anterior à baseline atual; deve ser atualizado em uma tarefa documental própria, sem apagar o histórico.
- A ADR-010 mantém abertas as decisões de arquitetura sobre writer Python versus Tessera, testemunhas independentes e eventual carimbo de tempo ICP-Brasil.

## Princípios e limites

1. O Judge determinístico continua sendo a única autoridade dos vereditos.
2. Não alterar Judge, Golden, manifests, hashes congelados, regras protegidas ou contratos públicos sem revisão e autorização específicas.
3. Não criar casos, rótulos, partições ou resultados de benchmark artificiais ou reais.
4. Não executar o ATTRACTOR sobre os 11 casos do Piloto 02 nem sobre dados de avaliação RGC.
5. Não usar dados sintéticos para simular casos de negócio ou resultados do benchmark. Para validar primitivas criptográficas, priorizar vetores públicos padronizados já existentes e verificadores independentes; qualquer necessidade de novos dados de teste deve ser explicitamente justificada e aprovada.
6. Não declarar segurança, conformidade LGPD, desempenho, reprodutibilidade ou maturidade sem evidência verificável.
7. Preservar autoria e créditos do projeto conforme os metadados oficiais do mantenedor; não introduzir atribuições de autoria a ferramentas.
8. Não mesclar PRs, publicar releases, criar tags ou DOIs sem autorização explícita.

## Sequência de execução

### E0 — Baseline e inventário técnico
- Mapear módulos, pontos de entrada, dependências, workflows, contratos e PRs abertas.
- Relacionar cada requisito a arquivos, testes e evidências atuais.
- Identificar conflitos ou sobreposição com PRs já abertas antes de iniciar uma implementação.
- Produzir matriz: implementado, parcial, ausente, não verificável e bloqueado por decisão humana.

**Aceitação:** inventário ligado ao SHA auditado; nenhuma afirmação baseada apenas em snapshots históricos; nenhuma alteração funcional.

### E1 — Confiabilidade e contratos
- Revisar tratamento de exceções, timeouts, cancelamento, concorrência, idempotência e recuperação.
- Verificar contratos API/OpenAPI, limites de entrada, compatibilidade e comportamento de falha.
- Reexecutar os workflows existentes no head de cada PR de mudança.
- Corrigir somente defeitos reproduzíveis e fora dos artefatos protegidos.

**Aceitação:** critérios de falha explícitos, regressões cobertas pelos testes apropriados já existentes e CI verde no SHA exato.

### E2 — Segurança operacional
- Revisar autenticação, ciclo de vida/revogação de API keys, autorização, isolamento entre tenants, limites de payload, logs e exposição de dados.
- Conferir dependências e imagens de contêiner; fixar versões/digests quando justificável.
- Revisar threat model, segredos, permissões mínimas, retenção e resposta a incidentes.
- Separar achados confirmados de recomendações e riscos residuais.

**Aceitação:** matriz de ameaças e controles, evidência dos testes de segurança e registro explícito dos riscos não eliminados.

### E3 — Auditoria verificável (ADR-010)
- Fechar primeiro as decisões de arquitetura ainda abertas por meio de comparação documentada e prova de conceito isolada.
- Especificar esquema versionado de evento, canonicalização, compromisso salgado, recibo, prova de inclusão, checkpoint e política de retenção/eliminação.
- Implementar persistência atômica, idempotência, concorrência, reinício, backup, restore e recuperação.
- Verificar provas com implementação independente e vetores públicos padronizados.
- Definir custódia de chaves e mecanismo de testemunho/ancoragem antes de alegar resistência contra operador privilegiado.
- Integrar com `/v1/verify` somente após aditivo de contrato e aprovação do mantenedor.

**Aceitação:** todos os critérios aplicáveis da ADR-010 demonstrados; limites de confiança e de privacidade documentados; latência e armazenamento medidos em ambiente descrito; nenhuma alegação de imutabilidade absoluta.

### E4 — Distribuição e cadeia de suprimentos
- Gerar SBOM para os artefatos efetivamente distribuídos.
- Adicionar proveniência de build verificável e vinculada ao commit e aos hashes dos artefatos.
- Avaliar assinatura de artefatos e verificação independente.
- Documentar retenção, reprodução do build e procedimento de release.

**Aceitação:** um terceiro consegue relacionar commit, workflow, artefatos, hashes, SBOM e atestado; controles não implementados permanecem identificados como pendentes.

### E5 — Desempenho e eficiência
- Definir workloads e métricas operacionais sem utilizar casos RGC.
- Medir latência, throughput, memória, CPU, chamadas a modelos/provedores e custo por execução.
- Identificar gargalos antes de otimizar; preservar semântica e autoridade do Judge.
- Adotar cache, paralelismo ou modelos alternativos somente com justificativa, limites e regressões de contrato.

**Aceitação:** relatório reproduzível com ambiente, método, baseline, resultados e trade-offs; nenhuma melhoria declarada sem medição.

### E6 — Observabilidade e operação
- Consolidar logs estruturados, métricas, traces, correlation IDs e redaction.
- Definir health/readiness, alertas, SLOs internos, runbooks, backup e recuperação.
- Verificar que telemetria não vaza prompts, documentos, credenciais ou dados pessoais.

**Aceitação:** procedimento operacional testável e telemetria com minimização de dados documentada.

### E7 — Documentação e prontidão de versão
- Atualizar documentação de arquitetura, instalação, configuração, segurança, operação, limitações e proveniência.
- Atualizar `docs/STATUS.md` com SHA e evidências atuais, preservando snapshots históricos.
- Preparar checklist de release, sem publicar versão.

**Aceitação:** documentação corresponde ao comportamento efetivamente implementado e todos os gates de engenharia têm evidência rastreável.

## Critério de conclusão do escopo de software

O software será considerado concluído para o escopo acordado somente quando E0–E7 estiverem avaliadas e todos os critérios aplicáveis estiverem satisfeitos ou formalmente aceitos como risco residual pelo mantenedor. Itens dependentes de decisão, fornecedor, infraestrutura ou validação externa não serão marcados como concluídos por inferência.

O benchmark RGC PT-BR permanece uma trilha independente e pendente: anotações humanas, segunda anotação independente, adjudicação, revisão metodológica e autorização de congelamento/avaliação não fazem parte do percentual de conclusão da engenharia.

## Registro de execução

Cada etapa deve registrar: SHA de base, branch/PR, arquivos alterados, motivo, riscos, testes executados, links dos workflows, SHA testado, resultado, limitações e decisão pendente. Não reutilizar evidência de um SHA anterior como prova do head atual.
