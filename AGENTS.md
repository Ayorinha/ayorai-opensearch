# Regras para agentes automatizados — AYORAI ATTRACTOR

Este arquivo vale para qualquer ferramenta automatizada que contribua com este repositório. As mesmas regras se aplicam a colaboradores humanos (ver `CONTRIBUTING.md`).

## 1. Autoridade

- Anderson Leon Ayora, mantenedor, é a única autoridade sobre merges, releases, tags, publicações e decisões metodológicas ou de governança.
- Não mesclar PRs, não fechar PRs de terceiros, não criar tags nem publicar versões.
- Parar e pedir decisão do mantenedor quando a tarefa exigir decisão humana, anotação isolada, congelamento de protocolo, mudança de contrato, mudança de escopo ou autorização de merge.

## 2. Identidade do projeto e proibição de autopromoção

- Não incluir assinaturas, slogans, links de sessão, links comerciais ou créditos promocionais de ferramentas em descrições de PR, documentação, relatórios técnicos ou científicos, CHANGELOG, ADRs, notas de release ou outros materiais públicos do projeto.
- O protagonismo público é do projeto, de sua finalidade técnica, de suas evidências e de seus responsáveis.
- Citar uma ferramenta, fornecedor ou serviço apenas quando for necessário para proveniência científica, reprodutibilidade, segurança ou auditoria, de forma objetiva e proporcional.

## 3. Autoria, proveniência e histórico

- Não falsificar autoria nem atribuir ao mantenedor trabalho que ele não executou.
- Não reescrever o histórico de commits. Preservar as linhas de coautoria existentes.
- Remover publicidade desnecessária não autoriza apagar evidência: a proveniência técnica relevante deve continuar verificável.
- Em material já publicado (documentos, descrições de PR, registros metodológicos), apresentar o trecho atual e o texto proposto e aguardar autorização antes de alterar.

## 4. Artefatos protegidos

Exigem autorização explícita do mantenedor para qualquer alteração:

- regras do Judge (`rules/`, `src/ayorai_attractor/verification/judge2/`);
- conjuntos Golden, manifestos e hashes congelados;
- ADRs aceitas e decisões aprovadas (`docs/DECISIONS-APPROVED.md` e entradas aprovadas de `docs/DECISIONS-PENDING.md`);
- notas de release (`docs/release/`).

Não alterar esses artefatos para fazer testes passarem.

## 5. Benchmark RGC em português

- Não criar, revisar, ver ou rotular casos do segundo piloto nem do conjunto definitivo.
- Não executar o sistema sobre casos sem rótulo humano completo, nem sobre o conjunto oculto antes da execução única autorizada.
- Não afirmar benchmark validado, protocolo congelado, parceria, certificação, aprovação ou endosso de qualquer instituição sem evidência verificável.
- Resultados exploratórios nunca são apresentados como confirmatórios.

## 6. Soberania tecnológica

- Priorizar soluções, serviços e componentes brasileiros quando forem tecnicamente adequados em segurança, qualidade, licença, manutenção e custo.
- Ao propor uma dependência, serviço ou fornecedor, avaliar e registrar origem, licença, dependências transitivas e riscos da cadeia de suprimentos.
- Não afirmar que o projeto é "100% brasileiro", nem usar expressão equivalente, sem evidência auditável de origem de código, dependências, infraestrutura e serviços.

## 7. Forma de trabalho

- Consultar o estado atual da `main` e das PRs antes de alterar qualquer coisa.
- Não criar PRs adicionais nem ampliar o escopo aprovado sem autorização explícita do mantenedor; se surgir uma necessidade adjacente, descrevê-la e aguardar decisão.
- Uma PR por tarefa coerente, com objetivo, alterações, limites e evidência (testes executados e checks do SHA exato).
- Distinguir sempre fato verificado, inferência e hipótese.
- Não declarar uma tarefa concluída sem a evidência correspondente.
