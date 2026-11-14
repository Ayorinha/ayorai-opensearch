# [PROPOSTO] Executor de avaliação do benchmark RGC (v1)

**Estado:** [PROPOSTO] — aguarda congelamento pelo mantenedor  
**Data:** 2026-10-13  
**Responsável:** Anderson Leon Ayora  
**Código:** `evals/ptbr/rgc_eval.py` · **Testes:** `tests/test_rgc_eval_runner.py`  
**Relação:** complementa `docs/eval/PREREGISTRATION-RGC-v1.md` (métricas e critérios) e `docs/eval/PROTOCOL-GOLDEN-V1.md` (anotação).

Este documento fixa **como** o sistema será executado sobre os casos do RGC, antes de qualquer execução sobre casos reais. O executor foi testado apenas com documentos e casos **sintéticos**. Nenhum caso do piloto ou do benchmark foi executado.

## 0. Gate obrigatório de congelamento

O subcomando `run` agora falha fechado enquanto o protocolo estiver proposto ou em revisão. Antes de qualquer avaliação (inclusive descritiva), devem existir:

1. `docs/eval/PROTOCOL-GOLDEN-V1.md` com a linha de estado iniciada por `Status: CONGELADO`;
2. `docs/eval/PREREGISTRATION-RGC-v1.md` com `**Estado:** [CONGELADO]`;
3. `docs/eval/RUNNER-RGC-v1.md` com `**Estado:** [CONGELADO]`;
4. `docs/eval/PROTOCOL-FREEZE.json`, aprovado pelo mantenedor, com exatamente estes campos:

```json
{
  "schema_version": 2,
  "status": "FROZEN",
  "approved_by": "Nome do mantenedor que aprovou",
  "approved_at": "AAAA-MM-DD",
  "protocol_sha256": "SHA-256 exato de PROTOCOL-GOLDEN-V1.md",
  "preregistration_sha256": "SHA-256 exato de PREREGISTRATION-RGC-v1.md",
  "runner_spec_sha256": "SHA-256 exato de RUNNER-RGC-v1.md",
  "runner_code_sha256": "SHA-256 exato de evals/ptbr/rgc_eval.py",
  "runner_dependencies_sha256": {
    "evals/ptbr/rgc_agreement.py": "SHA-256 exato",
    "evals/ptbr/rgc_components.py": "SHA-256 exato",
    "evals/ptbr/rgc_ids.py": "SHA-256 exato",
    "evals/ptbr/rgc_random.py": "SHA-256 exato"
  },
  "runner_version": "rgc-eval/versão aprovada"
}
```

A partir de `schema_version` 2, o congelamento vincula também os módulos que decidem números do RGC: concordância, componentes, gramática de IDs e gerador. Antes, uma mudança nesses módulos depois do congelamento passava despercebida, porque só `rgc_eval.py` era conferido. Manifestos com `schema_version` 1 são recusados.

O JSON acima é apenas um esquema ilustrativo, **não** um manifesto válido nem autorização para executar. O manifesto real só deve ser criado depois do piloto humano 02, da revisão dos achados e de uma decisão explícita de congelamento. O executor compara os hashes do manifesto com os arquivos atuais; qualquer alteração posterior no protocolo, pré-registro, especificação ou código do executor bloqueia a execução até nova aprovação e atualização auditável do manifesto.

O relatório registra o hash do manifesto, os hashes dos artefatos vinculados (incluindo os módulos dependentes), a versão do executor, o responsável e a data declarados. Esse mecanismo detecta divergência de artefatos; não substitui a revisão humana nem prova, sozinho, a autenticidade da aprovação. `export-corpus` permanece disponível sem congelamento porque apenas exporta a fonte capturada e não executa o sistema sobre casos.

### 0.0.1 Manifesto de execução (E5)

Cada `run` grava, ao lado do relatório, `<relatório>.manifest.json` (`rgc-run-manifest/1`, JSON com chaves ordenadas). O manifesto contém exatamente:
- versão do executor, commit git, se a árvore de trabalho estava limpa, versão e implementação do Python, versão do pacote, partição e horários de início e fim;
- os hashes das entradas;
- o SHA-256 da configuração em JSON canônico;
- os hashes dos manifestos de congelamento e de aprovação das anotações;
- os hashes do executor e dos módulos dependentes;
- o nome e o SHA-256 exato do relatório.

