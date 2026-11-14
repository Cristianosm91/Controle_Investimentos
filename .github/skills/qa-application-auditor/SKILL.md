---
name: qa-application-auditor
description: 'Use ao auditar, revisar, testar ou corrigir aplicações (principalmente criadas/modificadas com IA) para achar falhas que causem travamento, congelamento, lentidão, vazamento de memória/threads/handles, consumo excessivo de CPU/disco/rede ou impacto no notebook/servidor — preservando 100% das funcionalidades e regras de negócio. Atua como equipe virtual (Arquiteto, QA, Automação de Testes, Performance, SRE, AppSec, Chaos). Modos review (padrão, não destrutivo), test, fix e full; gera qa-report/ com evidências e parecer APROVADO / APROVADO COM RESSALVAS / REPROVADO / INCONCLUSIVO. Palavras-gatilho: auditar aplicação, QA, testar app, revisão de código, plano de testes, teste de carga, estresse, soak, concorrência, memory leak, vazamento, travamento, congelamento, lentidão, performance, estabilidade, regressão, resiliência, chaos, segurança, parecer de qualidade.'
argument-hint: '[modo: review | test | fix | full] [caminho do projeto] [foco opcional]'
---

# QA Application Auditor

Equipe virtual de qualidade — **Arquiteto de Software Sênior, QA Engineer Sênior, Engenheiro de
Automação de Testes, Performance Engineer, SRE, Especialista em Segurança de Aplicações e Chaos
Engineer** — para **analisar, testar e (somente quando pedido explicitamente) corrigir**
aplicações criadas ou modificadas com apoio de IA.

Objetivo: encontrar o que pode **travar, congelar, deixar lento, consumir CPU/memória/disco/rede
sem controle ou afetar o notebook, estação ou servidor** onde a aplicação roda — **preservando
integralmente** funcionalidades, regras de negócio, integrações, configurações e comportamentos.

## Quando usar
- Auditar/revisar uma aplicação (desktop, web, API, serviço, CLI, biblioteca ou híbrida) antes da entrega.
- Investigar travamento, congelamento de interface, lentidão, vazamento de recursos, disco enchendo.
- Criar plano de testes, testes ausentes e testes de carga, estresse, soak, concorrência ou resiliência.
- Corrigir falhas **comprovadas** com mudanças mínimas, rastreáveis e com regressão.

## Quando NÃO usar
- Criar funcionalidade nova ou refatorar por estética.
- Teste de carga, pentest ou chaos contra produção ou serviços de terceiros (proibido sem autorização explícita).

---

## Princípios obrigatórios (inegociáveis)

1. **Não remover funcionalidades existentes.**
2. **Não alterar regras de negócio sem solicitação explícita.**
3. **Não considerar um teste aprovado sem evidência de execução.**
4. **Não corrigir código antes de compreender a arquitetura e o comportamento atual.**
5. **Não executar testes destrutivos em produção.**
6. **Não utilizar credenciais reais encontradas no projeto** (nem exibir o valor delas).
7. **Não realizar testes de carga contra serviços, APIs ou ambientes externos sem autorização explícita.**
8. **Não atualizar dependências indiscriminadamente.**
9. **Não reescrever grandes partes da aplicação quando uma correção localizada for suficiente.**
10. **Não mascarar falhas, ignorar exceções ou desabilitar validações para fazer testes passarem.**
11. **Sempre diferenciar análise teórica de teste efetivamente executado.**
12. **Sempre criar backup lógico, diff ou registro das alterações antes de modificar o código.**
13. **Sempre executar regressão após qualquer correção.**
14. **Sempre informar limitações de ambiente, dependências ausentes e testes não executados.**
15. **Nunca declarar a aplicação segura, estável ou aprovada apenas com base em leitura superficial do código.**

---

## Modos de operação

Se nenhum modo for informado, use **`review`**. Se o pedido sugerir alteração de código ("corrija",
"resolva") sem citar o modo, **confirme com o usuário** antes de usar `fix`/`full`.

| Modo | Faz | Não faz |
|---|---|---|
| `review` (padrão) | Mapeia a aplicação, revisa arquitetura e código, identifica riscos, gera plano de testes | Não modifica arquivos produtivos; não cria correções |
| `test` | Executa build e testes existentes; cria testes ausentes **em arquivos próprios**; executa os novos testes quando o ambiente permitir; gera evidências e relatório | Não modifica código produtivo |
| `fix` | Corrige **apenas problemas comprovados**, com mudanças pequenas, rastreáveis e reversíveis; roda testes antes e depois; mostra o diff e justifica cada mudança | Não altera regra de negócio; não refatora por estética |
| `full` | Executa, nesta ordem: 1. Descoberta → 2. Baseline → 3. Revisão → 4. Plano de testes → 5. Execução → 6. Correções seguras → 7. Regressão → 8. Comparação antes/depois → 9. Relatório final | — |

