---
name: prontidao-producao
description: 'Use para avaliar se uma aplicação (ou uma funcionalidade nova/alterada) está pronta para uso real com qualidade de produção — orquestra as skills especializadas de QA, segurança, cálculos, dados, integrações, observabilidade, privacidade, UX/acessibilidade, testes E2E, CI/CD, migrações, backup e documentação, consolida os achados e emite um parecer PRONTO / PRONTO COM RESSALVAS / NÃO PRONTO / INCONCLUSIVO. Valida o que existe sem alterar regras de negócio ou funcionalidades por conta própria. Palavras-gatilho: prontidão para produção, production readiness, checklist de produção, go-live, aplicação completa, validar funcionalidade nova, definition of done, gate de qualidade, auditoria completa, revisão geral, está pronto?'
argument-hint: '[escopo: app | funcionalidade <nome> | diff] [modo: review | test | fix] [áreas opcionais]'
---

# Prontidão para produção (gate de qualidade)

Orquestrador que avalia uma aplicação — inteira ou apenas uma funcionalidade nova/alterada — contra
os pilares de uma aplicação real em produção, delegando cada pilar à skill especializada e
consolidando tudo em um único parecer. O objetivo é **validar** e **apontar lacunas com evidência**,
nunca reescrever o produto.

## Quando usar
- Antes de uma versão/entrega: "a aplicação está pronta?", "faça uma revisão geral".
- Ao concluir uma **funcionalidade nova ou alterada** (Definition of Done).
- Periodicamente, para medir a evolução (comparar com o parecer anterior).

## Quando NÃO usar
- Para implementar funcionalidades novas (use o fluxo normal de desenvolvimento).
- Para uma análise isolada e já identificada (chame direto a skill especializada).
- Temas fora de escopo desta skill: licenciamento, termos comerciais, autenticação/login,
  multi-tenancy e conformidade jurídica formal.

---

## Princípios obrigatórios (inegociáveis)
1. **Não alterar regras de negócio, fórmulas, textos de domínio, fluxos ou funcionalidades** sem
   solicitação explícita do usuário. Divergência encontrada vira **achado com evidência e proposta**.
2. **Modo padrão `review` é somente leitura.** `test` só cria testes/arquivos de evidência novos;
   `fix` exige pedido explícito **e** confirmação dos itens a corrigir.
3. **Sem evidência, sem aprovação:** nenhum pilar é "OK" por leitura superficial. Diferencie sempre
   `[EXECUTADO]`, `[ANÁLISE ESTÁTICA]` e `[NÃO EXECUTADO]`.
4. **Uma skill por pilar:** siga o fluxo e os princípios da skill especializada; não duplique nem
   relaxe regras dela.
5. **Nada de serviços externos reais em testes, carga contra terceiros ou dados pessoais reais.**
6. **Mudanças mínimas e rastreáveis** quando houver `fix`, com regressão completa ao final.
7. **Informe limitações** (ferramentas ausentes, arquivos bloqueados por política, ambiente).

---

## Modos de operação

| Modo | Faz | Não faz |
|---|---|---|
| `review` (padrão) | Descobre a aplicação, roda cada pilar em modo `review`, consolida achados e parecer | Não altera arquivos produtivos |
| `test` | `review` + executa build/testes existentes e cria testes ausentes em arquivos próprios | Não altera código produtivo |
| `fix` | Corrige **apenas** achados confirmados pelo usuário, um por vez, com teste antes/depois | Não muda regra de negócio; não refatora por estética |

Escopos: `app` (aplicação inteira), `funcionalidade <nome>` (só o que a funcionalidade toca) ou
`diff` (alterações da branch atual em relação à base — `git diff <base>...HEAD`).

---

## Pilares e skills responsáveis

| # | Pilar | Skill | Perguntas-chave |
|---|---|---|---|
| 1 | Estabilidade, performance, recursos | `qa-application-auditor` | Trava? Vaza memória/threads? Escala com o volume real? |
| 2 | Segurança da aplicação | `qa-appsec` | Superfície, entradas, uploads, dependências, segredos, cabeçalhos |
| 3 | Privacidade de dados | `privacidade-dados` | Dados pessoais mínimos, mascarados, fora de logs, apagáveis |
| 4 | Correção de cálculos | `calculos-financeiros-fiscais` | Precisão, arredondamento, vigência de regras, casos de referência |
| 5 | Banco e migrações | `migracoes-banco` | Toda mudança de esquema tem migração testada (upgrade/downgrade) |
| 6 | Backup e recuperação | `backup-recuperacao` | RPO/RTO, restauração testada, integridade |
| 7 | Integrações externas | `integracoes-externas` | Timeouts, retries, cache, dado desatualizado sinalizado, mocks |
| 8 | Observabilidade e erros | `observabilidade-logs` | Logs úteis sem dados pessoais, healthcheck, erros tratados |
| 9 | UX e acessibilidade | `web-ux-acessibilidade` (web) / `app-ux` (desktop) | WCAG 2.2 AA, estados de tela, formatos pt-BR |
| 10 | Testes ponta a ponta | `testes-e2e` | Fluxos críticos cobertos, isolados e estáveis |
| 11 | CI/CD e release | `ci-cd-release` + `git-workflow` | Pipeline roda lint/testes/build; versão, changelog e tag |
| 12 | Documentação | `documentacao-funcional` | Docs refletem o código; changelog e FAQ atualizados |
| 13 | Manutenibilidade | `software-engineering-refactoring` (só diagnóstico) | Acoplamento, duplicação, testabilidade |

