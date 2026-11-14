# Matriz de cobertura — Funcionalidade × Cenário E2E — <Aplicação>

**Data:** · **Versão/commit:** · **Fonte do inventário:** router, menu, páginas (arquivos lidos)

Legenda de status: `planejado` · `implementado` · `aprovado` · `reprovado` · `instável` ·
`bloqueado` · `não executado` · `sem cobertura`

## Inventário funcional

| ID func. | Área/menu | Rota/página | Funcionalidade | Ações do usuário | Dependências externas | Criticidade |
|---|---|---|---|---|---|---|
| F-001 | | `/` | | | nenhuma | Alta |
| F-002 | | | | | | |

## Matriz

| ID func. | Cenário | ID E2E | Tipo | Smoke | Mock necessário | Arquivo do teste | Status | Última execução |
|---|---|---|---|---|---|---|---|---|
| F-001 | Abre e exibe dados semeados | E2E-T-001 | feliz | sim | — | | planejado | |
| F-001 | Estado vazio | E2E-T-002 | vazio | não | — | | planejado | |
| F-001 | Erro de API exibe mensagem | E2E-T-003 | erro | não | `page.route` 500 | | planejado | |
| F-002 | Criação com validação de campos | | validação | | | | | |
| F-002 | Exclusão com confirmação/cancelamento | | destrutivo | | | | | |

Tipos: `feliz` · `validação` · `vazio` · `erro` · `destrutivo` · `permissão de arquivo/IO` ·
`a11y` · `visual` · `navegação/deep link`.

## Resumo de cobertura

| Métrica | Valor |
|---|---|
| Funcionalidades inventariadas | |
| Com ao menos 1 cenário | |
| Fluxos críticos com cenário feliz + erro | |
| Cenários smoke | |
| Funcionalidades sem cobertura (IDs) | |
