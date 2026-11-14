# Checklist — Cálculos financeiros e fiscais

Use na revisão e no plano de testes. Cada item não atendido vira achado `CFF-NNN` com evidência
(arquivo:linha, saída de teste ou cálculo manual) e proposta — nunca correção silenciosa.

## 1. Precisão numérica

| Verificar | Risco | Como comprovar |
|---|---|---|
| Valores monetários em `float` (código, JSON, banco) | Erro acumulado (`0.1 + 0.2`) | Buscar `float(`, colunas `Float/REAL`; teste com somas longas |
| `Decimal(float)` em vez de `Decimal(str)` | Herda imprecisão binária | `Decimal(0.1) != Decimal("0.1")` |
| Contexto `Decimal` (precisão, `ROUND_*`) explícito e consistente | Resultado depende do ambiente | Localizar `getcontext()`/`quantize` |
| Coluna monetária com escala definida (`Numeric(p, s)`) | Truncamento/perda no banco | Modelos e migrações; SQLite não impõe escala |
| Serialização API → front preserva precisão (string ou centavos inteiros) | `number` JS perde dígitos | Teste de ida e volta |
| Quantidades fracionárias com escala própria | Arredondar quantidade como moeda | Escala por tipo de valor |
| Divisão por zero / posição zerada tratada | Exceção, `NaN`, `Infinity` | Caso de borda |

## 2. Arredondamento

- Regra documentada: **modo** (meio para cima, bancário, truncamento) e **onde** (por operação,
  por linha, no total, só na exibição).
- Python `round()` é bancário (`ROUND_HALF_EVEN`) — confirmar se é o desejado.
- Arredondar intermediários × só o final: diferenças de centavos documentadas.
- Valor formatado para exibição nunca é reutilizado como entrada de cálculo.
- Soma de parcelas arredondadas = total (ou diferença tratada explicitamente).

## 3. Câmbio e moedas

- Toda conversão registra **taxa, data da taxa e fonte**.
- Data aplicada definida pela regra (negócio, liquidação, fechamento do dia útil anterior).
- Taxa ausente na data → regra explícita (dia útil anterior ou erro), nunca a "taxa atual".
- Valor original + moeda armazenados junto do convertido.
- Nenhuma soma mistura moedas.

## 4. Posição e preço médio

- Compra: preço médio ponderado com/sem custos conforme regra documentada.
- Venda: não altera preço médio; resultado = (preço de venda − PM) × qtd − custos (conforme regra).
- Ordem das operações no mesmo dia documentada e testada.
- Operações de mesmo dia separadas quando a regra exigir.
- Venda acima da posição → erro/alerta, não posição negativa silenciosa (salvo regra explícita).
- Resultado independe da ordem de importação dos arquivos (quando a regra disser isso).

## 5. Eventos corporativos

| Evento | Quantidade | Preço médio | Custo total |
|---|---|---|---|
| Desdobramento N:1 | × N | ÷ N | inalterado |
| Grupamento 1:N | ÷ N (frações tratadas) | × N | inalterado |
| Bonificação | + bonificadas | recalculado com custo atribuído | + custo atribuído (conforme regra) |
| Troca de código/ticker | mantém | mantém | histórico vinculado |

- Data de referência (data-com/ex) correta; evento idempotente (não aplicado duas vezes).
- Tratamento de frações documentado.

## 6. Rentabilidade

- **TWR**: sub-períodos quebrados em cada aporte/resgate; neutraliza fluxos.
- **TIR/XIRR**: convenção de dias (365/252), sinal dos fluxos, chute inicial, máximo de iterações,
  ausência de solução e múltiplas raízes tratados.
- Proventos considerados conforme a definição exibida ao usuário.
- Carteira vazia, período sem fluxo e fluxo único não quebram.
- Casos comparados com planilha (`XIRR`/`XTIR`) como referência.

## 7. Taxas e custos

- Corretagem, emolumentos, liquidação, custódia, IOF etc. com **vigência** e fonte.
- Rateio de custos de uma nota entre ativos com regra e arredondamento documentados.
- Custo no preço médio × abatido no resultado conforme regra.

## 8. Tributos

- Alíquotas, limites de isenção, códigos de recolhimento e prazos em **tabela de regras com
  `vigente_desde`/`vigente_ate`**, nunca constantes soltas.
- Regra escolhida pela **data do fato gerador**.
- Isenção aplicada sobre o critério correto (ex.: total de **vendas** do mês × lucro) e por
  categoria; testar limite exato e limite + 0,01.
- Categorias separadas (operação comum, mesmo dia, outros tipos) quando a regra exigir.
- **Compensação de prejuízo**: saldo por categoria, transportado entre meses/anos conforme regra,
  sem compensar categorias não permitidas; saldo exibido ao usuário.
- **Valor mínimo de recolhimento**: imposto abaixo do mínimo acumula para meses seguintes; testar
  acúmulo em vários meses e a quitação.
- Imposto retido na fonte deduzido sem dupla contagem.
- Aviso visível: "valores estimados; conferir antes de pagar/declarar".

## 9. Calendário e tempo

- Dias úteis/feriados de fonte versionada (inclui feriados móveis).
- Datas sem ambiguidade de fuso (data local da operação × UTC).
- Virada de mês/ano, ano bissexto.
- `today()`/`now()` injetável em testes (sem depender do relógio real).

## 10. Testes

| Tipo | Exigência |
|---|---|
| Referência (golden) | Valor esperado de **fonte externa** (planilha validada, contador, documentação oficial, extrato fictício); origem citada no teste |
| Propriedade (`hypothesis` ou equivalente) | Invariantes: comprar e vender tudo zera posição; desdobrar e grupar na mesma razão volta ao original; soma de rateios = total; TWR sem fluxos = retorno simples; custo total preservado em eventos |
| Borda | Zero, limite exato ± 0,01, virada de vigência, feriado, fuso |
| Regressão | Casos de referência não mudam sem justificativa aprovada |
| Conciliação | Totais comparados com fonte independente (relatório da bolsa, extrato, informe) com tolerância documentada |

## 11. Rastreabilidade e transparência

- "Como foi calculado": entradas, regra/versão aplicada, vigência, arredondamentos.
- Versão da regra registrada junto ao resultado persistido.
- Logs sem dados pessoais (ver `privacidade-dados`).
