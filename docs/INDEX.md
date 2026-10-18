# Documentação do AYORAI ATTRACTOR

A documentação é organizada por finalidade. Comece pelo README para entender o projeto; avance para a arquitetura, a execução ou os registros técnicos conforme sua necessidade.

## Roteiro recomendado

1. **Entender o propósito:** [README do projeto](../README.md) — problema, proposta, fluxo de verificação e limites.
2. **Entender como funciona:** [Visão geral da arquitetura](ARCHITECTURE.md) — etapas, papéis e pontos de atenção para auditoria.
3. **Executar e verificar:** [Guia passo a passo](GUIA-PASSO-A-PASSO.md) — ambiente, testes e reprodução documentada.
4. **Conferir o estado atual:** [Status técnico](STATUS.md) — entregas, verificações e limitações vigentes.
5. **Inspecionar os contratos:** [Rastreabilidade do Judge 2.0](judge2/TRACEABILITY.md) — regras e referências aos testes.

## Documentação por tema

| Tema | Documento principal | Para que serve |
|---|---|---|
| Arquitetura | [Visão geral](ARCHITECTURE.md) | Entender o fluxo e as fronteiras de responsabilidade. |
| Execução | [Guia passo a passo](GUIA-PASSO-A-PASSO.md) | Preparar o ambiente e executar verificações. |
| Estado do projeto | [Status técnico](STATUS.md) | Ver o que está concluído, em andamento ou limitado. |
| Regras do Judge | [Rastreabilidade Judge 2.0](judge2/TRACEABILITY.md) | Relacionar comportamento esperado e testes. |
| Decisões | [ADRs](adr/README.md) | Consultar decisões técnicas e suas justificativas. |
| Segurança | [Modelo de ameaças](THREAT-MODEL.md) | Entender riscos considerados, controles e exclusões. |
| Contexto brasileiro | [Conformidade no Brasil](CONFORMIDADE-BRASIL.md) | Conhecer possíveis pontos de apoio e limites regulatórios. |
| Avaliação | [Guia de execução](GUIA-PASSO-A-PASSO.md) e os artefatos de avaliação no repositório | Reproduzir resultados e consultar as limitações dos conjuntos. |
| Autoria e citação | [Autoria](AUTHORSHIP.md) · [CITATION.cff](../CITATION.cff) | Atribuir e citar o projeto corretamente. |

## Como interpretar os resultados

- Identifique sempre a versão, o commit, o conjunto de avaliação e a configuração.
- Golden v0 e Golden v0.1 são resultados históricos de desenvolvimento em dados sintéticos em inglês; não os apresente como evidência de desempenho em produção.
- **Não há resultado de benchmark em português.** O protocolo RGC está em desenvolvimento e não está congelado.
- Hashes apoiam a verificação de integridade de artefatos; não provam a veracidade de uma afirmação.
- Diferencie implementação existente, proposta, trabalho em andamento e item não implementado.

## Princípios de manutenção documental

- O README apresenta o projeto; não deve duplicar o manual técnico.
- [Status técnico](STATUS.md) é a referência para o estado atual. Relatórios históricos descrevem apenas a revisão e o commit a que se referem.
- Os documentos normativos, os contratos, os testes e os artefatos congelados prevalecem sobre resumos introdutórios.
- Não apague decisões, resultados históricos ou evidências para tornar a documentação mais curta. Simplifique a navegação e elimine duplicações, preservando a rastreabilidade.
- Toda afirmação pública sobre capacidade ou desempenho deve ter uma fonte verificável e declarar os limites relevantes.
