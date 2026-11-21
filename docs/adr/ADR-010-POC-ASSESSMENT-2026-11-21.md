# ADR-010 — Pesquisa e avaliação preliminar da prova de conceito

- **Data:** 2026-11-21
- **Baseline de código:** branch de experimento criada a partir da main observada em e35dce886dbdc049e56895eabc41c3777874225f
- **Status:** avaliação técnica preliminar; não fecha decisão de arquitetura
- **Decisão owner:** Anderson Leon Ayora
- **Escopo:** persistência isolada para o log Merkle; nenhuma integração com API ou Judge

## 1. Resultado da pesquisa normativa

### C2SP tlog-tiles

A especificação está na versão estável 1.0.0. Ela define a publicação de checkpoints assinados, hashes Merkle em tiles e bundles de entradas. O hashing da árvore segue RFC 6962 com SHA-256. A especificação usa recursos estáticos e endereços determinísticos, permitindo cache eficiente; o checkpoint é mutável e deve ter política de cache curta, enquanto tiles e bundles são imutáveis.

A consequência de engenharia é importante: implementar apenas uma árvore Merkle e uma API de inclusão não basta para interoperar com tlog-tiles. O writer precisa produzir a estrutura de tiles, os bundles e o checkpoint no formato especificado, com comportamento correto para tiles parciais e consistência entre tamanhos de árvore.

### C2SP tlog-checkpoint e assinaturas

O checkpoint contém origem, tamanho da árvore e raiz em Base64, em formato de signed note. A especificação define assinatura Ed25519 do log e cosignaturas Ed25519 ou ML-DSA-44; ML-DSA-44 é recomendado para cosignaturas. A escolha de custódia, rotação e recuperação de chaves continua sendo requisito operacional separado.

### Tessera

O projeto oficial descreve Tessera como uma biblioteca Go para construir logs em tiles, sucessora lógica da abordagem Trillian v1. A documentação declara suporte a drivers POSIX, AWS e GCP e classifica o projeto como geralmente disponível e pronto para produção. Tessera implementa o modelo tlog-tiles e oferece recursos de log, armazenamento e witnesses. A versão estável consultada para o experimento é v1.0.4. O upstream fornece tanto uma personalidade de conformidade POSIX com endpoint HTTP quanto a ferramenta posix-oneshot para gravar em disco local. Isso permite testar a implementação oficial sem criar um servidor próprio nesta primeira etapa.

**Correção arquitetural:** Tessera não é, em si, um microserviço HTTP genérico pronto para conectar ao FastAPI; é uma biblioteca Go. O upstream fornece personalidades de exemplo/conformidade, que podem servir como ponto de partida. Para manter a aplicação principal em Python, ainda será necessário avaliar um adaptador/processo Go com contrato de comunicação explícito ou assumir uma integração mais profunda em Go. O custo desse limite operacional precisa entrar na comparação.

### Trillian

A documentação oficial do Trillian informa que o projeto está em modo de manutenção e recomenda que novos operadores avaliem Tessera e APIs tiled. Portanto, Trillian v1 não é a opção preferencial para uma nova implementação, salvo requisito de compatibilidade que ainda não foi identificado.

## 2. Estado real do AYORAI antes deste experimento

Já existem no repositório:

- hashing RFC 6962 com SHA-256;
- geração e verificação de provas de inclusão e consistência;
- compromisso salgado com canonicalização RFC 8785;
- vetores Merkle gerados pela implementação Go de referência transparency-dev/merkle;
- testes de adulteração, truncamento, ordenação, provas malformadas e compatibilidade.

Ainda não existem como implementação de produção:

- writer persistente;
- checkpoint assinado C2SP;
- API tlog-tiles e bundles;
- custódia/rotação de chaves;
- testemunhas externas e ancoragem;
- persistência transacional e recuperação integradas ao /v1/verify;
- política completa de retenção/eliminação do registro restrito.

## 3. Prova de conceito Python — o que está sendo testado

O protótipo em experiments/adr010_poc/python_writer.py utiliza somente a biblioteca padrão do Python e a biblioteca Merkle já existente. Não adiciona dependência de runtime.

O writer recebe hashes de folhas já calculados. Ele não recebe texto de claim, evidência, corpo de requisição ou veredito. A persistência é feita em SQLite file-backed, WAL, synchronous FULL e transação BEGIN IMMEDIATE. O índice é sequencial; a chave de idempotência é única; reuso da chave com outra folha gera conflito.

A cada append, o protótipo recalcula a raiz inteira e armazena a raiz/tamanho associados ao recibo local. Isso torna a implementação fácil de inspecionar, mas O(n) por append. É intencionalmente um baseline de correção, não uma proposta de escala.

A suíte reutiliza os 17 hashes e as 18 raízes do vetor público já mantido no repositório, produzido pela implementação Go independente. Também testa reabertura do banco, idempotência, conflito, concorrência, exclusão de linha e alteração de folha contra um checkpoint guardado pelo chamador.

## 4. Limites de segurança e interpretação

O protótipo não assina checkpoints e não cria estado externo confiável. A raiz devolvida pelo processo é apenas uma estrutura local. Se um operador puder reescrever o banco e todos os recibos/checkpoints armazenados junto dele, o protótipo não detectará a reescrita. Essa limitação é consistente com a ADR-010: resistência a operador privilegiado exige recibos mantidos por clientes, testemunhas independentes ou ancoragem externa.

A chave de idempotência e a folha já comprometida são apenas dados de teste/controle do protótipo. O modelo de produção ainda precisa resolver atomicamente a geração e retenção do salt, o registro restrito, a devolução do recibo e a repetição da mesma requisição sem criar outro compromisso.

