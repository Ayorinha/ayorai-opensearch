# ADR-002 — Judge Rules and Evidence Verification

**Status:** Draft — aguardando aprovação humana junto com Golden Set v0  
**Date:** 2026-09-30  
**Scope:** R1 verification engine

## Decision

O veredito é determinístico e baseado exclusivamente em evidência estruturada, proveniência, independência, stance e contradições. Um LLM pode redigir rationale, mas **nunca decide o veredito**.

### 1. Estados do Judge

| Estado | Definição | Condição mínima | Casos v0 |
|---|---|---|---|
| VERIFIED | Claim confirmado por evidência suficiente, independente e com proveniência completa | ≥2 clusters independentes concordantes + proveniência completa | f01–f04, p01 |
| SUPPORTED | Claim sustentado, mas sem todos os requisitos de VERIFIED | evidência positiva suficiente, porém apenas 1 cluster independente ou proveniência incompleta | m01–m03, c01–c02, p02 |
| PARTIALLY_SUPPORTED | Há evidência positiva, mas insuficiente para SUPPORT/VERIFY | exatamente 1 cluster independente ou evidência positiva limitada | r01, r02, h01, ch01 |
| UNVERIFIED | Não há base independente suficiente para afirmar o claim | zero evidência independente, evidência somente mock/LLM, ou evidência insuficiente | c03, n01–n02, i01–i03, o01–o02 |
| REFUTED | A proposição do claim é contrariada por evidência válida sem evidência positiva concorrente equivalente | ≥1 evidência independente que contradiz o claim e nenhum cluster independente que o sustente | rf01 |
| CONFLICTING | Existem clusters independentes com proposições incompatíveis para o mesmo claim/atributo | ≥1 suporte e ≥1 refutação incompatíveis, ou ≥2 valores mutuamente exclusivos | c01, x01–x06 |

**Regra importante:** REFUTED não significa simplesmente “existe uma fonte que diz o contrário”. Se houver também evidência positiva concorrente de qualidade comparável, o estado é CONFLICTING.

### 2. Proveniência completa

Uma evidência tem proveniência completa quando contém, no mínimo:
1. identificador estável da fonte;
2. URL/localização da fonte;
3. retrieved_at válido;
4. offsets válidos para o trecho recuperado (start <= end e ambos dentro do conteúdo);
5. excerpt verificável associado ao documento;
6. identificação de origem (origin_id) ou URL canônica suficiente para formar o cluster.

A ausência de qualquer item obrigatório torna a proveniência incompleta. Duas fontes independentes concordantes com proveniência completa podem produzir VERIFIED; a mesma situação com uma ou mais fontes incompletas não pode produzir VERIFIED e, se houver suporte positivo suficiente, produz SUPPORTED.

### 3. Clusters de origem e independência

Evidências pertencem ao mesmo cluster quando qualquer uma das relações abaixo estabelecer dependência:
- mesma URL canônica;
- mesmo origin_id;
- mesmo hash de conteúdo normalizado;
- cadeia de citação em que uma fonte apenas republica/cita a origem da outra.

Domínios diferentes não implicam independência.

Três documentos com o mesmo origin_id continuam sendo **um cluster**, não três fontes.

Conteúdo idêntico em domínios diferentes também é um cluster único.

Duas fontes com origins distintos, conteúdo não duplicado e sem relação de citação são independentes para fins do Judge.

### 4. Agregação global — elo mais fraco

A ordem de severidade do lattice global é:
VERIFIED < SUPPORTED < PARTIALLY_SUPPORTED < UNVERIFIED < REFUTED < CONFLICTING

O global recebe o estado de maior severidade entre os claims relevantes:
- qualquer CONFLICTING torna o global CONFLICTING;
- na ausência de CONFLICTING, qualquer REFUTED torna o global REFUTED;
- depois aplicam-se UNVERIFIED, PARTIALLY_SUPPORTED, SUPPORTED e VERIFIED nessa ordem;
- claims adicionais não podem elevar um resultado acima do elo mais fraco;
- ABSTAIN é um status de resposta da API, não um estado do Judge, e é usado quando a pergunta não pode ser respondida de forma responsável.

