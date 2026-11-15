Implemente a funcionalidade de recolher e expandir a barra lateral de navegação do InvestHub+.

Atualmente, o menu lateral permanece sempre aberto e ocupa uma área considerável da tela. Quero permitir que o usuário recolha essa barra para aumentar a área útil do conteúdo principal.

Comportamento esperado
Adicione um botão de recolher/expandir na parte superior da barra lateral, preferencialmente próximo ao nome InvestHub+.

Quando o menu estiver expandido, mantenha o comportamento visual atual:

exibir ícone + nome de cada opção;
manter a largura atual;
manter o destaque visual da opção selecionada.

Quando o menu estiver recolhido:

reduzir sua largura para aproximadamente 64 a 72 px;
exibir somente os ícones dos menus;
ocultar os nomes das opções;
centralizar adequadamente os ícones;
manter destacado o item atualmente selecionado;
exibir um tooltip com o nome da opção ao passar o mouse sobre cada ícone.

Ao recolher a barra lateral, o conteúdo principal deve automaticamente utilizar o espaço liberado. Não deve permanecer uma área vazia correspondente à largura anterior do menu.

A expansão/recolhimento deve possuir uma transição visual curta e suave, aproximadamente 150 a 250 ms, sem provocar saltos ou desalinhamentos no conteúdo.

O estado escolhido pelo usuário deve ser persistido, preferencialmente usando localStorage. Por exemplo:

usuário recolheu o menu;
navegou para outra tela;
atualizou a página com F5;
o menu deve continuar recolhido.

Recolher ou expandir o menu não pode recarregar a página, alterar a rota atual ou provocar perda de:

filtros;
query string;
paginação;
formulários;
dados temporários da tela;
estado do usuário.
Responsividade

Em desktop, utilizar os estados expandido e recolhido.

Em telas menores, não deixar o menu ocupar permanentemente parte relevante da tela. Preferencialmente utilizar comportamento de drawer/overlay, acionado por botão, sem deslocar ou comprimir excessivamente o conteúdo.

Acessibilidade

O controle deve funcionar com mouse e teclado.

Adicionar os atributos apropriados, como:

aria-label;
aria-expanded;
title ou tooltip acessível para os itens quando o menu estiver recolhido.

O botão de recolher/expandir deve possuir indicador visual suficientemente claro, como chevrons ‹ e › ou ícone equivalente já utilizado pelo padrão visual da aplicação.

Importante

Não altere as rotas, permissões, nomes ou funcionalidades existentes no menu.

Não reorganize as opções neste momento. O objetivo desta alteração é somente melhorar o aproveitamento de espaço por meio do recolhimento da barra lateral, preservando o funcionamento atual.

Critérios de aceite

Considere a implementação concluída somente se:

 É possível recolher e expandir a barra lateral.
 Recolhida, a barra apresenta apenas os ícones.
 Os tooltips identificam corretamente cada opção.
 O item selecionado continua destacado.
 O conteúdo principal aumenta de largura ao recolher o menu.
 Não aparece espaço vazio no local anteriormente ocupado pela barra.
 A navegação entre os menus continua funcionando normalmente.
 O estado recolhido/expandido é preservado após F5.
 Navegar para outra seção preserva o estado da sidebar.
 Query strings e filtros da tela atual não são perdidos.
 Não há sobreposição ou corte de conteúdo.
 O comportamento responsivo funciona corretamente.
 A alteração não introduz regressões nas telas existentes.
Validação final

Após implementar, teste pelo menos as telas Resumo, Portfólio, Rentabilidade, Operações, Imposto de Renda, Valuation e Configurações nos estados expandido e recolhido.

Informe ao final:

quais arquivos/componentes foram alterados;
como o estado da sidebar foi persistido;
se foi necessário alterar o layout principal;
quais testes foram realizados;
se foi identificada alguma tela que não se adapte corretamente ao menu recolhido.