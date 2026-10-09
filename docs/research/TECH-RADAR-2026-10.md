# Radar de tecnologia — ATTRACTOR como referência de auditoria em português

**Data da pesquisa:** 2026-10-09 (fontes acessadas nesta data). Complementa `STATE-OF-THE-ART.md` (2026-10-03).

Objetivo: escolher as tecnologias que tornam o ATTRACTOR melhor **e** diferente — verificação auditável de respostas de IA contra fontes oficiais brasileiras — sem abrir mão da regra central: **o modelo informa, o Judge determinístico decide**.

## 1. O que a simulação real mostrou (PT-CP-Audit, Código Penal)

| Medida no test reservado (casos manuais) | Regras v5 | Regras v6 |
|---|---:|---:|
| Apoio falso | 25,9% | 14,8% |
| Acurácia | 65,0% | 72,5% |

Os erros que sobram não são de regra: negação semântica ("não respondem criminalmente" ≈ "inimputáveis"), condições diferentes no mesmo esquema e distinções lexicais finas ("regime aberto" × "semi-aberto"). Isso define a próxima tecnologia: um **classificador semântico de stance em português**, com o Judge fora do modelo.

## 2. Estado da arte relevante (2025–2026)

### 2.1 Verificadores de fundamentação (inglês)
- **LLM-AggreFact** (média): Bespoke-MiniCheck-7B 77,4; Claude-3.5 Sonnet 77,2; Granite Guardian 3.3 (8B) 76,5; Mistral-Large 2 76,5; GPT-4o 75,9; **FactCG-DeBERTa-L (0,4B) 75,6**; MiniCheck-Flan-T5-L (0,8B) 75,0. Modelos pequenos especializados empatam com LLMs gigantes. [LLM-AggreFact](https://llm-aggrefact.github.io/)
- **FactCG** gera dados multi-hop a partir de grafos de documentos e chega a 75,6 com 0,4B parâmetros. [FactCG](https://arxiv.org/html/2501.17144v1)
- **HalluGuard (4B)**: modelo pequeno de raciocínio que rotula afirmação × documento e escreve uma **justificativa citando o documento**; 75,7 no LLM-AggreFact, 84,0 no RAGTruth; licença Apache 2.0 anunciada, ainda não liberada. A ideia de justificativa citada é diretamente útil para auditoria. [HalluGuard](https://arxiv.org/html/2510.00880v1)
- Lacuna: todos são majoritariamente em inglês e emitem um escore, não um veredito auditável com proveniência.

### 2.2 Encoders em português (base para o AYORAI-PT-NLI)
ASSIN 2 (inferência textual), Macro-F1: BERTimbau Large 90,04; **BERTomelo Large 89,21** (ModernBERT, contexto de 1.024 tokens); Albertina-900M PT-BR 89,09; BERTimbau Base 89,20. [BERTomelo](https://arxiv.org/html/2606.28999)
**NorBERTo-large** (ModernBERT, corpus Aurora-PT de 331 bilhões de tokens, PROPOR 2026) tem o maior F1 de *entailment* no ASSIN 2 (0,904) entre os encoders avaliados. [NorBERTo](https://aclanthology.org/2026.propor-1.18/), [encoders PT do zero](https://aclanthology.org/2026.propor-1.93.pdf)
Conclusão: há encoders brasileiros modernos e de contexto longo competitivos com os clássicos. **Licenças precisam ser verificadas na fonte primária antes de qualquer uso comercial** (os artigos não as informam).

### 2.3 Direito brasileiro
**LegalBench-BR** (TJSC via DataJud/CNJ): um BERTimbau ajustado com LoRA chegou a 87,6% de acurácia contra 65,7% (Claude 3.5 Haiku) e 60,0% (GPT-4o mini) em zero-shot. Rodou em ~233 ms por amostra em CPU. Modelos pequenos ajustados vencem LLMs genéricos em texto jurídico brasileiro. [LegalBench-BR](https://arxiv.org/pdf/2604.18878)

### 2.4 Calibração e abstenção com garantia
Predição conformal para factualidade: *coherent factuality* (ICLR 2025) e treino conformal diferenciável (ICML 2026) dão **garantias estatísticas** de cobertura para a decisão de afirmar ou abster. [ICLR 2025](https://proceedings.iclr.cc/paper_files/paper/2025/hash/679fcceef65c3d855aa885bd024542c1-Abstract-Conference.html), [ICML 2026](https://icml.cc/virtual/2026/poster/63378)

### 2.5 Trilha de auditoria à prova de adulteração
**Sigstore Rekor**: log de transparência público e somente-acréscimo, com provas de inclusão verificáveis por qualquer pessoa. Hoje usado para software, aplicável a vereditos. [Rekor](https://docs.sigstore.dev/logging/overview/)

## 3. Recomendações, em ordem

### R1 — Fábrica de dados jurídicos por construção (inovação principal)
A PT-CP-Audit mostrou que leis em domínio público, com estrutura de dispositivos e histórico de redação, permitem gerar pares afirmação × trecho **com rótulo por construção**: paráfrase (apoia), mutação de número, fração, negação, ator ou condição (contradiz), dispositivo vizinho (neutro).
- Escalar para LGPD, LAI, CDC, Marco Civil, Constituição, normas do BCB e da CVM.
- Gera dados de treino comercialmente limpos para o AYORAI-PT-NLI (ADR-008), sem XNLI nem ANLI.
- Continua exigindo o parecer jurídico do ADR-008 §4 e a separação total do Golden v1.

### R2 — AYORAI-PT-NLI em encoder brasileiro moderno
- Candidatos: BERTimbau Large (referência), BERTomelo Large, NorBERTo-large, EuroBERT-210m (ADR-008). Escolha por licença primária primeiro, depois desempenho.
- Treino: ASSIN 2 (verificar licença) + dados da R1. Avaliação: PT-CP-Audit test, depois Golden v1.
- Saída continua sendo stance (SUPPORTS/CONTRADICTS/NEUTRAL); o Judge decide.

### R3 — Verificação temporal ("era verdade até quando?")
O dataset do Código Penal traz `vigenteDesde`, `vigenteAte` e a lei de origem de cada redação. A alucinação mais comum da simulação foi uma **regra antiga** ("o limite é de 30 anos", que vigorou até a Lei 13.964/2019). Proposta de ADR: comparar a afirmação com **todas as versões** do dispositivo e registrar "contradiz a versão vigente; coincide com a versão de [data] a [data]". Nenhum verificador público faz isso, e é exatamente o que um auditor precisa.

### R4 — Justificativa citada no relatório
Inspirado no HalluGuard: cada stance passa a carregar a frase exata do trecho e a regra ou modelo que a produziu, com offsets. O Judge continua decidindo, e a explicação vira prova.

### R5 — Abstenção calibrada com garantia
Aplicar predição conformal sobre a confiança do stance (calibração no dev, nunca no Golden v1) para controlar a taxa de apoio falso com garantia estatística, em vez de um limiar escolhido à mão. Exige pré-registro e ADR.

### R6 — Log de transparência dos vereditos
Publicar o hash de cada relatório de verificação num log somente-acréscimo (Rekor ou um log próprio com árvore de Merkle). Assim qualquer terceiro consegue provar que um veredito existia numa data e não foi alterado. É o diferencial de auditoria, não de acurácia.

## 4. O que não fazer

- Não trocar o Judge por um LLM ("LLM como juiz"): perde reprodutibilidade e auditabilidade.
- Não usar modelos ou dados NC (XNLI, ANLI, Bespoke-MiniCheck) em produção ou treino comercial.
- Não medir evolução no Golden v0/v0.1 de novo: já foram vistos demais. Usar o test da PT-CP-Audit e o Golden v1.
