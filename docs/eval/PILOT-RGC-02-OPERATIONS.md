# Guia operacional — piloto humano 02 do RGC PT-BR

**Estado:** infraestrutura documental; o piloto 02 continua pendente.  
**Data:** 2026-10-21  
**Escopo:** orientar anotadores humanos no uso da ficha em branco e do verificador offline. Este guia não autoriza congelamento, anotação definitiva, execução do sistema ou publicação de resultados.

## Artefatos de referência

- [Ficha em branco do piloto 02](PILOT-RGC-02-WORKSHEET.md) — formulário Markdown que o verificador aceita; mantenha o arquivo versionado vazio.
- [Protocolo de anotação](../annotation/PROTOCOLO.md) — regras humanas para afirmações, átomos, evidências, rótulos, proveniência e adjudicação.
- [Guia de fontes](../annotation/SOURCES.md) — requisitos de fonte e proveniência.
- [Protocolo Golden v1](PROTOCOL-GOLDEN-V1.md) — gates de anotação, isolamento e congelamento.
- [Pré-registro RGC](PREREGISTRATION-RGC-v1.md) — desenho proposto e critérios ainda sujeitos aos gates definidos.
- Verificador mecânico: `scripts/check_pilot_worksheet.py`.
- Corpus de documentos capturados usado por padrão pelo verificador: `evals/ptbr/sources/DOCUMENTS.jsonl`.
- Testes do verificador: `tests/test_check_pilot_worksheet.py`.

## Antes de começar

1. Faça uma cópia local da ficha em branco para um diretório privado. **Não preencha nem substitua a cópia versionada no repositório.**
2. O trabalho de criação e rotulagem do piloto deve ser exclusivamente humano. Não consulte ChatGPT, outros assistentes ou modelos de IA para redigir afirmações, escolher rótulos, decompor átomos ou justificar casos.
3. Não execute o AYORAI ATTRACTOR, o Judge, pipelines de verificação ou modelos sobre os casos do piloto.
4. Use fontes oficiais elegíveis. Confira literalmente o dispositivo e o trecho no artefato-fonte preservado; registre origem, localização, datas relevantes, hash e retificação quando aplicável.
5. A meta de aproximadamente 10 casos é orientativa e condicionada à elegibilidade. Não invente casos, force categorias nem copie casos do piloto 01.
6. Não envie a ficha preenchida, afirmações, trechos, rótulos ou justificativas a chats, issues, pull requests, serviços de IA ou repositórios públicos. Não versione a ficha preenchida.

## Fluxo operacional

### 1. Anotação humana

Preencha a cópia local da ficha usando as regras do protocolo de anotação. Preserve texto literal e proveniência. Registre ambiguidades e limitações; não resolva por inferência jurídica ou conhecimento externo não documentado.

### 2. Verificação mecânica offline

Execute a partir da raiz do repositório, apontando para a cópia local preenchida:

```bash
python scripts/check_pilot_worksheet.py /caminho/privado/minha-ficha.md
```

O script usa por padrão `evals/ptbr/sources/DOCUMENTS.jsonl`. Se for necessário apontar para outro arquivo de documentos capturados, use:

```bash
python scripts/check_pilot_worksheet.py /caminho/privado/minha-ficha.md --documents /caminho/privado/DOCUMENTS.jsonl
```

O verificador não usa rede ou modelos, não importa nem executa o ATTRACTOR, não decide se um rótulo está correto e não sugere rótulos. Ele verifica apenas condições mecânicas previstas no código e reporta identificadores/campos com problemas, sem imprimir o conteúdo dos casos. Um resultado sem erros **não** certifica a correção factual ou jurídica da anotação.

### 3. Revisão humana e encerramento

- Compare cada aviso do verificador com a fonte preservada e corrija a cópia local manualmente.
- Registre dúvidas de regra, falhas de proveniência e categorias não cobertas sem fabricar exemplos.
- Após a revisão, descarte os casos preenchidos do piloto e preserve somente os achados metodológicos necessários, sem reproduzir afirmações, trechos ou rótulos.
- Não calcule nem publique métricas do sistema a partir do piloto; não o use como conjunto definitivo.
- Aguarde a revisão humana do piloto 02 e uma decisão explícita do mantenedor antes de qualquer congelamento. A infraestrutura deste guia não é aprovação do protocolo.

## Checklist de isolamento

- [ ] Cópia de trabalho armazenada localmente e fora do repositório público.
- [ ] Nenhum assistente/modelo de IA foi consultado na criação ou rotulagem.
- [ ] O ATTRACTOR/Judge não foi executado sobre os casos.
- [ ] Fontes oficiais e trechos foram conferidos literalmente.
- [ ] O verificador mecânico foi executado localmente, sem rede/modelos.
- [ ] A ficha preenchida não foi versionada nem enviada a serviços externos.
- [ ] Somente achados metodológicos agregados serão preservados.
- [ ] Nenhum resultado de benchmark foi calculado ou alegado.

**Limites:** o piloto 02 é humano e exploratório. Este guia não congela o protocolo, não autoriza criar os 300 casos definitivos e não autoriza execução confirmatória. Não existe resultado de benchmark RGC PT-BR nesta etapa.
