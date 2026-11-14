# Guia — Proteção de `homolog` e `main`

## Objetivo

Garantir que commits sejam feitos nas branches de desenvolvimento
(`feature/`, `refactor/`, `fix/` e `docs/`) e que `homolog` e `main` recebam
alterações por Merge Request no fluxo padrão:

```text
feature/ | refactor/ | fix/ | docs/  →  homolog  →  main
```

As proteções no GitLab são obrigatórias. No clone, a skill `git-workflow`
é a barreira adicional (sem hook local); não substitui as permissões do servidor.

## 1. Criar `homolog` se ainda não existir

Um Maintainer/Owner deve criar `homolog` no GitLab a partir da `main` atual
(Repository → Branches → New branch) e, em seguida, protegê-la pelas
configurações abaixo. Criar a branch a partir da `main` inicializa o fluxo; não
é um atalho para integrar mudanças de desenvolvimento em produção.

Defina `main` como branch padrão em **Settings → Repository → Default branch**.

## 2. Proteger as branches no GitLab — obrigatório

Um Maintainer/Owner configura cada branch em **Settings → Repository →
Protected branches**:

| Branch | Allowed to push and merge | Allowed to merge | Force push |
|---|---|---|---|
| `homolog` | `No one` | `Developers + Maintainers` (ou papel mais restrito) | Off |
| `main` | `No one` | `Maintainers` (ou papel mais restrito) | Off |

Confirme os nomes exatos e as permissões disponíveis na versão do GitLab usada
pelo projeto. Nenhum membro deve poder fazer push direto nessas branches.

### Merge Requests e aprovações

- MR de desenvolvimento: branch `feature/`, `refactor/`, `fix/` ou `docs/`
  para `homolog`.
- MR de produção: `homolog` para `main`, após homologação e aprovação do piloto.
- Exija pelo menos **2 aprovações** no MR para `main`.
- Para MR de desenvolvimento para `homolog`, recomenda-se pelo menos 1
  aprovação humana, além dos testes e da revisão do agente.
- Ative **Pipelines must succeed** quando o projeto tiver CI.
- Recomenda-se habilitar exclusão da branch de origem após o merge, somente para
  branches de desenvolvimento; nunca excluir `homolog` nem `main`.
- Recomenda-se configurar o *squash* de commits como incentivado ou obrigatório,
  conforme a política da equipe.

A regra de origem e destino deve ser reforçada nas configurações de MR/CI e
seguida pelos desenvolvedores e agentes. Proteção de branch, por si só, impede
push direto, mas não necessariamente restringe a origem de todo MR.

> Um `git push origin main` ou `git push origin homolog` deve ser recusado pelo
> servidor. O caminho normal é branch de desenvolvimento → MR → `homolog` →
> validação/piloto → MR → `main`.

## 3. Proteção no clone — feita pela skill

Não há hook local. No clone, a proteção é aplicada pelo agente por meio da skill
`git-workflow`: ele não faz commit, merge local, push nem MR envolvendo
`homolog`/`main` fora do fluxo padrão sem confirmação explícita, e recusa
`master` como destino.

### 3.1. Exceção após confirmação explícita

Siga [branches.md](branches.md#exceções-ao-fluxo). Antes da confirmação, apresente
repositório, origem, destino, remoto, SHAs, operações e riscos das etapas
ignoradas. Isso permite MR alternativo, merge local e/ou push **normal**,
conforme o escopo confirmado. Não vale como autorização permanente.

Antes do push confirmado, obtenha a ref remota atual (`git fetch`) e verifique
que é fast-forward (`git merge-base --is-ancestor <SHA remoto> <SHA local>`).
Não use uma remote-tracking ref desatualizada como prova do estado do servidor.
Se os SHAs ou o destino mudarem, reavalie e obtenha nova confirmação.
Publique somente o SHA revisado: `git push origin <sha>:refs/heads/main`.

Não use `--force`, `--force-with-lease`, `--all`, `--mirror` nem `--no-verify`.
Exclusão ou criação de branch protegida, force-push e reescrita de histórico
exigem autorização separada. Não desenvolva/commite diretamente na branch
protegida.

O GitLab continua autoritativo: com a configuração recomendada (`No one` para
push), o servidor rejeitará até o push confirmado. A confirmação não altera
permissões. Nesse caso, pare e ofereça MR ou atuação de alguém autorizado; não
tente contornar nem prometa contato com administradores.

### 3.2. Projetos que usavam o antigo hook

Se `git config --show-origin --get core.hooksPath` apontar para o antigo
`hooks`, `Regras/hooks` ou `Guia/hooks`, remova a configuração com
`git config --local --unset core.hooksPath`. Se a pasta tiver outros hooks
personalizados, preserve-os e avalie antes.

## 4. Padronizar `master` como `main`

Se o projeto ainda usar `master`, um Maintainer/Owner deve definir `main` como
branch padrão e ajustar as proteções antes de remover `master`. Não mantenha
duas branches principais.

### 4.1. Renomear localmente

```bash
git branch -m master main
```

### 4.2. Publicar `main` e remover `master` do servidor

```bash
git push -u origin main
git push origin --delete master
```

Se `master` estiver protegida no GitLab, primeiro desproteja-a ou altere a
branch padrão para `main` em **Settings → Repository → Default branch**. Depois,
confirme as proteções de `main` conforme este guia.

### 4.3. Evitar `master` em novos repositórios

```bash
git config --global init.defaultBranch main
```

## Checklist

- [ ] `homolog` criada a partir da `main` se ainda não existia.
- [ ] `homolog` e `main` protegidas contra push direto e force push.
- [ ] `main` definida como branch padrão.
- [ ] MR de desenvolvimento direcionado a `homolog`.
- [ ] MR de `homolog` para `main` exige no mínimo 2 aprovações.
- [ ] Pipeline obrigatória quando houver CI.
- [ ] Agente segue o protocolo de confirmação da skill `git-workflow`.
- [ ] Não há uma branch `master` concorrente.
