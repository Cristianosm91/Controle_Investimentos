# Guia — Fluxo de Tag e Release (ligado ao CHANGELOG e ao Versionamento)

## Objetivo

Padronizar como publicamos uma versão: definir a versão → atualizar o
`CHANGELOG.md` → validar em `homolog` → gerar piloto → integrar em `main` →
gerar pacote final → criar tag `vX.Y.Z` → publicar a Release no GitLab.

Este guia conecta três peças:

- [versionamento.md](versionamento.md) — decide qual é a próxima versão.
- [commits.md](commits.md) — os `feat`/`fix` viram as linhas do changelog.
- Este guia — leva a versão pelo fluxo de homologação até a Release.

## 1. Definir a próxima versão

Siga a regra de [versionamento.md](versionamento.md) (`MAJOR.MINOR.CORREÇÃO`):

| Mudança na versão | Quando |
|---|---|
| **MAJOR** (`2.0.0`) | Mudança grande / incompatível |
| **MINOR** (`1.3.0`) | Nova funcionalidade (`feat`) |
| **CORREÇÃO** (`1.2.4`) | Correção / ajuste (`fix`, `perf`) |

Atualize também a fonte única da versão no app (`__version__`), conforme o
padrão do header, antes de gerar o piloto.

## 2. Atualizar o `CHANGELOG.md`

O changelog é a lista legível das novidades por versão. Seguimos o formato
[Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/).

### 2.1. Estrutura do arquivo

```markdown
# Changelog

Todas as mudanças relevantes deste projeto são documentadas aqui.
O formato segue o Keep a Changelog e o versionamento segue MAJOR.MINOR.CORREÇÃO.

## [Não lançado]

## [1.2.0] - 2026-09-16
### Adicionado
- Exportação de relatório em CSV.

### Corrigido
- Trava do segundo download no app desktop.

### Alterado
- Ícone atualizado para a nova paleta de cores.

## [1.1.0] - 2026-08-30
### Adicionado
- Filtro de logs por horário.
```

Seções possíveis: **Adicionado**, **Alterado**, **Corrigido**, **Removido**,
**Depreciado**, **Segurança**.

### 2.2. Da mensagem de commit para o changelog

Os tipos de [commits.md](commits.md) mapeiam direto:

| Commit | Seção do changelog |
|---|---|
| `feat:` | Adicionado |
| `fix:` / `perf:` | Corrigido |
| `refactor:` / `chore:` / `style:` | Alterado (se relevante ao usuário) |
| `feat!:` / `BREAKING CHANGE:` | Alterado + nota de incompatibilidade |

Dica para levantar o que entrou desde a última tag:

```bash
git log v1.1.0..HEAD --pretty=format:"- %s"
```

## 3. Preparar e validar em `homolog`

A versão e o `CHANGELOG.md` devem ser atualizados em uma branch de
desenvolvimento, usando o prefixo correspondente à mudança (`feature/`,
`refactor/`, `fix/` ou `docs/`). Faça o MR para `homolog` conforme
[branches.md](branches.md).

Use a branch de desenvolvimento correspondente às mudanças da versão (não crie
uma branch de release com prefixo fora do padrão):

```bash
# Atualize a branch da tarefa a partir da homolog atual
git checkout homolog
git pull origin homolog
git checkout -b feature/minha-funcionalidade

# Atualize __version__ e CHANGELOG.md e faça os commits nesta branch
git add .
git commit -m "feat: adiciona a funcionalidade da versão 1.2.0"

# 3. Publique e abra o Merge Request para homolog
git push origin feature/minha-funcionalidade
# Abra o MR no GitLab: feature/minha-funcionalidade -> homolog
```

Use no exemplo o prefixo que corresponda à mudança real: `feature/`,
`refactor/`, `fix/` ou `docs/`. Se a versão não acompanhar uma funcionalidade
nova, não use `feature/` nem `feat:` apenas por ser uma atualização de versão.
Siga [branches.md](branches.md) e [commits.md](commits.md).

Depois do merge para `homolog`, 2 ou 3 pessoas executam os testes de
homologação. Se não houver falhas, gere e valide o **pacote piloto a partir de
`homolog`**. Registre a versão, os resultados dos testes e a aprovação do
piloto. Se forem encontrados problemas, corrija-os em uma nova branch de
desenvolvimento e percorra novamente o fluxo até `homolog`.

