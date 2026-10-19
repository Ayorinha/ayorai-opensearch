Revisão por ferramenta automatizada, publicada pelo mantenedor.

# Auditoria do Documento Técnico Público — v1.0 → v1.1

- **Documento auditado:** versão v1.0 do PDF, adicionada no commit `9be3a38` e substituída pela v1.1; o arquivo original continua acessível no histórico do repositório.
- **Versão revisada:** `docs/institutional/AYORAI-ATTRACTOR-Documento-Tecnico-v1.1.pdf`.
- **Base de conferência:** `main` no commit `ae44c2380d07635966ba036563681f151cd5a937` (18/10/2026).
- **Data da auditoria:** 18/10/2026.
- **Escopo:** somente documentação. Nenhum código, regra, Golden, manifesto, hash, pré-registro, ADR ou release foi alterado.

## 1. Método

1. Leitura do código que implementa cada afirmação técnica do documento: `api/app.py`, `api/auth.py`, `verification/api_models.py`, `verification/models.py`, `verification/clusters.py`, `verification/judge2/gates.py`, `verification/judge2/adjudication.py`, `verification/nli.py`, `replay_store.py`, `auditlog/`.
2. Conferência dos números contra `docs/eval/F1-RESULTS.md`, `docs/eval/F1.2-RESULTS.md`, `docs/eval/PREREGISTRATION-RGC-v1.md`, `docs/eval/PROTOCOL-GOLDEN-V1.md` (Emenda 5), `docs/legal/MODEL-LICENSE-POLICY.md`, `docs/legal/PRIOR-IP-RECORD.md` e `docs/STATUS.md`.
3. Execução do exemplo do capítulo 6 na rota `POST /v1/verify` (r2-a), com `TestClient` e autenticação desligada apenas no ambiente local de teste.
4. Execução da suíte de testes e consulta dos check-runs do GitHub Actions no mesmo SHA.
5. Consulta das fontes oficiais citadas (CNJ, Anatel, Planalto, Câmara dos Deputados) em 18/10/2026.

## 2. Achados

Classificação: **E** = erro comprovado; **P** = afirmação que precisava de delimitação ou de evidência adicional; **Ed** = melhoria editorial. Gravidade: Alta, Média, Baixa.

