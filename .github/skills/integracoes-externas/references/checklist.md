# Checklist — Integrações Externas

Cada item reprovado vira achado `INT-XXX` com evidência (`arquivo:linha`, trecho, saída de teste)
e proposta. Marque cada item como **OK · Achado · N/A · Não verificado** (com motivo).

## 1. Inventário
- [ ] Todas as integrações listadas, inclusive as implícitas (bibliotecas que fazem rede: wrappers de cotações, `pandas.read_html/read_csv(url)`, downloads em startup).
- [ ] Para cada uma: finalidade, formato, frequência, gatilho (usuário/job/startup), dado produzido, onde é persistido.
- [ ] Endpoints e parâmetros configuráveis por configuração/ambiente, não espalhados no código.
- [ ] Existe uma camada de adaptador/provedor; regras de negócio não fazem HTTP diretamente.

## 2. Rede e timeouts
- [ ] Timeout **explícito** em toda chamada, separando connect e read quando o cliente permite (`httpx.Timeout(connect=5, read=20)`, `requests.get(..., timeout=(5, 20))`).
- [ ] `requests` sem `timeout=` é achado (o padrão é esperar indefinidamente).
- [ ] Bibliotecas sem timeout configurável são isoladas (thread/processo com limite, `asyncio.wait_for`, `concurrent.futures` com `timeout`).
- [ ] Tamanho máximo de resposta/download definido; streaming para arquivos grandes; arquivos temporários removidos.
- [ ] Sessão/cliente reutilizado (pool de conexões) e fechado no shutdown; sem cliente novo por item em laço.
- [ ] Nº de requisições por atualização proporcional ao necessário (lote quando o provedor permite; sem N+1).

## 3. Retry, rate limit e circuit breaker
- [ ] Retry **somente** para operações idempotentes (GET/consultas) e para erros transitórios (timeout, conexão, 429, 502/503/504). Nunca para 400/401/403/404 nem para payload inválido.
- [ ] Backoff exponencial **com jitter** e limite de tentativas e de tempo total (ex.: `tenacity` `wait_random_exponential`, `stop_after_attempt`, `stop_after_delay`).
- [ ] 429 respeitado: lê `Retry-After` (segundos ou data HTTP); sem header, usa backoff conservador.
- [ ] Limite de taxa local (intervalo mínimo entre chamadas / semáforo) quando o provedor é sensível.
- [ ] Circuit breaker ou **cooldown** após N falhas consecutivas: suspende chamadas por um período e registra o estado.
- [ ] Retries não multiplicados em camadas (cliente + biblioteca + job tentando de novo).

## 4. Cache, frescor e indicação ao usuário
- [ ] Cache com TTL coerente com a natureza do dado (intradiário × diário × mensal).
- [ ] Cada dado persistido guarda **fonte** e **data/hora de referência** (do dado) e **data/hora de coleta**.
- [ ] UI exibe fonte e data/hora; dado acima do limite de frescor exibe **aviso de desatualizado**.
- [ ] Falha na atualização **não apaga** o último dado válido; mantém e sinaliza.
- [ ] Fins de semana/feriados/fora do pregão não geram falso alerta de dado antigo (limite considera calendário).

## 5. Fallback
- [ ] Ordem de fontes documentada; fallback é decisão de negócio (não alterar sem pedido).
- [ ] Dado vindo de fallback é **rotulado** com a fonte real usada.
- [ ] Fontes com semântica diferente (ajustado × não ajustado por proventos/splits, moeda, fuso, D-1) são normalizadas ou sinalizadas.
- [ ] Fallback não mascara erro persistente da fonte primária (gera log/alerta).

## 6. Parsing defensivo
- [ ] Payload validado por esquema (Pydantic/dataclass/TypedDict + checagens) antes de uso.
- [ ] Scraping HTML/CSV: verifica presença de colunas/seletores esperados; ausência gera erro "layout alterado" rastreável — **nunca** zero/vazio silencioso.
- [ ] Conversão numérica tolerante a locale (`1.234,56` × `1,234.56`), `"-"`, `"N/A"`, vazio → `None`, não `0`.
- [ ] Encoding explícito (UTF-8/Latin-1) em arquivos públicos legados.
- [ ] Valores fora de faixa plausível (preço ≤ 0, variação absurda, data futura) são rejeitados ou marcados.
- [ ] Mudança detectada é **reportada** (log WARNING/ERROR + status do job), não corrigida automaticamente.

## 7. "Sem dado" × "erro" × "zero"
- [ ] O modelo distingue `None`/ausente, erro de coleta e valor zero legítimo.
- [ ] `except Exception: return {}` ou `return 0` não confunde falha com ausência legítima — falha é logada **e** refletida no status.
- [ ] API devolve o estado (ex.: `status: "ok" | "sem_dado" | "erro" | "desatualizado"`) e a UI o representa de forma distinta.
- [ ] Cálculos agregados não tratam ausência como zero sem sinalizar (ver `calculos-financeiros-fiscais`).

