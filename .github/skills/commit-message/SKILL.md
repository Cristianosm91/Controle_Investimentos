---
name: commit-message
description: Gera mensagens de commit no padrao Conventional Commits, compativeis com o changelog
disable-model-invocation: true
---
Use a skill git-workflow e gere a mensagem de commit com base no resumo abaixo.

Resumo da mudanca:
{{input:Descreva em 1-3 frases o que mudou no codigo.}}

Escopo sugerido (opcional):
{{input:Exemplo api, build, parser, logs.}}

Tipo sugerido (opcional):
{{input:Exemplo feat, fix, refactor, chore.}}

Regras:
- Escolha o tipo que descreve a mudanca real e mantenha a mensagem compativel
  com o changelog: feat = Adicionado; fix/perf = Corrigido;
  refactor/chore/style = Alterado quando relevante ao usuario;
  feat! ou BREAKING CHANGE = Alterado com nota de incompatibilidade.
- Nunca adicione o trailer `Co-authored-by: Copilot` à mensagem de commit.
- Nao diga nem sugira que testes foram executados, aprovados, que houve
  homologacao, aprovacao de pessoas ou release se isso nao estiver informado
  explicitamente no resumo.
- A mensagem descreve o commit, nao certifica que o fluxo de desenvolvimento,
  homologacao ou producao foi concluido. Consulte git-workflow para
  orientacao sobre branches e Merge Requests.

Resposta obrigatoria:
1. Uma versao em uma linha.
2. Uma versao completa com corpo em bullets curtos (quando fizer sentido).
3. Uma alternativa curta caso eu queira titulo ainda mais objetivo.
