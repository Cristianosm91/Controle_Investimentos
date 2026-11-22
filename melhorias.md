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
8. ALOCAÇÃO - METODOLOGIAS ARCA E KRAKEN
==================================================

Na tela Alocação, localizar a seção existente:

"Por estratégia"

Logo ABAIXO dela, criar uma nova seção:

"Metodologias de alocação"

Essa seção deverá permitir visualizar duas metodologias:

[ ARCA ] [ KRAKEN ]

IMPORTANTE:
"KRAKEN" neste contexto significa a METODOLOGIA DE ALOCAÇÃO descrita abaixo.
Não confundir com corretora/exchange de criptomoedas chamada Kraken.

Preservar integralmente a identidade visual atual da aplicação.
Não criar uma tela separada se não houver necessidade.

==================================================
8.1 ARCA
==================================================

A metodologia ARCA deve dividir o patrimônio da carteira em quatro grupos:

A — Ações e Negócios
- Principalmente ações/negócios brasileiros.

R — Real Estate
- Fundos Imobiliários (FIIs).
- Outros investimentos imobiliários quando houver classificação inequívoca.

C — Caixa
- Renda fixa.
- Caixa e instrumentos de liquidez/reserva.

A — Ativos Internacionais
- Ações internacionais.
- ETFs internacionais.
- Demais investimentos cuja exposição seja efetivamente internacional.

Não determinar exposição internacional apenas pela moeda de negociação.

==================================================
8.2 KRAKEN
==================================================

Para esta aplicação, considerar KRAKEN como a metodologia de diversificação de patrimônio composta pelos seguintes grupos:

1. Caixa

Liquidez, reserva e recursos destinados a oportunidades.

Exemplos:
- caixa
- renda fixa compatível com esse objetivo
- instrumentos de liquidez

2. Real Estate

Exposição imobiliária e geração de renda pelo segmento.

Exemplos:
- FIIs
- REITs
- outros ativos imobiliários inequivocamente classificados

3. Ações / ETFs

Exposição ao mercado de ações local e internacional.

Exemplos:
- ações brasileiras
- ações dos EUA
- ETFs brasileiros
- ETFs internacionais

4. Criptoativos

Exposição específica a criptomoedas.

Exemplos:
- BTC
- ETH
- demais criptomoedas existentes na carteira

IMPORTANTE:
Uma criptomoeda continua pertencendo a Criptoativos independentemente da moeda usada para sua compra.

Por exemplo:

BTC comprado em BRL -> Criptoativos
BTC comprado em USD -> Criptoativos
BTC comprado em EUR -> Criptoativos

A moeda não altera a natureza do ativo.

5. Negócios / Oportunidades

Investimentos complementares que se enquadrem explicitamente nessa categoria.

Não classificar ativos nessa categoria apenas porque não foi possível descobrir sua classe.

Ativos sem classificação segura devem permanecer como:

"Não classificado"

==================================================
8.3 NÃO CONFUNDIR AS DUAS METODOLOGIAS
==================================================

ARCA e KRAKEN possuem classificações próprias.

Um mesmo ativo poderá pertencer a categorias diferentes dependendo da metodologia analisada.

Exemplo conceitual:

PETR4
ARCA -> Ações e Negócios
KRAKEN -> Ações / ETFs

FII
ARCA -> Real Estate
KRAKEN -> Real Estate

BTC
ARCA -> verificar regra/configuração da metodologia;
não assumir categoria automaticamente.
KRAKEN -> Criptoativos

A classificação deve ocorrer por metodologia.

Não modificar a classe original do ativo para realizar essa classificação.

==================================================
8.4 MODELO DE DADOS
==================================================

Não espalhar condições hardcoded pelas telas.

Criar uma camada centralizada de classificação de metodologias.

A arquitetura deve permitir conceitualmente:

Ativo
  -> classificação original
  -> características
     - classe
     - mercado
     - país
     - tipo
     - setor
     - moeda
     - exchange
  -> classificação ARCA
  -> classificação KRAKEN

Utilizar apenas campos realmente existentes no projeto.

Não criar propriedades fictícias no banco apenas para satisfazer essa estrutura conceitual.

Se algum metadado necessário não existir, identificar isso na entrega.

==================================================
8.5 TABELA
==================================================

Ao selecionar ARCA, mostrar algo equivalente a:

Categoria | Valor atual | % atual

Ações e Negócios
Real Estate
Caixa
Ativos Internacionais
Não classificado
TOTAL

Ao selecionar KRAKEN:

Categoria | Valor atual | % atual

Caixa
Real Estate
Ações / ETFs
Criptoativos
Negócios / Oportunidades
Não classificado
TOTAL

A linha "Não classificado" somente precisa aparecer quando existir algum valor nessa situação.

A linha TOTAL deverá representar 100% do patrimônio considerado.

==================================================
8.6 CÁLCULO
==================================================

Calcular a participação utilizando VALOR/PATRIMÔNIO e não quantidade de ativos.

Para cada categoria:

% categoria =
valor atual da categoria
/
valor atual total considerado
* 100

