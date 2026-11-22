# P2 — Relatório de conclusão técnica (trilha verificável, ADR-010)

| item | valor |
|---|---|
| Data | 2026-11-22 |
| PR | #634 (draft), branch `p2-auditlog-review` |
| Base | `main` em `76876bb70abcffe488176bb9b3b324942227aaad` |
| SHA de partida | `9e957cd5fc8fdd9a8a6565f02350f49c974b6255` |
| SHA final | ver seção 13 |

Rótulos: **[FATO VERIFICADO]** foi executado ou lido e tem evidência citada. **[INFERÊNCIA]** é uma conclusão tirada desses fatos. **[HIPÓTESE]** não foi verificada.

## 1. Resumo executivo

- **[FATO VERIFICADO] M1 corrigido.**
  - `verify_log()` passa a auditar a tabela de idempotência.
  - O reenvio só devolve o recibo guardado se ele ainda abre o próprio evento.
  - O ataque original (recibo de outro evento guardado sob a chave) é detectado em 20 de 20 instâncias. Antes da correção, 0 de 20.
  - O reenvio não devolve mais o recibo de outro evento.
- **[FATO VERIFICADO] M2, encontrado nesta etapa, também corrigido.**
  - O apagamento LGPD deixava o registro e o sal dentro do recibo de idempotência, e um reenvio os devolvia.
  - Agora o recibo é substituído por uma versão redigida, e o reenvio recebe 409.
- **[FATO VERIFICADO] B1, B2 e B3:** cada um tem testes específicos, todos aprovados.
- **[FATO VERIFICADO] Torchwood:** a testemunha de referência torchwood v0.10.0 foi executada de verdade, em TLS local. **14 de 14 checagens** passaram com o cliente final.
  - O mesmo roteiro, rodado com o cliente original da PR, falha já no primeiro envio: a testemunha responde HTTP 400. Isso confirma o defeito do formato `old <tamanho>`.
- **[FATO VERIFICADO] Golden e Judge intactos:**
  - hashes semânticos do Golden idênticos;
  - árvores protegidas idênticas às da `main`;
  - Judge Regression aprovado.
- **[INFERÊNCIA] Fora do escopo do código:** uma limitação de projeto continua e depende de decisão do mantenedor. O vínculo chave → evento não é ancorado na árvore assinada (seção 12).

## 2. Estado inicial

**[FATO VERIFICADO]**
- **Ponto de partida:** branch local e `origin/p2-auditlog-review` em `9e957cd5`, árvore limpa, PR #634 em draft.
- **Revisão independente (`P2-INDEPENDENT-REVIEW.md`), veredito "aprovada com ressalvas":**
  - M1 (média, preexistente): recibos de idempotência não auditados;
  - B1 a B3 (baixa): lacunas de teste nos limites de 63 nós, no 409 com tamanho 0 e na sequência inicial de checkpoints;
  - interoperabilidade real não executada, porque o controle de permissões bloqueou a execução.
- **Reprodução de M1** (`idem_gap.py`):
  - a linha da chave `k-0` passa a guardar o recibo do evento 1;
  - `verify_log()` responde `valid=True`;
  - o reenvio devolve o evento 1 (`SUPPORTED`), embora a requisição original seja `REFUTED`;
  - `verify_receipt` aceita esse recibo.
- **Reprodução de M2** (feita nesta etapa):
  - depois de `erase(0)`, a linha de idempotência ainda guarda o recibo com o registro (`verdict`, `client`) e o sal;
  - `verify_log()` responde válido;
  - o reenvio devolve o registro apagado.

## 3. Correção M1 (e M2)

**Causa raiz [FATO VERIFICADO]:**
- `vlog_idempotency(key_digest, input_sha256, idx, receipt)` fica fora da árvore assinada.
- O reenvio confiava no JSON guardado.
- `verify_log()` não lia essa tabela.
- `erase()` não a alterava.
- A assinatura do recibo prova que ele vem do log, mas não que é o recibo daquela requisição.

**Correção** (`src/ayorai_attractor/auditlog/store.py`), um único verificador `_idempotency_problems(idx, input_sha256, receipt)` usado em dois lugares:

