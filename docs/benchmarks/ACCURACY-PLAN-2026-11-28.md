# Plano de acurácia no LLM-AggreFact — proposta para decisão (2026-11-28)

Revisão por ferramenta automatizada, publicada pelo mantenedor.

**Natureza:** proposta. Nenhum experimento foi executado. Toda execução DEV ou TEST depende de autorização explícita do mantenedor. Testes de software não são resultado científico.

## 1. Onde estamos [FATO]

| item | valor | fonte |
|---|---|---|
| Melhor modelo do projeto | FactCG-DeBERTa-L (0,4B) | `reports/benchmarks/2026-11-07-dev-calibration-v2/README.md` |
| BA cross-fitted, DEV-A, média macro | **74,68%** | idem |
| MiniCheck (DEV-A) | 72,87% | idem |
| Ponto fraco | ExpertQA 59,5%; CNN 62,9%; XSum 68,1% | idem |
| Hardware usado | CPU, fp32 | idem |

**Ressalva de comparabilidade:** o número do projeto é DEV (cross-fitted). O ranking publica TEST. Os dois não são diretamente comparáveis.

## 2. Ranking internacional (LLM-AggreFact, TEST) [FATO, fontes públicas]

| sistema | média | tamanho |
|---|---|---|
| GauntletScore (arXiv 2611.22027, 2026-11-17) | 79,51 | vários leitores LLM |
| nimble-v4-max | 79,5 | 27B |
| Clef | 79,0 | 27B |
| Bespoke-MiniCheck-7B | 77,4 | 7B |
| Granite Guardian 3.3 | 76,5 | 8B, Apache-2.0 |
| FactCG-DeBERTa-L (o modelo atual do projeto) | 75,6 | 0,4B, MIT |

**Fontes:** `docs/benchmarks/snapshots/LLM-AGGREFACT-LEADERBOARD-2026-11-07.md` e a página do artigo no Hugging Face.

**Leitura:**
- Superar o topo (≈79,5) exige cerca de **+4 a +5 pontos** sobre o modelo atual.
- Nenhum modelo de 0,4B chega lá.
- Os sistemas do topo usam modelos de 7B a 27B, ou combinações de vários leitores.

## 3. Caminhos, em ordem de custo e risco

| # | caminho | ganho esperado [HIPÓTESE] | custo | decisão necessária |
|---|---|---|---|---|
| A | **Combinação dos modelos já integrados** (FactCG + MiniCheck), regra fixa ou empilhamento simples aprendido só em DEV-A e validado em DEV-B. O experimento E3 já explorou isso | +0,5 a +1,5 | baixo; CPU; reaproveita os caches cifrados | pré-registro da regra; autorização de execução DEV |
| B | **Leitor de 7–8B com licença permissiva** (Granite Guardian 3.3, Apache-2.0) | +1 a +2 sozinho; +2 a +3 combinado com A | **GPU** (infraestrutura nova, custo mensal); novo protocolo de inferência | aprovar infraestrutura GPU e orçamento; licença; pré-registro |
| C | **Bespoke-MiniCheck-7B** | similar a B | GPU | a licença do modelo precisa ser verificada para uso comercial [HIPÓTESE: não comercial] |
| D | **Vários leitores independentes com regra bayesiana fixa**, no estilo do GauntletScore: contradição só quando dois leitores concordam | até o patamar de 79–80 | alto: GPU ou API de LLM; custo por caso | decisão estratégica; dados enviados a provedores externos (LGPD e soberania tecnológica) |
| E | **Ajuste do segmentador e dos chunks** para CNN e XSum (documentos longos) | +0,5 a +1 nessas coortes | médio | muda o protocolo; exige nova DEC (protocolo científico) |

## 4. Rota recomendada

1. **A primeiro.** Barata, roda na infraestrutura atual e mede o teto dos modelos já integrados.
   - Pré-registrar a regra.
   - Aprender só em DEV-A e validar em DEV-B.
   - Rodar uma vez, com autorização.
2. **B em seguida, se A ficar abaixo de 77.** Granite Guardian 3.3 em GPU, com a mesma disciplina.
3. **TEST só uma vez**, com o sistema congelado antes do primeiro caso e o plano de parada registrado. É o mesmo padrão que deu credibilidade ao GauntletScore.
4. **Nunca usar TEST para ajustar** limiar, regra ou modelo.

## 5. Pré-requisitos que dependem do mantenedor

- Configurar `PHASE1B_GOLD_LABEL_ENCRYPTION_KEY`, distinta da chave de artefato. Sem ela não há métrica de qualidade.
- Autorizar a execução DEV completa. O minimal não calcula acurácia.
- Para B, C ou D: decidir sobre GPU e orçamento, licenças e envio de dados a terceiros.
