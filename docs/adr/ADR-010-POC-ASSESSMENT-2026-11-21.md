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

A ADR-010 também registra que C2SP tlog-proof ainda está em desenvolvimento. A maturidade de tlog-tiles 1.0.0 não deve ser confundida com a estabilidade do formato de prova de inclusão transportado ao cliente. A implementação deverá versionar o envelope de prova e exigir interoperabilidade independente antes de fixar esse contrato.

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

A suíte reutiliza os 17 hashes e as 18 raízes do vetor público já mantido no repositório, produzido pela implementação Go independente. Também testa reabertura do banco, idempotência, conflito, concorrência, exclusão de linha e alteração de folha contra um checkpoint guardado pelo chamador. Dois testes adicionais encerram um processo abruptamente: um antes do commit, para verificar rollback; outro depois do commit e antes da resposta, para verificar que o retry retorna o recibo original sem criar uma segunda entrada.

### Resultados de execução (21/11/2026)

A primeira execução detectou um defeito real em verify_receipt: para uma árvore de uma única folha, a prova de inclusão é vazia e a implementação inicial não comparava a folha persistida com a folha do recibo. A correção foi aplicada e coberta por teste de regressão.

A POC Python/Tessera foi expandida depois da validação inicial. No SHA 1b55b6620c4c59c63a465d5b4a07932db4f23f43, o workflow [ADR-010 isolated persistence POC — run 44919722764](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/44919722764) passou integralmente:

- 46 testes Python aprovados, incluindo o estado durável de idempotência, o adaptador fail-closed e a verificação/persistência de provas de inclusão;
- Ruff check aprovado;
- Tessera v1.0.4 POSIX one-shot: 17 folhas, tree size 17 e raiz SHA-256 1780178a188d10bf4aa75b1f78378e13c28db181dca036d01a2551000299be62, igual à referência dos vetores públicos;
- Tessera HTTP: cinco folhas iniciais, índices 0–4, checkpoint size 5 e raiz 4e3bbb1f7b478dcfe71fb631631519a3bca12c9aefca1612bfce4c13a86264d4;
- no mesmo servidor, a repetição imediata do primeiro corpo retornou índice 0; depois de reiniciar o processo, o mesmo corpo com a mesma Idempotency-Key foi anexado novamente no índice 5; outro corpo com a mesma Idempotency-Key foi aceito no índice 6;
- checkpoint final size 7, raiz c49c6f0c96c9e8738d63ad3c08ab337f1a775e049ef2d35de13b46e80034e2c3; assinatura, tiles e entry bundles aprovados pelo Tessera fsck.

