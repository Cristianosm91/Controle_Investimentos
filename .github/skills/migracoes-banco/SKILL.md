---
name: migracoes-banco
description: 'Use ao auditar, testar ou validar migrações de banco de dados (Alembic ou equivalente) de uma aplicação — cobertura de toda mudança de schema, upgrade/downgrade em banco vazio e em cópia com dados, migrações de dados idempotentes, operações destrutivas, limitações do SQLite (batch mode) × PostgreSQL, constraints, índices, chaves estrangeiras, defaults de colunas NOT NULL, drift entre modelos e migrações, convenções de nomes, backup antes de migrar, testes em CI e restauração de backups antigos — sem alterar regras de negócio por conta própria. Modos review (padrão, somente leitura), test e fix. Palavras-gatilho: migração, migration, Alembic, autogenerate, upgrade, downgrade, revision, head, schema, drift, DDL, ALTER TABLE, batch_alter_table, SQLite, PostgreSQL, constraint, índice, foreign key, NOT NULL, server_default, migração de dados, rollback de schema.'
argument-hint: '[modo: review | test | fix] [caminho] [foco opcional]'
---

# Migrações de Banco

Valida a **segurança, reversibilidade e consistência** das migrações de banco de dados de uma
aplicação — as já aplicadas e as futuras. Objetivo: garantir que toda mudança de schema e de dados
seja versionada, testada em banco vazio e com dados, não destrua informação sem backup e
confirmação, e mantenha modelos e banco sincronizados — **sem alterar regras de negócio,
funcionalidades ou dados por iniciativa própria**.

## Quando usar
- Revisar a pasta de migrações e os modelos ORM antes de uma versão.
- Validar nova migração (schema ou dados) adicionada por uma funcionalidade.
- Investigar falha de `upgrade`, drift entre modelo e banco, ou banco de usuário "preso" em versão antiga.
- Criar testes de migração (upgrade/downgrade, dados, restauração de backups antigos) e integrá-los à CI.

## Quando NÃO usar
- Desenho de modelo de dados novo ou mudança de regra de negócio (decisão do usuário).
- Estratégia de backup/restauração em si → `backup-recuperacao`.
- Tuning geral de consultas → `qa-application-auditor`.
- Licenciamento, autenticação, multi-tenant, aspectos regulatórios/comerciais (fora de escopo).

---

## Princípios obrigatórios (inegociáveis)

1. **Não alterar regras de negócio, fórmulas, funcionalidades ou comportamento sem solicitação
   explícita do usuário.**
2. **Divergência encontrada vira achado com evidência e proposta**, nunca correção silenciosa.
3. **Modo padrão `review` é somente leitura** — não executar `upgrade`/`downgrade` em banco real.
4. **`fix` só com pedido explícito e confirmação**; mudanças mínimas, com teste que **falha antes
   e passa depois**.
5. **Nunca editar migração já aplicada/distribuída** — corrigir com nova migração.
6. **Nenhuma operação destrutiva** (`DROP`, perda de coluna, truncamento, conversão com perda) sem
   backup verificado e confirmação explícita.
7. **Testar somente em bancos descartáveis**: banco vazio temporário ou **cópia** do banco com
   dados fictícios — nunca no arquivo/instância de uso real.
8. **Diferenciar análise teórica de teste executado** (`[TEÓRICO]` / `[EXECUTADO]`).
9. **Nunca usar dados reais/pessoais em fixtures**: usar dados fictícios.
10. **Informar limitações** (SGBD não disponível, versão antiga sem backup de exemplo etc.).

---

## Modos de operação

Sem modo informado, use **`review`**. Pedido de "corrigir" sem modo → **confirme** antes de `fix`.

| Modo | Faz | Não faz |
|---|---|---|
| `review` (padrão) | Lê migrações, modelos e configuração; checa cadeia de revisões, reversibilidade, riscos destrutivos, drift teórico | Não executa migrações; não modifica arquivos |
| `test` | Em bancos temporários: upgrade/downgrade, comparação modelo × banco, migração com dados fictícios, restauração de backups antigos; cria testes **em arquivos de teste próprios** | Não toca o banco real; não altera código produtivo/migrações |
| `fix` | Cria **nova** migração ou ajuste mínimo confirmado, com teste que falha antes e passa depois | Não edita migração aplicada; não executa destrutivo sem backup e confirmação |

