# Regras de Responsividade, Resolução e High DPI (reutilizável)

Checklist e receitas para deixar apps desktop adaptáveis a múltiplos
monitores, resoluções e escalas do Windows (100 / 125 / 150 / 175%), sem cortes.
Cobre os dois stacks usados aqui: **pywebview (HTML/CSS)** e **PyQt5/PySide**.

---

## 0. Princípios (valem para qualquer stack)

1. **Nunca** use tamanhos/coordenadas fixas para layout. Defina apenas
   **largura/altura mínimas**; deixe a janela crescer livremente.
2. O conteúdo deve **rolar** quando faltar espaço — é preferível scroll a esconder.
3. Barras (título/header/rodapé) ficam fixas; a **área de conteúdo** é a que rola.
4. Scroll **vertical** quando faltar altura; **horizontal só quando necessário**.
5. Torne o processo **DPI-aware por monitor (v2)** e teste arrastando entre telas.
6. Ao abrir, **encolha para caber** na área útil do monitor (shrink-only).

---

## 1. High DPI (Windows) — a causa nº 1 de corte ao trocar de monitor

A definição de DPI awareness só vale a **primeira** vez no processo. Faça isso
**no início do `main()`, antes de criar qualquer janela**.

```python
def enable_high_dpi():
    """Per-Monitor v2 → rescala ao mover entre monitores de escalas diferentes."""
    import ctypes
    u = ctypes.windll.user32
    try:
        # DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 (Win10 1703+)
        u.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4)); return
    except Exception:
        pass
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2); return  # per-monitor v1
    except Exception:
        pass
    try:
        u.SetProcessDPIAware()  # system-aware (fallback)
    except Exception:
        pass
```

- **pywebview**: por padrão chama só `SetProcessDPIAware()` (v1). Chame
  `enable_high_dpi()` antes de `webview.create_window(...)` para forçar v2.
- **PyQt5**: antes de criar o `QApplication`:
  ```python
  from PyQt5.QtCore import Qt, QCoreApplication
  QCoreApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
  QCoreApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
  # opcional (Qt >= 5.14): política de arredondamento de fator de escala
  from PyQt5.QtGui import QGuiApplication
  QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
      Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
  ```
  (No PyQt6 o High DPI já é padrão.)

---

## 2. Tamanho inicial que cabe na tela (shrink-only)

Abrir maior que o monitor corta conteúdo — pior ainda em janela *frameless*
(sem redimensionar pela borda). Encolha para caber, **nunca** aumente.

```python
def fit_size(default_w, default_h, margin=48):
    """Dimensões LÓGICAS que cabem na área útil do monitor primário."""
    import ctypes
    u = ctypes.windll.user32
    try:
        cx = u.GetSystemMetrics(16)  # SM_CXFULLSCREEN (área útil)
        cy = u.GetSystemMetrics(17)  # SM_CYFULLSCREEN
        scale = (u.GetDpiForSystem() or 96) / 96.0  # física → lógica
        w = int(min(default_w, max(640, cx / scale - margin)))
        h = int(min(default_h, max(480, cy / scale - margin)))
        return w, h
    except Exception:
        return default_w, default_h
```

> ⚠️ pywebview trata `width/height` como **lógicos** (multiplica pela escala ao
> posicionar). Por isso dividimos a área física pela escala do sistema.

- Defina **somente** `min_size` (ex.: `(760, 480)`), nunca tamanho fixo.
- Escolha defaults que caibam a 175% (ex.: altura ≤ ~700 lógico).

---

## 3. Layout responsivo em CSS (pywebview / web)

Estrutura **flex de altura total**: barras fixas + `<main>` rolável.

```css
* { box-sizing: border-box; }
html, body { height: 100%; }
body { margin: 0; display: flex; flex-direction: column; overflow: hidden; }

.titlebar, .topbar, .footer { flex: none; }      /* barras fixas */
main {
  flex: 1 1 auto; min-height: 0;                  /* permite encolher/rolar */
  overflow-y: auto;                               /* scroll vertical sob demanda */
  overflow-x: auto;                               /* horizontal só se necessário */
  padding: 24px;
}
main > * { max-width: 1180px; margin-inline: auto; }  /* conteúdo centralizado */
```

Regras de ouro:
- Em filhos de `flex`/`grid` que podem transbordar, use **`min-width: 0`**
  (evita overflow horizontal).
- Colunas flexíveis com **`minmax(0, 1fr)`**, não `1fr` puro.
- Campo de busca: `flex: 1 1 260px; min-width: 0;` → ocupa o espaço e encolhe.
- Botões: `flex: none; white-space: nowrap;` → não extrapolam nem quebram.
- Textos longos (IDs/tokens): `overflow-wrap: anywhere;` ou `word-break: break-word;`.
- Barras com muitos itens: `flex-wrap: wrap;`.
- Breakpoints para empilhar (`@media (max-width: 820px) { ... 1fr ... }`).
- Blocos de código/JSON: `white-space: pre-wrap;` + `overflow: auto; max-height`.
- Use `px` em CSS sem medo: no WebView é densidade-independente (escala com DPI).

---

## 4. Layout responsivo em PyQt (quando o app for Qt)

- **Nunca** `setFixedWidth/Height` nem `setGeometry` para layout. Use layouts:
  `QVBoxLayout`, `QHBoxLayout`, `QGridLayout`.
- **Stretch factors**: `layout.addWidget(w, stretch)` / `addStretch()`.
- **QSizePolicy**: `Expanding` no que deve crescer (campo de busca, tabela),
  `Fixed/Preferred` nos botões.
- Área rolável: envolva o conteúdo em `QScrollArea` com
  `setWidgetResizable(True)`.
- Tabelas: `header.setSectionResizeMode(QHeaderView.Stretch)` (ou `ResizeToContents`
  nas colunas curtas + `Stretch` na principal).
- Só `setMinimumSize(...)`. Deixe o `sizeHint` cuidar do resto.

---

## 5. Janela frameless (custom chrome) — cuidados

- Sem barra nativa **não há redimensionar por borda** (no backend winforms) nem
  botões do SO → forneça controles próprios (minimizar/maximizar/fechar).
- Defina uma **região de arraste** (`.pywebview-drag-region`) e
  `easy_drag=False` para não arrastar ao selecionar texto.
- Faça `event.stopPropagation()` no `mousedown` dos botões da barra para o clique
  não iniciar arraste.
- **Ícone**: winforms exige `.ico` (SVG/PNG quebram).

---

## 6. Checklist de testes (obrigatório)

- [ ] 1920×1080 e 1920×1200.
- [ ] Notebook + monitor externo (escalas diferentes).
- [ ] **Arrastar a janela entre monitores** durante a execução (sem borrão/corte).
- [ ] Escalas 100 / 125 / 150 / 175%.
- [ ] Maximizar, restaurar e redimensionar manualmente.
- [ ] Janela no tamanho mínimo → conteúdo acessível via scroll, nada cortado.
- [ ] Sem scroll horizontal em uso normal (só quando realmente necessário).

---

## 7. Erros comuns (evitar)

- Definir DPI awareness **depois** de criar a janela (não tem efeito).
- Comparar tamanho lógico com área **física** do monitor (janela abre grande demais).
- `overflow: hidden` no container de conteúdo (esconde informação — use `auto`).
- `1fr` sem `minmax(0, …)` (causa overflow horizontal).
- Esquecer `min-width: 0` em filhos flex/grid.
- Tamanho fixo “porque ficou bom no meu monitor” — quebra em outra escala.
