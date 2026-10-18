# Decisões aprovadas — AYORAI ATTRACTOR

Este arquivo registra decisões explícitas do mantenedor já aprovadas. Não substitui ADRs normativas; mantém a trilha de governança e autorização.

## DEC-012 — Registro de auditoria verificável: decisões 1–4 da ADR-010

- **Data da decisão:** 2026-10-17
- **Decisor e mantenedor:** Anderson Leon Ayora
- **Decisão:** ACEITO, seguindo a recomendação técnica em todas as quatro perguntas.
  1. **Compromissos com sal** em vez de hashes diretos: a folha do log guarda `SHA-256(domain_label || salt || canonical_record)`; sal e registro ficam num armazenamento apagável, com controle de acesso, e no recibo do cliente.
  2. **Veredito só dentro do compromisso**, nunca em claro na folha.
  3. **Falha de gravação bloqueia:** no modo "registro obrigatório", sem evento gravado não há veredito; a API devolve erro.
  4. **Emenda à ADR-009 §15 aprovada** (registrada como §15.1): `audit_status`, `audit_receipt` e `Idempotency-Key`, campos aditivos fora de `result`, só com o registro ligado.
- **Continua em aberto:** escritor em Python ou Tessera (decidir por prova de conceito), testemunhas independentes e carimbo do tempo ICP-Brasil.
- **Execução:** em fases, uma PR por fase (ADR-010, "Implementation phasing"). A fase 1 é uma biblioteca isolada (árvore de Merkle RFC 6962 e compromissos), sem mudar API, banco, dependências ou o Judge.
- **Condições permanentes:** CI verde, revisão do SHA exato, nenhuma alteração de Golden, regras, hashes ou manifestos congelados.
- **Limite de maturidade:** até a fase 3 estar mesclada e implantada, nenhuma instalação pode ser descrita como tendo log de auditoria verificável.

## DEC-007 — Publicar a release v0.4.0?

- **Data da decisão:** 2026-10-11
- **Decisor e mantenedor:** Anderson Leon Ayora
- **Decisão de governança:** ACEITO COM RESSALVAS
- **Opção sobre a release:** OPÇÃO A — PUBLICAR
- **Decisão:** Aceitar o encerramento técnico da Onda 1 (PRs #147, #148 e #149) e da Fase 1 e autorizar a continuidade da Onda 2.
- **Autorização documental:** abrir e mesclar uma PR documental `docs: finalize v0.4.0 release metadata`, atualizando `docs/release/v0.4.0.md` para status `Released`, data `2026-10-11` e tag declarada `v0.4.0`; atualizar `CHANGELOG.md` para `[0.4.0] — 2026-10-11`; registrar `date-released: 2026-10-11` em `CITATION.cff`; e mover esta decisão da fila pendente para este registro aprovado.
- **Tag e publicação GitHub:** não criar automaticamente. Anderson criará manualmente a tag e a GitHub Release depois do merge da PR documental.
- **Correção obrigatória dos resultados:** nunca apresentar Path B 66,67% contra baseline 43,33% sem o contexto de ambas as versões. Golden v0: Path B = 43,33%, igual à classe majoritária. Golden v0.1: Path B = 66,67%, mas v0.1 foi reescrito após a observação dos resultados e não é evidência confirmatória independente. Relatar Golden v0 e v0.1 lado a lado em todos os relatórios e documentos relevantes.
- **Condições permanentes:** revisão independente do SHA exato de cada PR, CI verde, merge por SQUASH e artefatos congelados intocados. Nenhuma alteração de Golden, threshold ou manifesto congelado é autorizada por esta decisão.
- **Limite de maturidade:** a publicação v0.4.0 não afirma que o Judge 2.0.0 esteja totalmente implementado, que os Goldens de desenvolvimento demonstrem generalização em produção ou que haja certificação regulatória ou conformidade jurídica automática.

## DEC-008 — Publicar a release v0.5.0?

- **Data da decisão:** 2026-10-13
- **Decisor e mantenedor:** Anderson Leon Ayora
- **Decisão de governança:** ACEITO COM RESSALVAS
- **Opção sobre a release:** OPÇÃO A — PUBLICAR
- **Decisão:** autorizar a preparação da release v0.5.0 com os itens 2.1–2.7 do Judge 2.0, condicionada à revisão independente do SHA exato da PR e à aprovação dos seis checks obrigatórios.
- **Autorização documental:** abrir a PR `release: prepare v0.5.0 (Phase 2 — Judge 2.0)`, atualizar metadados de versão, changelog, guia, matriz de rastreabilidade e notas de release, preservando os artefatos congelados.
- **Compatibilidade:** adiar para v0.6.0 a remoção de `ResponseStatus`, dos campos `verification` e `confidence` e do caminho `r1-a` com regras 1.x. Nada é removido na v0.5.0.
- **Tag e publicação GitHub:** não criar automaticamente. Anderson criará manualmente a tag `v0.5.0` e a GitHub Release após o merge da PR.
- **Condições permanentes:** revisão independente do SHA exato, seis checks CI verdes e artefatos congelados intocados. Nenhuma alteração de Golden, thresholds, manifestos congelados ou `rules/judge-2.0.0.json` é autorizada.
- **Limite de maturidade:** não se afirma certificação regulatória, conformidade jurídica automática nem generalização em produção a partir dos Goldens de desenvolvimento. Hashes identificam conteúdo, mas não demonstram a verdade factual; a limitação documentada de forja em processo permanece.

## DEC-002 — Política de licença e proveniência das fontes

- **Data da decisão:** 2026-10-13
- **Decisor e mantenedor:** Anderson Leon Ayora
- **Decisão:** OPÇÕES 1 e 3 combinadas, conforme detalhado abaixo. A opção 2 (exceções caso a caso) não foi adotada.
- **Atos oficiais:** textos de leis, decretos, regulamentos, resoluções e demais atos oficiais podem ser usados no corpus e em fixtures, com base na Lei nº 9.610/1998, art. 8º, IV (fonte primária: https://www.planalto.gov.br/ccivil_03/leis/l9610.htm). Para cada documento é obrigatório registrar em `docs/annotation/SOURCES.md`: URL oficial, órgão emissor, data de publicação, data e hora de coleta, método de captura e SHA-256 dos bytes capturados.
- **Demais fontes:** comentários doutrinários, livros, notícias, páginas comerciais, bases privadas e qualquer material de terceiros só entram com licença ou permissão explícita registrada. Sem esse registro, ficam excluídos.
- **Separação pública e privada:** fixtures públicos e o conjunto de avaliação oculto têm controles e manifestos distintos; os casos ocultos nunca entram no repositório público (`docs/eval/PROTOCOL-GOLDEN-V1.md`).
- **Efeito sobre o benchmark RGC:** a Resolução Anatel nº 765/2023 é ato oficial e fica autorizada como fonte, **condicionada** à captura e ao registro de proveniência acima. A coleta pode começar somente depois desse registro, seguindo `docs/eval/PREREGISTRATION-RGC-v1.md`.
- **Limite:** esta decisão não afirma parceria, apoio ou validação da Anatel e não constitui parecer jurídico; antes de contrato com instituição, recomenda-se confirmação por assessoria jurídica.

