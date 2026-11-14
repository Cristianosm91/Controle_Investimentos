---
name: web-ux-acessibilidade
description: 'Use para revisar, testar ou (com confirmação) ajustar UX e acessibilidade de aplicações web SPA (React, Vue, Angular etc.) — WCAG 2.2 AA (teclado, foco visível, foco preso em modais, rótulos, contraste, ARIA só quando necessário, tabelas com cabeçalhos, gráficos com alternativa textual, não depender só de cor), estados de carregamento/vazio/erro/dados desatualizados, mensagens de erro acionáveis, confirmação de ações destrutivas, formulários com formatos pt-BR (vírgula decimal, moeda, data), responsividade, zoom 200%, desempenho percebido, consistência de componentes e microtextos — sem alterar textos de domínio, layout ou fluxos sem confirmação. Modos review (padrão, somente leitura), test e fix. Palavras-gatilho: acessibilidade, a11y, WCAG, axe, Lighthouse, jsx-a11y, contraste, foco, teclado, leitor de tela, ARIA, estado vazio, skeleton, loading, mensagem de erro, confirmação, formulário, máscara, vírgula decimal, responsividade, zoom, microtexto, UX web.'
argument-hint: '[modo: review | test | fix] [caminho] [foco opcional]'
---

# UX Web e Acessibilidade

Avalia se a interface web é **utilizável por qualquer pessoa, previsível e consistente** —
conformidade WCAG 2.2 nível AA, estados de tela coerentes, formulários adequados ao pt-BR,
responsividade e desempenho percebido. A skill **propõe**; não redesenha. Textos de domínio,
decisões de layout e fluxos só mudam com confirmação explícita do usuário. Para apps desktop
(PyQt/pywebview: barra de título, ícone, DPI) use `app-ux`.

## Quando usar
- Revisar acessibilidade e UX de uma SPA antes de homologação/release.
- Validar uma tela ou funcionalidade nova contra o padrão já existente na app.
- Padronizar estados (carregando, vazio, erro, desatualizado) e mensagens entre páginas.
- Configurar verificações automatizadas (axe-core, Lighthouse, eslint-plugin-jsx-a11y).

## Quando NÃO usar
- Janela desktop, barra de título frameless, ícone `.ico`, DPI do Windows → `app-ux`.
- Criar identidade visual/marca ou redesenhar telas sem pedido.
- Testes funcionais de fluxo completo → `testes-e2e` (que reutiliza os checks desta skill).

---

## Princípios obrigatórios (inegociáveis)

1. **Não alterar regras de negócio, funcionalidades, textos de domínio, layout ou fluxos**
   sem solicitação explícita do usuário. Melhorias são **propostas** com antes/depois.
2. **Divergência vira achado** com evidência (critério WCAG, screenshot, saída do axe, passo de
   teclado) e proposta — nunca correção silenciosa.
3. **Modo padrão `review` é somente leitura.** `fix` só com pedido explícito e confirmação;
   mudanças mínimas (atributos, rótulos técnicos, foco, contraste dentro dos tokens existentes),
   verificadas antes/depois.
4. **Diferenciar análise teórica de teste executado**: leitura de código ≠ teste com teclado,
   leitor de tela ou ferramenta. Ferramentas automáticas cobrem só parte do WCAG — declare isso.
5. **Nunca usar dados reais/pessoais** em screenshots e testes (ver `redigir-dados-sensiveis`).
6. **ARIA só quando o HTML nativo não resolve** (primeira regra do ARIA).
7. **Reutilizar o que existe**: tokens, componentes e padrões da própria app antes de propor novos.
8. **Informar limitações** (sem leitor de tela, sem browser, app não sobe, dados indisponíveis).

---

## Modos de operação

| Modo | Faz | Não faz |
|---|---|---|
| `review` (padrão) | Lê componentes/estilos, mapeia padrões, aponta violações WCAG e inconsistências de UX | Não altera arquivos |
| `test` | Roda axe-core (via Playwright), Lighthouse, eslint-plugin-jsx-a11y, navegação por teclado, zoom 200% e viewports; coleta evidências | Não altera código produtivo |
| `fix` | Aplica correções técnicas confirmadas (rótulos, `alt`, foco, `scope`, contraste por token) | Não muda texto de domínio, layout ou fluxo sem confirmação item a item |

---

## Fluxo de trabalho

1. **Descoberta** — framework, roteamento, biblioteca de componentes, tokens (CSS vars/tema),
   formatação (`Intl`, utilitários de moeda/data), gráficos, modais, tabelas, toasts.
2. **Inventário de telas** — rotas/páginas e componentes compartilhados (reutilize o inventário
   de `testes-e2e`/`documentacao-funcional` se existir).
3. **Padrões de referência** — identifique como a app **já** faz: loading, vazio, erro, confirmação,
   máscara, botão primário. Inconsistência = desvio desse padrão dominante.
4. **Revisão por área** — acessibilidade, estados, formulários, responsividade, desempenho
   percebido, consistência, microtexto. Checklist: [references/checklist.md](references/checklist.md).