Exceto `finished_at` e o próprio hash do relatório, todos esses campos também estão gravados no relatório, cujos bytes o manifesto fixa.

**Verificação** (`verify_run_manifest(manifesto, relatório, root=None, input_files=None)`). Recusa, com `ValueError`, qualquer diferença:
- arquivo ausente, ilegível, JSON inválido ou com chave duplicada; schema desconhecido; campo ausente ou a mais;
- tipos e formatos: SHA-256 em 64 hexadecimais minúsculos, commit em 40, `worktree_clean` booleano ou nulo, partição `hidden` ou `development`, horários ISO 8601 em UTC;
- nome e SHA-256 do relatório;
- cada campo gravado no relatório, recalculado e comparado (inclusive o JSON canônico da configuração e os hashes de congelamento, dependências e aprovação);
- partição oculta sem commit ou com árvore alterada, mesmo que manifesto e relatório concordem;
- ordem `started_at ≤ generated_at ≤ finished_at`;
- com `input_files`, o hash de cada arquivo de entrada informado é recalculado;
- com `root`, o executor e os quatro módulos estatísticos do checkout são recalculados e comparados com os hashes congelados registrados no relatório.

**Gravação.** Relatório e manifesto são gravados por arquivo temporário e substituição atômica. Um manifesto anterior com o mesmo nome é removido antes da gravação, e o manifesto recém-gravado é verificado em seguida. Se qualquer passo falhar, o manifesto é removido e a execução termina com código 2 ("RGC run incomplete"). Relatório sem manifesto verificável não é execução concluída.

Na partição oculta, a execução é recusada (código 2) se o commit não puder ser resolvido ou se a árvore de trabalho tiver alterações, porque a execução confirmatória única precisa ser reproduzível a partir de um commit registrado.

**Limites.** O manifesto é registro técnico da execução. Ele não aprova, não congela e não publica nada: a aprovação metodológica está nos manifestos de congelamento e de anotação, e a publicação de resultados é decisão humana separada. SHA-256 dá integridade, não autenticidade: não há assinatura digital, e quem puder reescrever os dois arquivos consegue produzir um par coerente. `finished_at` só é verificado em formato e ordem. O commit é verificado em formato, não em existência num repositório. O manifesto não prova quem executou nem a autenticidade das aprovações.

### 0.1 Gate de concordância e aprovação das anotações

O gate de congelamento não substitui a aprovação do conjunto anotado. Cada execução `run` também exige:

- `--annotation-a` e `--annotation-b`: os dois arquivos de anotação humana independentes, mantidos em diretório privado;
- `--agreement-report`: relatório produzido por `evals/ptbr/rgc_agreement.py`, com Cohen's kappa não ponderado, `gate_passed: true` e hashes dos dois arquivos de anotação humana;
- `--adjudication-record`: registro privado da revisão das divergências e da adjudicação humana;
- `--annotation-approval`: manifesto aprovado pelo mantenedor que vincula o relatório de concordância, o registro de adjudicação, o arquivo exato de casos e o arquivo exato de rótulos finais.

O manifesto de aprovação tem exatamente estes campos:

```json
{
  "schema_version": 1,
  "status": "APPROVED",
  "approved_by": "Nome do mantenedor que aprovou",
  "approved_at": "AAAA-MM-DD",
  "cases_sha256": "SHA-256 do arquivo de casos desta partição",
  "labels_sha256": "SHA-256 do arquivo de rótulos finais adjudicados",
  "development_cases_sha256": "SHA-256 dos casos públicos de desenvolvimento",
  "development_labels_sha256": "SHA-256 dos rótulos públicos de desenvolvimento",
  "agreement_report_sha256": "SHA-256 do relatório de concordância",
  "adjudication_record_sha256": "SHA-256 do registro de adjudicação",
  "annotation_a_sha256": "SHA-256 do arquivo do anotador A registrado no relatório",
  "annotation_b_sha256": "SHA-256 do arquivo do anotador B registrado no relatório",
  "cohen_kappa": 0.6
}
```