## 8. TLS, proxy e identificação
- [ ] Nenhum `verify=False`, `ssl._create_unverified_context`, `NODE_TLS_REJECT_UNAUTHORIZED=0` ou `PYTHONHTTPSVERIFY=0`.
- [ ] Certificado corporativo/proxy tratado por **configuração** (bundle CA via `SSL_CERT_FILE`/`REQUESTS_CA_BUNDLE`/parâmetro `verify=<caminho>`, `truststore`, `HTTPS_PROXY`/`NO_PROXY`).
- [ ] Erro de certificado/proxy gera mensagem acionável ao usuário (não stack trace).
- [ ] `User-Agent` identifica a aplicação e versão (sem dados pessoais) quando o provedor permite.
- [ ] Nenhum segredo em URL/query string; tokens em header; URLs logadas sem query sensível.
- [ ] Credenciais de proxy fora do código e dos logs.

## 9. Jobs agendados
- [ ] Trava por tarefa: execução agendada e manual não se sobrepõem (`max_instances=1`, lock, ou rejeição com "tarefa ocupada").
- [ ] `coalesce=True` e `misfire_grace_time` definidos (app que dorme/hiberna não dispara rajada de execuções).
- [ ] Fuso horário **explícito** (`ZoneInfo`) no scheduler e nos gatilhos; horário de pregão/publicação respeitado.
- [ ] Backoff após falhas consecutivas (não repete a cada minuto contra provedor fora do ar).
- [ ] Duração máxima por job; job travado não bloqueia os demais.
- [ ] Status persistido: início, fim, duração, sucesso, mensagem resumida, itens sem dado.
- [ ] Scheduler iniciado uma única vez (cuidado com reload/múltiplos workers) e encerrado no shutdown.

## 10. Concorrência e event loop
- [ ] Rotas `async def` não chamam cliente síncrono (`requests`, wrappers síncronos) diretamente — usar `httpx.AsyncClient`, `run_in_threadpool`/`asyncio.to_thread` ou rota `def`.
- [ ] Paralelismo limitado (semáforo) ao consultar muitos ativos.
- [ ] Sessão de banco não compartilhada entre threads de job.
- [ ] Cancelamento/shutdown interrompe chamadas pendentes dentro do timeout.

## 11. Página de status para o usuário
- [ ] Tela/endpoint lista cada atualização: última execução, sucesso/erro, duração, próxima execução, itens sem dado.
- [ ] Mensagens em linguagem do usuário ("Fonte X indisponível; exibindo dados de dd/mm hh:mm").
- [ ] Ação manual "atualizar agora" respeita trava e rate limit.

## 12. Testes de contrato
Ferramentas: `respx`/`pytest-httpx` (httpx), `responses` (requests), `vcrpy`/`pytest-recording` (cassetes), monkeypatch do wrapper para bibliotecas, MSW (front).
- [ ] Cenários por integração: sucesso · timeout · erro de conexão · 429 com e sem `Retry-After` · 5xx · 4xx · payload malformado · payload vazio · layout/colunas alteradas · dado parcial.
- [ ] Testes rodam **sem rede** (bloquear sockets: `pytest-socket` `--disable-socket` ou fixture equivalente).
- [ ] Cassetes/fixtures sanitizados (sem cookies, tokens, IPs, dados pessoais) e pequenos.
- [ ] Asserções verificam o **estado** resultante (erro × sem dado × desatualizado), não só "não lançou exceção".
- [ ] Retry/backoff testados com relógio/espera mockados (sem `sleep` real).

## 13. Modo offline
- [ ] Aplicação inicia e funciona sem rede com dados locais; atualizações falham com mensagem clara.
- [ ] Startup não bloqueia esperando provedor externo.
- [ ] Ao voltar a rede, a próxima atualização ocorre normalmente (sem cooldown permanente).

## Exemplo de referência (Python, httpx)

```python
TIMEOUT = httpx.Timeout(connect=5.0, read=20.0, write=10.0, pool=5.0)

@retry(
    retry=retry_if_exception(eh_transitorio),          # timeout, conexão, 429, 502-504
    wait=wait_random_exponential(multiplier=1, max=30),
    stop=stop_after_attempt(4) | stop_after_delay(60),
    reraise=True,
)
def buscar(cliente: httpx.Client, url: str) -> dict:
    r = cliente.get(url, timeout=TIMEOUT)
    if r.status_code == 429:
        raise LimiteTaxa(retry_after=r.headers.get("Retry-After"))
    r.raise_for_status()
    return EsquemaResposta.model_validate(r.json()).model_dump()
```
Exemplo ilustrativo: a política real (tentativas, limites, fontes) é decisão do projeto.
