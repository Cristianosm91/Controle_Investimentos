---
name: app-ux
description: 'Use ao criar ou editar a interface (UI) de apps desktop em Python — pywebview, PyQt5 com QWebEngine ou widgets nativos. Abrange barra de título frameless, ícone .ico, controles de janela, cantos arredondados, redimensionamento, responsividade e escala DPI, versão no header, padrão visual, design tokens, tema claro/escuro, layout, cards e botões. Gatilhos: barra de título, titlebar, frameless, ícone .ico, WM_SETICON, QSizeGrip, AppUserModelID, DPI, design tokens, tema, dark mode, layout, cards, botões, versão no header.'
---

# UX/UI de apps desktop (pywebview / PyQt5)

Use estas regras para criar ou editar interfaces desktop em pywebview, PyQt5 com
QWebEngine ou PyQt5 de widgets nativos. Consulte as fontes de verdade em
`guia-skills/docs/ux/` antes de implementar.

## Quando não usar

- Não use para interface web servida em navegador sem janela desktop própria;
  nesse caso, use `web-ux-acessibilidade`.
- Se o app desktop embutir HTML (pywebview/QWebEngine), use também
  `web-ux-acessibilidade` para o conteúdo.

## Fontes de verdade

- Tokens visuais e temas: [docs/ux/design-tokens.md](../../../guia-skills/docs/ux/design-tokens.md)
- Barra de título e ícone: [docs/ux/barra-de-titulo.md](../../../guia-skills/docs/ux/barra-de-titulo.md)
- Versão no header: [docs/ux/versao-header.md](../../../guia-skills/docs/ux/versao-header.md)
- Responsividade e DPI: [docs/ux/responsividade-dpi.md](../../../guia-skills/docs/ux/responsividade-dpi.md)

## Regra 0 — Escopo (prioridade máxima)

- Altere somente o que foi pedido. Não faça melhorias visuais adjacentes por
  iniciativa própria.
- Reutilize os design tokens, componentes e padrões já existentes no app; não
  crie uma segunda identidade visual.
- Antes de uma mudança visual ampla, apresente uma crítica objetiva e opções de
  solução, explique os impactos e aguarde aprovação. Não implemente a mudança
  ampla antes da aprovação.
- Não use verde como cor de destaque; reserve-o para indicar sucesso.

## Padrão visual

- Centralize cores, tipografia, espaçamento, raios, sombras e estados em
  variáveis CSS ou em `theme.py` no Qt. Não use valores hexadecimais soltos nos
  componentes; consuma os tokens definidos em
  [design-tokens.md](../../../guia-skills/docs/ux/design-tokens.md).
- Use a mesma escala de tokens nos temas claro e escuro, variando somente seus
  valores.
- Use Segoe UI Variable, com fallback para Segoe UI, e escala tipográfica de
  12, 14, 16 e 20 px. Limite a tipografia a dois pesos.
- Use grade de espaçamento de 4 px e raios de 4 ou 8 px.
- Apresente um único botão primário por área de ação. Use os demais botões como
  secundários ou neutros.
- Prefira sombras sutis ou borda de 1 px para separar superfícies; evite
  elevação e decoração excessivas.
- Defina estados visuais para hover, pressed, foco visível, desabilitado,
  carregando, vazio e erro.
- Mantenha transições entre 120 e 200 ms. Respeite a preferência do sistema
  para movimento reduzido quando aplicável.
- Use contraste de pelo menos 4.5:1 para texto normal em ambos os temas.

## Tema claro e escuro

- Siga o tema atual do Windows na primeira execução.
- Permita alternar entre claro e escuro e salve a preferência do usuário em
  `%APPDATA%\<App>\settings.json`. Não grave essa preferência na pasta de
  instalação, pois o app pode estar em uma pasta compartilhada na rede.
- Preserve os mesmos nomes e papéis dos tokens nos dois temas; só altere os
  valores.
- Atualize superfícies, texto, bordas, estados, foco e controles do sistema ao
  alternar o tema; mantenha contraste e legibilidade.

## Barra de título (padrão Windows 11)

- Quando criar uma barra de título própria, use altura de 32 px e botões de
  controle de 46 × 32 px.
- Use Segoe Fluent Icons, com fallback para Segoe MDL2 Assets.
- No hover do botão Fechar, use `#C42B1C`; mantenha esse valor centralizado como
  token do tema.
- Permita maximizar e restaurar com duplo clique na área de título.
- Limite a região de arraste à área livre; ela não pode cobrir os botões de
  minimizar, maximizar/restaurar ou fechar.
- Mantenha os controles acessíveis por teclado e forneça rótulos acessíveis.
- Para a barra frameless, mantenha `frameless=True` e `easy_drag=False` no
  pywebview; marque somente a região arrastável com
  `pywebview-drag-region`. Nos controles, use `event.stopPropagation()` no
  `mousedown` para impedir que o clique inicie o arraste.
- Respeite a barra de tarefas ao maximizar a janela frameless; use `rcWork`
  do monitor.

