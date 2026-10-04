# Conformidade no Brasil

> **Aviso:** este documento é técnico e informativo. Não constitui parecer jurídico nem certificação de conformidade.

## Objetivo

O ATTRACTOR foi desenhado para **apoiar** processos que exigem rastreabilidade, preservação de evidências, controle de acesso, auditoria e reprodução de resultados.

Ele não substitui análise jurídica, controles internos, políticas de governança ou avaliações específicas do ambiente de implantação.

## Mapa de requisitos e recursos

~~~mermaid
flowchart LR
    A["Requisitos de governança"] --> B["Proteção de dados"]
    A --> C["Rastreabilidade"]
    A --> D["Segurança"]
    A --> E["Explicabilidade e revisão"]
    B --> F["Minimização e finalidade"]
    C --> G["Claims + evidence + provenance"]
    D --> H["Regras determinísticas + controle"]
    E --> I["Judge + proof trail"]
~~~

## LGPD

A arquitetura pode apoiar controles relacionados a:

- **art. 6º, VI:** transparência;
- **art. 6º, X:** responsabilização e prestação de contas;
- **art. 20:** revisão de decisões automatizadas, quando aplicável;
- **art. 37:** registro das operações de tratamento;
- **art. 46:** medidas de segurança técnicas e administrativas;
- **art. 50:** boas práticas e governança.

O projeto deve ser usado como componente técnico de um programa mais amplo. **Não se declara "conformidade com a LGPD" apenas pela adoção do ATTRACTOR.**

## PL 2.338/2023

O **PL 2.338/2023** foi aprovado no Senado em dezembro de 2024 e permanece em tramitação na Câmara. O texto e seu status legislativo devem ser verificados no momento de qualquer decisão de produto ou implantação.

O ATTRACTOR pode apoiar mecanismos de documentação, rastreabilidade e avaliação, mas não substitui obrigações legais futuras ou controles específicos que venham a ser exigidos.

## Auditoria e evidência

Para trabalhos de auditoria, a arquitetura pode apoiar:

- identificação da afirmação analisada;
- registro da evidência usada;
- preservação de offsets e proveniência;
- hashes SHA-256;
- reprodução da regra de decisão;
- separação entre análise do modelo e autoridade do Judge.

Referências técnicas de auditoria incluem **NBC TA 500** para evidência de auditoria e **NBC TA 230** para documentação de auditoria, conforme o contexto profissional aplicável.

## Governança de IA

O **AI Act**, especialmente os arts. **12–14**, e a **ISO/IEC 42001** reforçam temas como registros, transparência, supervisão humana e sistema de gestão de IA.

O ATTRACTOR pode apoiar esses objetivos por meio de:

- trilhas de evidência;
- registros reproduzíveis;
- separação de responsabilidades;
- avaliação documentada;
- mecanismos de revisão.

Isso não significa que o projeto, isoladamente, atenda a qualquer regime regulatório.

## Setores e vereditos úteis

| Contexto | Vereditos especialmente úteis |
|---|---|
| Serviços financeiros | <code>VERIFIED</code>, <code>SUPPORTED</code>, <code>CONFLICTING</code>, <code>UNVERIFIED</code> |
| Mercado de capitais | <code>VERIFIED</code>, <code>CONFLICTING</code>, <code>REFUTED</code> |
| Seguros | <code>SUPPORTED</code>, <code>PARTIALLY_SUPPORTED</code>, <code>UNVERIFIED</code> |
| Jurídico e compliance | <code>SUPPORTED</code>, <code>REFUTED</code>, <code>CONFLICTING</code> |
| Setor público | <code>VERIFIED</code>, <code>UNVERIFIED</code>, <code>CONFLICTING</code> |
| Auditoria interna | todos, conforme o caso de uso |

## O que ainda falta

Antes de uma implantação regulada, ainda são necessários, conforme o caso:

- análise jurídica específica;
- definição de controlador, operador e responsabilidades;
- avaliação de impacto e riscos;
- políticas de retenção e descarte;
- controles de acesso e segregação;
- gestão de incidentes;
- validação independente;
- evidência operacional em ambiente real;
- testes de segurança e continuidade;
- governança de modelos e dados;
- critérios de aprovação para uso em decisões de alto impacto.

**Status:** ferramenta de engenharia e pesquisa, não certificação.
