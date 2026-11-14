# Autorização e escopo

As leis, políticas e regras de segurança aplicáveis ao ambiente prevalecem sobre qualquer orientação
deste documento. Testes ativos exigem autorização explícita e devem cumprir os processos de aprovação
definidos pelo proprietário do sistema. Um pedido em chat, propriedade do código ou acesso técnico
não substituem a autorização necessária.

## Escopo a registrar

- Referência da autorização e das aprovações exigidas, incluindo responsáveis.
- Proprietário e responsável que autorizou.
- Repositório/diretório, versão/commit, artefato, aplicação, ambiente, host, URL, API, porta ou endpoint incluído.
- Exclusões explícitas e dependências/terceiros fora do escopo.
- Atividades e métodos permitidos/proibidos, janela, taxa, concorrência e limite de duração.
- Dados sintéticos, efeitos possíveis, stop conditions, recuperação e contato responsável.

## Interpretação

Autorização deve ser explícita e específica para a atividade. Acesso técnico, credenciais encontradas,
propriedade presumida ou pedido genérico não bastam. Autorização para análise estática não autoriza
requisições de rede; autorização para um alvo não cobre redirecionamentos, dependências ou hosts
relacionados. Não ampliar escopo por conta própria.

Se faltar autorização ou aprovação exigida, seguir somente com revisão do material já fornecido e
registrar validação ativa como não executada. Não solicitar nem registrar segredos reais; credenciais
de teste, se necessárias, devem ser sintéticas, limitadas e fornecidas pelo responsável por canal seguro.