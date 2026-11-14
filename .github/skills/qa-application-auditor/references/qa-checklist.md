# Checklist de QA — descoberta, baseline, planejamento e estabilidade

Referência das Etapas 1, 2, 4 e 7 da skill `qa-application-auditor`.

---

## 1. Descoberta

Preencha `qa-report/02-inventario-da-aplicacao.md`. Para cada item, indique a **fonte** (arquivo e
linha) ou registre "não identificado".

- [ ] Linguagem principal e secundárias
- [ ] Frameworks (UI, web, ORM, testes)
- [ ] Tipo de aplicação: desktop, web, API, serviço, CLI, biblioteca ou híbrida
- [ ] Sistema operacional esperado (caminhos `C:\`, `ctypes.windll`, `win32*`, `.bat`/`.ps1`, `/etc`, `systemd`…)
- [ ] Gerenciador de dependências e versões fixadas (lockfile?)
- [ ] Comandos de instalação
- [ ] Comandos de build/empacotamento (PyInstaller `.spec`, `dotnet build`, `npm run build`…)
- [ ] Comandos de execução
- [ ] Estrutura de diretórios
- [ ] Pontos de entrada (`__main__`, `Main()`, `app.listen`, `webview.start`, `app.exec_()`…)
- [ ] Testes existentes e ferramentas configuradas (pytest, unittest, jest, vitest, xUnit, NUnit, JUnit…)
- [ ] Banco de dados (driver, string de conexão — **sem expor o valor**)
- [ ] APIs e integrações externas
- [ ] Filas, sockets e mensageria
- [ ] Configuração: `.ini`, JSON, YAML, XML, `.env`, variáveis de ambiente, registro do Windows
- [ ] Threads, processos, timers, jobs e tarefas assíncronas
- [ ] Rotinas de leitura e escrita de arquivos
- [ ] Rotinas potencialmente pesadas (parsing, loops sobre grandes volumes, relatórios, compressão)
- [ ] Recursos que exigem encerramento/descarte (arquivos, conexões, sockets, handles, processos filhos)
- [ ] Dependências nativas (DLLs, `ctypes`, drivers ODBC, binários externos)
- [ ] Scripts de CI/CD existentes
- [ ] Documentação e instruções do repositório (README, CONTRIBUTING, docs/, `.github/instructions`)

### Onde descobrir comandos (nunca assumir)
README/CONTRIBUTING · `package.json` (`scripts`) · `pyproject.toml`/`setup.cfg`/`tox.ini`/`noxfile.py`
· `Makefile` · `*.sln`/`*.csproj` · `pom.xml`/`build.gradle` · pipelines (`.github/workflows`,
`.gitlab-ci.yml`, `azure-pipelines.yml`, `Jenkinsfile`) · `Dockerfile`/`compose` · scripts `.bat`,
`.ps1`, `.sh` do próprio projeto · `.spec` do PyInstaller.

`detect_project.py` lista os candidatos com a fonte; **leia a fonte** antes de executar qualquer um.

### CLI e bibliotecas
- CLI: códigos de saída, mensagens de erro, `--help`, entrada por stdin, comportamento sem TTY,
  arquivos de entrada inexistentes/vazios/enormes, interrupção (`Ctrl+C`) e limpeza de temporários.
- Biblioteca: API pública (contratos, exceções documentadas), efeitos colaterais na importação,
  estado global, thread-safety declarada, compatibilidade de versões suportadas.

---

## 2. Inventário funcional e baseline

Preencha `qa-report/03-inventario-funcional.md`:

| Item | Conteúdo |
|---|---|
| Funcionalidades | Nome, descrição, arquivo/função de entrada |
| Fluxos principais | Passo a passo do caminho feliz |
| Fluxos alternativos | Cancelamento, erro, dados ausentes, repetição, reprocessamento |
| Regras de negócio | Regra, onde está implementada (arquivo:linha), exemplo de entrada → saída |
| Entradas aceitas | Formatos, limites, validações existentes |
| Saídas esperadas | Arquivos, telas, respostas, logs, códigos de saída |
| Integrações | Sistema, protocolo, timeout configurado, tratamento de falha |
| Configurações | Chave, valor padrão, efeito no comportamento |
| Tratamento de erros | Onde captura, o que faz (log, retry, mensagem, encerra) |
| Pontos críticos | Onde uma falha trava, perde dados ou afeta a máquina |

### Baseline (sem alterar a lógica produtiva)
1. **Testes existentes** — `run_tests.py` com o comando oficial; guarde o JSON/log.
2. **Testes de caracterização** (golden master) em arquivos próprios: capturam a saída atual para
   entradas conhecidas, **mesmo que pareça errada** — documente a dúvida, não "corrija" no teste.
3. **Fixtures** e entradas/saídas conhecidas (copie para `tests/qa_audit/fixtures/`, anonimizadas).
4. **Snapshots**, quando aplicável (HTML gerado, relatórios, JSON de resposta).
5. **Logs controlados**: rode com nível de log configurável, não altere o código para logar.
6. **Métricas**: `collect_metrics.py` em dois cenários no mínimo — **ocioso** (app aberto sem uso)
   e **operação típica**. Registre tempo de resposta, CPU, RSS, threads, handles, processos e disco.

Registre ambiente da baseline: SO, versão da linguagem, hardware (núcleos/RAM), commit/hash.

---

## 3. Planejamento dos testes

Use [../templates/test-plan.md](../templates/test-plan.md). IDs `TC-001`, `TC-002`… Prioridade:
**P1** fluxos principais e riscos Críticos/Altos · **P2** fluxos alternativos e riscos Médios ·
**P3** demais.

| # | Categoria | O que validar |
|---|---|---|
| 1 | Unitário | Funções/regras isoladas, limites e exceções |
| 2 | Integração | Módulo + banco/arquivo/API real local ou dublê |
| 3 | Funcional | Requisito ponta a ponta do ponto de vista do usuário |
| 4 | Regressivo | Comportamento da baseline continua idêntico |
| 5 | End-to-end | Fluxo completo com a aplicação em execução |
| 6 | Interface | Responsividade, bloqueio de UI, cliques repetidos, progresso, cancelamento |
| 7 | Configuração | Config ausente, inválida, valores-limite, variáveis de ambiente |
| 8 | Compatibilidade | Versões de SO/linguagem/navegador, DPI, caminhos com espaço/acentos, OneDrive |
| 9 | Carga | Volume esperado de uso (local) |
| 10 | Estresse | Acima do esperado até degradar; verificar recuperação |
| 11 | Duração (soak) | Uso contínuo por tempo longo; tendência de memória/handles/threads |
| 12 | Concorrência | Operações simultâneas, condições de corrida, deadlock |
| 13 | Recuperação | Reinício após falha, arquivos parciais, transações interrompidas |
| 14 | Resiliência | Dependência lenta, indisponível ou com resposta inválida |
| 15 | Segurança | Ver [security-checklist.md](security-checklist.md) |
| 16 | Limite | Valores mínimos/máximos, vazio, nulo, tamanho máximo |
| 17 | Entradas inválidas | Tipos errados, encoding, caracteres especiais, arquivos corrompidos |
| 18 | Arquivos grandes | Arquivo de centenas de MB/GB gerado localmente; uso de memória |
| 19 | Indisponibilidade de dependências | Banco/API/rede/disco/permissão ausentes |
| 20 | Destrutivo controlado | Somente em cópia isolada e descartável |

Campos obrigatórios por cenário: ID · Categoria · Funcionalidade · Objetivo · Risco coberto ·
Pré-condições · Dados de entrada · Passos · Resultado esperado · Evidência necessária ·
Prioridade · Possibilidade de automação · Status
(`planejado | executado | aprovado | reprovado | bloqueado | não executado`).

### Regras para testes novos
- Arquivos **próprios** (ex.: `tests/qa_audit/test_<area>.py`), usando o framework já existente.
- Dublês (mock/fake/servidor local) para qualquer serviço externo.
- Dados de teste **fictícios**; nunca credenciais reais.
- Timeouts em todo teste que possa travar (ex.: `pytest-timeout` se já instalado, ou timeout no
  `run_tests.py`).
- Arquivos grandes gerados em pasta temporária e removidos ao final do próprio teste.

---

## 4. Validação de estabilidade

| Cenário | Como executar com segurança |
|---|---|
| Inicialização/encerramento repetidos | Loop de N execuções via script de teste; conferir processos órfãos, locks e temporários restantes |
| Uso contínuo | `collect_metrics.py --duration` ≥ 30 min com operação repetitiva automatizada |
| Crescimento de memória | Tendência MB/min + R² do `collect_metrics.py`; repetir com carga constante para confirmar |
| CPU limitada | Container com `--cpus` (se Docker disponível) ou rodar junto de carga sintética local; caso contrário, NÃO EXECUTADO |
| Memória limitada | Container com `--memory`; sem container, NÃO EXECUTADO |
| Disco próximo do limite | Somente em volume isolado (VHD/pasta de container); nunca encher o disco do usuário |
| Arquivos grandes | Gerar arquivo sintético em pasta temporária; medir RSS e tempo |
| Muitos arquivos em diretório | Gerar milhares de arquivos vazios em pasta temporária; medir listagem/UI |
| Operações simultâneas | Threads/processos de teste disparando a mesma operação |
| Cancelamento no meio | Interromper durante o processamento; verificar estado consistente e recursos liberados |
| Dependência lenta | Servidor fake local com atraso; verificar timeout e UI responsiva |
| Dependência indisponível | Porta fechada/host inválido local; verificar mensagem, sem retry infinito |
| Resposta inválida | Fake retornando JSON malformado, vazio, enorme, status 500 |
| Perda/recuperação de conexão | Derrubar e subir o fake; verificar reconexão com backoff |
| Falha parcial | Um componente falha, os demais continuam ou falham de forma controlada |
| Encerramento inesperado | Matar o processo durante gravação; verificar integridade ao reabrir |
| Recuperação após reinício | Reabrir após o cenário anterior; dados e configurações íntegros |

### Ambiente isolado para cenários destrutivos
- Copie o projeto para uma pasta temporária **fora** do OneDrive/rede, ou use container/VM descartável.
- Use dados fictícios e configs apontando para dublês locais.
- Documente como o ambiente foi criado e destruído.
- Sem isolamento possível → marque **NÃO EXECUTADO** e registre o risco.
