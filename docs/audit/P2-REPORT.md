# P2 — Hardening da trilha verificável

- **Data:** 2026-11-22
- **Branch:** `p2-auditlog-review`
- **Base:** `main` em `76876bb70abcffe488176bb9b3b324942227aaad` (merge da AP1 #632)
- **HEAD de referência do primeiro relatório:** `b8c66a30003ef633efd417282fe6f964c5236a47`
- **PR:** #634 (draft, aberta para revisão); sem merge, release, tag ou DOI.

## Objetivo

Endurecer a trilha da ADR-010 sem alterar regras do Judge, contratos públicos, Golden, decisões aprovadas ou artefatos protegidos. A P2 separa integridade local, evidência mantida fora do servidor e testemunhas realmente independentes.

## 1. Achados de código

### P2-01 — o verificador local não reabria o compromisso do registro restrito

**[FATO VERIFICADO — leitura de código]** Antes desta alteração, `VerificationLog.verify_log()` recalculava os hashes das folhas e conferia as raízes/checkpoints assinados, mas não recomputava o compromisso salgado a partir de `vlog_records.record` e `vlog_records.salt`.

Consequência: uma alteração isolada na tabela restrita podia deixar o Merkle tree e seus checkpoints intactos, sem que `verify_log()` a identificasse. A verificação offline do recibo já conferia o compromisso, mas isso não substituía a auditoria do armazenamento mantido pelo servidor.

**Alteração nesta branch:** para cada folha de evento, o verificador agora:
- exige a linha correspondente no armazenamento restrito, salvo quando existe evento de apagamento válido;
- recalcula o compromisso usando o registro e o sal armazenados;
- detecta alteração do registro, alteração do sal e apagamento parcial;
- detecta linha restrita órfã ou sem folha de evento;
- exige que a folha de apagamento aponte para uma folha de evento anterior, não para outra folha de apagamento;
- detecta mais de uma folha de apagamento para o mesmo evento;
- valida a estrutura e o motivo da folha de apagamento;
- confere se o timestamp do registro restrito corresponde ao timestamp imutável da folha;
- detecta registro restaurado depois de seu evento de apagamento.

### P2-02 — esquemas de folha desconhecidos eram ignorados

**[FATO VERIFICADO — leitura de código]** O verificador classificava folhas conhecidas de evento e apagamento, mas não registrava explicitamente uma folha JSON com esquema desconhecido.

**Alteração nesta branch:** esquemas públicos não reconhecidos passam a gerar problema de integridade, e a ausência da folha de evento correspondente é apontada.

## 2. Testes de regressão acrescentados

Em `tests/test_verify_log_integrity.py`:
- alteração do registro sem alterar a folha;
- alteração do sal;
- apagamento parcial do registro;
- linha de registro órfã;
- folha de apagamento apontando para outra folha de apagamento;
- esquema público desconhecido;
- adulteração do timestamp de apagamento;
- restauração do registro depois do apagamento;
- motivo inválido em folha de apagamento;
- folhas de apagamento duplicadas para o mesmo evento.

Os testes foram adicionados à PR #634. A primeira execução da CI encontrou duas violações Ruff de UP012 em `cosignature.py` e `test_witness_client.py`; as correções foram aplicadas nesta branch e precisam ser revalidadas por nova execução completa. Os resultados parciais da execução anterior não constituem aprovação da suíte principal.

## 3. Testemunhas externas — escopo e limites

A ADR-010 e a DEC-029 distinguem:
1. checkpoint diário guardado fora do host pelo operador — etapa operacional já documentada, mas não é testemunha independente;
2. pelo menos duas testemunhas sem vínculo de controle com o operador — etapa de protocolo ainda a implementar e de instituições ainda não selecionadas.

A especificação C2SP `tlog-witness` v1.1.0 define `POST <submission-prefix>/add-checkpoint`: o log envia o tamanho anterior, a prova de consistência e o checkpoint assinado. A testemunha verifica a assinatura do log, o tamanho anterior e a prova de consistência; persiste o novo checkpoint antes de responder e devolve uma cosignatura. A atualização do estado e a verificação precisam ser atômicas para impedir regressão por concorrência. Ver:
- https://c2sp.org/tlog-witness@v1.1.0
- https://c2sp.org/tlog-cosignature@v1.1.0
- https://c2sp.org/tlog-checkpoint@v1.1.0

A cosignatura Ed25519 C2SP usa o tipo de assinatura `0x04`, inclui timestamp POSIX de 8 bytes (uint64, incluindo zero) e assina a mensagem com separação de domínio `cosignature/v1`, seguida do checkpoint completo. O key ID inclui o nome do cosigner, LF, tipo `0x04` e chave pública. Ela não é a assinatura Ed25519 padrão `0x01` do checkpoint do log. O cliente valida uma identidade de testemunha configurada; isso ainda não implementa quórum de duas testemunhas.

**Limite de decisão:** não foram escolhidas ou contatadas testemunhas. Não será configurado endpoint real, política de quórum, chave de terceiro ou afirmação de independência sem uma seleção verificável e sem validar a compatibilidade operacional. O carimbo RFC 3161/ICP-Brasil continua adiado pela DEC-030; esta P2 não contrata serviço nem cria afirmação temporal.

## 4. Próximos passos técnicos

1. Reexecutar CI completa em Python 3.11, 3.12 e 3.13, Ruff, mypy, suíte integral, cobertura e verificações de regressão após os ajustes C2SP.
2. Realizar revisão técnica independente do formato de cosignatura, parsing do checkpoint e semântica de concorrência/rollback.
3. Tratar persistência durável do último checkpoint, armazenamento das cosignaturas e política de quórum como fase operacional separada, com desenho e testes de recuperação.
4. Selecionar e validar pelo menos duas testemunhas reais independentes antes de qualquer alegação de proteção operacional contra split-view.

## 5. Restrições preservadas

- Nenhuma alteração em `rules/`, `judge2/`, `evals/`, `docs/eval/`, `docs/adr/`, decisões aprovadas ou notas de release.
- Nenhuma alteração no Judge, nos vereditos, nos contratos HTTP ou nos hashes Golden.
- Nenhuma publicação, merge, tag, release ou DOI.
- A resistência ao operador que controla simultaneamente banco e chave **não** é alegada sem duas cosignaturas independentes ativas.


## 6. Implementação complementar — 2026-11-22

**[FATO VERIFICADO — código presente na branch]**

- **P2-03:** `VerificationLog.consistency(0)` agora retorna uma prova vazia, conforme o primeiro contato do protocolo de testemunhas; valores negativos, booleanos e tamanhos maiores que a árvore continuam inválidos.
- **P2-04:** `verify_log()` agora exige a presença de cada checkpoint esperado entre 1 e o tamanho atual da árvore e reporta lacunas individualmente.
- **Cosignaturas:** novo módulo `auditlog/cosignature.py`, separado de `note.py`, implementa Ed25519 C2SP tipo `0x04`, key ID específico, timestamp POSIX de 8 bytes e separação de domínio `cosignature/v1`. A assinatura de log tipo `0x01` permanece inalterada.
- **Cliente:** novo `auditlog/witness_client.py` envia `add-checkpoint`, valida a assinatura do log e a cosignatura configurada, mantém checkpoint local monotônico e não avança o estado em HTTP 409 ou resposta inválida.
- **Vetores e testes:** foi adicionado um vetor determinístico de interoperabilidade derivado das regras publicadas C2SP v1.1.0 (explicitamente não apresentado como vetor oficial mantido pelo C2SP), além de testes para adulteração, chave incorreta, timestamp futuro, rollback, HTTP 409, prova inconsistente/split-view e concorrência simulada.

### Limites ainda explícitos

- O cliente é uma implementação de protocolo; não configura nem contata testemunhas reais.
- A simulação em memória é exclusivamente teste e não é um serviço de testemunha implantável.
- A política de quórum de duas testemunhas e o armazenamento durável da lista de cosignaturas continuam pendentes de desenho e decisão própria.
- O estado monotônico do cliente é em memória; a persistência durável do último checkpoint observado pelo cliente ainda precisa ser integrada a um armazenamento operacional.
- Nenhum carimbo RFC 3161/ICP-Brasil foi implementado ou contratado.

### Evidência de validação

Os testes direcionados, suíte completa, Ruff, mypy e CI remoto **ainda não foram executados/confirmados neste registro**. O código deve ser tratado como implementação candidata até a conclusão da CI e revisão independente. Não declarar a P2 pronta para produção antes dessa evidência.


## 7. Correções de conformidade C2SP após análise da CI — 2026-11-22

- A primeira CI apontou duas regras Ruff UP012, corrigidas sem supressões.
- A leitura da especificação C2SP confirmou timestamp como uint64 não negativo; o código e os testes agora aceitam timestamp zero e o limite uint64.
- A validação do nome foi ampliada para rejeitar whitespace Unicode, além de `+` e controles ASCII abaixo de U+0020.
- A decodificação da cosignatura agora exige base64 canônico.
- A CI precisa ser executada novamente após esses commits; nenhum desses ajustes é considerado validado até a conclusão dos jobs.

## 8. Integração do cliente com a API de prova — 2026-11-22

**[FATO VERIFICADO — revisão de código]** A inspeção da integração entre `VerificationLog.consistency()` e `WitnessClient.submit()` encontrou uma incompatibilidade de tipos: o armazenamento entrega nós da prova em strings Base64, enquanto o cliente aceitava apenas bytes e tentava codificar novamente cada nó. A chamada direta do fluxo de produção falharia antes do envio HTTP.

**Correção aplicada nesta branch:**
- o cliente agora aceita nós brutos de 32 bytes ou strings Base64 canônicas de 32 bytes;
- valida tipo, tamanho e canonicalidade antes de qualquer requisição;
- converte os dois formatos para bytes para verificar a prova e serializa o formato C2SP uma única vez;
- erros de transporte HTTP são convertidos em `WitnessError`, sem avançar o checkpoint local;
- o endpoint exige HTTPS e rejeita credenciais embutidas, query e fragmento;
- o timeout exige valor positivo e finito;
- o teste de avanço do checkpoint agora usa o mesmo formato Base64 produzido por `VerificationLog.consistency()`, e foi acrescentado teste negativo para Base64 inválido.

**Status:** correção implementada nos commits posteriores a `6100731`. A validação automatizada desses commits ainda precisa ser observada. Não declarar aprovação da CI, cobertura ou revisão independente com base apenas na implementação.

A revisão complementar também passou a exigir que a origem declarada no checkpoint corresponda ao nome da identidade presente na chave verificadora configurada. Foi acrescentado teste negativo para checkpoint corretamente assinado, mas com origem divergente; a requisição deve ser recusada antes de contatar a testemunha.

**Estado do código em `f481077` (HEAD de código antes desta atualização documental):** não havia execução de workflow nem status de commit reportado. Portanto, os ajustes das seções 8 e 9 permanecem sem validação automatizada remota. A CI aprovada em commit anterior não valida estas alterações. Esta atualização documental não altera o código.

## 10. Primeiro contato e checkpoint de tamanho zero — 2026-11-22

A revisão do verificador Merkle mostrou que `verify_consistency()` rejeita corretamente provas cujo tamanho anterior é zero: pela especificação, o primeiro contato usa tamanho zero e prova vazia, sem invocar a verificação RFC 6962 de prefixo não vazio. O cliente agora trata explicitamente esse estado especial, exige a raiz vazia correta e aceita a evolução posterior para um checkpoint maior somente com prova vazia. Checkpoints repetidos de tamanho zero também precisam preservar a mesma raiz.

Foram adicionados testes para:
- registrar um checkpoint assinado de tamanho zero e avançar depois para tamanho um;
- rejeitar uma raiz conflitante em checkpoint repetido de tamanho zero;
- simular a regra correspondente no witness de teste.

**Último commit de código desta rodada:** `cf6a9f637d194379ec51e664b038f9b1dac3bb7f`. A identidade da testemunha também é validada na construção, antes de qualquer requisição. Esses testes e correções ainda aguardam execução automatizada; não há status remoto novo disponível para o HEAD atual.

## 11. Validação remota após correção de formatação — 2026-11-22

**[FATO VERIFICADO — GitHub Actions, PR #634, HEAD de código `c84c5ab75c02efed2a326caec0411a2a79d8b4af`]**

A primeira execução no HEAD anterior falhou somente em `ruff format --check`, por espaçamento em `tests/auditlog/test_witness_client.py`. A formatação foi corrigida e a nova execução completa terminou com sucesso.

Resultados confirmados:
- CI principal: sucesso, incluindo Python 3.11, 3.12 e 3.13.
- Suíte completa em Python 3.11: **3.040 testes aprovados**, cobertura total **95%**.
- Ruff check, Ruff format e mypy: sucesso na matriz.
- Guardas de cobertura por módulo e baseline: sucesso.
- Golden Regression, Golden Smoke, Judge Regression e Golden Lint: sucesso.
- Security, Dependency Review e CodeQL: sucesso.
- API Contract Guard e Schemathesis Full API Contract: sucesso.
- ADR-010 isolated persistence POC e Tessera POSIX conformance: sucesso.
- Build distributions e workflow lint: sucesso.

A aprovação da CI demonstra que o conjunto de código testado passou nas verificações automatizadas. Ela não substitui revisão independente de protocolo nem valida testemunhas externas reais.

### Situação de encerramento

A implementação candidata da P2 e sua CI estão aprovadas. Permanecem fora deste incremento: persistência operacional durável do estado do cliente, quórum de duas testemunhas reais e configuração de testemunhas independentes. A PR continua Draft e sem aprovação independente registrada; portanto, não foi mesclada.


## 12. Expansão dirigida da cobertura e endurecimento final — 2026-11-22

**[FATO VERIFICADO — relatório de cobertura da CI no commit `eb46a5a4a2381c2b6e6c7549503a9a79224ac90c`]** A cobertura anterior específica da trilha era:
- `cosignature.py`: 86% (11 linhas não cobertas);
- `witness_client.py`: 81% (22 linhas não cobertas);
- `store.py`: 99% (4 linhas não cobertas);
- `merkle.py`: 99% (1 linha não coberta);
- `note.py` e `commitment.py`: 100%.

A cobertura total do pacote era 95%, com 3.040 testes aprovados nessa execução. Esses números são uma linha de base histórica; não representam a cobertura dos commits posteriores desta seção.

### Correções de implementação

- `WitnessClient` rejeita contêineres de prova que não sejam sequências, antes de tentar iterá-los ou enviar requisições.
- A validação de timeout também trata números inteiros tão grandes que não podem ser convertidos para float, recusando-os como valores não finitos em vez de deixar escapar `OverflowError`.
- `WitnessIdentity` valida explicitamente que o nome é texto antes de codificar e validar o identificador C2SP.

### Testes acrescentados

- `tests/auditlog/test_p2_coverage_edges.py`: entradas inválidas para nomes, chaves, timestamps, seeds, notas, base64 não canônico, provas, URLs, timeouts, respostas HTTP, erros de transporte, checkpoints inválidos, rollback, origem divergente, tamanho zero e checkpoint de mesmo tamanho com raiz conflitante.
- `tests/auditlog/test_p2_merkle_boundaries.py`: rejeição de hashes de folha com tamanho/tipo inválido pela árvore incremental.
- `tests/test_verify_log_integrity.py`: dados residuais após apagamento, JSON restrito malformado e falha simulada de integridade na cópia de backup.

### Estado de validação

**[FATO VERIFICADO]** Os commits desta expansão foram gravados somente em `p2-auditlog-review`; a `main` não foi alterada. Os testes foram desenhados para cobrir as linhas que constavam como ausentes no relatório anterior.

**[PENDENTE — não declarar como aprovado]** Ainda não há resultado de CI associado ao HEAD desta expansão. Portanto, não afirmar que a cobertura atual chegou a 100%, nem que os testes passaram. A próxima validação obrigatória é executar Ruff check/format, mypy e a suíte completa com cobertura em Python 3.11, 3.12 e 3.13; então usar o novo relatório `coverage.json`/saída `term-missing` para corrigir qualquer lacuna residual.

A meta é 100% de cobertura de linhas nos módulos críticos da P2, sem excluir código nem alterar o escopo de cobertura para inflar o indicador. Cobertura de linhas não substitui branch coverage, testes de mutação, revisão de protocolo ou validação com testemunhas externas reais.


## 13. Validação completa da cobertura P2 — 2026-11-22

**[FATO VERIFICADO — GitHub Actions, HEAD `2a24a6a42c64af9238e6d6f564c984965554a37a`, PR #634]**

A execução completa da CI terminou com sucesso em Python 3.11, 3.12 e 3.13. Em cada versão, a suíte aprovou **3.112 testes** e o relatório de cobertura apresentou os seis módulos de `auditlog` com **100% de cobertura de linhas**:

| Módulo | Statements | Missing | Line coverage |
|---|---:|---:|---:|
| `commitment.py` | 34 | 0 | 100% |
| `cosignature.py` | 76 | 0 | 100% |
| `merkle.py` | 179 | 0 | 100% |
| `note.py` | 106 | 0 | 100% |
| `store.py` | 313 | 0 | 100% |
| `witness_client.py` | 123 | 0 | 100% |
| **Total auditlog** | **831** | **0** | **100%** |

Cobertura global do pacote: **96%** (7.619 statements, 340 não cobertos). O baseline do repositório continua em 85%; a CI registrou melhoria para 96%, sem alterar o baseline.

### Resultados por versão

- Python 3.11: 3.112 testes aprovados em 83,90 s; cobertura global 96%.
- Python 3.12: 3.112 testes aprovados em 96,25 s; cobertura global 96%.
- Python 3.13: 3.112 testes aprovados em 74,58 s; cobertura global 96%.

### Demais verificações

Concluíram com sucesso: Ruff check, Ruff format, mypy, strict mypy não bloqueante, Golden Regression, Golden Smoke, Golden Lint, Judge Regression, workflow lint, build distributions, Security, CodeQL, Dependency Review, API Contract Guard, Schemathesis API e full contract, OpenAPI compatibility, ADR-010 isolated persistence POC e Tessera POSIX conformance.

Execuções relevantes:
- CI: `45058044270`
- Security: `45058044207`
- CodeQL: `45058044280`
- API Contract Guard: `45058044202`
- Schemathesis Full API Contract: `45058044369`
- ADR-010 isolated persistence POC: `45058044306`
- Dependency Review: `45058044285`
- Golden r2 Migration: `45058044366`

### Interpretação e limites

- **100% significa cobertura de linhas executáveis dos seis módulos auditlog**, confirmada nos três runtimes Python; não significa 100% de cobertura do projeto inteiro.
- A configuração executada não mede branch coverage; 100% de linhas não garante que toda combinação de decisão tenha sido testada.
- Testes de mutação não foram executados nesta rodada.
- A suíte não substitui revisão criptográfica/protocolar independente nem prova operação com testemunhas externas reais.
- Permanecem pendentes a persistência durável do estado do cliente, a seleção e integração de duas testemunhas independentes e a política operacional de quórum.

**Conclusão de engenharia:** a meta de 100% de cobertura de linhas da P2 foi atingida nos seis módulos de auditoria e a suíte passou em Python 3.11, 3.12 e 3.13. A implementação continua candidata a revisão independente; a PR #634 permanece Draft e não foi mesclada.
