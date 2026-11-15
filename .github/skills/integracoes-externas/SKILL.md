---
name: integracoes-externas
description: 'Use ao revisar, testar ou validar integrações com APIs de terceiros, scraping e feeds de dados (cotações, índices, arquivos públicos) para garantir resiliência de nível produção — timeouts, retries com backoff e jitter, rate limit/429/Retry-After, circuit breaker, cache com TTL e indicador de dado desatualizado, fallback rotulado, parsing defensivo, distinção entre "sem dado", "erro" e "zero", TLS, proxy corporativo, jobs agendados e testes de contrato com fixtures gravadas — sem alterar regras de negócio. Modos review (padrão, somente leitura), test e fix. Palavras-gatilho: integração externa, API de terceiros, provedor de dados, scraping, feed, timeout, retry, backoff, jitter, rate limit, 429, Retry-After, circuit breaker, cache, TTL, dado desatualizado, fallback, parsing, layout mudou, TLS, proxy, certificado, User-Agent, APScheduler, job agendado, misfire, event loop, run_in_threadpool, respx, responses, vcr, modo offline.'
argument-hint: '[modo: review | test | fix] [caminho] [foco opcional]'
---

# Integrações Externas

Valida se as chamadas a **serviços de terceiros** (APIs REST, scraping de HTML, downloads de
CSV/ZIP, bibliotecas que encapsulam provedores de dados) são **resilientes, observáveis e honestas
com o usuário**: falham de forma controlada, não travam a aplicação, não sobrecarregam o provedor,
não transformam falha em dado falso e informam a **fonte e a data/hora** de cada dado exibido.
Aplica-se a integrações existentes e a toda nova integração ou alteração de provedor.

## Quando usar
- Auditar provedores de dados, clientes HTTP, scrapers e jobs de atualização antes de considerar a aplicação pronta.
- Investigar dados zerados, cotações antigas exibidas como atuais, travamentos durante atualização, erros intermitentes de rede/proxy/certificado.
- Validar uma **nova integração** ou mudança de fonte/endpoint/biblioteca.
- Criar testes de contrato com respostas gravadas (sucesso, timeout, 429, 5xx, payload malformado/vazio).

## Quando NÃO usar
- Escolher, contratar ou avaliar termos de uso/licenciamento de provedores (fora de escopo).
- Teste de carga ou de indisponibilidade contra o serviço real de terceiros (proibido).
- Pentest de APIs → `qa-appsec`. Desempenho geral da aplicação → `qa-application-auditor`.

---

## Princípios obrigatórios (inegociáveis)

1. **Não alterar regras de negócio, funcionalidades ou comportamento visível sem solicitação explícita do usuário** (inclui a escolha de fonte, a ordem de fallback e a frequência de atualização).
2. **Divergência encontrada vira achado com evidência e proposta** — nunca correção silenciosa.
3. **Modo padrão `review` é somente leitura.**
4. **`fix` só com pedido explícito e confirmação**; mudanças mínimas, com teste que **falha antes e passa depois**.
5. **Diferenciar análise teórica de teste efetivamente executado.**
6. **Nunca chamar serviços externos reais em testes automatizados** nem fazer carga, varredura ou repetição contra terceiros — usar mocks e fixtures gravadas.
7. **Nunca usar dados reais ou pessoais em fixtures**; fixtures gravadas devem ser revisadas e sanitizadas (sem tokens, cookies, IPs internos, nomes de usuário).
8. **Nunca desabilitar verificação TLS** (`verify=False`) nem sugerir isso como solução.
9. **Não expor segredos** (tokens, chaves, senhas de proxy) em relatórios, logs ou fixtures.
10. **Informar limitações** (sem rede, proxy indisponível, provedor sem sandbox, testes não executados).

---

## Modos de operação

Sem modo informado, use **`review`**. Pedido de "corrigir" sem modo → confirme antes de usar `fix`.

| Modo | Faz | Não faz |
|---|---|---|
| `review` (padrão) | Inventaria integrações, lê clientes/provedores/jobs, aplica o checklist, gera relatório com achados e plano de testes | Não modifica arquivos; não acessa a rede |
| `test` | Executa testes existentes; cria testes de contrato **em arquivos próprios** com mocks (`respx`, `responses`, `vcrpy`, `pytest-httpx`, MSW no front) cobrindo os cenários obrigatórios | Não altera código produtivo; não chama o provedor real |
| `fix` | Corrige achados comprovados (ex.: timeout ausente, `verify=False`, exceção engolida que vira zero) com diff mínimo e teste de regressão | Não troca provedor, não muda regra de cálculo nem frequência sem pedido |

---

## Fluxo de trabalho

