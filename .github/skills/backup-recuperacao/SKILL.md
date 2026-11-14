---
name: backup-recuperacao
description: 'Use ao auditar, testar ou validar backup e recuperação de dados de uma aplicação — definição de RPO/RTO, backups automáticos e manuais, retenção, verificação de integridade (PRAGMA integrity_check, pg_restore --list), testes periódicos de restauração em ambiente isolado, cópia antes de restaurar, restauração de backups de versões antigas do schema, criptografia e local de armazenamento, regra 3-2-1, backup de configuração, validação pós-restauração por contagens/somatórios, concorrência durante backup/restore e cenários de desastre — sem alterar regras de negócio por conta própria. Modos review (padrão, somente leitura), test e fix. Palavras-gatilho: backup, cópia de segurança, restauração, restore, recuperação, RPO, RTO, retenção, integrity_check, pg_dump, pg_restore, VACUUM INTO, sqlite backup API, 3-2-1, disaster recovery, desastre, banco corrompido, disco cheio, teste de restauração.'
argument-hint: '[modo: review | test | fix] [caminho] [foco opcional]'
---

# Backup e Recuperação

Valida se uma aplicação **consegue de fato recuperar os dados do usuário** — não apenas se gera
arquivos de backup. Objetivo: garantir backups consistentes, verificados, retidos e armazenados com
segurança, restauração testada e documentada, com metas de perda (RPO) e tempo (RTO) explícitas —
**sem alterar regras de negócio, funcionalidades ou dados por iniciativa própria**.

## Quando usar
- Revisar rotinas de backup/restauração existentes ou recém-adicionadas.
- Antes de liberar versão que altere schema, local de dados ou rotina de backup.
- Executar teste de restauração (drill) em ambiente isolado.
- Investigar backup corrompido, restauração falha ou perda de dados.

## Quando NÃO usar
- Escrever migrações de schema → `migracoes-banco` (esta skill valida a restauração de backups antigos que migram).
- Infraestrutura corporativa de backup (servidores, políticas de TI) — apenas recomendações.
- Licenciamento, autenticação, multi-tenant, aspectos regulatórios/comerciais (fora de escopo).

---

## Princípios obrigatórios (inegociáveis)

1. **Não alterar regras de negócio, fórmulas, funcionalidades ou comportamento sem solicitação
   explícita do usuário.**
2. **Divergência encontrada vira achado com evidência e proposta**, nunca correção silenciosa.
3. **Modo padrão `review` é somente leitura** — não gerar, apagar, mover nem restaurar backups reais.
4. **`fix` só com pedido explícito e confirmação**; mudanças mínimas, com teste que **falha antes e
   passa depois**.
5. **Nunca restaurar sobre os dados reais do usuário** em teste: restaurar em **diretório/instância
   isolada**; antes de qualquer restauração real, **cópia do estado atual**.
6. **Nunca apagar backups existentes** (nem aplicar retenção) sem confirmação explícita.
7. **Diferenciar análise teórica de teste executado** (`[TEÓRICO]` / `[EXECUTADO]`). Backup sem
   restauração testada **não** é considerado válido.
8. **Nunca usar dados reais/pessoais em fixtures**: usar bancos com dados fictícios.
9. **Não expor conteúdo de backups** (dados pessoais/financeiros) em relatórios ou logs.
10. **Informar limitações** (ambiente sem SGBD, sem espaço, sem backup antigo de exemplo).

---

## Modos de operação

Sem modo informado, use **`review`**. Pedido de "corrigir" sem modo → **confirme** antes de `fix`.

| Modo | Faz | Não faz |
|---|---|---|
| `review` (padrão) | Mapeia dados a proteger, rotinas, gatilhos, destino, retenção, integridade, restauração e documentação; avalia RPO/RTO | Não executa backup/restore; não modifica arquivos |
| `test` | Com dados fictícios em diretório isolado: gera backup, verifica integridade, restaura, valida contagens/somatórios, simula desastres; cria testes **em arquivos próprios** | Não toca dados/backups reais; não altera código produtivo |
| `fix` | Ajuste mínimo confirmado (ex.: verificação de integridade, cópia antes de restaurar), com teste que falha antes e passa depois | Não muda retenção/destino sem confirmação; não apaga backups |

---

## Fluxo de trabalho