| # | Tipo | Gravidade | Trecho da v1.0 | Evidência | Correção na v1.1 |
|---|---|---|---|---|---|
| 1 | E | Alta | Cap. 14: “com n = 30, uma melhora pareada significativa sobre 43,33% (p < 0,05) exigiria cerca de 60% de acurácia”. | Cálculo exato (seção 3): 18/30 = 60% dá p = 0,0625 mesmo no melhor arranjo. Mínimo possível: 19/30 (63,3%), só se o sistema acertar todos os casos que a baseline acerta; pior arranjo: 24/30 (80%). | Afirmação substituída pela derivação, com a observação de que a significância depende dos pares discordantes. |
| 2 | E | Alta | Cap. 9: exemplo de requisição com `claims[]`, `source_texts` como lista, `start`/`end`, stance sem `id`. | `Judge2VerificationRequest` em `verification/api_models.py`: uma afirmação por requisição (`claim_id`, `claim_text`), `atoms` com `text`, `source_texts` como objeto, evidências com `claim_id`, `source_location`, `retrieved_at`, `start_offset`, `end_offset`, `origin_id` ou `canonical_url`; stances com `id`. | Exemplo reescrito com os campos reais. |
| 3 | P | Alta | Cap. 1: “dada a mesma entrada e a mesma versão das regras, o resultado é sempre o mesmo, byte a byte”. | O determinismo testado (T7, `tests/verification/test_judge2_canonical_output.py`) é do Judge 2.0 sobre entrada estruturada. Extração, NLI e tradução dependem de modelos. | Garantia delimitada ao Judge e ao contrato r2-a; pipeline completo descrito como dependente de versões fixadas. |
| 4 | P | Alta | Cap. 14: tabela Golden sem indicar regras nem versão. | `F1-RESULTS.md`: medição no commit `c4b73f4` com Judge 1.x (seis estados, incluindo VERIFIED). `F1.2-RESULTS.md`: caminho C mede 23,33% no Golden v0 com o código atual (26,67% era do commit `c4b73f4`). | Tabela rotulada (Judge 1.x, commit, Golden v0.1 via E1), IC95% incluídos, nota sobre o caminho C. Valores históricos preservados. |
| 5 | E | Média | Cap. 6, etapa 2: “o Judge se abstém” quando a afirmação está fora de escopo etc. | `gates.py`, `_abstention_codes`: os motivos vêm de sinalizadores booleanos enviados pelo chamador (`out_of_scope`, `factual_claim`, `temporal_anchor_present`, `retrieval_succeeded`, `evidence_pool_integrity_ok`). | Texto corrigido; a figura 4 passou a dizer “sinalizadores do chamador”. |
| 6 | E | Média | Cap. 6, etapa 4: três motivos de rejeição. | `IMPLEMENTED_E_REJECTIONS` inclui `SOURCE_UNAVAILABLE`. Evidência sem stance para o átomo é rejeitada como `NEUTRAL_STANCE`. | Motivo acrescentado; avaliação por par evidência × átomo explicada. |
| 7 | E | Média | Cap. 6, etapa 1: `NO_ATOMS` = “afirmação composta sem átomos”. | `_validate_g1`: qualquer requisição r2-a sem átomos é rejeitada; o texto do átomo deve coincidir com o trecho declarado. | Descrições de `NO_ATOMS` e `ATOM_SPAN_OUT_OF_RANGE` corrigidas. |
| 8 | P | Média | Cap. 6, etapa 5 e figura 5: evidência “sem metadados” como UNKNOWN; clusters chamados de “independentes”. | `Evidence` exige `origin_id` ou `canonical_url`. `clusters.py` separa evidências sem dependência conhecida; isso não prova independência. | Figura 5 e texto refeitos: clusters distintos = nenhuma dependência detectada. |
| 9 | P | Média | Cap. 6, etapa 7: escala R0–R3 sem explicação. | `adjudication.py`, `_robustness`: R2/R3 dependem de `provenance_complete`, declarado pelo chamador, com padrão `true`. | Nota explicando a ordem (R2 entre R1 e R3 por informação incompleta) e a dependência do campo declarado. Contrato não alterado (ver seção 5). |
| 10 | Ed | Média | Cap. 6: exemplo ilustrativo com offsets inventados. | Exemplo executado na API em `ae44c23`: `DECIDED`, `REFUTED` por `2.0.0/K1`, átomos `2.0.0/A2` e `2.0.0/A3`, robustez R1, `output_sha256 = a1a38fe0…a4c5c6`, igual em duas execuções. | Exemplo substituído pela execução real. |
| 11 | E | Média | Cap. 11: paráfrase do art. 27 da Res. CNJ 615 como “controle de versão e registros de auditoria para preservar integridade e rastreabilidade dos dados”, ligada a regras do Judge. | Texto oficial: o caput trata de impedir a alteração dos dados recebidos antes do uso no desenvolvimento de soluções de IA (datasets), por controle de versões, tokens e registros. | Paráfrase corrigida; relação descrita como analogia de prática, não obrigação. |
| 12 | P | Média | Cap. 11: art. 21, §2º, como “produtos de IA identificados nos logs” ligados ao “registro previsto na ADR-010”. | Texto oficial: produtos gerados por IA devem registrar o uso de IA nos logs, com rótulos, para estatística, monitoramento e auditoria. ADR-010 não está implantada. | Redação ajustada para “aplicação potencial”. |
| 13 | P | Média | Cap. 11: sem menção a alterações da Res. CNJ 615. | Res. CNJ 674/2026 alterou o art. 15 (composição do comitê), não citado no documento. | Nota acrescentada. |
| 14 | P | Média | Cap. 10: RGC sem situação de vigência. | Página oficial da Anatel (atualizada em 06/07/2026): vigência principal desde 01/09/2025, exceções do Acórdão nº 228/2024, arts. 2º a 79 revogados pela Res. 777/2025. | Nota de vigência com data de consulta; benchmark não interpreta vigência. |
| 15 | P | Média | Cap. 5, 13 e 16: “autenticação fechada por padrão”. | `api/auth.py`: modo `api_key` por padrão, falha fechada se mal configurado, desligável por `ATTRACTOR_AUTH_MODE=off`; `/health` público; limite de corpo configurável; sem rate limiting nem TLS próprio. | Controles e ausências descritos; serviço não descrito como pronto para produção. |
| 16 | P | Média | Cap. 14: protocolo RGC sem baseline primária nem critério primário. | `PREREGISTRATION-RGC-v1.md` §4–5 e Emenda 5 / DEC-014. | Baseline B (partição pública de 70%), critério primário de três condições, kappa entre dois anotadores, estado PROPOSTO, execução única. |
| 17 | E | Baixa | Cap. 7: caminho B “EVAL_ONLY”. | `MODEL-LICENSE-POLICY.md`: tradução EVAL_ONLY por precaução; NLI de B COMMERCIAL_DEFAULT. | Linha corrigida. |
| 18 | P | Baixa | Cap. 12: “o núcleo executa sem rede (T9)”. | T9 cobre a adjudicação do Judge 2.0. | “O Judge 2.0 executa sem acesso à rede”. |
| 19 | P | Baixa | Cap. 4: “testes AST bloqueiam outros módulos”. | `TRACEABILITY-MASTER.md`: as guardas AST restringem, mas não provam todo comportamento em execução. | Redação ajustada. |
| 20 | P | Baixa | Cap. 18: “o autor permanece titular dos direitos”; documentação “licenciada”. | `LICENSE`, `NOTICE`, `TRADEMARKS.md`, `CONTRIBUTING.md` (DCO), `PRIOR-IP-RECORD.md` (sem pedido no INPI). | Titularidade de contribuições de terceiros, seção 4(d), ausência de registro de marca e aviso de que não é parecer jurídico. |
| 21 | P | Baixa | Cap. 2: frase sobre o que “Anderson identificou”. | Não havia fonte no repositório para a formulação. | Reescrita com base em `docs/INVESTIDORES.md`. |
| 22 | Ed | Baixa | Indicadores: “800+ commits”, “1.057 testes” sem SHA, “4 releases com DOI”. | API do GitHub: 903 commits na `main` em 18/10/2026; releases v0.1.0 a v0.5.0 e baseline-legacy-v0; DOIs de v0.2.0 a v0.5.0 e do baseline. | Números com SHA e data; DOIs nomeados. |

