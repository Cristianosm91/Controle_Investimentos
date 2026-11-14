# Checklist — UX Web e Acessibilidade

Marque `OK`, `ACHADO (UX-XXX)`, `N/A` ou `NÃO VERIFICADO` (com motivo). Entre colchetes, o
critério WCAG 2.2 de referência.

## 1. Teclado e foco
- [ ] Todas as ações acessíveis por teclado; nada exige mouse/hover [2.1.1].
- [ ] Sem armadilha de teclado fora de modais [2.1.2].
- [ ] Ordem de foco segue a ordem visual/lógica [2.4.3].
- [ ] Foco sempre visível, contraste ≥ 3:1 do indicador; `outline: none` só com substituto [2.4.7, 2.4.11].
- [ ] Foco não fica encoberto por header fixo, toast ou drawer [2.4.11].
- [ ] Link "pular para o conteúdo" quando há navegação extensa [2.4.1].
- [ ] Modal: foco vai para o modal ao abrir, fica preso nele, `Esc` fecha, foco volta ao gatilho; `role="dialog"` + `aria-modal="true"` + `aria-labelledby`.
- [ ] Menus, abas e dropdowns customizados seguem o padrão de teclado do WAI-ARIA APG.
- [ ] Mudança de rota SPA move o foco (ou anuncia) o novo título da página; `document.title` atualizado [2.4.2].

## 2. Semântica, nomes e ARIA
- [ ] `<html lang="pt-BR">` [3.1.1].
- [ ] Um `h1` por página; hierarquia de títulos sem saltos [1.3.1].
- [ ] Landmarks: `header`, `nav`, `main`, `footer` [1.3.1].
- [ ] Botões são `<button>`, links são `<a href>`; nada de `div` clicável [4.1.2].
- [ ] Botões só de ícone têm nome acessível (`aria-label`/texto oculto) [4.1.2].
- [ ] Imagens informativas com `alt`; decorativas com `alt=""` [1.1.1].
- [ ] ARIA só onde HTML nativo não resolve; sem `role` conflitante; `aria-*` referenciando IDs existentes.
- [ ] Atualizações assíncronas relevantes anunciadas (`role="status"`/`aria-live="polite"`; erros `role="alert"`) [4.1.3].

## 3. Percepção
- [ ] Contraste texto ≥ 4.5:1 (≥ 3:1 para texto grande) [1.4.3].
- [ ] Contraste de componentes e gráficos ≥ 3:1 (bordas de campo, ícones, séries) [1.4.11].
- [ ] Cor nunca é o único meio (positivo/negativo também com sinal, ícone ou texto) [1.4.1].
- [ ] Zoom 200% sem perda de conteúdo/função; reflow em 320px CSS sem rolagem bidimensional (exceto tabelas/gráficos) [1.4.4, 1.4.10].
- [ ] Espaçamento de texto ajustável sem corte [1.4.12].
- [ ] Conteúdo em hover/foco (tooltip) dispensável com `Esc`, persistente e acessível por teclado [1.4.13].
- [ ] Animações respeitam `prefers-reduced-motion` [2.3.3].
- [ ] Alvos de clique ≥ 24×24 px CSS ou espaçamento equivalente [2.5.8].

## 4. Tabelas e gráficos
- [ ] Tabelas de dados com `<th>`, `scope`, `<caption>` ou `aria-label` [1.3.1].
- [ ] Ordenação indicada com `aria-sort`; botões de ordenação com nome.
- [ ] Números alinhados à direita, formato pt-BR consistente, unidade/moeda clara.
- [ ] Em telas estreitas: contêiner com rolagem horizontal (`overflow-x: auto`, focável com `tabindex="0"` e nome) e primeira coluna/cabeçalho legível.
- [ ] Gráficos com alternativa: tabela de dados, resumo textual ou `aria-describedby` [1.1.1].
- [ ] Legenda de gráfico não depende só de cor (padrões, rótulos diretos).

## 5. Estados de tela (consistência entre páginas)
- [ ] Carregando: skeleton ou indicador no mesmo padrão; `aria-busy` na região.
- [ ] Vazio: explica o motivo e oferece a próxima ação.
- [ ] Erro: o que aconteceu + o que fazer (tentar de novo, verificar arquivo); sem stack trace/mensagem técnica crua.
- [ ] Parcial/desatualizado: indica data/hora da última atualização e fonte indisponível.
- [ ] Sucesso: feedback discreto (toast `role="status"`), sem bloquear a tela.
- [ ] Mesmo componente/estilo para cada estado em todas as páginas.

## 6. Ações destrutivas
- [ ] Exclusão/limpeza/sobrescrita pede confirmação nomeando o alvo e a consequência.
- [ ] Botão destrutivo visualmente distinto e não é o foco padrão do diálogo.
- [ ] Desfazer oferecido onde a app já suporta; nunca prometer desfazer inexistente.
- [ ] Ações em lote informam a quantidade afetada.

## 7. Formulários
- [ ] Todo campo com `<label>` associado (ou `aria-labelledby`) [3.3.2].
- [ ] Obrigatórios indicados por texto/ícone com nome, não só cor/asterisco [3.3.2].
- [ ] Erro identificado no campo, com texto, `aria-invalid="true"` e `aria-describedby` [3.3.1].
- [ ] Sugestão de correção quando conhecida [3.3.3]; foco vai ao primeiro erro no envio.
- [ ] Números: vírgula decimal, separador de milhar `.`, `inputmode="decimal"`; aceita colar `1.234,56` e `1234,56`.
- [ ] Moeda `R$ 1.234,56`; percentuais `12,34%`; datas `dd/mm/aaaa`; via `Intl`/utilitário existente.
- [ ] Máscaras não impedem apagar, colar ou editar no meio; valor enviado à API no formato canônico.
- [ ] `autocomplete` adequado; dados já informados não são pedidos de novo [3.3.7].
- [ ] Botão de envio desabilitado/indicado durante o envio; sem duplo envio.

## 8. Responsividade e desempenho percebido
- [ ] Breakpoints testados: 360, 768, 1024, 1280, 1920.
- [ ] Sidebar vira drawer acessível (botão com `aria-expanded`, foco gerenciado).
- [ ] Nada corta ou sobrepõe em zoom 200%.
- [ ] Listas grandes paginadas/virtualizadas; filtros não recarregam a página inteira.
- [ ] Feedback imediato a cliques; sem saltos de layout (CLS) ao carregar dados.

## 9. Consistência e microtexto
- [ ] Cores, espaçamentos e tipografia via tokens/variáveis; sem valores mágicos repetidos.
- [ ] Componentes compartilhados reutilizados (botão, modal, tabela, campo).
- [ ] Mesmo termo para o mesmo conceito em toda a app (glossário implícito).
- [ ] Rótulos de botão são verbos claros ("Salvar", "Excluir lançamento").
- [ ] Capitalização, pontuação e tom consistentes.
- [ ] Ajuda contextual/tooltips presentes nos campos complexos e acessíveis.
- [ ] Onboarding/estado inicial orienta o primeiro uso sem bloquear.

> Mudanças de texto de domínio, layout ou fluxo são **propostas** — aplicar só com confirmação.
