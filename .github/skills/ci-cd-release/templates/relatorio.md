# Relatório — CI/CD e Release — <Aplicação>

**Modo executado:** review | test | fix
**Data:**
**Versão/commit avaliado:**
**Plataforma Git:** GitHub | GitLab | outra
**Ambiente:** SO, versões de Python/Node, runner (local/CI)

## Resumo

- Pipeline versionado: sim | não (motivo) | ignorado pelo `.gitignore`
- Paridade local × CI: completa | parcial | inexistente
- Achados: Crítica 0 · Alta 0 · Média 0 · Baixa 0 · Informativa 0

## Paridade local × CI

| Comando local (fonte) | Job/step no CI | Mesmos argumentos? | Status |
|---|---|---|---|
| `python -m ruff check .` (script local) | `backend › Lint` | sim | OK |
| | | | |

## Portões

| Portão | Presente | Bloqueia merge | Executado nesta análise | Resultado |
|---|---|---|---|---|
| Lint | | | | |
| Tipos | | | | |
| Testes | | | | |
| Migrações | | | | |
| Build | | | | |
| Smoke E2E | | | | |
| Auditoria de dependências | | | | |
| Varredura de segredos | | | | |
| SBOM (opcional) | | | | |

## Achados

| ID | Severidade | Título | Evidência (arquivo:linha / comando + saída) | Proposta | Status |
|---|---|---|---|---|---|
| CI-001 | Crítica/Alta/Média/Baixa/Informativa | | | | Aberto · Proposto · Aceito · Corrigido · Recusado |

### CI-001 — <título>
- **Tipo:** Evidência confirmada | Hipótese
- **Evidência:**
- **Impacto:**
- **Proposta (mudança mínima):**
- **Requer confirmação do usuário:** sim/não
- **Status:**

## Release

| Item | Situação | Evidência |
|---|---|---|
| Versão em fonte única | | |
| CHANGELOG atualizado | | |
| Tag `vX.Y.Z` | | |
| Artefatos + checksum | | |
| Notas de release | | |

## Testes não executados

| Item | Motivo | Dependência necessária | Comando que seria utilizado | Risco não validado |
|---|---|---|---|---|

## Alterações realizadas (somente `fix`)

Nenhuma | lista de arquivos + diff em `evidencias/`.

## Limitações

- [LIMITAÇÃO] …

---
Gerado com a skill `ci-cd-release`. Vale apenas para a versão e o ambiente listados.