5. **Testes (`test`)** — automáticos + manuais roteirizados (Tab/Shift+Tab/Enter/Esc, zoom 200%,
   viewports 360/768/1280, `prefers-reduced-motion`). Ferramentas: [references/ferramentas.md](references/ferramentas.md).
6. **Propostas** — para cada achado: critério violado, impacto no usuário, proposta mínima, se
   muda texto/layout/fluxo (→ exige confirmação).
7. **Relatório** — achados `UX-XXX` em [templates/relatorio.md](templates/relatorio.md).

## Áreas avaliadas (resumo)

| Área | Pontos-chave |
|---|---|
| WCAG 2.2 AA | Teclado completo, foco visível e não encoberto, foco preso e devolvido em modais, `label` em campos, contraste 4.5:1 / 3:1, alvo ≥ 24px, tabelas com `th`/`scope`/`caption`, gráficos com tabela/texto alternativo, cor nunca como único sinal, `lang="pt-BR"` |
| Estados | Loading (skeleton), vazio (com próxima ação), erro (com causa + ação), parcial/desatualizado (data da última atualização) — iguais em todas as páginas |
| Erros e confirmações | Mensagem diz o que houve e o que fazer; destrutivas pedem confirmação nomeando o alvo; desfazer onde já existir |
| Formulários | Validação no campo e no envio, `aria-invalid` + `aria-describedby`, máscaras que não bloqueiam colar/editar, vírgula decimal, `R$ 1.234,56`, `dd/mm/aaaa`, `inputmode` adequado |
| Responsividade | Breakpoints, sidebar → drawer, tabelas com rolagem horizontal e cabeçalho visível, reflow a 320px CSS, zoom 200% sem perda |
| Desempenho percebido | Skeletons, paginação/virtualização, feedback < 100 ms, botões desabilitados durante envio |
| Consistência | Tokens de cor/espaço/tipografia, componentes reutilizados, mesma ação = mesmo rótulo/ícone/posição |
| Microtexto e ajuda | Terminologia única, tom consistente, tooltips/ajuda contextual acessíveis por teclado, onboarding discreto |

## Checklist

Lista completa: [references/checklist.md](references/checklist.md).

## Validação de novas funcionalidades

Toda tela/componente novo ou alterado, antes do merge:
- Passa no axe (sem `serious`/`critical`) e no `eslint-plugin-jsx-a11y` (se configurado).
- É operável só por teclado, com foco visível e ordem lógica.
- Tem os quatro estados (loading, vazio, erro, desatualizado quando aplicável) no padrão da app.
- Usa formatação pt-BR pelos utilitários existentes (não formatação ad hoc).
- Reutiliza componentes/tokens existentes; novo padrão visual só com justificativa.
- Ação destrutiva tem confirmação; textos seguem a terminologia já usada.
- Funciona a 360px de largura e zoom 200%.

## Entregáveis

Relatório em `qa-report/web-ux-acessibilidade/` (não comitar sem pedido) com
[templates/relatorio.md](templates/relatorio.md): achados com **ID** (`UX-001`…), **severidade**
(Crítica/Alta/Média/Baixa/Informativa), **critério WCAG** quando aplicável, **evidência**,
**proposta** (e se exige confirmação) e **status**. Evidências em `evidencias/` com dados fictícios.

| Severidade | Exemplo |
|---|---|
| Crítica | Fluxo principal impossível por teclado; foco perdido em modal sem saída; ação destrutiva sem confirmação |
| Alta | Campo sem rótulo; contraste de texto < 4.5:1; erro sem mensagem; gráfico sem alternativa |
| Média | Estados inconsistentes entre páginas; tabela sem rolagem em mobile; formato numérico misto |
| Baixa | Microtexto inconsistente; tooltip sem teclado em info secundária |
| Informativa | Sugestões de refinamento |

## Integração com outras skills

| Skill | Relação |
|---|---|
| `prontidao-producao` | Orquestrador: usa o parecer de UX/a11y como portão |
| `app-ux` | UX de apps **desktop** (frameless, ícone, DPI) — complementar, não sobreposta |
| `testes-e2e` | Executa axe-core dentro dos cenários e valida estados de tela |
| `ci-cd-release` | Inclui jsx-a11y/axe/Lighthouse CI como checks |
| `documentacao-funcional` | Textos de ajuda in-app e consistência com a documentação |
| `calculos-financeiros-fiscais` | Formatação e arredondamento exibidos devem refletir a regra de cálculo |
| `qa-application-auditor` | Lentidão real de renderização, vazamentos no front-end |
| `qa-appsec` / `privacidade-dados` | Exposição de dados na UI, mascaramento |
| `redigir-dados-sensiveis` | Screenshots de evidência com dados fictícios |
| `software-engineering-refactoring` | Extração de componentes compartilhados sem mudar comportamento |
| `git-workflow` / `commit-message` | Commits `fix(a11y)`/`style(...)` e fluxo de branches |