## 3. Cálculo estatístico (achado 1)

Teste exato de McNemar bilateral. A baseline de classe majoritária acerta m = 13 de n = 30 casos. Para um sistema com k acertos e sobreposição o com os acertos da baseline, os pares discordantes são b = k − o e c = 13 − o, e p = min(1, 2·P[Bin(b+c, 1/2) ≤ min(b, c)]).

```python
from math import comb


def exact_mcnemar(b, c):
    n = b + c
    if n == 0:
        return 1.0
    return min(1.0, 2 * sum(comb(n, i) for i in range(min(b, c) + 1)) / 2**n)


n, m = 30, 13
for k in range(m, n + 1):
    best = exact_mcnemar(k - min(k, m), m - min(k, m))
    worst = exact_mcnemar(k - max(0, k + m - n), m - max(0, k + m - n))
    print(k, round(k / n, 4), round(best, 4), round(worst, 4))
```

Resultado relevante:

| Acertos | Acurácia | p (melhor arranjo) | p (pior arranjo) |
|---|---|---|---|
| 18/30 | 60,00% | 0,0625 | 0,4583 |
| 19/30 | 63,33% | 0,0312 | 0,3449 |
| 24/30 | 80,00% | 0,0010 | 0,0347 |

A mesma afirmação de “aproximadamente 60%” aparece em `docs/adr/ADR-005-hybrid-multilingual-stance.md` e em `docs/eval/F1-RESULTS.md`. Esses arquivos são registros aceitos e não foram alterados (ver seção 5).

## 4. Testes e verificações executados

| Verificação | Resultado |
|---|---|
| `pytest` no commit `ae44c23` (Python 3.13, ambiente local) | 1.057 aprovados, 1 falha: `tests/test_namespace.py::test_official_sdk_namespaces_are_not_shadowed`, porque o Python do Debian instala pacotes em `dist-packages` e o teste espera `site-packages`. |
| Check-runs do GitHub Actions no commit `ae44c23` | Todos concluídos com sucesso, incluindo `test (3.11)`, `test (3.12)`, `test (3.13)`, `golden-regression`, `judge-regression`, `security`, `namespace-compatibility`, `analyze`; `rgc-design-simulation` pulado por desenho. |
| Check-runs no commit `9be3a38` (PR do PDF v1.0) | Todos concluídos com sucesso. |
| Exemplo do capítulo 6 em `POST /v1/verify` (r2-a) | HTTP 200, `DECIDED`, `REFUTED` (`2.0.0/K1`), mesmo `output_sha256` em duas execuções. |
| Busca por menções a ferramentas no PDF v1.1 | Nenhuma ocorrência. |

## 5. Pontos abertos que exigem decisão do mantenedor

