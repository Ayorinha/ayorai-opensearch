# Guia passo a passo

> Este guia descreve uma execução reprodutível. Resultados devem ser registrados com commit, versão da suíte e hashes.

## Preparação

~~~bash
git clone https://github.com/Ayorinha/ayorai-opensearch.git
cd ayorai-opensearch
git checkout feat/f1-multilingual-stance
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,nli]"
~~~

No Windows, ative o ambiente virtual pelo mecanismo equivalente.

## Verificações de engenharia

Execute:

~~~bash
pytest
ruff check .
mypy src/ayorai_attractor
~~~

O estado documentado desta revisão espera **235 testes passando**.

## Conferir hashes

Golden v0:

~~~text
2613aefccf232989833b80c0d23257e6e9f312e0f6b720801a0658407b2f1c75
~~~

Golden v0.1:

~~~text
a7076512196c1ee9670478f036f7a3996fe89a483efad140ec7b985a54846fb9
~~~

Corpus:

~~~text
ce2333ccfe4003ebfc90819400beaf6a245620754deb8572c7611bd8bbb7dea3
~~~

O manifesto deve ser conferido antes de qualquer avaliação.

## Executar o caminho C

O caminho C é a ablação determinística baseada em regras.

~~~bash
attractor eval --suite golden-v0.1 --out reports/golden-v0.1.json
~~~

Resultado esperado documentado: **33.33%**.

## Executar os caminhos A e B

A é o caminho de pesquisa; B é o caminho candidato comercial.

~~~bash
pip install -e ".[dev,nli]"
python scripts/run_f1_eval.py --suite golden-v0.1
~~~

Resultados esperados:

- **A: 76.67% — research only**
- **B: 66.67% — commercial candidate**
- **Baseline: 43.33%**
- **B vs baseline: p=0.0085**

Esses resultados são de desenvolvimento e não devem ser apresentados como generalização de produção.

## E3 manual

O E3 deve ser tratado como avaliação manual/auditável, não como promoção automática.

Regras:

- registrar o commit avaliado;
- preservar a definição binária utilizada;
- registrar o conjunto avaliado;
- não ajustar regras ou limiares depois de observar o resultado;
- separar o resultado do E3 de claims sobre o Judge;
- não usar E3 para declarar generalização em português.

## Evidência da F1

Commits de referência:

~~~text
ee0f3e9
deb1d50
aa11090
22579cf
f922f01
7309a24
0ed77d2
ec7ca77
~~~

Eles representam correções, congelamento de avaliação, ajustes de métricas, proveniência, E3 e a proposta do caminho AYORAI-PT-NLI.

## Regras de prova

1. O Golden não é alterado durante a avaliação.
2. Limiares congelados não são ajustados para melhorar o resultado.
3. Pré-registros permanecem imutáveis.
4. Toda avaliação registra commit e hashes.
5. O Judge determinístico permanece como autoridade final.
6. Modelo de stance não é sinônimo de veredito.
7. Resultado de desenvolvimento não é evidência automática de generalização.
8. O Golden v1 oculto permanece fora do ciclo de desenvolvimento.

## Próximos passos

- consolidar a avaliação multilíngue;
- preparar dados autorizados para treinamento;
- validar AYORAI-PT-NLI sob regras de proveniência;
- executar avaliação independente no Golden v1;
- medir segurança, latência e auditabilidade antes de qualquer adoção operacional.
