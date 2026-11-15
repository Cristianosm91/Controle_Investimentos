# Relatório — Migrações de banco — <Aplicação>

**Parecer:** `APROVADO` | `APROVADO COM RESSALVAS` | `REPROVADO` | `INCONCLUSIVO`
**Modo executado:** review | test | fix
**Data:**
**Versão/commit auditado:**
**Ambiente:** SO, linguagem, ferramenta de migração, SGBD(s) e versões

## Resumo

…

## Inventário de revisões

| Revisão | Mensagem | down_revision | Tipo (schema/dados) | Reversível | Destrutiva | Observações |
|---|---|---|---|---|---|---|
| | | | | sim/não/documentado | sim/não | |

## Matriz de testes de migração

| Teste | SGBD | Banco (vazio/cópia fictícia/backup antigo) | Resultado | Evidência |
|---|---|---|---|---|
| upgrade head → downgrade base → upgrade head | | vazio | aprovado / reprovado / não executado | |
| Passo a passo | | | | |
| Upgrade com dados (contagens antes/depois) | | cópia fictícia | | |
| Backup de versão antiga → head | | backup antigo | | |
| Drift (`alembic check`) | | | | |

## Achados

| ID | Severidade | Título | Evidência | Natureza | Proposta | Status |
|---|---|---|---|---|---|---|
| MIG-001 | Crítica/Alta/Média/Baixa/Informativa | | | [EXECUTADO]/[TEÓRICO] | | aberto / aguardando confirmação / corrigido / aceito como risco |

## Testes não executados

| ID | Motivo | Dependência | Comando que seria usado | Risco não validado |
|---|---|---|---|---|

## Alterações realizadas (somente `fix`)

Nenhuma | nova migração criada, diff resumido, teste que falhava antes e passa depois, confirmação do usuário.

## Limitações

- [LIMITAÇÃO] …

## Recomendações

1. …

---
Gerado com a skill `migracoes-banco`. Válido apenas para a versão, os SGBDs e os testes listados.
