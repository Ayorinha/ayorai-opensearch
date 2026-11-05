# Site oficial do AYORAI ATTRACTOR

Este branch (`gh-pages`) contém somente o site público do projeto, publicado pelo GitHub Pages em:

**https://ayorinha.github.io/ayorai-opensearch/**

O código-fonte, a documentação técnica e os artefatos de avaliação ficam no branch `main`. Nenhum arquivo deste branch é usado pela aplicação.

## Estrutura

| Caminho | Conteúdo |
| --- | --- |
| `index.html` | Página inicial do projeto |
| `auditoria-de-inteligencia-artificial/` | Guia de auditoria de inteligência artificial |
| `alucinacao-de-ia/` | Guia sobre alucinação de IA e verificação de respostas |
| `404.html` | Página de erro |
| `assets/site.css` | Estilo compartilhado por todas as páginas |
| `assets/ayorai-attractor-banner.png` | Banner oficial, cópia idêntica de `docs/assets/brand/` no `main` (SHA-256 `4ba4a1af9e5891c5b1412d47858096b25e39240a3747f9eea9ab35686e0a4559`) |
| `assets/og-image.png` | Prévia para redes sociais: o banner oficial, sem alteração, centralizado em fundo preto (1280×640) |
| `sitemap.xml` | Lista de páginas para buscadores |
| `robots.txt` | Permissões para robôs de busca |
| `llms.txt` | Resumo do projeto para sistemas de IA |
| `<chave>.txt` | Chave de verificação do IndexNow |
| `.nojekyll` | Publica os arquivos como estão, sem processamento |
| `.github/workflows/indexnow.yml` | Avisa os buscadores (IndexNow) a cada publicação |

## Princípios do conteúdo

- O texto acompanha o `README.md` do `main` e declara os mesmos limites: o projeto não é apresentado como certificado e ainda não há resultado de benchmark em português.
- A identidade visual segue `docs/assets/brand/README.md`: fundo preto e banner sem distorção, recoloração ou separação do dente-de-leão.
- Nenhuma afirmação de benchmark validado, certificação, parceria ou endosso sem evidência verificável (ver `AGENTS.md`).

## Como atualizar

1. Edite os arquivos neste branch.
2. Ao incluir ou remover uma página, atualize `sitemap.xml`, `llms.txt` e os links do menu e do rodapé.
3. Ao alterar o conteúdo, atualize a data de `lastmod` no `sitemap.xml` e de `dateModified` nos dados estruturados da página.
4. Faça o commit. O GitHub Pages publica em cerca de 1 minuto, e a automação do IndexNow avisa os buscadores em seguida.

Mantenedor: Anderson Leon Ayora. Licença do projeto: Apache-2.0.
