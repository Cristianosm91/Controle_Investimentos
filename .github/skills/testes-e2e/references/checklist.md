# Checklist — Testes E2E

Marque `OK`, `ACHADO (E2E-XXX)`, `N/A` ou `NÃO VERIFICADO` (com motivo).

## 1. Inventário e cobertura
- [ ] Inventário extraído do código: rotas do router, menu/navegação, páginas, modais, formulários.
- [ ] Cada funcionalidade visível tem ao menos um cenário na matriz.
- [ ] Fluxos críticos (cadastro, edição, exclusão, importação, exportação, cálculo exibido) com cenário feliz **e** de erro.
- [ ] Ações destrutivas testam a confirmação e o cancelamento.
- [ ] Estados vazio, carregando e erro de API cobertos nas páginas principais.
- [ ] Rotas inexistentes / deep links (recarregar página em rota interna) testados.

## 2. Isolamento e dados
- [ ] Banco de teste dedicado e descartável (arquivo temporário, schema próprio ou container).
- [ ] Banco criado pelas migrações oficiais (não por `create_all` divergente).
- [ ] Seed via API pública da app ou fixtures; dados **fictícios** (nomes, documentos, valores).
- [ ] Cada teste independe da ordem; sem estado compartilhado entre workers.
- [ ] Teardown limpa o que criou; nenhuma escrita em diretórios do usuário.
- [ ] Data/hora e fuso controlados quando o resultado depende deles (`page.clock`, variável de ambiente do backend).

## 3. Dependências externas
- [ ] Todas as chamadas a terceiros mapeadas (frontend e backend).
- [ ] Frontend: `page.route('**/api-externa/**', ...)` com respostas fictícias.
- [ ] Backend: modo de teste/flag que substitui clientes externos, ou servidor fake local.
- [ ] Rede externa bloqueada por padrão (rota catch-all que falha para hosts não permitidos).
- [ ] Cenários de falha do terceiro (timeout, 500, payload inválido) cobertos.

## 4. Qualidade dos testes
- [ ] Seletores por papel/rótulo/texto acessível; `data-testid` só quando necessário.
- [ ] Nenhum seletor por classe CSS gerada, XPath posicional ou índice frágil.
- [ ] Nenhum `waitForTimeout`/`sleep`; asserções web-first.
- [ ] Um comportamento por teste; nomes descrevem o fluxo em pt-BR.
- [ ] Page Objects/fixtures sem lógica de negócio duplicada.
- [ ] Asserções de valores formatados conferem o formato pt-BR (vírgula decimal, `R$`, `dd/mm/aaaa`).

## 5. Diagnóstico
- [ ] `trace: 'on-first-retry'`, `screenshot: 'only-on-failure'`, `video: 'retain-on-failure'`.
- [ ] Relatório HTML/JUnit gerado e anexado no CI.
- [ ] Traces e screenshots sem dados reais (só seeds fictícios).

## 6. Acessibilidade automatizada
- [ ] `@axe-core/playwright` (Node) ou `axe-playwright-python` nas páginas principais.
- [ ] Tags `wcag2a`, `wcag2aa`, `wcag21aa`, `wcag22aa`; violações `serious`/`critical` falham o teste.
- [ ] Exceções documentadas com justificativa (não desabilitar regra globalmente).

## 7. Execução e CI
- [ ] Headless no CI; `workers` e `retries` definidos; `timeout` por teste e global.
- [ ] `webServer` sobe a app (ou script equivalente) com banco de teste e espera healthcheck.
- [ ] Suíte smoke (`@smoke`) < ~5 min; completa separada.
- [ ] Testes instáveis reportados (passou após retry) e acompanhados.
- [ ] Matriz de browsers e regressão visual apenas se o projeto optar (baseline versionada, dados fixos).