Pilares que não se aplicam (ex.: sem banco, sem integração externa) são marcados **N/A com
justificativa**, nunca omitidos.

---

## Fluxo de trabalho

Registre o progresso com uma lista de tarefas (um item por pilar).

1. **Descoberta** — stack, tipo de app, comandos reais (README, manifestos, scripts), estrutura,
   testes existentes, banco, integrações, jobs, CI. Para `funcionalidade`/`diff`, mapeie os
   arquivos, rotas, telas, tabelas e regras afetadas.
2. **Inventário funcional** — liste funcionalidades e regras de negócio visíveis (fonte: código,
   docs e testes). Este inventário é a **referência do comportamento atual** a preservar.
3. **Baseline** — rode lint/testes/build existentes (modos `test`/`fix`) e registre o resultado.
4. **Avaliação por pilar** — para cada pilar aplicável, siga a skill responsável no modo
   correspondente, usando o mínimo de [references/criterios-por-pilar.md](references/criterios-por-pilar.md).
   Reaproveite relatórios recentes (`qa-report/`, `security-report/`) quando escopo e versão
   coincidirem; caso contrário, reexecute.
5. **Consolidação** — unifique os achados em [templates/parecer.md](templates/parecer.md),
   removendo duplicados entre pilares e mantendo o ID de origem.
6. **Plano de ação** — ordene por severidade e esforço; separe "corrigível sem mudar regra" de
   "exige decisão do usuário".
7. **Correções** (somente `fix`) — aplique os itens confirmados, um por vez, com teste antes/depois
   e regressão completa no final.
8. **Parecer** — emita o resultado e as condições para atingir o próximo nível.

---

## Validação de novas funcionalidades (Definition of Done)
Toda funcionalidade nova ou alterada só é considerada pronta quando:
- [ ] Regras de negócio confirmadas pelo usuário e cobertas por testes (unitários + casos de referência quando houver cálculo).
- [ ] Mudança de banco acompanhada de migração testada e compatível com backups antigos.
- [ ] Entradas validadas no servidor; uploads/arquivos com limites; nenhum dado pessoal novo em logs.
- [ ] Integrações novas com timeout, tratamento de falha, estado visível ao usuário e testes com mocks.
- [ ] Estados de carregando/vazio/erro, teclado e leitores de tela tratados na interface.
- [ ] Fluxo principal coberto por teste E2E (ou justificativa registrada).
- [ ] Lint, type check, testes e build passando localmente e no CI.
- [ ] README/FAQ/regras de cálculo/CHANGELOG atualizados na mesma mudança.
- [ ] Versão e changelog seguem o `git-workflow`.

---

## Severidade e parecer

Severidades: **Crítica** (perda/corrupção de dados, cálculo errado com impacto financeiro,
falha de segurança explorável), **Alta** (funcionalidade principal falha ou sem recuperação),
**Média** (degradação, lacuna de teste em fluxo crítico), **Baixa** (melhoria), **Informativa**.

| Parecer | Condição |
|---|---|
| **PRONTO** | Nenhum achado Crítico/Alto/Médio aberto; pilares aplicáveis com evidência executada |
| **PRONTO COM RESSALVAS** | Sem Crítico/Alto; Médios com plano, ou pilares com limitação documentada |
| **NÃO PRONTO** | Qualquer Crítico ou Alto aberto |
| **INCONCLUSIVO** | Evidência insuficiente nos pilares essenciais (1, 2, 4, 5, 6) |

---

## Entregáveis
- `qa-report/prontidao/AAAAMMDD-<escopo>.md` — parecer consolidado ([templates/parecer.md](templates/parecer.md)).
- Relatórios de cada pilar nas pastas das skills especializadas (`qa-report/<skill>/`).
- Evidências (logs de comandos, saídas de teste) referenciadas no parecer — nunca com dados reais.

## Integração com outras skills
Esta skill **não substitui** as especializadas: ela as chama e consolida. Ao final de uma
funcionalidade, use também `commit-message` e `git-workflow` para registrar a entrega.