1. **No reenvio, antes de devolver qualquer coisa:**
   - se a entrada difere, continua `IdempotencyConflict` (409);
   - se o recibo não abre o próprio evento, `LogCorruption`: no modo `required`, 503 sem veredito; no `local`, `not_recorded` sem recibo;
   - se o evento foi apagado, `IdempotencyErased`, subclasse de `IdempotencyConflict`, e portanto 409, sem mudar o contrato OpenAPI.
2. **Em `verify_log()`, para cada linha da tabela.** O verificador exige que:
   - `key_digest` seja um SHA-256 hexadecimal;
   - nenhum evento seja nomeado por duas chaves;
   - `idx` seja inteiro e aponte para uma folha de evento existente;
   - para um evento vivo:
     - `receipt.index == idx`;
     - a folha do recibo seja byte a byte a folha guardada;
     - `verify_receipt` passe (assinatura do checkpoint, inclusão e compromisso com o sal);
     - `record.input_sha256` seja igual à entrada da linha;
   - para um evento apagado, o recibo tenha exatamente `{"redacted": true, "index": idx, "erasure_index": n}` e `n` seja a folha de apagamento desse evento. Recibo completo de evento apagado é problema.
3. **`erase()`** troca o recibo pela forma redigida na mesma transação que apaga o registro e acrescenta a folha de apagamento.

A correção não se apoia só na assinatura: a folha, o índice e a entrada são comparados com o armazenamento, e o compromisso é reaberto.

**Testes** (`tests/test_verify_log_idempotency.py`, 47 casos; mais 2 de HTTP em `tests/test_verify_log.py`) **[FATO VERIFICADO]**:

| # | caso pedido | teste | resultado |
|---|---|---|---|
| 1 | troca de recibo entre eventos | `test_m1_01_*` | detectado; reenvio recusado (`LogCorruption`) |
| 2 | troca entre requisições | `test_m1_02_*` | linhas inteiras trocadas: `verify_log()` **não** detecta (limitação, seção 12); o reenvio é recusado com 409, nunca devolve o recibo alheio |
| 3 | recibo para evento inexistente | `test_m1_03_*`, `test_m1_03b_*` | detectado (`idx` 99 e -1; `index` do recibo 99) |
| 4 | linha sem recibo | `test_m1_04_*`, `test_m1_04b_*` | vazio, não-JSON, `[]`, `null` e `{}` detectados; `NULL` recusado pelo esquema |
| 5 | recibo sem linha | `test_m1_05_*` | não se aplica por desenho: a chave é opcional e a árvore não a registra. Linha apagada não é detectável e o reenvio grava o evento de novo (seção 12) |
| 6 | identificador da requisição alterado | `test_m1_06_*`, `test_m1_06b_*` | detectado; reenvio recusado com 409 |
| 7 | identificador do evento alterado | `test_m1_07_*` (3 variantes) | detectado (índice, folha e duplicidade) |
| 8 | compromisso divergente | `test_m1_08_*` (veredito, cliente, sal, entrada) | detectado |
| 9 | duplicidade | `test_m1_09_*`, `09b`, `09c` | duas chaves para um evento e digest malformado detectados; chave repetida recusada pelo esquema |
| 10 | reenvio após adulteração | `test_m1_10_*` | três reenvios recusados, árvore inalterada, e recuperação quando o recibo é restaurado |
| 11 | reabertura e verificação offline | `test_m1_11_*` | recibo verificável só com a chave pública; adulteração com o log fechado é detectada na reabertura |
| 12 | banco adulterado diretamente | `test_m1_12_*`, `12b` | recibo forjado com outra chave detectado; as outras chaves continuam funcionando |
| M2 | apagamento | `test_m2_*` (10 casos) | recibo redigido, sem sal nem registro; reenvio com 409; recibo completo restaurado, redação forjada e redação de evento não apagado detectados; persiste na reabertura |
| — | linhas e folhas malformadas | 4 testes | índice não inteiro, folha de apagamento, folha não-JSON |
| HTTP | `test_idempotent_retry_*` | 2 testes | 409 para evento apagado; recibo adulterado nunca servido (503 no `required`, `not_recorded` no `local`) |

**Benchmark de adulteração** (20 instâncias por classe, logs com chave em todo evento, semente fixa) **[FATO VERIFICADO]**:

