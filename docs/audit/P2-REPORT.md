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

**Estado do HEAD `f481077`:** não há execução de workflow nem status de commit reportado para este HEAD. Portanto, os ajustes desta seção permanecem sem validação automatizada remota. A CI aprovada em commit anterior não valida estas alterações.
