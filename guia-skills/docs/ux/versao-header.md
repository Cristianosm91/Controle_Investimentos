# Regras — Versão da aplicação no header (topo, ao lado do título)

Padrão reutilizável para exibir **permanentemente a versão da aplicação** no
header principal, imediatamente após o nome da ferramenta, em **todas as telas**,
independente da tecnologia (web/Flask, pywebview, PyQt5 ou console).

> **Numeração da versão:** NÃO é tratada aqui. O formato `MAJOR.MINOR.CORREÇÃO`,
> tags e changelog ficam em [versionamento.md](../git/versionamento.md). Este documento cobre
> apenas **onde** e **como** a versão aparece na interface.
>
> **Barra de título:** ver [barra-de-titulo.md](barra-de-titulo.md). A versão fica
> **dentro** do bloco de título, ao lado do nome — nunca no rodapé.

---

## Resultado esperado

```
Meu App v4.0.0
```

- Posição: **canto superior esquerdo**, no mesmo container do título, logo após o
  nome da aplicação.
- Formato: **`vMAJOR.MINOR.CORREÇÃO`** (SemVer completo, sempre 3 dígitos, prefixo
  `v` — igual às tags Git `v4.0.0`). Conforme [versionamento.md](../git/versionamento.md).
- Visível **sem nenhuma interação**, ao abrir qualquer tela.

---

## Regras de ouro (checklist)

1. **Fonte única (`__version__`)**: a versão vem de **um único ponto** por projeto
   (`version.py`). Proibido hardcode espalhado (`<small>v4.0</small>`, títulos, etc.).
2. **Formato `vMAJOR.MINOR.CORREÇÃO`** sempre com 3 dígitos (`v4.0.0`, não `v4.0`).
3. **Todas as telas**: injete a versão de forma central (context processor, API JS
   ou helper), nunca tela a tela.
4. **Sem duplicidade na UI**: a versão visível aparece **só no header**. Não repita
   em rodapé, cards ou corpo. Título de janela/console é nível de SO (permitido),
   mas deve ler o **mesmo** `__version__`.
5. **Sincronia de build**: o `file_version_info.txt` do PyInstaller e o
   `CHANGELOG.md` usam o **mesmo** valor do `__version__`.
6. **Responsivo**: reutilize o estilo do título (`<small>` sutil); `white-space:
   nowrap` no título para não quebrar linha.

---

## 0. Fonte única da versão — `version.py`

Um arquivo por projeto, na raiz, importado por todos os pontos que exibem a versão:

```python
# version.py
__version__ = "4.0.0"          # única fonte da verdade (SemVer — ver docs/git/versionamento.md)
APP_NAME = "Meu App"

def full_title() -> str:
    """Título com versão: 'Meu App v4.0.0'."""
    return f"{APP_NAME} v{__version__}"
```

> Ao subir a versão: altere **apenas** `__version__`, gere a tag `vX.Y.Z` e
> atualize o `CHANGELOG.md`. O `file_version_info.txt` deve derivar deste valor.

---

## 1. Web (Flask + HTML) — context processor + Jinja

Expõe `app_version` para **todos** os templates automaticamente (uma vez só):

```python
# _backend.py
from version import __version__ as APP_VERSION

@app.context_processor
def _inject_version():
    return {"app_version": APP_VERSION}
```

```html
<!-- templates/index.html — dentro do bloco do título -->
<span class="header__title">Meu App <small>v{{ app_version }}</small></span>
```

---

## 2. pywebview estático (HTML + JS API) — sem Flask

Exponha a versão na API e preencha no carregamento:

```python
# app.py
from version import __version__

class Api:
    def get_version(self):
        return __version__
```

```html
<span class="tb-title">Meu App <small id="appVersion"></small></span>
```

```js
// app.js
window.addEventListener('pywebview-ready', async () => {
  const v = await window.pywebview.api.get_version();
  document.getElementById('appVersion').textContent = `v${v}`;
});
```

---

## 3. PyQt5 — `QLabel` no header

Reutilize `full_title()` da fonte única ao montar o cabeçalho:

```python
from PyQt5.QtWidgets import QLabel
from version import APP_NAME, __version__

titulo = QLabel(f"{APP_NAME}  <small>v{__version__}</small>")
titulo.setTextFormat(Qt.RichText)      # permite o <small>
```

> Também use `self.setWindowTitle(f"{APP_NAME} v{__version__}")` — mesmo valor,
> sem string literal duplicada.

---

## 4. Console (.py / .bat)

Título do terminal a partir da fonte única:

```python
import os
from version import full_title
os.system(f'title {full_title()}')     # "Meu App v4.0.0"
```

---

## CSS (web/pywebview) — estilo do sufixo de versão

```css
.header__title { white-space: nowrap; }         /* não quebra linha (responsivo) */
.header__title small {
  font-weight: 400;
  color: var(--text-muted, #999999);
  margin-left: 4px;                              /* margin, nunca gap (QtWebEngine) */
}
```

---

## Checklist ao criar/atualizar um app

- [ ] Existe um `version.py` com `__version__` como fonte única.
- [ ] Header mostra `Nome vMAJOR.MINOR.CORREÇÃO` (3 dígitos, prefixo `v`).
- [ ] Versão injetada de forma central (context processor / API JS / helper).
- [ ] Aparece em **todas** as telas, sem interação.
- [ ] **Não** há versão duplicada em rodapé/corpo/cards.
- [ ] `file_version_info.txt`, título de janela/console e `CHANGELOG.md` usam o
      mesmo `__version__`.
- [ ] `.header__title` com `white-space: nowrap` (responsivo).