A documentação do Tessera classifica o antispam como best-effort: ele não garante supressão de todas as duplicatas. Portanto, ele não satisfaz sozinho a regra forte da ADR-010 para Idempotency-Key (mesma chave e mesma entrada → mesmo evento/recibo; mesma chave e entrada diferente → conflito). Essa semântica deverá ser imposta por uma camada transacional de personalidade/adapter do AYORAI, independentemente do antispam Tessera.

O Tessera também separa sequenciamento durável, integração à árvore e publicação do checkpoint. O futuro de Appender.Add pode devolver um índice durável antes de o item estar verificável na árvore. A ferramenta oficial posix-oneshot usa PublicationAwaiter e só conclui após o checkpoint incluir os itens; a integração do AYORAI deverá preservar esse requisito se a resposta precisar conter prova de inclusão.

Nenhum resultado desta POC deve ser descrito como log inviolável, prova de autoria, prova temporal, validação jurídica ou conformidade LGPD.

## 5. Matriz preliminar de decisão

| Critério | Writer Python | Tessera via adaptador Go |
|---|---|---|
| Linguagem/integração | Nativa no serviço Python | Fronteira adicional Python ↔ Go |
| Merkle core | Já existe no AYORAI, com vetores Go | Implementação Tessera |
| tlog-tiles | Precisaria ser implementado e validado | Parte central do projeto Tessera |
| Checkpoint assinado | Implementar/validar signed notes | Integrar os mecanismos Tessera |
| Armazenamento POSIX | Escolha e operação próprias | Driver POSIX oficial |
| Witnesses | Integrar e operar | Suporte declarado no projeto |
| Dependências de runtime Python | Potencialmente nenhuma além do conjunto atual | Processo/binário Go adicional |
| Complexidade operacional | Menos processos, mais código criptográfico/armazenamento próprio | Mais uma fronteira operacional, menos protocolo próprio |
| Evidência atual | POC SQLite isolada; sem benchmark de capacidade | Runner isolado criado para Tessera v1.0.4, usando posix-oneshot + fsck e os mesmos vetores públicos; execução CI pendente |
| Decisão | **Não decidida** | **Não decidida** |

## 6. Experimento comparativo obrigatório antes da decisão 5

O runner de Tessera em experiments/adr010_poc/run_tessera_poc.py executa o posix-oneshot v1.0.4 sobre os 17 vetores públicos, verifica o tamanho e a raiz do checkpoint contra a referência Go existente e executa Tessera fsck para validar assinatura, tiles e bundles. A suíte automatizada correspondente está em .github/workflows/adr010-poc.yml. O runner usa uma chave de demonstração publicada pelo próprio projeto Tessera, exclusivamente para o log descartável do teste; essa chave nunca pode ser usada em qualquer ambiente real.

A comparação Tessera precisa ser executada em branch e ambiente isolados, com versões e digests fixados. O protocolo mínimo:

1. usar exatamente os mesmos 17 hashes e raízes públicas;
2. usar armazenamento POSIX local e documentar filesystem, kernel, CPU, RAM e versão do Go/Python;
3. medir append individual e em lotes, p50/p95/p99, throughput, CPU, RSS e bytes persistidos;
4. testar restart limpo e recuperação após encerramento abrupto do processo;
5. testar idempotência e colisão de chave;
6. verificar provas de inclusão e consistência com o verificador independente já utilizado no CI;
7. confirmar interoperabilidade dos checkpoints e tiles com tooling independente;
8. registrar falhas, limites e operações manuais necessárias;
9. repetir os testes e publicar comandos, versões e resultados brutos.

Os 17 itens são vetores criptográficos públicos, não casos de negócio, não amostras do benchmark RGC e não estimativa de volume de produção. A medição com esse conjunto é um teste de correção/latência de pequena escala; uma avaliação de capacidade exigirá workload operacional separado e aprovado.

## 7. Recomendação técnica provisória

Não escolher Python ou Tessera apenas pela linguagem ou por alegação de maturidade. O Tessera tem vantagem clara em aderência nativa ao ecossistema tlog-tiles, armazenamento e witnesses; o Python tem vantagem de integração e reaproveitamento do core existente. A comparação só será conclusiva depois de construir o adaptador Tessera e medir ambos no mesmo ambiente.

**Decisão 5 permanece aberta ao mantenedor.** As decisões 6 (testemunhas independentes) e 7 (eventual ACT/ICP-Brasil) também permanecem abertas. Este documento não autoriza integração com /v1/verify, alteração de contrato, inclusão de dependência de runtime ou mudança do Judge.

## Fontes primárias consultadas em 2026-11-21

- C2SP, [Tiled Transparency Logs / tlog-tiles](https://c2sp.org/tlog-tiles) — versão estável 1.0.0.
- C2SP, [Transparency Log Checkpoints](https://c2sp.org/tlog-checkpoint) — formato e assinaturas de checkpoints.
- C2SP, [Transparency Log Proofs](https://c2sp.org/tlog-proof) — composição de provas offline.
- [Tessera v1.0.4 — documentação oficial](https://github.com/transparency-dev/tessera/tree/v1.0.4) — biblioteca Go, drivers, batching, publicação e witnesses.
- [Tessera POSIX one-shot](https://github.com/transparency-dev/tessera/tree/v1.0.4/cmd/examples/posix-oneshot) — exemplo oficial com PublicationAwaiter.
- [Tessera fsck](https://github.com/transparency-dev/tessera/tree/v1.0.4/cmd/fsck) — verificação de checkpoint, tiles e bundles.
- [Trillian — documentação oficial](https://github.com/google/trillian) — modo de manutenção e recomendação de avaliar Tessera.
- [RFC 6962](https://www.rfc-editor.org/rfc/rfc6962) — hashing Merkle e provas.