| classe | `main` | P2 antes (`9e957cd5`) | P2 final |
|---|---|---|---|
| logs íntegros sem falso alarme | 60/60 | 60/60 | **60/60** |
| T01–T13 (armazenamento, já medidos na revisão) | 7 de 13 classes | 13/13 | **13/13** |
| I01 recibos trocados entre eventos | 0/20 | 0/20 | **20/20** |
| I02 índice da linha alterado | 0/20 | 0/20 | **20/20** |
| I03 veredito do recibo alterado | 0/20 | 0/20 | **20/20** |
| I04 recibo esvaziado | 0/20 | 0/20 | **20/20** |
| I05 linha aponta para evento inexistente | 0/20 | 0/20 | **20/20** |
| I06 duas chaves para um evento | 0/20 | 0/20 | **20/20** |
| I07 registro apagado mantido no recibo | 0/20 | 0/20 | **20/20** |
| I08 linhas inteiras trocadas entre chaves (fora do alcance) | 0/20 | 0/20 | 0/20 |
| truncamento consistente do fim (fora do alcance, `truncate_pure.py`) | 0/20 | 0/20 | 0/20 |

T14 do benchmark original aparece como 20/20 nas três versões, pelo mesmo artefato já explicado na revisão: a última folha é um apagamento. A medida correta é a de `truncate_pure.py`, na última linha.

**Compatibilidade [FATO VERIFICADO / INFERÊNCIA]:**
- Esquema do banco, formato da folha, do registro e do recibo, OpenAPI: sem mudança. [FATO VERIFICADO]
- Um banco criado antes desta correção, com apagamentos já feitos, terá linhas de idempotência com recibo completo de evento apagado. [INFERÊNCIA]
  - `verify_log()` passa a apontá-las;
  - o reenvio dessas chaves passa a ser recusado (503 ou `not_recorded`).
  - É a detecção correta do resíduo de dados pessoais.
  - A remediação é reescrever o recibo na forma redigida, decisão operacional do mantenedor. Nenhuma migração automática foi implementada.
- Desempenho, 5.000 eventos todos com chave, mediana de 3 execuções [FATO VERIFICADO]:
  - gravação 1,37 ms/evento (`main` 1,42);
  - `verify_log()` 1,49 s (`main` 0,58; P2 antes 0,65), porque cada recibo é reverificado;
  - reenvio 0,17 ms (antes 0,017).
  - Medido com a mutação rodando em paralelo, então os valores absolutos são aproximados.

## 4. Correções B1, B2 e B3

Todas em `tests/auditlog/test_witness_client_protocol.py`, 82 casos aprovados. Não foi preciso mudar o código do cliente: os testes confirmaram o comportamento já corrigido em `9e957cd5`. **[FATO VERIFICADO]**

**B1, limite de 63 nós:**
- 0, 1, 62 e 63 nós decodificam;
- 64, 65 e 200 são recusados;
- via `submit`, 62 e 63 passam o limite e só falham na prova local, enquanto 64 falham no limite. Nos três casos, nenhum pedido HTTP sai;
- lista vazia vale só onde a especificação permite: primeiro contato e repetição;
- 15 formas malformadas, recusadas antes de qualquer pedido: nó vazio, 31 ou 33 bytes, alfabeto inválido, espaço, sem preenchimento, quebra de linha, base64url, inteiro, `None`, bytes ou str no lugar de lista, mapeamento;
- base64 não canônico também é recusado.
- O limite é aplicado depois da decodificação, então nenhum formato de entrada o contorna.

**B2, 409:**
- `0\n` dá `witness_size == 0`, distinto de `None`;
- valores positivos, inclusive o máximo de uint64, são lidos;
- o parâmetro `charset` e o tipo em maiúsculas são aceitos;
- dão `None`: cabeçalho ausente, outro tipo de mídia, negativo, não numérico, decimal, espaço antes ou depois, linha extra, CRLF, zeros à esquerda, dígito de largura total, corpo vazio e falta de LF final;
- com tamanho da testemunha menor ou maior que o local (0, 1, 5 e 9), o estado local não avança nem regride, e não há reenvio automático;
- 400, 403, 404, 422, 500 e 503 não são `WitnessConflict`;
- 200 malformado e erro de transporte não mudam o estado.

