# Checklist de performance, recursos e confiabilidade

Referência da Etapa 3 (revisão técnica). Para cada item: **onde procurar**, e como **comprovar**
antes de registrar como falha confirmada. Sem comprovação → registre como **Suspeita**.

Categorias do `detect_project.py` relacionadas aparecem entre colchetes, ex.: `[loop-polling]`.

---

## Memória e recursos

| Verificar | Onde procurar | Como comprovar |
|---|---|---|
| Memory leaks | Objetos acumulados em listas/dicts globais, singletons, closures | Soak com `collect_metrics.py`: RSS cresce de forma consistente (R² alto) sob carga constante |
| Objetos retidos indevidamente | Referências em callbacks, caches de instância, widgets sem `deleteLater()` | Contagem de objetos antes/depois (`gc.get_objects()`, `tracemalloc`, heap snapshot) |
| Coleções sem limite | `append` em loop de longa duração, histórico, filas internas | Teste que repete a operação N vezes e mede tamanho/memória |
| Cache sem expiração/limite | `dict` como cache, `@lru_cache(maxsize=None)`, `@cache` | Mesma técnica; verificar política de expiração |
| Streams/arquivos não fechados `[open-sem-with]` | `f = open(...)` sem `with`, `FileStream` sem `using` | Handles crescendo; `ResourceWarning` com `python -X dev -W error::ResourceWarning` |
| Conexões não encerradas `[banco-de-dados]` `[integracao-rede]` | Conexões abertas por chamada sem `close`/pool | Conexões abertas no SO (`netstat -ano`) crescendo |
| Handles não liberados | `ctypes`/`win32` (`CreateFile`, `OpenProcess`, GDI) sem `CloseHandle`/`DeleteObject` | Coluna `handles` do `collect_metrics.py` crescendo |
| Eventos/callbacks não removidos | `connect` sem `disconnect`, `addEventListener` sem remover, observers | Repetir abrir/fechar tela N vezes e medir |
| Recursos descartáveis sem descarte | `IDisposable` sem `using`, `subprocess.Popen` sem `wait`/`communicate` | Processos zumbis/filhos (`processos` no CSV) |
| Buffers excessivos | Leitura inteira para memória, `bytearray` crescente | RSS ao processar arquivo grande |
| Cópias desnecessárias de grandes volumes | `list(...)` de geradores, `df.copy()`, concatenação de strings em loop | Profiling de memória (`tracemalloc`) |

## CPU e processamento

| Verificar | Onde procurar | Como comprovar |
|---|---|---|
| Loops infinitos `[loop-polling]` | `while True` sem condição de saída ou `break` alcançável | Teste com timeout; CPU 100% de um núcleo |
| Polling agressivo `[timers-jobs]` `[sleep-bloqueante]` | Timers com intervalo baixo (< 100 ms) sem necessidade | CPU do processo ocioso > ~5% de um núcleo |
| Busy wait | Loop verificando flag sem `sleep`/`Event.wait`/condição | CPU alta sustentada com app ocioso |
| Recursão sem limite | Recursão sobre dados externos (árvores, diretórios, JSON) | Entrada profunda gerada → `RecursionError`/stack overflow |
| Algoritmos ineficientes | Loops aninhados sobre coleções grandes, `in` em lista dentro de loop | Medir tempo com 10×, 100× o volume; crescimento quadrático |
| Reprocessamentos desnecessários | Mesma consulta/cálculo a cada evento/tick | Contar chamadas com mock/spy |
| Parsing repetido | `re.compile`/`json.loads`/leitura de config dentro de loop | Profiling (`cProfile`) |
| Operações caras frequentes | I/O ou rede em handler de evento de alta frequência (scroll, keypress, timer) | Profiling durante uso |
| Processamento pesado na thread de UI | Ver [desktop-app-checklist.md](desktop-app-checklist.md) | Medição de latência do event loop |

## Concorrência

| Verificar | Onde procurar `[concorrencia]` | Como comprovar |
|---|---|---|
| Deadlocks | Dois locks adquiridos em ordens diferentes; lock + espera de thread que precisa do mesmo lock | Teste de concorrência com timeout; dump de threads (`faulthandler.dump_traceback_later`) |
| Race conditions | Estado compartilhado sem lock (contadores, listas, arquivos) | Teste com muitas threads; resultado não determinístico |
| Locks excessivos | Lock cobrindo I/O ou rede | Throughput não escala com threads |
| Locks ausentes | Escrita concorrente em arquivo/estrutura compartilhada | Corrupção/perda em teste concorrente |
| Starvation | Prioridade/fila injusta, worker sempre ocupado | Medir latência de tarefas de baixa prioridade |
| Threads órfãs | `Thread` não-daemon sem `join`, `QThread` sem `quit/wait` | Processo não encerra; `threads` no CSV crescendo |
| Tasks não aguardadas | `asyncio.create_task` sem referência/`await`; `Task.Run` fire-and-forget | Warnings "Task was destroyed but it is pending"; exceções perdidas |
| Falta de cancelamento | Operações longas sem `Event`/`CancellationToken`/`AbortController` | Cancelar no meio e medir se para |
| Acesso concorrente inseguro | Objetos de UI acessados fora da thread de UI; conexão SQLite compartilhada | Crash intermitente; `check_same_thread` |
| Filas sem limite | `queue.Queue()` sem `maxsize`, `asyncio.Queue()` sem limite | Produtor mais rápido que consumidor → memória cresce |
| Uso incorreto de semáforos/mutex/pools | `acquire` sem `release` em exceção; pool sem limite | Revisão + teste de exceção no meio |

