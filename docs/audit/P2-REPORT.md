# P2 — Hardening da trilha verificável

- **Data:** 2026-11-22
- **Branch:** `p2-auditlog-hardening`
- **Base:** `main` em `76876bb70abcffe488176bb9b3b324942227aaad` (merge da AP1 #632)
- **HEAD de referência do primeiro relatório:** `b8c66a30003ef633efd417282fe6f964c5236a47`
- **Estado:** trabalho em andamento; sem PR, merge, release, tag ou DOI.

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

Esses testes foram adicionados, mas **a suíte ainda precisa ser executada em ambiente com as dependências do projeto**. A branch não foi aberta como PR, portanto ainda não há CI remoto associado a este HEAD. Nenhum resultado de teste é declarado como aprovado nesta etapa.

## 3. Testemunhas externas — escopo e limites

A ADR-010 e a DEC-029 distinguem:
1. checkpoint diário guardado fora do host pelo operador — etapa operacional já documentada, mas não é testemunha independente;
2. pelo menos duas testemunhas sem vínculo de controle com o operador — etapa de protocolo ainda a implementar e de instituições ainda não selecionadas.

A especificação C2SP `tlog-witness` v1.1.0 define `POST <submission-prefix>/add-checkpoint`: o log envia o tamanho anterior, a prova de consistência e o checkpoint assinado. A testemunha verifica a assinatura do log, o tamanho anterior e a prova de consistência; persiste o novo checkpoint antes de responder e devolve uma cosignatura. A atualização do estado e a verificação precisam ser atômicas para impedir regressão por concorrência. Ver:
- https://c2sp.org/tlog-witness@v1.1.0
- https://c2sp.org/tlog-cosignature@v1.1.0
- https://c2sp.org/tlog-checkpoint@v1.1.0

A cosignatura Ed25519 C2SP usa o tipo de assinatura `0x04`, inclui timestamp POSIX de 8 bytes e assina uma mensagem com separação de domínio `cosignature/v1`. Ela não é a assinatura Ed25519 padrão `0x01` que o módulo atual usa para o checkpoint do log. A implementação deve tratar os dois tipos separadamente e verificar um quórum configurado de chaves independentes; não basta aceitar qualquer linha adicional de assinatura.

**Limite de decisão:** não foram escolhidas ou contatadas testemunhas. Não será configurado endpoint real, política de quórum, chave de terceiro ou afirmação de independência sem uma seleção verificável e sem validar a compatibilidade operacional. O carimbo RFC 3161/ICP-Brasil continua adiado pela DEC-030; esta P2 não contrata serviço nem cria afirmação temporal.

## 4. Próximos passos técnicos

1. Executar a suíte direcionada e a suíte completa em ambiente de desenvolvimento; corrigir qualquer falha antes de ampliar o escopo.
2. Adicionar vetores independentes e testes negativos para cosignaturas C2SP Ed25519 `0x04`, incluindo timestamp, nome, key ID, corpo do checkpoint e assinaturas desconhecidas/malformadas.
3. Implementar cliente de testemunha com estado monotônico, retry seguro e tratamento de HTTP 409 sem rebaixar o checkpoint local.
4. Definir persistência das cosignaturas e política de quórum sem alterar o contrato de resposta existente por acidente.
5. Projetar o monitoramento/recuperação contra split-view e concorrência; provar comportamento com testemunhas simuladas antes de qualquer conexão externa.
6. Só então propor integração com duas testemunhas reais independentes e validar os critérios da ADR-010.

## 5. Restrições preservadas

- Nenhuma alteração em `rules/`, `judge2/`, `evals/`, `docs/eval/`, `docs/adr/`, decisões aprovadas ou notas de release.
- Nenhuma alteração no Judge, nos vereditos, nos contratos HTTP ou nos hashes Golden.
- Nenhuma publicação, merge, tag, release ou DOI.
- A resistência ao operador que controla simultaneamente banco e chave **não** é alegada sem duas cosignaturas independentes ativas.