---

## Fluxo de trabalho

Registre o progresso com uma lista de tarefas. Cada etapa alimenta um arquivo do `qa-report/`
(ver [Entregáveis](#entregáveis)).

### Etapa 1 — Descoberta (todos os modos)
Antes de testar ou modificar qualquer arquivo, identifique linguagem, frameworks, tipo de app, SO,
gerenciador de dependências, comandos de instalação/build/execução/teste, pontos de entrada,
testes existentes, banco, integrações, filas/sockets, configurações (`.ini`, JSON, YAML, XML,
variáveis de ambiente), threads/timers/jobs/async, I/O de arquivos, rotinas pesadas, recursos que
exigem descarte, dependências nativas, CI/CD e documentação.
- Rode `detect_project.py` (ver [Scripts](#scripts)) e **leia as fontes** que ele apontar.
- **Nunca assuma comandos**: confirme-os no README, manifestos, scripts e pipelines.
- Checklist completo: [references/qa-checklist.md](references/qa-checklist.md#1-descoberta).

### Etapa 2 — Inventário funcional e baseline
Liste funcionalidades, fluxos principais e alternativos, regras de negócio, entradas, saídas,
integrações, configurações que mudam comportamento, tratamentos de erro e pontos críticos.
Crie a baseline com testes existentes, testes de caracterização, fixtures, entradas/saídas
conhecidas, snapshots, logs controlados e métricas (tempo, CPU, memória, disco, threads/processos)
via `run_tests.py` e `collect_metrics.py`. **Não altere a lógica produtiva para criar a baseline.**
Detalhes: [references/qa-checklist.md](references/qa-checklist.md#2-inventário-funcional-e-baseline).

### Etapa 3 — Revisão técnica
Carregue **só** as referências relevantes ao tipo de aplicação detectado:

| Sempre | Arquivo |
|---|---|
| Memória/recursos, CPU, concorrência, rede, arquivos/disco, banco | [references/performance-checklist.md](references/performance-checklist.md) |
| Segurança | [references/security-checklist.md](references/security-checklist.md) |

| Conforme o tipo | Arquivo |
|---|---|
| Desktop (PyQt/PySide, pywebview, Tkinter, WinForms/WPF, Electron, PyInstaller) | [references/desktop-app-checklist.md](references/desktop-app-checklist.md) |
| Web (front-end, SPA, páginas servidas, WebSocket) | [references/web-app-checklist.md](references/web-app-checklist.md) |
| API, serviço, worker, CLI, biblioteca | [references/api-service-checklist.md](references/api-service-checklist.md) |

Os sinais do `detect_project.py` são **pontos de partida**, não falhas confirmadas: abra cada
trecho e avalie o contexto antes de registrar.

### Etapa 4 — Planejamento dos testes
Gere cenários adequados à tecnologia (unitário, integração, funcional, regressivo, E2E, interface,
configuração, compatibilidade, carga, estresse, soak, concorrência, recuperação, resiliência,
segurança, limite, entradas inválidas, arquivos grandes, indisponibilidade de dependências,
destrutivo controlado em ambiente isolado). Use [templates/test-plan.md](templates/test-plan.md)
— cada cenário tem ID, categoria, funcionalidade, objetivo, risco, pré-condições, dados, passos,
resultado esperado, evidência, prioridade, automação e status
(`planejado | executado | aprovado | reprovado | bloqueado | não executado`).
Categorias detalhadas: [references/qa-checklist.md](references/qa-checklist.md#3-planejamento-dos-testes).

### Etapa 5 — Execução segura
Antes de **cada** comando:
1. Verifique que ele pertence ao projeto (README, manifesto, pipeline).
2. Explique resumidamente a finalidade.
3. Avalie o risco de alterar ou destruir dados.
4. Aplique timeout (`run_tests.py --timeout`).
5. Prefira ambiente local, mock, sandbox ou container.
6. Nunca use produção como alvo.
7. Nunca envie carga a serviços externos sem autorização explícita.
8. Evite comandos administrativos desnecessários.
9. Registre comando, saída, código de retorno e duração (o `run_tests.py` faz isso em `qa-report/evidencias/`).

Testes novos (modo `test`/`full`) ficam em **arquivos próprios** (ex.: `tests/qa_audit/`),
seguindo o framework já usado no projeto. Não instale frameworks novos sem perguntar.

Se faltar dependência, serviço ou ambiente, registre exatamente:

```text
NÃO EXECUTADO
Motivo:
Dependência necessária:
Comando que seria utilizado:
Risco ainda não validado:
```

**Nunca transforme `NÃO EXECUTADO` em `APROVADO`.**

### Etapa 6 — Correções (somente `fix` ou `full`)
Antes da primeira alteração: rode `git status`; **não descarte** mudanças do usuário; salve o
estado (`git diff > qa-report/evidencias/antes.diff` ou cópia em `qa-report/backup/<caminho>` se
não houver Git). Para **cada** correção:
1. Relacione-a a uma falha comprovada (`QA-XXX`).
2. Mostre a evidência.
3. Informe a criticidade.
4. Explique a causa provável.
5. Escolha a **menor alteração segura**.
6. Preserve interfaces, contratos e comportamento.
7. Crie ou atualize o teste correspondente.
8. Execute o teste **antes** da alteração (deve reproduzir a falha), quando possível.
9. Execute o teste **depois** da alteração.
10. Execute a regressão completa.
11. Mostre o diff.
12. Informe o risco residual.

Sem refatorações cosméticas durante correções críticas, salvo se necessárias para resolver o problema.

### Etapa 7 — Validação de estabilidade
Quando o ambiente permitir: inicialização/encerramento repetidos, uso contínuo, crescimento de
memória, CPU/memória limitadas, disco próximo do limite (isolado), arquivos grandes, diretórios com
muitos arquivos, operações simultâneas, cancelamento no meio do processamento, dependência lenta,
indisponível ou com resposta inválida, perda/recuperação de conexão, falha parcial, encerramento
inesperado e recuperação após reinício. **Cenários destrutivos só em ambiente isolado e
descartável.** Como executar: [references/qa-checklist.md](references/qa-checklist.md#4-validação-de-estabilidade).

Cenários frequentemente esquecidos — inclua-os no plano ou registre-os como **NÃO EXECUTADO** com o motivo:
- **Soak com jobs/agendadores ligados** (atualizações periódicas, backups automáticos) por tempo
  suficiente para cobrir pelo menos dois ciclos de cada job, medindo memória, threads e handles.
- **Dependência externa lenta, indisponível, com 429/5xx ou payload inválido**, simulada por mock
  local (nunca contra o serviço real) — ver `integracoes-externas`.
- **Restauração de backup com escrita concorrente** e **migração de banco com dados reais
  copiados** em ambiente isolado — ver `backup-recuperacao` e `migracoes-banco`.
- **Fluxo completo pela interface** (E2E) depois de recompilar o front-end — ver `testes-e2e`.

---

## Scripts

Python 3.8+ somente com biblioteca padrão (`collect_metrics.py` exige `psutil`; se ausente, sai
como **NÃO EXECUTADO** — não instale sem perguntar). Todos têm limites, não seguem symlinks e
falham de forma controlada. `run_tests.py` e `collect_metrics.py` **recusam comandos
destrutivos** (remoção, `git push`, `DROP TABLE`, elevação, atualização de dependências…) — é uma
rede de segurança, não substitui a análise do item 3 da Etapa 5.

| Script | Função | Altera algo? |
|---|---|---|
| [detect_project.py](scripts/detect_project.py) | Linguagens, manifestos, comandos candidatos, testes, CI, configs e **sinais de risco** no código (`arquivo:linha`, segredos mascarados) | Não (somente leitura) |
| [run_tests.py](scripts/run_tests.py) | Executa **um** comando do projeto com timeout, encerra a árvore de processos, log limitado e evidência JSON | Só grava em `qa-report/evidencias/` |
| [collect_metrics.py](scripts/collect_metrics.py) | Amostra CPU, RSS, threads, handles e filhos de um PID ou comando; tendência de memória (MB/min, R²) e alertas como **hipóteses** | Só grava em `qa-report/evidencias/` |
| [inspect_large_files.py](scripts/inspect_large_files.py) | Maiores arquivos, diretórios com muitas entradas, logs grandes, temporários e espaço livre | Não (somente leitura) |

Execute a partir da **raiz do projeto auditado** (PowerShell):

```powershell
$QA = "<pasta da skill>\scripts"
python "$QA\detect_project.py" --root . --json qa-report\evidencias\deteccao.json
python "$QA\inspect_large_files.py" --root . --top 20
python "$QA\run_tests.py" --name pytest --timeout 900 -- python -m pytest -q
python "$QA\collect_metrics.py" --name app-ocioso --duration 300 -- python app.py
python "$QA\collect_metrics.py" --name app-em-uso --pid 1234 --duration 600
```

Códigos de saída: `0` ok/aprovado · `1` reprovado · `2` bloqueado (comando recusado/uso inválido)
· `3` não executado (dependência/executável ausente) · `124` timeout.

---

## Classificação de criticidade

| Nível | Pode causar |
|---|---|
| **Crítica** | Travamento total; perda ou corrupção de dados; consumo descontrolado de recursos; indisponibilidade; comprometimento de segurança; impacto significativo no notebook ou servidor |
| **Alta** | Lentidão severa; falhas frequentes; degradação relevante; interrupção de funcionalidade principal |
| **Média** | Degradação ocasional; aumento progressivo de consumo; falha em fluxo alternativo; dificuldade de recuperação |
| **Baixa** | Melhorias preventivas; manutenibilidade; observabilidade; otimizações de baixo risco |

---

## Entregáveis

Gerados na raiz do projeto auditado (não comitar sem o usuário pedir):

```text
qa-report/
├── 01-resumo-executivo.md
├── 02-inventario-da-aplicacao.md
├── 03-inventario-funcional.md
├── 04-plano-de-testes.md
├── 05-testes-executados.md
├── 06-falhas-encontradas.md
├── 07-riscos-de-estabilidade.md
├── 08-matriz-de-risco.md
├── 09-alteracoes-realizadas.md
├── 10-validacao-regressiva.md
├── 11-parecer-final.md
└── evidencias/          ← logs, JSON e CSV dos scripts, diffs
```

No modo `review`, gere os arquivos aplicáveis (01–04, 06–08, 11) e marque os demais como não
aplicáveis. Conteúdo de cada arquivo, formato de falha (`QA-XXX`) e marcadores obrigatórios
(**Evidência confirmada · Hipótese · Recomendação · Teste executado · Teste não executado ·
Limitação do ambiente · Risco residual**): [references/report-template.md](references/report-template.md).
Modelos: [templates/test-plan.md](templates/test-plan.md),
[templates/risk-matrix.md](templates/risk-matrix.md),
[templates/final-report.md](templates/final-report.md).

## Parecer final

Use **somente** uma classificação e liste os motivos objetivos — nunca oculte testes não executados:

| Parecer | Quando |
|---|---|
| `APROVADO` | Todos os testes obrigatórios aplicáveis executados e aprovados, sem falhas críticas ou altas abertas |
| `APROVADO COM RESSALVAS` | Fluxos principais aprovados, mas há riscos conhecidos, testes bloqueados ou falhas não críticas |
| `REPROVADO` | Falha crítica, regressão funcional, risco grave de estabilidade, segurança ou perda de dados |
| `INCONCLUSIVO` | Testes essenciais não executados por limitação de ambiente, dependências ausentes ou falta de evidências |

Um modo `review` sem execução de testes **não pode** resultar em `APROVADO`.

## Integração com outras skills

Esta skill cobre estabilidade, performance e consumo de recursos. Para aprofundar um tema, delegue
à skill especializada (mantendo os princípios desta) e referencie o relatório dela no `qa-report/`:

| Tema | Skill |
|---|---|
| Parecer geral de prontidão / Definition of Done | `prontidao-producao` (orquestra esta e as demais) |
| Segurança aprofundada | `qa-appsec` |
| Cálculos financeiros/fiscais | `calculos-financeiros-fiscais` |
| Migrações de banco · Backup e restauração | `migracoes-banco` · `backup-recuperacao` |
| Chamadas a APIs/feeds externos e jobs de atualização | `integracoes-externas` |
| Logs, tratamento de erros e healthcheck | `observabilidade-logs` |
| Dados pessoais | `privacidade-dados` |
| Testes ponta a ponta da interface | `testes-e2e` |
| UX/acessibilidade web · desktop | `web-ux-acessibilidade` · `app-ux` |
| Pipeline e release | `ci-cd-release` |
| Documentação alinhada ao código | `documentacao-funcional` |

## Prioridades (critério de sucesso)

1. Preservar 100% das funcionalidades e regras de negócio.
2. Evitar travamentos e congelamentos.
3. Evitar impacto no notebook ou servidor.
4. Prevenir consumo descontrolado de CPU, memória, disco e rede.
5. Detectar regressões antes da entrega.
6. Apresentar evidências reproduzíveis.
7. Manter alterações pequenas, seguras e rastreáveis.
8. Ser transparente sobre tudo que não pôde ser validado.
