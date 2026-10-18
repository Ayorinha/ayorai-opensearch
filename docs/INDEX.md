# Documentação do AYORAI ATTRACTOR

Este índice organiza a documentação por objetivo. A página inicial apresenta o projeto; os documentos especializados preservam detalhes de implementação, decisões, avaliação e governança.

## Comece por aqui

1. [README do projeto](../README.md) — resumo, princípios, escopo e instalação.
2. [Guia passo a passo](GUIA-PASSO-A-PASSO.md) — instruções para preparar e executar o projeto.
3. [Status técnico](STATUS.md) — estado atual, entregas e limitações. Use este documento para informações que mudam com frequência.

## Entender a solução

- [Matriz de rastreabilidade](TRACEABILITY-MASTER.md) — relação entre requisitos, implementação e evidências.
- [Registros de decisão de arquitetura (ADRs)](adr/README.md) — decisões e justificativas técnicas.
- [Modelo de ameaças](THREAT-MODEL.md) — riscos considerados e limites de segurança.
- [Conformidade no Brasil](CONFORMIDADE-BRASIL.md) — notas de escopo regulatório; não é certificação nem parecer jurídico.

## Avaliação e reprodutibilidade

Consulte os documentos da pasta [eval](eval/) para protocolos, pré-registros, resultados, conjuntos de avaliação e referências de hashes. Ao citar números, informe sempre a versão, o conjunto usado e as limitações registradas. Golden v0 e Golden v0.1 devem ser apresentados em conjunto quando comparados.

**Limite atual:** não há resultado de benchmark em português. O protocolo RGC continua em desenvolvimento e não está congelado.

## Autoria e publicação

- [Autoria](AUTHORSHIP.md)
- [Metadados de citação](../CITATION.cff)
- [Licença Apache-2.0](../LICENSE)

## Regra editorial

- Mantenha o README curto e voltado a novos leitores.
- Registre o estado mutável em [STATUS.md](STATUS.md), não duplicado em capítulos históricos.
- Diferencie claramente o que está **implementado**, **proposto**, **em andamento** e **não implementado**.
- Não descreva hashes como prova de verdade, nem apresente testes sintéticos como validação de produção.
- Preserve protocolos, decisões aprovadas, dados congelados e evidências históricas; reorganizar a documentação não autoriza apagá-los.
