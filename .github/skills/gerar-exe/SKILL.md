---
name: gerar-exe
description: 'Use sempre que uma solicitação resultar na geração ou atualização de um executável (.exe) de um app Python: criar, empacotar, reconstruir, recompilar ou atualizar, inclusive pedidos equivalentes como gerar uma nova versão do aplicativo, preparar o app para distribuição ou entregar o programa atualizado, mesmo sem mencionar .exe, PyInstaller ou build. Reconstrói o .exe a partir da fonte validada (um .bat não basta). Usa PyInstaller no Windows — --onefile, .ico, --add-data, hidden imports e sys._MEIPASS. SEMPRE pergunta qual .ico usar e SEMPRE aciona o versionamento (git-workflow) para pôr a versão no nome. Cobre linha de comando direta e arquivo .spec. Palavras-gatilho: gerar exe, compilar, build, PyInstaller, onefile, add-data, hidden-import, spec, dist, MEIPASS, empacotar, executável, .ico, reconstruir, recompilar, atualizar executável, nova versão do aplicativo, distribuir o app, entregar o programa atualizado.'
---

# Gerar o executável (.exe) com PyInstaller

Padrão reutilizável para **compilar apps Python** em um `.exe` único no Windows.
Os apps usam PyInstaller em modo `--onefile` com um ícone `.ico` escolhido pelo usuário.

## Regras inegociáveis (leia primeiro)
1. **Gere o `.exe` DE FATO** — rode o PyInstaller e produza `dist\<Nome>.exe`. O
   `.bat` é **apenas um launcher ao lado do `.exe`**, criado DEPOIS do build.
   **Nunca** entregue só o `.bat` no lugar do executável.
2. **SEMPRE pergunte qual `.ico`** usar antes de compilar
   (ver "Ícone — SEMPRE perguntar"). É uma etapa **obrigatória e bloqueante**.
3. **SEMPRE acione o versionamento** (`git-workflow` / `guia-skills/docs/git/versionamento.md`)
   antes de cada build de distribuição e **calcule o nome pela branch**:
   `homolog` → `<App>-piloto-v<versao>` (regerações `-r1`, `-r2`, ...);
   `main` → `<App>-v<versao>`. Siga a regra de origem e revisões em
   [versionamento.md](../../../guia-skills/docs/git/versionamento.md). Nunca escolha
   manualmente piloto/produção, use produção como fallback ou renomeie o
   piloto como pacote definitivo.
4. **Confirme a origem do build:** o ponto de entrada e os recursos de interface
   usados pelo comando ou `.spec` devem ser os da versão atual do código-fonte.
   Reutilizar um binário anterior ou apenas criar/atualizar um `.bat` não basta.

## Quando usar
- **Qualquer solicitação que resulte em criar, empacotar, reconstruir ou atualizar
  um `.exe`**, mesmo sem mencionar `.exe`, PyInstaller ou build. Considere o
  resultado solicitado, não apenas as palavras: "gere uma nova versão do
  aplicativo", "prepare o app para distribuição" e "entregue o programa
  atualizado" acionam esta skill quando implicarem gerar/atualizar o executável.
- **Compilar** um script Python em `.exe` para distribuir sem instalar Python.
- **Empacotar arquivos de dados** (`.txt`, `.ico`, `.py` auxiliares, pastas) no executável.
- Resolver erros de **módulo não encontrado** em runtime (`hidden imports`).
- Criar/ajustar um arquivo **`.spec`** de build.
- Padronizar **pacotes piloto/produção por branch** e revisões `r1`, `r2`, ...
  na geração de executáveis.

## Quando NÃO usar
- Apenas rodar/testar o script em desenvolvimento (use `python app.py`).
- Definir/aplicar o ícone **na janela** do app em runtime — isso é UX
  (ver skill `app-ux` / `guia-skills/docs/ux/barra-de-titulo.md`).

## Pré-requisitos (instalar 1x)
```powershell
python -m pip install --upgrade pyinstaller
```

## Ícone — SEMPRE perguntar (obrigatório e bloqueante)
**Antes de montar o comando do PyInstaller, PERGUNTE ao usuário qual `.ico`
usar.** Nunca fixe um ícone por conta própria e nunca pule esta etapa.

