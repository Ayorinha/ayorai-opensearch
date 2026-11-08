# Reagregação Phase 1b — resultado exploratório e análise de poder LTT

**Classificação:** EXPLORATÓRIO · PÓS-HOC · DEV  
**Data do registro:** 2026-11-08  
**Autoria e responsabilidade:** ANDERSON AYORA  
**Escopo:** registro documental. Não altera o pré-registro vigente, código, dados, modelos, thresholds, Judge, Golden, RGC, Piloto 02 ou ResponsePolicy. Não autoriza execução TEST.

> **Conclusão de leitura:** a reaggregação manteve as Camadas 1 e 2 idênticas à v0.7.0 e, sob a Emenda 2, quatro coortes passaram pelo LTT em DEV. Este resultado é exploratório porque a regra foi emendada depois de observado DEV-B. O resultado oficial da v0.7.0 permanece **0/11 pela regra original**. Nenhuma das quatro coortes é aqui declarada confirmatoriamente certificada.

## 1. Proveniência e integridade

| Campo | Valor |
|---|---|
| Execução original de inferência | [42389121599](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/42389121599) |
| Execução de reaggregação exploratória | [42436331559](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/42436331559) |
| SHA do código da reaggregação | `caa912cb836e2c263b22c5693ce6f8ccc5fd2ef5` |
| Run de origem | `42389121599` |
| `manifest_sha256` | `deb3ef389553a03bb840e03a1e314e3f4d02dac50f4aa3d1c713c88a9dd55a74` |
| `report_sha256` | `43b45a752a464e11431752cb21f7ffc8c6e2821a6eded66401dc6c863f3c647c` |
| SHA-256 esperado de `phase1b-aggregate.json` | `9260e4d3033cee02e29d9e2978d9a177a3924705369580b8ac9e5fd49676c9a0` |
| SHA-256 esperado de `PROVENANCE.json` | `3ebf003fa563ec875e25d3b648f15b16fd12827cdee325ccd96f9b1cf81c9a22` |

Os arquivos originais do artefato `phase1b-dev-full-aggregate` da run 42436331559 estão nesta pasta, sem modificação: [`phase1b-aggregate.json`](phase1b-aggregate.json) e [`PROVENANCE.json`](PROVENANCE.json). **Conferência do revisor (2026-11-08):** os SHA-256 dos dois arquivos correspondem aos valores acima; o arquivo não contém `record_id` nem `records`; as Camadas 1 e 2 (`model_selection` e `models`) são idênticas, campo a campo, às do relatório da v0.7.0; `ltt_rule = "amendment-2-skip-ineligible"`.

A execução de reaggregação não realizou nova inferência: ela reprocessou os artefatos cifrados originados na run 42389121599. Não há dados individuais neste documento.

## 2. Resultado das Camadas 1 e 2

As duas primeiras camadas permaneceram idênticas à v0.7.0:

| Camada | Resultado | Comparação |
|---|---:|---|
| Modelo selecionado | FactCG | Inalterado |
| BA cross-fitted de FactCG | **0,7468 (74,68%)** | Idêntica |
| ECE | **0,0054** | Idêntico |

A Emenda 2 não alterou seleção de modelo, calibração ou métricas das Camadas 1 e 2. Essa invariância é uma verificação importante de escopo, mas não transforma o resultado da Camada 3 em confirmação independente.

## 3. Camada 3 — quatro coortes passaram pela regra emendada

A regra executada foi `ltt_rule = "amendment-2-skip-ineligible"`. Os valores abaixo são agregados por coorte.

| Coorte | Limiar | Acerto entre aceitas | Cobertura |
|---|---:|---:|---:|
| RAGTruth | 0,56 | **92,7%** | **91,6%** |
| ClaimVerify | 0,86 | **94,6%** | **67,2%** |
| Lfqa | 0,89 | **93,7%** | **45,2%** |
| Reveal | 0,92 | **95,6%** | **32,6%** |

RAGTruth é especialmente relevante por representar uma coorte de respostas baseadas em recuperação (RAG). Neste DEV exploratório, a combinação de acerto observado e cobertura foi de 92,7% e 91,6%, respectivamente. A formulação correta é que a coorte **passou pelo procedimento LTT emendado nesta reaggregação exploratória**. Não afirmar que o desempenho foi certificado confirmatoriamente ou que a garantia já foi validada em TEST.

