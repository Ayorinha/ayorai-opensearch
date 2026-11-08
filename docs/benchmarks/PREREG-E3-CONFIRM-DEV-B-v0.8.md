# Pré-registro P1 — Confirmação da E3b-01 em DEV-B (v0.8)

**Status:** PR Draft; pré-registro documental proposto. Não aprovado para execução até revisão e aprovação explícita do mantenedor.  
**Autoria:** ANDERSON AYORA  
**Decisões aplicáveis:** DEC-024, opção B (somente calibração monotônica, limiares e regra fixa); DEC-025 (uso único do DEV-B como holdout confirmatório da E3b-01).  
**Escopo desta PR:** somente documentação. Não implementa código, não dispara workflow e não produz resultado.

> **Regra temporal:** este documento é escrito antes de qualquer cálculo do ensemble em DEV-B. Nenhum resultado em DEV-B de qualquer configuração E3 foi produzido ou consultado. O único resultado E3 existente é o exploratório em DEV-A (`reports/benchmarks/2026-11-08-e3-exploratory/`, run 42485634513, `report_sha256` 43dcd7ef…).

## 1. Por que esta confirmação existe

O E3 exploratório avaliou seis candidatos em DEV-A e selecionou o melhor (E3b-01: FactCG + MiniCheck, média dos logits), com ganho de +0,0136 de BA macro sobre o FactCG pelo mesmo pipeline. Selecionar o máximo entre vários candidatos produz viés otimista (*winner's curse*). Um ganho só passa a ser tratado como efeito real se for reproduzido em dados que não participaram da seleção, com hipótese, métrica e critério fixados antes.

Esta é **uma única hipótese**, testada **uma única vez**, em DEV-B.

## 2. Hipótese única

- **H1:** a E3b-01 tem BA macro maior que a do FactCG em DEV-B, nas coortes comuns.
- Nenhuma outra configuração (E3a-01, 03, 04, 02, 05) é avaliada em DEV-B. Não há escolha posterior entre regras, membros ou variantes.

## 3. Dados e partição

- Cache cifrado de scores DEV produzido pelo run **42477997402** (re-agregação verificada; manifesto `deb3ef389553a03bb840e03a1e314e3f4d02dac50f4aa3d1c713c88a9dd55a74`; 30.420 registros; replay da Calibration V2 idêntico nos runs 42480384607 e 42483517733).
- Partição DEV-A/DEV-B determinística da Calibration V2 (`split_dev_a_b`), sem alteração.
- **DEV-A:** usado para calibrar e escolher limiares (já usado na seleção exploratória).
- **DEV-B:** usado uma única vez, só para avaliação.
- **TEST:** não é usado.

## 4. Pipeline fixo (sem parâmetros aprendidos de rótulos de DEV-B)

1. **Membros:** `factcg`, `minicheck`. **Regra:** E3b — média dos logits das probabilidades IVAP, com clipping fixo em [1e-6, 1 − 1e-6] (seção 4.2 do pré-registro E3).
2. **Elegibilidade:** `configs/benchmarks/e3-eligibility-v0.8.json` exatamente como na `main` em `ba65753382cecdff0403461becc976916e30d4b8` (sha256 do arquivo `8b7becf74727a1ad1d52706760c9682b04bd1805476bf3c0c0adddefa1f569f4`). Coortes comuns: as 10 em que o FactCG é elegível (Wice excluída). Nessas 10, os dois membros são elegíveis.
3. **Calibração para DEV-B:** para cada membro, um calibrador IVAP ajustado em **todo o DEV-A** (scores e rótulos de DEV-A) produz as probabilidades de DEV-B. Implementação: IVAP exato (`e3_ivap.ivap`), equivalente à referência da Calibration V2.
4. **Limiares:** probabilidades IVAP fora-do-fold de DEV-A (os mesmos 5 folds de `crossfit_folds`), combinadas pela regra E3b; limiar por coorte escolhido em todo o DEV-A com `calibrate_by_cohort` (grade 0,01–0,99; empate → menor limiar).
5. **Avaliação:** aplicar em DEV-B os limiares do passo 4 às probabilidades combinadas do passo 3; BA por coorte; BA macro = média aritmética das 10 coortes.
6. **Comparador:** FactCG sozinho pelo **mesmo** pipeline (passos 3–5 com um membro).

Nenhum limiar, calibrador, clipping, membro ou regra usa rótulos de DEV-B.

## 5. Estatística e critério de decisão

- **Estimativa:** Δ = BA_macro(E3b-01) − BA_macro(FactCG) em DEV-B.
- **IC95% primário — bootstrap pareado estratificado por coorte:** em cada réplica, reamostrar com reposição os registros de DEV-B **dentro de cada coorte** (mesmo tamanho da coorte), aplicando a mesma reamostragem aos dois braços; recalcular Δ. 2.000 réplicas, `numpy.random.Generator(PCG64(20261109))`, percentis 2,5% e 97,5% com `method="linear"`. As coortes são fixas (a pergunta é sobre estas 10 coortes); a incerteza vem dos casos.
- **Réplica inválida:** se uma coorte reamostrada ficar sem uma das classes, a réplica é inválida; reportar a contagem. Mais de 5% inválidas → IC declarado não estimável e H1 **não confirmada**.
- **Secundário (descritivo, sem efeito na decisão):** bootstrap por cluster de coorte, igual ao do E3 (2.000 réplicas, PCG64(20261108)), e BA por coorte dos dois braços.

**Decisão (fixa):**

| Resultado | Condição |
|---|---|
| **CONFIRMADO** | Δ ≥ 0,005 **e** limite inferior do IC95% primário > 0 |
| **NÃO CONFIRMADO** | qualquer outro caso |
| **EVIDÊNCIA CONTRÁRIA** (subcaso de não confirmado) | limite superior do IC95% primário < 0 |

Se **CONFIRMADO**, a E3b-01 passa a ser o candidato principal para a execução única no TEST (que exigirá pré-registro e autorização próprios). Se **NÃO CONFIRMADO**, o FactCG continua o baseline; o resultado exploratório permanece publicado como exploratório e nenhuma outra configuração é testada em DEV-B.

**Expectativa (registrada antes, não usada na decisão):** pelo viés de seleção, o ganho verdadeiro provavelmente é menor que +0,0136; um valor entre +0,005 e +0,012 é plausível. Um resultado abaixo de 0,005 é possível e será publicado da mesma forma.

## 6. Execução

- Uma execução, via workflow protegido `phase1b-dev-cache-experiment.yml` com o experimento `e3-confirm-dev-b`, disparada e aprovada manualmente pelo mantenedor, na `main`, com `cache_run_id = 42477997402`.
- O código recusa a execução se este documento não tiver a linha `**Status:** Aprovado pelo mantenedor em AAAA-MM-DD`.
- Nova execução só por falha de infraestrutura (sem relatório gerado), com o mesmo código e o mesmo cache; todas as tentativas são reportadas. Uma execução que produziu relatório não pode ser repetida para obter outro resultado.
- Saída somente agregada; nenhum dado por instância.

## 7. Relação com a Calibration V2

- A certificação LTT já publicada (DEV-B, FactCG) não é alterada.
- Se, no futuro, a E3b-01 for certificada por LTT em DEV-B, o relatório deverá declarar que DEV-B também foi usado nesta confirmação (mesma amostra para confirmação e certificação).
- A ampliação do uso de DEV-B é registrada na DEC-025 e limita-se a esta hipótese.

## 8. Relato obrigatório

Publicar, independentemente do resultado: Δ, IC95% primário, contagem de réplicas inválidas, BA por coorte dos dois braços, limiares usados por coorte, IC secundário por cluster, SHA do código, run do cache, run da execução, `report_sha256`, e a classificação CONFIRMADO / NÃO CONFIRMADO. Não omitir resultado negativo.

**Estado final:** proposta fechada para revisão. A execução exigirá aprovação explícita do mantenedor neste documento.