**B3, sequência de checkpoints, só com regras da C2SP e do cliente:**
- primeiro contato com o checkpoint 1 envia `old 0`;
- sem o checkpoint 1, o primeiro contato no tamanho 5 também é `old 0` com prova vazia. É permitido pela especificação: ausência legítima, não inconsistência;
- primeiro contato com prova é recusado;
- árvore vazia: tamanho 0, repetição do tamanho 0, recusa de prova a partir do 0 e salto 0 → 2;
- progressão 1 → 2 → 7;
- lacuna com prova de outro tamanho é recusada;
- repetição do mesmo checkpoint, com prova não vazia recusada;
- regressão 3 → 2, 1, 0 é recusada antes do HTTP;
- mesmo tamanho com outra raiz é recusado;
- estado anterior incompatível (outro log, outra chave, lixo) é recusado;
- testemunha à frente de um cliente reiniciado: 409 com o tamanho dela, e retomada a partir do checkpoint dela.

## 5. Interoperabilidade Torchwood

**[FATO VERIFICADO] Executada.**
- **Binário:** `interopwitness`, sha256 `a9a9d0fb995608f9d3440a0e951464fbde6e376bc1dedbb300c45bcae9659a05`.
  - Compilado de `filippo.io/torchwood@v0.10.0` `internal/witness`, sem modificação, mais um `main.go` de 60 linhas que só cria o banco, registra a chave do log e serve por `httptest` em TLS local.
  - Módulo baixado do proxy oficial do Go e conferido pelo `sum.golang.org`.
  - Go 1.27.0.
- **Ambiente:** loopback, com o TLS verificado contra o certificado do próprio servidor. Nenhum controle de segurança foi desativado.
- **Comando:** `PYTHONPATH=<árvore>/src python -P interop.py <interopwitness> <dir>`.

| cenário | resultado (cliente final) |
|---|---|
| chave da testemunha é C2SP tipo 0x04 Ed25519 | PASS |
| S1 primeiro contato (`old 0`, tamanho 1), cossignatura verificada | PASS |
| S2 progressão 1→3 com prova | PASS |
| S3 repetição do tamanho 3 | PASS |
| S4 lacuna 3→9 com prova | PASS |
| S5 cliente sem estado: 409 com tamanho 9 | PASS |
| S5 o 409 não avança o estado | PASS |
| S6 retomada 9→10 a partir do checkpoint da testemunha | PASS |
| S7 primeira linha sem `old ` → 400 | PASS |
| S8 64 linhas de prova → 400 | PASS |
| S9 checkpoint de outra visão do log (split view) → 422 | PASS |
| S9b o cliente recusa a outra visão localmente | PASS |
| S10 checkpoint assinado por chave desconhecida → 403 | PASS |
| S11 `old` errado → 409 `text/x.tlog.size` `10\n` | PASS |

**[FATO VERIFICADO]** Com o cliente da cabeça original da PR (`7e078bc1`), o primeiro envio já falha: `WitnessError: witness returned HTTP 400`. É o defeito do formato, agora comprovado contra a implementação real.

Níveis de evidência, separados:
- **leitura de código:** `processAddCheckpointRequest` do torchwood, na revisão;
- **testes próprios:** testemunha simulada que segue a especificação;
- **execução real:** esta seção.

**Limites:**
- uma única implementação de testemunha, em loopback;
- nenhuma testemunha pública ou independente foi contatada.

## 6. Revisão criptográfica e de segurança

**[FATO VERIFICADO]** Releitura dos seis módulos. `commitment.py`, `merkle.py` e `note.py` não mudaram em relação à `main`.

- **Canonicalização e serialização:**
  - o compromisso usa RFC 8785 com rótulo de domínio fixo e sal de 32 bytes do CSPRNG;
  - o recibo guardado usa `json.dumps(sort_keys=True)`; a folha é comparada byte a byte, codificada em base64.
- **Comparações:**
  - o compromisso e as raízes Merkle usam `hmac.compare_digest`;
  - o cliente de testemunha compara raízes públicas com `!=`, sem segredo envolvido, então o tempo de resposta não vaza nada.
- **Base64:** `validate=True` e exigência de forma canônica nos nós de prova.
- **Provas:** inclusão e consistência RFC 6962, já conferidas com `transparency-dev/merkle`.
- **Checkpoints:**
  - assinatura, origem e tamanho são conferidos;
  - checkpoint ausente é apontado;
  - rollback é recusado no cliente;
  - truncamento consistente só é detectável com testemunha.
