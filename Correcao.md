Analise as alterações realizadas nesta branch e conclua ou corrija a implementação considerando integralmente os requisitos e as regras de negócio descritos abaixo.

O objetivo é:

1. Finalizar a compatibilidade com o novo modelo de importação.
2. Disponibilizar esse novo modelo na funcionalidade de modelos para download.
3. Corrigir e validar o cálculo do Valor Investido.
4. Manter separadas as métricas de Valor Investido e Valor Investido em Posições Abertas.
5. Garantir o tratamento correto de compras, vendas, taxas, impostos, amortizações, bonificações, cisões e operações de Day Trade.
6. Preservar as funcionalidades e os modelos de importação já existentes.
7. Evitar regressões e duplicidade de regras financeiras.

# 1. Análise inicial obrigatória

Antes de alterar o código:

1. Compare a branch atual com sua branch de origem.
2. Analise o diff completo.
3. Identifique quais alterações já foram implementadas.
4. Não refaça desnecessariamente o que já estiver correto.
5. Não reverta alterações válidas realizadas nesta branch.
6. Identifique onde estão implementados atualmente:
   - importação dos arquivos;
   - modelos disponíveis para download;
   - classificação dos eventos;
   - cálculo do Valor Investido;
   - cálculo do Valor Realizado;
   - cálculo do custo das posições abertas;
   - cálculo das compras e vendas;
   - tratamento de taxas, impostos e IR;
   - tratamento de amortizações;
   - tratamento de bonificações;
   - tratamento de cisões;
   - tratamento de operações de Day Trade;
   - indicadores exibidos no Portfolio.
7. Identifique semanticamente o que cada campo, variável, método e indicador representa antes de alterar as fórmulas.
8. Verifique se existem regras financeiras duplicadas entre:
   - importação;
   - serviços;
   - domínio;
   - componentes;
   - tela de Portfolio;
   - dashboards;
   - relatórios.
9. Sempre que possível, mantenha uma única fonte de verdade para cada cálculo.
10. Preserve a arquitetura, os padrões, a nomenclatura e as convenções já adotadas pelo projeto.

# 2. Novo modelo de importação

Nesta branch foi adicionada compatibilidade com um novo modelo ou formato de importação.

Valide se essa implementação está completa e corretamente integrada ao restante da aplicação.

O novo modelo também precisa estar disponível na funcionalidade de modelos para download, seguindo o mesmo padrão dos modelos já existentes.

Garanta que:

- o novo formato seja reconhecido corretamente;
- o arquivo possa ser importado;
- os campos sejam interpretados corretamente;
- os tipos de eventos sejam classificados corretamente;
- as taxas, os impostos e demais valores sejam importados corretamente;
- o modelo correspondente esteja disponível para download;
- o arquivo disponibilizado para download possua estrutura válida para importação;
- os modelos anteriores continuem funcionando;
- os modelos antigos permaneçam disponíveis para download;
- a inclusão do novo formato não introduza regressões;
- mensagens de validação e erro continuem claras e consistentes.

Não crie um fluxo totalmente separado se o novo formato puder aproveitar e estender a estrutura de importação existente.

# 3. Conceitos financeiros que devem permanecer separados

A aplicação deve separar claramente os seguintes conceitos:

## 3.1. Volume movimentado

Representa o valor bruto associado a um evento ou operação.

O fato de um evento possuir um valor monetário não significa automaticamente que houve entrada ou saída de dinheiro.

## 3.2. Fluxo de caixa

Representa o dinheiro que efetivamente entrou ou saiu do bolso do investidor.

Somente eventos com movimentação financeira real devem afetar o fluxo de caixa.

## 3.3. Valor Investido

Representa o capital líquido efetivamente aportado pelo investidor, considerando o fluxo financeiro real acumulado.

Em termos conceituais:

Valor Investido =
todas as saídas financeiras relacionadas aos investimentos
menos
todas as entradas financeiras que retornaram ao investidor

O cálculo deve considerar valores líquidos, incluindo taxas, impostos, IR e demais custos financeiros aplicáveis.

## 3.4. Valor Realizado

Representa a parcela de custo ou resultado já realizada por meio dos eventos encerrados, conforme a regra financeira adotada pela aplicação.

Antes de alterar essa métrica, identifique exatamente sua finalidade e como ela é utilizada atualmente.

Não confunda:

- valor recebido em uma venda;
- lucro ou prejuízo;
- custo realizado;
- valor bruto negociado;
- fluxo de caixa.

## 3.5. Valor Investido em Posições Abertas

Representa o custo que ainda permanece associado às posições atualmente abertas.

