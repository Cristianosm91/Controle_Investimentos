# Como contribuir

## Onde cada coisa fica

| Tipo | Local | Nome |
|---|---|---|
| Regra/guia (documento completo) | `docs/<tema>/` (`git`, `ux`, `seguranca`...) | kebab-case, ex.: `barra-de-titulo.md` |
| Skill do Copilot | `.github/skills/<nome>/SKILL.md` | pasta = `name` do frontmatter |
| Script de uma skill | `.github/skills/<nome>/scripts/` | snake_case `.py` |
| Instruction automática | `.github/instructions/<nome>.instructions.md` | com `applyTo` |
| Prompt reutilizável | `.github/prompts/<nome>.prompt.md` | — |
| Imagens, vídeos, ícones | `assets/<tema>/` | — |
| Script utilitário do repositório | `scripts/` | snake_case `.py` |

Esses são os caminhos canônicos dentro do repositório Guia. Ao sincronizar para um projeto que
mantém `Guia/` como subpasta, o script instala as configurações Copilot em `.github/` na raiz
consumidora e ajusta os links para os documentos e recursos em `Guia/`.

## Criar uma skill

1. Crie `.github/skills/<nome>/SKILL.md` com frontmatter:
   ```yaml
   ---
   name: <nome>            # igual ao nome da pasta
   description: 'Use ao ... Palavras-gatilho: ...'
   ---
   ```
2. Mantenha o `SKILL.md` curto: resumo + checklist. Regras extensas vão em `docs/<tema>/`
   e a skill aponta para elas com link relativo (`../../../docs/<tema>/arquivo.md`).
   Ao replicar a pasta `Guia` com `scripts/atualizar_skills.py`, a skill é instalada no
   `.github/skills/` da raiz do projeto consumidor e os links são ajustados para `guia-skills/docs/`.
3. Uma regra tem **um único dono**: não copie o conteúdo entre skills, referencie.
4. Registre a skill na tabela do [README.md](README.md).

## Fluxo de alteração

1. Crie uma branch conforme [docs/git/branches.md](docs/git/branches.md).
2. Faça commits no padrão de [docs/git/commits.md](docs/git/commits.md).
3. Atualize o [CHANGELOG.md](CHANGELOG.md) na seção `[Não publicado]`.
4. Abra o Merge Request; após o merge, crie a tag conforme [docs/git/tag-release.md](docs/git/tag-release.md).
5. Verifique se nenhum link relativo quebrou após mover/renomear arquivos.
6. Replique para as cópias nos projetos com `scripts/atualizar_skills.py` (rode antes com `--simular`).