Este inventário registra os pontos identificados na primeira revisão. O estado atualizado está indicado em cada item abaixo e nas seções 7–9; os itens não devem ser considerados pendentes sem consultar essas atualizações.

1. **ADR-005 e `F1-RESULTS.md` — resolvido documentalmente.** As notas E6 datadas foram acrescentadas aos dois arquivos, preservando os registros históricos e esclarecendo que acurácia isolada não estabelece significância. Ver seção 7.
2. **`README.md` — divergência não reproduzida na branch examinada.** A seção 7 registra que a versão consultada não contém os valores ou a afirmação apontados no achado. Não foi feita alteração; reavaliar somente se o conteúdo relevante reaparecer.
3. **Semântica de robustez (achados 8 e 9).** R3 depende de `provenance_complete`, declarado pelo chamador e com padrão `true`; clusters distintos significam apenas ausência de dependência detectada. Proposta para avaliação em ADR: tornar `provenance_complete` obrigatório no r2-a, ou derivá-lo dos critérios da ADR-006 §2, e registrar a justificativa da ordem R1 < R2 < R3. Qualquer mudança exige nova versão das regras.
4. **Origem do projeto (capítulo 2).** O relato pessoal do autor não está documentado no repositório; pode ser acrescentado pelo autor numa revisão futura.
5. **CPC art. 369 e CPP arts. 158-A a 158-F.** As páginas do Planalto vieram truncadas no acesso desta revisão; os dispositivos devem ser conferidos no texto oficial antes de qualquer uso jurídico do documento.
6. **Descrição da PR.** A descrição da PR deve refletir o estado final do PDF e da auditoria; a descrição será reconciliada com os dados registrados na seção 9.
7. **DCO.** Os commits desta PR não têm linha `Signed-off-by`; cabe ao mantenedor decidir se a regra se aplica aos próprios commits.

## 6. Recomendação

**Pronto para revisão final do mantenedor, com ressalvas.** A v1.1 corrige os erros documentais identificados e delimita afirmações dependentes de contexto. A nota estatística foi propagada para os registros Markdown conforme a seção 7. A conferência jurídica continua exigindo validação humana antes de qualquer uso jurídico. As limitações de proveniência, a fonte de geração não versionada e a situação do DCO permanecem explicitamente registradas.


## 7. Acompanhamento após a auditoria — 18/10/2026

- **Correção estatística documental:** foram acrescentadas notas datadas E6 em `docs/adr/ADR-005-hybrid-multilingual-stance.md` e `docs/eval/F1-RESULTS.md`. Elas preservam os registros históricos e esclarecem que a significância do teste exato bilateral de McNemar depende dos pares discordantes; acurácia isolada não basta.
- **Referências jurídicas:** conferidas em fontes oficiais do Planalto em 18/10/2026: CPC, Lei nº 13.105/2015, art. 369 (`https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2015/lei/l13105.htm`) e CPP, Decreto-Lei nº 3.689/1941, arts. 158-A a 158-F (`https://www.planalto.gov.br/ccivil_03/decreto-lei/del3689compilado.htm`). A conferência confirma o texto dos dispositivos citados, não constitui parecer jurídico nem valida qualquer conclusão jurídica aplicada ao projeto.
- **README e caminho C:** a versão de `README.md` consultada nesta branch não contém atualmente os valores 26,67% ou 23,33% nem a afirmação específica identificada no achado 2 da seção 5. Por isso, nenhuma alteração foi feita no README; a divergência permanece registrada como item a reavaliar se a versão do arquivo mudar.
- **Robustez / provenance:** não foi alterado o contrato r2-a nem a regra do Judge. Tornar `provenance_complete` obrigatório ou derivado é uma decisão de desenho que exige ADR, testes e versionamento explícito; não deve ser feito silenciosamente em uma PR documental.
- **Narrativa pessoal:** não foi inventado nem acrescentado relato autobiográfico. O mantenedor poderá editar esse trecho se quiser acrescentar fatos em primeira pessoa.
- **PDF v1.1 — registro histórico:** no momento em que esta seção foi escrita, o PDF ainda não havia sido regenerado. Essa pendência foi resolvida pela regeneração documentada na seção 8; a seção 8 prevalece sobre esta observação temporal.

## 8. Regeneração do PDF v1.1 — revisão de acompanhamento, 18/10/2026

Esta seção registra a regeneração do PDF pendente desde a seção 7. Nenhum código, regra do Judge, Golden, manifesto, hash congelado, pré-registro, ADR, captura de fonte ou release foi alterado. Os valores históricos (Golden v0 e v0.1, `output_sha256` do exemplo, contagens de testes e commits) foram preservados sem recálculo.