## 4. Sete coortes sem aprovação no primeiro limiar testado

Os valores de `p` são p-valores da cauda binomial inferior, calculados sob a hipótese nula de risco de 10%, e comparados com $\alpha_c = 0{,}05/11 \approx 0{,}004545$. Não são taxas de erro observadas.

| Coorte | Primeiro limiar testado | Aceitas (n) | Erros | Acerto observado | p-valor |
|---|---:|---:|---:|---:|---:|
| AggreFact-CNN | 0,97 | 74 | 6 | 91,9% | 0,382 |
| AggreFact-XSum | 0,97 | 31 | 3 | 90,3% | 0,624 |
| ExpertQA | 0,98 | 59 | 7 | 88,1% | 0,766 |
| FactCheck-GPT | 0,98 | 38 | 2 | 94,7% | 0,254 |
| TofuEval-MediaS | 0,98 | 34 | 2 | 94,1% | 0,326 |
| TofuEval-MeetB | 0,96 | 28 | 1 | 96,4% | 0,215 |
| Wice | 0,95 | 25 | 3 | 88,0% | 0,764 |

Nenhum desses p-valores ficou abaixo de 0,004545. Portanto, o teste não rejeitou a hipótese nula no primeiro limiar testado e a sequência foi encerrada conforme a regra fixed-sequence.

**Interpretação equilibrada:** em cinco dessas sete coortes, o acerto observado no primeiro limiar foi superior a 90%, mas a evidência não foi suficiente para rejeitar a hipótese nula com o ajuste familiar aplicado. Em ExpertQA e Wice, o acerto observado nesse limiar também ficou abaixo de 90%. Logo, não é correto atribuir automaticamente as sete não aprovações apenas à falta de poder estatístico, nem concluir que o modelo falhou em todas elas. A não rejeição significa insuficiência de evidência para a garantia requerida naquele teste; não prova que o risco verdadeiro excede 10%, nem prova que é inferior a 10%.

## 5. O que significam 52, 91 e 196 casos

O código vigente implementa `_binomial_lower_tail_pvalue(errors, n)` em `scripts/benchmarks/phase1b/calibration_v2/selective_ltt.py`. A função calcula:

$$
P_{p_0=0{,}10}(X \le e), \quad X \sim \operatorname{Binomial}(n, 0{,}10)
$$

A rejeição ocorre quando esse valor é menor ou igual a:

$$
\alpha_c = \frac{0{,}05}{11} \approx 0{,}00454545.
$$

Os números 52, 91 e 196 são tamanhos mínimos para **rejeitar a hipótese nula dado um número observado de erros compatível com determinada proporção**. Foram reproduzidos com a CDF binomial exata e a regra:

$$
P(\operatorname{Bin}(n,0{,}10) \le \lfloor r n \rfloor) \le 0{,}05/11.
$$

| Erro observado de referência $r$ | Menor n | Erros observados usados no cálculo | p-valor sob $p_0=10\%$ |
|---:|---:|---:|---:|
| 0% | 52 | 0 | 0,004175 |
| 3% | 91 | 2 | 0,004228 |
| 5% | 196 | 9 | 0,004523 |

Esses valores **não são cálculos de poder**. Eles respondem: “dado este número observado de erros, qual é o menor n em que o teste pode rejeitar?”. Não respondem: “se a taxa verdadeira de erro for p1, qual a chance de o teste rejeitar?”.

## 6. Análise de poder: cálculo correto

Para cada tamanho amostral $n$, definir o maior número crítico de erros:

$$
k_{\mathrm{crit}}(n)=\max\{k: P_{0{,}10}(X\le k)\le 0{,}05/11\}.
$$

Se não existir tal $k$, o teste não pode rejeitar para aquele n e o poder é zero. Para uma taxa verdadeira alternativa $p_1$, o poder é:

$$
\operatorname{Power}(n,p_1)
=P_{p_1}(X\le k_{\mathrm{crit}}(n)),
\quad X\sim\operatorname{Binomial}(n,p_1).
$$

