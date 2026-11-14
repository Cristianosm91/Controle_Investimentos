# Relatório — Observabilidade e Logs — <Aplicação>

**Modo executado:** review | test | fix
**Data:**
**Versão/commit:**
**Escopo:** (backend, front-end, jobs, empacotamento)

## 1. Resumo

| Severidade | Abertos | Corrigidos |
|---|---|---|
| Crítica | 0 | 0 |
| Alta | 0 | 0 |
| Média | 0 | 0 |
| Baixa | 0 | 0 |
| Informativa | 0 | 0 |

Conclusão em 3–5 linhas (sem declarar "aprovado" apenas com análise teórica).

## 2. Mapa de logging

| Item | Situação atual | Evidência |
|---|---|---|
| Onde é configurado | | |
| Formato / correlation id | | |
| Nível padrão / configurável | | |
| Destino dos arquivos (fora de pasta sincronizada?) | | |
| Rotação / limite | | |
| Mascaramento | | |
| Loggers de terceiros | | |

## 3. Pontos de erro

| Local (`arquivo:linha`) | Padrão | Loga? | Sinaliza ao usuário/status? | Observação |
|---|---|---|---|---|
| | `except Exception: pass` | | | |

## 4. Saúde, status e suporte

| Item | Existe? | Observação |
|---|---|---|
| Health (liveness) | | |
| Readiness com dependências | | |
| Versão exposta / log de startup | | |
| Status de jobs persistido e visível | | |
| Métricas de duração | | |
| Error boundary (front) | | |
| Pacote de diagnóstico sem dados pessoais | | |
| Runbook | | |

## 5. Achados

### OBS-001 — <título curto>
- **Severidade:** Crítica | Alta | Média | Baixa | Informativa
- **Área:** configuração | dados em log | rotação | erro backend | health | jobs | métricas | front | diagnóstico | runbook
- **Tipo de evidência:** Teste executado | Análise teórica
- **Evidência:** `arquivo:linha`, trecho **mascarado** ou saída de teste
- **Impacto:**
- **Proposta:** mudança mínima (sem alterar textos/fluxos visíveis sem pedido)
- **Teste de regressão proposto:**
- **Requer decisão do usuário?** sim/não
- **Status:** Aberto | Em correção | Corrigido (commit/diff) | Aceito como risco | Não reproduzido

## 6. Testes

| ID | Objetivo | Ferramenta | Status | Evidência |
|---|---|---|---|---|
| T-01 | Log não contém CPF | pytest `caplog` | | |

Testes não executados (motivo, dependência, comando, risco não validado):

| ID | Motivo | Dependência | Comando | Risco |
|---|---|---|---|---|

## 7. Alterações realizadas (modo fix)

Nenhuma | arquivos, resumo do diff, teste antes (falha) × depois (passa).

## 8. Limitações

- [LIMITAÇÃO] …

## 9. Riscos residuais e próximos passos

- [RISCO RESIDUAL] …
- [RECOMENDAÇÃO] …

---
Gerado com a skill `observabilidade-logs`. Válido apenas para a versão e os testes listados.
