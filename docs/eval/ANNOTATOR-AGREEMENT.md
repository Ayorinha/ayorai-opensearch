# Guia de cálculo de concordância entre anotadores (DEC-020)

## Objetivo e limites

Este guia descreve a ferramenta reprodutível para calcular a concordância entre duas anotações humanas independentes. A ferramenta não anota casos, não adjudica divergências, não executa o ATTRACTOR e não autoriza promover o conjunto para a versão definitiva. O protocolo geral continua **[PROPOSTO]**.

## Formato de entrada

Cada arquivo é JSONL, uma linha por caso, com exatamente estes campos operacionais:

```json
{"case_id":"ID_DO_CASO","label":"SUPPORTED"}
```

Valores permitidos de `label`: `SUPPORTED`, `REFUTED`, `UNVERIFIED`, `PARTIALLY_SUPPORTED`, `CONFLICTING` e o marcador piloto `RULE_GAP`. O marcador não é um sexto rótulo para kappa. Não incluir nomes, e-mails ou outros dados pessoais nos arquivos de anotação.

Os dois arquivos devem conter exatamente o mesmo conjunto de `case_id`, sem duplicatas e sem rótulos ausentes/desconhecidos. Divergências de integridade interrompem o cálculo.

## Regra de concordância aprovada

- Cohen's kappa não ponderado para as cinco categorias nominais definitivas.
- Gate pela estimativa pontual `κ ≥ 0,6`.
- Reportar IC95% percentil por bootstrap de casos, 10.000 reamostragens, seed `20261003`; o limite inferior não é um gate.
- Reportar concordância observada, matriz de confusão e marginais por classe.
- Se qualquer anotador usar `RULE_GAP`, excluir o par do kappa e reportar a exclusão e suas discordâncias separadamente.
- Se o kappa for indefinido por ausência de variação, o gate não é aprovado.

## Execução

Após a segunda anotação humana independente estar concluída e os arquivos serem revisados:

```bash
python evals/ptbr/rgc_agreement.py \
  --annotation-a <anotacao-1.jsonl> \
  --annotation-b <anotacao-2.jsonl> \
  --out <relatorio-concordancia.json>
```

A saída é um relatório de concordância, não uma métrica do ATTRACTOR nem um resultado de benchmark. Não executar com rótulos fictícios para simular concordância humana; testes automatizados usam apenas dados sintéticos em memória.

## Pendências humanas

- Uma pessoa distinta deve realizar a segunda anotação sem visualizar os rótulos iniciais.
- Anderson e a segunda pessoa devem revisar e registrar as divergências caso a caso.
- A revisão humana independente F-01 permanece pendente.