---

## Fluxo de trabalho

1. **Descoberta** — ferramenta de migração, configuração (`alembic.ini`/`env.py`), `target_metadata`,
   SGBDs suportados, como a app aplica migrações (manual, no startup), onde fica o banco, testes
   existentes, rotina de backup prévia.
2. **Cadeia de revisões** — única `head`, sem ramos órfãos, `down_revision` coerente, nomes e
   mensagens descritivas.
3. **Revisão de cada migração** — aplicar [references/checklist.md](references/checklist.md):
   reversibilidade, destrutivos, defaults, constraints, índices, FKs, batch mode, migração de dados
   idempotente, duração.
4. **Drift** — comparar modelos × banco migrado (`alembic check` / `compare_metadata`); qualquer
   diferença é achado.
5. **Testes** (`test`/`fix`) — banco vazio: `upgrade head` → `downgrade base` → `upgrade head`;
   cópia com dados fictícios: upgrade preservando contagens/somatórios; backups de versões antigas
   migrando para `head`.
6. **Correções** (somente `fix`, após confirmação) — nova migração, teste reproduzindo, regressão.
7. **Relatório** — [templates/relatorio.md](templates/relatorio.md) em `qa-report/migracoes-banco/`.

---

## Checklist

Detalhado em [references/checklist.md](references/checklist.md). Prioridades:
- Mudança em modelo sem migração correspondente (drift).
- Coluna `NOT NULL` adicionada sem `server_default` ou sem preenchimento prévio.
- `ALTER` incompatível com SQLite fora de `batch_alter_table` (ou `render_as_batch` ausente).
- Migração de dados não idempotente ou dependente de modelos ORM atuais (usar SQL/tabelas leves).
- `downgrade` vazio, com `pass`, ou que perde dados sem aviso.
- Migração aplicada automaticamente no startup **sem backup prévio**.

---

## Validação de novas funcionalidades

Toda funcionalidade que altere schema ou dados persistidos deve trazer:
- **Migração nova** (nunca edição de antiga), com mensagem descritiva e convenção de nomes.
- `upgrade` e `downgrade` implementados (ou `downgrade` justificado como irreversível e documentado).
- Defaults/backfill para colunas obrigatórias; constraints, índices e FKs nomeados.
- Compatibilidade com todos os SGBDs suportados (ex.: batch mode no SQLite).
- Teste de migração: banco vazio ida/volta + cópia com dados fictícios + checagem de drift.
- Backup antes de migrar garantido pelo fluxo da aplicação (ver `backup-recuperacao`).
- Nota de versão/documentação do impacto (tempo, irreversibilidade, necessidade de backup).

---

## Entregáveis

Em `qa-report/migracoes-banco/`:
- `relatorio.md` a partir de [templates/relatorio.md](templates/relatorio.md): inventário de
  revisões, matriz de testes de migração, achados (ID `MIG-NNN`, severidade
  **Crítica/Alta/Média/Baixa/Informativa**, evidência, proposta, status), limitações e parecer.
- Testes criados e evidências (comandos, saídas, contagens antes/depois).

Severidade: **Crítica** — perda/corrupção de dados ou banco impossível de migrar; **Alta** —
upgrade falha em cenário plausível (dados existentes, SQLite, backup antigo) ou drift relevante;
**Média** — downgrade ausente, migração não idempotente sem impacto confirmado; **Baixa** —
convenção de nomes, mensagens; **Informativa** — melhoria.

---

## Integração com outras skills

- `prontidao-producao` — gate orquestrador que aciona esta skill e consolida o parecer.
- `backup-recuperacao` — backup antes de migrar; restauração de backups antigos migrando para `head`.
- `calculos-financeiros-fiscais` — tipo/escala de colunas monetárias, tabelas de regras com vigência.
- `qa-application-auditor` — duração e bloqueios de migrações longas.
- `qa-appsec` — SQL dinâmico em migrações, permissões de arquivo do banco.
- `software-engineering-refactoring` — organização de modelos sem alterar schema efetivo.
- `ci-cd-release` — testes de migração e checagem de drift obrigatórios no pipeline.
- `observabilidade-logs` — registro de versão de schema e de falhas de migração.
- `privacidade-dados` — dados fictícios em cópias de teste.
- `documentacao-funcional` — procedimento de atualização para o usuário.
