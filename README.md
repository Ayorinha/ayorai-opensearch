<div align="center">

<p><img src="docs/assets/brand/ayorai-attractor-banner.png" alt="AYORAI ATTRACTOR" width="760"></p>

# AYORAI ATTRACTOR

### Auditoria técnica de respostas de inteligência artificial baseada em evidências

**Da afirmação à evidência. Da evidência a um resultado verificável.**

[![CI](https://github.com/Ayorinha/ayorai-opensearch/actions/workflows/ci.yml/badge.svg)](https://github.com/Ayorinha/ayorai-opensearch/actions/workflows/ci.yml)
[![Security](https://github.com/Ayorinha/ayorai-opensearch/actions/workflows/security.yml/badge.svg)](https://github.com/Ayorinha/ayorai-opensearch/actions/workflows/security.yml)
[![CodeQL](https://github.com/Ayorinha/ayorai-opensearch/actions/workflows/codeql.yml/badge.svg)](https://github.com/Ayorinha/ayorai-opensearch/actions/workflows/codeql.yml)
[![Licença Apache-2.0](https://img.shields.io/badge/licença-Apache--2.0-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.13-blue)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23125082.svg)](https://doi.org/10.5281/zenodo.23125082)

**Site oficial:** [ayorinha.github.io/ayorai-opensearch](https://ayorinha.github.io/ayorai-opensearch/) · [Guia de auditoria de inteligência artificial](https://ayorinha.github.io/ayorai-opensearch/auditoria-de-inteligencia-artificial/)

[Entenda o projeto](#o-que-é) · [Como funciona](#como-funciona) · [Estado e limites](#o-que-está-comprovado-hoje) · [Documentação](docs/INDEX.md) · [Instalação](#começar)

</div>

---

## O que é

O **AYORAI ATTRACTOR** é um projeto open source de engenharia para verificar respostas de inteligência artificial no nível de cada afirmação. Seu objetivo é tornar mais fácil examinar **o que foi afirmado, quais evidências foram usadas, como elas se relacionam com a afirmação e por que determinada classificação foi emitida**.

O problema que ele aborda é concreto: uma resposta pode parecer convincente e citar uma fonte sem que essa fonte sustente o que foi dito. Em contextos que exigem responsabilidade, não basta receber uma resposta fluente; é preciso poder inspecionar a relação entre afirmação e evidência.

O ATTRACTOR desenvolve uma abordagem estruturada para essa verificação. Ele não promete eliminar todas as alucinações nem provar que uma fonte externa é verdadeira.

## Como funciona

```mermaid
flowchart TD
    A["Resposta ou afirmação a verificar"] --> B["Identificação das afirmações"]
    B --> C["Evidências e proveniência"]
    C --> D["Análise: suporte, contradição ou neutralidade"]
    D --> E["Judge determinístico"]
    E --> F["Veredito segundo regras versionadas"]
    E --> G["Referências para inspeção e reprodução"]
```

1. **Delimitar a afirmação:** definir exatamente o que está sendo verificado.
2. **Relacionar evidências:** identificar fontes e trechos relevantes, preservando referências de proveniência disponíveis.
3. **Analisar a relação:** classificar se a evidência apoia, contradiz ou não esclarece a afirmação.
4. **Aplicar o Judge:** regras determinísticas versionadas selecionam o veredito final.
5. **Inspecionar e reproduzir:** consultar os artefatos e testes correspondentes para entender o resultado dentro dos limites definidos.

### A separação fundamental

> **Inteligência ≠ Autorização ≠ Execução**

Modelos podem auxiliar a análise. **Não são a autoridade do veredito final.** O Judge determinístico aplica o contrato explícito do sistema. A aplicação que consome o resultado também não deve transformar uma sugestão de modelo em decisão factual sem passar pelas regras previstas.

Os cinco vereditos do Judge 2.0 são: `SUPPORTED`, `PARTIALLY_SUPPORTED`, `UNVERIFIED`, `REFUTED` e `CONFLICTING`. A semântica completa está no [contrato e na rastreabilidade do Judge 2.0](docs/judge2/TRACEABILITY.md).

## Por que isso importa para auditoria

O ATTRACTOR busca tornar a verificação de respostas de IA mais **inspecionável, rastreável e reproduzível**, em vez de depender apenas de uma explicação em linguagem natural.

- **Rastreabilidade:** conectar a afirmação às evidências e às referências disponíveis.
- **Regras explícitas:** manter a decisão final separada da análise assistida por modelos.
- **Reprodutibilidade:** versionar regras, conjuntos de avaliação e artefatos relevantes.
- **Verificação técnica:** usar testes automatizados, regressões e verificações de segurança.
- **Limites declarados:** distinguir resultados medidos, funcionalidades implementadas e trabalho ainda em desenvolvimento.

Esses princípios podem apoiar pesquisas e projetos que necessitam avaliar respostas geradas por IA. A adequação a um uso real depende de validação no domínio, qualidade das fontes, configuração, controles operacionais e revisão humana.

## O que está comprovado hoje

O repositório contém implementação de verificação, contrato do Judge 2.0, testes de regressão e conjuntos sintéticos de avaliação. Há resultados históricos documentados para Golden v0 e Golden v0.1, produzidos em inglês e voltados ao desenvolvimento do sistema.

**Ainda não há resultado de benchmark em português.** O protocolo RGC permanece em desenvolvimento e não está congelado. Resultados sintéticos não demonstram desempenho em produção nem generalização para documentos jurídicos brasileiros.

O projeto **não é apresentado como certificado**, não garante a detecção de toda alucinação e não comprova conformidade regulatória por si só. Hashes ajudam a verificar a integridade de artefatos; não provam a veracidade de seu conteúdo.

Para saber o estado mais recente, consulte o [Status técnico](docs/STATUS.md). Ele é a referência para entregas, verificações e limitações atuais; relatórios antigos descrevem somente a revisão e o commit a que se referem.

## Começar

Requer Python 3.11, 3.12 ou 3.13.

```bash
git clone https://github.com/Ayorinha/ayorai-opensearch.git
cd ayorai-opensearch
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

No Windows, ative o ambiente virtual pelo mecanismo equivalente. Para avaliações opcionais que usam backends NLI, consulte o [guia de execução](docs/GUIA-PASSO-A-PASSO.md).

## Demonstração Docker: veredito e trilha de prova

O exemplo abaixo sobe a API localmente com o provedor determinístico
`mock` e autenticação por chave. O caso é **inteiramente sintético**:
a evidência é um fixture fornecido na própria requisição, não uma fonte
externa nem uma checagem de fato do mundo real.

Requer Docker, Python e `jq`.

```bash
# Gere uma chave de demonstração e um pepper independentes.
export ATTRACTOR_DEMO_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
export ATTRACTOR_DEMO_PEPPER="$(python -c 'import secrets; print(secrets.token_hex(32))')"

# A API armazena somente o HMAC-SHA-256 da chave, nunca a chave em claro.
export ATTRACTOR_DEMO_KEY_DIGEST="$(
  ATTRACTOR_DEMO_KEY="$ATTRACTOR_DEMO_KEY" \
  ATTRACTOR_DEMO_PEPPER="$ATTRACTOR_DEMO_PEPPER" \
  python -c '
import hashlib, hmac, os
pepper = bytes.fromhex(os.environ["ATTRACTOR_DEMO_PEPPER"])
key = os.environ["ATTRACTOR_DEMO_KEY"].encode()
print(hmac.new(pepper, key, hashlib.sha256).hexdigest())
'
)"

# Construa a imagem e inicie o serviço apenas em loopback.
docker build -f docker/Dockerfile -t ayorai-attractor:local .
docker run -d --rm --name ayorai-attractor-demo \
  -p 127.0.0.1:8000:8000 \
  -e ATTRACTOR_PROVIDER=mock \
  -e ATTRACTOR_AUTH_MODE=api_key \
  -e ATTRACTOR_API_KEY_PEPPER="$ATTRACTOR_DEMO_PEPPER" \
  -e ATTRACTOR_API_KEYS_HMAC_SHA256="$ATTRACTOR_DEMO_KEY_DIGEST" \
  ayorai-attractor:local

# /health é público; os endpoints de operação exigem a chave.
curl -fsS http://127.0.0.1:8000/health | jq .

# Judge 2.0 recebe uma alegação e uma evidência sintéticas coincidentes.
# Os offsets são intervalos [início, fim) em pontos de código Unicode.
curl -fsS -X POST http://127.0.0.1:8000/v1/verify \
  -H "Authorization: Bearer $ATTRACTOR_DEMO_KEY" \
  -H "Content-Type: application/json" \
  --data-binary @- <<'JSON' | jq '.result | {
    decision_state,
    verdict,
    judge_rules_version,
    rule_trace,
    atoms,
    output_sha256
  }'
{
  "schema_version": "r2-a",
  "protocol_version": "r2-a",
  "claim_id": "demo-claim-001",
  "claim_text": "Fictional Atlas demo service launched in 2026.",
  "atoms": [
    {
      "id": "a1",
      "text": "Fictional Atlas demo service launched in 2026.",
      "start_offset": 0,
      "end_offset": 46
    }
  ],
  "evidence": [
    {
      "id": "e1",
      "claim_id": "demo-claim-001",
      "source_id": "source-demo-1",
      "source_location": "fixture://atlas-demo",
      "retrieved_at": "2026-11-04T12:00:00Z",
      "start_offset": 0,
      "end_offset": 46,
      "excerpt": "Fictional Atlas demo service launched in 2026.",
      "origin_id": "origin-demo-1"
    }
  ],
  "stances": [
    {
      "id": "s1",
      "atom_id": "a1",
      "evidence_id": "e1",
      "stance": "SUPPORTS"
    }
  ],
  "source_texts": {
    "source-demo-1": "Fictional Atlas demo service launched in 2026."
  }
}
JSON

# Encerre e remova o container de demonstração.
docker stop ayorai-attractor-demo
unset ATTRACTOR_DEMO_KEY ATTRACTOR_DEMO_PEPPER ATTRACTOR_DEMO_KEY_DIGEST
```

O resultado esperado para esse fixture é `DECIDED` com veredito
`SUPPORTED`. A resposta inclui a versão das regras, a trilha de regras
(`rule_trace`), os átomos com as evidências admitidas e o hash da saída
(`output_sha256`). O hash permite conferir a integridade do resultado;
não prova a veracidade da alegação nem a independência da evidência.

A rota `/v1/verify` aplica o Judge determinístico. Já `/v1/audit`
registra a trilha operacional do pipeline e declara explicitamente
`verdict_authority: not_adjudicated`; ela não substitui a verificação
formal. Para uso fora deste exemplo local, mantenha a autenticação
habilitada e gerencie chave e pepper como segredos distintos.

## Navegue pela documentação

A documentação foi organizada por finalidade para que cada leitor encontre o nível de detalhe adequado, sem transformar a página inicial em um inventário técnico.

- **Quero entender a solução:** [Visão geral da arquitetura](docs/ARCHITECTURE.md)
- **Quero instalar e executar:** [Guia passo a passo](docs/GUIA-PASSO-A-PASSO.md)
- **Quero verificar o estado real:** [Status técnico](docs/STATUS.md)
- **Quero conferir regras e decisões:** [Judge 2.0](docs/judge2/TRACEABILITY.md) · [Decisões de arquitetura](docs/adr/README.md)
- **Quero avaliar evidências, riscos e limites:** [Modelo de ameaças](docs/THREAT-MODEL.md) · [Considerações para o Brasil](docs/CONFORMIDADE-BRASIL.md)
- **Quero ler ou baixar o documento técnico completo:** [Documento técnico público AYORAI ATTRACTOR v1.1 (PDF)](docs/institutional/AYORAI-ATTRACTOR-Documento-Tecnico-v1.1.pdf)
- **Quero encontrar os documentos restantes:** [Índice completo da documentação](docs/INDEX.md)

## Projeto aberto e responsabilidade

O AYORAI ATTRACTOR é distribuído sob a licença [Apache-2.0](LICENSE). A documentação técnica e os artefatos de avaliação devem ser lidos considerando sua versão, escopo e limitações. O sistema apoia a análise; não substitui profissionais responsáveis, revisão humana, controles internos ou avaliação jurídica.

**Princípio do projeto:** toda conclusão relevante deve poder ser examinada à luz das evidências e das regras que a produziram.

<div align="center">

**AYORAI ATTRACTOR** · Evidência antes de conclusão.

</div>
