Analise a implementação atual antes de alterar qualquer código.

Quero evoluir principalmente os filtros das telas Rentabilidade, Proventos e Operações, além de fazer dois ajustes nas telas Alocação e Portfólio.

IMPORTANTE:
- Preserve o design atual da aplicação.
- Não redesenhe as telas.
- Não altere cores, identidade visual, cards, tipografia ou estrutura geral sem necessidade.
- Não altere regras financeiras existentes que não estejam relacionadas diretamente a esta solicitação.
- Reutilize componentes existentes sempre que possível.
- Antes de implementar, identifique como os ativos, classes, mercados, países, setores, operações e proventos estão modelados atualmente.
- Não crie valores fictícios ou classificações arbitrárias.
- Os filtros devem funcionar sobre os dados reais disponíveis para o investidor selecionado.
- Implemente backend e frontend necessários, não apenas a interface.
- Após implementar, teste cada combinação relevante de filtros.

==================================================
1. FILTRO MULTISSELEÇÃO DE ATIVOS
==================================================

Nas telas:

- Rentabilidade
- Proventos
- Operações

quero poder selecionar um ou vários ativos simultaneamente.

Exemplos:

[✓] PETR4
[ ] VALE3
[✓] ITUB4
[ ] IVVB11
[✓] BTC

O usuário deve conseguir selecionar:

- somente 1 ativo
- 2 ativos
- 3 ativos
- vários ativos
- todos os ativos

A seleção não deve funcionar como um select simples onde escolher uma opção substitui a anterior.

Utilize um componente de multisseleção semelhante ao filtro de Classes existente no Portfólio, com checkboxes, mas adaptado para seleção de ativos.

Adicionar também:

- opção "Todos os ativos"
- busca pelo código/nome do ativo caso existam muitos ativos
- indicação visual resumida da seleção

Exemplos no campo fechado:

"Todos os ativos"

"PETR4"

"PETR4 + VALE3"

"3 ativos selecionados"

Evite mostrar uma lista enorme dentro do campo quando muitos ativos estiverem selecionados.

A lista deve considerar somente os ativos existentes na carteira/contexto atual do investidor.

==================================================
2. FILTRO POR MERCADO / TIPO DE INVESTIMENTO
==================================================

Nas mesmas telas:

- Rentabilidade
- Proventos
- Operações

criar um novo filtro que permita separar os investimentos em:

[ ] Brasil
[ ] EUA
[ ] Criptomoedas

Esse filtro também deve ser MULTISSELEÇÃO.

Exemplos válidos:

Brasil

EUA

Criptomoedas

Brasil + EUA

Brasil + Criptomoedas

EUA + Criptomoedas

Brasil + EUA + Criptomoedas

Todos

IMPORTANTE:

Não utilizar moeda como única regra para determinar o mercado do ativo.

Analise o modelo existente e procure primeiro campos como:

- mercado
- país
- exchange
- asset_type
- classe
- tipo
- origem

ou equivalentes.

A classificação deve ser baseada na estrutura real existente no projeto.

Criptomoedas devem continuar sendo identificadas como criptomoedas independentemente da moeda utilizada na operação, pois uma criptomoeda pode ter sido adquirida em BRL, USD, EUR etc.

Não implementar algo incorreto como:

BRL = Brasil
USD = EUA

porque isso não é suficiente para determinar a origem/tipo do investimento.

==================================================
3. COMBINAÇÃO DOS FILTROS
==================================================

Os filtros precisam funcionar de forma combinada.

Por exemplo:

Mercado:
[✓] Brasil
[ ] EUA
[✓] Criptomoedas

Ativos:
[✓] PETR4
[✓] BTC

Classe:
[✓] Ações
[✓] Cripto

Nesse cenário, os componentes da tela devem considerar apenas os ativos correspondentes aos filtros selecionados.

O filtro de mercado deve também restringir dinamicamente os ativos disponíveis no filtro "Ativos".

Exemplo:

Se selecionar apenas "Brasil", não faz sentido continuar oferecendo BTC ou AAPL na lista de ativos.

Se selecionar "Criptomoedas", devem aparecer somente as criptomoedas disponíveis para aquele investidor.

