# Checklist — APIs, serviços, workers e CLIs de longa duração

Carregue quando houver API HTTP/gRPC, serviço Windows/daemon, worker de fila, job agendado ou
processo de longa duração. Para CLIs e bibliotecas, ver também
[qa-checklist.md](qa-checklist.md#cli-e-bibliotecas).

## Limites e proteção de recursos

| Verificar | Onde procurar | Como comprovar |
|---|---|---|
| Timeouts de entrada | Servidor sem timeout de leitura/corpo/keep-alive | Cliente local que envia devagar (slowloris controlado, local) |
| Timeouts de saída | Chamadas a banco/HTTP/fila sem timeout | Dublê lento |
| Tamanho máximo de requisição | Upload/corpo sem limite | Corpo grande gerado localmente |
| Paginação | Endpoints de listagem sem `limit`/página máxima | Base de teste volumosa |
| Limite de concorrência | Workers/threads/conexões sem teto; pool de conexões sem limite | Teste de carga local |
| Rate limiting (quando aplicável) | Endpoints caros/autenticação sem limite | Teste de carga local |
| Filas internas | Fila em memória sem `maxsize`; sem back-pressure | Produtor > consumidor |
| Pools | Pool de conexão sem `max_size`, sem devolução em exceção | Exceção no meio da requisição; contar conexões |

## Confiabilidade

| Verificar | O que esperar |
|---|---|
| Retry | Limitado, com backoff exponencial e jitter; só para operações idempotentes |
| Circuit breaker (quando aplicável) | Dependência falhando repetidamente deixa de ser chamada por um período |
| Idempotência | Reprocessar a mesma mensagem/requisição não duplica efeitos |
| Transações | Curtas; rollback em erro; sem I/O externo dentro da transação |
| Graceful shutdown | SIGTERM/Ctrl+C/parada do serviço: para de aceitar, conclui ou devolve trabalho, fecha conexões |
| Health/readiness | Endpoint leve que não derruba dependências; reflete estado real |
| Startup | Dependência indisponível no start → falha clara ou espera limitada, não trava eterno |
| Jobs agendados | Sem sobreposição de execuções (lock/flag); duração máxima; registro de falhas |
| Erros | Exceção não derruba o processo inteiro; respostas de erro sem stack trace/segredos |

## Logs e observabilidade

- Rotação e retenção configuradas (tamanho/tempo).
- Sem payload completo, senhas, tokens ou dados de cartão em log.
- Correlação (ID de requisição) e níveis adequados; log em loop de erro não inunda o disco.

## Segurança (API)

- Autenticação e autorização em **todos** os endpoints que exigem; checagem de propriedade do
  recurso (IDOR).
- Validação de entrada por schema; rejeição de campos inesperados quando aplicável.
- CORS restrito; sem `*` com credenciais.
- Mensagens de erro genéricas para o cliente; detalhes só no log.
- Ver também [security-checklist.md](security-checklist.md).

## Testes de carga — regras

- **Somente contra instância local** (localhost/container) com dependências substituídas por dublês.
- Nunca contra homologação/produção/serviços de terceiros sem autorização **explícita e escrita**.
- Use ferramenta já disponível no projeto ou na máquina (`locust`, `k6`, `autocannon`,
  `bombardier`, `wrk`); não instale sem perguntar.
- Perfil: aquecimento → patamar esperado (carga) → acima do esperado (estresse) → retorno ao
  normal (recuperação). Registre latência p50/p95/p99, taxa de erro, throughput.
- Monitore o processo com `collect_metrics.py --pid` durante a carga.
- Defina limite de duração e de taxa antes de iniciar; interrompa se a máquina do usuário degradar.
