# Guia de custódia da partição oculta

Este guia descreve controles operacionais. Não deve conter dados reais, credenciais ou caminhos privados.

## Princípios obrigatórios
1. **Fora do repositório:** manter arquivos da partição oculta, rótulos e manifestos reais em armazenamento privado aprovado, fora do GitHub público e de clones de trabalho comuns.
2. **Criptografia:** usar criptografia em trânsito e em repouso; gerir as chaves separadamente dos arquivos.
3. **Acesso mínimo:** conceder acesso nominal apenas às pessoas designadas e estritamente necessárias. O executor não deve conhecer previamente os rótulos ocultos.
4. **Autenticação forte:** exigir MFA e contas individuais; nunca compartilhar credenciais.
5. **Trilha de auditoria:** registrar concessão/revogação de acesso, leitura, alteração, exportação e incidentes com data/hora e identidade.
6. **Integridade:** calcular SHA-256 dos artefatos aprovados e manter inventário em local restrito. Não publicar metadados que permitam inferências não autorizadas.
7. **Separação:** manter partição de desenvolvimento e partição oculta em locais e permissões distintos.
8. **Sem serviços externos não aprovados:** não enviar materiais ocultos a assistentes/modelos, serviços de terceiros, issues, PRs ou logs públicos.

## Procedimento de custódia
- [ ] Designar custodiante humano e registrar a autorização em documento restrito.
- [ ] Criar armazenamento criptografado e validar permissões antes de inserir arquivos.
- [ ] Registrar inventário, contagens e hashes em registro privado.
- [ ] Restringir o acesso aos rótulos ocultos ao mínimo necessário.
- [ ] Registrar toda transferência de custódia e validar hashes após cada transferência.
- [ ] Preparar o pacote de execução sem expor os rótulos ao executor.
- [ ] Autorizar a execução única somente após aprovação formal dos gates aplicáveis.
- [ ] Preservar logs, hashes, configuração e relatório final no arquivo de auditoria restrito.
- [ ] Revogar acessos temporários e registrar a revogação após o fechamento.

## Incidente ou suspeita de exposição
1. Suspender transferências e execuções relacionadas.
2. Preservar logs e evidências sem replicar o conteúdo exposto.
3. Notificar imediatamente o custodiante e o mantenedor responsável.
4. Registrar escopo, horário, pessoas potencialmente afetadas e medidas de contenção em registro privado.
5. Retomar somente após decisão humana documentada sobre validade do conjunto e medidas corretivas.

## Limites de publicação
Publicar no repositório público apenas procedimentos e metadados aprovados que não revelem conteúdo oculto. Nunca incluir casos, rótulos, credenciais, caminhos internos, logs de acesso identificáveis ou manifestos reais.