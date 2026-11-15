---
name: testes-e2e
description: 'Use para inventariar as funcionalidades de uma aplicação web (rotas, páginas, menus, ações) e criar, revisar ou executar testes end-to-end com Playwright (Python ou Node) dos fluxos críticos — dados fictícios isolados, serviços externos simulados, seletores estáveis, sem sleeps, trace/screenshot em falha, suítes smoke e completa, acessibilidade com axe-core, execução headless em CI, política de testes instáveis e matriz funcionalidade × cenário — sem alterar regras de negócio. Modos review (padrão, somente leitura), test e fix. Palavras-gatilho: E2E, end-to-end, Playwright, teste de interface, teste de fluxo, smoke, regressão visual, axe-core, data-testid, getByRole, flaky, teste instável, trace, headless, matriz de cobertura, cenário E2E.'
argument-hint: '[modo: review | test | fix] [caminho] [foco opcional]'
---

# Testes E2E

Valida, do ponto de vista do usuário, que **cada funcionalidade existente continua funcionando**
e que **toda funcionalidade nova** entra com o cenário E2E do seu fluxo principal. A skill
começa pelo **inventário funcional** (rotas, páginas, menus, ações), mapeia cada item para
cenários E2E em uma matriz de cobertura e só então cria ou executa testes com Playwright —
isolados, determinísticos e sem tocar serviços reais de terceiros. Os testes **descrevem o
comportamento atual**; não o redefinem.

## Quando usar
- Criar a primeira suíte E2E ou revisar uma existente.
- Montar/atualizar a matriz "funcionalidade × cenário E2E".
- Incluir smoke E2E no pipeline (`ci-cd-release`).
- Investigar testes instáveis (flaky) ou lentos.
- Validar que uma funcionalidade nova tem cenário do fluxo principal.

## Quando NÃO usar
- Testes unitários/integração de backend isolados → framework do projeto (ex.: pytest) / `qa-application-auditor`.
- Carga, estresse ou soak → `qa-application-auditor`.
- Pentest/DAST → `qa-appsec`.
- Auditoria aprofundada de UX/WCAG → `web-ux-acessibilidade` (aqui só os checks automatizáveis).

---

## Princípios obrigatórios (inegociáveis)

1. **Não alterar regras de negócio, funcionalidades, textos de domínio ou comportamento visível**
   sem solicitação explícita do usuário. O teste espelha o comportamento atual.
2. **Divergência vira achado** com evidência (trace, screenshot, passo) e proposta — nunca
   correção silenciosa nem ajuste da asserção para "passar".
3. **Modo padrão `review` é somente leitura.** `fix` só com pedido explícito e confirmação;
   mudanças mínimas, verificadas antes/depois.
4. **Diferenciar análise teórica de teste executado.** Cenário escrito ≠ cenário aprovado.
5. **Nunca usar dados reais/pessoais**: banco de teste isolado e descartável, dados fictícios
   semeados via API ou fixtures. Nunca apontar para o banco do usuário.
6. **Nunca chamar serviços externos reais** (cotações, APIs públicas, e-mail, pagamentos):
   intercepte com `page.route`/mocks ou desligue por configuração de teste.
7. **Sem `sleep`/`waitForTimeout`**: use auto-wait e asserções web-first (`expect(...).toBeVisible()`).
8. **Seletores estáveis**: `getByRole`/`getByLabel`/`getByText` acessíveis; `data-testid` só quando
   não houver alternativa. Adicionar `data-testid` ao código produtivo é mudança → requer `fix` confirmado.
9. **Não instalar frameworks novos sem perguntar**; prefira a linguagem já usada no projeto.
10. **Informar limitações** (browsers ausentes, rede bloqueada, app não sobe, dados não semeáveis).

---

## Modos de operação

| Modo | Faz | Não faz |
|---|---|---|
| `review` (padrão) | Inventaria funcionalidades, monta a matriz, revisa testes existentes (seletores, waits, isolamento, mocks) | Não cria nem altera arquivos |
| `test` | Cria testes E2E **em arquivos próprios** (ex.: `e2e/`), sobe a app com banco de teste, executa, coleta trace/screenshot/relatório | Não altera código produtivo |
| `fix` | Corrige testes frágeis e, com confirmação, adiciona ganchos mínimos de testabilidade (`data-testid`, flag de mock) | Não altera regra de negócio, textos ou fluxo |

---

## Fluxo de trabalho

1. **Descoberta** — stack do frontend/backend, como subir a app, como apontar para banco de
   teste, testes E2E existentes, runner (Playwright Python × Node: siga o que o projeto já usa;
   sem preferência prévia, Node se o frontend é JS/TS).
