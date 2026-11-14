# Matriz de risco — <Aplicação>

## Escalas

**Probabilidade** — Alta: ocorre no uso normal · Média: ocorre em condições específicas
(volume, concorrência, falha de dependência) · Baixa: exige combinação rara de fatores.

**Impacto** — usa a classificação de criticidade da skill: Crítico · Alto · Médio · Baixo.

## Mapa

| Probabilidade \ Impacto | Baixo | Médio | Alto | Crítico |
|---|---|---|---|---|
| **Alta** | Média | Alta | Crítica | Crítica |
| **Média** | Baixa | Média | Alta | Crítica |
| **Baixa** | Baixa | Baixa | Média | Alta |

Posicione os IDs nas células (ex.: `R-001`, `R-004` em Alta × Crítico).

| Probabilidade \ Impacto | Baixo | Médio | Alto | Crítico |
|---|---|---|---|---|
| **Alta** | | | | |
| **Média** | | | | |
| **Baixa** | | | | |

## Riscos

| ID | Risco | Falha relacionada | Origem | Probabilidade | Impacto | Nível | Recursos afetados | Mitigação recomendada | Status |
|---|---|---|---|---|---|---|---|---|---|
| R-001 | | QA-XXX | Evidência / Hipótese | Alta / Média / Baixa | Crítico / Alto / Médio / Baixo | | CPU, Memória, Disco, Rede, Interface, Dados, Segurança | | Aberto / Mitigado / Aceito |

Notas:
- **Origem = Hipótese** indica risco ainda não comprovado; informe o teste que o confirmaria.
- **Aceito** só com decisão registrada do usuário/responsável.
