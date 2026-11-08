# Documentação do AYORAI ATTRACTOR

Este índice organiza a documentação por finalidade e identifica a fonte adequada para cada tipo de consulta. Comece pelo README para uma visão geral; use o Status técnico para o estado corrente e os documentos normativos, relatórios e registros de decisão para detalhes verificáveis.

## Roteiro recomendado

1. **Conhecer o projeto:** [README](../README.md) — objetivo, arquitetura em alto nível, resultados publicados e limites.
2. **Entender a arquitetura:** [Visão geral da arquitetura](ARCHITECTURE.md) e [Manual Técnico](manual/README.md) — visão conceitual e especificações técnicas.
3. **Consultar o estado vigente:** [Status técnico](STATUS.md) — referência principal para entregas, pendências e limitações.
4. **Executar verificações:** [Guia passo a passo](GUIA-PASSO-A-PASSO.md) — preparação do ambiente e comandos documentados; confirme sempre a versão e o commit aplicáveis.
5. **Entender o Judge 2.0:** [Rastreabilidade do Judge](judge2/TRACEABILITY.md) — relação entre regras, contratos e testes.
6. **Consultar resultados:** relatórios e proveniência em [reports/benchmarks](../reports/benchmarks/), sempre respeitando partição, protocolo, SHA e limitações.
7. **Citar o projeto:** [Autoria](AUTHORSHIP.md) e [CITATION.cff](../CITATION.cff).

## Documentação por finalidade

| Finalidade | Documento principal | Uso |
|---|---|---|
| Visão institucional | [README](../README.md) | Apresentação pública do projeto e seus limites. |
| Arquitetura | [Visão geral](ARCHITECTURE.md) · [Manual Técnico](manual/README.md) | Conceitos, componentes e contratos técnicos. |
| Execução | [Guia passo a passo](GUIA-PASSO-A-PASSO.md) | Preparar ambiente e reproduzir verificações documentadas. |
| Estado do projeto | [Status técnico](STATUS.md) | Consultar o estado corrente; snapshots históricos não substituem este arquivo. |
| Judge 2.0 | [Rastreabilidade](judge2/TRACEABILITY.md) | Regras, contratos, referências e testes do Judge. |
| Decisões | [Decisões aprovadas](DECISIONS-APPROVED.md) · [Decisões pendentes](DECISIONS-PENDING.md) · [ADRs](adr/README.md) | Distinguir decisões aprovadas, pendentes e registros arquiteturais. |
| Segurança | [Modelo de ameaças](THREAT-MODEL.md) | Controles, riscos e exclusões documentados. |
| Proveniência | [Modelo de proveniência](PROVENANCE-MODEL.md) · [Rastreabilidade](TRACEABILITY-MASTER.md) | Origem de dados, evidências e relações documentadas. |
| Avaliação e benchmarks | [Pré-registro Calibration V2](benchmarks/CALIBRATION-V2-PREREGISTRATION.md) · [Datasets](benchmarks/DATASETS.md) · [Radar tecnológico](benchmarks/RADAR-TECNOLOGICO-2026-11.md) | Protocolos, conjuntos, proveniência e riscos; verificar sempre o status de cada documento. |
| Resultados | [Relatório DEV Calibration V2](../reports/benchmarks/2026-11-07-dev-calibration-v2/README.md) · [Reagregação Amendment 2 exploratória](../reports/benchmarks/2026-11-08-phase1b-amendment-2-exploratory/README.md) · [Proveniência Calibration V2](../reports/benchmarks/2026-11-07-dev-calibration-v2/PROVENANCE.md) | Resultados DEV e análise pós-hoc; não equivalem a TEST, produção ou certificação confirmatória. |
| Contexto brasileiro | [Conformidade Brasil](CONFORMIDADE-BRASIL.md) | Referências legais e limites de interpretação; não substitui parecer jurídico. |
| Anotação e avaliação humana | [Documentação de anotação](annotation/) · [Piloto RGC](eval/PILOT-RGC-02-OPERATIONS.md) | Materiais metodológicos e operacionais; não significam autorização para executar ou congelar protocolo. |
| Documento técnico institucional | [Documento técnico público v1.1 (PDF)](institutional/AYORAI-ATTRACTOR-Documento-Tecnico-v1.1.pdf) | Apresentação técnica consolidada; confira o Status para informações correntes. |
| Autoria e citação | [Autoria](AUTHORSHIP.md) · [CITATION.cff](../CITATION.cff) | Atribuição e referência bibliográfica. |