O cálculo mantém o teste unilateral exato, o limite de risco $p_0=10\%$ e o ajuste familiar $\alpha_c=0{,}05/11$. Não altera a regra de aceitação.

### 6.1 Tabela de poder

| n de respostas aceitas | $k_{\mathrm{crit}}$ | Poder se $p_1=3\%$ | Poder se $p_1=5\%$ | Poder se $p_1=7\%$ |
|---:|---:|---:|---:|---:|
| 25 | — | 0,00% | 0,00% | 0,00% |
| 50 | — | 0,00% | 0,00% | 0,00% |
| 75 | 1 | 33,80% | 10,56% | 2,88% |
| 100 | 2 | 41,98% | 11,83% | 2,58% |
| 125 | 4 | 67,83% | 24,59% | 5,76% |
| 154 | 6 | 81,82% | 34,56% | 8,04% |
| 200 | 9 | 91,92% | 45,47% | 10,10% |
| 250 | 12 | 95,98% | 51,75% | 10,32% |
| 300 | 16 | 99,00% | 66,66% | 15,36% |
| 342 | 20 | 99,82% | 80,38% | 23,74% |
| 400 | 24 | 99,94% | 84,90% | 25,11% |
| 500 | 32 | 100,00% | 93,36% | 33,81% |
| 750 | 53 | 100,00% | 99,46% | 56,48% |
| 1.051 | 80 | 100,00% | 99,99% | 80,04% |

O caráter discreto do teste importa: o poder não cresce de forma estritamente monotônica a cada incremento de n. Por exemplo, para $p_1=5\%$, o poder é 80,38% em n=342, 80,02% em n=343 e cai para 79,66% em n=344, até o próximo salto de $k_{\mathrm{crit}}$. Portanto, escolher simplesmente o primeiro n que cruza 80% pode deixar tamanhos amostrais imediatamente maiores abaixo de 80%.

### 6.2 Proposta de cenário de planejamento e mínimo operacional

Recomenda-se discutir $p_1=5\%$ como cenário de planejamento: é metade do limite máximo de risco de 10%, representando um desempenho substancialmente melhor que o limite que se pretende garantir. Essa escolha é uma decisão de desenho baseada no limite de risco pré-existente e no alvo convencional de poder de 80%; **não foi escolhida olhando quais coortes passariam**.

Para evitar a oscilação do poder causada pelos valores críticos inteiros, a análise numérica procurou o menor piso N tal que o poder permanecesse ≥80% para todos os tamanhos amostrais avaliados a partir desse piso (varredura reproduzível até n=15.206 (tamanho total de DEV-B nesta execução, portanto um limite superior conservador para qualquer coorte)):

| Alternativa verdadeira $p_1$ | Primeiro n isolado com poder ≥80% | Piso operacional robusto N | Poder em N | Menor poder observado para n ≥ N na varredura |
|---:|---:|---:|---:|---:|
| 3% | 154 | 168 | 86,56% | 82,10% (n=181) |
| **5%** | **342** | **367** | **84,04%** | **80,18% (n=379)** |
| 7% | 1.051 | 1.108 | 82,57% | 80,33% (n=1.118) |

**Proposta para deliberação na v0.8:** elevar o mínimo de respostas aceitas para o primeiro teste LTT de 25 para **367 por coorte**, condicionado à revisão independente do cálculo e à confirmação de que as premissas binomiais são adequadas. O número 367 é uma proposta metodológica, não uma regra vigente ou congelada.

O cálculo de poder pressupõe, para cada limiar fixo, erros Bernoulli independentes com taxa verdadeira $p_1$, e a mesma estrutura binomial usada no teste. Dependência entre observações, agrupamento por fonte, correlação entre itens ou desvio da distribuição binomial pode reduzir o poder real e comprometer a interpretação do teste. A revisão da v0.8 deve verificar a unidade amostral e a plausibilidade da independência/exchangeability; se a premissa não for defensável, não basta aumentar N: será necessário um desenho estatístico adequado, com decisão explícita e pré-registro próprio.

### 6.3 Esboço reproduzível do cálculo

