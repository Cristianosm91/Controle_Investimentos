# Modelo do relatório `qa-report/`

Referência dos entregáveis da skill `qa-application-auditor`. Gere os arquivos na raiz do
projeto auditado. Arquivo não aplicável ao modo → mantenha-o com uma linha
`Não aplicável no modo <modo>.` (não apague, para o leitor saber que foi considerado).

## Marcadores obrigatórios

Todo achado, resultado ou afirmação deve estar sob um destes marcadores — nunca misture:

| Marcador | Uso |
|---|---|
| **[EVIDÊNCIA]** | Fato confirmado por execução, saída de comando, log, métrica ou trecho de código citado (`arquivo:linha`) |
| **[HIPÓTESE]** | Suspeita baseada em leitura/heurística, ainda não reproduzida |
| **[RECOMENDAÇÃO]** | Ação sugerida (não aplicada) |
| **[EXECUTADO]** | Teste rodado, com resultado e referência à evidência |
| **[NÃO EXECUTADO]** | Teste não rodado — bloco completo obrigatório (abaixo) |
| **[LIMITAÇÃO]** | Restrição do ambiente que reduz a confiança da análise |
| **[RISCO RESIDUAL]** | O que continua podendo falhar após a análise/correção |

Bloco obrigatório para teste não executado:

```text
NÃO EXECUTADO
Motivo:
Dependência necessária:
Comando que seria utilizado:
Risco ainda não validado:
```

## Evidências

- Guarde em `qa-report/evidencias/` (logs, JSON e CSV dos scripts, diffs, prints anonimizados).
- Cite sempre: comando, código de retorno, duração e caminho do log.
- Trechos de saída: no máximo o necessário; **mascare** segredos e dados sensíveis.

---

## Conteúdo de cada arquivo

### 01-resumo-executivo.md
Parecer (uma das quatro classificações), modo executado, data, escopo, contagem de falhas por
criticidade, contagem de testes por status, 3–5 principais riscos e próximos passos. Uma página.

### 02-inventario-da-aplicacao.md
Resultado da Etapa 1 ([qa-checklist.md](qa-checklist.md#1-descoberta)), cada item com a fonte.
Inclua os comandos descobertos (instalar, build, executar, testar) e de onde vieram.

### 03-inventario-funcional.md
Funcionalidades, fluxos, regras de negócio (com `arquivo:linha`), entradas, saídas, integrações,
configurações, tratamento de erros, pontos críticos e a **baseline** (comandos, resultados,
métricas iniciais, ambiente).

### 04-plano-de-testes.md
Tabela do [../templates/test-plan.md](../templates/test-plan.md) com todos os cenários e status.

### 05-testes-executados.md
Para cada teste executado: ID, comando, início, duração, código de retorno, resultado,
evidência. Em seguida, **todos** os testes não executados com o bloco `NÃO EXECUTADO`.

### 06-falhas-encontradas.md
Uma seção por falha, no formato abaixo, ordenadas por criticidade.

### 07-riscos-de-estabilidade.md
Riscos de travamento, congelamento, vazamento e impacto na máquina — inclusive os **não**
confirmados (como hipóteses), com o teste que os confirmaria.

### 08-matriz-de-risco.md
Matriz do [../templates/risk-matrix.md](../templates/risk-matrix.md).

### 09-alteracoes-realizadas.md
Somente `fix`/`full`. Por alteração: falha relacionada (`QA-XXX`), arquivos e linhas, diff,
justificativa, teste antes/depois, como reverter. Sem alterações → "Nenhuma alteração realizada".

### 10-validacao-regressiva.md
Somente `fix`/`full`. Comparação antes × depois: testes (mesmo comando), métricas
(CPU/RSS/threads/handles/tempo), comportamento funcional. Qualquer diferença funcional é regressão
até prova em contrário.

### 11-parecer-final.md
Modelo [../templates/final-report.md](../templates/final-report.md).

---

## Formato de cada falha

```markdown
## QA-XXX - Título da falha

**Criticidade:** Crítica | Alta | Média | Baixa
**Status:** Confirmada | Suspeita | Não reproduzida
**Componente:**
**Arquivo e linha:**

### Descrição

### Evidência

### Passos para reprodução

### Resultado atual

### Resultado esperado

### Impacto

- CPU:
- Memória:
- Disco:
- Rede:
- Interface:
- Dados:

### Causa provável

### Correção recomendada

### Teste de validação

### Risco residual
```

Regras:
- **Confirmada** exige evidência de execução ou reprodução para falhas de comportamento
  (travamento, vazamento, lentidão, corrupção). Fatos estáticos verificáveis (ex.: credencial real
  versionada, entrada do usuário concatenada em SQL) podem ser confirmados citando o trecho exato.
  Fora disso, leitura de código = **Suspeita**.
- **Não reproduzida**: tentou-se reproduzir e não ocorreu — descreva a tentativa.
- Numeração `QA-001`, `QA-002`… estável entre execuções (não renumere falhas já reportadas).

## Regras do parecer

| Parecer | Condição objetiva |
|---|---|
| `APROVADO` | Todos os testes obrigatórios aplicáveis executados e aprovados; nenhuma falha Crítica ou Alta aberta |
| `APROVADO COM RESSALVAS` | Fluxos principais aprovados; há riscos conhecidos, testes bloqueados ou falhas Média/Baixa |
| `REPROVADO` | Falha Crítica, regressão funcional, risco grave de estabilidade, segurança ou perda de dados |
| `INCONCLUSIVO` | Testes essenciais não executados (ambiente, dependências, falta de evidência) |

- `REPROVADO` prevalece sobre os demais quando houver falha Crítica confirmada.
- Modo `review` sem execução de testes → no máximo `INCONCLUSIVO` (ou `REPROVADO`, se houver falha
  Crítica comprovada por evidência objetiva, ex.: credencial real versionada).
- Liste **todos** os testes não executados no parecer, sem exceção.