Essa métrica não representa necessariamente o mesmo valor do fluxo financeiro líquido acumulado.

Eventos sem movimentação de caixa podem modificar o custo das posições abertas.

# 4. Regra do Valor Investido

O indicador Valor Investido deve representar exclusivamente o capital líquido que efetivamente saiu do bolso do investidor.

Não confunda Valor Investido com:

- valor bruto das operações;
- volume negociado;
- custo das posições abertas;
- patrimônio atual;
- valor de mercado;
- lucro ou prejuízo;
- Valor Realizado.

Um evento pode alterar quantidade, volume ou custo sem representar entrada ou saída de dinheiro.

# 5. Tratamento dos eventos

## 5.1. Compra

Uma compra representa saída de dinheiro.

O Valor Investido deve aumentar considerando:

valor da compra + taxas + demais custos financeiros associados à compra

Exemplo:

- Valor da compra: R$ 100,00
- Taxas: R$ 0,20
- Total efetivamente desembolsado: R$ 100,20

Impactos esperados:

- Fluxo de caixa: saída de R$ 100,20
- Valor Investido: aumenta R$ 100,20
- Custo da posição: aumenta conforme o custo total da compra

## 5.2. Venda

Uma venda representa entrada de dinheiro e deve reduzir o Valor Investido pelo valor líquido efetivamente recebido.

O cálculo deve considerar:

valor bruto da venda
menos taxas
menos impostos
menos IR
menos demais custos associados à venda

Exemplo:

- Valor bruto da venda: R$ 100,00
- Taxa: R$ 0,20
- IR: R$ 0,10
- Valor líquido recebido: R$ 99,70

Impactos esperados:

- Fluxo de caixa: entrada de R$ 99,70
- Valor Investido: reduz R$ 99,70
- Custo da posição: reduz conforme o custo realizado da quantidade vendida

Não utilize simplesmente o valor bruto da venda para reduzir o Valor Investido.

Também não confunda o valor líquido recebido com o custo realizado da posição. São conceitos diferentes e podem possuir valores diferentes.

## 5.3. Amortização

Amortização representa devolução de capital ao investidor.

Impactos esperados:

- Fluxo de caixa: entrada de dinheiro
- Valor Investido: reduz pelo valor efetivamente recebido
- Custo da posição: deve ser ajustado conforme a regra financeira aplicável

A amortização não deve ser tratada apenas como rendimento ou volume movimentado, pois representa retorno de parte do capital investido.

## 5.4. Bonificação

Bonificação não representa desembolso financeiro.

Mesmo que o evento possua um valor monetário informado:

- não deve aumentar o Valor Investido;
- não deve reduzir o Valor Investido;
- não deve ser considerada dinheiro que saiu do bolso;
- não deve ser considerada entrada de dinheiro;
- pode alterar quantidade;
- deve alterar o custo da posição conforme o valor de custo atribuído ao evento.

Exemplo:

- Bonificação registrada com valor de R$ 100,00
- Impacto no Fluxo de Caixa: R$ 0,00
- Impacto no Valor Investido: R$ 0,00
- Impacto no custo da posição: aumenta R$ 100,00, caso esse seja o custo atribuído ao evento

O valor informado na bonificação representa custo atribuído, e não dinheiro desembolsado pelo investidor.

## 5.5. Cisão

Cisão não representa, por si só, movimentação de caixa.

Impactos esperados:

- Fluxo de caixa: não altera
- Valor Investido: não altera
- Custo da posição: reduz pelo custo transferido ou pelo valor correspondente ao evento
- Quantidade e distribuição entre ativos: devem seguir a regra existente ou aplicável ao evento

A cisão deve ser tratada como um evento de transferência, redistribuição ou redução de custo, sem ser interpretada automaticamente como entrada ou saída de dinheiro.

## 5.6. Day Trade

Operações de Day Trade também devem refletir o fluxo financeiro real.

Na compra de Day Trade:

- existe saída de dinheiro;
- o Valor Investido aumenta pelo valor da compra mais taxas e custos.

Na venda de Day Trade:

- existe entrada de dinheiro;
- o Valor Investido reduz pelo valor líquido recebido;
- devem ser descontados taxas, impostos, IR e demais custos.

Não trate Day Trade apenas como volume negociado.

Mesmo quando a compra e a venda ocorrerem no mesmo dia, devem ser considerados os valores líquidos efetivamente movimentados.

Ao final da operação, verifique se permaneceu ou não alguma posição aberta e trate separadamente:

- fluxo de caixa;
- resultado realizado;
- custo remanescente;
- taxas e impostos.