A tabela pode ser reproduzida com a CDF binomial exata. O exemplo abaixo explicita o cálculo de $k_{crit}$, poder e piso robusto; deve ser executado com a versão de SciPy fixada no ambiente de análise e os valores resultantes arquivados no pacote de revisão:

```python
import numpy as np
from scipy.stats import binom

alpha_cohort = 0.05 / 11
risk_null = 0.10
power_target = 0.80
n_max = 15_206
n = np.arange(1, n_max + 1)

# ppf(alpha) é o menor k cuja CDF alcança alpha;
# por isso kcrit = ppf(alpha) - 1.
k_crit = binom.ppf(alpha_cohort, n, risk_null).astype(int) - 1

def power_curve(p_true):
    return np.where(k_crit >= 0, binom.cdf(k_crit, n, p_true), 0.0)

for p_true in (0.03, 0.05, 0.07):
    power = power_curve(p_true)
    # O piso exige poder >=80% em todo n >= N até o máximo DEV-B.
    suffix_min = np.minimum.accumulate(power[::-1])[::-1]
    candidates = np.flatnonzero(suffix_min >= power_target)
    n_floor = int(candidates[0] + 1) if len(candidates) else None
    print(p_true, n_floor, suffix_min[n_floor - 1] if n_floor else None)
```

O cálculo acima usa a mesma hipótese nula e o mesmo $\alpha_c$ do LTT; a distribuição sob $p_1$ é usada somente para calcular poder. O piso robusto evita escolher um n isolado no qual o poder ultrapasse 80% por um salto discreto, mas caia novamente para n ligeiramente maior.

### 6.4 Informação usada e controle de circularidade

A escolha ilustrativa de $p_1=5\%$ e a proposta de piso 367 foram motivadas por:

1. limite de risco já fixado em 10%;
2. escolha de um cenário alternativo equivalente à metade desse limite;
3. nível familiar de 5% com Bonferroni em onze coortes;
4. poder-alvo de 80%;
5. comportamento discreto do teste binomial exato.

Não foram usados para escolher 5% ou 367: a identidade das coortes aprovadas, os erros observados por coorte, os limiares certificados, as coberturas observadas ou a comparação de quais coortes passariam em diferentes valores de N.

O DEV pode informar o planejamento amostral, pois essa é a finalidade da partição de desenvolvimento. A vedação é escolher N após examinar quais coortes específicas passariam com cada valor. A justificativa, o cálculo, o código de reprodução, o N escolhido e a regra de elegibilidade devem ser registrados e congelados **antes de qualquer acesso ao TEST**.

### 6.5 Verificação independente e viabilidade por coorte (nota do revisor)

**Verificação:** o revisor recalculou de forma independente $k_{crit}$, os primeiros n com poder ≥ 80% (154, 342 e 1.051) e os pisos robustos (168, 367 e 1.108), e conferiu $k_{crit}$ em n = 75, 100, 154, 200, 342 e 367 contra `_binomial_lower_tail_pvalue` do repositório. Os valores conferem.

**Consequência a decidir explicitamente:** um piso de N aceitas torna **estruturalmente impossível** testar qualquer coorte cujo tamanho total seja menor que N, independentemente do desempenho. Em DEV-B, os tamanhos por coorte foram: Wice 174; AggreFact-CNN 229; AggreFact-XSum 388; ClaimVerify 546; ExpertQA 1.886; FactCheck-GPT 768; Lfqa 1.014; RAGTruth 7.670; Reveal 828; TofuEval-MediaS 900; TofuEval-MeetB 803. Com N = 367, Wice e AggreFact-CNN não poderiam ser testadas em DEV-B, e coortes com cobertura baixa também ficariam inelegíveis. A decisão da v0.8 deve declarar isso como custo assumido do desenho (essas coortes seriam reportadas como "não testáveis pelo desenho"), sem criar exceções por coorte. Tamanhos de coorte são metadados de desenho; esta nota não usa resultados por coorte para escolher N.

## 7. Proposta para v0.8: separar mínimo amostral de regra de aceitação

### 7.1 Alteração recomendada — mínimo de amostras (preserva a garantia)

A única mudança recomendada para a v0.8 nesta etapa é aumentar o mínimo de aceitas exigido para que um limiar seja elegível ao teste, mantendo:

