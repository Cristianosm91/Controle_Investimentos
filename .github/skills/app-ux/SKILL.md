---
name: app-ux
description: 'Use ao criar ou editar a interface (UI) de apps desktop em Python — barra de título frameless (custom chrome), ícone da janela/barra de tarefas do Windows, controles minimizar/maximizar/fechar, cantos arredondados, redimensionamento e responsividade/escala DPI. Aplica-se a apps pywebview e PyQt5 — tanto QWebEngine (HTML/CSS/JS) quanto widgets nativos (QWidget/QLabel/QPushButton). Palavras-gatilho: barra de título, titlebar, frameless, ícone .ico, WM_SETICON, cantos arredondados, QSizeGrip, AppUserModelID, DPI, responsividade, versão no header.'
---

# UX/UI de apps desktop (pywebview / PyQt5)

Técnicas reutilizáveis para apps desktop (web via pywebview, PyQt5 + QWebEngine,
ou PyQt5 de widgets nativos). Os detalhes ficam em `guia-skills/docs/ux/`.

## Quando usar
- Criar/editar uma **barra de título** própria (janela frameless).
- Tratar **responsividade** e **escala DPI** (barras fixas, conteúdo rolável).
- Definir/reaplicar o **ícone** da janela e da barra de tarefas.
- Exibir a **versão** do app junto ao título.

## Quando NÃO usar
- Interface web servida no navegador (SPA React/Vue etc.) sem janela desktop própria — use
  `web-ux-acessibilidade`. Se o app desktop embute HTML (pywebview/QWebEngine), use as duas:
  esta para a janela e aquela para o conteúdo.

## Fontes de verdade (leia antes de aplicar)
- Barra de título + ícone: [docs/ux/barra-de-titulo.md](../../../guia-skills/docs/ux/barra-de-titulo.md)
- Versão no header: [docs/ux/versao-header.md](../../../guia-skills/docs/ux/versao-header.md)
- Responsividade / DPI: [docs/ux/responsividade-dpi.md](../../../guia-skills/docs/ux/responsividade-dpi.md)

## Regras que NÃO podem ser esquecidas
1. **Espaçamento em flexbox no QtWebEngine:** use `margin` (ex.: `.tb-icon { margin: 0 9px }`),
   **nunca `gap`**. O PyQt5 QtWebEngine 5.15.2 (Chromium 83) ignora `gap` em flexbox.
2. **Ícone:** use arquivo `.ico` (SVG/PNG quebram no backend); em janela frameless,
   reaplique via `WM_SETICON`. **Sempre apresente as variações disponíveis e deixe o
   usuário escolher** antes de fixar o ícone (ver "Escolha do ícone").
3. **Barras fixas, conteúdo rolável:** `body` em flex-column;
   `main { flex:1; min-height:0; overflow:auto }`. Defaults que caibam a 175% de escala.
4. **Janela frameless:** forneça controles próprios (minimizar/maximizar/fechar).
5. **Versão no header:** ao lado do título, formato `vMAJOR.MINOR.CORREÇÃO` (`v4.0.0`),
   obtida de fonte única (`__version__`) — nunca hardcoded e sem duplicar em outros
   pontos da UI (ver versao-header.md).

## PyQt5 widgets nativos (sem QWebEngine) — não esquecer
Quando o app for PyQt5 de **widgets nativos** (sem HTML), as seções HTML/CSS não se
aplicam; traduza para Qt (ver barra-de-titulo.md):
1. **Formas circulares com `QPainter`** — `QLabel` + `border-radius` vira quadrado.
2. **Espaçamento com `layout.addSpacing(9)`** — `margin` de stylesheet não espaça widgets.
3. **Cantos arredondados** (Win11) via `DwmSetWindowAttribute` no `showEvent`.
4. **`QSizeGrip`** para redimensionar (frameless perde o resize pela borda).
5. **`AppUserModelID`** antes do `QApplication` para o ícone na barra de tarefas.

## Escolha do ícone (sempre apresentar opções)
Antes de aplicar o `.ico`, **liste as variações disponíveis e peça ao usuário para
escolher** — nunca fixe um ícone por conta própria.

1. **Procure os `.ico` no workspace** (raiz do app, pasta do app e `guia-skills/`).
2. **Apresente as opções encontradas** ao usuário (lista curta e clara) e **aguarde a
   escolha** — de preferência indicando qual é o padrão sugerido.
3. **Aplique só a opção escolhida**, com fallback resiliente:
   ```python
   _BASE_DIR = getattr(sys, "_MEIPASS", _DIR)   # fallback PyInstaller onefile
   _ICON_CANDIDATES = [
       os.path.join(_BASE_DIR, "app_icon.ico"),   # escolha do usuário
       os.path.join(_DIR, "app_icon.ico"),        # execução via .py
   ]
   _ICON_PATH = next((p for p in _ICON_CANDIDATES if os.path.isfile(p)), "")
   ```
4. **Registre a escolha** para reutilizar no build (`gerar-exe`) — o `--icon` e o
   `--add-data` devem usar exatamente o mesmo `.ico` escolhido aqui.

## Procedimento
1. Abra o(s) documento(s) de `guia-skills/docs/ux/` relevantes à tarefa.
2. Copie os trechos de HTML/CSS/Python e ajuste títulos/cores do app.
3. **Para o ícone, apresente as opções e confirme a escolha** (ver "Escolha do ícone").
4. Confira o checklist do documento antes de gerar o `.exe`.
