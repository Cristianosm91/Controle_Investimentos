# Regras — Barra de título da janela (superior) leve e integrada

Padrão reutilizável para apps desktop **pywebview** (janela *frameless* com barra
de título customizada, clara e integrada ao restante da interface). Copie os
trechos e ajuste cores/títulos à identidade visual do seu projeto.

---

## Conceito

- A janela é **frameless** (`frameless=True`) — remove a barra nativa do Windows,
  que é escura, não pode ser recolorida e não comporta branding.
- No lugar dela, uma **barra de título HTML** clara (fundo `#F4F6F9`), integrada ao
  fundo do app, com:
  - à esquerda: marca opcional (logo e/ou ponto colorido) + nome do app;
  - à direita: controles **minimizar / maximizar / fechar**.
- A barra é a **região de arraste** da janela (`pywebview-drag-region`).
- Opcionalmente, abaixo dela um header do app com logo/subtítulo/versão.

### Por que assim
- Concentra o branding numa barra própria, com aparência moderna (custom chrome).
- Elimina o "duplo cabeçalho" (barra nativa escura + header do app).

---

## Regras de ouro (checklist)

1. `frameless=True` + `easy_drag=False` (só a `.pywebview-drag-region` arrasta; o
   conteúdo continua selecionável).
2. Marcar a barra com a classe **`pywebview-drag-region`**.
3. Nos **botões de controle**, `event.stopPropagation()` no `mousedown` para o
   clique não iniciar arraste.
4. Como frameless **não redimensiona pela borda** no backend Windows, forneça
   sempre **minimizar / maximizar / fechar** próprios.
5. **Maximizar** deve respeitar a **barra de tarefas**: use `rcWork` do monitor
   (o `maximize()` nativo em frameless cobre a tela inteira).
6. Reaplique o **ícone** no HWND (frameless não associa o ícone à barra de tarefas).
7. Barra de título com `user-select: none` (evita selecionar o texto ao arrastar).

---

## 1. Python (pywebview) — criação da janela

```python
import os, sys
import webview

WINDOW_TITLE = "Meu App"            # usado também para achar o HWND (FindWindowW)

window = webview.create_window(
    WINDOW_TITLE,
    url=INDEX_HTML,
    js_api=Api(),
    width=win_w, height=win_h,
    min_size=(760, 480),            # só mínimo; sem tamanho fixo
    background_color="#002754",
    frameless=True,                 # remove a barra nativa
    easy_drag=False,                # só a .pywebview-drag-region arrasta
    text_select=True,               # permite selecionar/copiar o conteúdo
)
# Reaplica o ícone na barra de tarefas (frameless não o associa sozinho).
window.events.shown += lambda: _apply_window_icon(ICON_PATH, WINDOW_TITLE)
webview.start(icon=ICON_PATH)
```

## 2. Python — controles da janela (API exposta ao JS)

```python
_MAXIMIZED = False
_RESTORE_RECT = None   # geometria salva antes de maximizar (l, t, r, b)

class Api:
    def win_minimize(self):
        try: webview.windows[0].minimize()
        except Exception as exc: print(f"[aviso] minimize: {exc}")

    def win_toggle_max(self):
        global _MAXIMIZED, _RESTORE_RECT
        try:
            if _MAXIMIZED:
                _restore_window(_RESTORE_RECT); _MAXIMIZED = False
            else:
                _RESTORE_RECT = _maximize_to_workarea()
                _MAXIMIZED = _RESTORE_RECT is not None
        except Exception as exc:
            print(f"[aviso] maximize/restore: {exc}")
        return _MAXIMIZED

    def win_close(self):
        try: webview.windows[0].destroy()
        except Exception as exc: print(f"[aviso] close: {exc}")
```

## 3. Python — maximizar respeitando a barra de tarefas

```python
def _maximize_to_workarea():
    """Maximiza a janela frameless até a área de trabalho (exclui a barra de tarefas).
    Retorna a geometria anterior (l, t, r, b) para restaurar."""
    import ctypes
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    hwnd = user32.FindWindowW(None, WINDOW_TITLE)
    if not hwnd:
        return None

    class MONITORINFO(ctypes.Structure):
        _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", wintypes.RECT),
                    ("rcWork", wintypes.RECT), ("dwFlags", wintypes.DWORD)]

    prev = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(prev))
    saved = (prev.left, prev.top, prev.right, prev.bottom)

    MONITOR_DEFAULTTONEAREST = 2
    hmon = user32.MonitorFromWindow(hwnd, MONITOR_DEFAULTTONEAREST)
    mi = MONITORINFO(); mi.cbSize = ctypes.sizeof(MONITORINFO)
    if not user32.GetMonitorInfoW(hmon, ctypes.byref(mi)):
        return None

    w = mi.rcWork
    SWP_NOZORDER, SWP_NOACTIVATE = 0x0004, 0x0010
    user32.SetWindowPos(hwnd, None, w.left, w.top,
                        w.right - w.left, w.bottom - w.top,
                        SWP_NOZORDER | SWP_NOACTIVATE)
    return saved


def _restore_window(rect):
    import ctypes
    if not rect: return
    user32 = ctypes.windll.user32
    hwnd = user32.FindWindowW(None, WINDOW_TITLE)
    if not hwnd: return
    l, t, r, b = rect
    user32.SetWindowPos(hwnd, None, l, t, r - l, b - t, 0x0004 | 0x0010)
```

