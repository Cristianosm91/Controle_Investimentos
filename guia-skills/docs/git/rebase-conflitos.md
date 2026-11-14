# Guia — Rebase e Resolução de Conflitos

## Objetivo

Manter o histórico limpo e a sua branch de desenvolvimento sempre atualizada
com `homolog` antes de abrir o Merge Request, sabendo resolver conflitos com
segurança.

---

## 1. Merge vs. Rebase (a diferença em 1 minuto)

Sua branch nasceu de um ponto de `homolog`. Enquanto você trabalhava, `homolog`
avançou. Para incorporar o que mudou, há dois caminhos:

- **Merge** (`git merge homolog`): cria um "commit de merge" juntando as histórias.
  Preserva tudo, mas polui o histórico com merges.
- **Rebase** (`git rebase homolog`): **reaplica** os seus commits por cima de `homolog`
  atualizada, como se você tivesse começado agora. Histórico **linear e limpo**.

> Regra da equipe: use **rebase para atualizar a sua branch** antes do MR.
> **Nunca** faça rebase de uma branch compartilhada/já publicada que outra
> pessoa esteja usando.

---

## 2. Atualizar sua branch com `homolog` (rebase)

```bash
# 1. Atualize homolog
git checkout homolog
git pull origin homolog

# 2. Volte para a sua branch e faça o rebase
git checkout feature/minha-tarefa
git rebase homolog
```

Atalho equivalente, direto do remoto:

```bash
git pull --rebase origin homolog
```

Dica: torne o `pull` sempre rebase por padrão (evita merges acidentais):

```bash
git config --global pull.rebase true
```

---

## 3. Resolvendo conflitos passo a passo

Se durante o `rebase` (ou `merge`) o Git encontrar linhas que mudaram dos dois
lados, ele **pausa** e marca os arquivos em conflito.

### 3.1. Ver o que está em conflito

```bash
git status
```

Os arquivos aparecem em **"Unmerged paths"**.

### 3.2. Entender os marcadores

O Git insere marcadores no arquivo:

```text
  <<<<<<< HEAD
  código que já estava em homolog (ou no destino)
  =======
  código que veio da sua branch
  >>>>>>> feature/minha-tarefa
```

- Acima do `=======` → versão do **destino** (`homolog`, no rebase).
- Abaixo do `=======` → versão da **sua** alteração.

Edite o trecho deixando **apenas o código final correto** e **remova** as três
linhas de marcação (`<<<<<<<`, `=======`, `>>>>>>>`).

### 3.3. Marcar como resolvido e continuar

```bash
git add caminho/do/arquivo-resolvido
git rebase --continue
```

Repita até o rebase terminar. Se aparecerem mais conflitos, resolva e
`--continue` novamente.

### 3.4. Se algo der errado — abortar

Volta tudo ao estado anterior, sem estrago:

```bash
git rebase --abort
```

(No caso de merge: `git merge --abort`.)

---

## 4. Publicar a branch após o rebase

Como o rebase **reescreve** os commits, o push normal é recusado. Use o
force **seguro**, que só sobrescreve se ninguém mais tiver empurrado nada:

```bash
git push --force-with-lease
```

> ⚠️ Use `--force-with-lease`, **nunca** `--force` puro. O `--force` pode apagar
> o trabalho de outra pessoa; o `--force-with-lease` aborta se o remoto mudou.

---

## 5. Boas práticas

- Faça rebase **cedo e com frequência** — conflitos pequenos são fáceis.
- Commits pequenos e coesos geram conflitos menores.
- Se o conflito for grande/confuso, `git rebase --abort` e peça ajuda a quem
  mexeu no arquivo.
- Ferramenta visual ajuda: `git mergetool` ou o editor de conflitos do VS Code.

---

## Checklist antes de abrir o Merge Request

- [ ] `git pull --rebase origin homolog` executado (branch atualizada).
- [ ] Conflitos resolvidos e testados.
- [ ] Histórico limpo (sem commits de "merge homolog" desnecessários).
- [ ] `git push --force-with-lease` feito (se houve rebase).