Evite estados inconsistentes quando um filtro tornar uma seleção anterior inválida.

==================================================
4. RENTABILIDADE
==================================================

Aplicar os novos filtros na tela Rentabilidade.

Hoje existe principalmente o filtro:

Classe

E quero manter esse filtro.

Adicionar:

Mercado/Tipo
Ativos

Sugestão de organização:

Mercado | Classe | Ativos

Todos devem aceitar seleção múltipla quando aplicável.

Ao selecionar os filtros, recalcular corretamente todos os componentes dependentes da carteira filtrada, incluindo, quando aplicável:

- TWR
- retorno
- patrimônio
- resultado no período
- fluxo líquido
- gráficos
- séries históricas
- benchmarks/comparações

Não recalcular simplesmente médias dos indicadores individuais dos ativos.

Respeitar a metodologia financeira atualmente implementada no sistema.

==================================================
5. PROVENTOS
==================================================

Aplicar exatamente o mesmo conceito à tela Proventos.

Adicionar filtros:

Mercado/Tipo
Classe
Ativos

Com suporte a multisseleção.

Os filtros precisam valer para todas as visões relevantes da tela:

- Lançamentos
- Matriz mensal
- Agenda e projeção

Se houver dados carregados por APIs/endpoints diferentes entre essas abas, garantir que o filtro seja aplicado consistentemente em todas elas.

Totais, médias, projeções e demais indicadores devem refletir somente os ativos efetivamente selecionados.

==================================================
6. OPERAÇÕES
==================================================

Na tela Operações já existe um campo de Ativos.

Avalie a implementação atual e evolua esse filtro para suportar seleção estruturada de um ou vários ativos.

Quero o mesmo comportamento das outras telas.

Adicionar também o filtro:

Mercado/Tipo

com:

Brasil
EUA
Criptomoedas

mantendo os filtros existentes:

- Classe
- Evento
- Corretora
- Data inicial
- Data final

Todos os filtros devem poder ser combinados.

Exemplo:

Mercado = Brasil + EUA
Ativos = PETR4 + AAPL
Evento = Compra
Corretora = Todas
Período = 01/01/2026 até 31/12/2026

A tabela deve retornar somente operações compatíveis com todos esses critérios.

==================================================
7. COMPONENTE REUTILIZÁVEL
==================================================

Não quero três implementações diferentes para o mesmo comportamento.

Se a arquitetura atual permitir, crie/reutilize um componente genérico de multisseleção que possa ser utilizado em:

- Mercado
- Classe
- Ativos

e futuramente em outros filtros.

Esse componente deve permitir:

- checkbox
- selecionar todos
- limpar seleção
- selecionar múltiplos itens
- pesquisar quando houver muitos itens
- fechar clicando fora
- manter seleção ao abrir novamente
- apresentar quantidade selecionada
- funcionar corretamente com teclado quando possível

Não alterar o estilo visual atual da aplicação desnecessariamente.

==================================================
8. ALOCAÇÃO - ARCA E KRAKEN
==================================================

Na tela Alocação, localizar a seção:

"Por estratégia"

Logo ABAIXO dessa seção quero adicionar uma nova tabela comparativa/analítica relacionada às estratégias:

ARCA
KRAKEN

IMPORTANTE:

NÃO inventar o significado das letras ARCA ou KRAKEN.

Ainda vou fornecer a composição/significado dessas estratégias.

Neste momento:

1. analise como "Por estratégia" está implementado;
2. identifique quais dados da carteira poderão alimentar ARCA/KRAKEN;
3. prepare a estrutura necessária para a tabela;
4. mantenha essa funcionalidade isolada para permitir configurar posteriormente as regras de ARCA e KRAKEN;
5. se o significado/composição for indispensável para concluir os cálculos, pare especificamente nessa parte e me pergunte qual é o significado de cada letra/componente.

Não assuma percentuais ou classificações.

A tabela deve ficar logo abaixo de "Por estratégia" e seguir a mesma identidade visual das demais tabelas/cards da aplicação.

==================================================
9. PORTFÓLIO - TROCAR SUBSETOR POR SETOR
==================================================

Existe atualmente um problema no Portfólio:

o campo/subsetor não está sendo carregado corretamente e acaba ficando vazio ou sem classificação.

Quero substituir o uso de "subsetor" por "setor".

Mas NÃO faça apenas uma troca de label no frontend.

Primeiro rastreie o fluxo completo:

Banco/model → serviço → API → serialização → frontend.

Identifique:

- de onde deveria vir o subsetor;
- por que ele não está sendo populado;
- qual campo real de "setor" existe;
- se setor já está sendo retornado pela API;
- se existe inconsistência de nomes entre backend e frontend.

Depois substitua a exibição/uso de subsetor por setor onde fizer sentido.

Teste utilizando ativos que realmente possuam setor cadastrado.

A seção "Exposição por setor" também deve utilizar essa mesma informação de maneira consistente.

Não quero simplesmente trocar "Sem setor" por outro texto.

O objetivo é fazer o setor REAL do ativo carregar corretamente.

==================================================
10. CONSISTÊNCIA DOS DADOS
==================================================

Centralize os critérios de classificação sempre que possível.

Não quero que:

Rentabilidade classifique um ativo como Brasil,

Proventos classifique o mesmo ativo de outra forma,

e Operações use uma terceira regra.

Brasil / EUA / Criptomoedas devem usar uma regra única e compartilhada.

O mesmo vale para:

- Classe
- Setor
- Ativo

Evite duplicação de lógica entre páginas.

==================================================
11. PERSISTÊNCIA E UX DOS FILTROS
==================================================

Ao navegar entre abas internas da mesma tela, preserve os filtros selecionados quando isso fizer sentido.

Exemplo:

Proventos:
Matriz mensal → Agenda e projeção → Lançamentos

A seleção de:

Mercado
Classe
Ativos

não deve desaparecer desnecessariamente.

Ao escolher "Todos", o comportamento deve continuar compatível quando novos ativos forem adicionados à carteira.

Ou seja, preferencialmente represente "Todos" como estado lógico e não apenas como a lista atual de IDs selecionados.

==================================================
12. TESTES OBRIGATÓRIOS
==================================================

Depois de implementar, teste pelo menos:

Caso 1
1 ativo

Caso 2
2 ativos

Caso 3
3 ou mais ativos

Caso 4
todos os ativos

Caso 5
somente Brasil

Caso 6
somente EUA

Caso 7
somente Criptomoedas

Caso 8
Brasil + EUA

Caso 9
Brasil + Criptomoedas

Caso 10
EUA + Criptomoedas

Caso 11
todos os mercados

Caso 12
Mercado + Classe + múltiplos Ativos simultaneamente

Caso 13
trocar mercado depois de selecionar ativos e verificar se seleções incompatíveis são tratadas corretamente

Caso 14
trocar investidor e verificar se filtros/ativos são atualizados corretamente

Caso 15
filtrar um conjunto que não possui resultados e garantir estado vazio adequado

Também validar:

- Rentabilidade
- Proventos
- Operações
- Portfólio / Setor
- Alocação

==================================================
13. CUIDADOS COM REGRESSÃO
==================================================

Não quebrar:

- seleção de investidor
- cálculos atuais
- importação de operações
- cadastro de operações
- edição/exclusão de operações
- paginação
- exportação
- filtros existentes
- carregamento das cotações
- histórico
- cálculo de rentabilidade
- proventos
- moeda das operações
- suporte a criptomoedas em diferentes moedas

==================================================
14. ENTREGA
==================================================

Implemente as alterações no código.

Ao final, apresente objetivamente:

1. arquivos alterados;
2. componentes criados/reutilizados;
3. endpoints/query parameters alterados;
4. regra utilizada para identificar Brasil, EUA e Criptomoedas;
5. como funciona a multisseleção;
6. causa encontrada para o problema de subsetor/setor;
7. como o problema de setor foi corrigido;
8. estrutura preparada para ARCA/KRAKEN;
9. testes executados;
10. resultado dos testes;
11. qualquer ponto que ainda dependa da definição de ARCA/KRAKEN.

Não faça refatorações fora do escopo apenas por preferência arquitetural.
Não altere funcionalidades que não sejam necessárias para esta solicitação.