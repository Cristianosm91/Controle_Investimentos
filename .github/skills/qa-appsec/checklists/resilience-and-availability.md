# Resiliência e disponibilidade

## Revisão de desenho e código
- Timeouts existem em chamadas de rede, banco e processos; valores são coerentes com o fluxo?
- Retries têm limite, backoff/jitter e proteção contra repetição de operação não idempotente?
- Circuit breaker, bulkhead, filas e limites evitam cascata e consumo ilimitado?
- Degradação/failover preserva segurança e integridade, sem bypass de autorização?
- Transações, idempotência, concorrência, rollback e recuperação de estado estão definidos?
- Health/readiness/liveness diferenciam falha recuperável de falha crítica?
- Quotas, pools, cache, disco, tamanho de arquivo e filas têm limites e alertas?
- Backup/restore, RPO/RTO, continuidade e dependências single-point-of-failure são conhecidos?

## Validação
Sem autorização, avaliar código, configuração, documentação e testes existentes. Teste de carga,
chaos, indisponibilidade simulada ou falha injetada exigem autorização explícita, sandbox, limites,
rollback e condições de parada; não executar em produção ou terceiros.