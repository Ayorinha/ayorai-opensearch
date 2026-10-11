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
- **art. 20:** direito de solicitar a revisão de decisões tomadas unicamente com base em tratamento automatizado, quando aplicável;
- **art. 37:** registro das operações de tratamento;
- **art. 46:** medidas de segurança técnicas e administrativas;
- **art. 50:** boas práticas e governança.

O projeto deve ser usado como componente técnico de um programa mais amplo. **Não se declara "conformidade com a LGPD" apenas pela adoção do ATTRACTOR.**

## PL 2.338/2023

**Status consultado em 11/10/2026:** aprovado no Senado; em tramitação na Câmara dos Deputados. A ficha oficial informa que aguarda parecer do relator na Comissão Especial e registra como última ação a apensação de 02/09/2026. Consulte a [ficha oficial da Câmara dos Deputados](https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao=2487262) e reconfirme o andamento na data de cada nova publicação.

O ATTRACTOR pode apoiar mecanismos de documentação, rastreabilidade e avaliação, mas não substitui obrigações legais futuras ou controles específicos que venham a ser exigidos.

## Auditoria e evidência

Para trabalhos de auditoria, a arquitetura pode apoiar:

- identificação da afirmação analisada;
- registro da evidência usada;
- preservação de offsets e proveniência;
- hashes SHA-256;
- reprodução da regra de decisão;
- separação entre análise do modelo e autoridade do Judge.

Este documento não estabelece conformidade com normas profissionais de auditoria; referências específicas só devem ser incluídas após conferência de fonte primária oficial e da edição vigente.

## Governança de IA

O **AI Act**, especialmente os arts. **12–14**, e a **ISO/IEC 42001** reforçam temas como registros, transparência, supervisão humana e sistema de gestão de IA.

O ATTRACTOR pode apoiar esses objetivos por meio de:

- trilhas de evidência;
- registros reproduzíveis;
- separação de responsabilidades;
- avaliação documentada;
- mecanismos de revisão.

Isso não significa que o projeto, isoladamente, atenda a qualquer regime regulatório.

## Domínio jurídico delimitado

O domínio jurídico previsto para avaliação futura é a regulação de telecomunicações, começando pelo Regulamento Geral de Direitos do Consumidor de Serviços de Telecomunicações (RGC), aprovado pela Resolução Anatel nº 765/2023 ([fonte primária da Anatel](https://informacoes.anatel.gov.br/legislacao/resolucoes/2023/1900-resolucao-765%29)). Esta referência delimita um possível corpus de avaliação; não indica parceria, apoio ou validação pela Anatel.

O escopo não promete análise geral do setor público, auditoria de órgãos federais, interpretação jurídica, hierarquia normativa, revogação ou análise jurisprudencial. O Judge permanece determinístico: referências normativas estruturais e datas de vigência podem ser metadados, não conclusões jurídicas.

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

## Fontes normativas oficiais

- **LGPD — Lei nº 13.709/2018, art. 20:** o titular tem o direito de solicitar a revisão de decisões tomadas unicamente com base em tratamento automatizado. A lei não deve ser descrita aqui como exigindo revisão humana. [Texto oficial no Planalto](https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm). A aplicação depende do contexto concreto de tratamento.
- **PL 2.338/2023:** [tramitação oficial na Câmara dos Deputados](https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao=2487262). Verificar o andamento atual no momento da consulta.
- **Regulamento Europeu de IA (Regulamento (UE) 2024/1689):** [texto oficial no EUR-Lex](https://eur-lex.europa.eu/eli/reg/2024/1689/oj). A aplicabilidade depende do âmbito e das datas de aplicação pertinentes.
- **ISO/IEC 42001:** [página oficial da ISO](https://www.iso.org/standard/81230.html). A referência à norma não significa que o projeto seja certificado.
- **NBC TA 500 e NBC TA 230:** confirmar edição vigente e contexto de aplicação junto às fontes profissionais oficiais antes de usar como fundamento formal de auditoria.

**Status:** ferramenta de engenharia e pesquisa, não certificação.
