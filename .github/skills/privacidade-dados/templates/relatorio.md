# Relatório — Privacidade de Dados — <Aplicação>

**Modo executado:** review | test | fix
**Data:**
**Versão/commit:**
**Escopo:** (backend, front-end, importadores, exportações, repositório)
**Declaração:** relatório técnico; não constitui parecer de conformidade legal.

## 1. Resumo

| Severidade | Abertos | Corrigidos |
|---|---|---|
| Crítica | 0 | 0 |
| Alta | 0 | 0 |
| Média | 0 | 0 |
| Baixa | 0 | 0 |
| Informativa | 0 | 0 |

Conclusão em 3–5 linhas (sem declarar "conforme" ou "aprovado" apenas com análise teórica).

## 2. Inventário de dados (sem valores reais)

| Entidade | Campo | Classificação | Finalidade | Obrigatório | Origem | Local de armazenamento | Exibido mascarado? | Exportado? | Coberto pela exclusão? |
|---|---|---|---|---|---|---|---|---|---|
| | | identificador / pessoal / financeiro / terceiro | | | | | | | |

## 3. Canais de saída

| Canal | Dados pessoais? | Mascarado? | Aviso/marcação? | Destino | Observação |
|---|---|---|---|---|---|
| UI | | | | | |
| Exportação CSV/XLSX/PDF | | | | | |
| Logs / erros | | | | | |
| Pacote de diagnóstico | | | | | |
| Chamadas externas | | | | | |
| Backups | | | | | |
| Temporários | | | | | |
| Área de transferência / impressão | | | | | |
| Telemetria | | | | | |

## 4. Matriz de exclusão

| Dado vinculado à pessoa | Removido? | Anonimizado? | Mecanismo (cascade/serviço) | Teste | Limitação |
|---|---|---|---|---|---|
| | | | | | Backups anteriores mantêm o dado até a retenção expirar |

## 5. Repositório e repouso

| Item | Situação | Evidência (sem abrir conteúdo) |
|---|---|---|
| Banco fora do repositório / ignorado | | |
| Planilhas, extratos, backups ignorados | | |
| Arquivos sensíveis já versionados | | `git ls-files` |
| Secret scanning | | |
| Local do banco / pasta sincronizada | | |
| Criptografia de disco recomendada | | |

## 6. Achados

### PRIV-001 — <título curto>
- **Severidade:** Crítica | Alta | Média | Baixa | Informativa
- **Área:** inventário | minimização | mascaramento | exportação | exclusão | repouso | fixtures | repositório | envio externo | temporários | telemetria
- **Tipo de evidência:** Teste executado | Análise teórica
- **Evidência:** `arquivo:linha`, caminho/tipo de arquivo ou saída de teste com dados fictícios
- **Impacto:**
- **Proposta:** mudança mínima (sem alterar o que é exibido/exportado/apagado sem pedido)
- **Teste de regressão proposto:**
- **Requer decisão do usuário?** sim/não
- **Status:** Aberto | Em correção | Corrigido (commit/diff) | Aceito como risco | Não reproduzido

## 7. Testes

| ID | Objetivo | Dados | Status | Evidência |
|---|---|---|---|---|
| T-01 | Exclusão em cascata | fictícios | | |

Testes não executados (motivo, dependência, comando, risco não validado):

| ID | Motivo | Dependência | Comando | Risco |
|---|---|---|---|---|

## 8. Alterações realizadas (modo fix)

Nenhuma | arquivos, resumo do diff, teste antes (falha) × depois (passa).

## 9. Limitações

- [LIMITAÇÃO] …

## 10. Riscos residuais e próximos passos

- [RISCO RESIDUAL] …
- [RECOMENDAÇÃO] …

---
Gerado com a skill `privacidade-dados`. Válido apenas para a versão e os testes listados; não
constitui parecer jurídico.
