# Guia passo a passo

> Este guia descreve uma execução reprodutível. Resultados devem ser registrados com commit, versão da suíte e hashes.

## Preparação

~~~bash
git clone https://github.com/Ayorinha/ayorai-opensearch.git
cd ayorai-opensearch
git switch main
# Para a versão estável v0.5.0, use: git switch --detach v0.5.0
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
~~~

Optional NLI backends (downloads large model dependencies): `pip install -e ".[dev,nli]"`.

No Windows, ative o ambiente virtual pelo mecanismo equivalente.

## Verificações de engenharia

Execute:

~~~bash
pytest
ruff check .
mypy src/ayorai_attractor
~~~

Todos os testes devem passar; o número atual aparece no resultado do CI.

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

The A/B paths use optional NLI backends. Install them only when running these evaluations:

~~~bash
pip install -e ".[dev,nli]"
python scripts/run_f1_eval.py --suite golden-v0.1
~~~

Resultados históricos esperados (E1), sempre lado a lado, conforme DEC-007:

| Caminho | Golden v0 | Golden v0.1 |
|---|---:|---:|
| A (research only / EVAL_ONLY) | 40.00% | 76.67% |
| B (commercial candidate) | 43.33% | 66.67% |
| C | 26.67% | 33.33% |
| Baseline de classe majoritária | 43.33% | 43.33% |

No Golden v0, o caminho B é igual à baseline. O Golden v0.1 foi reescrito depois de os resultados por caso terem sido observados; por isso não é evidência confirmatória independente, e nenhum número do v0.1 (nem valor-p calculado só sobre ele) deve ser apresentado isoladamente.

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

## Limite de tamanho do corpo HTTP

A API aplica um limite de tamanho ao corpo de cada requisição HTTP antes de o FastAPI/Pydantic analisar o conteúdo. O padrão é **2 MiB (2.097.152 bytes)**. Uma requisição acima do limite recebe HTTP **413** com JSON, sem alterar os modelos Pydantic nem o contrato OpenAPI congelado.

Configure o limite em bytes pela variável de ambiente `ATTRACTOR_MAX_BODY_BYTES`. O valor deve ser um inteiro positivo; um valor inválido ou menor/igual a zero impede a inicialização do middleware.

Exemplo para iniciar a API com limite de 1 MiB:

~~~bash
ATTRACTOR_MAX_BODY_BYTES=1048576 uvicorn ayorai_attractor.api.app:app --host 127.0.0.1 --port 8000
~~~

Verificação manual contra um servidor Uvicorn real, usando o limite padrão de 2 MiB:

~~~bash
# Terminal 1
uvicorn ayorai_attractor.api.app:app --host 127.0.0.1 --port 8000

# Terminal 2: o corpo excede 2 MiB; espera-se HTTP 413 e JSON.
python -c "import urllib.error, urllib.request; data=b'x'*(2*1024*1024+1); req=urllib.request.Request('http://127.0.0.1:8000/v1/verify', data=data, headers={'Content-Type':'application/json'}, method='POST'); exec('try:\n r=urllib.request.urlopen(req)\n print(r.status, r.read())\nexcept urllib.error.HTTPError as e:\n print(e.code, e.read().decode())')"
~~~

O comando acima usa bytes que não são JSON de propósito: a checagem de tamanho deve rejeitar o corpo antes da análise JSON. Não exponha o servidor publicamente apenas para executar esse teste.