### 8.1 Identificação da versão revisada

| Item | Valor |
|---|---|
| Arquivo | `docs/institutional/AYORAI-ATTRACTOR-Documento-Tecnico-v1.1.pdf` |
| SHA-256 do PDF final | `468e471ce8be3efd18edcf0ec03d3478b7fdd75a907ad836d9cd99d730a40b44` |
| Tamanho e páginas | 498.841 bytes; 31 páginas A4; PDF 1.7 |
| PDF substituído | SHA-256 `8f42f46005c079d439b0172bb57a6cb3907d707f6a2a8a18e7eeb4d8101a63ac` (446.845 bytes, 37 páginas), do commit `5425162`/`93ef9b9`; continua acessível no histórico |
| Base de conteúdo | `main` em `ae44c2380d07635966ba036563681f151cd5a937` (inalterada em 18/10/2026) e branch `docs/documento-tecnico-pdf` em `6d3d7b4a9253668dba95f93d6c60effede11fc4b` |
| Geração | HTML e CSS próprios renderizados com WeasyPrint 70.0 (pydyf 0.13.0, fontTools 4.65.0), fontes Inter e DejaVu Sans Mono embutidas, as mesmas da versão anterior |
| Fonte HTML usada na geração | SHA-256 `0f4272609bdd22030ff3687835f7e4715fd1c3e8422bf6c965af0cc2db5782e5`; não incluída no repositório (ver 8.7) |
| Imagem da marca d'água | logotipo AYORAI ATTRACTOR fornecido pelo mantenedor, SHA-256 `f69f8f24cdb0494e9af22b29b3650036d9474dca80e113fc45c355efa7903611` |

O arquivo-fonte em HTML da v1.0/v1.1 original não estava no repositório; o documento foi reconstruído a partir do texto extraído do PDF anterior e da inspeção visual das páginas, mantendo a capa, a paleta, a tipografia, a ordem dos 20 capítulos, as 13 figuras, as tabelas e os selos de estado. Duas gerações sucessivas a partir da mesma fonte produzem texto idêntico (`pdftotext`), mas não bytes idênticos, porque o subconjunto das fontes embutidas varia entre execuções. Por isso, o SHA-256 acima identifica este arquivo publicado, e não uma compilação reproduzível byte a byte.

### 8.2 Alterações no PDF