1. **Procure os `.ico` no workspace** (pasta do app e `guia-skills/`) e **apresente as
   variações encontradas** para o usuário escolher (ex.: variações claro/escuro,
   `app_icon.ico` específico do app, se existir).
2. **Aguarde a escolha** do usuário (indique qual é o padrão sugerido) — não
   compile antes de confirmar.
3. Depois de escolhido, **use o MESMO `.ico`** em dois lugares:
   - `--icon "<escolhido>.ico"` — ícone do arquivo `.exe` no Explorer.
   - `--add-data "<escolhido>.ico;."` — para o `sys._MEIPASS` achá-lo em runtime
     (ícone da janela/barra de tarefas via `setWindowIcon` + `AppUserModelID`).
4. Se o `.ico` escolhido não estiver na pasta do app, **copie-o** para lá antes do
   build (o `--add-data` precisa do arquivo no projeto).

### Se o `.py` NÃO tiver ícone → o `.exe` sai sem ícone
Dois níveis de ícone, e **os dois** dependem de algo no build:
- **Ícone do arquivo `.exe`** (Explorer/atalho): vem **só** da flag `--icon`.
  → **Sempre passe `--icon "<mesmo .ico>"`.**
- **Ícone da janela / barra de tarefas** (runtime): vem **só** do código
  (`setWindowIcon` + `AppUserModelID`, resolvido via `sys._MEIPASS`) + `--add-data`.
  → Garanta a lógica do `app-ux` no `.py` e empacote o `.ico` com `--add-data`.

Regra: **nunca gere um `.exe` sem `--icon`**; e se a janela precisar do ícone, garanta
primeiro a lógica do `app-ux` no `.py`.

## Procedimento
1. **Identifique a origem do build:** siga o ponto de entrada até a interface
  principal e localize os templates/estáticos que precisam ser empacotados
  (`--add-data` ou `datas` do `.spec`).