## Como interpretar a documentação e os resultados

- Identifique a versão, o commit, o conjunto de avaliação, a configuração e a data de cada evidência.
- Diferencie resultado DEV, resultado TEST, experimento exploratório, proposta, pré-registro e decisão aprovada.
- A reaggregação Amendment 2 é exploratória e pós-hoc; não substitui o resultado oficial da v0.7.0 pela regra original.
- Golden v0 e Golden v0.1 são referências históricas de desenvolvimento com dados sintéticos em inglês; não são evidência de desempenho em produção.
- Não há resultado de benchmark em português. O protocolo RGC permanece proposto e não congelado.
- Hashes verificam integridade de artefatos, não a veracidade de seu conteúdo.
- A existência de uma proposta ou workflow em arquivo não significa que esteja ativo, aprovado ou autorizado para execução.

## Candidatos a consolidação ou arquivamento — nenhuma movimentação autorizada

A lista abaixo é apenas uma proposta para revisão futura. **Nenhum arquivo foi movido, renomeado ou excluído por esta PR.** Antes de qualquer arquivamento, conferir referências internas, dependências de documentação, links públicos e histórico de decisões.

| Candidato | Motivo para revisão | Tratamento sugerido, sujeito a aprovação |
|---|---|---|
| [PROGRESS.md](PROGRESS.md) | O próprio documento declara que preserva narrativa histórica e remete ao [STATUS.md](STATUS.md) como fonte corrente; há risco de duplicação de estado e referências de releases antigas. | Avaliar consolidação de referências históricas em [history/](history/) e manter um aviso/link para STATUS, sem apagar conteúdo probatório. |
| [MILESTONES.md](MILESTONES.md) | Também se define como índice histórico e remete ao STATUS; pode sobrepor-se ao registro de progresso e à rastreabilidade. | Avaliar consolidação com PROGRESS ou conversão em índice histórico; preservar decisões, referências e datas. |
| [architecture.md](architecture.md) | É um resumo técnico de navegação que aponta para o capítulo 02 do Manual Técnico, enquanto [ARCHITECTURE.md](ARCHITECTURE.md) cobre a visão geral conceitual. | Revisar sobreposição e finalidade; se houver consolidação, preservar os fatos de implementação e redirecionar referências antes de arquivar. |
| [EXPERIMENTAL-MODULES.md](EXPERIMENTAL-MODULES.md) | Lista um subconjunto de módulos experimentais e declara que não é inventário completo; o Manual Técnico também documenta limites de integração. | Verificar se continua sendo a fonte operacional apropriada ou se deve ser incorporado ao manual, sem perder ressalvas de segurança e compatibilidade. |

### Documentos que devem permanecer preservados nesta etapa

- Relatórios, manifests, hashes e evidências históricas em `reports/` e referências publicadas em DOI.
- Pré-registros, emendas, protocolos, decisões aprovadas e registros de auditoria em `docs/eval/`, `docs/benchmarks/` e `docs/adr/`.
- Snapshots históricos em `docs/history/`.
- Propostas de workflow e documentos explicitamente marcados como proposta, até decisão formal sobre sua substituição.

## Princípios de manutenção documental

- O README apresenta o projeto; o Status técnico é a referência para o estado corrente.
- Relatórios históricos descrevem somente o SHA, os dados e o protocolo que efetivamente auditaram.
- Documentos normativos, contratos, testes e artefatos congelados prevalecem sobre resumos introdutórios.
- Simplifique a navegação sem apagar decisões, resultados históricos ou evidências.
- Toda afirmação pública sobre capacidade, desempenho ou conformidade deve ter fonte verificável e limites explícitos.
