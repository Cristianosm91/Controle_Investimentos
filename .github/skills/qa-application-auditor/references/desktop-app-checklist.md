# Checklist — aplicações desktop

Carregue quando o app for desktop: PyQt5/PyQt6/PySide, pywebview, Tkinter/CustomTkinter,
WinForms/WPF, Electron ou executável empacotado (PyInstaller).

## Interface e experiência de uso

| Verificar | Onde procurar | Como comprovar |
|---|---|---|
| Congelamento da interface | I/O, rede, banco, `subprocess.run`, `time.sleep` em slots/handlers de botão | Medir latência do event loop (abaixo) durante a operação |
| Operações síncronas pesadas | Processamento de arquivos/relatórios no handler | Idem + tempo da operação |
| Ausência de indicação de progresso | Operações > ~1 s sem barra/spinner/status | Teste de interface/manual |
| Ausência de cancelamento | Operações longas sem botão/flag de cancelamento | Tentar cancelar; verificar se para e libera recursos |
| Cliques repetidos → operações duplicadas | Botão não desabilitado durante a execução; sem guarda de reentrância | Disparar o clique N vezes rapidamente (teste de UI ou chamada direta do slot) |
| Atualizações excessivas da UI | `setText`/`repaint`/`evaluate_js` por item em loop grande | Profiling; CPU alta durante atualização |
| Erros não tratados encerrando o app | Exceção em slot/thread sem `try` ou `sys.excepthook` | Forçar exceção com dublê |
| Falta de recuperação após falha | Estado inconsistente após erro (botões desabilitados para sempre) | Forçar erro e tentar repetir a operação |

## Threads e event loop por framework

- **PyQt/PySide**: trabalho pesado em `QThread`/`QThreadPool`/`QRunnable`; UI só na thread
  principal (atualizar via `signal`). Conferir `quit()` + `wait()` no `closeEvent`, `deleteLater()`
  em widgets dinâmicos, `QTimer` parado ao fechar, `disconnect` de sinais em objetos de vida curta.
- **pywebview**: métodos do `js_api` rodam em thread separada — verificar acesso concorrente a
  estado compartilhado e chamadas `evaluate_js` em excesso; `webview.start()` bloqueia a thread
  principal; callbacks de fechamento liberam recursos.
- **Tkinter**: nenhuma chamada de widget fora da thread principal; usar `after()` para polling
  (intervalo razoável) e `queue` para comunicação com threads.
- **WinForms/WPF**: `async/await` sem `.Result`/`.Wait()` na UI (deadlock); `Invoke`/`Dispatcher`
  para atualizar a UI; `Dispose` de timers, `Bitmap`, `Graphics`, `Process`.
- **Electron**: trabalho pesado fora do renderer; IPC sem flood; `contextIsolation` ligado,
  `nodeIntegration` desligado.

## Específicos do Windows

- **Handles/GDI**: `ctypes`/`win32` (`CloseHandle`, `DeleteObject`, `ReleaseDC`); acompanhar a
  coluna `handles` do `collect_metrics.py` ao abrir/fechar telas repetidamente.
- **Caminhos**: espaços, acentos, OneDrive (arquivos sob demanda podem bloquear a leitura), caminhos
  > 260 caracteres, unidades de rede lentas.
- **Arquivos bloqueados**: arquivo aberto no Excel/antivírus → tratar `PermissionError`.
- **DPI/escala**: 100%, 125%, 150%, 175% — layout cabe e permanece utilizável.
- **Instância única**: abrir o app duas vezes — conflito de arquivos, portas ou locks?
- **Automação de UI** (`pyautogui`, `pywinauto`): FAILSAFE ativo, timeouts em esperas por janela,
  sem loop infinito aguardando elemento.

## Empacotamento (PyInstaller)

- `--onefile` extrai para `%TEMP%\_MEIxxxx`: encerramento forçado deixa a pasta para trás —
  verificar com `inspect_large_files.py --root $env:TEMP` (somente leitura) antes/depois.
- Recursos via `sys._MEIPASS` com fallback para execução em desenvolvimento.
- Antivírus pode atrasar a inicialização: medir tempo de abertura do `.exe` separadamente do `.py`.
- Processos filhos (`subprocess`) com `CREATE_NO_WINDOW` e encerrados ao fechar o app.

## Medir congelamento da UI (somente em teste)

Sonda de latência do event loop para usar **em arquivo de teste**, não no código produtivo.
Exemplo PyQt:

```python
import time
from PyQt5.QtCore import QTimer

class LoopLagProbe:
    """Registra quanto o event loop atrasou em relação ao intervalo esperado."""
    def __init__(self, interval_ms=50):
        self.interval = interval_ms / 1000
        self.max_lag = 0.0
        self._last = time.perf_counter()
        self._timer = QTimer()
        self._timer.timeout.connect(self._tick)
        self._timer.start(interval_ms)

    def _tick(self):
        now = time.perf_counter()
        self.max_lag = max(self.max_lag, now - self._last - self.interval)
        self._last = now

    def stop(self):
        self._timer.stop()
```

Critério sugerido: atraso máximo > 200 ms = UI perceptivelmente travada; > 1 s = congelamento.
Em Tkinter, a mesma ideia com `root.after()`.

## Inicialização e encerramento

- Abrir/fechar o app N vezes: sem processos órfãos (`Get-Process`), temporários ou locks restantes.
- Fechar durante uma operação longa: threads encerradas, arquivos não corrompidos.
- Configurações persistidas íntegras após encerramento inesperado.