Este exemplo é apenas um esquema, não uma aprovação válida. O executor recalcula os hashes dos dois arquivos de anotação e confere-os com o relatório; também valida o gate de concordância, os hashes e a correspondência entre relatório e manifesto. Qualquer alteração nas anotações, casos, rótulos, relatório ou registro de adjudicação exige nova aprovação. Para partições públicas e ocultas, usar manifestos separados, cada um vinculado aos respectivos arquivos de casos e rótulos; o material oculto e os registros completos de anotação permanecem fora do repositório público.

A aprovação é uma declaração auditável, não prova criptográfica da identidade do aprovador. Nenhum caso real, rótulo ou relatório de concordância é criado por esta implementação.

## 1. Salvaguardas

- O subcomando `run` exige um arquivo de rótulos humanos completo (`--labels`). Não existe modo "só previsões"; por isso o sistema não pode ser rodado sobre casos ainda não rotulados, evitando que a saída do sistema influencie a anotação.
- Casos sem rótulo, rótulos de casos inexistentes e casos duplicados interrompem a execução (erro), em vez de serem descartados em silêncio.
- Rótulo `RULE_GAP` (lacuna nas regras de anotação, usado somente no piloto) remove o caso do denominador e é sempre listado em `excluded` no relatório; no conjunto definitivo, `RULE_GAP` é proibido no campo `label`.
- **DEC-017 (Opção A aprovada em 2026-10-21; Emenda 7):** o executor interrompe a execução diante de registro ausente/duplicado, ID desconhecido, rótulo humano ausente ou arquivo inconsistente; uma predição presente não mapeável para `judge2` recebe `INVALID_PREDICTION`, permanece no denominador e conta como erro. A aprovação não autoriza avaliação confirmatória e não congela o protocolo.
- O relatório registra: versão do executor, commit, versão do Python, SHA-256 dos casos, dos rótulos e dos documentos, configuração completa, cada previsão com o `output_sha256` do Judge e a contagem de previsões cujo estado original do Judge foi `ABSTAINED`.

## 2. Pipeline por caso (determinístico, sem rede, sem componente aprendido)

1. **Evidência**
   - **Modo `oracle`**: usa os trechos do próprio caso (`evidence[].excerpt`), conferidos caractere a caractere contra o texto do documento nos offsets declarados. Mede stance + Judge isoladamente, sem recuperação.
   - **Modo `retrieval`**: o texto de `DOCUMENTS.jsonl` é segmentado em dispositivos e os *k* melhores trechos são recuperados por BM25 (§3). Mede o sistema de ponta a ponta.
2. **Stance**: `RuleStanceDetector` (versão registrada no relatório) para cada par (afirmação, trecho).
3. **Veredito**: Judge 2.0 `adjudicate` (ADR-009). Afirmação simples: **um átomo** cobrindo a afirmação inteira. Afirmação composta (DEC-010, opção A): os átomos anotados no campo `atoms` do caso (dois ou mais trechos da afirmação, por `start_offset`/`end_offset`, ordenados e sem sobreposição); a posição é detectada por átomo contra cada trecho, e o veredito composto segue K1–K5. Anotação de átomos inválida interrompe a execução.
4. **Estrato retificado** (Emenda 4, DEC-011 opção A; executor `rgc-eval/0.7.0`): o campo opcional `rectified` do caso deve ser booleano (`true`/`false`); ausência equivale a `false` e qualquer outro valor interrompe a execução. Casos retificados **permanecem** nas métricas primárias e também são reportados em `strata.rectified`; os demais em `strata.not_rectified`. Cada estrato traz `n`, contagens de referência, acurácia, acurácia balanceada, macro-F1, IC95% por bootstrap e matriz de confusão; nenhum critério H1 é decidido por estrato. A marca não entra no Judge: o `output_sha256` de cada caso é idêntico com ou sem o campo.
5. **Mapeamento** (`to_label`): `DECIDED` → veredito do Judge; `ABSTAINED` → `UNVERIFIED` (DEC-009 aprovada); qualquer outro estado → `INVALID_PREDICTION`. No vocabulário histórico `adr002`, `SUPPORTED` com robustez `R3` → `VERIFIED` (ADR-009 §11), mas esse mapeamento não se aplica ao vocabulário RGC `judge2`.

## 3. Parâmetros propostos para congelamento