Para apps com executável, siga a skill `gerar-exe` para gerar e validar
o pacote piloto.

O gerador identifica automaticamente a branch conforme
[versionamento.md](versionamento.md): o primeiro piloto é
`<aplicacao>-piloto-v<versao>` (ex.: `gwcel-piloto-v1.2.0`); novos builds da
mesma versão recebem `-r1`, `-r2`, ... por reserva no histórico persistente.
Não informe manualmente o canal nem a revisão, não sobrescreva pilotos
anteriores e não use apenas o conteúdo de `dist` como contador.

## 4. Aprovar em produção e gerar o pacote final

Com o piloto aprovado, abra no GitLab o MR `homolog` → `main`. O MR deve ter
pelo menos **2 aprovações**. Depois do merge, gere e valide o **pacote final a
partir da `main`**. O pacote final deve corresponder ao código integrado e
aprovado; não publique o pacote piloto como se fosse o pacote final.

Para apps com executável, siga a skill `gerar-exe` também para gerar e
validar o pacote final.

O nome de produção é `<aplicacao>-v<versao>` (ex.: `gwcel-v1.2.0`), sem
`piloto` e sem revisão de piloto. Preserve a mesma versão aprovada; faça o
build do código integrado na `main`, sem renomear/reaproveitar o binário
de `homolog`. Origem não verificável deve bloquear a distribuição, nunca
ser tratada como produção.

## 5. Criar a tag `vX.Y.Z`

Crie a tag somente depois que a versão tiver sido integrada à `main` e o pacote
final tiver sido gerado e validado:

```bash
git checkout main
git pull

# Tag anotada (recomendada — guarda autor, data e mensagem)
git tag -a v1.2.0 -m "Release 1.2.0"

# Enviar a tag para o GitLab
git push origin v1.2.0
```

Conferir:

```bash
git tag
git show v1.2.0
```

Use sempre o prefixo `v` (ex.: `v1.2.0`), conforme
[versionamento.md](versionamento.md).

## 6. Publicar a Release no GitLab

A **Release** é a vitrine da tag: título, notas e anexos (ex.: o pacote final).

### 6.1. Pela interface

1. **Deploy → Releases → New release**.
2. **Tag name:** selecione `v1.2.0`.
3. **Release title:** `v1.2.0`.
4. **Release notes:** cole a seção correspondente do `CHANGELOG.md`.
5. Em **Release assets**, anexe o pacote final/artefatos, se houver.
6. **Create release**.

### 6.2. Automático via CI (opcional)

Quando houver `.gitlab-ci.yml`, dá para criar a Release automaticamente ao subir
uma tag, usando o `release-cli`:

```yaml
release_job:
  stage: release
  image: registry.gitlab.com/gitlab-org/release-cli:latest
  rules:
    - if: $CI_COMMIT_TAG
  script:
    - echo "Publicando release $CI_COMMIT_TAG"
  release:
    tag_name: $CI_COMMIT_TAG
    description: "Veja o CHANGELOG.md para os detalhes desta versão."
```

## 7. Comunicar

- Avise a equipe sobre a nova versão (canal/e-mail).
- Confirme que o `CHANGELOG.md` na `main` reflete a tag publicada.

## Checklist de release

- [ ] Versão decidida conforme [versionamento.md](versionamento.md).
- [ ] `__version__` atualizado (fonte única).
- [ ] `CHANGELOG.md` com a nova seção (data + itens).
- [ ] MR de desenvolvimento integrado em `homolog`.
- [ ] Homologação realizada por 2 ou 3 pessoas, sem falhas pendentes.
- [ ] Pacote piloto gerado e aprovado a partir de `homolog`.
- [ ] Nome do piloto contém `-piloto-`; revisão automática registrada sem colisões.
- [ ] MR `homolog` → `main` aprovado por pelo menos 2 pessoas e integrado.
- [ ] Pacote final gerado e validado a partir de `main` (`.exe`, se aplicável).
- [ ] Nome final segue `<aplicacao>-v<versao>`, sem `piloto` nem revisão de piloto.
- [ ] Tag `vX.Y.Z` criada e enviada (`git push origin vX.Y.Z`).
- [ ] Release publicada no GitLab com as notas do changelog.
- [ ] Equipe comunicada.
