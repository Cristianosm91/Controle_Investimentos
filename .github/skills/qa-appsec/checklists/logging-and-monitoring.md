# Logging, monitoramento e rastreabilidade

## Logs e auditoria
- Eventos relevantes registram ator, ação, alvo, resultado, horário e correlação sem excesso de dados?
- Tokens, senhas, PII, payloads, headers de autenticação e dados financeiros são excluídos ou mascarados?
- Entradas são normalizadas para evitar falsificação/injeção de logs?
- Logs de autenticação, autorização, mudanças administrativas e exportações são protegidos contra alteração indevida?
- Retenção, acesso, descarte e sincronização de horário estão definidos?

## Detecção e resposta
- Alertas cobrem falhas repetidas, acesso privilegiado, mudança de configuração e volume incomum?
- Métricas/traces não carregam segredos nem conteúdo sensível desnecessário?
- Alertas têm limiares, responsável, runbook e tratamento de falso positivo?
- Falhas em logging/monitoramento têm comportamento seguro sem mascarar falha de negócio?
- Há rastreabilidade entre aplicação, identidade, integração e evento de auditoria?

Inspecionar configuração e exemplos sanitizados. Não gerar eventos em sistemas externos nem exportar
logs reais para confirmar hipótese.