# Critérios mínimos por pilar

Mínimo que cada pilar precisa demonstrar para ser considerado atendido. O detalhamento completo
está no checklist da skill responsável; aqui ficam só os critérios de corte do parecer.
Marque cada item como `[EXECUTADO]`, `[ANÁLISE ESTÁTICA]`, `[NÃO EXECUTADO]` ou `N/A (motivo)`.

## 1. Estabilidade e performance — `qa-application-auditor`
- Testes existentes passam; tempo de inicialização e das telas principais medidos com volume realista.
- Jobs/threads/timers sem sobreposição e encerrados no shutdown; memória estável em execução prolongada.
- Nenhuma operação pesada bloqueando o event loop ou a thread de interface.

## 2. Segurança — `qa-appsec`
- Superfície exposta mapeada (portas, rotas, uploads, arquivos lidos/escritos).
- Entradas validadas no servidor; uploads com tipo, tamanho e expansão limitados.
- Dependências sem vulnerabilidade conhecida não tratada; nenhum segredo versionado.
- Cabeçalhos de segurança e proteção contra requisições de outras origens quando houver interface web.

## 3. Privacidade — `privacidade-dados`
- Inventário de dados pessoais; mascaramento na interface, exportações e logs.
- Possibilidade de excluir os dados de uma pessoa (e limitação documentada para backups).
- Nenhum dado pessoal enviado a serviços externos; fixtures fictícias.

## 4. Cálculos — `calculos-financeiros-fiscais`
- Tipos numéricos e arredondamento adequados e consistentes.
- Regras com vigência (sem constantes "mágicas" que mudam com a lei).
- Casos de referência validados por fonte independente e testes de invariantes.

## 5. Banco e migrações — `migracoes-banco`
- Modelo e migrações sem divergência; upgrade em banco vazio e em cópia com dados.
- Backup antes de migrar; backups antigos restauram e migram para o esquema atual.

## 6. Backup e recuperação — `backup-recuperacao`
- RPO/RTO definidos; backup automático com retenção; verificação de integridade.
- Restauração testada em ambiente isolado com conferência de contagens/totais.

## 7. Integrações externas — `integracoes-externas`
- Timeouts explícitos, retries apenas idempotentes, tratamento de 429/5xx/payload inválido.
- Data/hora e fonte do dado visíveis; dado desatualizado sinalizado; testes com mocks.

## 8. Observabilidade — `observabilidade-logs`
- Logs por módulo com rotação e sem dados pessoais; nenhuma exceção engolida.
- Healthcheck com versão; status dos jobs visível; erro padronizado na API e na interface.

## 9. UX e acessibilidade — `web-ux-acessibilidade` / `app-ux`
- Navegação por teclado, foco visível, rótulos, contraste AA, gráficos com alternativa textual.
- Estados carregando/vazio/erro em todas as telas; formatos pt-BR; confirmação em ações destrutivas.

## 10. Testes E2E — `testes-e2e`
- Matriz funcionalidade × cenário; fluxos críticos automatizados com dados fictícios e mocks.

## 11. CI/CD e release — `ci-cd-release` + `git-workflow`
- Pipeline versionado executando os mesmos comandos do lint/teste local.
- Versão em fonte única, CHANGELOG e tag por release.

## 12. Documentação — `documentacao-funcional`
- Toda funcionalidade visível documentada; nenhuma doc descreve comportamento inexistente.

## 13. Manutenibilidade — `software-engineering-refactoring`
- Diagnóstico de acoplamento, duplicação e testabilidade, priorizado — sem refatorar neste gate.
