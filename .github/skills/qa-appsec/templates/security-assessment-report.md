# Relatório de avaliação de segurança e resiliência

## Identificação
- Aplicação/serviço:
- Versão, commit ou hash do artefato:
- Data e período analisado:
- Perfil: `quick-scan | standard | deep`
- Responsável pela avaliação:

## 1. Resumo executivo
- Conclusão limitada ao escopo:
- Risco predominante:
- Achados: Crítica __ | Alta __ | Média __ | Baixa __ | Informativa __
- Prioridades imediatas:
- Limitações relevantes:

## 2. Escopo e autorização
- Repositório, diretórios, artefatos, ambientes e componentes incluídos:
- Alvos explicitamente autorizados para validação dinâmica (se houver):
- Exclusões e restrições:
- Dados utilizados: sintéticos / outros autorizados (descrever sem expor):
- Evidência da autorização e janela:

## 3. Tecnologias e arquitetura
- Linguagens, frameworks e versões:
- Componentes, integrações e dependências:
- Autenticação, autorização e identidades de serviço:
- Armazenamento, filas, APIs e terceiros:
- Fronteiras de confiança:

## 4. Metodologia e cobertura
- Referências usadas e pertinência:
- Revisões estáticas/arquiteturais realizadas:
- Ferramentas locais utilizadas e versões:
- Validações dinâmicas autorizadas:
- Testes executados / resultado / evidência:
- Testes não executados / motivo:

## 5. Superfície de ataque e fluxos de dados
- Atores, ativos, entradas e saídas:
- Superfície de ataque observada:
- Dados sensíveis e classificação:
- Fluxos, cópias, retenção e descarte:
- Controles preventivos, detectivos e corretivos:

## 6. Achados
Para cada item, use o formato de [relatório técnico](technical-report.md). Inclua confirmados,
potenciais, recomendações preventivas, controles positivos e falsos positivos relevantes.

## 7. Cenários e matriz de risco
Use [registro de riscos](risk-register.md). Separe impacto, probabilidade, severidade e confiança.

## 8. Resiliência e disponibilidade
- Dependências críticas e modos de falha:
- Timeouts, retries, limites, filas e degradação segura:
- Backup, restauração, failover, RPO/RTO (se documentados):
- Monitoramento, alertas e rastreabilidade:
- Cenários não validados:

## 9. Plano de correção
Use [plano](remediation-plan.md) e [backlog](remediation-backlog.md). Liste controles compensatórios,
responsáveis sugeridos, critérios de aceite e risco residual.

## 10. Limitações e risco residual
- Escopo não disponível:
- Dependências/ferramentas ausentes:
- Ambiente ou autorização ausentes:
- Suposições não confirmadas:
- Risco residual após controles observados:

## 11. Plano de reteste
Use [relatório de reteste](retest-report.md); não marque itens como corrigidos sem evidência.

## Conclusão
Escolha uma classificação e justifique: `CRÍTICA` | `INSUFICIENTE` | `PARCIALMENTE ADEQUADA` |
`ADEQUADA COM MELHORIAS` | `BOA POSTURA DE SEGURANÇA`.
Declare cobertura, achados abertos, testes não executados e risco residual. Esta conclusão não declara
ausência total de vulnerabilidades.