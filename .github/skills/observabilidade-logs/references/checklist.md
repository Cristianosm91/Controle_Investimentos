# Checklist — Observabilidade e Logs

Cada item reprovado vira achado `OBS-XXX` com evidência (`arquivo:linha`, trecho **mascarado**,
saída de teste) e proposta. Marque cada item como **OK · Achado · N/A · Não verificado** (com motivo).

## 1. Configuração de logging
- [ ] Configuração centralizada e aplicada **uma vez** (sem `basicConfig` em vários módulos; sem handlers duplicados após reload).
- [ ] `logging.getLogger(__name__)` por módulo; sem uso do root logger direto nem `print` em código produtivo.
- [ ] Níveis coerentes: DEBUG (detalhe de dev, desligado por padrão), INFO (eventos de negócio/rotinas), WARNING (degradação recuperável), ERROR (falha de operação), CRITICAL (app inoperante).
- [ ] Nível configurável por configuração/variável de ambiente sem alterar código.
- [ ] Loggers ruidosos de terceiros (`urllib3`, `httpx`, `sqlalchemy.engine`, `apscheduler`) em nível adequado; SQL com parâmetros **nunca** em INFO.
- [ ] Formato com timestamp ISO com fuso, nível, logger, mensagem e correlation id; JSON opcional quando houver consumidor.
- [ ] `log.exception(...)` ou `exc_info=True` em erros inesperados (stack trace no log, não na resposta).
- [ ] Interpolação preguiçosa (`log.info("x=%s", x)`) em vez de f-string em caminhos quentes.

## 2. Correlation / request id
- [ ] Middleware gera/propaga `X-Request-ID` (aceita do cliente se válido; senão UUID) e devolve no header da resposta.
- [ ] Id disponível no log via `contextvars` + `logging.Filter`.
- [ ] Jobs agendados geram id próprio por execução.
- [ ] Mensagem de erro ao usuário inclui o id para suporte ("Código: abc123").

## 3. Dados sensíveis nos logs
- [ ] Nenhum segredo (token, senha, chave, cookie, header `Authorization`, string de conexão com senha).
- [ ] Nenhum dado pessoal (nome, CPF/documento, e-mail, telefone, endereço, dados de familiares).
- [ ] Nenhum valor patrimonial/financeiro individual (saldos, posições, valores de operação) — usar contagens, ids técnicos ou valores mascarados.
- [ ] Payloads de request/response e objetos ORM não são logados inteiros (`repr` de modelo pode conter tudo).
- [ ] URLs logadas sem query string sensível.
- [ ] Filtro de mascaramento como **rede de segurança** (regex de CPF, e-mail, tokens), não como única defesa.
- [ ] Mensagens de exceção de terceiros que ecoam entrada do usuário são tratadas antes de logar.
- [ ] Teste com `caplog` prova a ausência dos campos sensíveis.

## 4. Destino, rotação e retenção
- [ ] `RotatingFileHandler` (tamanho, ex.: 5–10 MB × 5 arquivos) ou `TimedRotatingFileHandler` com `backupCount`; nunca `FileHandler` ilimitado.
- [ ] `encoding="utf-8"` explícito.
- [ ] Diretório de logs em local de dados do usuário/app (ex.: `%LOCALAPPDATA%\<app>\logs`, `~/.local/state/<app>`), **fora** de pastas sincronizadas na nuvem e fora do repositório.
- [ ] Diretório criado no startup com tratamento de falha de permissão (app não quebra se não puder logar em arquivo; cai para stderr).
- [ ] Logs de dev/teste ignorados no `.gitignore`.
- [ ] Rotação segura com múltiplos processos (um processo escreve, ou `QueueHandler`/handler por processo).

## 5. Tratamento de erros (backend)
- [ ] Sem `except: pass`, `except Exception: pass`, `except ...: continue`/`return None` sem log nem sinalização.
- [ ] Exceções capturadas no nível em que podem ser tratadas; demais propagam até o handler global.
- [ ] Exceções de domínio (validação, não encontrado, conflito, ocupado) mapeadas para códigos HTTP coerentes.
- [ ] Handler global (`@app.exception_handler(Exception)`) devolve esquema único, ex.: `{"erro": {"codigo": "...", "mensagem": "...", "request_id": "..."}}`, sem stack trace nem SQL.
- [ ] `HTTPException` e `RequestValidationError` seguem o mesmo esquema (ou o esquema atual é documentado e consistente).
- [ ] Mensagem ao usuário em linguagem simples e acionável; detalhe técnico só no log.
- [ ] Rollback de transação em erro; sessão de banco sempre fechada.
- [ ] Threads/jobs têm try/except no nível mais alto com log (exceção em thread não morre em silêncio).

