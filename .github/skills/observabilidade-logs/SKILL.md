---
name: observabilidade-logs
description: 'Use ao revisar, testar ou validar logs, tratamento de erros e observabilidade de aplicações (API, desktop/local, jobs, front-end) para nível produção — logging estruturado por módulo com níveis e correlation id, mascaramento de dados pessoais/segredos/valores financeiros, rotação e limite de tamanho, local dos logs fora de pastas sincronizadas, exceções engolidas, handler global com esquema de erro consistente, health/readiness com versão e dependências, status de jobs persistido, métricas leves, pacote de diagnóstico sem dados pessoais, error boundary no front e runbook — sem alterar regras de negócio. Modos review (padrão, somente leitura), test e fix. Palavras-gatilho: log, logging, observabilidade, correlation id, request id, RotatingFileHandler, rotação de log, except pass, exceção engolida, tratamento de erro, mensagem de erro, exception handler, health check, readiness, status de job, métricas, diagnóstico, pacote de diagnóstico, error boundary, runbook, troubleshooting.'
argument-hint: '[modo: review | test | fix] [caminho] [foco opcional]'
---

# Observabilidade e Logs

Valida se a aplicação **registra o suficiente para diagnosticar falhas sem expor dados**, trata
erros de forma consistente (usuário recebe mensagem compreensível; detalhe técnico vai para o log),
expõe sua **saúde e o status das rotinas** e permite gerar um **pacote de diagnóstico** seguro para
suporte. Contexto prioritário: aplicação local/desktop ou servidor pequeno — **nenhum SaaS externo
de observabilidade é obrigatório**; integrações desse tipo são opcionais e opt-in.

## Quando usar
- Auditar logging, tratamento de erros, health check e status de jobs antes de considerar a aplicação pronta.
- Investigar "erro sem log", log gigante, log com dado sensível, falha silenciosa, mensagem técnica exibida ao usuário.
- Validar que uma **nova funcionalidade** é observável (logs, erros, métricas, status).
- Criar runbook de falhas comuns e pacote de diagnóstico.

## Quando NÃO usar
- Implantar stack de monitoramento corporativa/SaaS (fora de escopo; no máximo recomendação opcional).
- Auditoria de segurança de logs (integridade, injeção, retenção legal) → `qa-appsec` ([logging-and-monitoring](../qa-appsec/checklists/logging-and-monitoring.md)).
- Performance/profiling detalhado → `qa-application-auditor`.

---

## Princípios obrigatórios (inegociáveis)

1. **Não alterar regras de negócio, funcionalidades ou comportamento visível sem solicitação explícita do usuário** (inclui textos de mensagens exibidas e códigos HTTP consumidos pelo front).
2. **Divergência encontrada vira achado com evidência e proposta** — nunca correção silenciosa.
3. **Modo padrão `review` é somente leitura.**
4. **`fix` só com pedido explícito e confirmação**; mudanças mínimas, com teste que **falha antes e passa depois**.
5. **Diferenciar análise teórica de teste efetivamente executado.**
6. **Nunca chamar serviços externos reais em testes automatizados** nem enviar logs/eventos a terceiros — usar mocks e fixtures.
7. **Nunca usar dados reais ou pessoais em fixtures**, nem copiar trechos de logs reais com dados pessoais para o relatório (mascarar).
8. **Não mascarar falhas**: transformar exceção em log silencioso para "passar" é proibido.
9. **Informar limitações** (logs reais indisponíveis, ambiente sem execução, testes não executados).

---

## Modos de operação

Sem modo informado, use **`review`**. Pedido de "corrigir" sem modo → confirme antes de usar `fix`.

| Modo | Faz | Não faz |
|---|---|---|
| `review` (padrão) | Mapeia configuração de logging, handlers de erro, health, jobs e front; aplica o checklist; gera relatório | Não modifica arquivos |
| `test` | Executa testes existentes; cria testes **em arquivos próprios** (`caplog`, `TestClient`, testes de error boundary) para mascaramento, esquema de erro, health e status de jobs | Não altera código produtivo |
| `fix` | Corrige achados comprovados (ex.: `except: pass`, log com CPF, falta de rotação, stack trace na resposta) com diff mínimo e regressão | Não muda textos/fluxos visíveis nem códigos de resposta sem pedido |

---

## Fluxo de trabalho