2. Abra um terminal **na pasta do script principal** (o `.py` que inicia o app).
3. **Pergunte qual `.ico`** o usuário quer (etapa obrigatória — ver "Ícone — SEMPRE
   perguntar") e **aguarde a escolha** antes de montar o comando.
4. **Acione o versionamento** (`git-workflow` / `guia-skills/docs/git/versionamento.md`): confirme
   a fonte única da versão, identifique automaticamente a branch do repositório
   da aplicação e resolva o nome-base conforme
   [versionamento.md](../../../guia-skills/docs/git/versionamento.md). Em `homolog`,
   reserve a revisão automaticamente no histórico persistente antes do build.
   Origem não verificável ou falha na reserva bloqueia a distribuição com erro
   explícito; não peça o canal/revisão ao usuário.
5. Monte a linha do PyInstaller conforme o caso (ver receitas abaixo) ou ajuste o
  `.spec`, confirmando que usa a fonte validada e inclui os recursos da interface.
6. **Rode o comando e reconstrua a partir da fonte validada**, confirmando que
  **`dist\<Nome>.exe` foi gerado** — o build é obrigatório; **não** entregue só o `.bat`.
7. Teste o `.exe` gerado **fora do ambiente de dev** (outra pasta/máquina) para
  validar que todos os dados e imports foram empacotados e que a interface
  principal abre corretamente.
8. **Crie o launcher `.bat`** ao lado do `.exe` (mesmo nome do app) — ver seção
   "Launcher `.bat`". Reutilize o nome-base em todos os artefatos de distribuição
   e finalize o registro do build; preserve reservas de builds que falharam.

## Receitas

As receitas abaixo pressupõem `$NomePacote` **já calculado e reservado pelo
gerador**, seguindo [versionamento.md](../../../guia-skills/docs/git/versionamento.md).
Não atribua manualmente um nome de piloto/produção à variável. Ao aplicar esta
skill a um app, inspecione e integre o mecanismo existente de branch, versão e
histórico em todos os caminhos de build (comando direto, `.spec` e CI).
Se não houver mecanismo, implemente-o e valide os casos do guia antes de
distribuir. Estas receitas não implementam, sozinhas, a detecção ou o contador.

### 1) App simples (um arquivo, sem dados extras)
```powershell
python -m PyInstaller --noconfirm --onefile --clean --name "$NomePacote" `
  --icon "app_icon.ico" app.py
```

### 2) App com arquivos de dados embutidos
Cada recurso vira `--add-data "ORIGEM;DESTINO"` (no Windows o separador é **`;`**):
```powershell
python -m PyInstaller --onefile --clean `
  --name "$NomePacote" `
  --icon "app_icon.ico" `
  --add-data "servidores.txt;." `
  --add-data "diretorio.txt;." `
  --add-data "modules/colors.py;modules" `
  main.py
```

### 3) Resolver "ModuleNotFoundError" em runtime (hidden imports)
Comum com `pyautogui`, `pywin32` e afins:
```powershell
python -m PyInstaller --onefile --clean --icon "app_icon.ico" `
  --name "$NomePacote" `
  --hidden-import=pyautogui.windows `
  --hidden-import=pythoncom `
  --hidden-import=pywintypes `
  autenticar.py
```

### 4) App desktop com interface web embutida
**Este é o padrão a reproduzir** para apps de janela nativa que servem uma
interface web (PyQt5 + `QWebEngineView` + Flask/`web/`). Características: versão no
nome, `--noconsole`, pasta `web` embutida e hidden imports do QtWebEngine.
```powershell
python -m PyInstaller --onefile --noconsole --clean `
  --name "$NomePacote" `
  --icon "<ico_escolhido>.ico" `
  --add-data "web;web" `
  --add-data "<ico_escolhido>.ico;." `
  --add-data "servers.py;." `
  --add-data "_backend.py;." `
  --hidden-import "PyQt5.QtWebEngineWidgets" `
  --hidden-import "PyQt5.QtWebChannel" `
  app.py
```
Pontos do padrão:
- **Nome automático no `--name`** — branch, versão e revisão resolvidas via
  `git-workflow` / [versionamento.md](../../../guia-skills/docs/git/versionamento.md).
- **`--noconsole`** (app GUI, sem janela de terminal).
- **`--add-data "web;web"`** embute templates/estáticos da interface.
- **`--icon` + `--add-data` do mesmo `.ico` escolhido** pelo usuário.
- **Hidden imports do QtWebEngine** (`QtWebEngineWidgets`, `QtWebChannel`) —
  o PyInstaller não os detecta sozinho.
- Saída em `dist\<NomePacote>.exe` + launcher `.bat` de mesmo nome-base.

## Ler recursos empacotados em runtime (obrigatório com --onefile)
Com `--onefile`, os dados são extraídos para uma pasta temporária em `sys._MEIPASS`.
**Nunca** use o caminho relativo direto; resolva assim:
```python
import sys, os

def caminho_recurso(rel):
    """Caminho de um recurso, funcione como script ou empacotado (.exe)."""
    base = getattr(sys, "_MEIPASS", os.path.abspath("."))
    return os.path.join(base, rel)

# uso:
with open(caminho_recurso("servidores.txt"), encoding="utf-8") as f:
    ...
```

## Alternativa: arquivo .spec
Para builds repetíveis, gere e edite um `.spec` (o PyInstaller cria um no 1º build):
```powershell
python -m PyInstaller NomeApp.spec
```
Pontos-chave do `.spec`:
- `datas=[('servidores.txt', '.'), ('modules/colors.py', 'modules')]` — equivale a `--add-data`.
- `hiddenimports=[...]` — equivale a `--hidden-import`.
- `console=True` — app de terminal; `console=False` — app com janela (GUI).
- `icon=['app_icon.ico']`; `name` recebe o mesmo nome-base
  calculado/reservado pelo gerador, sem hardcode de canal, versão ou revisão.
  Não tente sobrescrever o nome de um `.spec` apenas com `--name`: integre
  o nome calculado nos objetos `EXE`/`COLLECT`, quando presentes.

## Flags úteis
| Flag | Efeito |
|------|--------|
| `--onefile` | Um único `.exe` (padrão do workspace) |
| `--clean` | Limpa cache/temporários do build anterior |
| `--noconfirm` | Dispensa confirmação do PyInstaller; não autoriza sobrescrever piloto registrado |
| `--name "X"` | Nome do executável de saída |
| `--icon "x.ico"` | Ícone do `.exe` (use `.ico`) |
| `--noconsole` / `--windowed` | Sem janela de console (apps GUI) |
| `--add-data "o;d"` | Empacota arquivo/pasta (`;` no Windows) |
| `--hidden-import=mod` | Força inclusão de módulo não detectado |

## Launcher `.bat` (na mesma pasta do `.exe`)
> ⚠️ O `.bat` **NÃO substitui** o build. Crie-o **depois** de gerar o `.exe`.

Sempre gere, **na mesma pasta do `.exe`**, um arquivo `.bat` com o **mesmo nome do app**
(mesmo nome-base do executável). O conteúdo é **obrigatoriamente** este — exatamente
**duas linhas**, sem comentários, sem `cd`, sem `start`, sem `%*`:

```bat
@echo off
cmd /k "<NomeDoApp>.exe"
```
Exemplo já preenchido (apenas ilustrativo do formato):
```bat
@echo off
cmd /k "MeuApp-piloto-v4.0.0-r1.exe"
```

Regra fixa: **use sempre `cmd /k "<exe>"`** — vale também para apps GUI/janela
(nunca troque por `start` nem adicione outras linhas). A única coisa que muda é o
nome do `.exe` entre aspas.

Regras:
- Nome do `.bat` = nome-base do `.exe` (ex.: `MeuApp-piloto-v4.0.0-r1.exe` →
  `MeuApp-piloto-v4.0.0-r1.bat`).
- Fica **ao lado** do `.exe` (mesma pasta de distribuição).
- Referêncie o `.exe` pelo nome (sem caminho absoluto), para o `.bat` funcionar em
  qualquer máquina onde a pasta for copiada.

## Checklist antes de entregar o .exe
- **Ícone escolhido pelo usuário** (perguntado — nunca fixado sozinho), em `.ico`
  (não `.png`), usado no `--icon` **e** no `--add-data`.
- **Fonte validada efetivamente empacotada**, com os recursos de interface
  incluídos no comando/`.spec`, e `.exe` reconstruído dessa versão. Apenas
  criar/atualizar um `.bat` ou reutilizar um binário anterior não é suficiente.
- **`.exe` realmente gerado** em `dist\<Nome>.exe` (não entregar só o `.bat`).
- **Branch de origem verificada automaticamente** no repositório da aplicação.
- **Nome padronizado em todos os artefatos:** `homolog` sempre contém `-piloto-`;
  `main` usa `<App>-v<versao>`, sem revisão de piloto.
- **Revisão automática e persistente** por aplicação/versão, sem sobrescrita
  nem colisão entre builds; validar os casos de
  [versionamento.md](../../../guia-skills/docs/git/versionamento.md).
- Todos os `.txt`/auxiliares acessados via `sys._MEIPASS` e incluídos com `--add-data`.
- **Launcher `.bat`** criado ao lado do `.exe`, com o mesmo nome do app.
- Testado em pasta/máquina **sem** o ambiente de desenvolvimento.
- `build/` e artefatos temporários não versionados desnecessariamente.

## Erros comuns (aprendidos)
- **Gerou só o `.bat` e não o `.exe`:** o `.bat` é apenas launcher — **rode o
  PyInstaller** e produza o `dist\<Nome>.exe`.
- **Não perguntou o ícone:** é obrigatório apresentar as variações disponíveis e aguardar
  a escolha antes de compilar.
- **Não acionou o versionamento:** confirme a versão (`git-workflow`) e
  coloque-a no `--name` antes do build.
- **`FileNotFoundError` só no `.exe`:** esqueceu `--add-data` ou leu sem `sys._MEIPASS`.
- **`ModuleNotFoundError` só no `.exe`:** falta `--hidden-import` (típico de `pyautogui`,
  `pythoncom`, `pywintypes`, `PyQt5.QtWebEngineWidgets`, `PyQt5.QtWebChannel`).
- **Separador errado no `--add-data`:** no Windows é `;`, não `:`.
- **Ícone não aparece:** use `.ico` (não `.png`) e caminho absoluto se necessário.