- **Entradas malformadas:** devolvem problema ou `False` em vez de exceção. As exceções de `verify_receipt` são capturadas.
- **Concorrência e transação:**
  - o reenvio valida o recibo dentro do `BEGIN IMMEDIATE`;
  - `erase()` redige o recibo na mesma transação;
  - `verify_log()` faz leituras sucessivas sem snapshot único. Isso é preexistente e já era assim para folhas e checkpoints. [INFERÊNCIA] Uma gravação concorrente de outro processo pode, em tese, gerar um aviso transitório.
- **Armazenamento e offline:** o mesmo `verify_receipt` é usado na verificação offline e na auditoria da tabela.
- **Observação mantida:** `verify_cosignature` devolve `False` na primeira linha da testemunha com assinatura inválida, sem olhar linhas seguintes. A especificação trata isso como nota malformada.

Nenhum defeito crítico ou alto pendente foi encontrado. Nenhuma mudança de algoritmo foi feita.

## 7. Testes e cobertura

**[FATO VERIFICADO]**

| medida | revisão (`9e957cd5`) | final |
|---|---|---|
| suíte completa | 3.125 | **3.267 aprovados**, 0 falhas, em Python 3.11.18, 3.12.3 e 3.13.18 (local, venv limpo por versão) |
| cobertura de linhas, 7 arquivos `auditlog` | 100% | **100%** (915 linhas) |
| cobertura de ramos | 99% | **99%**: 380 ramos, 2 parciais (`store.py` 109→111, caminho `:memory:`; 367→369, rollback fora de transação), ambos preexistentes |
| Ruff check / format (0.17.5) | limpo | **limpo** (569 arquivos) |
| mypy `src/ayorai_attractor` | limpo | **limpo** (107 arquivos); `--strict` em `auditlog` também limpo |
| Bandit `src/ayorai_attractor` | limpo | **limpo** (0 médio, 0 alto) |
| build `sdist` + `wheel` | — | gerados localmente (`ayorai_opensearch-0.8.0`) |

**Os 142 testes a mais:**
- 47 de M1 e M2;
- 2 de HTTP;
- 82 de B1, B2 e B3;
- 24 das lacunas apontadas pela mutação (`tests/auditlog/test_p2_mutation_gaps.py`).

Nenhum teste foi removido ou alterado para passar.

## 8. Mutação

**Ferramenta:** a mesma da revisão, troca de operadores por AST em cópia temporária.
- Comparações, `and`/`or`, `not`, constantes inteiras e booleanas.
- Desta vez rodaram **todos** os pontos de mutação dos três arquivos, não uma amostra.

**[FATO VERIFICADO]**

| arquivo | revisão (amostra) | completa, antes dos testes de lacuna | completa, final |
|---|---|---|---|
| `store.py` | 50/53 | 163/182 | **171/182** |
| `witness_client.py` | 52/60 | 73/79 | **78/79** |
| `cosignature.py` | 44/50 | 70/81 | **76/81** |
| total | 146/163 (89,6%) | 306/342 (89,5%) | **325/342 (95,0%)** |

**Diferença em relação à revisão:** a revisão sorteou 163 mutantes. Aqui foram os 342. A taxa intermediária é a mesma; a final sobe porque 19 sobreviventes eram lacunas reais e ganharam testes:
- checkpoint 1 ausente;
- base64 não estrito no recibo;
- reabertura com lacuna ou com hash divergente, isoladamente;
- `frozen`;
- diretório pai;
- usuário sem senha na URL;
- timeout menor que 1 s;
- linha sem LF final;
- janela padrão de 300 s;
- `now` negativo, zero ou máximo;
- linha com campo extra;
- linha curta antes de uma válida.

**Classificação dos 17 sobreviventes finais:**