1. **Mapa de logging** — onde é configurado (uma única vez?), níveis, formato, handlers, destino dos arquivos, rotação, loggers de terceiros (`uvicorn`, `sqlalchemy`, `httpx`, `apscheduler`).
2. **Varredura de erros** — busque `except:`/`except Exception` com `pass`/`continue`/`return` sem log, `print(` em código produtivo, `log.error` sem `exc_info`, `console.log` de payloads, `catch {}` vazio no front.
3. **Dados nos logs** — procure interpolação de objetos inteiros, payloads, headers, URLs com query, nomes/CPF/valores; confira filtros de mascaramento.
4. **Contrato de erro da API** — handlers globais, esquema de erro único, ausência de stack trace na resposta, mapeamento de exceções de domínio.
5. **Saúde e status** — health/readiness, versão exposta, status de jobs persistido e visível, logs de startup/shutdown.
6. **Front-end** — error boundary, tratamento de falha de rede, mensagem ao usuário, ausência de dados sensíveis no console.
7. **Suporte** — métricas leves, pacote de diagnóstico, runbook.
8. **Testes** (`test`/`fix`) e **relatório** em [templates/relatorio.md](templates/relatorio.md).

---

## Checklist

Checklist completo e critérios de aceite: [references/checklist.md](references/checklist.md).
Não duplicar: segurança de logs em
[qa-appsec/checklists/logging-and-monitoring.md](../qa-appsec/checklists/logging-and-monitoring.md);
vazamento por logs/erros em
[qa-appsec/checklists/data-leakage-prevention.md](../qa-appsec/checklists/data-leakage-prevention.md);
crescimento de disco por logs em
[qa-application-auditor/references/performance-checklist.md](../qa-application-auditor/references/performance-checklist.md).

Achados mais comuns:
- `except Exception: pass` ou retorno vazio sem log — falha invisível.
- Log com dado pessoal, token, URL com query ou valor patrimonial.
- `FileHandler` sem rotação; log dentro de pasta sincronizada (OneDrive/Dropbox) ou do repositório.
- Resposta 500 com stack trace ou formatos de erro diferentes por rota.
- Job falha e a UI continua mostrando "atualizado".

---

## Validação de novas funcionalidades

Toda funcionalidade nova ou alterada só é aceita com:
- [ ] Logger do módulo (`logging.getLogger(__name__)`), níveis adequados e eventos-chave (início/fim/falha) com contexto mínimo e sem dados pessoais.
- [ ] Nenhuma exceção engolida; erros esperados mapeados para o esquema de erro da API com mensagem ao usuário.
- [ ] Se tiver rotina/job: status persistido (início, fim, duração, sucesso, mensagem) e visível na UI.
- [ ] Se tiver dependência nova (arquivo, serviço, diretório): refletida no readiness.
- [ ] Duração registrada para operações potencialmente lentas.
- [ ] Teste com `caplog` garantindo que dados sensíveis não aparecem no log e que a falha é registrada.
- [ ] Runbook atualizado se a funcionalidade introduz um novo modo de falha.

---

## Entregáveis

Gerados em `qa-report/observabilidade-logs/` na raiz do projeto (não comitar sem pedido):
- `relatorio.md` — a partir de [templates/relatorio.md](templates/relatorio.md): mapa de logging, inventário de pontos de erro, achados `OBS-XXX` (severidade **Crítica/Alta/Média/Baixa/Informativa**, evidência, proposta, status), testes e limitações.
- `evidencias/` — saídas de testes, trechos de log **mascarados**, diffs (modo `fix`).

Severidade de referência: **Crítica** = segredo/dado pessoal em log ou resposta, falha de dados silenciosa; **Alta** = log sem rotação/limite, stack trace ao usuário, job falhando sem status; **Média** = esquema de erro inconsistente, sem health/readiness, sem correlation id; **Baixa** = níveis inadequados, `print`; **Informativa** = métricas/diagnóstico opcionais.

---

## Integração com outras skills

| Skill | Relação |
|---|---|
| `prontidao-producao` | Orquestrador/gate: consome o relatório desta skill no parecer de prontidão |
| `qa-application-auditor` | Disco/CPU consumidos por logging, desempenho e estabilidade |
| `qa-appsec` | Integridade, retenção e segurança dos logs; vazamento por erros |
| `privacidade-dados` | Lista de campos pessoais a mascarar; pacote de diagnóstico sem dados pessoais |
| `integracoes-externas` | Métricas e logs de chamadas externas e status de atualizações |
| `backup-recuperacao` | Logs e status das rotinas de backup/restauração |
| `migracoes-banco` | Logs de startup com versão de schema e falhas de migração |
| `ci-cd-release` | Versão/commit expostos no health e nos logs de startup |
| `testes-e2e` | Fluxos de erro e error boundary validados ponta a ponta |
| `web-ux-acessibilidade` | Apresentação acessível das mensagens de erro |
| `documentacao-funcional` | Runbook e guia de suporte |
| `software-engineering-refactoring` | Centralizar configuração de logging/handlers quando houver duplicação |
