# Relatório — Integrações Externas — <Aplicação>

**Modo executado:** review | test | fix
**Data:**
**Versão/commit:**
**Escopo:** (pastas/módulos analisados)
**Rede durante os testes:** bloqueada (obrigatório) | justificar

## 1. Resumo

| Severidade | Abertos | Corrigidos |
|---|---|---|
| Crítica | 0 | 0 |
| Alta | 0 | 0 |
| Média | 0 | 0 |
| Baixa | 0 | 0 |
| Informativa | 0 | 0 |

Conclusão em 3–5 linhas (sem declarar "aprovado" apenas com análise teórica).

## 2. Inventário de integrações

| ID | Provedor/fonte | Finalidade | Cliente/biblioteca | Formato | Gatilho | Frequência | Dado produzido | Persistência |
|---|---|---|---|---|---|---|---|---|
| I-01 | | | | | | | | |

## 3. Matriz de resiliência

Legenda: ✅ ok · ⚠️ parcial · ❌ ausente · N/A

| ID | Timeout | Retry/backoff | 429/Retry-After | Cooldown | Cache/TTL | Fonte+data exibidas | Fallback rotulado | Parsing validado | Sem dado≠erro≠zero | TLS ok | Não bloqueia loop | Testes contrato | Offline |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| I-01 | | | | | | | | | | | | | |

## 4. Jobs agendados

| Job | Trava | Coalesce/misfire | Fuso | Backoff | Status persistido | Observação |
|---|---|---|---|---|---|---|
| | | | | | | |

## 5. Achados

### INT-001 — <título curto>
- **Severidade:** Crítica | Alta | Média | Baixa | Informativa
- **Integração:** I-01
- **Tipo de evidência:** Teste executado | Análise teórica
- **Evidência:** `arquivo:linha`, trecho ou saída de teste (sem segredos)
- **Impacto:** o que o usuário vê / o que pode acontecer
- **Proposta:** mudança mínima sugerida (sem alterar regra de negócio)
- **Teste de regressão proposto:** cenário de contrato que falha hoje e deve passar
- **Requer decisão do usuário?** sim/não (ex.: mudar fonte, frequência, fallback)
- **Status:** Aberto | Em correção | Corrigido (commit/diff) | Aceito como risco | Não reproduzido

## 6. Testes

| ID | Integração | Cenário | Ferramenta | Status | Evidência |
|---|---|---|---|---|---|
| T-01 | I-01 | timeout | respx | executado/aprovado | evidencias/... |

Testes não executados (motivo, dependência, comando que seria usado, risco não validado):

| ID | Motivo | Dependência | Comando | Risco |
|---|---|---|---|---|

## 7. Alterações realizadas (modo fix)

Nenhuma | lista de arquivos, resumo do diff, teste antes (falha) × depois (passa).

## 8. Limitações

- [LIMITAÇÃO] …

## 9. Riscos residuais e próximos passos

- [RISCO RESIDUAL] …
- [RECOMENDAÇÃO] …

---
Gerado com a skill `integracoes-externas`. Válido apenas para a versão e os testes listados.
