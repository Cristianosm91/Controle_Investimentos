# Checklist — Backup e recuperação

Use na revisão e no plano de testes. Cada item não atendido vira achado `BKP-NNN` com evidência
(arquivo:linha, saída do comando, tempo medido, contagens antes/depois) e proposta.

## 1. Escopo e metas

| Verificar | Exigência |
|---|---|
| Inventário do que proteger | Banco, anexos/importações, configuração, preferências, chaves necessárias para ler dados criptografados |
| RPO definido | Ex.: "no máximo 24 h de perda"; frequência de backup compatível |
| RTO definido | Ex.: "restaurar em até 15 min"; tempo medido no drill compatível |
| Responsável/gatilho | Automático (agendado, antes de migrar/atualizar, ao fechar) e manual (botão/comando) |

## 2. Consistência do backup

- SQLite: usar **API de backup** (`sqlite3.Connection.backup`) ou `VACUUM INTO`; **nunca** copiar o
  arquivo `.db` com conexões abertas (ignora `-wal`/`-shm`, gera cópia inconsistente).
- PostgreSQL: `pg_dump` (formato custom `-Fc`) ou backup físico com ferramenta própria; não copiar
  o diretório de dados com o servidor rodando.
- Backup é atômico do ponto de vista do arquivo: gravar em temporário e renomear ao final (queda no
  meio não deixa arquivo parcial com nome válido).
- Nome com data/hora e versão de schema/aplicação (ex.: `app_<AAAAMMDD-HHMMSS>_<revisão>.db`).

## 3. Integridade

| SGBD | Verificação após gerar |
|---|---|
| SQLite | Abrir o backup e rodar `PRAGMA integrity_check` (= `ok`); opcional `PRAGMA foreign_key_check` |
| PostgreSQL | `pg_restore --list` sem erro; drill de restauração periódico |
| Arquivos | Hash (SHA-256) registrado em manifesto e conferido antes de restaurar |

- Falha de verificação gera alerta visível e **não** substitui backups bons anteriores.

## 4. Retenção

- Política explícita (ex.: diários por 7 dias, semanais por 4 semanas, mensais por 12 meses).
- Limpeza só remove backups **verificados como mais antigos** e nunca o último íntegro.
- Limite de espaço: alerta antes de encher o disco.

## 5. Armazenamento (3-2-1)

- **3** cópias, em **2** mídias/locais diferentes, **1** fora do equipamento.
- Não manter backup apenas no mesmo disco/pasta do banco.
- **Banco aberto não deve ficar em pasta sincronizada na nuvem** (risco de corrupção/conflito);
  backups fechados podem ser enviados a pasta sincronizada.
- Permissões de arquivo restritas ao usuário.
- **Criptografia em repouso** quando o backup sai do equipamento ou contém dados sensíveis; chave
  guardada separada do backup e com procedimento de recuperação documentado.

## 6. Configuração

- Arquivos de configuração e preferências incluídos (sem segredos em texto puro).
- Caminhos absolutos do equipamento antigo não quebram a restauração em outro equipamento.

## 7. Restauração

| Verificar | Exigência |
|---|---|
| Cópia antes de restaurar | Estado atual salvo automaticamente antes de sobrescrever |
| Verificação antes | Integridade/hash do backup escolhido conferidos antes de aplicar |
| Aplicação parada/conexões fechadas | Pool fechado, escrita bloqueada durante a troca |
| Troca atômica | Restaurar em temporário → validar → substituir |
| Schema antigo | Backup de versão anterior é migrado para `head` após restaurar (ver `migracoes-banco`) |
| Schema mais novo que a app | Recusa com mensagem clara |
| Validação depois | Contagens por tabela, somatórios relevantes (ex.: totais financeiros), checksums comparados com o manifesto do backup |
| Rollback | Falha na restauração volta à cópia feita antes |
| Confirmação do usuário | Diálogo claro com data/origem do backup e consequências |

## 8. Concorrência

- Escritas durante o backup: snapshot consistente (API de backup/transação) e sem travar a app por
  tempo excessivo.
- Backup agendado não sobrepõe outro em execução (lock).
- Restauração bloqueia escrita até concluir.

## 9. Cenários de desastre (testar em ambiente isolado)

| Cenário | Comportamento esperado |
|---|---|
| Disco cheio durante backup | Falha clara, sem arquivo parcial válido, backups anteriores intactos |
| Queda/encerramento durante backup | Próximo início detecta e descarta parcial |
| Queda durante restauração | Banco anterior preservado (cópia prévia) |
| Banco principal corrompido | Detecção (`integrity_check`) e caminho de restauração orientado |
| Backup corrompido | Verificação rejeita; usuário orientado ao anterior |
| Pasta de backup indisponível (unidade removida, rede) | Erro claro, sem travar a aplicação |
| Equipamento novo | Restauração a partir da cópia externa funciona seguindo a documentação |

## 10. Testes automatizados (exemplo genérico)

```python
import sqlite3

def test_backup_e_restauracao(tmp_path):
    origem = tmp_path / "origem.db"
    src = sqlite3.connect(origem)
    src.execute("create table t (id integer primary key, valor text)")
    src.executemany("insert into t (valor) values (?)", [("10.50",), ("20.25",)])
    src.commit()
    dst = sqlite3.connect(tmp_path / "backup.db")
    src.backup(dst)
    src.close()
    assert dst.execute("pragma integrity_check").fetchone()[0] == "ok"
    assert dst.execute("select count(*) from t").fetchone()[0] == 2
    dst.close()
```

## 11. Documentação para o usuário

- Onde ficam os backups, frequência, retenção, como fazer backup manual.
- Passo a passo de restauração (inclusive em equipamento novo) e o que conferir depois.
- Como copiar backups para fora do equipamento (3-2-1).
- Data do último drill de restauração e resultado.