## 4. Python — reaplicar o ícone no HWND (barra de tarefas)

> **Qual `.ico` usar:** pergunte ao usuário qual ícone o app deve ter antes de
> aplicar (ex.: `assets/app_icon.ico`). Não invente nem reutilize o ícone de
> outro app sem confirmação.

```python
ICON_PATH = os.path.join(BASE_DIR, "assets", "app_icon.ico")
```

```python
def _apply_window_icon(icon_path, title):
    """Envia WM_SETICON ao HWND real (frameless não associa o ícone sozinho)."""
    import ctypes, os
    if not os.path.isfile(icon_path): return
    try:
        user32 = ctypes.windll.user32
        IMAGE_ICON, LR_LOADFROMFILE, LR_DEFAULTSIZE = 1, 0x10, 0x40
        WM_SETICON, ICON_SMALL, ICON_BIG = 0x0080, 0, 1
        hwnd = user32.FindWindowW(None, title)
        if not hwnd: return
        big = user32.LoadImageW(None, icon_path, IMAGE_ICON, 0, 0,
                                LR_LOADFROMFILE | LR_DEFAULTSIZE)
        small = user32.LoadImageW(None, icon_path, IMAGE_ICON, 16, 16, LR_LOADFROMFILE)
        if big:   user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, big)
        if small: user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, small)
    except Exception:
        pass
```

## 5. HTML — a barra de título

```html
<header class="titlebar pywebview-drag-region">
  <div class="tb-title">
    <!-- opcional: logo do projeto (SVG/IMG) -->
    <img class="tb-logo" src="assets/logo.svg" alt="Logo">
    <span class="tb-dot"></span>            <!-- opcional: indicador colorido -->
    <span class="tb-app">Meu App</span>
  </div>
  <div class="win-controls" id="win-controls">
    <button class="win-btn" id="win-min" title="Minimizar" aria-label="Minimizar">
      <svg viewBox="0 0 12 12" width="11" height="11"><rect x="1" y="5.5" width="10" height="1.2" fill="currentColor"/></svg>
    </button>
    <button class="win-btn" id="win-max" title="Maximizar" aria-label="Maximizar">
      <svg viewBox="0 0 12 12" width="11" height="11"><rect x="1.5" y="1.5" width="9" height="9" fill="none" stroke="currentColor" stroke-width="1.2"/></svg>
    </button>
    <button class="win-btn win-close" id="win-close" title="Fechar" aria-label="Fechar">
      <svg viewBox="0 0 12 12" width="11" height="11"><path d="M2 2 L10 10 M10 2 L2 10" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/></svg>
    </button>
  </div>
</header>
```

## 6. CSS — barra clara e integrada + controles

```css
:root { --accent:#0078D4; --navy:#002754; --steel:#6699CC; --light:#F4F6F9; --line:#dfe5ee; }

/* a barra é fixa; o conteúdo (main) é que rola */
.titlebar, .topbar { flex: none; }

.titlebar {
  display: flex; align-items: center; justify-content: space-between;
  background: var(--light); color: var(--navy);
  height: 36px; padding: 0 6px 0 14px;
  border-bottom: 1px solid var(--line);
  user-select: none; -webkit-user-select: none;   /* não seleciona ao arrastar */
}
/* Espaçamento por MARGIN (não use `gap`): o QtWebEngine 5.15.2 = Chromium 83
   ignora `gap` em flexbox (só chegou no Chromium 84). Ver Armadilhas. */
.tb-title { display: flex; align-items: center; }
.tb-logo  { height: 16px; width: auto; display: block; }
.tb-dot   { width: 8px; height: 8px; border-radius: 50%; background: var(--accent); margin: 0 9px; }
.tb-app   { font-size: 12.5px; font-weight: 600; color: #33465c; letter-spacing: .2px; }

/* controles de janela */
.win-controls { display: flex; align-items: center; gap: 2px; }
.win-btn {
  width: 40px; height: 30px;
  display: flex; align-items: center; justify-content: center;
  background: transparent; border: none; border-radius: 6px;
  color: #5a6a7e; cursor: pointer;
  transition: background .12s, color .12s;
}
.win-btn:hover  { background: #e4e9f1; color: var(--navy); }
.win-btn:active { background: #d7deea; }
.win-btn.win-close:hover { background: #e81123; color: #fff; }
.win-btn:focus-visible { outline: 2px solid var(--steel); outline-offset: 1px; }
```

