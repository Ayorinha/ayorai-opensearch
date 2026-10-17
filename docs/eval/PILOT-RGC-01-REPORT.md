# Relatório do piloto exploratório RGC PT-BR 01

**Status: registro histórico de piloto exploratório — descartado; não é benchmark**  
**Data do piloto:** 2026-10-16  
**Anotador:** Anderson Leon Ayora  
**Redação dos casos:** os 20 casos (afirmação e trechos) foram gerados com auxílio de uma ferramenta automatizada de geração de texto, a partir das fontes oficiais registradas em `evals/ptbr/sources/`; o anotador apenas atribuiu rótulos e justificativas. O piloto era exploratório e foi descartado conforme previsto no protocolo; a redação automatizada dos casos está entre as limitações registradas abaixo.  
**Identificação do arquivo de casos:** SHA-256 `3cbbed018f241d6fdc1d83717aec5248e37811b9afc7e2badf17b4fcbd24065c` (o arquivo não integra o repositório; o hash é registrado para rastreabilidade).  
**Escopo:** piloto exploratório de anotação; não é avaliação do sistema.

## Objetivo

Verificar, em caráter exploratório, como as regras de anotação do protocolo Golden v1 em português brasileiro se comportam antes do congelamento do protocolo e da preparação do conjunto definitivo. O piloto foi usado para identificar ambiguidades no guia, não para estimar o desempenho do AYORAI ATTRACTOR.

## Distribuição agregada

Foram anotados 20 casos. A distribuição agregada foi:

| Rótulo | Quantidade |
| --- | ---: |
| SUPPORTED | 9 |
| REFUTED | 11 |
| UNVERIFIED | 0 |
| PARTIALLY_SUPPORTED | 0 |
| CONFLICTING | 0 |
| RULE_GAP | 0 |
| **Total** | **20** |

O piloto não continha casos projetados para exercitar os rótulos PARTIALLY_SUPPORTED ou CONFLICTING. A distribuição observada não deve ser interpretada como representativa de um conjunto definitivo.

## Achados encaminhados à DEC-011

Os achados históricos foram discutidos na [PR #206](https://github.com/Ayorinha/ayorai-opensearch/pull/206), e a escolha para a Parte 2 foi registrada na [PR #207](https://github.com/Ayorinha/ayorai-opensearch/pull/207). A decisão consolidada foi aprovada na DEC-011 e documentada na [PR #227](https://github.com/Ayorinha/ayorai-opensearch/pull/227). Este relatório não reproduz afirmações, trechos de fontes, justificativas ou rótulos individuais.

1. **Confirmação versus contradição — pilot-18 (Parte 1):** a regra foi aprovada na DEC-011 e incorporada à Emenda 4: ausência de evidência = `UNVERIFIED`; `REFUTED` exige contradição explícita e citação da frase incompatível.
2. **Texto retificado — pilot-19 (Parte 2):** Anderson aprovou a opção A em 2026-10-17. A Emenda 4 determina considerar o texto vigente após retificações, ignorar redação superada, marcar `rectified: true` e reportar esse estrato separadamente, sem alterar o Judge.
3. **Valores, quantificadores e modalidade — pilot-04 e pilot-12 (Parte 3):** Anderson aprovou a tabela de regras e decidiu excluir do v1 afirmações que transformem “preferencialmente” em obrigação sem suporte textual explícito. A decisão não autoriza inferências jurídicas pelo anotador.

## Limitações e transparência

- Houve um único anotador: Anderson. Não houve anotação independente por segunda pessoa nem cálculo de Cohen's kappa.
- Os casos foram gerados com auxílio de uma ferramenta automatizada de geração de texto, e não redigidos pelo anotador. No conjunto definitivo, a redação cabe ao mantenedor (DEC-008); portanto, o piloto não testou a etapa de redação humana dos casos.
- Não havia casos projetados para PARTIALLY_SUPPORTED ou CONFLICTING; portanto, o piloto não testou adequadamente esses cenários.
- O mantenedor confirmou que a justificativa de pilot-04 teve auxílio de IA.
- Depois da rotulagem, os textos do piloto foram consultados em assistentes externos. Esse fato deve ser considerado ao avaliar a independência do processo e a aderência às regras de isolamento.
- A DEC-011 foi aprovada em 2026-10-17 e suas regras foram registradas na Emenda 4. O segundo piloto humano ainda é necessário para verificar ambiguidades remanescentes; a aprovação da decisão não equivale a congelamento do protocolo.
- Os resultados e rótulos individuais do piloto são descartados e não foram incorporados ao repositório.

## Relação com a avaliação do sistema

**O sistema AYORAI ATTRACTOR não foi executado sobre os casos do piloto.** O piloto foi exclusivamente exploratório e serviu para encontrar problemas nas regras de anotação. A distribuição apresentada acima descreve somente os rótulos produzidos pelo anotador durante esse exercício; não mede, compara nem demonstra o desempenho do sistema.

**Não existe resultado de benchmark em português.** Nenhuma métrica de desempenho do sistema pode ser inferida deste piloto.

## Próximos passos

1. Executar um segundo piloto exploratório de aproximadamente 10 casos novos, sem consulta a assistentes/modelos de IA, com fontes oficiais verificadas e anotação humana.
2. Descartar os casos do piloto; não executar o sistema sobre eles nem incorporá-los ao conjunto definitivo.
3. Revisar os achados e documentar ambiguidades ou ajustes necessários.
4. Solicitar aprovação explícita para congelar o protocolo; só depois iniciar a redação dos 300 casos definitivos.
5. Obter uma segunda anotação independente e exigir Cohen's kappa >= 0,6.
6. Somente depois dos gates anteriores, executar o sistema uma única vez sobre o conjunto congelado e completamente rotulado.
