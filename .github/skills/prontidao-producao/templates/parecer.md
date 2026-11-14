# Parecer de prontidão — <aplicação> <versão>

| Item | Valor |
|---|---|
| Escopo | app / funcionalidade `<nome>` / diff `<base>...<head>` |
| Commit / branch | |
| Data | AAAA-MM-DD |
| Modo | review / test / fix |
| Ambiente | SO, versões de runtime, banco |

## Parecer: **PRONTO | PRONTO COM RESSALVAS | NÃO PRONTO | INCONCLUSIVO**

Justificativa objetiva (3–5 linhas).

## Situação por pilar

| # | Pilar | Skill | Status | Evidência | Achados abertos |
|---|---|---|---|---|---|
| 1 | Estabilidade e performance | qa-application-auditor | OK / Ressalva / Falha / N/A | [EXECUTADO] link | |
| 2 | Segurança | qa-appsec | | | |
| 3 | Privacidade | privacidade-dados | | | |
| 4 | Cálculos | calculos-financeiros-fiscais | | | |
| 5 | Banco e migrações | migracoes-banco | | | |
| 6 | Backup e recuperação | backup-recuperacao | | | |
| 7 | Integrações externas | integracoes-externas | | | |
| 8 | Observabilidade | observabilidade-logs | | | |
| 9 | UX e acessibilidade | web-ux-acessibilidade / app-ux | | | |
| 10 | Testes E2E | testes-e2e | | | |
| 11 | CI/CD e release | ci-cd-release / git-workflow | | | |
| 12 | Documentação | documentacao-funcional | | | |
| 13 | Manutenibilidade | software-engineering-refactoring | | | |

## Achados consolidados

| ID | Origem (ID do pilar) | Severidade | Descrição | Evidência | Proposta | Exige decisão do usuário? | Status |
|---|---|---|---|---|---|---|---|
| PP-001 | | Crítica/Alta/Média/Baixa/Informativa | | | | Sim/Não | aberto/corrigido/aceito |

## Plano de ação
1. Itens corrigíveis sem mudar regra de negócio (ordem sugerida).
2. Itens que exigem decisão do usuário (com opções e impacto).

## Testes não executados e limitações
- Descrever limitações e testes pendentes.

## Comparação com o parecer anterior
- Data/versão anterior, achados resolvidos, novos achados, tendência.
