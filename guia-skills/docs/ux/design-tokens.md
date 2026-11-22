# Design tokens — temas claro e escuro

Use os mesmos nomes e papéis de tokens em todos os componentes. Altere os
valores por tema, sem introduzir cores, tamanhos, espaçamentos ou raios
avulsos. O accent azul segue o padrão Fluent e deve ser adaptado somente com
aprovação quando o app já tiver identidade visual própria. Reserve verde para
estados de sucesso.

## CSS — tema claro e escuro

Defina o tema no elemento raiz com `data-theme="light"` ou
`data-theme="dark"`. Na primeira execução, escolha o tema do Windows; persista
a preferência explícita do usuário em `%APPDATA%\<App>\settings.json`.

```css
:root,
:root[data-theme="light"] {
  color-scheme: light;
  --font-family: "Segoe UI Variable", "Segoe UI", sans-serif;
  --font-size-sm: 12px;
  --font-size-md: 14px;
  --font-size-lg: 16px;
  --font-size-title: 20px;
  --font-weight-regular: 400;
  --font-weight-semibold: 600;

  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 20px;
  --space-6: 24px;
  --radius-sm: 4px;
  --radius-md: 8px;

  --color-canvas: #F5F5F5;
  --color-surface: #FFFFFF;
  --color-surface-subtle: #FAFAFA;
  --color-surface-hover: #F0F0F0;
  --color-surface-pressed: #E6E6E6;
  --color-text: #242424;
  --color-text-secondary: #616161;
  --color-text-disabled: #A19F9D;
  --color-border: #D1D1D1;
  --color-border-strong: #8A8886;
  --color-accent: #0F6CBD;
  --color-accent-hover: #115EA3;
  --color-accent-pressed: #0C3B5E;
  --color-on-accent: #FFFFFF;
  --color-focus: #005FB8;
  --color-window-close-hover: #C42B1C;
  --color-success: #0F7B0F;
  --color-warning: #8A5700;
  --color-error: #C42B1C;
  --color-info: #0F6CBD;

  --border-width: 1px;
  --shadow-card: 0 1px 2px rgb(0 0 0 / 10%);
  --focus-ring: 0 0 0 2px var(--color-focus);
  --motion-duration: 160ms;
  --motion-easing: ease-out;
}

:root[data-theme="dark"] {
  color-scheme: dark;
  --color-canvas: #202020;
  --color-surface: #292929;
  --color-surface-subtle: #2D2D2D;
  --color-surface-hover: #333333;
  --color-surface-pressed: #3D3D3D;
  --color-text: #F5F5F5;
  --color-text-secondary: #C7C7C7;
  --color-text-disabled: #737373;
  --color-border: #484848;
  --color-border-strong: #757575;
  --color-accent: #479EF5;
  --color-accent-hover: #62ABF5;
  --color-accent-pressed: #2886DE;
  --color-on-accent: #1A1A1A;
  --color-focus: #479EF5;
  --color-window-close-hover: #C42B1C;
  --color-success: #54B054;
  --color-warning: #F2C661;
  --color-error: #F1707B;
  --color-info: #479EF5;
  --shadow-card: 0 1px 2px rgb(0 0 0 / 35%);
}
```

Consuma os tokens em componentes, incluindo hover, pressed, foco visível,
desabilitado, carregando, vazio e erro. Mantenha pelo menos 4.5:1 de contraste
para texto normal nos dois temas. Evite transições fora de 120–200 ms e
desative-as quando o usuário pedir redução de movimento.

```css
body {
  background: var(--color-canvas);
  color: var(--color-text);
  font-family: var(--font-family);
  font-size: var(--font-size-lg);
}

.card {
  background: var(--color-surface);
  border: var(--border-width) solid var(--color-border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-card);
  padding: var(--space-4);
}

button:focus-visible,
input:focus-visible,
select:focus-visible {
  outline: none;
  box-shadow: var(--focus-ring);
}
```

Não aplique um botão primário a cada controle: use apenas um por área de ação.
Use `--color-success` somente para comunicar sucesso, não como cor de marca ou
de destaque.

## PyQt5 — equivalente em `theme.py`

Qt Style Sheets não oferecem variáveis CSS. Centralize os valores em `theme.py`
e construa as paletas/estilos a partir do dicionário do tema ativo. Mantenha os
mesmos papéis e valores visuais definidos no bloco CSS.

```python
# theme.py
TOKENS = {
    "light": {
        "canvas": "#F5F5F5",
        "surface": "#FFFFFF",
        "surface_subtle": "#FAFAFA",
        "surface_hover": "#F0F0F0",
        "surface_pressed": "#E6E6E6",
        "text": "#242424",
        "text_secondary": "#616161",
        "text_disabled": "#A19F9D",
        "border": "#D1D1D1",
        "border_strong": "#8A8886",
        "accent": "#0F6CBD",
        "accent_hover": "#115EA3",
        "accent_pressed": "#0C3B5E",
        "on_accent": "#FFFFFF",
        "focus": "#005FB8",
        "window_close_hover": "#C42B1C",
        "success": "#0F7B0F",
        "warning": "#8A5700",
        "error": "#C42B1C",
        "info": "#0F6CBD",
        "radius_sm": "4px",
        "radius_md": "8px",
        "border_width": "1px",
        "focus_width": "2px",
        "shadow_card": (0, 1, 2, 26),
    },
    "dark": {
        "canvas": "#202020",
        "surface": "#292929",
        "surface_subtle": "#2D2D2D",
        "surface_hover": "#333333",
        "surface_pressed": "#3D3D3D",
        "text": "#F5F5F5",
        "text_secondary": "#C7C7C7",
        "text_disabled": "#737373",
        "border": "#484848",
        "border_strong": "#757575",
        "accent": "#479EF5",
        "accent_hover": "#62ABF5",
        "accent_pressed": "#2886DE",
        "on_accent": "#1A1A1A",
        "focus": "#479EF5",
        "window_close_hover": "#C42B1C",
        "success": "#54B054",
        "warning": "#F2C661",
        "error": "#F1707B",
        "info": "#479EF5",
        "radius_sm": "4px",
        "radius_md": "8px",
        "border_width": "1px",
        "focus_width": "2px",
        "shadow_card": (0, 1, 2, 89),
    },
}

FONT_FAMILY = '"Segoe UI Variable", "Segoe UI"'
FONT_SIZES = {"sm": 12, "md": 14, "lg": 16, "title": 20}
FONT_WEIGHTS = {"regular": 400, "semibold": 600}
SPACING = {1: 4, 2: 8, 3: 12, 4: 16, 5: 20, 6: 24}
MOTION_DURATION_MS = 160
MOTION_EASING = "OutCubic"
```

Use `TOKENS[theme_name]` to preencher `QPalette` e QSS dos widgets; não
espalhe literais de cor nos componentes. No QSS, defina explicitamente os
estados de hover, pressed, foco visível, desabilitado, carregando, vazio e
erro. Use `shadow_card` para configurar `QGraphicsDropShadowEffect` e os
tokens de movimento em `QPropertyAnimation`. Salve a escolha do tema em
`%APPDATA%\<App>\settings.json` e use o tema do Windows como padrão inicial.

## Verificação

- [ ] Os mesmos papéis de token existem nos temas claro e escuro.
- [ ] Componentes consomem tokens; não há cores ou medidas avulsas.
- [ ] O accent é azul e o verde aparece somente para sucesso.
- [ ] Texto normal atinge contraste mínimo de 4.5:1 nos dois temas.
- [ ] Estados de interação, foco e conteúdo estão definidos.
- [ ] A preferência do usuário é persistida fora da pasta de instalação.
