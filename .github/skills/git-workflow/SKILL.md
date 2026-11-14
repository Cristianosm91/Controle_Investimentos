---
name: git-workflow
description: 'Use ao escrever ou validar commits, criar branches, fazer merge/push/MR/PR e definir versões/pacotes. Cobre Conventional Commits, fluxo feature/refactor/fix/docs → homolog → main no GitLab ou GitHub, proteção de homolog/main feita pelo próprio agente (sem hook local), exceção por operação após confirmação explícita, tags e pacotes piloto/produção. Palavras-gatilho: commit, branch, homolog, main, merge, push, proteção, confirmação, Merge Request, Pull Request, GitLab, GitHub, versionamento, versão, tag, changelog, semver, pacote, piloto, produção, revisão, r1, r2.'
---

# Git / Fluxo de trabalho

Padrões de commits, branches e versionamento dos projetos.
As regras completas ficam em `guia-skills/docs/git/`.

## Quando usar
- Escrever, gerar ou **validar mensagem de commit** (título e corpo).
- Criar ou **nomear uma branch**.
- Fazer **merge, push ou MR**, inclusive exceções confirmadas para `main`/`homolog`.
- Definir a **próxima versão** / criar tag / atualizar changelog.
- Identificar pacotes de **piloto/produção** e suas revisões pela branch.

## Fontes de verdade (leia antes de aplicar)
- Commits: [docs/git/commits.md](../../../guia-skills/docs/git/commits.md)
- Branches: [docs/git/branches.md](../../../guia-skills/docs/git/branches.md)
- Proteção de `homolog`/`main`: [docs/git/protecao-main.md](../../../guia-skills/docs/git/protecao-main.md)
- Versionamento: [docs/git/versionamento.md](../../../guia-skills/docs/git/versionamento.md)
- Tag / Release: [docs/git/tag-release.md](../../../guia-skills/docs/git/tag-release.md)

## Resumo de bolso
- **Commit:** `tipo(escopo): descrição no imperativo, minúsculas, sem ponto final`
  (tipos: `feat | fix | docs | style | refactor | perf | test | chore | build | ci`).
- **Branches de desenvolvimento:** somente `feature/nome`, `refactor/descricao`,
  `fix/descricao` ou `docs/descricao`.
- **Fluxo padrão:** branch de desenvolvimento → MR para `homolog` → testes por
  2 ou 3 pessoas → pacote piloto → MR `homolog` → `main` com no mínimo 2
  aprovações → pacote final.
- Não desenvolver nem commitar diretamente em `homolog` ou `main`. Merge local
  e push normal são exceções somente após confirmação específica, conforme abaixo.
- **Versão:** `MAJOR.MINOR.CORREÇÃO` — funcionalidade nova → MINOR; correção → CORREÇÃO;
  mudança grande/incompatível → MAJOR. Toda versão em produção recebe tag `vX.Y.Z`.
- **Pacotes:** classificação automática pela branch; `homolog` gera
  `<aplicacao>-piloto-v<versao>` (regerações `-r1`, `-r2`, ...), `main` gera
  `<aplicacao>-v<versao>`. Identificação da origem, persistência e reserva das
  revisões seguem [versionamento.md](../../../guia-skills/docs/git/versionamento.md).

## Regras obrigatórias de fluxo

1. Leia [docs/git/branches.md](../../../guia-skills/docs/git/branches.md) e
   [docs/git/protecao-main.md](../../../guia-skills/docs/git/protecao-main.md) antes de
   orientar ou executar operações de branch/MR.
2. Crie branches de desenvolvimento a partir da `homolog` atualizada. Se a
   branch remota `homolog` não existir, crie-a a partir da `main` atual e
   proteja-a antes do uso, desde que haja acesso e permissão de Maintainer/Owner.
   Caso contrário, peça que um Maintainer/Owner faça essa configuração e não
   improvise outro destino.
3. Direcione MRs de `feature/`, `refactor/`, `fix/` ou `docs/` para `homolog`.
   Direcione MRs de `homolog` para `main` somente após a homologação e a
   aprovação do piloto; exija pelo menos 2 aprovações no MR para `main`.
4. Se o desenvolvedor solicitar explicitamente outro destino ou desvio do
   fluxo, informe a regra que será contornada e o risco, e peça confirmação
   explícita antes de criar/alterar o MR, executar o merge local ou fazer push
   normal. Sem confirmação, mantenha o fluxo padrão. Siga o protocolo abaixo;
   a exceção não permite commits de desenvolvimento direto nessas branches.

## Plataforma: GitLab ou GitHub

As regras desta skill valem para as duas plataformas. Identifique a plataforma pelo remoto
(`git remote -v`) e use o termo equivalente — os guias em `guia-skills/docs/git/` usam a
nomenclatura do GitLab:

| GitLab | GitHub |
|---|---|
| Merge Request (MR) | Pull Request (PR) |
| Protected branches (`Allowed to push/merge`) | Branch protection rules / Rulesets |
| Approvals mínimos no MR | Required approvals / required reviews |
| Maintainer / Owner | Maintain / Admin |
| `.gitlab-ci.yml` | `.github/workflows/*.yml` (GitHub Actions) |
| Release (release-cli) | Release (`gh release create`) |
| `CI_COMMIT_BRANCH` | `GITHUB_REF_NAME` |

Neste documento, "MR" significa MR ou PR, e "plataforma" significa GitLab ou GitHub. Para o
pipeline e as verificações obrigatórias antes do merge, use a skill `ci-cd-release`.

