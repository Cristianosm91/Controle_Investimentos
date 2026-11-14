# Segurança da lógica de negócio

## Fluxos e invariantes
- Mapear estados permitidos, transições, pré-condições e atores autorizados.
- Verificar se preços, quantidades, limites, descontos e resultados são calculados no servidor.
- Operações financeiras/transacionais usam idempotência, controle de duplicidade e reconciliação?
- Aprovação, revisão e execução são segregadas onde necessário (maker-checker/self-approval)?
- Regras de propriedade, tenant, limites por usuário e validade são impostas server-side?
- Concorrência e repetição não violam saldos, quotas, reservas ou estados?
- Cancelamento, reversão, timeout e falha parcial deixam estado consistente e auditável?
- Exportação, reembolso, crédito, cupom ou ação administrativa respeitam limites e trilha de auditoria?

## Evidência segura
Descrever o caso de abuso como hipótese ou achado confirmado conforme evidência de código/testes.
Não criar transações reais, modificar dados de produção ou fornecer sequência explorável. Validar com
fixtures sintéticas em ambiente isolado e autorização explícita.