# Auditoria de cobertura de testes — 2026-11-22

- **Base:** `main` @ `88a519e1ace7c8e2994f9c5cf36eb9e4eadf920d` (merge da #628).
- **Escopo:** cobertura de linhas e branches, o teste ignorado no CI e os componentes críticos das ADR-010, ADR-012 e ADR-013.
- **Limites:** nenhuma mudança de código de produção, regras do Judge, Golden, RGC, thresholds ou benchmarks.

Fato verificado: medido nesta auditoria, com o comando indicado. Inferência: conclusão tirada desses fatos.

## 1. Estado inicial

| Item | CI da `main` (`88a519e1`, job `test (3.12)`) | Reexecução local (Python 3.13) |
|---|---|---|
| Testes | 2.771 aprovados, 1 ignorado | 2.772 aprovados, 0 ignorados |
| Cobertura de linhas | 94% (7.170 instruções, 402 não cobertas) | 94,39% |
| Cobertura de branches | não medida (o CI não usa `--cov-branch`) | 87,07% (1.905 de 2.188) |

Comando local: `pytest -W error::ResourceWarning -W error::pytest.PytestUnraisableExceptionWarning --cov=ayorai_attractor --cov-branch`.

**O gate do CI:** a catraca exige no mínimo 85% de linhas (`.github/coverage-baseline.txt`), mais 90% em `verification/security.py` e 80% em `translation.py` e `nli.py`. Nenhum desses limites cobre os módulos de autenticação, tenant ou trilha.

## 2. O teste ignorado

- **Teste:** `tests/test_source_derived_text.py::test_extraction_is_reproducible_with_same_poppler_version`.
- **Como foi identificado (fato):**
  - no log do CI, a linha com o `s` termina em 75% e tem o `s` na 32ª posição, o que corresponde ao teste de índice 2048 da coleta;
  - o teste de índice 2048 na coleta local é este, e ele é o único com skip dependente de ambiente que roda no Linux.
- **Condição do skip:** `skipif(shutil.which("pdftotext") is None)` ou versão do poppler diferente de 24.02.0.
- **Causa:** o runner `ubuntu-24.04` do GitHub não tem o `poppler-utils` instalado.
- **O que o teste garante:** que o texto derivado das fontes oficiais do RGC (`evals/ptbr/sources/`, artefato protegido) é reproduzido byte a byte a partir dos PDFs capturados.
- **Impacto:** é reprodutibilidade científica, não segurança. A integridade desse texto continua coberta por hash em outros testes, que rodam no CI. A reprodutibilidade da extração, não.
- **Decisão:** o skip fica como está. Ele é legítimo, porque o teste depende de uma ferramenta externa de versão fixa. Em vez de removê-lo, o job `test` do CI passa a instalar o `poppler-utils`, cuja versão no Ubuntu 24.04 é 24.02.0. Localmente, com o poppler 24.02.0, o teste roda e passa.

## 3. Onde está a cobertura ausente

As 402 linhas não cobertas concentram-se assim:

| Classe | Módulos | Linhas não cobertas (antes) | Natureza |
|---|---|---|---|
| Crítica | `auditlog/note.py`, `auditlog/store.py`, `api/keys.py`, `api/auth.py`, `audit_store.py` | 86 | Caminhos de rejeição: assinatura, chave de verificação, adulteração, arquivo de chaves e limite por chave |
| Alta | `verification/judge2/*`, `verification/document_check.py`, `verification/field_check.py` | cerca de 110 | Ramos de validação do Judge 2.0. **Não alterados:** são artefatos protegidos e não podem ser mudados para fazer teste passar |
| Média | `evaluation/international.py`, `evaluation/international_cli.py`, `evaluation/golden.py` | cerca de 85 | Ferramentas de avaliação exploratória e CLI sem teste |
| Baixa | `durable.py`, `hybrid.py`, `observability/tracing.py` e outros | restante | Inicialização, adaptadores opcionais, mensagens de erro de configuração |

### Lacunas críticas encontradas (fato verificado)

1. **`auditlog/note.py` (ADR-010):**
   - 84% das linhas e 69% dos branches cobertos;
   - sem teste: chave de verificação malformada, hash de chave que não confere, nota sem bloco de assinatura, linha de assinatura com prefixo errado ou base64 inválido, corpo de checkpoint malformado e entradas inválidas do assinador.
   - O caminho de aceitação já era cruzado com a referência em Go; os de rejeição não tinham teste.
2. **`auditlog/store.py` (ADR-010):**
   - os testes de adulteração mexiam num banco fechado, e a adulteração era pega na reabertura (`LogCorruption`);
   - as verificações do `verify_log()` com o log aberto nunca eram executadas: folha com hash divergente, lacuna na sequência, raiz do checkpoint diferente da árvore, folha que não é JSON e folha de apagamento apontando para evento inválido;
   - também sem teste: apagamento que falha no meio e recibo de folha de apagamento.
3. **`api/auth.py` (ADR-012):** o limite de requisições por chave autenticada (429) nunca era atingido em teste. O limite por IP sempre disparava antes.
4. **`api/keys.py` (ADR-012):** sem teste: arquivo apagado depois da subida, documento sem a estrutura esperada, `revoked_by` inválido, intervalo de recarga inválido, e falhas da ferramenta (sem pepper, `id` inválido, falha de gravação).
5. **`audit_store.py`:** sem teste: entrada da cadeia com tipo desconhecido e encadeamento correto, purga com conteúdo ilegível, purga que alega cobrir entradas futuras, versão de replay forjada, rebaixamento para `r2-v1` sem veredito, e checkpoint tirado com o store vazio.
6. **ADR-013:** nenhum teste mostrava que o cliente não consegue escolher o tenant, seja por cabeçalho, por parâmetro de consulta ou por principal enviado.

## 4. Testes adicionados (só testes; nenhum código de produção mudou)

| Arquivo | Testes | O que fixam |
|---|---|---|
| `tests/auditlog/test_note_negative.py` | 42 | Todos os caminhos de rejeição de notas, chaves de verificação e checkpoints; uma assinatura válida entre assinaturas desconhecidas continua valendo |
| `tests/test_verify_log_integrity.py` | 28 | Cada problema do `verify_log()` com o log aberto, nomeado; apagamento atômico (falha no meio não muda nada); apagamento depois de outro escritor; recibos que não podem verificar |
| `tests/test_auth_failure_paths.py` | 31 | Arquivo de chaves apagado mantém o último válido; estrutura e campos inválidos; limite por chave atravessando IPs (429); tenant não escolhível pelo cliente; falhas da ferramenta de chaves sem alterar o arquivo |
| `tests/test_audit_chain_forgery.py` | 18 | Entradas forjadas com encadeamento correto; purgas inválidas; versões de replay forjadas; store selado que se recusa a abrir sem as chaves; checkpoint do store vazio |

**Mudança de CI:** o job `test` passa a instalar o `poppler-utils`.

### Observações sem defeito

- **Registro órfão:** quando uma folha é trocada por outra, com hash recalculado, o registro dela fica órfão e o `verify_log()` não o nomeia individualmente. A adulteração continua detectada pelas raízes assinadas.
- **Contagem de falhas de recarga:** o contador de recarga do arquivo de chaves soma uma falha por tentativa, no máximo uma por intervalo de recarga. É o comportamento previsto, e o alerta usa `increase(...) > 0`.
- **Store selado:** um banco com rastros selados por HMAC se recusa a abrir sem as chaves. Isso é mais forte do que a verificação por rastro: a falha é fechada.

**Nenhum defeito de produção foi encontrado.**

## 5. Resultado (fato verificado, Python 3.13 local)

| Medida | Antes | Depois |
|---|---|---|
| Testes | 2.772 aprovados, 0 ignorados | 2.891 aprovados, 0 ignorados |
| Linhas, global | 94,39% | 95,24% |
| Branches, global | 87,07% | 88,80% |
| Linhas, componentes críticos* | 94,59% | 98,34% |
| Branches, componentes críticos* | 88,75% | 95,54% |

\* `api/auth.py`, `api/keys.py`, `api/verify_log.py`, `auditlog/*`, `audit_store.py`, `tenancy.py` e `tenant.py`.

| Módulo | Linhas | Branches | O que falta e por quê |
|---|---|---|---|
| `auditlog/note.py` | 100% | 100% | — |
| `auditlog/commitment.py` | 100% | 100% | — |
| `api/verify_log.py` | 100% | 100% | — |
| `auditlog/merkle.py` | 99,4% | 98,9% | Validação de tamanho de folha na API interna da árvore incremental |
| `auditlog/store.py` | 99,6% | 96,7% | `backup()` com `integrity_check` falhando: exige corromper a cópia durante a API de backup do SQLite |
| `api/keys.py` | 98,4% | 94,7% | Leitura que falha entre o `stat` e o `read` (corrida); `__main__` |
| `api/auth.py` | 97,6% | 91,9% | Pepper ausente no modo `api_key` (inalcançável: a subida recusa); poda periódica do limitador; cliente sem endereço |
| `audit_store.py` | 97,0% | 95,1% | Rollback depois de exceção do SQLite em retenção e nova selagem; exige falha de disco simulada |
| `tenant.py` / `tenancy.py` | 94–100% | 67–83% | Primitivas do runtime de agentes (R13), fora do caminho HTTP da ADR-013 |

## 6. Pendências

**Problemas reais, fora do escopo autorizado:**
1. Os módulos do Judge 2.0 (`judge2/adjudication.py` com 87% de cobertura de linhas na medição local registrada nesta auditoria; a cobertura de branches desse módulo não foi discriminada aqui, além de `gates.py` e `__init__.py`) têm ramos de validação sem teste. O valor de 90% citado no resumo da revisão não está sustentado por este relatório e não deve ser usado sem uma nova medição reproduzível. Os testes podem ser escritos sem tocar nas regras, mas precisam de casos sintéticos revisados contra a ADR-009. Fica proposto como tarefa própria.
2. `evaluation/international_cli.py` está com 0%. É uma CLI exploratória e pede um teste de fumaça.
3. A catraca de cobertura do CI está em 85% e só mede linhas. Recomendação, que depende de decisão do mantenedor:
   - medir branches (`--cov-branch`);
   - acrescentar um piso por módulo para os componentes críticos, por exemplo 95% de linhas em `auditlog/*`, `api/auth.py`, `api/keys.py` e `audit_store.py`.

**Limitações justificadas:**
- Rollback depois de falha de disco do SQLite.
- Corrida entre `stat` e `read` do arquivo de chaves.
- Linhas inalcançáveis mantidas como defesa em profundidade.

## 7. Parecer

**Boa.** A suíte é ampla e os caminhos de aceitação das três ADRs têm verificação cruzada independente (Go, Docker). Ela não estava excelente antes desta auditoria, porque partes relevantes das defesas criptográficas e de integridade, os caminhos de rejeição, nunca eram executadas. Com os 119 testes acrescentados, os componentes críticos passam a 98% de linhas e 96% de branches, com cada rejeição fixada por nome.

Cobertura não prova segurança criptográfica. As garantias das primitivas continuam vindo da biblioteca `cryptography`, dos vetores públicos e da verificação cruzada com Go.