| # | Local | Alteração | Fonte de conferência |
|---|---|---|---|
| R1 | Cap. 14 | Nova subseção sobre o teste exato bilateral de McNemar: definição dos pares discordantes b e c, fórmula, tabela 18/30, 19/30 e 24/30 com melhor e pior arranjo, e caixa de correção da v1.0 que menciona as notas E6. | Seção 3 deste relatório; notas E6 em `docs/adr/ADR-005-hybrid-multilingual-stance.md` e `docs/eval/F1-RESULTS.md` |
| R2 | Cap. 11 e ref. 9–10 | O aviso jurídico deixa de dizer que CPC art. 369 e CPP arts. 158-A a 158-F não foram conferidos e passa a registrar a conferência oficial de 18/10/2026 descrita na seção 7; a URL do CPP passa a ser a do texto compilado. Mantida a ressalva de que não há parecer jurídico nem conformidade. | Seção 7 deste relatório (ver limitação em 8.5) |
| R3 | Cap. 8 | “Falha fechada” e “defesa vem de fora” estavam no presente, como se implantados. Passam a ser desenho proposto da ADR-010 (fase 3), ainda não implantado. | ADR-010, decisão 3 e fase 3; `docs/STATUS.md` |
| R4 | Cap. 1, 8, 15 e fig. 8 e 12 | ADR-010 descrita como “aceita em parte” (decisões 1–4), com decisões 5–7 em aberto, em vez de “decidida”. | ADR-010, linha de status; `docs/STATUS.md` |
| R5 | Cap. 6, fig. 4 e 5, glossário | Etapa 5 renomeada para “Clusters de dependência”; o cluster 1 conta como “1 cluster”, não “1 fonte independente”; acrescentado que vínculos não declarados pelo chamador produzem clusters distintos. Robustez R2/R3 descrita como proveniência “declarada”; incluída a proposta em aberto sobre `provenance_complete`. Diretriz 6 passa a dizer “clusters distintos” em vez de “independentes”. | `verification/clusters.py`, `verification/judge2/adjudication.py` (`_robustness`), `verification/api_models.py` (`provenance_complete: bool = True`), `verification/models.py` (`origin_id` ou `canonical_url`) |
| R6 | Cap. 1, 12, 14 e 16 | Estado do benchmark PT-BR explicitado: piloto 01 concluído e descartado sem execução do sistema; piloto 02 é o próximo passo e só tem ficha em branco; protocolo não congelado; nenhum caso definitivo; nenhum resultado. H1 identificada como hipótese. | `docs/STATUS.md`; `docs/eval/PREREGISTRATION-RGC-v1.md` (nota DEC-011); `docs/eval/PILOT-RGC-02-WORKSHEET.md` |
| R7 | Sumário | Quadro “Como ler” passa a distinguir resultado medido, hipótese, proposta e funcionalidade não implementada; selo PARCIAL explicado. | Pedido do mantenedor |
| R8 | Cap. 2 | A paráfrase de `docs/INVESTIDORES.md` incluía “perante um auditor, um perito ou um juiz”, que não está na fonte. Passa a reproduzir a crítica registrada (linha 68) e atribui a exigência de reprodutibilidade às ADR-002 e ADR-009. | `docs/INVESTIDORES.md`, linha 68 |
| R9 | Cap. 12 e ref. 20 | Removida a referência 20 (página comercial de comparação entre dois fornecedores), que não era citada no texto e não sustentava a frase sobre provedores. A frase passou a indicar que é contexto geral de mercado não avaliado pelo projeto. Acrescentadas chamadas [6], [8] e [12] às referências já listadas. “Já exige” sobre a Res. CNJ 615 trocado por “trata de”. | Inspeção contra publicidade (8.4) |
| R10 | Cap. 7 | Caminho A: indicada a licença CC BY-NC 4.0 do XNLI; caminho B: a restrição EVAL_ONLY é operacional, não constatação de licença NC; recomendação de revisão por especialista atribuída à política e à ADR-005. | `docs/legal/MODEL-LICENSE-POLICY.md`; nota E5 de `docs/eval/F1-RESULTS.md` |
| R11 | Cap. 9 e 10 | Recibo e prova de inclusão do `/v1/verify` e “recibo juntável aos autos” marcados como proposta dependente da ADR-010. Exemplo de requisição indicado como abreviado. | ADR-010 |
| R12 | Cap. 14 | Resultados Golden rotulados como “medidos e históricos”, sem recálculo. | `docs/eval/F1-RESULTS.md`; `docs/eval/F1.2-RESULTS.md` |
| R13 | Cap. 20 | Descrição do `README.md` atualizada (não contém mais “evidências v0.3.0”); acrescentados `MODEL-LICENSE-POLICY.md`, `F1-RESULTS.md` e este relatório; lista de ADRs corrigida para os arquivos existentes (ADR-002 a ADR-006, ADR-009 e ADR-010). | Árvore do repositório em `6d3d7b4` |
| R14 | Paginação | A v1.1 anterior tinha uma página com duas linhas (pág. 22) e outras quase vazias. Nenhuma página da nova versão tem menos de um terço de conteúdo, salvo finais de capítulo. Capítulo 19 renomeado para “Glossário e histórico de revisões”. | Inspeção visual e `pdftotext` |
| R15 | Todas as páginas | Marca d'água com o logotipo do projeto, centrada, em azul-marinho com opacidade de cerca de 8,5% nas páginas internas e em branco com cerca de 15% na capa; desenhada atrás do conteúdo, com fundos de tabelas e quadros semitransparentes para não encobri-la. | Pedido do mantenedor |
| R16 | Cap. 19 e 20 | Histórico de revisões e nota final atualizados com esta regeneração e com a nova execução da suíte de testes. | Seção 8.3 |

Divergências entre o PDF anterior e os Markdown que foram corrigidas: R1 (o PDF não citava as notas E6), R2 (o PDF dizia que CPC e CPP não haviam sido conferidos, ao contrário da seção 7), R3, R4 e R8.

### 8.3 Verificações executadas