## Rede e integrações

| Verificar | Onde procurar `[integracao-rede]` `[http-sem-timeout]` | Como comprovar |
|---|---|---|
| Ausência de timeout | `requests.get(url)` sem `timeout=`, `HttpClient` sem `Timeout`, sockets sem `settimeout` | Fake local que nunca responde → chamada fica presa |
| Retry infinito | `while True: try ... except: continue` | Fake indisponível → loop eterno (CPU/log) |
| Retry sem backoff | Retry imediato | Contar requisições por segundo ao fake |
| Reconexão agressiva | Reconnect em loop sem espera | Idem |
| Falta de circuit breaker (quando aplicável) | Muitas chamadas a dependência já falhando | Fake falhando; latência acumulada |
| Falta de limite de concorrência | Requisições paralelas sem limite | Fake registra conexões simultâneas |
| Sockets não encerrados | `socket` sem `close`/`with` | `netstat` com conexões em `CLOSE_WAIT`/`TIME_WAIT` crescendo |
| Respostas incompletas/inválidas | `json()` sem tratamento, campos acessados sem checagem | Fake retornando corpo truncado/malformado |
| Dependência externa bloqueando a app | Chamada síncrona na UI ou no startup | Fake lento → UI congela / app não abre |
| Falhas que se propagam sem isolamento | Exceção de integração derruba o processo | Fake retornando erro → app encerra |

## Arquivos e disco

| Verificar | Onde procurar `[io-arquivo-integral]` `[log-sem-rotacao]` | Como comprovar |
|---|---|---|
| Leitura integral de arquivos grandes | `.read()`, `readlines()`, `ReadAllText`, `readFileSync`, `pd.read_csv` sem `chunksize` | Arquivo sintético grande → RSS proporcional ao arquivo |
| Carregamento completo de diretórios extensos | `os.listdir`/`glob` sobre pastas enormes, recursão sem limite | Pasta temporária com milhares de arquivos |
| Escrita excessiva | Flush/escrita por item, regravação do arquivo inteiro a cada mudança | Medir bytes escritos (`psutil` io_counters) |
| Temporários não removidos | `tempfile.mkstemp`/`NamedTemporaryFile(delete=False)` sem limpeza | `inspect_large_files.py` antes/depois |
| Falta de rotação de logs | `logging.FileHandler`, `basicConfig(filename=...)` | Tamanho do log após soak |
| Crescimento ilimitado de logs | Log em loop, log de payload inteiro | Idem |
| Operações bloqueantes | I/O na thread de UI ou em rede (OneDrive/share) | Latência da UI durante I/O |
| Disco cheio | Escrita sem tratar `OSError`/`ENOSPC` | Volume isolado pequeno (nunca o disco do usuário) |
| Falta de permissão | Escrita em `Program Files`, pasta de outro usuário, arquivo aberto no Excel | Arquivo somente leitura/bloqueado em pasta temporária |
| Caminhos inválidos/arquivos corrompidos | Caminhos com espaço, acento, > 260 chars; arquivo truncado | Fixtures com esses casos |

## Banco de dados

| Verificar | Onde procurar `[banco-de-dados]` `[sql-concatenado]` | Como comprovar |
|---|---|---|
| Consultas dentro de loops (N+1) | `execute` dentro de `for` | Contar consultas com spy/log do driver |
| Falta de paginação | `SELECT` sem `LIMIT/TOP`, `fetchall()` | Base de teste com volume alto |
| Transações longas | Transação aberta durante I/O/rede/UI | Bloqueios em teste concorrente |
| Conexões não liberadas | Conexão sem `close`/`with`/pool | Contagem de conexões no SGBD de teste |
| Ausência de timeout | Driver sem `timeout`/`connect_timeout`/`CommandTimeout` | Banco de teste com lock proposital |
| Falta de rollback | `except` sem `rollback` | Falha no meio → dados parciais |
| Consultas excessivas | Mesma consulta repetida | Spy/log |
| Grandes resultados desnecessários | `SELECT *`, carregar tudo para filtrar em memória | RSS com base volumosa |
| Concorrência e bloqueios | Escrita concorrente em SQLite sem `timeout`/WAL | Teste concorrente → `database is locked` |
| Indisponibilidade | Banco fora do ar | App trava, faz retry infinito ou encerra? |

---

## Ferramentas úteis (somente se já disponíveis localmente)

- Python: `cProfile`, `tracemalloc`, `faulthandler`, `python -X dev`, `py-spy` (se instalado).
- .NET: `dotnet-counters`, `dotnet-trace` (se instalados).
- Node: `--inspect` + heap snapshot, `--cpu-prof`.
- Windows: Gerenciador de Tarefas/Resource Monitor (colunas Handles, Threads, GDI objects),
  `netstat -ano`.

Não instale ferramentas sem perguntar ao usuário.