1. **Descoberta** — o que precisa ser protegido (banco, anexos, configuração, chaves), onde fica,
   SGBD, mecanismo atual (cópia de arquivo, API de backup, `VACUUM INTO`, `pg_dump`), gatilhos
   (agendado, antes de migrar, manual), destino, retenção, criptografia, procedimento de restauração.
2. **Metas** — registrar ou propor **RPO** (perda máxima aceitável) e **RTO** (tempo máximo para
   voltar a operar); metas não definidas = achado e pergunta ao usuário.
3. **Revisão** — aplicar [references/checklist.md](references/checklist.md): consistência,
   integridade, retenção, armazenamento/3-2-1, criptografia, configuração, concorrência,
   restauração, documentação.
4. **Plano de testes** — drill de restauração, backup de versão antiga do schema, validação
   antes/depois, cenários de desastre.
5. **Execução** (`test`/`fix`) — tudo em diretório temporário isolado com dados fictícios;
   medir tempo de backup e restauração (comparar com RTO).
6. **Correções** (somente `fix`, após confirmação) — mudança mínima, teste, regressão.
7. **Relatório** — [templates/relatorio.md](templates/relatorio.md) em `qa-report/backup-recuperacao/`.

---

## Checklist

Detalhado em [references/checklist.md](references/checklist.md). Prioridades:
- Cópia de arquivo de banco **aberto** (SQLite com WAL, PostgreSQL em execução) → backup inconsistente.
  Usar API de backup / `VACUUM INTO` / `pg_dump`.
- Backup nunca verificado (`PRAGMA integrity_check`, `pg_restore --list`) nem restaurado em teste.
- Backup só no mesmo disco/pasta do banco; banco aberto em pasta sincronizada na nuvem.
- Restauração sobrescreve o banco atual sem cópia prévia nem validação.
- Backup de schema antigo não migra para a versão atual ao ser restaurado.
- Ausência de procedimento documentado para o usuário.

---

## Validação de novas funcionalidades

Toda funcionalidade que crie novos dados persistidos, arquivos, configurações ou altere schema deve:
- Garantir que os novos dados/arquivos **entram no backup** e **voltam na restauração**.
- Manter backup automático antes de migrações (ver `migracoes-banco`).
- Incluir teste: criar dados fictícios → backup → restaurar em diretório isolado → comparar
  contagens/somatórios/hashes.
- Testar restauração de backup gerado pela **versão anterior** na versão nova.
- Atualizar documentação do procedimento de backup/restauração e RPO/RTO se impactados.

---

## Entregáveis

Em `qa-report/backup-recuperacao/`:
- `relatorio.md` a partir de [templates/relatorio.md](templates/relatorio.md): inventário de dados
  protegidos, RPO/RTO (meta × medido), resultado dos drills, achados (ID `BKP-NNN`, severidade
  **Crítica/Alta/Média/Baixa/Informativa**, evidência, proposta, status), limitações e parecer.
- Testes criados e evidências (comandos, tempos, contagens antes/depois — sem conteúdo dos dados).

Severidade: **Crítica** — dados não recuperáveis (backup inconsistente, restauração falha,
inexistente); **Alta** — backup único no mesmo disco, sem verificação, restauração sem cópia
prévia, backup antigo não migra; **Média** — retenção indefinida, RPO/RTO sem meta, sem
criptografia onde necessário; **Baixa** — documentação incompleta; **Informativa** — melhoria.

---

## Integração com outras skills

- `prontidao-producao` — gate orquestrador que aciona esta skill e consolida o parecer.
- `migracoes-banco` — backup antes de migrar; backups antigos migrando para `head`.
- `calculos-financeiros-fiscais` — somatórios financeiros como critério de validação pós-restauração.
- `qa-application-auditor` — disco cheio, concorrência, tempo de backup em volume.
- `qa-appsec` — criptografia, permissões e local dos arquivos de backup.
- `privacidade-dados` — retenção, descarte e exposição de dados pessoais em backups.
- `observabilidade-logs` — registro de sucesso/falha de backups e alertas.
- `ci-cd-release` — teste de restauração automatizado no pipeline.
- `testes-e2e` — fluxo de backup/restauração pela interface.
- `web-ux-acessibilidade` — confirmação clara antes de restaurar e feedback de progresso.
- `documentacao-funcional` — procedimento de backup/restauração para o usuário.
- `software-engineering-refactoring` — isolar rotina de backup testável.
