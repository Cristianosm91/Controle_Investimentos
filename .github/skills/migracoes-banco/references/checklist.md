# Checklist — Migrações de banco

Use na revisão e no plano de testes. Cada item não atendido vira achado `MIG-NNN` com evidência
(arquivo:linha da migração, saída do comando, contagem antes/depois) e proposta.

## 1. Configuração e cadeia de revisões

| Verificar | Como comprovar |
|---|---|
| `target_metadata` aponta para **todos** os modelos (imports completos) | Ler `env.py`; `alembic check` sem diferenças |
| Uma única `head` | `alembic heads` |
| Sem revisões órfãs/duplicadas; `down_revision` coerente | `alembic history` |
| `render_as_batch=True` quando SQLite é suportado | Ler `env.py` |
| `compare_type=True` (e `compare_server_default` se relevante) | Ler `env.py` |
| Convenção de nomes (`naming_convention` no `MetaData`) para PK, FK, UQ, IX, CK | Ler metadata; nomes estáveis entre SGBDs |
| URL do banco vinda de configuração, sem credencial hardcoded | Ler `alembic.ini`/`env.py` |
| Como a app aplica migrações (manual/startup) e se faz backup antes | Ler ponto de entrada |

## 2. Cada migração

- **Mensagem/nome descritivo**; uma mudança lógica por migração.
- **Nunca editada após aplicada** (comparar com histórico do VCS).
- `upgrade` e `downgrade` implementados; `downgrade` irreversível documentado e levantando erro claro.
- Não importa modelos ORM da aplicação (eles mudam no futuro) — usar `sa.table()`/SQL.
- Sem dependência de dados de ambiente (datas atuais, arquivos locais) sem necessidade.

## 3. Colunas, constraints e índices

| Situação | Exigência |
|---|---|
| Nova coluna `NOT NULL` em tabela com dados | `server_default` ou: adicionar nullable → backfill → tornar NOT NULL |
| Mudança de tipo | Conversão explícita; testar com dados limite (texto longo, decimal com escala) |
| Coluna monetária | Tipo exato (`Numeric(p, s)`), nunca `Float` |
| Renomear coluna/tabela | `alter_column(new_column_name=...)`/`rename_table`, não drop + add |
| Constraint/índice/FK | Nomeado; `ondelete` coerente com a regra; índices para FKs e filtros frequentes |
| Unicidade nova | Verificar duplicados existentes antes (senão o upgrade falha) |
| Enum | Estratégia de adição de valores por SGBD documentada |

## 4. SQLite × PostgreSQL

- SQLite não suporta a maioria dos `ALTER` (drop/alter column, add constraint): usar
  `op.batch_alter_table` (recria a tabela) — verificar FKs, índices e triggers preservados.
- Batch mode com FKs ativas: `PRAGMA foreign_keys` pode precisar ser desligado durante a cópia.
- SQLite não impõe tamanho de `VARCHAR` nem escala de `NUMERIC` — testar também no SGBD estrito
  se suportado.
- DDL transacional: PostgreSQL faz rollback de DDL; SQLite parcialmente; MySQL não — avaliar
  estado após falha no meio.
- Operações que bloqueiam tabela no PostgreSQL (`ADD COLUMN ... DEFAULT` volátil, índice sem
  `CONCURRENTLY`, validação de constraint) em tabelas grandes.

## 5. Migrações de dados

- **Idempotentes**: rodar duas vezes não duplica nem corrompe (usar `WHERE` de condição, upsert).
- Em lotes para tabelas grandes; sem carregar tudo em memória.
- Separadas de migrações de schema quando possível.
- Contagens/somatórios antes e depois registrados no teste.
- Valores derivados de regra de negócio: regra confirmada com o usuário (nunca inventada).
- `downgrade` de dados: reverte ou documenta perda.

## 6. Operações destrutivas

- `drop_table`, `drop_column`, truncamento, conversão com perda, `DELETE` em massa:
  **backup verificado + confirmação explícita** + aviso na nota de versão.
- Preferir depreciação em duas versões (deixar de usar → remover depois).

## 7. Drift modelo × banco

- `alembic check` (ou `compare_metadata`) após `upgrade head` em banco vazio: **zero diferenças**.
- Banco criado por `create_all()` × banco criado por migrações: mesmo schema (comparar
  `sqlite_master`/`information_schema`).
- Tabelas/colunas existentes no banco e ausentes nos modelos documentadas.

## 8. Testes de migração

| Teste | Procedimento |
|---|---|
| Ida e volta em banco vazio | `upgrade head` → `downgrade base` → `upgrade head` (sem erro) |
| Passo a passo | Para cada revisão: `upgrade +1` → `downgrade -1` → `upgrade +1` |
| Com dados | Cópia do banco com dados **fictícios** na revisão N-1 → `upgrade head` → contagens/somatórios/integridade |
| Backup antigo | Backups de exemplo de versões anteriores (fictícios) restaurados e migrados para `head` |
| Drift | `alembic check` sem diferenças |
| Falha no meio | Simular erro numa migração: banco permanece consistente/recuperável |
| CI | Todos acima executados no pipeline, em banco temporário |

Exemplo genérico (pytest + Alembic, banco temporário):

```python
from alembic import command
from alembic.config import Config

def test_ida_e_volta(tmp_path):
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{tmp_path / 'teste.db'}")
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
```

## 9. Operação

- **Backup antes de migrar** (automático quando a app migra no startup), com verificação de
  integridade.
- Versão de schema registrada e exibida (diagnóstico).
- Migração longa: feedback ao usuário, sem timeout que interrompa no meio, espaço em disco
  verificado antes.
- App mais nova em banco mais novo/antigo: comportamento definido (migra, recusa com mensagem clara).
- Logs de migração sem dados pessoais.