| Verificação | Resultado |
|---|---|
| Estado da PR #267 (API REST do GitHub) | Na verificação registrada à época, aberta e não mesclada, base `main`, cabeça `6d3d7b4`. O estado mais recente é registrado na seção 9. |
| Check-runs do commit `6d3d7b4` | 19 concluídos com sucesso (incluindo `test (3.11)`, `test (3.12)`, `test (3.13)`, `golden-regression`, `judge-regression`, `security`, CodeQL, Schemathesis e OpenAPI); `rgc-design-simulation` pulado por desenho. |
| `pytest -q` em `6d3d7b4`, Python 3.13.16, ambiente virtual local | 1.058 testes aprovados, nenhuma falha. A falha de ambiente registrada na seção 4 (`dist-packages`) não ocorre em ambiente virtual. |
| Afirmações técnicas contra o código | Conferidos: autoridade do Judge e teste T7 (`tests/verification/test_judge2_canonical_output.py`), T9 sem rede, `provenance_complete` com padrão `true`, exigência de `origin_id` ou `canonical_url`, predicados de robustez, licenças dos caminhos A e B, comandos `search` e `eval` da CLI, estado da ADR-010, DEC-013, DEC-014, piloto 02, 903 commits na `main`, datas das releases e DOIs. |
| Abertura e integridade do PDF | `pdfinfo`, `qpdf --check` (sem erros de sintaxe ou de stream) e `pypdf` abrem o arquivo; 31 páginas; fontes embutidas. |
| Extração de texto | `pdftotext` em todas as páginas: nenhuma página vazia, nenhum caractere U+FFFD ou de controle. |
| Links internos | 60 links do sumário e de referências internas; todos resolvem para destinos existentes. As URLs externas são texto, como na versão anterior. |
| Marca d'água | Presente nas 31 páginas (`pdfimages -list`). |
| Correções incorporadas | Busca no texto extraído pelos trechos das correções R1–R6 e pelo `output_sha256` do exemplo: todos presentes. |
| Comparação com a versão anterior | Comparação frase a frase do texto extraído; as diferenças correspondem às alterações listadas em 8.2 ou a mudanças de quebra de linha e de layout de tabelas. |

### 8.4 Inspeção contra publicidade e propaganda de cloud

Busca, sem distinção de maiúsculas, no texto extraído do PDF final pelos termos: nuvem, cloud, AWS, Amazon, Azure, Microsoft, Google, Oracle, IBM, Vectara, Cleanlab, rfp.wiki, Anthropic, Claude, OpenAI, ChatGPT, Gemini, Copilot, Hugging, patrocín, parceri, oferta, desconto, gratuit, assine, compre e WeasyPrint.

- Nenhuma ocorrência de provedor de cloud, de fornecedor de modelo ou da ferramenta usada para gerar ou revisar o documento, nem de linguagem de oferta ou chamada comercial.
- “nuvem”: uma ocorrência, na frase neutra do capítulo 12 sobre recursos semelhantes de grandes provedores, sem nomes nem recomendação.
- “parceri”: duas ocorrências, ambas negando parceria.
- Removida a referência comercial rfp.wiki (R9).
- Permanecem, por serem dependências reais ou dados de proveniência descritos de forma neutra: GitHub e GitHub Actions, Dependabot, CodeQL, Bandit, Zenodo (DOI), FastAPI, Typer, Uvicorn e SQLite.
- Os metadados do PDF contêm o campo técnico padrão `Producer: WeasyPrint 70.0`, gravado automaticamente pelo gerador; não é conteúdo visível nem promocional e foi mantido por proveniência.

Resultado: o PDF não contém publicidade nem propaganda de cloud.

### 8.5 Limitações que continuam abertas

1. **CPC art. 369 e CPP arts. 158-A a 158-F.** Nesta revisão, as páginas do Planalto voltaram truncadas pela ferramenta de leitura e o acesso direto foi bloqueado pela rede do ambiente; só os textos iniciais dos arts. 77, 79, 80 e 81 do CPC foram lidos no texto oficial. O PDF registra a conferência com base na seção 7; esta revisão não a refez de forma independente. Recomenda-se nova conferência humana antes de uso jurídico.
2. **Semântica de robustez e clusters.** `provenance_complete` continua declarado pelo chamador e com padrão `true`; clusters distintos continuam significando apenas ausência de dependência detectada. Qualquer mudança exige ADR e nova versão das regras (seção 5, item 3).
3. **Contexto de mercado no capítulo 12.** A frase sobre plataformas comerciais e provedores de nuvem ficou sem fonte específica após a remoção da referência comercial; está marcada no texto como contexto não avaliado.
4. **Narrativa pessoal (capítulo 2)** e **DCO dos commits** continuam como na seção 5, itens 4 e 7.
5. **Indicadores históricos.** “1.057 testes”, “~9,0 mil” e “~10,1 mil linhas” e os 823/813/7 commits de 13/10/2026 foram preservados da v1.1 e não recalculados nesta revisão.

