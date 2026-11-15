---
name: calculos-financeiros-fiscais
description: 'Use ao auditar, testar ou validar cálculos financeiros e fiscais de uma aplicação (existentes ou novos) — precisão Decimal × float, arredondamento, câmbio, preço médio, eventos corporativos, rentabilidade (TWR, TIR/XIRR), taxas, regras tributárias com vigência, isenções, compensação de prejuízo, acúmulo de valor mínimo, calendário de dias úteis, testes de referência, testes de propriedade, conciliação e rastreabilidade — sem alterar fórmulas ou regras de negócio por conta própria. Modos review (padrão, somente leitura), test e fix. Palavras-gatilho: cálculo financeiro, cálculo fiscal, imposto, IR, alíquota, isenção, prejuízo a compensar, DARF, preço médio, rentabilidade, TWR, TIR, XIRR, arredondamento, Decimal, float, câmbio, cotação, desdobramento, bonificação, grupamento, dias úteis, feriados, vigência, teste de referência, golden test, hypothesis, conciliação.'
argument-hint: '[modo: review | test | fix] [caminho] [foco opcional]'
---

# Cálculos Financeiros e Fiscais

Valida a **correção, precisão e rastreabilidade** de cálculos financeiros e fiscais de uma
aplicação — os já existentes e os que forem adicionados — atuando como revisor técnico de
domínio. Objetivo: garantir que valores monetários, posições, rentabilidades e tributos sejam
calculados de forma **determinística, reproduzível, testada contra referências externas e
auditável**, **sem alterar fórmulas, regras de negócio ou funcionalidades por iniciativa própria**.

## Quando usar
- Revisar módulos de cálculo (posição, preço médio, rentabilidade, impostos, taxas, câmbio).
- Antes de liberar versão que toque cálculos, regras tributárias ou importação de movimentações.
- Criar testes de referência (golden), de propriedade (invariantes) e de conciliação.
- Avaliar o impacto de mudança na legislação/regra (nova alíquota, novo limite de isenção).
- Validar nova funcionalidade que produza ou consuma valores monetários.

## Quando NÃO usar
- Consultoria tributária ou interpretação jurídica definitiva (a skill aponta; o usuário/contador decide).
- Performance geral, vazamentos e travamentos → `qa-application-auditor`.
- Licenciamento, autenticação, multi-tenant, aspectos regulatórios/comerciais (fora de escopo).

---

## Princípios obrigatórios (inegociáveis)

1. **Não alterar regras de negócio, fórmulas, funcionalidades ou comportamento sem solicitação
   explícita do usuário.**
2. **Nunca "corrigir" uma fórmula porque parece errada.** Divergência vira **achado com evidência
   e proposta**; a regra é confirmada com o usuário e com fonte (legislação, documentação oficial,
   planilha validada, contador). Nada de correção silenciosa.
3. **Modo padrão `review` é somente leitura.**
4. **`fix` só com pedido explícito e confirmação**; mudanças mínimas, com teste que **falha antes
   e passa depois**; mostrar diff e justificar cada mudança.
5. **Diferenciar análise teórica de teste executado** — marcar `[TEÓRICO]` ou `[EXECUTADO]`.
6. **Nunca usar dados reais/pessoais em fixtures** (nomes, documentos, contas, carteiras reais):
   usar dados fictícios e valores sintéticos.
7. **Não usar o resultado do próprio código como referência** — o valor esperado vem de fonte
   independente.
8. **Informar limitações**: regra não confirmada, fonte ausente, período sem caso de referência,
   teste não executado.

---

## Modos de operação

Sem modo informado, use **`review`**. Pedido de "corrigir" sem modo → **confirme** antes de `fix`.

| Modo | Faz | Não faz |
|---|---|---|
| `review` (padrão) | Mapeia cálculos, tipos numéricos, arredondamentos, regras e vigências; aponta riscos; gera plano de testes | Não modifica arquivos |
| `test` | Executa testes existentes; cria testes de referência, propriedade e conciliação **em arquivos de teste próprios**; registra evidências | Não modifica código produtivo |
| `fix` | Corrige **apenas divergências confirmadas pelo usuário**, com teste que falha antes e passa depois; regressão completa | Não muda regra/fórmula sem confirmação; não refatora por estética |

---

## Fluxo de trabalho

1. **Descoberta** — localizar funções de cálculo, modelos com campos monetários (tipo e escala da
   coluna), parsers de importação, constantes numéricas (alíquotas, limites, datas), fontes de
   cotação/câmbio, calendário usado e testes existentes.