# 6. Portfolio: duas visões obrigatórias

Na tela de Portfolio, devem existir duas métricas distintas:

1. Valor Investido
2. Valor Investido em Posições Abertas

Essas métricas não devem ser consolidadas em um único indicador e não devem ser tratadas como sinônimos.

## 6.1. Valor Investido

Deve representar o capital líquido efetivamente aportado considerando o fluxo financeiro real da carteira.

Deve responder à pergunta:

“Quanto dinheiro líquido efetivamente saiu do meu bolso para os investimentos, considerando também os valores que já retornaram?”

Esse indicador deve considerar:

- compras;
- vendas;
- taxas;
- impostos;
- IR;
- amortizações;
- operações de Day Trade;
- demais eventos com movimentação financeira efetiva.

Bonificações e cisões não devem alterar esse indicador porque não movimentam caixa.

## 6.2. Valor Investido em Posições Abertas

Deve representar quanto do custo permanece associado aos ativos e às posições que continuam abertas.

Deve responder à pergunta:

“Quanto do custo ainda está alocado nas posições que permanecem na minha carteira?”

A aplicação atualmente apresenta um valor calculado de forma equivalente a:

Valor Investido - Valor Realizado

Não remova essa visão.

Caso essa fórmula represente corretamente o custo das posições abertas, mantenha-a e apresente o resultado separadamente como:

“Valor Investido em Posições Abertas”

Entretanto, não assuma que essa fórmula está correta apenas porque corresponde à implementação atual.

Primeiro identifique:

- o significado atual de Valor Investido;
- o significado atual de Valor Realizado;
- se o cálculo utiliza fluxo de caixa ou custo da posição;
- como bonificações e cisões são incorporadas;
- como vendas parciais e totais afetam o cálculo;
- como taxas e impostos são tratados.

Se a implementação atual estiver misturando fluxo de caixa com custo, separe os cálculos.

# 7. Regra crítica sobre as duas métricas

Não assuma automaticamente que:

Valor Investido em Posições Abertas =
Valor Investido - Valor Realizado

é uma fórmula universalmente correta.

Essa fórmula só deve ser mantida se, após a análise da implementação e dos cenários de teste, representar corretamente o custo das posições abertas.

O motivo é que existem eventos que:

- alteram o custo sem movimentar caixa;
- movimentam caixa sem possuir o mesmo impacto sobre o custo;
- possuem valor bruto diferente do valor líquido;
- afetam quantidade e custo de formas diferentes.

Exemplos importantes:

Bonificação:

- não altera o Valor Investido;
- não movimenta caixa;
- pode aumentar o custo da posição aberta.

Cisão:

- não altera o Valor Investido;
- não movimenta caixa;
- pode reduzir ou redistribuir o custo da posição aberta.

Venda:

- reduz o Valor Investido pelo valor líquido recebido;
- reduz o custo da posição pelo custo realizado;
- o valor líquido recebido e o custo realizado não são necessariamente iguais.

Portanto:

- cálculos de caixa devem utilizar somente eventos que efetivamente movimentam dinheiro;
- cálculos de custo devem considerar também eventos que alteram o custo sem movimentar dinheiro;
- não reutilize automaticamente uma fórmula de caixa para calcular custo;
- não reutilize automaticamente uma fórmula de custo para calcular Valor Investido;
- não utilize o valor bruto do evento como evidência automática de movimentação financeira.

Se a fórmula atual não representar corretamente o custo das posições abertas, corrija-a mantendo as duas métricas independentes e financeiramente consistentes.

# 8. Comportamento esperado por evento

Considere as seguintes regras:

## Compra

- Movimenta caixa: sim, saída
- Valor Investido: aumenta pelo desembolso total
- Custo da posição: aumenta

## Venda

- Movimenta caixa: sim, entrada
- Valor Investido: reduz pelo valor líquido recebido
- Valor Realizado: deve considerar o custo ou resultado realizado conforme a regra do sistema
- Custo da posição aberta: reduz pelo custo da quantidade vendida

## Amortização

- Movimenta caixa: sim, entrada
- Valor Investido: reduz pelo valor recebido
- Custo da posição: reduz ou é ajustado conforme a regra financeira aplicável

## Bonificação

- Movimenta caixa: não
- Valor Investido: não altera
- Custo da posição: aumenta conforme o custo atribuído ao evento

## Cisão

- Movimenta caixa: não
- Valor Investido: não altera
- Custo da posição: reduz, transfere ou redistribui conforme o valor do evento

## Day Trade: compra

