vamos trabalhar com 3 níveis de branches.

Branch é uma cópia do projeto onde você trabalha nas suas mudanças sem mexer na versão oficial. Quando tudo estiver testado e aprovado, essas mudanças são juntadas ao projeto principal.

1º nível: desenvolvimento: É aqui que quem estiver desenvolvendo vai trabalhar. A pessoa cria uma branch nova e faz as alterações necessárias.

Aqui acontece a primeira etapa de validação:
Quem desenvolveu faz os próprios testes;
O agente de IA revisa o código em busca de falhas de segurança, erros e problemas de qualidade.
No primeiro nível iremos classificar cada Branch entre as opções abaixo:
feature/, refactor/, fix/ e docs/
feature/ = Nova funcionalidade.
Exemplo: feature/botão-excluir-itens-selecionados
refactor/ = Reorganização interna sem mudança funcional.
Exemplo: refactor/separar-camada-de-dados
fix/ = Correção de bug encontrado no desenvolvimento ou na homolog.
Exemplo: fix/corrigir-encerramento-ocorrencias
docs/ = Só documentação (README, guias)
Exemplo: docs/guia-instalacao
Commits são feitos somente na branch de desenvolvimento. Depois de concluir os
testes e da revisão do agente de IA, quem desenvolveu abre um Merge Request da
branch de desenvolvimento para `homolog`. Se `homolog` não existir, um
Maintainer/Owner a cria a partir da `main` atual e a protege antes do uso.

2º nível: homologação: É a segunda etapa de validação. Aqui, 2 ou 3 pessoas testam a aplicação. Se não encontrarem falhas, geramos a partir daqui o pacote piloto.

3º nível: produção: Com o piloto aprovado, chegamos à última etapa: o Merge
Request da branch `homolog` para `main`. Esse MR precisa ser aprovado por pelo
menos 2 pessoas. Depois do merge, geramos o pacote final a partir da `main`,
que vai para produção.

Feature/Refactor/Fix/Docs → Homolog → Piloto → Main → Pacote final → Produção

Para fugir do destino ou das etapas definidos, o desenvolvedor deve pedir isso
explicitamente. O agente informa a regra e o risco que serão contornados e pede
confirmação específica após o aviso antes de abrir/alterar o MR, executar merge
local ou fazer push normal. Deve distinguir essas operações e apresentar
repositório, origem, destino, remoto e etapas ignoradas. Sem confirmação,
segue-se o fluxo padrão. A exceção vale só para as operações discriminadas,
podendo abranger merge local e push normal para `homolog` ou `main`; não permite
commits de desenvolvimento direto nessas branches, force-push, reescrita de
histórico, exclusão de branches ou alteração das proteções. Não persista a
autorização e não repita a pergunta sem mudança de escopo.
O agente publica somente os remoto/ref/SHAs confirmados, conforme
[proteção de branches](docs/git/protecao-main.md). A confirmação não supera
permissões do GitLab: se houver rejeição, pare e ofereça MR ou atuação de alguém
autorizado. Diferencie sempre merge local de alteração efetiva no servidor.

Com isso, a gente garante que o código da main nunca será quebrado, será sempre o oficial testado e aprovado.