| linha | mutante | classe | motivo |
|---|---|---|---|
| `store.py` 281, 301, 360 (4) | `sort_keys` True→False | equivalente comprovado | o JSON é relido com `json.loads`; o compromisso usa RFC 8785, não essa ordem |
| `store.py` 178 (2) | `0`→`1`, `+1`→`+2` em `_stored_size` | equivalente comprovado | só força uma recarga a mais da árvore (desempenho), sem mudar resultado |
| `store.py` 480 | `<`→`<=` no alvo do apagamento | equivalente comprovado | alvo igual ao próprio índice é recusado logo depois por `target not in event_leaves` |
| `store.py` 538 | `[:12]`→`[:13]` no rótulo | equivalente comprovado | só muda o texto da mensagem |
| `store.py` 643 | `or`→`and` no teste de `bool` | equivalente comprovado | `verify_inclusion` recusa índice `bool` por conta própria (defesa em profundidade) |
| `store.py` 447 | `else 0`→`else 1` | comportamento não alcançável | o log sempre publica o checkpoint de tamanho 0, então a lista nunca está vazia em operação |
| `store.py` 409 | `parents=True`→`False` em `backup()` | lacuna de teste (baixa) | backup para diretório com avô inexistente; não afeta integridade |
| `witness_client.py` 58 | `255`→`256` | equivalente comprovado | `key_id` recusa nome acima de 255 bytes logo depois |
| `cosignature.py` 31 (2) | `< 0x20`→`<=`, `0x20`→`0x21` | equivalente comprovado | 0x20 é espaço e já é recusado por `isspace()` |
| `cosignature.py` 106 (2) | `< 0`→`<= 0`, `0`→`1` | comportamento não alcançável | separador na posição 0 exige nota que começa com linha vazia, sem corpo de checkpoint |
| `cosignature.py` 121 | `validate=True`→`False` | equivalente comprovado | a recodificação canônica na linha seguinte recusa o mesmo conjunto |

Não há sobrevivente inconclusivo.

## 9. CI

Ver o adendo no fim do relatório.

## 10. Golden e Judge

**[FATO VERIFICADO]** Golden, antes e depois idênticos aos hashes congelados:
- smoke-v0 `969ec61a4aee4e4426f5d217819bd185ebba248743e7721714a3123f5df67c3d`;
- v0 `21abb816facce73fc924842d12b373b8792abc2e7389e129c35bb58bab806632`;
- v0.1 `1fd6fdb75fabcf95b81c0657053a6ba570f97abde96b9dbf5cdda554bf0a9180`.

**[FATO VERIFICADO]** Judge Regression, comandos do `ci.yml`:
- `JUDGE_V0: PASS` (6/6);
- `JUDGE_SMOKE: PASS`.

**[FATO VERIFICADO]** `git diff origin/main` vazio em `rules/`, `judge2/`, `evals/`, `docs/eval/`, `docs/release/`, `DECISIONS-APPROVED.md` e `DECISIONS-PENDING.md`. Objetos de árvore idênticos aos da `main`:
- `rules` `ba33f663`;
- `judge2` `e0047500`;
- `evals/golden` `8f092dda`;
- `evals/ptbr/sources` `86468921`.

## 11. Limitações operacionais (classificação)

| limitação | classe | decisão |
|---|---|---|
| nenhuma testemunha real configurada | 4. depende de decisão (DEC-029: instituições a selecionar) | não implementar |
| só Ed25519; testemunha só ML-DSA-44 não aceita | 2. limitação documentada; 3. evolução para produção | não implementar sem dependência PQC avaliada (origem, licença, cadeia) |
| último checkpoint do cliente em memória | 2. limitação documentada. A testemunha guarda o estado com autoridade: o 409 com tamanho permite retomar (teste B3 e cenário S6) | persistência é evolução para produção |
| sem quórum de duas testemunhas | 4. depende de decisão (ADR-010, DEC-029) | não implementar |

Nenhuma delas é defeito de segurança dentro do escopo da P2. **[INFERÊNCIA]**

## 12. Riscos remanescentes

- **[FATO VERIFICADO] Troca de linhas inteiras entre chaves (I08).** Também vale para a linha apagada (caso 5).
  - O vínculo chave → evento não está na árvore assinada. Quem escreve no banco pode remapear chaves.
  - Efeito limitado: o reenvio confere a entrada e nunca devolve o recibo de outra entrada; no pior caso, recusa com 409 ou grava o evento de novo.
  - **Proposta isolada, não implementada:** registro v3 com o digest da chave dentro do registro salgado. `verify_log()` então conferiria `key_digest` contra o registro comprometido.
  - Isso muda o registro exposto no recibo público, ou seja, o contrato. Pela seção 1 do `AGENTS.md`, fica para decisão do mantenedor.