## 7. JS — ligar os controles (ponte pywebview)

```js
function whenReady(cb) {
  if (window.pywebview && window.pywebview.api) return cb();
  window.addEventListener("pywebviewready", cb, { once: true });
}

// evita que clicar nos botões inicie o arraste da janela
document.getElementById("win-controls")
  .addEventListener("mousedown", (e) => e.stopPropagation());

let API = null;
document.getElementById("win-min").addEventListener("click",  () => API && API.win_minimize());
document.getElementById("win-max").addEventListener("click",  () => API && API.win_toggle_max());
document.getElementById("win-close").addEventListener("click", () => API && API.win_close());

whenReady(() => { API = window.pywebview.api; });
```

---

## 8. PyQt5 — widgets nativos (sem QWebEngine / sem HTML)

> **Quando usar:** apps PyQt5 feitos com **widgets nativos** (`QWidget`,
> `QLabel`, `QPushButton`…), **sem** `QWebEngineView` e **sem** HTML/CSS/JS.
> As seções 1–7 (pywebview/HTML) **não se aplicam**; traduza o mesmo visual para
> widgets Qt usando as regras abaixo.

### Regras de ouro (widgets nativos)

1. **Frameless:** `self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)` na
   construção da janela (antes do `show()`).
2. **Ponto colorido (opcional) é desenhado com `QPainter`** — **nunca** `QLabel` +
   `border-radius` (vira **quadrado** em widget vazio).
3. **Espaçamento por `layout.addSpacing(9)`** entre marca/ponto/nome — o `margin`
   de stylesheet **não** gera folga confiável entre widgets num `QHBoxLayout`
   (equivale à proibição do `gap`, mas no mundo dos widgets Qt).
4. **Versão só no header do app**, **nunca** na barra de título
   (ver [versao-header.md](versao-header.md)).
5. **Controles próprios** minimizar/maximizar/fechar (`QPushButton`); a barra é a
   **região de arraste** (eventos de mouse); **duplo-clique** alterna maximizar.
6. **Maximizar:** use `self.showMaximized()` — o Qt já respeita a **área de
   trabalho** (barra de tarefas), sem precisar do cálculo de `rcWork`.
7. **Redimensionar:** frameless perde o resize pela borda — adicione um
   **`QSizeGrip`** (ex.: no canto inferior direito / barra de status).
8. **Cantos arredondados (Windows 11):** frameless não arredonda sozinho — peça
   ao DWM via `DWMWA_WINDOW_CORNER_PREFERENCE`.
9. **Ícone na barra de tarefas:** `self.setWindowIcon(QIcon(ico))` + defina um
   **`AppUserModelID`** próprio (senão herda o ícone genérico do `python.exe`).

### 8.1 Ponto colorido opcional (círculo desenhado)

```python
from PyQt5.QtGui import QPainter, QColor
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget

class ColorDot(QWidget):
    """Ponto circular colorido. QLabel+border-radius vira quadrado — use QPainter."""
    def __init__(self, diameter: int = 8, color: str = "#0078D4", parent=None):
        super().__init__(parent)
        self._d = diameter
        self._color = color
        self.setFixedSize(diameter, diameter)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(self._color))
        p.drawEllipse(0, 0, self._d, self._d)
```

### 8.2 Barra de título + arraste + controles

```python
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton

class TitleBar(QWidget):
    _BAR_H = 36
    def __init__(self, win: QWidget):
        super().__init__(win)
        self._win = win
        self._drag_offset = None
        self.setFixedHeight(self._BAR_H)
        self.setStyleSheet("background:#F4F6F9; border-bottom:1px solid #DFE5EE;")
        lay = QHBoxLayout(self); lay.setContentsMargins(14, 0, 6, 0); lay.setSpacing(0)

        app_lbl = QLabel("Meu App")            # SEM versão aqui
        app_lbl.setStyleSheet("color:#33465C; font-size:12.5px; font-weight:600;")

        lay.addWidget(ColorDot(8), 0, Qt.AlignVCenter)   # opcional
        lay.addSpacing(9)                       # espacamento pelo LAYOUT, nao 'margin'
        lay.addWidget(app_lbl)
        lay.addStretch(1)
        for glyph, tip, slot, close in (
            ("\u2015", "Minimizar", win.showMinimized, False),
            ("\u25A1", "Maximizar", self._toggle_max, False),
            ("\u2715", "Fechar",    win.close,         True),
        ):
            b = QPushButton(glyph); b.setToolTip(tip); b.setFixedSize(40, 30)
            b.setCursor(Qt.PointingHandCursor)
            hover = "#E81123" if close else "#E4E9F1"
            fg = "#FFFFFF" if close else "#002754"
            b.setStyleSheet("QPushButton{background:transparent;border:none;"
                            "border-radius:6px;color:#5A6A7E;}"
                            f"QPushButton:hover{{background:{hover};color:{fg};}}")
            b.clicked.connect(slot); lay.addWidget(b)

    def _toggle_max(self):
        self._win.showNormal() if self._win.isMaximized() else self._win.showMaximized()

    # Arraste da janela pela barra
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton and not self._win.isMaximized():
            self._drag_offset = e.globalPos() - self._win.frameGeometry().topLeft()
    def mouseMoveEvent(self, e):
        if self._drag_offset and e.buttons() & Qt.LeftButton and not self._win.isMaximized():
            self._win.move(e.globalPos() - self._drag_offset)
    def mouseReleaseEvent(self, e):
        self._drag_offset = None
    def mouseDoubleClickEvent(self, e):
        if e.button() == Qt.LeftButton: self._toggle_max()
```