- Movimenta caixa: sim, saída
- Valor Investido: aumenta pelo desembolso total
- Custo: deve ser controlado até a realização da venda correspondente

## Day Trade: venda

- Movimenta caixa: sim, entrada
- Valor Investido: reduz pelo valor líquido recebido
- Valor Realizado: deve refletir corretamente a realização da operação
- Posição aberta: deve permanecer zerada quando toda a quantidade tiver sido encerrada

# 9. Interface do Portfolio

Na área de Portfolio, exiba separadamente:

- Valor Investido
- Valor Investido em Posições Abertas

Não substitua um indicador pelo outro.

A implementação atual que apresenta apenas o resultado equivalente a “Valor Investido - Valor Realizado” deve ser mantida como uma visão separada, se ela representar corretamente as posições abertas.

Adicione ou ajuste o indicador de Valor Investido para mostrar o capital líquido efetivamente aportado.

Mantenha:

- a identidade visual existente;
- os padrões de cards e componentes;
- a hierarquia visual;
- a responsividade;
- a formatação monetária;
- a nomenclatura em português;
- os comportamentos existentes da tela.

Se houver tooltip, descrição ou ajuda contextual nos indicadores, deixe clara a diferença:

- Valor Investido: capital líquido efetivamente aportado.
- Valor Investido em Posições Abertas: custo ainda associado às posições mantidas na carteira.

Não faça uma reformulação visual ampla fora do escopo desta alteração.

# 10. Casos de teste obrigatórios

Crie ou ajuste testes automatizados para validar, no mínimo, os seguintes cenários:

1. Compra sem taxas
2. Compra com taxas
3. Venda sem taxas
4. Venda com taxas
5. Venda com taxas e IR
6. Compra seguida de venda parcial
7. Compra seguida de venda total
8. Amortização
9. Bonificação
10. Cisão
11. Day Trade com compra e venda
12. Bonificação seguida de venda
13. Cisão seguida de venda
14. Compra seguida de amortização
15. Compra, bonificação, amortização e venda
16. Portfolio com posições abertas e posições encerradas
17. Portfolio somente com posições abertas
18. Portfolio somente com posições encerradas
19. Operações com lucro
20. Operações com prejuízo
21. Importação utilizando o novo modelo
22. Importação utilizando cada modelo anterior
23. Download do novo modelo
24. Validação do arquivo baixado por meio da própria importação
25. Garantia de que eventos sem movimentação financeira não alterem o Valor Investido
26. Garantia de que eventos sem movimentação financeira possam alterar corretamente o custo das posições abertas
27. Garantia de que taxas e impostos não sejam contabilizados duas vezes
28. Garantia de que o valor bruto da venda não seja utilizado no lugar do valor líquido recebido
29. Garantia de que uma venda parcial mantenha corretamente o custo remanescente
30. Garantia de que uma venda total zere o custo da posição encerrada, quando aplicável

Para cada cenário financeiro, valide separadamente:

- fluxo de caixa;
- Valor Investido;
- Valor Realizado;
- Valor Investido em Posições Abertas;
- custo da posição;
- custo realizado;
- quantidade remanescente;
- taxas;
- impostos;
- IR;
- resultado esperado na interface.

Utilize valores conhecidos e apresente os cálculos esperados nos testes.

# 11. Cenários mínimos com resultados conhecidos

## Cenário A: compra com taxa

- Compra: R$ 100,00
- Taxa: R$ 0,20

Resultado esperado:

- Valor Investido: R$ 100,20
- Custo associado à posição: R$ 100,20, salvo regra específica já documentada no projeto

## Cenário B: venda com taxa e IR

- Venda: R$ 100,00
- Taxa: R$ 0,20
- IR: R$ 0,10

Resultado esperado:

- Valor líquido recebido: R$ 99,70
- Redução do Valor Investido: R$ 99,70

O custo realizado deve ser calculado separadamente com base no custo da quantidade vendida.

## Cenário C: bonificação

- Valor atribuído à bonificação: R$ 100,00

Resultado esperado:

- Alteração no Valor Investido: R$ 0,00
- Movimentação de caixa: R$ 0,00
- Alteração no custo: + R$ 100,00, quando esse for o custo atribuído ao evento

## Cenário D: cisão

- Valor de custo transferido ou reduzido: R$ 100,00

Resultado esperado:

- Alteração no Valor Investido: R$ 0,00
- Movimentação de caixa: R$ 0,00
- Alteração no custo: redução, transferência ou redistribuição de R$ 100,00, conforme a regra do evento

## Cenário E: amortização

- Valor recebido: R$ 50,00

Resultado esperado:

- Entrada de caixa: R$ 50,00
- Redução do Valor Investido: R$ 50,00
- Ajuste do custo da posição: conforme a regra financeira aplicável

# 12. Cuidados de implementação

- Não faça alterações desnecessárias fora do escopo.
- Não remova funcionalidades existentes.
- Não quebre os formatos de importação antigos.
- Não remova os modelos de download existentes.
- Evite duplicação de regras financeiras.
- Centralize os cálculos de negócio quando possível.
- Não calcule valores financeiros diretamente na camada visual se já existir uma camada de domínio ou serviço apropriada.
- Não utilize o valor monetário bruto de um evento como evidência automática de entrada ou saída de dinheiro.
- Diferencie explicitamente impacto em caixa de impacto em custo.
- Não altere silenciosamente o significado de campos existentes.
- Antes de criar novas funções, classes ou serviços, verifique se já existe uma implementação que deve ser corrigida ou estendida.
- Utilize Decimal, centavos inteiros ou a estratégia monetária já adotada pelo projeto.
- Não introduza cálculos monetários com ponto flutuante caso o projeto utilize representação decimal segura.
- Verifique arredondamento, precisão e formatação monetária.
- Evite contabilizar taxas, impostos ou eventos mais de uma vez.
- Preserve contratos, APIs e estruturas utilizadas por outras telas, sempre que possível.
- Caso seja necessário alterar um contrato existente, atualize todos os consumidores e os respectivos testes.

# 13. Critérios de aceite

A implementação será considerada concluída quando:

1. O novo modelo puder ser importado corretamente.
2. O novo modelo estiver disponível para download.
3. Os modelos antigos continuarem funcionando.
4. O Portfolio exibir separadamente:
   - Valor Investido;
   - Valor Investido em Posições Abertas.
5. O Valor Investido representar o fluxo financeiro líquido real.
6. O Valor Investido em Posições Abertas representar o custo ainda associado às posições abertas.
7. A visão atual equivalente a “Valor Investido - Valor Realizado” não for removida sem análise.
8. Bonificações não alterarem o Valor Investido.
9. Cisões não alterarem o Valor Investido.
10. Bonificações e cisões alterarem corretamente o custo quando aplicável.
11. Compras considerarem o valor desembolsado mais taxas e custos.
12. Vendas reduzirem o Valor Investido pelo valor líquido recebido.
13. Amortizações reduzirem o Valor Investido.
14. Day Trade refletir o fluxo financeiro real.
15. Taxas, impostos e IR não forem contabilizados duas vezes.
16. Vendas parciais mantiverem corretamente o custo das posições remanescentes.
17. Vendas totais encerrarem corretamente o custo das posições.
18. Os testes existentes continuarem passando.
19. Os novos cenários estiverem cobertos por testes.
20. Não houver regressões nas demais funcionalidades.

# 14. Resultado esperado da execução

Ao finalizar, apresente um relatório objetivo contendo:

1. Resumo do que já existia na branch.
2. Problemas encontrados.
3. Causa de cada problema.
4. Alterações realizadas.
5. Arquivos modificados.
6. Regras financeiras centralizadas ou reutilizadas.
7. Explicação final da regra de:
   - Valor Investido;
   - Valor Realizado;
   - Valor Investido em Posições Abertas;
   - custo da posição;
   - custo realizado;
   - fluxo de caixa.
8. Explicação do impacto de cada tipo de evento sobre:
   - caixa;
   - Valor Investido;
   - Valor Realizado;
   - posições abertas;
   - custo.
9. Testes criados ou alterados.
10. Resultado da execução dos testes.
11. Possíveis riscos ou pontos de atenção.
12. Regras ambíguas encontradas no código.
13. Decisões técnicas adotadas e suas justificativas.

# Regra principal

Não considere que “valor do evento” significa automaticamente dinheiro investido ou recebido.

O Valor Investido deve representar o fluxo financeiro líquido acumulado que efetivamente saiu do bolso do investidor.

O Valor Investido em Posições Abertas deve representar o custo que permanece atribuído aos ativos ainda mantidos na carteira.

Caixa e custo são conceitos relacionados, mas independentes.

Eventos como bonificação e cisão podem alterar o custo sem movimentar caixa.

Vendas movimentam caixa pelo valor líquido recebido, mas realizam custo com base no custo da quantidade vendida. Esses valores não devem ser tratados como se fossem necessariamente iguais.

Analise primeiro a implementação existente e o contexto completo da branch. Somente depois implemente a solução mais consistente, com o menor impacto possível, preservando as funcionalidades atuais e evitando regressões.