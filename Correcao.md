Conciliação da planilha Cris v7.0 DLP: aprendizados

Como as abas medem coisas diferentes

Portfolio, “valor investido”: custo das posições abertas, ou seja, qtd_atual × pm_atual da última linha de cada ticker na Op.Normal.
Histórico.Consolidado: soma da coluna volume ou fluxo_caixa da Op.Normal. Isso mostra o dinheiro que saiu do bolso, não o custo do que sobrou.
Relação entre elas: fluxo_caixa (sem IR) − resultado realizado (swing + day trade) = custo das posições do Portfolio.
volume: é bruto (sem taxas) e vale 0 em amortizações e cisões. fluxo_caixa: desconta taxas e inclui amortizações, mas não abate o IR retido. A coluna lucro também ignora o IR.

Quais eventos movimentam dinheiro de verdade

Contam: C, V, V.SUB, AM e DT.
Não contam: BN (bonificação, que a planilha lança como saída sem você ter pago), CISÃO, AT (troca de ticker) e S/I (grupamento).

Erros achados e corrigidos

BRDT3 → VBBR3 e VVAR3 → VIIA3: a entrada do novo ticker estava como C (compra), duplicando R$ 4.338,40 no fluxo. O certo é AT nas duas pontas.
VICI (16/09/2025): compra lançada em BRL com preço em dólar, custo subestimado em cerca de R$ 994. O certo é USD.
INBR31 → INTR: o custo perdia cerca de R$ 98 porque as AT usavam preço diferente do preço médio. A correção foi lançar a entrada do INTR em USD, com preço USD = PM do ticker antigo em BRL ÷ PTAX da linha, uma PTAX por linha.
XPBR31 (cisão do ITUB4): a entrada das ações recebidas não deve ser C. A fração leiloada vira uma venda (V) com o valor recebido.

Regras práticas para lançar

Troca de ticker: use AT nas duas pontas, com o preço médio do ticker antigo como preço, para o fluxo zerar e o custo ser herdado certo.
Ativo em dólar: moeda USD, com preço em dólar e a PTAX do dia da linha.
Day trade: evento DT, que não aparece na Op.Normal normal e precisa entrar na fórmula.

Fórmula do dinheiro líquido que saiu do bolso (confira as letras das colunas na sua aba):

=SUMIFS(Q5:Q1288;C5:C1288;"C")+SUMIFS(Q5:Q1288;C5:C1288;"V")+SUMIFS(Q5:Q1288;C5:C1288;"V.SUB")+SUMIFS(Q5:Q1288;C5:C1288;"AM")+SUMIFS(Q5:Q1288;C5:C1288;"DT")-SUM(H5:H1288)

Resultado final conciliado

Visão	R$
Saiu do bolso (com day trade e IR)	700.124,74
Caixa ainda preso na carteira	685.192,63
Custo das posições (Portfolio)	691.277,00

A diferença entre o seu número com bonificações (691.287,41) e o Portfolio é de R$ 10,41: R$ 6,22 de IR (não entra no custo) mais R$ 4,19 de arredondamento de preço médio. Não há mais erro de lançamento a procurar.

Pendências e ressalvas

Proventos: R$ 146.034,70 no Portfolio ficam fora desses números. Para o caixa líquido de verdade, subtraia-os.
MRFG3 → MBRF3: o preço lançado (7,51) é diferente do PM (7,5188). O efeito é de cerca de R$ 9,70, ainda não confirmado se foi ajustado.
IR: para o imposto de renda real (fração de cisão, BDR que virou ação estrangeira), confirme com seu contador.