## 6. Health, readiness e versão
- [ ] `GET /health` (liveness) barato, sem tocar dependências.
- [ ] `GET /ready` (ou `/status`) verifica banco (consulta trivial), diretórios graváveis, scheduler ativo, versão do schema; devolve status por dependência sem dados sensíveis.
- [ ] Versão da aplicação (e commit/build, se houver) exposta e registrada no startup.
- [ ] Dependências externas **não** derrubam o readiness (reportadas como "degradado").

## 7. Startup e shutdown
- [ ] Log de startup: versão, ambiente, caminho do banco/logs (sem dados pessoais nem segredos), nível de log, jobs registrados.
- [ ] Log de shutdown: encerramento do scheduler, fechamento de conexões/clientes.
- [ ] Falha de startup (porta ocupada, banco inacessível, migração falhou) gera mensagem clara e código de saída ≠ 0.

## 8. Jobs e rotinas
- [ ] Cada execução registra início, fim, duração, resultado e resumo (contagens, não dados).
- [ ] Status persistido (banco/arquivo) sobrevive a reinício; UI mostra última execução, sucesso/erro e próxima execução.
- [ ] Falhas consecutivas destacadas (contador) e visíveis ao usuário.

## 9. Métricas leves
- [ ] Duração de jobs, chamadas externas e requisições (middleware com `time.perf_counter`), com WARNING acima de limiar.
- [ ] Consultas lentas detectáveis (evento `before/after_cursor_execute` com limiar, sem logar parâmetros).
- [ ] Contadores simples (requisições, erros por rota, falhas por integração) em memória/endpoint local; Prometheus/OpenTelemetry apenas opcional.

## 10. Front-end
- [ ] Error boundary (React) na raiz e nas áreas críticas, com mensagem amigável e opção de recarregar.
- [ ] Erros de rede/HTTP tratados centralmente (interceptor/wrapper de `fetch`) mostrando a mensagem do esquema de erro e o request id.
- [ ] Sem `console.log` de payloads com dados pessoais/financeiros em build de produção.
- [ ] Promises rejeitadas não tratadas capturadas (`window.addEventListener("unhandledrejection", ...)`).
- [ ] Relato de erro ao backend (se existir) é local e sem dados pessoais; envio externo só opt-in.

## 11. Pacote de diagnóstico
- [ ] Ação/comando gera ZIP com: versão, SO, versão de runtime, configuração **sem segredos**, status de jobs, health, últimos N logs **mascarados**, contagens de tabelas (não conteúdo).
- [ ] Nunca inclui banco de dados, planilhas, backups, `.env` nem dados pessoais.
- [ ] Usuário vê o conteúdo/lista antes de compartilhar; arquivo gerado em local informado.
- [ ] Teste automatizado verifica ausência de campos sensíveis no pacote.

## 12. Runbook
- [ ] Documento com falhas comuns: provedor indisponível, proxy/certificado, banco bloqueado/corrompido, disco cheio, porta ocupada, migração falhou, job travado.
- [ ] Para cada uma: sintoma, onde olhar (log/tela/endpoint), causa provável, ação, quando escalar.
- [ ] Indica onde ficam logs, banco e backups e como gerar o pacote de diagnóstico.

## Exemplo de referência (Python)

```python
request_id: ContextVar[str] = ContextVar("request_id", default="-")

class ContextoFilter(logging.Filter):
    def filter(self, record):
        record.request_id = request_id.get()
        return True

handler = RotatingFileHandler(dir_logs / "app.log", maxBytes=5_000_000, backupCount=5, encoding="utf-8")
handler.addFilter(ContextoFilter())
handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s [%(request_id)s] %(message)s"))

@app.exception_handler(Exception)
async def erro_inesperado(request, exc):
    log.exception("Erro inesperado em %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"erro": {"codigo": "erro_interno",
        "mensagem": "Ocorreu um erro inesperado.", "request_id": request_id.get()}})
```
Exemplo ilustrativo: nomes de campos e formato do esquema são decisão do projeto.
