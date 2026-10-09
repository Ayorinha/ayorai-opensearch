# Para investidores e parceiros

> **Aviso:** este documento descreve uma oportunidade de produto e uma arquitetura de engenharia. Não constitui parecer jurídico, financeiro ou regulatório.

## Problema

Sistemas de IA podem produzir respostas convincentes sem demonstrar que cada afirmação é realmente sustentada pelas fontes citadas.

Em ambientes nos quais decisões precisam ser explicáveis e auditáveis, isso cria uma lacuna entre **resposta**, **evidência** e **decisão**.

## Solução

O ATTRACTOR transforma uma resposta de IA em unidades verificáveis:

~~~mermaid
flowchart LR
    A["Resposta de IA"] --> B["Afirmações"]
    B --> C["Evidências"]
    C --> D["Stance<br/>sustenta / contradiz / neutro"]
    D --> E["Proveniência"]
    E --> F["Clusters de evidência"]
    F --> G["Judge determinístico"]
    G --> H["Veredito auditável"]
~~~

O modelo pode auxiliar a análise. O **Judge determinístico** permanece separado e decide o estado final.

## Por que agora

A adoção de IA aumenta a necessidade de:

- rastrear a origem de uma afirmação;
- separar interpretação de autorização;
- preservar evidências;
- reproduzir avaliações;
- identificar conflitos entre fontes;
- reduzir dependência de respostas narrativas não auditáveis.

## O que a engenharia demonstra

A implementação pública permite inspecionar e auditar:

- separação entre assistência do modelo e autoridade do Judge determinístico;
- registros explícitos de evidência e proveniência;
- integridade dos artefatos congelados, endereçados por SHA-256;
- pré-registros e documentação das limitações das avaliações;
- regras e contratos de verificação versionados e testáveis.

Esses elementos demonstram decisões e controles de engenharia. Eles não equivalem a validação independente, generalização em produção, certificação regulatória ou comprovação de precisão universal.

## Resultados de desenvolvimento (não generalização)

As medições disponíveis devem ser lidas lado a lado. Golden v0.1 foi reescrito após o autor ter visto resultados por caso, fato declarado no [pré-registro](eval/PREREGISTRATION-GOLDEN-v0.1.md).

| Caminho | Golden v0 | Golden v0.1 |
|---|---:|---:|
| A | **40,00%** | **76,67%** |
| B | **43,33%** | **66,67%** |
| C | **26,67%** | **33,33%** |
| Baseline majoritária | **43,33%** | **43,33%** |

**Limitações:** conjunto de desenvolvimento; 52 documentos sintéticos, todos `en-US`; n=30 casos avaliados. No Golden v0, os ICs de 95% de A e B incluem o baseline de 43,33%. O Golden v0.1 foi reescrito após a inspeção de resultados por caso, portanto seus números não devem ser apresentados isoladamente como evidência confirmatória. A generalização para documentos genuinamente em português continua reservada ao Golden v1 oculto.

## Diferencial frente à "IA juíza"

Uma arquitetura na qual o próprio modelo produz a resposta e também decide se a resposta está correta concentra funções que deveriam permanecer separadas.

O ATTRACTOR estabelece uma fronteira:

~~~mermaid
flowchart TB
    I["Intelligence<br/>model assistance"] --> E["Evidence<br/>structured record"]
    E --> S["Stance<br/>supports / contradicts / neutral"]
    S --> J["Deterministic Judge"]
    J --> V["Final verdict"]
    V --> A["Audit trail"]
~~~

**LLM ≠ Judge.**

## Open core

~~~mermaid
flowchart LR
    CORE["Open verification core"] --> RULES["Explicit rules"]
    CORE --> EVAL["Public evaluation"]
    CORE --> PROV["Provenance"]
    CORE --> AUDIT["Audit trail"]
    CORE --> API["Integration boundary"]
~~~

A estratégia é manter o núcleo de verificação observável e reproduzível, enquanto integrações, serviços e implantação podem evoluir conforme o caso de uso.

## Plano

**Fase de pesquisa:** consolidar a verificação multilíngue e a avaliação independente.

**Fase de piloto:** integrar casos controlados, definir indicadores operacionais e medir qualidade com dados autorizados.

**Fase de produto:** transformar o núcleo de verificação em uma camada reutilizável de governança e auditoria para fluxos de IA.

## O que buscamos

- **Pilotos:** organizações interessadas em testar verificação de respostas de IA em fluxos controlados.
- **Anotadores:** especialistas para avaliação de claims, evidências e relações de suporte/contradição.
- **Investimento semente:** recursos para engenharia, avaliação e infraestrutura.
- **Fomento:** apoio para pesquisa aplicada, dados autorizados e validação independente.

## Riscos e mitigação

| Risco | Mitigação |
|---|---|
| Erro do modelo de stance | Judge separado, regras determinísticas e avaliação por categoria |
| Evidência insuficiente | <code>UNVERIFIED</code> em vez de inferência silenciosa |
| Fontes conflitantes | <code>CONFLICTING</code> e clusters de evidência |
| Viés do conjunto de desenvolvimento | Golden v1 oculto e avaliação independente |
| Direitos de uso de dados | política de proveniência e licença antes do treinamento |
| Latência e custo | caminhos graduais e medição de desempenho |
| Excesso de confiança nos resultados | divulgação explícita de limitações e status |

## Contato

Para pilotos, anotação, fomento ou parceria técnica, utilize o perfil público do projeto e os canais de contato indicados no repositório.