> **Atualização — 2026-11-14 (Emenda 11, `rgc-eval/0.9.0`):** a tabela reflete a DEC-027. O IC95% primário e o teste de H1 são por componente conectado (DEC-023); o cluster de artigo da DEC-019 e o caso passam a ser sensibilidade. O protocolo continua [PROPOSTO], e nenhuma saída do executor é resultado confirmatório enquanto o protocolo não for congelado e a execução única não for autorizada.

| Parâmetro | Valor proposto | Observação |
|---|---|---|
| Modo da avaliação principal | `retrieval` | `oracle` reportado ao lado, como análise secundária |
| Segmentação | `dispositivo` (início de linha: `Art.`, `§`, `Parágrafo único`, incisos romanos `I -`, alíneas `a)`) | alternativa `artigo` disponível só para análise secundária |
| Recuperação | BM25, `k1 = 1,2`, `b = 0,75`, top-*k* = 3 | empate desfeito pela ordem no corpus |
| Tokenização | `\w+` em minúsculas; mantém números; remove tokens com menos de 3 letras e uma lista fixa de palavras funcionais | nenhuma palavra do domínio na lista |
| Vocabulário | `judge2` (5 estados) | DEC-007 aprovada (5 estados); `adr002` (6 estados) permanece apenas como vocabulário histórico alternativo, não usado no RGC |
| Macro-F1 | média sobre a união dos estados de referência e previstos, **incluindo** `INVALID_PREDICTION` (F1 = 0, escolha conservadora) | |
| Acurácia balanceada | média das revocações dos estados presentes na referência | |
| IC95% primário | bootstrap percentil por componente conectado (DEC-023), 10.000 reamostragens, seed `20261003`, RGC-PRNG-1 `dec023-accuracy-bootstrap`, quantil tipo 7 | DEC-027 D5; Emenda 11 |
| IC95% de sensibilidade | bootstrap por cluster de artigo (DEC-019, `dec019-accuracy-bootstrap`) e por caso (`case-accuracy-bootstrap`) | Reportados separadamente; nunca substituem o primário |
| Baseline B primária | classe majoritária dos rótulos humanos da partição pública de desenvolvimento (70%); aplicada sem alteração à avaliação; empate resolvido pela ordem fixa de `VOCABULARIES["judge2"]` | DEC-014/Emenda 6; `majority_label` em `evals/ptbr/rgc_eval.py`; registrar rótulos, contagens e SHA-256 no relatório |
| Baseline A descritiva | classe majoritária da própria partição avaliada; empate desfeito pela ordem do vocabulário | somente prevalência observada; excluída de H1 |
| Comparação | sign-flip bilateral por componente (DEC-021): enumeração completa para K ≤ 20; para K > 20, 10.000 sorteios RGC-PRNG-1 `dec021-sign-flip` | DEC-027 D4; Emenda 11. McNemar exato e Obuchowski por componente só como sensibilidade |
| Precisão das decisões | as três condições de H1 usam valores **não arredondados**; o arredondamento (6 casas) vale só para o relatório | |

Depois de congelados, qualquer mudança nesses valores exige emenda datada antes de nova execução, conforme o pré-registro §5.

## 4. Exportação do corpus estrito

`python evals/ptbr/rgc_eval.py export-corpus --out <arquivo>` gera o corpus com exatamente os 5 campos aceitos por `scripts/check_golden_pt.py --corpus` (`source_id`, `source_url`, `source_license`, `retrieved_at`, `text`). O teste confirma que o validador aceita a exportação sem erros.

## 5. Limitações conhecidas (declaradas antes dos dados)

