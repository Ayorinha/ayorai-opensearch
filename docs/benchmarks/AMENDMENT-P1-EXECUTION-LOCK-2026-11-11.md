# Proposta de emenda operacional P1 — trava de execução única

- **Data:** 2026-11-11
- **Escopo:** somente o mecanismo operacional de reserva da execução P1 em DEV-B e sua integração ao workflow.
- **Autoridade:** mantenedor do AYORAI ATTRACTOR.
- **Efeito pretendido:** se aprovada explicitamente pelo mantenedor, esta emenda substituirá exclusivamente a especificação da referência de trava e da recuperação de tentativas na seção 6 do pré-registro P1. Até essa aprovação, não altera o pré-registro nem autoriza execução.

## 1. Referência persistente

Se aprovada, a reserva atômica passará a criar a referência:

`refs/heads/p1-dev-b-confirmation-lock`

A referência é uma branch técnica de bloqueio, não uma tag Git, tag de versão ou release. Ela aponta para o SHA exato do commit `main` que executou o workflow. A criação ocorre pelo endpoint Git References do GitHub; conflito ou referência preexistente significa recusa definitiva. O código confere o nome da referência, o tipo `commit` e o SHA retornado.

A referência deverá ser criada somente pelo job `p1-confirmation`, após aprovação do environment `international-benchmark-maintainer-approval`. Esse job tem `contents: write`; o job de experimentos exploratórios mantém `contents: read`. O token de escrita só é exposto ao processo de P1. A concorrência do workflow serializa chamadas P1, mas a garantia persistente é a criação atômica da referência, não o grupo de concorrência.

## 2. Semântica de uso único e falhas

Se aprovada, a primeira tentativa que ultrapassar todos os gates determinísticos e reservar a referência consumirá a única tentativa P1. Falha posterior, inclusive falha de infraestrutura, não autoriza nova tentativa automática nem remoção, movimentação ou recriação da referência. Uma eventual repetição exigiria nova decisão explícita e emenda aprovada pelo mantenedor antes de qualquer nova execução.

Se aprovada, esta regra mais conservadora substituirá a permissão de repetição por falha de infraestrutura descrita na seção 6 do pré-registro. Não há mecanismo de reset automático ou manual implícito.

## 3. Limites que permanecem inalterados

Esta proposta de emenda:
- não aprova o pré-registro P1 nem adiciona a linha de aprovação exigida pelo código;
- não aprova nem altera DEC-026, a matriz de elegibilidade, a exposição de seleção do FactCG ou a regra objetiva de coorte não estimável;
- não autoriza dispatch, cálculo, execução em DEV-B ou TEST, nem publicação de relatório;
- não altera o estimando, hipótese, métrica, bootstrap, limiares, rótulos ou classificação científica;
- mantém obrigatória a classificação **“confirmação condicional em holdout parcialmente usado (DEV-B)”**, nunca confirmação independente.

A opção `e3-confirm-dev-b` no workflow apenas torna a rota operacional explícita. Os gates científicos continuam fail-closed e devem ser aprovados separadamente pelo mantenedor.

## 4. Proteção administrativa da referência

Antes de qualquer futura execução autorizada, o mantenedor deve configurar no GitHub um ruleset de branches que proteja exatamente `p1-dev-b-confirmation-lock`, impedindo exclusão e atualização da referência por atores não autorizados. A proteção administrativa não é criada por esta alteração de código e não se presume ativa. Sem evidência dessa regra, a trava não deve ser considerada resistente à exclusão administrativa.

## 5. Evidência e estado

A implementação proposta correspondente:
- usa branch ref, nunca `refs/tags`;
- separa permissões de escrita do job P1 dos jobs read-only;
- passa o token de escrita apenas ao passo P1;
- valida no workflow a classificação obrigatória e a saída agregada;
- mantém concorrência sem cancelamento automático.

**Estado:** emenda operacional proposta para revisão do mantenedor. Não é autorização de execução P1. DEV-B e TEST permanecem intocados.
