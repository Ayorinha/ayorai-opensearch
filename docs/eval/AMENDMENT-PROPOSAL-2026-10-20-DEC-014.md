# Proposta de emenda datada — DEC-014 (20/10/2026)

**Estado:** proposta documental pendente de aprovação explícita do mantenedor.  
**Efeito imediato:** nenhum. Este arquivo não altera nem substitui o pré-registro vigente e não autoriza congelamento do protocolo, anotação definitiva ou execução confirmatória.

## Motivo

Registrar de forma auditável a definição da baseline primária e evitar que uma alteração metodológica seja interpretada como autorização para executar o benchmark.

## Texto proposto

1. **Baseline B é a comparação primária de H1.** Será calculada exclusivamente a partir dos rótulos humanos da partição pública de desenvolvimento de 70%, com IDs, contagens, correspondências, proveniência e hashes registrados. Seu rótulo majoritário e os artefatos usados serão congelados antes da avaliação confirmatória.
2. **Baseline A é apenas descritiva/oráculo.** Por ser calculada com os rótulos da própria partição avaliada, será apresentada somente como referência descritiva da prevalência observada. Não poderá ser usada para seleção, ajuste, decisão de H1 ou alegação de desempenho operacional.
3. **Critérios primários de H1** serão avaliados exclusivamente contra a baseline B: acurácia pelo menos 10 pontos percentuais acima de B; limite inferior do IC95% da acurácia acima da acurácia pontual de B; e teste exato bilateral de McNemar com p < 0,05, nos mesmos casos.
4. **Nenhuma execução fica autorizada por esta proposta.** Permanecem obrigatórios o segundo piloto humano isolado, a revisão documentada pós-piloto, a aprovação explícita e o congelamento formal do protocolo, a anotação definitiva, a separação dos conjuntos e todos os demais portões descritos no pré-registro.
5. Se aprovada, a emenda deverá ser incorporada ao registro metodológico por procedimento datado e auditável, preservando a redação anterior e o histórico; não se deve sobrescrever silenciosamente o histórico de decisões.

## Salvaguardas

- O piloto é humano: não usar IA para criar casos ou rótulos e não executar o ATTRACTOR nos casos do piloto.
- Não inventar casos, forçar categorias ou publicar casos ocultos.
- `RULE_GAP` permanece marcador exploratório exclusivo do piloto; não é veredito do Judge e não entra em métricas nem em concordância.
- Nenhum resultado do benchmark RGC PT-BR é reivindicado até que a avaliação válida seja efetivamente concluída.
- Este documento não declara parceria, apoio, endosso ou validação da Anatel ou de universidade.

## Decisão do mantenedor

- [ ] Aprovada explicitamente por Anderson Leon Ayora
- [ ] Rejeitada
- [ ] Solicita alterações

**Data da decisão:** pendente.  
**Responsável pela decisão:** Anderson Leon Ayora.
