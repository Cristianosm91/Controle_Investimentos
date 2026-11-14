---
name: UX de apps desktop
description: "Use ao criar/editar UI de apps desktop em Python (barra de título frameless, ícone, responsividade DPI) em HTML/CSS/JS ou PyQt5. Aplica-se automaticamente a arquivos de front-end desses apps."
applyTo: ["**/web/**/*.css", "**/web/**/*.html", "**/static/**/*.css", "**/templates/**/*.html", "**/App*.py"]
---

# Regras de UX — apps desktop

Documentos completos: `guia-skills/docs/ux/`.

## Barra de título (frameless)
- Espaçamento entre elementos da barra: use `margin` (ex.: `.tb-icon { margin: 0 9px }`).
  **Nunca use `gap`** — o PyQt5 QtWebEngine 5.15.2 (Chromium 83) ignora `gap` em flexbox
  (os elementos ficam "colados"). Detalhes: [barra-de-titulo.md](../../guia-skills/docs/ux/barra-de-titulo.md).
- Janela frameless: forneça controles próprios (minimizar/maximizar/fechar) e
  reaplique o ícone via `WM_SETICON`.

## Responsividade / DPI
- Barras (título/header) fixas; a **área de conteúdo** é a que rola
  (`body` flex-column; `main { flex:1; min-height:0; overflow:auto }`).
- Escolha defaults que caibam a 175% de escala. Detalhes: [responsividade-dpi.md](../../guia-skills/docs/ux/responsividade-dpi.md).

## Ícone
- Use arquivo `.ico` (SVG/PNG quebram no backend). Bundle com `--add-data` no PyInstaller
  e resolva o caminho com fallback `sys._MEIPASS` (onefile).