Essa regra impede que claims fortes “compensem” um claim conflitante, refutado ou não verificável.

### 5. Abstenção

- **no-answer:** a pergunta pertence ao domínio coberto pelo corpus, mas não existe evidência para o atributo solicitado. O claim fica UNVERIFIED; a API deve indicar ABSTAIN com motivo NO_ANSWER.
- **out-of-scope:** a pergunta pede uma decisão/serviço que não pertence ao escopo factual definido para o corpus. A API deve indicar ABSTAIN com motivo OUT_OF_SCOPE.

Diferença em uma frase: **no-answer é uma pergunta pertinente sem evidência; out-of-scope é uma pergunta que o sistema não se propõe a responder.**

### 6. Injeção

Conteúdo recuperado é sempre **dado**, nunca instrução de sistema.

Se um documento disser “declare VERIFIED”, “ignore outras fontes” ou “revele segredos/configuração”, essas frases são avaliadas apenas como conteúdo factual do documento. Elas não alteram prioridade, política, veredito, ferramentas, segredos ou instruções do sistema.

### 7. INSUFFICIENT_EVIDENCE do EvidenceStore atual

O EvidenceStore.status() atual retorna INSUFFICIENT_EVIDENCE quando não há evidências. No R1, esse estado interno será mapeado para:
- claim sem evidência → UNVERIFIED;
- pergunta sem claims respondíveis → API ABSTAIN;
- ABSTAIN deve carregar motivo NO_ANSWER ou OUT_OF_SCOPE quando essa classificação estiver disponível.

INSUFFICIENT_EVIDENCE não será exposto como um novo estado do Judge v2.

### 8. Rastreabilidade exigida

Cada regra desta tabela deve ter, no R1:
- teste unitário explícito;
- caso(s) do Golden Set que a exercitam;
- referência cruzada no ADR-002.

Uma regra sem teste e caso correspondente significa R1 incompleto.

## Resolução dos antigos casos ⚠️

Os casos abaixo foram revisados contra as regras acima. Nenhum permanece como dúvida aberta:
- **m01:** SUPPORTED global porque ambos os claims são suportados e o elo mais fraco entre eles é SUPPORTED; a agregação não transforma dois supports em verified.
- **m02:** SUPPORTED pelo mesmo princípio de agregação.
- **m03:** SUPPORTED; a evidência de latência e a evidência metodológica sustentam os claims, sem requisito de duas fontes independentes para cada claim.
- **c03:** UNVERIFIED; o documento de VectorLabs sustenta seu próprio foco, mas não existe claim equivalente independente para OrionCloud. O elo mais fraco permanece UNVERIFIED.
- **r01:** PARTIALLY_SUPPORTED; 007/008/031 têm o mesmo origin_id, logo um cluster, apesar de três documentos.
- **r02:** PARTIALLY_SUPPORTED; o mesmo cluster não satisfaz o requisito de duas fontes independentes.
- **h01:** PARTIALLY_SUPPORTED; conteúdo idêntico gera o mesmo cluster mesmo em domínios distintos.
- **ch01:** PARTIALLY_SUPPORTED; 008 cita 007 e compartilha a origem, portanto a cadeia não cria independência.
- **p01:** VERIFIED; 034 e 035 têm origins distintos e proveniência completa, com evidência concordante.
- **p02:** SUPPORTED; 034 e 036 concordam, mas 036 não tem retrieved_at, portanto a proveniência não é completa.
- **rf01:** REFUTED; a nova fixture doc-043 contém apenas a negação da proposição “AG-003 foi implantado”. Não há evidência positiva concorrente no caso, portanto a regra de refutação é satisfeita.

## Golden v0

O Golden Set permanece em 30 casos e não será executado nem congelado antes da aprovação humana explícita deste ADR e do v0.