### 8.6 Divergências não resolvidas

- A seção 7 afirma conferência oficial do CPC e do CPP que esta revisão não conseguiu reproduzir (8.5, item 1).
- A descrição da PR #267 foi revisada para refletir o PDF regenerado, o hash publicado e as ressalvas documentais; consulte a seção 9 para o estado final verificado.

### 8.7 Decisões para o mantenedor

- **Fonte do PDF.** Para regenerações futuras reproduzíveis, a fonte HTML e as imagens da marca d'água podem ser acrescentadas ao repositório (por exemplo, em `docs/institutional/fonte/`). Não foram incluídas porque isso amplia o escopo desta PR.
- **Merge.** A PR continua aberta e sem merge; a decisão é exclusiva do mantenedor.


## 9. Reconciliação final e estado da PR — 18/10/2026

Esta seção atualiza os registros operacionais anteriores, que foram escritos em momentos diferentes durante a revisão. Em caso de conflito temporal, esta seção e a identificação do artefato na seção 8 prevalecem sobre observações anteriores.

### 9.1 Artefato publicado na branch

- **PDF:** `docs/institutional/AYORAI-ATTRACTOR-Documento-Tecnico-v1.1.pdf`.
- **SHA-256 registrado:** `468e471ce8be3efd18edcf0ec03d3478b7fdd75a907ad836d9cd99d730a40b44`.
- **Formato registrado:** PDF 1.7, A4, 31 páginas.
- **Estado documental:** a seção 8 registra abertura, validação estrutural, extração de texto, links internos, presença da marca d'água e inspeção contra publicidade. Essas verificações são as relatadas pelo executor da regeneração; não devem ser descritas como auditoria jurídica independente.
- **Fonte de geração:** o HTML e os recursos de origem não foram incluídos nesta PR. Isso limita a reprodutibilidade da geração; a fonte pode ser adicionada em alteração futura, com decisão explícita de escopo.

### 9.2 Estado do repositório e dos checks

Na consulta ao GitHub que motivou esta atualização, a PR #267 estava aberta, não mesclada, com base `main` e HEAD `6d4770236ec64d9e4059d1ad61ac6e2a2f60e7f5`. Os workflows associados a esse SHA foram consultados e os sete workflows retornados estavam concluídos com sucesso: CI, Security, Dependency Review, CodeQL, Schemathesis Full API Contract, API Contract Guard e Golden r2 Migration. A consulta de status combinado não retornou status individuais; por isso, este relatório não interpreta esse resultado vazio como prova adicional de aprovação. O relatório anterior registra 19 check-runs no SHA anterior `6d3d7b4`, não no HEAD final.

A presente atualização da auditoria e da descrição da PR cria um novo commit e pode alterar o HEAD da PR. Portanto, os resultados dos checks acima **não devem ser atribuídos automaticamente ao novo HEAD**. Antes do merge, confirmar no GitHub que os checks obrigatórios estão concluídos e aprovados para o HEAD mais recente, incluindo os checks de segurança, regressão do Judge, Golden e contrato de API.

### 9.3 Descrição da PR e decisões ainda abertas

A descrição da PR foi alinhada ao PDF regenerado, ao SHA-256 registrado, às limitações jurídicas e à decisão de manter a PR aberta. A PR não deve ser mesclada automaticamente como parte desta atualização.

Permanecem decisões do mantenedor:
1. Se a fonte HTML e os recursos da marca d'água serão arquivados no repositório para futuras regenerações.
2. Se a regra DCO se aplica aos commits desta PR e, em caso afirmativo, qual é o procedimento permitido para regularização sem reescrever indevidamente o histórico.
3. Se haverá revisão humana das referências ao CPC e ao CPP antes de qualquer uso jurídico do PDF. A documentação não é parecer jurídico.
4. Se o contexto de mercado sem fonte específica será mantido como contexto não avaliado ou receberá uma referência verificável em revisão futura.

### 9.4 Conclusão operacional

O PDF v1.1 foi registrado como regenerado e validado pelo executor, e o SHA-256 acima identifica o arquivo informado como publicado. A auditoria documental explicita limitações, não reivindica resultados de benchmark PT-BR, certificações ou parcerias inexistentes e registra a ausência de publicidade promocional no conteúdo verificado. A PR deve permanecer aberta até que os checks do HEAD final sejam confirmados e o mantenedor conclua as decisões pendentes. Nenhum merge, tag ou release é autorizado por esta seção.