2. **Inventário funcional** — extraia do código: rotas (router), itens de menu/navegação,
   páginas, modais, formulários, ações destrutivas, importações/exportações, filtros, gráficos.
   Para cada item: objetivo, entradas, saídas, dependências externas. Fonte: código, não suposição.
3. **Matriz de cobertura** — preencha [templates/matriz-cobertura.md](templates/matriz-cobertura.md):
   funcionalidade × cenário (feliz, validação, vazio, erro de API, destrutivo com confirmação),
   prioridade e marcação `@smoke`.
4. **Isolamento** — banco descartável por execução/worker; seed via API ou fixture; limpeza no
   teardown; relógio/fuso fixos quando a regra depende de data.
5. **Mocks de terceiros** — mapeie chamadas externas e intercepte (`page.route`) ou use
   configuração de teste do backend. Bloqueie rede externa por padrão.
6. **Implementação (`test`)** — Page Objects leves, seletores acessíveis, asserções web-first,
   trace `on-first-retry`, screenshot/vídeo em falha, axe-core nas páginas principais.
   Padrões e exemplos: [references/playwright-padroes.md](references/playwright-padroes.md).
7. **Execução** — smoke primeiro, depois completa; headless; registre comando, duração,
   aprovados/reprovados/instáveis.
8. **Relatório** — achados `E2E-XXX` em [templates/relatorio.md](templates/relatorio.md) + matriz.

## Suítes

| Suíte | Conteúdo | Quando roda |
|---|---|---|
| Smoke (`@smoke`) | App sobe, navegação principal, 1 fluxo feliz por área crítica | Todo PR/MR, < 5 min |
| Completa | Toda a matriz, incluindo erros e vazios | Antes de homologação/release, ou agendada |
| Visual (opcional) | `toHaveScreenshot` em telas estáveis, dados fictícios fixos | Sob demanda; baseline versionada |
| Matriz de browsers (opcional) | chromium + firefox + webkit | Release |

## Política de testes instáveis
- Retry só no CI (`retries: 2`) e **todo teste que passou após retry é reportado como instável**.
- Instável não é ignorado: vira achado com trace; quarentena (`test.fixme` + issue) exige
  justificativa e prazo; nunca apagar o teste.
- Causa comum: espera por tempo, dependência de ordem, dado compartilhado, rede real, animação.

## Checklist

Lista completa: [references/checklist.md](references/checklist.md).

## Validação de novas funcionalidades

Toda funcionalidade nova ou alterada deve, no mesmo change:
- Entrar na matriz de cobertura (nova linha ou cenário ajustado).
- Ter cenário E2E do **fluxo principal**; se crítica, marcado `@smoke`.
- Ter cenário de erro/validação quando houver formulário ou chamada de API.
- Mockar qualquer dependência externa nova.
- Passar na suíte smoke e não aumentar a taxa de instabilidade.
Sem isso, registre achado (Alta para fluxo crítico, Média para os demais).

## Entregáveis

Relatório em `qa-report/testes-e2e/` (não comitar sem pedido) com
[templates/relatorio.md](templates/relatorio.md) e
[templates/matriz-cobertura.md](templates/matriz-cobertura.md): achados com **ID** (`E2E-001`…),
**severidade** (Crítica/Alta/Média/Baixa/Informativa), **evidência** (trace/screenshot/log),
**proposta** e **status**. Traces e relatórios HTML em `qa-report/testes-e2e/evidencias/`
(verifique que não contêm dados reais).

## Integração com outras skills

| Skill | Relação |
|---|---|
| `prontidao-producao` | Orquestrador: usa a matriz e o resultado smoke/completa como portão |
| `ci-cd-release` | Executa a suíte smoke headless no pipeline e publica traces |
| `qa-application-auditor` | Falhas funcionais/estabilidade encontradas pelo E2E; testes de carga |
| `web-ux-acessibilidade` | Critérios WCAG e estados de tela que os testes verificam |
| `qa-appsec` | Achados de segurança observados durante E2E |
| `integracoes-externas` | Contratos dos serviços que são simulados |
| `calculos-financeiros-fiscais` | Valores esperados nas asserções de cálculo |
| `migracoes-banco` / `backup-recuperacao` | Banco de teste a partir das migrações; fluxos de backup/restauração |
| `privacidade-dados` | Garantia de dados fictícios em seeds, traces e screenshots |
| `documentacao-funcional` | Inventário funcional compartilhado com a documentação |
| `software-engineering-refactoring` | Ganchos de testabilidade sem mudar comportamento |
| `git-workflow` / `commit-message` | Commits `test(...)` e fluxo de branches |