A observação de deduplicação é consistente com o código do [servidor POSIX de conformidade do Tessera v1.0.4](https://github.com/transparency-dev/tessera/blob/v1.0.4/cmd/conformance/posix/main.go): ele instancia antispam em memória. A execução confirma que esse cache não sobrevive ao restart e que o handler de exemplo não implementa semântica de Idempotency-Key. Portanto, o antispam do exemplo não substitui um registro de idempotência durável do AYORAI.

O CI geral do SHA atual ainda está em execução. A versão anterior, sem a variante frontier, o teste HTTP e o outbox, passou no [CI geral — run 44917649782](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/44917649782): 2.616 testes aprovados e 1 ignorado em Python 3.11/3.12/3.13, cobertura 94% contra baseline 85%, além de CodeQL, Security, Dependency Review, Golden r2 Migration e contratos API. **O CI geral da extensão atual está em execução; esse resultado anterior não é apresentado como validação do SHA atual.**

**Interpretação:** a POC isolada está aprovada nos cenários exercitados. Ela demonstra a viabilidade técnica de um writer Python incremental e de uma fronteira HTTP com Tessera, além de confirmar a insuficiência do antispam em memória para idempotência durável. Não comprova capacidade de produção, resistência contra operador privilegiado, conformidade LGPD ou desempenho em escala. Nenhum benchmark de capacidade foi executado.

### Variante incremental Python — frontier Merkle

Foi adicionada uma segunda variante isolada em experiments/adr010_poc/frontier_writer.py. Ela mantém os picos da árvore RFC 6962 em uma tabela SQLite compacta. Cada append combina apenas os subárvores indicados pelos bits setados do tamanho anterior e persiste a nova fronteira na mesma transação da entrada, do tamanho e da raiz do recibo.

- Atualização de frontier por append: O(log n) hashes de nó.
- Reconstrução e validação completa no restart: O(n) folhas, comparada também com tree_root da implementação existente.
- Geração de prova de inclusão: lê o prefixo de folhas e continua O(n) no protótipo.
- A raiz atual pode ser obtida da frontier em O(log n); raízes históricas são comparadas com o root_hash_at_append persistido.
- O writer serializa append com BEGIN IMMEDIATE e mantém a chave de idempotência na mesma transação do append local.

A variante é deliberadamente separada do writer de recomputação completa, que permanece como baseline simples. Nenhuma das duas implementa checkpoint assinado, tlog-tiles, testemunhas ou integração API. O frontier local não é âncora externa; a detecção de reescrita completa continua dependendo de checkpoint guardado fora do banco.


### Outbox de idempotência durável — state machine

Foi adicionada em experiments/adr010_poc/idempotency_outbox.py uma máquina de estados SQLite para o adaptador Tessera:

- PENDING: a chave e o hash da folha comprometida foram reservados localmente antes do envio ao Tessera.
- ASSIGNED: o índice retornado pelo Tessera foi persistido localmente.
- RECORDED: um checkpoint assinado que inclui o índice foi recebido e armazenado.
- Repetir a mesma chave e o mesmo leaf hash devolve o estado/recibo existente; repetir a chave com outro leaf hash gera conflito.
- Índices Tessera são únicos entre as chaves.
- PENDING e ASSIGNED são expostos por list_unresolved(); não há reenvio automático após restart.
- record_checkpoint() permite reconciliar uma linha PENDING quando um processo externo de recuperação localiza o índice correspondente no log durável.
- RECORDED persiste o checkpoint note e a prova de inclusão; a prova RFC 6962 é verificada contra o leaf hash, o índice, o tamanho e a raiz antes do commit.
- O contrato TesseraOutboxAdapter exige um VerifiedCheckpoint cuja assinatura e origem já tenham sido verificadas pelo cliente; a camada outbox valida a prova de inclusão.

A suíte inclui encerramento abrupto depois da reserva e depois da atribuição, restart, transições repetidas, conflitos, concorrência, colisão de índice e provas inválidas. **Limite:** o scanner que localiza um append no Tessera quando o processo cai entre Add e assign ainda não foi implementado. Até a reconciliação, a solicitação permanece pendente e o serviço deve falhar fechado. O módulo não verifica a assinatura do checkpoint: exige que o cliente a valide antes de persistir o note. A chave Idempotency-Key é armazenada em texto no banco experimental; produção precisa definir proteção, HMAC/derivação, retenção e controle de acesso.



### Contrato do adaptador — reconciliação fail-closed

experiments/adr010_poc/tessera_adapter.py define a interface mínima esperada do cliente Tessera: append(), find_entries() e wait_for_checkpoint(). O submit() coordena o outbox:

1. Uma reserva nova pode executar append() uma única vez.
2. Uma linha PENDING recuperada após restart nunca chama append() cegamente; exige exatamente um índice encontrado pelo scanner durável.
3. Zero ou múltiplos resultados deixam a operação pendente e geram ReconciliationRequired.
4. Uma linha ASSIGNED apenas aguarda um checkpoint que inclua o índice.
5. Uma linha RECORDED devolve o recibo persistido, incluindo prova de inclusão, sem nova gravação.
6. A prova é validada por verify_inclusion() antes do recibo ser persistido.

Os testes usam um cliente Tessera simulado para injetar crashes em cada fronteira e verificar que o adaptador não duplica gravações. O contrato é executável e testável, mas ainda não é o cliente HTTP real: find_entries() e a obtenção de provas a partir dos tiles/bundles do Tessera permanecem trabalho pendente.


## 4. Limites de segurança e interpretação

O protótipo não assina checkpoints e não cria estado externo confiável. A raiz devolvida pelo processo é apenas uma estrutura local. Se um operador puder reescrever o banco e todos os recibos/checkpoints armazenados junto dele, o protótipo não detectará a reescrita. Essa limitação é consistente com a ADR-010: resistência a operador privilegiado exige recibos mantidos por clientes, testemunhas independentes ou ancoragem externa.

A chave de idempotência e a folha já comprometida são apenas dados de teste/controle do protótipo. O modelo de produção ainda precisa resolver atomicamente a geração e retenção do salt, o registro restrito, a devolução do recibo e a repetição da mesma requisição sem criar outro compromisso.

A documentação do Tessera classifica o antispam como best-effort: ele não garante supressão de todas as duplicatas. Portanto, ele não satisfaz sozinho a regra forte da ADR-010 para Idempotency-Key (mesma chave e mesma entrada → mesmo evento/recibo; mesma chave e entrada diferente → conflito). Essa semântica deverá ser imposta por uma camada transacional de personalidade/adapter do AYORAI, independentemente do antispam Tessera.

O Tessera também separa sequenciamento durável, integração à árvore e publicação do checkpoint. O futuro de Appender.Add pode devolver um índice durável antes de o item estar verificável na árvore. A ferramenta oficial posix-oneshot usa PublicationAwaiter e só conclui após o checkpoint incluir os itens; a integração do AYORAI deverá preservar esse requisito se a resposta precisar conter prova de inclusão.

Nenhum resultado desta POC deve ser descrito como log inviolável, prova de autoria, prova temporal, validação jurídica ou conformidade LGPD.

## 5. Janela crítica de falha: idempotência entre dois armazenamentos

Uma integração Tessera + banco do AYORAI cria dois domínios de persistência: (1) o registro transacional de Idempotency-Key, compromisso e recibo; (2) o sequenciador/armazenamento Tessera. Sem uma transação distribuída ou um protocolo de reconciliação idempotente comprovado, existe uma janela:

1. O AYORAI reserva a chave e calcula/persiste o compromisso.
2. Tessera aceita a entrada e atribui um índice durável.
3. O processo cai antes de gravar esse índice no registro de idempotência.
4. No retry, a camada externa não sabe se a entrada foi sequenciada. O antispam best-effort do Tessera não garante deduplicação.

Portanto, uma tabela de idempotência externa, por si só, ainda não demonstra exactly-once. A POC do outbox agora modela os estados PENDING, ASSIGNED e RECORDED e falha fechado quando uma linha permanece pendente; ela ainda não implementa o scanner que localiza no Tessera o append cuja resposta se perdeu. A POC Tessera precisa incluir encerramento abrupto precisamente nessa janela e provar uma estratégia de reconciliação. Alternativas a avaliar incluem uma personality que controla conjuntamente o estado de idempotência e sequenciamento, um mecanismo de busca/reconciliação por hash de compromisso ou identificador opaco de operação, ou um backend transacional integrado. Não se deve declarar o requisito satisfeito com base apenas no índice retornado pelo Add.

A POC SQLite evita essa janela porque a chave, o índice e a raiz são gravados na mesma transação local. Isso não torna SQLite uma solução de produção: a raiz é recalculada O(n), os checkpoints não são assinados e o protocolo tlog-tiles não é servido.

## 6. Matriz preliminar de decisão

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
| Evidência atual | Baseline SQLite O(n), frontier O(log n) por append e outbox PENDING/ASSIGNED/RECORDED; 37 testes dedicados aprovados | Tessera v1.0.4 POSIX one-shot + HTTP + fsck; antispam em memória não sobrevive ao restart |
| Decisão | **Não decidida** | **Não decidida** |

## 7. Experimento comparativo obrigatório antes da decisão 5

O runner de Tessera em experiments/adr010_poc/run_tessera_poc.py executa o posix-oneshot v1.0.4 sobre os 17 vetores públicos, verifica o tamanho e a raiz do checkpoint contra a referência Go existente e executa Tessera fsck para validar assinatura, tiles e bundles. Isso é uma verificação de integridade do log inteiro; ainda não testa o formato de uma prova individual de inclusão nem o recibo entregue ao cliente. A suíte automatizada correspondente está em .github/workflows/adr010-poc.yml. O runner gera uma chave Ed25519 descartável com OpenSSL em tempo de execução; a chave privada não é versionada e é apagada junto com o diretório temporário.

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

## 8. Recomendação técnica provisória

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