- **[FATO VERIFICADO] Truncamento consistente do fim:** só é detectável com uma testemunha externa.
- **[INFERÊNCIA] Bancos com apagamentos anteriores** à correção passam a ser apontados (seção 3). Precisam de remediação operacional.
- **[HIPÓTESE]** `verify_log()` sem snapshot pode gerar falso aviso sob gravação concorrente de outro processo. Não foi observado e não foi testado.
- **[FATO VERIFICADO]** A especificação C2SP lida é a cópia do editor; `c2sp.org` está bloqueado neste ambiente. Não existe vetor oficial de cossignatura.

## 13. SHA final

**Commits nesta etapa, sobre `9e957cd5`:**
- `3d9d77ff` fix: recibos de idempotência auditados e redigidos no apagamento;
- `ea9f73c7` test: B1, B2, B3 e lacunas da mutação;
- `2ea2e2fa` docs: relatório e evidências;
- o commit deste texto final, que só altera documentação.

O SHA final e o resultado da CI nele constam da descrição da PR #634. Um relatório versionado não pode citar o hash do próprio commit.

## 14. Veredito técnico

**APROVADA COM RESSALVAS.** [INFERÊNCIA, a partir dos fatos das seções 3 a 10]

**Critérios atendidos:**
- M1 corrigido: o ataque original é detectado por `verify_log()`, e o reenvio não devolve recibo alheio;
- M2 corrigido;
- B1, B2 e B3 com testes específicos;
- suíte completa aprovada em 3.11, 3.12 e 3.13;
- Ruff, mypy e Bandit limpos;
- Golden e Judge intactos;
- nenhum defeito crítico ou alto pendente;
- interoperabilidade executada contra a testemunha de referência.

**Ressalvas, que não são defeitos do código entregue:**
1. o vínculo chave → evento não é ancorado na árvore. A correção completa muda o contrato do recibo e depende de decisão do mantenedor (seção 12);
2. bancos com apagamentos anteriores precisam de remediação operacional;
3. limitações operacionais da seção 11: nenhuma testemunha configurada, só Ed25519, estado em memória e sem quórum;
4. interoperabilidade testada com implementações de terceiros (torchwood, `sumdb/note`, `transparency-dev/merkle`), mas não com um serviço de testemunha público, que exige cadastro (adendo B).

Código corrigido, testes aprovados, conformidade normativa e interoperabilidade prática estão demonstrados nos níveis descritos acima. **Prontidão para produção não está demonstrada:** depende das decisões das seções 11 e 12.

## Adendo — questões de fechamento (2026-11-22)

### A. Interoperabilidade criptográfica independente

Cada formato foi conferido contra uma implementação de terceiros, e nos dois sentidos quando o formato tem produtor e verificador.

| formato | produzido por | verificado por | evidência |
|---|---|---|---|
| hashes, raízes, provas de inclusão e de consistência RFC 6962 | `transparency-dev/merkle` (Go) | Python, byte a byte | `tests/auditlog/vectors/rfc6962-transparency-dev.json`, na CI [FATO VERIFICADO] |
| checkpoint assinado (signed note Ed25519) e recibos | Python | `golang.org/x/mod/sumdb/note` (Go) | `tests/auditlog/vectors/verify_receipts.go.txt` (critério 4 da ADR-010) [FATO VERIFICADO] |
| checkpoint assinado e provas de consistência no pedido `add-checkpoint` | Python | testemunha torchwood v0.10.0 em execução | seção 5, 14/14 [FATO VERIFICADO] |
| cossignatura C2SP Ed25519 (tipo 0x04) | torchwood (testemunha real) | Python (`verify_cosignature`) | seção 5, cenários S1–S6 [FATO VERIFICADO] |
| cossignatura C2SP Ed25519 e chave do cossignatário | Python (`sign_cosignature`, `key_id`) | `torchwood.NewCosignatureVerifier` com `sumdb/note.Open` (Go) | `evidence/p2-closure/xverify-*`: 9/9 [FATO VERIFICADO] |

**Detalhe da última linha:**
- **Casos aceitos (5):** timestamps 0, 1,7·10⁹, 1,8·10⁹, 2⁶³−1 e 42; nomes com `/`, `-`, `_` e `oid/`; árvores de 0 a 1.000 folhas.
- **Casos recusados (4):** corpo alterado, assinatura alterada, timestamp alterado e chave de outro cossignatário.
- **Integridade do binário:** `xverify` tem sha256 `74b9d494…`; foi compilado de `filippo.io/torchwood@v0.10.0` e `golang.org/x/mod` sem modificação.