- **Átomos anotados, não decompostos automaticamente:** o executor não divide afirmações por conta própria. Sem o campo `atoms`, a afirmação é um único átomo e, pelas regras A1–A4, só pode resultar em `SUPPORTED`, `REFUTED`, `CONFLICTING` ou `UNVERIFIED`. `PARTIALLY_SUPPORTED` (regra K4) só é alcançável quando o caso traz dois ou mais átomos anotados. Por isso, todo caso de referência rotulado `PARTIALLY_SUPPORTED` deve trazer os átomos; a regra de anotação está na Emenda 3 do protocolo (PR #205, mesclada em 2026-10-16). Casos sem `atoms` produzem exatamente o mesmo resultado e o mesmo `output_sha256` da versão anterior do executor. Esta descrição e o executor permanecem **[PROPOSTO]**.
- **Stance lexical:** o `RuleStanceDetector` compara números, datas e sobreposição de palavras; paráfrases fortes e negações implícitas tendem a sair como `NEUTRAL` → `UNVERIFIED`.
- **Dispositivo sem o caput:** um inciso recuperado isoladamente não carrega o texto do caput do artigo.
- **Ruído do DOU:** cabeçalhos e rodapés de página extraídos pelo `pdftotext` ficam anexados ao dispositivo anterior.
- **Uma única origem:** todos os trechos vêm do mesmo ato normativo, portanto a robustez máxima esperada é limitada (`VERIFIED` exige R3 no vocabulário `adr002`).
- **`canonical_url` omitido:** o executor não preenche `canonical_url` nas evidências (a URL fica em `source_location`). Ver §6.

## 6. Achado durante a implementação (fora do escopo deste executor)

Uma requisição `r2-a` válida com `evidence[].canonical_url` preenchido retornava `INVALID_INPUT / SCHEMA_VIOLATION` em vez de ser adjudicada (issue #182). A correção, com testes de regressão, foi mesclada pelo mantenedor na [PR #192](https://github.com/Ayorinha/ayorai-opensearch/pull/192) em 2026-10-15. O executor continua sem preencher `canonical_url` (§5); essa escolha não depende mais do defeito.

## 7. Uso (somente após rótulos completos e parâmetros congelados)

```bash
python evals/ptbr/rgc_eval.py run <casos-avaliacao.jsonl> \
    --labels <rotulos-avaliacao.jsonl> \
    --annotation-a <anotacao-a.jsonl> --annotation-b <anotacao-b.jsonl> \
    --agreement-report <relatorio-concordancia.json> \
    --annotation-approval <aprovacao-da-particao.json> \
    --adjudication-record <registro-privado-de-adjudicacao.md> \
    --development-cases <casos-desenvolvimento-publico.jsonl> \
    --development-labels <rotulos-desenvolvimento-publico.jsonl> \
    --partition hidden --mode retrieval --out reports/rgc-<data>.json
```

Formato dos rótulos (um por linha): `{"case_id": "...", "verdict": "SUPPORTED"}`.

**Contrato estrito de rótulos — executor `rgc-eval/0.7.0` (2026-10-23; PR #398):** cada linha deve ser um objeto JSON com exatamente as chaves `case_id` e `verdict`; `case_id` deve ser uma string não vazia, `verdict` deve ser uma string pertencente ao vocabulário escolhido e IDs duplicados são rejeitados. JSON inválido, linha em branco, campos extras ou ausentes, ID vazio/não textual, veredito não textual/fora do vocabulário e duplicatas interrompem a leitura com erro identificado por linha. Arquivos de rótulos anteriormente aceitos por coerção de tipos ou tolerância a linhas vazias podem agora ser rejeitados; corrija a entrada, não contorne a validação. A mudança é uma alteração material do contrato de entrada e justifica a versão `0.7.0`.

**Contrato estrito de documentos-fonte (`load_documents`) — executor `rgc-eval/0.7.0` (2026-10-23; PR #399):** cada linha de `DOCUMENTS.jsonl` deve conter um objeto JSON com os campos obrigatórios `source_id`, `source_url`, `retrieved_at`, `source_license` e `text`, todos strings não vazias. A leitura falha com erro identificado pelo arquivo e número da linha quando encontra linha em branco, JSON inválido, objeto/campo obrigatório ausente, campo obrigatório vazio ou de tipo incorreto. `source_id` duplicado também é rejeitado, como já ocorria antes desta alteração; essa regra não é uma mudança de comportamento. Se `text_sha256` for informado, deve ser uma string com exatamente 64 caracteres hexadecimais minúsculos e corresponder ao SHA-256 UTF-8 de `text`; formato inválido ou hash divergente interrompe a leitura. O campo `text_sha256` é opcional; campos adicionais não são rejeitados por esta validação. Documentos anteriormente aceitos apesar de linhas em branco ou campos malformados podem agora ser rejeitados. Corrija os dados de origem; não contorne a validação.

**Gramática dos IDs de artigo — executor `rgc-eval/0.8.0` (DEC-027, D1):** em qualquer partição, todo campo fornecido é validado: cada item de `cited_article_ids`, o `bootstrap_cluster_id` de artigo único e cada membro de um `bundle:` devem casar com `[a-z0-9]+(-[a-z0-9]+)*(:[a-z0-9]+(-[a-z0-9]+)*)*`, ter no máximo 200 caracteres e não começar por `bundle:` nem `component:`. Na partição oculta, `cited_article_ids` e `bootstrap_cluster_id` são obrigatórios e a consistência entre eles também é verificada; na partição de desenvolvimento, os campos podem ser omitidos, mas, quando presentes, não podem conter IDs inválidos. O caractere `+` nunca ocorre num ID de artigo, então `bundle:` e `component:` são inequívocos. A validação está em `evals/ptbr/rgc_ids.py` e é compartilhada pelas ferramentas do RGC. IDs fora da gramática interrompem a execução; nunca são normalizados.

A execução exige a partição pública de desenvolvimento por `--development-cases` e seus rótulos humanos completos por `--development-labels`. O argumento obrigatório `--partition` declara a partição do arquivo de avaliação: `hidden` habilita o critério confirmatório de H1; `development` calcula somente métricas descritivas e marca H1 como não testada. O executor valida que os IDs dos dois arquivos correspondem exatamente, deriva B somente desses rótulos, registra os SHA-256 dos casos e rótulos e recusa IDs sobrepostos entre desenvolvimento e avaliação. A baseline A, derivada dos rótulos de avaliação, aparece separadamente como descritiva e não participa de H1.

Este executor não afirma validação, parceria ou endosso da Anatel ou de qualquer instituição.


## DEC-019 — agrupamento do bootstrap por artigo

Para cada caso elegível na partição oculta, `bootstrap_cluster_id` deve ser uma string não vazia e estável. Use o ID canônico do artigo que contém a regra principal que decide a afirmação. Se a afirmação depender conjuntamente de vários artigos sem um principal único, use `bundle:` seguido dos IDs canônicos únicos ordenados lexicalmente e unidos por `+`. `cited_article_ids` preserva a lista completa de artigos citados quando aplicável. Casos com a mesma chave são reamostrados juntos; bundles são clusters próprios. A execução confirmatória interrompe se o campo estiver ausente ou inválido.

O relatório publica `system_ci95` como intervalo primário por cluster de artigo e `system_ci95_case_bootstrap` como sensibilidade por caso, além do número de clusters e da unidade de reamostragem. Ambos usam 10.000 iterações e seed `20261003`. Nenhum bootstrap real ou métrica RGC foi produzido por esta alteração.

**Gerador e percentil — executor `rgc-eval/0.8.0` (DEC-027, D2 e D3):** todos os sorteios do executor e da ferramenta de concordância vêm de RGC-PRNG-1 (`evals/ptbr/rgc_random.py`), com um fluxo por procedimento: `dec019-accuracy-bootstrap` (cluster), `case-accuracy-bootstrap` (caso) e `case-kappa-bootstrap` (concordância por caso). Os limites do IC95% usam o quantil tipo 7 de Hyndman–Fan, calculado por fórmula. Antes, os sorteios usavam `random.Random` e os limites, estatística de ordem sem interpolação; por isso, intervalos calculados pela versão `0.7.0` não são comparáveis número a número. Os relatórios registram `generator` e `percentile`. Nenhum bootstrap real ou métrica RGC foi produzido por esta alteração.

**Limite de segurança do RGC-PRNG-1:** o gerador é determinístico e destinado exclusivamente à reprodutibilidade estatística do bootstrap e do sign-flip. Não implementa um mecanismo DRBG especificado/validado pela [NIST SP 800-90A](https://csrc.nist.gov/pubs/sp/800/90/a/r1/final), não recebe entropia nem oferece reseed/prediction resistance e não deve ser usado para chaves, tokens, nonces ou qualquer finalidade de segurança.


**Nota de consistência (2026-10-21):** DEC-017 e DEC-018 estão aprovadas pelo mantenedor (opção A); as propostas históricas correspondentes não representam estado pendente. O protocolo permanece **[PROPOSTO]** e não congelado.