### 8.3 Cantos arredondados (Windows 11) — chamar no `showEvent`

```python
def apply_rounded_corners(win):
    """Frameless nao arredonda sozinho; Win10 ignora silenciosamente."""
    import os, ctypes
    from ctypes import wintypes
    if os.name != "nt":
        return
    try:
        DWMWA_WINDOW_CORNER_PREFERENCE, DWMWCP_ROUND = 33, 2
        pref = ctypes.c_int(DWMWCP_ROUND)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            wintypes.HWND(int(win.winId())),
            DWMWA_WINDOW_CORNER_PREFERENCE, ctypes.byref(pref), ctypes.sizeof(pref))
    except Exception:
        pass
```

### 8.4 `QSizeGrip` (redimensionar) e ícone na barra de tarefas

```python
from PyQt5.QtWidgets import QSizeGrip
grip = QSizeGrip(status_bar); grip.setFixedSize(16, 16)
status_layout.addWidget(grip, 0, Qt.AlignBottom | Qt.AlignRight)
```

```python
# antes de criar o QApplication — senão a taskbar usa o ícone do python.exe
if os.name == "nt":
    import ctypes
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("MinhaEmpresa.MeuApp")
```

---

## Armadilhas conhecidas

- **Ícone**: o backend winforms exige `.ico` em `webview.start(icon=...)`; SVG/PNG
  quebram (`Argument 'picture' must be a picture that can be used as a Icon`).
  Em frameless, ainda é preciso reaplicar via `WM_SETICON` (passo 4).
- **`FindWindowW` depende do título** — mantenha `WINDOW_TITLE` único e igual em
  `create_window` e nas funções de janela.
- **Maximizar nativo em frameless cobre a barra de tarefas** — use `rcWork`.
- **Arraste vs. seleção**: sempre `easy_drag=False` + `pywebview-drag-region` na
  barra; e `stopPropagation` nos botões de controle.
- **`gap` de flexbox NÃO funciona em PyQt5 QtWebEngine 5.15.2 (Chromium 83)** —
  o suporte a `gap` em flex só chegou no Chromium 84. Sintoma: ponto/ícone
  "colado" no título. Use **`margin`** para espaçar (ex.: `.tb-dot { margin: 0 9px }`).
  Em pywebview (WebView2/Edge moderno) o `gap` funciona, mas prefira `margin`
  para o mesmo CSS servir aos dois backends.
- Rode com `PYTHONUTF8=1` para evitar problemas de acentuação no console.

### Armadilhas — PyQt5 widgets nativos (seção 8)

- **Ponto colorido quadrado:** `QLabel` + `background`/`border-radius` **não**
  arredonda em widget vazio — desenhe o círculo com `QPainter.drawEllipse`.
- **Ponto "colado" no título:** `margin` de stylesheet não espaça widgets num
  `QHBoxLayout` — use `layout.addSpacing(9)`.
- **Versão duplicada:** não repita a versão na barra de título; ela vive só no
  header do app ([versao-header.md](versao-header.md)).
- **Cantos retos no Win11:** frameless não arredonda sozinho — chame
  `DwmSetWindowAttribute(...DWMWA_WINDOW_CORNER_PREFERENCE...)` no `showEvent`.
- **Sem redimensionar:** frameless perde o resize pela borda — adicione `QSizeGrip`.
- **Ícone genérico na taskbar:** defina um `AppUserModelID` antes do `QApplication`.

## Layout de altura total (para a barra ficar fixa)

```css
* { box-sizing: border-box; }
html, body { height: 100%; }
body { margin: 0; display: flex; flex-direction: column; overflow: hidden; }
main { flex: 1 1 auto; min-height: 0; overflow: auto; }  /* o conteúdo rola aqui */
```