**Conclusão [INFERÊNCIA]:** não há formato criptográfico da P2 validado apenas contra a própria implementação.

### B. Testemunha: serviço externo real ou ambiente simulado

Há três níveis, e só os dois primeiros foram atingidos:

1. **Simulado** (testemunha em memória nos testes): sim, segue a especificação. [FATO VERIFICADO]
2. **Implementação real de terceiros em execução** (torchwood v0.10.0, o código das testemunhas públicas do ecossistema C2SP): sim, em TLS local. [FATO VERIFICADO]
3. **Serviço externo independente na internet:** não, por dois motivos.
   - Uma testemunha pública só cossigna logs que o operador dela cadastrou, com origem e chave pública. Nenhum log do AYORAI está cadastrado. [FATO VERIFICADO: pela especificação `tlog-witness`, origem desconhecida dá 404; no cenário S10, assinatura de chave não cadastrada deu 403.]
   - Escolher e contatar testemunhas independentes é a etapa 2 da DEC-029, que depende de decisão do mantenedor e de instituições externas.
   - Isso não é lacuna de código: o cliente que falaria com esse serviço é o mesmo que passou no nível 2.

### C. Registro v3: o formato atual é suficiente?

**Determinação [INFERÊNCIA, a partir dos fatos das seções 3 e 12]: o formato atual é suficiente para integridade, rastreabilidade e compatibilidade da P2. A v3 não é necessária agora.**

1. **Integridade da evidência.** Toda decisão gravada é uma folha assinada, com compromisso salgado e inclusão verificável sem o servidor. A tabela de idempotência não é evidência: é um cache para entrega única. Nenhuma manipulação dela altera, apaga ou forja uma decisão registrada. [FATO VERIFICADO: benchmark T01–T13 e I01–I07, recibos conferidos com Go]
2. **O que a v3 acrescentaria.** Só a detecção de uma linha de idempotência trocada inteira entre chaves, ou apagada, por quem tem escrita no banco (I08 e caso 5).
   - Com a correção M1, o pior efeito disso é o reenvio recusado com 409 ou gravado como evento novo.
   - Um evento duplicado continua visível no log, com o mesmo `input_sha256` em dois índices assinados.
   - O servidor nunca devolve o recibo de outra entrada. [FATO VERIFICADO: `test_m1_02`, `test_m1_05`]
3. **Rastreabilidade.** Requisição → evento → recibo é rastreável pela entrada (`input_sha256`) gravada no registro comprometido. A chave de idempotência é um detalhe de transporte do cliente e não precisa entrar na evidência.
4. **Compatibilidade.** A v3 mudaria o registro devolvido ao cliente no recibo (`record.schema`). Como na v2 (ADR-013, DEC-032), isso exige ADR e decisão própria. Manter a v2 não muda nada para quem já verifica recibos.
5. **Gatilhos para reabrir a questão:**
   - exigência contratual de entrega exatamente única auditável por terceiros;
   - mais de um escritor (migração para o Tessera, DEC-028);
   - a chave de idempotência passar a ter valor probatório.

**Status:** é uma recomendação técnica. O registro formal da decisão em `DECISIONS-APPROVED.md` cabe ao mantenedor, porque o arquivo é protegido.

## Evidências (`docs/audit/evidence/p2-closure/`)

| arquivo | conteúdo |
|---|---|
| `interop.py`, `interopwitness-main.go` | roteiro de interoperabilidade e servidor da testemunha torchwood |
| `interop-result-final.json`, `witness-final.log` | resultado 14/14 e pedidos registrados pela testemunha |
| `witness-original-head-7e078bc1.log` | recusa `invalid input` do pedido sem `old ` |
| `tamper_bench.py`, `truncate_pure.py`, `bench-*.json` | benchmark de adulteração (`main`, P2 antes, P2 final) |
| `perf_idem.py` | desempenho com chaves de idempotência |
| `mutate.py`, `mutation-results.txt` | ferramenta e resultados da mutação |
| `xverify-main.go`, `xverify_cases.py`, `xverify-result.txt` | verificação em Go (torchwood e `sumdb/note`) das cossignaturas e checkpoints produzidos em Python |

Reprodução: `PYTHONPATH=<árvore>/src python -P <script> <rótulo> <saída>`.
