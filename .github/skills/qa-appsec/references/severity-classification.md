# Classificação de severidade

## Dimensões separadas

- **Impacto:** efeito plausível sobre confidencialidade, integridade, disponibilidade, privacidade, negócio e obrigações.
- **Probabilidade:** exposição, pré-condições, privilégio, interação e controles existentes.
- **Severidade:** síntese contextual de impacto e probabilidade, não sinônimo de CVSS.
- **Confiança:** qualidade e completude da evidência de que a condição existe e é alcançável.

## Níveis

| Nível | Critério orientador |
|---|---|
| Crítica | Impacto sistêmico/grave: comprometimento amplo, privilégio máximo, exposição massiva ou interrupção crítica plausível. |
| Alta | Acesso indevido importante, exposição relevante, fraude, escalada ou falha grave de controle. |
| Média | Impacto limitado/condicionado, exposição parcial ou controle incompleto com mitigação existente. |
| Baixa | Alcance ou impacto reduzido; hardening preventivo de baixo risco. |
| Informativa | Contexto, controle positivo ou melhoria sem falha confirmada. |

Use o contexto do ativo, exposição, quantidade/sensibilidade de dados, alcance, esforço, automatização,
controles compensatórios, detecção e recuperação. Anote justificativa; não use soma mecânica.

## CVSS e confiança

Use CVSS somente se vetor e dados de entrada forem conhecidos; informe versão, vetor e limitações.
Não invente pontuação nem a use isoladamente para prioridade de negócio. Confiança `Alta | Média |
Baixa` deve refletir fonte, reprodução segura, contexto e incertezas, não a severidade.