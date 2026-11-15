# Git / GitLab — Fluxo de trabalho da equipe

Pasta com as regras relacionadas a **branches, commits, versionamento
e integração via GitLab**. É a fonte única desses guias em `Guia/`; a skill
correspondente fica em [.github/skills/git-workflow](../../.github/skills/git-workflow/SKILL.md).

> **Usa GitHub?** As regras são as mesmas; troque MR por Pull Request e "protected branches" por
> branch protection rules/rulesets. A tabela de equivalência está na skill `git-workflow`.

> **É a sua primeira vez com Git/GitLab?** Comece pela seção
> [Para quem está começando](#para-quem-está-começando) abaixo. Depois volte aqui
> e siga os guias na ordem do índice.

---

## Para quem está começando

Esta seção explica, **sem jargão**, o que é o GitLab e como o trabalho flui.
Se você já conhece Git, pule direto para o [Índice](#conteúdo).

### O que é isso, em uma frase

- **Git** é um programa que guarda o **histórico** do seu código — como um
  "Ctrl+Z infinito" que nunca perde nada.
- **GitLab** é o **site** onde esse histórico fica guardado na nuvem, para o time
  todo compartilhar, revisar e publicar versões.

> Analogia: o **Git** é o controle de versões de um documento; o **GitLab** é o
> "Google Drive" onde esse documento vive e onde as pessoas comentam e aprovam.

### Termos que você precisa entender

| Palavra | O que é (em linguagem simples) |
|---|---|
| **Repositório** (repo) | A pasta do projeto inteira, com todo o histórico. |
| **Commit** | Um "ponto de salvamento" com uma mensagem explicando o que mudou. |
| **Branch** | Uma "linha do tempo paralela" para você mexer sem quebrar a dos outros. |
| **`homolog`** | A branch de homologação, destino dos MRs de desenvolvimento. |
| **`main`** | A branch **oficial**, protegida e destino somente do MR de `homolog`. |
| **Push** | Enviar seus commits da máquina para o GitLab (a nuvem). |
| **Merge Request (MR)** | Pedido para revisar e integrar uma mudança em `homolog` ou `main`, conforme o fluxo. |

### Por que não trabalhar direto na `main`?

Porque `homolog` e `main` são branches compartilhadas e protegidas. Cada tarefa
ganha uma branch própria; o MR leva a mudança para homologação e, depois dos
testes e aprovações, outro MR leva `homolog` para `main`.

### O fluxo do dia a dia (a rotina que se repete)

```text
Atualizo homolog
  → crio feature/ | refactor/ | fix/ | docs/
  → desenvolvo, commito, testo e recebo revisão do agente
  → MR para homolog
  → 2 ou 3 pessoas testam; pacote piloto aprovado
  → MR homolog → main (mínimo de 2 aprovações)
  → pacote final para produção
```

Consulte [branches.md](branches.md) para o fluxo completo e as exceções.

### O que dá para fazer no GitLab (funcionalidades e possibilidades)

- **Issues** — lista de tarefas/bugs. Cada demanda vira uma issue com número
  (ex.: `#42`), e o commit/MR pode fechá-la automaticamente (`Closes #42`).
- **Merge Requests** — código de desenvolvimento é revisado antes de entrar em
  `homolog`; depois da homologação, outro MR leva `homolog` para `main`.
- **Branches protegidas** — trava `homolog` e `main` contra push direto (ver
  [protecao-main.md](protecao-main.md)); o MR para `main` requer pelo menos 2 aprovações.
- **Tags e Releases** — marcam versões oficiais (ex.: `v1.2.0`) e publicam as
  novidades (ver [tag-release.md](tag-release.md)).
- **CI/CD (pipelines)** — o GitLab pode **testar e gerar o `.exe`
  automaticamente** a cada envio, sem ninguém fazer à mão.
- **Histórico e culpa saudável** (`blame`) — dá para ver quem mudou cada linha e
  por quê, lendo as mensagens de commit.

### Os 5 comandos que resolvem 90% do dia

```bash
git status                 # o que mudou / em que branch estou
git checkout -b feature/x  # crio e entro numa branch nova
git add .                  # separo as mudanças para salvar
git commit -m "feat: ..."  # salvo com uma mensagem (ver commits.md)
git push origin feature/x  # envio para o GitLab
```

> Não decore: consulte esta tabela até virar hábito. Os guias abaixo aprofundam
> cada passo.

### Primeiros passos (uma vez só, para configurar a máquina)

1. Configure seu nome e e-mail:
   ```bash
   git config --global user.name "Seu Nome"
   git config --global user.email "seu.email@empresa.com"
   ```
2. Configure o acesso ao GitLab (SSH ou token) — ver
   [autenticacao.md](autenticacao.md).
3. Baixe o projeto (**clone**):
   ```bash
   git clone <url-do-projeto-no-gitlab>
   ```
4. Pronto — agora siga o "fluxo do dia a dia" acima para cada tarefa.

---

## Conteúdo

| Documento | Assunto |
|---|---|
| [branches.md](branches.md) | Nomenclatura (`feature/`, `refactor/`, `fix/`, `docs/`) e fluxo `homolog` → `main` |
| [commits.md](commits.md) | Mensagens no padrão Conventional Commits (tipos, escopo, corpo, exemplos) |
| [versionamento.md](versionamento.md) | Versionamento `MAJOR.MINOR.CORREÇÃO`, tags e changelog |
| [protecao-main.md](protecao-main.md) | Bloqueio de push em `homolog` e `main` (GitLab + confirmação pela skill) |
| [rebase-conflitos.md](rebase-conflitos.md) | Atualizar branch com rebase e resolver conflitos com segurança |
| [autenticacao.md](autenticacao.md) | Autenticação por SSH/PAT e commits assinados (selo *Verified*) |
| [tag-release.md](tag-release.md) | Fluxo de tag `vX.Y.Z` e Release ligado ao `CHANGELOG.md` e ao versionamento |
| [.github/skills/git-workflow/SKILL.md](../../.github/skills/git-workflow/SKILL.md) | Skill de commits (gerar/validar mensagem) + branches + versão |

---

## Fluxo resumido (desenvolvimento → homologação → produção)

```bash
# 1. Atualizar homolog
git checkout homolog
git pull origin homolog

# 2. Criar a branch da tarefa
git checkout -b feature/exportacao-csv

# 3. Desenvolver e commitar no padrão
git add .
git commit -m "feat(export): adiciona exportação para CSV"

# 4. Publicar a branch de desenvolvimento no GitLab
git push origin feature/exportacao-csv

# 5. Abrir MR feature/... -> homolog
# 6. Após merge em homolog, 2 ou 3 pessoas testam e aprovam o piloto
# 7. Abrir MR homolog -> main (mínimo de 2 aprovações)
# 8. Após o merge, gerar o pacote final para produção
```

---

## O que ainda falta para um desenvolvimento profissional com GitLab

Os guias atuais cobrem o **dia a dia** (branch, commit, versão), a **proteção de
`homolog` e `main`**, **rebase/conflitos**, **autenticação/assinatura** e o
fluxo de **tag/Release**.
Para fechar um fluxo profissional completo no GitLab, ainda faltam:

1. **`merge-request.md`** — como abrir um MR de verdade: título/descrição,
   *reviewers* e *approvers*, vincular a issue (`Closes #123`), regra de
   *squash* e "Delete source branch". Hoje o fluxo cita "abrir MR" mas não
   detalha.
2. **Template de MR e de Issue** (`.gitlab/merge_request_templates/` e
   `.gitlab/issue_templates/`) — padroniza descrição, checklist e critérios de
   aceite direto na interface do GitLab.
3. **CI/CD (`.gitlab-ci.yml`)** — pipeline mínima: lint, testes e build do
   `.exe` automático. Fecha o ciclo com a skill `gerar-exe`.
4. **`CONTRIBUTING.md` + `.gitignore` padrão** — porta de entrada única e
   `.gitignore` base (Python/PyInstaller: `__pycache__/`, `build/`, `dist/`,
   `*.spec`, `venv/`) para não versionar lixo.

### Já cobertos nesta pasta

- ✅ **Proteção de `homolog` e `main`** — [protecao-main.md](protecao-main.md)
- ✅ **Rebase e resolução de conflitos** — [rebase-conflitos.md](rebase-conflitos.md)
- ✅ **Autenticação SSH/PAT e commits assinados** — [autenticacao.md](autenticacao.md)
- ✅ **Fluxo de tag/Release ligado ao CHANGELOG e versionamento** — [tag-release.md](tag-release.md)

> Sugestão de próximo passo: os itens **1, 2 e 3** (Merge Request, templates e
> CI/CD) são os de maior impacto restante para profissionalizar o fluxo.