## Regras técnicas que não podem ser esquecidas

1. **QtWebEngine e flexbox:** use `margin` para espaçamento entre itens (por
   exemplo, `.tb-icon { margin: 0 9px }`); nunca use `gap`. PyQt5 QtWebEngine
   5.15.2 (Chromium 83) ignora `gap` em flexbox.
2. **Ícone:** use arquivo `.ico`; SVG e PNG não funcionam como ícone de janela
   nesse backend. Em janela frameless, reaplique o ícone com `WM_SETICON`.
   Sempre apresente as variações disponíveis e peça ao usuário que escolha
   antes de fixar o ícone (consulte “Escolha do ícone”).
3. **Layout:** mantenha barras fixas e conteúdo rolável. Use `body` em
   `flex-column` e `main { flex: 1; min-height: 0; overflow: auto }`. Defina
   dimensões iniciais que caibam em escala de 175%.
4. **Janela frameless:** forneça controles próprios para minimizar,
   maximizar/restaurar e fechar.
5. **Versão no header:** exiba junto ao título no formato
   `vMAJOR.MINOR.CORREÇÃO` (por exemplo, `v4.0.0`), obtido de fonte única
   (`__version__`). Não use valor hardcoded nem duplique a versão em outros
   pontos da interface; consulte `versao-header.md`.
6. **High DPI no PyQt5:** defina `AA_EnableHighDpiScaling` e
   `AA_UseHighDpiPixmaps` antes de criar `QApplication`.
7. **Ícone multi-resolução:** forneça recursos `.ico` em 16, 24, 32, 48 e
   256 px.
8. **Cantos arredondados:** no PyQt5, aplique `DwmSetWindowAttribute` no
   `showEvent`. No Windows 10, ignore em silêncio a falha ao definir cantos
   arredondados.

## PyQt5 com widgets nativos (sem QWebEngine)

As regras de HTML e CSS não se aplicam a widgets nativos; traduza o padrão para
Qt e consulte `barra-de-titulo.md`.

1. Desenhe formas circulares com `QPainter`; `QLabel` com `border-radius` vira
   quadrado.
2. Use `layout.addSpacing(9)` para espaçar widgets; `margin` de stylesheet não
   cria espaçamento entre widgets.
3. Aplique cantos arredondados (Windows 11) com `DwmSetWindowAttribute` no
   `showEvent`.
4. Use `QSizeGrip` para redimensionar; uma janela frameless perde o resize pela
   borda.
5. Defina `AppUserModelID` antes de criar `QApplication` para exibir o ícone na
   barra de tarefas.

## Escolha do ícone (sempre apresentar opções)

Antes de aplicar o `.ico`, liste as variações disponíveis e peça ao usuário
para escolher. Nunca fixe um ícone por conta própria.

1. Procure arquivos `.ico` no workspace, na raiz e na pasta do app e em
   `guia-skills/`.
2. Apresente uma lista curta das opções encontradas, indique a opção padrão
   sugerida e aguarde a escolha.
3. Aplique somente o arquivo escolhido e use fallback resiliente:

   ```python
   _BASE_DIR = getattr(sys, "_MEIPASS", _DIR)   # fallback PyInstaller onefile
   _ICON_CANDIDATES = [
       os.path.join(_BASE_DIR, "app_icon.ico"),   # escolha do usuário
       os.path.join(_DIR, "app_icon.ico"),        # execução via .py
   ]
   _ICON_PATH = next((p for p in _ICON_CANDIDATES if os.path.isfile(p)), "")
   ```

4. Registre a escolha para reutilizá-la no build por meio da skill
   `gerar-exe`; `--icon` e `--add-data` devem usar exatamente o mesmo `.ico`.

## Checklist antes de gerar o `.exe`

- [ ] Verifique as escalas de 100%, 125%, 150% e 175%.
- [ ] Teste a janela em vários monitores com níveis de DPI diferentes e arraste
      a janela entre eles.
- [ ] Confirme contraste de pelo menos 4.5:1 nos temas claro e escuro.
- [ ] Navegue por teclado e confirme que o foco está sempre visível.
- [ ] Teste maximizar, restaurar e redimensionar.
- [ ] Confirme o ícone na janela, na barra de tarefas e no Alt+Tab.
- [ ] Confirme que nenhum valor visual está fora dos tokens.
- [ ] Confirme que a versão aparece uma única vez na interface.
- [ ] Confirme que o conteúdo continua acessível em tamanho mínimo e nas escalas
      maiores.

## Procedimento

1. Leia os documentos relevantes de `guia-skills/docs/ux/` antes de implementar.
2. Reutilize os tokens e padrões existentes; adapte o layout ao app sem
   introduzir valores de estilo avulsos.
3. Para mudança visual ampla, apresente a crítica e as opções, e aguarde
   aprovação antes de alterar.
4. Para o ícone, apresente as opções e confirme a escolha.
5. Execute o checklist desta skill e o checklist do documento relevante antes
   de gerar o `.exe`.
