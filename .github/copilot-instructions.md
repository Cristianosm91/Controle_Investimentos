# Instruções do repositório

## Git

- O usuário pede explicitamente: **não incluir** o trailer
  `Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>` nem qualquer
  outra atribuição de coautoria ao Copilot em commits (inclusive squash e merge commits),
  merges, tags, releases, PRs/MRs ou demais registros Git.
- Antes de qualquer operação Git (commit, branch, merge, push, PR/MR, tag, versão),
  carregue a skill `git-workflow` e siga as regras dela.
- Para cada tarefa, crie uma nova branch a partir da `main` atualizada; faça commit
  e push nessa branch e depois integre-a na `main` com merge local e push. Este
  projeto não exige `homolog`, MR/PR, aprovações nem proteção de branches.