1. **Inventário** — liste cada integração: provedor, finalidade, biblioteca/cliente, endpoint (sem segredos), formato (JSON/HTML/CSV/ZIP), autenticação, frequência, quem chama (request do usuário, job, startup), dado produzido e onde é persistido. Inclua bibliotecas que fazem rede implicitamente (ex.: wrappers de cotações).
2. **Mapa de chamadas** — para cada integração, identifique timeout, retry, cache, fallback, tratamento de erro, logging e se roda em thread, processo, job ou no event loop.
3. **Revisão pelo checklist** — aplique [references/checklist.md](references/checklist.md) por seção (rede, retry/rate limit, cache/frescor, fallback, parsing, TLS/proxy, jobs, concorrência, UX de status, testes, offline).
4. **Semântica do dado** — confirme que "sem dado", "erro" e "zero" são distinguíveis do provedor até a tela; confirme que dado antigo é exibido com data/hora e fonte.
5. **Plano de testes de contrato** — para cada integração: sucesso, timeout, erro de conexão, 429 com/sem `Retry-After`, 5xx, 4xx, payload malformado, payload vazio, mudança de layout/colunas, dado parcial.
6. **Execução** (`test`/`fix`) — rode somente com mocks/fixtures; registre comando, saída e resultado.
7. **Relatório** — preencha [templates/relatorio.md](templates/relatorio.md) com achados, evidências, propostas e limitações.

---

## Checklist

Checklist completo e critérios de aceite: [references/checklist.md](references/checklist.md).
Itens genéricos de resiliência já cobertos em
[qa-appsec/checklists/resilience-and-availability.md](../qa-appsec/checklists/resilience-and-availability.md)
e de rede/concorrência em
[qa-application-auditor/references/performance-checklist.md](../qa-application-auditor/references/performance-checklist.md) — não duplicar, referenciar.

Pontos que mais geram defeito em produção:
- Chamada sem **timeout explícito** (connect e read) ou biblioteca sem timeout configurável usada sem proteção.
- `except Exception: return {}` / `return 0` que faz falha virar "sem posição" ou "preço zero".
- Retry em operação não idempotente, retry sem backoff/jitter, ou retry ignorando 429/`Retry-After`.
- Cliente síncrono chamado dentro de rota `async` (bloqueia o event loop).
- Jobs agendados que se sobrepõem, rodam fora do horário útil/fuso correto ou martelam o provedor após falha.
- Dado de cache/fallback exibido sem fonte, data/hora ou aviso de desatualizado.

---

## Validação de novas funcionalidades

Toda nova integração (ou mudança de provedor, endpoint, biblioteca ou formato) só é aceita com:
- [ ] Registro no inventário de integrações (finalidade, formato, frequência, dado produzido).
- [ ] Timeout explícito, política de retry documentada (idempotência justificada) e respeito a 429/`Retry-After`.
- [ ] Cache/TTL definido e **fonte + data/hora** do dado persistidas e exibidas.
- [ ] Parsing com validação de esquema; mudança de layout gera erro/alerta rastreável, não zero silencioso.
- [ ] Estados "sem dado", "erro" e "zero" distintos no modelo, na API e na UI.
- [ ] Nenhum dado pessoal enviado ao provedor (só identificadores públicos — ver `privacidade-dados`).
- [ ] Se agendada: trava contra sobreposição, `misfire_grace_time`/`coalesce`, fuso explícito, backoff após falhas e status visível.
- [ ] Testes de contrato com fixtures gravadas cobrindo os cenários do passo 5; nenhum teste depende de rede.
- [ ] Comportamento offline definido e testado.

---

## Entregáveis

Gerados em `qa-report/integracoes-externas/` na raiz do projeto (não comitar sem pedido):
- `relatorio.md` — a partir de [templates/relatorio.md](templates/relatorio.md): inventário, matriz de resiliência por integração, achados `INT-XXX` (severidade **Crítica/Alta/Média/Baixa/Informativa**, evidência `arquivo:linha` ou saída de teste, proposta, status), testes executados/não executados e limitações.
- `evidencias/` — saídas de testes, fixtures criadas (sanitizadas), diffs (modo `fix`).

Severidade de referência: **Crítica** = dado falso exibido como verdadeiro (zero/antigo sem aviso) ou travamento da aplicação; **Alta** = sem timeout, `verify=False`, job sem trava, retry agressivo contra terceiro; **Média** = sem cache/fallback rotulado, parsing frágil sem detecção; **Baixa** = User-Agent ausente, logs pobres; **Informativa** = melhoria opcional.

---

## Integração com outras skills

| Skill | Relação |
|---|---|
| `prontidao-producao` | Orquestrador/gate: consome o relatório desta skill no parecer de prontidão |
| `qa-application-auditor` | Travamentos, consumo de rede/CPU, concorrência e carga **local** |
| `qa-appsec` | Segredos, TLS, SSRF, dependências e cadeia de suprimentos |
| `observabilidade-logs` | Logs, métricas de duração de chamadas externas, status de jobs e health check |
| `privacidade-dados` | Garantir que nenhum dado pessoal sai para provedores externos |
| `calculos-financeiros-fiscais` | Impacto de dado ausente/antigo/zerado em cálculos |
| `migracoes-banco` | Novas colunas de fonte/data/status do dado |
| `testes-e2e` | Fluxos de atualização e telas de status com backend mockado |
| `web-ux-acessibilidade` | Exibição de avisos de dado desatualizado e estados de erro |
| `ci-cd-release` | Garantir que a suíte de contrato roda sem rede no pipeline |
| `software-engineering-refactoring` | Extrair cliente HTTP comum/adaptadores quando a duplicação justificar |
| `documentacao-funcional` | Documentar fontes, frequência e significado dos avisos ao usuário |