Exemplo:

Carteira KRAKEN:

Caixa                 R$ 10.000
Real Estate           R$ 25.000
Ações / ETFs          R$ 40.000
Criptoativos          R$ 20.000
Negócios              R$ 5.000

Total                 R$ 100.000

Resultado:

Caixa                 10%
Real Estate           25%
Ações / ETFs          40%
Criptoativos          20%
Negócios               5%

TOTAL                 100%

Utilizar a mesma regra de valuation/patrimônio já adotada pela aplicação.

Não criar uma segunda fórmula para calcular o valor atual dos ativos.

==================================================
8.7 ATUAL X ALVO
==================================================

Prepare a estrutura para permitir posteriormente:

Categoria | Atual | Alvo | Diferença

Exemplo visual:

Caixa                 10% | -- | --
Real Estate           25% | -- | --
Ações / ETFs          40% | -- | --
Criptoativos          20% | -- | --
Negócios               5% | -- | --

Não inventar percentuais-alvo.

Se o sistema ainda não possui configuração de meta para ARCA ou KRAKEN, não assumir:

25%
20%
ou qualquer outra distribuição.

A arquitetura deve apenas ficar preparada para receber esses percentuais posteriormente.

==================================================
8.8 VISUALIZAÇÃO
==================================================

Quero algo simples e consistente com a aplicação atual.

Estrutura preferida:

Metodologias de alocação

[ ARCA ] [ KRAKEN ]

Categoria                Atual      Valor
------------------------------------------------
Ações / ETFs             40%       R$ 40.000
Real Estate              25%       R$ 25.000
Criptoativos             20%       R$ 20.000
Caixa                    10%       R$ 10.000
Negócios / Oportunidades  5%       R$  5.000

Total                   100%       R$100.000

Isso é apenas referência de organização.
Não copiar literalmente se o design system atual possuir uma forma mais consistente de apresentar tabelas.

Não criar gráficos extras neste momento.
Primeiro implementar corretamente classificação, cálculo e tabela.

==================================================
8.9 REGRAS IMPORTANTES DE CLASSIFICAÇÃO
==================================================

Não usar apenas ticker para classificar ativos.

Não usar apenas moeda.

Não usar apenas corretora.

Não considerar:

USD = internacional
BRL = Brasil

como regra suficiente.

Priorizar, de acordo com os dados realmente disponíveis:

1. tipo/classe do ativo
2. país/mercado/exposição
3. exchange
4. demais metadados existentes
5. ticker apenas quando necessário e quando a regra for inequívoca

Cuidado principalmente com:

- BDR
- ETF brasileiro
- ETF internacional
- REIT
- FII
- criptomoedas
- ativos negociados no Brasil com exposição internacional

Um BDR, por exemplo, não deve ser tratado automaticamente como "ação brasileira" apenas porque é negociado no Brasil.

==================================================
8.10 INTEGRAÇÃO COM OS NOVOS FILTROS
==================================================

A implementação deve aproveitar a mesma classificação estruturada criada para os filtros:

- Brasil
- EUA
- Criptomoedas

Não criar uma regra de mercado para Rentabilidade e outra completamente diferente para Alocação.

Centralizar as informações fundamentais do ativo e permitir que cada metodologia apenas aplique seu próprio mapeamento.

Exemplo conceitual:

Ativo
   ↓
Metadados normalizados
   ↓
├── Mercado: Brasil/EUA/Cripto
├── ARCA: categoria correspondente
└── KRAKEN: categoria correspondente

==================================================
8.11 TESTES
==================================================

Criar testes para pelo menos:

1. ação brasileira
2. FII
3. renda fixa/caixa
4. ação americana
5. ETF brasileiro
6. ETF internacional
7. BDR
8. REIT
9. Bitcoin
10. outra criptomoeda
11. ativo sem classificação completa

Validar:

- classificação ARCA;
- classificação KRAKEN;
- valor de cada categoria;
- percentual;
- soma final;
- tratamento de não classificados.

A soma:

categorias classificadas
+
não classificados

deve corresponder ao patrimônio total considerado.

A soma percentual deve resultar em aproximadamente 100%, considerando somente eventual diferença de arredondamento.

==================================================
8.12 ENTREGA
==================================================

Ao finalizar, informar:

1. quais classes/tipos de ativos existem atualmente na aplicação;
2. como cada classe foi mapeada para ARCA;
3. como cada classe foi mapeada para KRAKEN;
4. quais ativos ficaram não classificados;
5. quais metadados foram utilizados na classificação;
6. como Brasil/EUA/Cripto estão sendo determinados;
7. se existem ativos cuja classificação é ambígua;
8. arquivos alterados;
9. testes executados;
10. resultado dos testes.

IMPORTANTE:

Se durante a análise aparecer uma classe ambígua, não tome uma decisão financeira por conta própria.

Exemplo:

"Encontrei a classe BDR e ela pode ser tratada de formas diferentes na metodologia ARCA."

Nesse caso, informe a situação antes de criar uma regra arbitrária.

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