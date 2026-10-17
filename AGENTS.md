# Regras para agentes automatizados — AYORAI ATTRACTOR

Este arquivo estabelece limites para agentes automatizados que contribuam com este repositório. As seções 2, 3, 4 e 7 também orientam colaboradores humanos, conforme `CONTRIBUTING.md`, sem restringir as atribuições do mantenedor. As proibições operacionais dirigidas a agentes automatizados nas seções 1 e 5 não impedem decisões e atividades humanas autorizadas; a governança do benchmark continua sujeita ao protocolo e às decisões aprovadas.

## 1. Autoridade

- Anderson Leon Ayora, mantenedor, é a única autoridade sobre merges, releases, tags, publicações e decisões metodológicas ou de governança.
- Agentes automatizados não mesclam PRs, não fecham PRs de terceiros, não criam tags nem publicam versões.
- Parar e pedir decisão do mantenedor quando a tarefa exigir decisão humana, anotação isolada, congelamento de protocolo, mudança de contrato, mudança de escopo ou autorização de merge.

## 2. Identidade do projeto e proibição de autopromoção

- Não incluir assinaturas, slogans, links de sessão, links comerciais ou créditos promocionais de ferramentas em descrições de PR, documentação, relatórios técnicos ou científicos, CHANGELOG, ADRs, notas de release ou outros materiais públicos do projeto.
- O protagonismo público é do projeto, de sua finalidade técnica, de suas evidências e de seus responsáveis.
- Citar uma ferramenta, fornecedor ou serviço apenas quando for necessário para proveniência científica, reprodutibilidade, segurança ou auditoria, de forma objetiva e proporcional.

## 3. Autoria, proveniência e histórico

As contribuições podem ser produzidas com auxílio de ferramentas automatizadas, sob supervisão, revisão e responsabilidade do mantenedor, e são registradas em seu nome. Os documentos científicos declaram esse auxílio, de forma genérica, quando ele for relevante para a proveniência.
- Não reescrever o histórico de commits. Preservar as linhas de coautoria existentes.
- Remover publicidade desnecessária não autoriza apagar evidência: a proveniência técnica relevante deve continuar verificável.
- Em material já publicado (documentos, descrições de PR, registros metodológicos), apresentar o trecho atual e o texto proposto e aguardar autorização antes de alterar.
- Pareceres de revisão produzidos por ferramenta automatizada começam com a linha: 'Revisão por ferramenta automatizada, publicada pelo mantenedor.' Não identificam a ferramenta.

## 4. Artefatos protegidos

Exigem autorização explícita do mantenedor para qualquer alteração:

- regras do Judge (`rules/`, `src/ayorai_attractor/verification/judge2/`);
- conjuntos Golden em `evals/golden/`, manifestos e hashes congelados;
- bytes oficiais capturados e textos derivados em `evals/ptbr/sources/`; registro de fontes em `evals/ptbr/SOURCES-REGISTRY.json`. Preservar capturas históricas e não sobrescrevê-las;
- `docs/eval/PROTOCOL-GOLDEN-V1.md` e `docs/eval/PREREGISTRATION-RGC-v1.md`: alterações somente por emenda datada e aprovada explicitamente pelo mantenedor;
- ADRs aceitas e decisões aprovadas (`docs/DECISIONS-APPROVED.md` e entradas aprovadas de `docs/DECISIONS-PENDING.md`);
- notas de release (`docs/release/`).

Não alterar esses artefatos para fazer testes passarem.

## 5. Benchmark RGC em português

- Agentes automatizados não criam, revisam, veem nem rotulam casos do segundo piloto nem do conjunto definitivo. A criação, revisão, visualização e rotulagem humanas seguem o protocolo e as decisões aprovadas pelo mantenedor.
- Agentes automatizados não executam o sistema sobre casos sem rótulo humano completo, nem sobre o conjunto oculto antes da execução única autorizada.
- Não afirmar benchmark validado, protocolo congelado, parceria, certificação, aprovação ou endosso de qualquer instituição sem evidência verificável.
- Resultados exploratórios nunca são apresentados como confirmatórios.

## 6. Soberania tecnológica

### 6.1 Objetivo

- A soberania tecnológica é um objetivo do projeto: priorizar soluções, serviços e componentes brasileiros quando forem tecnicamente adequados em segurança, qualidade, licença, manutenção e custo.
- Ao propor uma dependência, ferramenta, serviço ou fornecedor, avaliar e registrar origem, licença, dependências transitivas e riscos da cadeia de suprimentos.

### 6.2 Comprovação antes de qualquer declaração

- O projeto não se declara "100% brasileiro", nem usa expressão equivalente, antes de uma auditoria verificável que cubra dependências, ferramentas, infraestrutura e serviços.
- A auditoria deve ser reproduzível e publicada, com inventário de componentes (origem e licença), data e commit de referência, método de verificação e exceções declaradas.
- Enquanto essa auditoria não existir, a soberania tecnológica é comunicada apenas como objetivo.

## 7. Forma de trabalho

- Consultar o estado atual da `main` e das PRs antes de alterar qualquer coisa.
- Não abrir PR, branch pública ou issue que não tenha sido solicitada, nem ampliar o escopo autorizado, sem autorização explícita do mantenedor; se surgir uma necessidade adjacente, descrevê-la e aguardar decisão.
- Uma PR por tarefa coerente, com objetivo, alterações, limites e evidência (testes executados e checks do SHA exato).
- Distinguir sempre fato verificado, inferência e hipótese.
- Não declarar uma tarefa concluída sem a evidência correspondente.