2. **Inventário de regras** — para cada cálculo: entradas, fórmula, unidade/moeda, ponto de
   arredondamento, **fonte da regra** e **vigência**. Regra sem fonte = `[A CONFIRMAR]`.
3. **Revisão técnica** — aplicar [references/checklist.md](references/checklist.md).
4. **Plano de testes** — casos de referência com origem documentada, invariantes para testes de
   propriedade, bordas (zero, limite exato ± 0,01, virada de mês/ano/vigência, feriado, fuso) e
   conciliação com fonte independente.
5. **Execução** (`test`/`fix`) — baseline da suíte existente, depois testes novos; guardar
   comandos e saídas.
6. **Correções** (somente `fix`, após confirmação) — uma divergência por vez: teste que reproduz →
   regra confirmada → mudança mínima → teste passa → regressão completa.
7. **Relatório** — [templates/relatorio.md](templates/relatorio.md) em
   `qa-report/calculos-financeiros-fiscais/`.

---

## Checklist

Detalhado em [references/checklist.md](references/checklist.md). Prioridades:
- `float` em valor monetário, ou `Decimal(float)` (usar `Decimal(str(x))`/string/centavos inteiros).
- Arredondamento no ponto errado (por linha × no total) ou modo implícito (`round()` bancário).
- Alíquotas/limites/datas **hardcoded** em vez de tabela de regras com `vigente_desde/vigente_ate`.
- Câmbio sem data de referência explícita (negócio × liquidação × fechamento).
- Eventos corporativos que não ajustam quantidade e preço médio de forma consistente.
- Ausência de "como foi calculado" e de aviso de estimativa ("conferir antes de pagar/declarar").

---

## Mudança de legislação/regra

1. **Não editar a regra antiga**: criar nova linha/versão com `vigente_desde`, encerrando a
   anterior com `vigente_ate`.
2. Selecionar a regra pela **data do fato gerador**, não pela data de execução.
3. Testes cobrindo **os dois períodos** e a **virada** (último dia antigo, primeiro dia novo).
4. Recalcular histórico só com pedido explícito; registrar fonte (norma, data de publicação).
5. Atualizar documentação funcional e o texto de transparência exibido ao usuário.

---

## Validação de novas funcionalidades

Toda funcionalidade que crie ou altere cálculo deve trazer:
- Especificação da regra com **fonte** e **vigência**; tipo numérico e escala definidos.
- Modo e ponto de arredondamento documentados.
- Testes unitários + **≥ 1 caso de referência** validado externamente + invariantes
  (property-based) quando aplicável + casos de borda.
- "Como foi calculado" (memória de cálculo) exposto e aviso de estimativa quando fiscal.
- Migração revisada por `migracoes-banco` quando mudar schema.
- Documentação funcional atualizada.
- Regressão completa; casos de referência existentes inalterados (ou mudança justificada e aprovada).

---

## Entregáveis

Em `qa-report/calculos-financeiros-fiscais/`:
- `relatorio.md` a partir de [templates/relatorio.md](templates/relatorio.md): inventário de regras,
  achados (ID `CFF-NNN`, severidade **Crítica/Alta/Média/Baixa/Informativa**, evidência, proposta,
  status), testes executados × não executados, limitações e parecer.
- Testes criados (somente em arquivos de teste) e evidências de execução.

Severidade: **Crítica** — valor financeiro/fiscal errado entregue ao usuário; **Alta** — erro em
borda plausível (limite, virada de vigência, evento corporativo); **Média** — precisão ou
arredondamento inconsistente sem impacto confirmado; **Baixa** — falta de rastreabilidade/aviso;
**Informativa** — melhoria.

---

## Integração com outras skills

- `prontidao-producao` — gate orquestrador que aciona esta skill e consolida o parecer.
- `qa-application-auditor` — estabilidade/performance dos cálculos em volume.
- `qa-appsec` — validação de entrada em importações.
- `software-engineering-refactoring` — isolar cálculos em funções puras testáveis, sem mudar resultado.
- `migracoes-banco` — tipo/escala de colunas monetárias; tabela de regras com vigência.
- `backup-recuperacao` — conciliação de totais antes/depois de restauração.
- `integracoes-externas` — cotações, câmbio, calendários e relatórios importados.
- `observabilidade-logs` — registrar versão da regra aplicada, sem dados pessoais.
- `privacidade-dados` — fixtures fictícias e mascaramento em relatórios.
- `testes-e2e` — fluxo importação → cálculo → exibição.
- `web-ux-acessibilidade` — exibição de valores, formatação e avisos.
- `documentacao-funcional` — regras, fontes, vigências e limitações.
- `ci-cd-release` — testes de referência obrigatórios no pipeline.