## Proteção no clone (feita pelo agente)

Não há hook local: **esta skill é a proteção**. Ao executar operações Git:

1. Nunca faça commit, merge local, push ou MR envolvendo `homolog`/`main` fora do
   fluxo padrão sem o protocolo de exceção abaixo. Recuse `master` como destino.
2. Antes de qualquer push, confira a branch atual e o destino. Para `homolog`/`main`,
   obtenha a ref remota atual (`git fetch`) e verifique que o push é fast-forward
   (`git merge-base --is-ancestor <remoto> <local>`).
3. Nunca use `--force`, `--force-with-lease`, `--all`, `--mirror` ou `--no-verify`,
   nem crie/exclua branches protegidas, sem autorização separada.
4. Se o projeto ainda tiver `core.hooksPath` apontando para o antigo `hooks/`
   (`Regras/hooks` ou `guia-skills/hooks`), informe e, com autorização, remova com
   `git config --local --unset core.hooksPath`, preservando hooks personalizados.
5. Relate se a proteção na plataforma (GitLab/GitHub) foi verificada ou permanece
   não verificada. Não peça credenciais nem altere permissões na plataforma.

## Protocolo de exceção confirmada

1. Diferencie **MR para main**, **merge local na main** e **push para main**.
   Um pedido inicial como "faça merge na main" não é a confirmação do aviso.
   Esclareça a modalidade se estiver ambígua.
2. Antes de agir, apresente repositório, origem, destino, remoto (se houver),
   operação e etapas ignoradas (homologação, piloto, aprovações), com os riscos.
   Use a ferramenta de perguntas para obter confirmação explícita após o aviso.
3. A confirmação vale apenas para as operações discriminadas. Pode cobrir merge
   local + push normal se ambos forem descritos; não vale para outras branches,
   outro remoto, novas alterações ou operações futuras. Uma confirmação vigente
   não deve ser pedida repetidamente sem mudança de escopo.
4. Confira o estado do clone, as referências atuais e os testes relevantes antes
   de executar. Não inclua alterações locais alheias. Se o escopo mudar, informe
   a mudança e obtenha nova confirmação. Não invente testes/aprovações.
5. Para push normal confirmado, publique somente o SHA revisado na ref confirmada
   (`git push <remoto> <sha>:refs/heads/<branch>`), apenas se continuar
   fast-forward em relação à ref remota atual. Não persista a autorização.
6. Confirmação de merge/push **não autoriza force-push, rebase, reset destrutivo,
   reescrita de histórico, exclusão de branch nem mudança de proteção**. Essas
   operações exigem avaliação e autorização separadas.
7. A confirmação não concede permissões na plataforma. Se o servidor recusar, pare,
   informe a rejeição e ofereça MR ou atuação de alguém autorizado. Não tente
   contornar, pedir credenciais nem assumir acesso aos administradores.
8. Verifique o resultado e diferencie merge local, push aceito e MR integrado.
   Não diga que a `main` remota mudou se apenas o merge local foi concluído.

## Release: gerar o `.exe` antes da tag
Ao **publicar uma versão** (app com executável), gere o `.exe` conforme a skill
`gerar-exe`: atualize `__version__` e `CHANGELOG.md` antes da
homologação, gere/valide o piloto a partir de `homolog`, obtenha a aprovação,
integre em `main` por MR, gere/valide o pacote final a partir de `main` e só
então crie a tag `vX.Y.Z`. Nunca declare builds ou aprovações que não foram
executados/confirmados.
O piloto nunca é renomeado como pacote definitivo: gere novamente na `main`.
Não classifique branch desconhecida como produção nem escolha manualmente o canal.

## Procedimento
1. Identifique a tarefa (commit, branch/merge/push/MR ou versão).
2. Abra o documento correspondente em `guia-skills/docs/git/`.
3. Para fluxo de branch/MR, confira o destino e aplique as regras de confirmação
   de exceções acima.
4. Aplique o padrão e valide contra os exemplos do guia.

## Mensagens de commit (detalhe)

### Regras obrigatórias
- Título: `tipo(escopo): descrição curta` — sem escopo: `tipo: descrição curta`.
- Em minúsculas (exceto siglas técnicas), sem ponto final, até ~72 caracteres.
- Verbo no presente: "adiciona", "corrige", "remove", "ajusta".
- Corpo opcional em bullets curtos; evite textos genéricos como "ajustes".
- É proibido atribuir coautoria ao Copilot em qualquer operação ou artefato Git:
  commits (inclusive squash e merge commits), merges, mensagens ou trailers,
  PRs/MRs, releases, tags e demais registros. Não adicione, preserve nem sugira
  essa atribuição em metadados, descrições ou textos relacionados.
- Tipo extra além dos do resumo: `revert` (reversão de commit).
- Escopo curto e estável (ex.: `relatorio`, `parser`, `build`, `logs`, `io`).
- Quebra de compatibilidade: no corpo, `BREAKING CHANGE: <impacto objetivo>`.

### Saída esperada
1. Uma versão em uma linha.
2. Uma versão completa com corpo (quando fizer sentido).

```text
feat(relatorio): adiciona feedback de progresso no console

- mostra andamento por servidor no formato [x/y]
- exibe resumo final com totais de avisos e erros
```

### Checklist antes de responder
- O tipo condiz com a mudança? O escopo é consistente com o módulo alterado?
- A descrição está específica e curta, sem ponto final?
- O corpo está objetivo e sem repetição?