- risco máximo $p_0=10\%$;
- nível familiar $\delta=0{,}05$;
- Bonferroni em onze coortes ($0{,}05/11$);
- teste binomial exato e sua definição;
- sequência de limiares e ordem atual;
- regra fixed-sequence: parar na primeira não rejeição;
- critérios de classificação, calibração e abstenção;
- ausência de piso de cobertura.

Com o mínimo proposto de 367, limiares com menos de 367 aceitas seriam pulados como inelegíveis, nunca certificados. A elegibilidade deve continuar dependendo somente das probabilidades/contagens de aceitas, nunca dos rótulos. Essa mudança posterga o início dos testes; não relaxa o teste nem altera a promessa estatística. Pode resultar em mais coortes sem certificação quando não houver amostra suficiente.

A proposta só poderá ser adotada depois de revisão do cálculo, validação das premissas e congelamento prévio. A PR atual não altera o valor 25 no código nem no pré-registro.

### 7.2 Alternativas não adotadas — mudanças na regra (alteram a garantia)

As alternativas abaixo ficam registradas apenas para distinguir decisões futuras:

- **Bonferroni também sobre os limiares:** amplia a família de hipóteses e torna o critério mais conservador; muda o procedimento e a garantia.
- **Holm:** substitui o ajuste atual por outro procedimento de controle de multiplicidade; requer definição da família, ordenação e prova de validade no desenho específico.
- **Testar todos os limiares sem parar na primeira não rejeição:** abandona a sequência fixed-sequence atual e exige tratamento explícito da multiplicidade entre limiares; altera a garantia.
- **Afrouxar ou remover Bonferroni entre coortes:** muda o controle do erro familiar e a promessa simultânea para as onze coortes.

Nenhuma dessas alternativas é recomendada ou adotada nesta proposta. Não misturar uma alteração de mínimo amostral com uma alteração do teste.

## 8. Status, limitações e linguagem autorizada

- A aplicação da Emenda 2 à mesma DEV-B é **exploratória e pós-hoc**.
- O resultado oficial da v0.7.0 permanece **0/11 pela regra original**.
- As quatro coortes da seção 3 passaram pelo procedimento emendado nesta reaggregação, mas não são certificações confirmatórias.
- A análise de poder é uma proposta para planejar a v0.8, não uma mudança já aprovada.
- O limite de risco permanece 10%; o nível familiar permanece 5% com Bonferroni em onze coortes.
- Não houve inspeção, ajuste ou execução de TEST.
- Nenhum dado individual é incluído.
- A confirmação estatística futura exige pré-registro congelado antes de TEST, execução única e avaliação de acordo com os critérios previamente fixados.

Formulação pública permitida:

> “Na reaggregação exploratória pós-hoc de DEV, quatro das onze coortes passaram pelo procedimento LTT após a Emenda 2. As Camadas 1 e 2 permaneceram idênticas à v0.7.0. O resultado oficial da v0.7.0 continua sendo 0/11 pela regra original. A confirmação depende de pré-registro congelado e avaliação futura em TEST.”

Não usar “quatro coortes certificadas” sem o qualificador exploratório/pós-hoc. Não afirmar garantia de produção, generalização ou certificação TEST.

## 9. Checklist para revisão e fechamento

- [x] Mantenedor/revisor adiciona os arquivos originais `phase1b-aggregate.json` e `PROVENANCE.json`, sem reconstrução.
- [x] Conferir SHA-256 dos dois arquivos com os valores da seção 1.
- [ ] Revisar os p-valores e os resultados agregados contra o relatório de origem.
- [ ] Revisar independentemente o cálculo de poder, o piso robusto 367 e as premissas de independência.
- [ ] Confirmar que a proposta não altera risco, alfa, Bonferroni, sequência ou parada.
- [ ] Confirmar que o resultado original 0/11 da v0.7.0 permanece intacto.
- [ ] Confirmar ausência de dados individuais.
- [ ] Manter esta PR como documentação exploratória; sem merge, release, DOI ou dispatch nesta etapa.

---
**Estado final deste documento:** registro exploratório e proposta metodológica para deliberação. Não congela o pré-registro v0.8, não altera a implementação, não autoriza TEST e não publica certificação.
