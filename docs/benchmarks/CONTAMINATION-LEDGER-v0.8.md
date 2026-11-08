# Ledger de contaminação A4 — AYORAI ATTRACTOR v0.8

**Autoria:** ANDERSON AYORA  
**Consulta documental:** 2026-11-08 (UTC−03:00)  
**Status:** rascunho de pesquisa; incompleto; nenhuma célula liberada para avaliação confirmatória.  
**Escopo:** documentação e pesquisa de proveniência. Não executa modelos, não consulta exemplos ou rótulos de TEST, não altera código ou pesos e não autoriza benchmark.

> **Regra fail-closed:** ausência de evidência não é evidência de ausência. Somente o status **eligible** após fonte primária verificável, revisão/versão identificada e comparação de proveniência documentada. **blocked** indica sobreposição/exposição impeditiva conhecida ou gate pendente por risco específico; **unverified** indica que a investigação não demonstrou nem excluiu contaminação. Ambos impedem uso confirmatório. Nenhuma célula deste rascunho é eligible.

## 1. Fontes-base e método

1. [Cartão oficial do LLM-AggreFact](https://huggingface.co/datasets/lytang/LLM-AggreFact) — composição das 11 coortes, formato, splits e identificador de contaminação. Consultado em 2026-11-08.
2. [MiniCheck, EMNLP 2024](https://arxiv.org/abs/2404.10774) e [apêndice publicado](https://aclanthology.org/2024.emnlp-main.499.pdf) — construção C2D/D2C e dados de treinamento. Consultados em 2026-11-08.
3. [Radar tecnológico AYORAI, 2026-11-07](RADAR-TECNOLOGICO-2026-11.md) — pesquisa anterior, riscos conhecidos, licenças e fontes primárias. Consultado em 2026-11-08; é pista documental, não substitui fontes originais.
4. [FactCG — repositório oficial](https://github.com/derenlei/FactCG) e [paper](https://arxiv.org/abs/2501.17144) — dados declarados e tuning de limiar. Consultados em 2026-11-08.
5. [HHEM-2.1-Open — cartão do modelo](https://huggingface.co/vectara/hallucination_evaluation_model) e [artigo EMNLP Industry 2025](https://aclanthology.org/2025.emnlp-industry.54/) — backbone, RAGTruth e conjuntos adicionais confidenciais. Consultados em 2026-11-08.

Para cada modelo, a investigação completa deve registrar: URL primária, data de consulta, revisão imutável (commit SHA), arquitetura/backbone, pré-treino, fine-tuning/adapters, dados sintéticos e linhagem, validação/calibração/tuning de limiar, exposição por coorte, licenças de pesos/código/tokenizer/datasets, deduplicação por IDs/conteúdo, limitações e decisão do revisor. Nome de dataset sem split, versão e relação com o checkpoint não basta para declarar contaminação nem independência. Fontes confidenciais ou não divulgadas permanecem **unverified** e bloqueiam a coorte.

## 2. Proveniência declarada dos cinco modelos

| Modelo | Fontes primárias / treinamento declarado | Risco e pendências A4 |
|---|---|---|
| **FactCG-DeBERTa-v3-Large** (yaxili96/FactCG-DeBERTa-v3-Large) | [Cartão](https://huggingface.co/yaxili96/FactCG-DeBERTa-v3-Large); [repositório](https://github.com/derenlei/FactCG); [paper](https://arxiv.org/abs/2501.17144). Radar registra ANLI, MiniCheck C2D/D2C, HotpotQA/MuSiQue e tuning de limiar por dataset no validation LLM-AggreFact. | Separar exposição de tuning de contaminação de pesos. Fixar versões/splits/IDs e deduplicar C2D/D2C. WiCE **blocked**; demais coortes **unverified**. |
| **MiniCheck-DeBERTa-v3-Large** (lytang/MiniCheck-DeBERTa-v3-Large) | [Cartão](https://huggingface.co/lytang/MiniCheck-DeBERTa-v3-Large); [paper](https://arxiv.org/abs/2404.10774); [apêndice](https://aclanthology.org/2024.emnlp-main.499.pdf). Radar registra ANLI e C2D/D2C sintéticos, incluindo fontes Wikipedia/Google News. | Exigir versões dos dados sintéticos, fontes e IDs. WiCE **blocked**; outras coortes **unverified**, inclusive notícias. |
| **mDeBERTa-v3-base NLI** (MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7) | [Cartão do checkpoint](https://huggingface.co/MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7); [mDeBERTa-v3-base](https://huggingface.co/microsoft/mdeberta-v3-base). Radar registra XNLI e restrição CC BY-NC. | Fixar revisão, lineage do backbone, splits e fine-tuning adicional. Ausência de sobreposição direta conhecida não comprova independência: todas as coortes **unverified**. |
| **MiniCheck-Flan-T5-Large** (lytang/MiniCheck-Flan-T5-Large) | [Cartão](https://huggingface.co/lytang/MiniCheck-Flan-T5-Large); [FLAN-T5-Large](https://huggingface.co/google/flan-t5-large); [registro FLAN](https://github.com/google-research/FLAN/blob/main/flan/tasks.py); [paper MiniCheck](https://arxiv.org/abs/2404.10774). Radar registra C2D/D2C, ANLI e tarefas FLAN que incluem CNN/DailyMail e XSum. | CNN, XSum, WiCE e REVEAL **blocked** até deduplicação/verificação. Outras coortes **unverified**; investigar notícias e dados sintéticos. |
| **HHEM-2.1-Open** (vectara/hallucination_evaluation_model) | [Cartão](https://huggingface.co/vectara/hallucination_evaluation_model); [artigo EMNLP Industry 2025](https://aclanthology.org/2025.emnlp-industry.54/). Fontes declaram RAGTruth train e outros conjuntos confidenciais; backbone Flan-T5. | RAGTruth, CNN e XSum **blocked**. Demais coortes **unverified**: dados confidenciais impedem provar independência. Sem disclosure suficiente, não há elegibilidade confirmatória. |

As fontes acima são pontos de partida. Antes de qualquer status eligible, abrir as fontes primárias, capturar revisão imutável, verificar configurações/datasets e registrar evidência específica. Páginas main não substituem o SHA do snapshot efetivamente usado.

## 3. Fontes das 11 coortes

O [cartão oficial lytang/LLM-AggreFact](https://huggingface.co/datasets/lytang/LLM-AggreFact) lista as 11 coortes e trabalhos de origem. A fonte inicial abaixo não substitui a verificação da cópia efetivamente usada pelo benchmark.

| ID | Coorte | Fonte de origem / referência inicial | Verificação pendente |
|---|---|---|---|
| C01 | AggreFact-CNN | [Tang et al., 2023 / cartão](https://huggingface.co/datasets/lytang/LLM-AggreFact) — sumarização CNN/DailyMail | Fixar upstream, split, IDs, hashes e sumarizadores; comparar com FLAN e dados sintéticos. |
| C02 | AggreFact-XSum | [Tang et al., 2023 / cartão](https://huggingface.co/datasets/lytang/LLM-AggreFact) — sumarização XSum | Fixar split/IDs e linhagem dos resumos; comparar com tarefas FLAN e dados sintéticos. |
| C03 | TofuEval-MediaS | [Tang et al., 2024 / cartão](https://huggingface.co/datasets/lytang/LLM-AggreFact) — sumarização de diálogo/media | Identificar diálogos, split, IDs e geradores; verificar dados de diálogo nos modelos. |
| C04 | TofuEval-MeetB | [Tang et al., 2024 / cartão](https://huggingface.co/datasets/lytang/LLM-AggreFact) — sumarização de reuniões/MeetingBank | Fixar versão/split, IDs de reuniões e linhagem de geração. |
| C05 | WiCE | [Kamoi et al., 2023 / cartão](https://huggingface.co/datasets/lytang/LLM-AggreFact) — claims com evidência Wikipedia | Fixar IDs/claims/páginas e snapshot Wikipedia; deduplicar C2D e dados sintéticos. |
| C06 | REVEAL | [Jacovi et al., 2024 / cartão](https://huggingface.co/datasets/lytang/LLM-AggreFact) — verificação de raciocínio/respostas de busca | Fixar fontes de busca, documentos, splits e geradores; investigar tarefas/instruções e notícias. |
| C07 | ClaimVerify | [Liu et al., 2023 / cartão](https://huggingface.co/datasets/lytang/LLM-AggreFact) — respostas de sistemas search-augmented | Identificar versão, fontes web, IDs e splits; comparar com D2C/Google News. |
| C08 | FactCheck-GPT | [Wang et al., 2023 / cartão](https://huggingface.co/datasets/lytang/LLM-AggreFact) — factualidade de respostas ChatGPT | Fixar documentos, claims, geradores e splits; separar tuning/validação de contaminação de pesos. |
| C09 | ExpertQA | [Malaviya et al., 2024 / cartão](https://huggingface.co/datasets/lytang/LLM-AggreFact) — QA de domínio especializado | Identificar domínios, fontes documentais, split/IDs e dados de QA nos modelos. |
| C10 | LFQA | [Chen et al., 2023 / cartão](https://huggingface.co/datasets/lytang/LLM-AggreFact) — long-form QA | Fixar upstream, split, fontes web e IDs; investigar HotpotQA/MuSiQue e dados sintéticos. |
| C11 | RAGTruth | [Niu et al., 2024 / cartão](https://huggingface.co/datasets/lytang/LLM-AggreFact); [cartão RAGTruth](https://huggingface.co/datasets/leobianco/ragtruth) — respostas RAG anotadas | Fixar versão/split/IDs; confirmar uso permitido e qualquer uso de RAGTruth train nos modelos. |

Esta é uma trilha inicial, não uma conclusão de contaminação. Cada coorte exige referência primária, snapshot e evidência de identidade dos exemplos. Preservar o campo contamination_identifier do benchmark e usá-lo conforme protocolo autorizado. Não exportar exemplos, textos ou labels de TEST para este ledger.

## 4. Matriz de status — 5 modelos × 11 coortes

**Data de avaliação:** 2026-11-08. Sem evidência positiva e reproduzível de independência, status **unverified**; sobreposição/exposição impeditiva conhecida, **blocked**. Nenhuma célula é **eligible**.

| Modelo / Coorte | CNN | XSum | MediaS | MeetB | WiCE | REVEAL | ClaimVerify | FactCheck-GPT | ExpertQA | LFQA | RAGTruth |
|---|---|---|---|---|---|---|---|---|---|---|---|
| FactCG-DeBERTa-v3-Large | unverified | unverified | unverified | unverified | **blocked** | unverified | unverified | unverified | unverified | unverified | unverified |
| MiniCheck-DeBERTa-v3-Large | unverified | unverified | unverified | unverified | **blocked** | unverified | unverified | unverified | unverified | unverified | unverified |
| mDeBERTa-v3-base NLI | unverified | unverified | unverified | unverified | unverified | unverified | unverified | unverified | unverified | unverified | unverified |
| MiniCheck-Flan-T5-Large | **blocked** | **blocked** | unverified | unverified | **blocked** | **blocked** | unverified | unverified | unverified | unverified | unverified |
| HHEM-2.1-Open | **blocked** | **blocked** | unverified | unverified | unverified | unverified | unverified | unverified | unverified | unverified | **blocked** |

### 4.1 Fundamentação dos bloqueios

- **WiCE × FactCG / MiniCheck-DeBERTa:** bloqueio provisório por C2D/claims Wikipedia e falta de deduplicação conclusiva por IDs.
- **CNN/XSum × MiniCheck-Flan-T5:** bloqueio por linhagem FLAN-T5 com tarefas CNN/DailyMail e XSum; exigir revisão de tarefas/dados e prova de não sobreposição.
- **WiCE/REVEAL × MiniCheck-Flan-T5:** bloqueio conservador herdado do radar por C2D/Wikipedia e exposição de tarefas/claims; reclassificação exige fonte primária e deduplicação.
- **RAGTruth × HHEM:** bloqueio direto porque a publicação declara uso do split train do RAGTruth.
- **CNN/XSum × HHEM:** bloqueio conservador pela linhagem Flan-T5 e falta de prova de independência para sumarização.
- **Demais células:** **unverified**, não eligible. Datasets confidenciais adicionais do HHEM impedem concluir ausência de contaminação.
- **FactCG:** registrar threshold tuning no validation LLM-AggreFact como exposição separada. Não chamar automaticamente isso de contaminação de pesos, mas não alegar independência total do processo de seleção dos autores.

## 5. Requisitos para mudar uma célula para eligible

- [ ] URL e referência primária do dataset/coorte e dos datasets de treino.
- [ ] Data de consulta, revisão imutável (commit SHA), versão e split.
- [ ] Fontes/linhagem de dados declaradas pelos autores do modelo.
- [ ] Evidência sobre dados sintéticos, fontes subjacentes e geradores.
- [ ] Deduplicação documentada por contamination_identifier, IDs e/ou hashes permitidos, sem expor dados de TEST.
- [ ] Exposição por calibração, validação, threshold tuning e seleção registrada separadamente da contaminação de pesos.
- [ ] Licenças de checkpoint, backbone, tokenizer, código e datasets verificadas.
- [ ] Evidência identificada, método reproduzível e limitações explícitas.
- [ ] Revisor independente e data de adjudicação.
- [ ] Histórico aditivo da mudança, justificativa e responsável.

**Fail-closed:** faltando qualquer item obrigatório, manter **unverified** ou **blocked**. Não declarar elegibilidade por reputação do modelo, ausência de menção no model card ou falta de correspondência textual.

## 6. Decisão operacional

1. A4 permanece **aberto e incompleto**.
2. Todas as células **blocked** e **unverified** são inelegíveis para E3 confirmatório.
3. Não executar E3 confirmatório até revisão do ledger, elegibilidade documentada das células usadas e congelamento da matriz antes dos resultados.
4. E3 exploratório, se considerado, exige autorização e classificação separada; não pode selecionar retrospectivamente coortes/modelos para o confirmatório.
5. Este documento não altera o pré-registro E3, Calibration V2, cache A1, Judge, Golden, thresholds de produção ou TEST.
6. Próxima revisão deve anexar evidências por célula e registrar o hash do ledger. Mudanças de status devem ser auditáveis, preservando o histórico.

**Conclusão:** neste estado, nenhuma combinação confirmatória está liberada. O resultado correto da pesquisa incompleta é **unverified/blocked**, não independência presumida.
