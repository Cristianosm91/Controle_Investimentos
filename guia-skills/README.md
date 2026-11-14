# Guia — Padrões reutilizáveis para projetos

Central de padrões reutilizáveis para novos apps (web/pywebview, PyQt5 e console):
UX/UI, segurança e fluxo Git — mais as skills do Copilot que as aplicam.

> Nos projetos de destino, as cópias usam o nome `guia-skills`. O atualizador migra cópias antigas `Guia` e `Regras`.

## Estrutura

```text
Guia/
├── README.md               ← este índice
├── CHANGELOG.md            ← histórico de versões deste repositório
├── CONTRIBUTING.md         ← como adicionar/alterar regras e skills
├── .gitignore              ← arquivos que não vão para o repositório
├── .gitattributes          ← fim de linha (LF) e Git LFS para vídeos/GIFs/.ai
├── .github/
│   ├── instructions/       ← instruções aplicadas automaticamente (applyTo)
│   ├── prompts/            ← prompts reutilizáveis (/commit-message)
│   └── skills/             ← ÚNICO local das skills (uma pasta por skill + SKILL.md)
├── docs/
│   ├── git/                ← commits, branches, versionamento, tag/release, proteção da main...
│   ├── ux/                 ← barra de título, versão no header, responsividade/DPI
│   └── seguranca/          ← salvar senha (DPAPI)
├── Versionamento/          ← cópia distribuível dos guias e skills Git
└── scripts/
    ├── atualizar_skills.py ← replica esta pasta para as cópias guia-skills dos projetos
    └── copiar_skills.py    ← copia esta pasta para um projeto que ainda não a tem
```

---

## Índice

### UX / UI

| Documento | Assunto | Aplica-se a |
|---|---|---|
| [docs/ux/barra-de-titulo.md](docs/ux/barra-de-titulo.md) | Barra de título frameless (custom chrome), ícone superior do Windows, controles minimizar/maximizar/fechar, cantos arredondados e `AppUserModelID` | pywebview e PyQt5 (WebEngine) |
| [docs/ux/versao-header.md](docs/ux/versao-header.md) | Versão da aplicação no header, ao lado do título (`Nome vMAJOR.MINOR.CORREÇÃO`), obtida de fonte única (`__version__`) — sem hardcode nem duplicidade | web, pywebview, PyQt5 e console |
| [docs/ux/responsividade-dpi.md](docs/ux/responsividade-dpi.md) | Responsividade e escala DPI (barras fixas, conteúdo rolável, defaults que cabem a 175%) | web/pywebview |

### Git / Fluxo de trabalho

| Documento | Assunto |
|---|---|
| [docs/git/commits.md](docs/git/commits.md) | Mensagens de commit no padrão Conventional Commits (tipos, escopo, corpo, exemplos) |
| [docs/git/branches.md](docs/git/branches.md) | Padrão de branches (nomenclatura `feature/`, `fix/`, `docs/`, `refactor/` e fluxo de merge) |
| [docs/git/versionamento.md](docs/git/versionamento.md) | Política de versionamento `MAJOR.MINOR.CORREÇÃO`, tags e changelog |
| [docs/git/README.md](docs/git/README.md) | Introdução ao Git/GitLab e demais guias: proteção da `main`, rebase/conflitos, autenticação, tag/Release |
| [Versionamento/README.md](Versionamento/README.md) | Cópia independente dos guias, skills e instruções para compartilhar com outros projetos |

### Segurança

| Documento | Assunto | Aplica-se a |
|---|---|---|
| [docs/seguranca/salvar-senha.md](docs/seguranca/salvar-senha.md) | "Lembrar senha": salvar/ler/apagar credencial com a DPAPI do Windows (`CryptProtectData`/`CryptUnprotectData` via `ctypes`), sem libs externas | web, pywebview e PyQt5 (Windows) |

### Skills (`.github/skills/`)

| Skill | Uso | Regras de referência |
|---|---|---|
| [app-ux](.github/skills/app-ux/SKILL.md) | Barra de título, ícone, versão no header, DPI | `docs/ux/` |
| [gerar-exe](.github/skills/gerar-exe/SKILL.md) | Gerar `.exe` com PyInstaller (ícone, `--add-data`, `_MEIPASS`) | `docs/ux/`, `docs/git/versionamento.md` |
| [git-workflow](.github/skills/git-workflow/SKILL.md) | Commits, branches, merge/push com confirmação (proteção de `homolog`/`main`), versão, tag/Release | `docs/git/` |
| [salvar-senha](.github/skills/salvar-senha/SKILL.md) | "Lembrar senha" com DPAPI | `docs/seguranca/` |
| [redigir-dados-sensiveis](.github/skills/redigir-dados-sensiveis/SKILL.md) | Anonimizar dados sensíveis em screenshots (Loja/PDV/NSU/Valor, usuário, caminhos) | — |
| [gerar-pdf](.github/skills/gerar-pdf/SKILL.md) | Montar PDF/carrossel a partir de imagens | — |
| [qa-application-auditor](.github/skills/qa-application-auditor/SKILL.md) | Auditoria de QA/estabilidade (modos review/test/fix/full): travamentos, vazamentos, performance, segurança, plano de testes e parecer com evidências | `references/`, `templates/` e `scripts/` da própria skill |
| [software-engineering-refactoring](.github/skills/software-engineering-refactoring/SKILL.md) | Análise e refatoração segura e incremental (Clean Code, SOLID, modularização, acoplamento/coesão, erros, logging, testabilidade, segurança) preservando comportamento | — |
| [qa-appsec](.github/skills/qa-appsec/SKILL.md) | Auditoria defensiva de segurança e privacidade (inclui checklist de app web local em `localhost`) | `checklists/`, `references/`, `templates/` da própria skill |

#### Qualidade de produção

Todas validam o que existe (e o que for adicionado) **sem alterar regras de negócio ou funcionalidades
por conta própria**: modo padrão `review` somente leitura, `fix` apenas com pedido e confirmação.

| Skill | Uso |
|---|---|
| [prontidao-producao](.github/skills/prontidao-producao/SKILL.md) | **Orquestrador**: avalia a aplicação, uma funcionalidade ou um diff em 13 pilares, chama as skills abaixo e emite parecer PRONTO / COM RESSALVAS / NÃO PRONTO / INCONCLUSIVO; inclui a Definition of Done |
| [calculos-financeiros-fiscais](.github/skills/calculos-financeiros-fiscais/SKILL.md) | Precisão, arredondamento, câmbio, rentabilidade, regras fiscais com vigência, casos de referência e testes de propriedade |
| [migracoes-banco](.github/skills/migracoes-banco/SKILL.md) | Migrações (Alembic ou equivalente): drift modelo × migração, upgrade/downgrade, dados existentes, backups antigos |
| [backup-recuperacao](.github/skills/backup-recuperacao/SKILL.md) | RPO/RTO, retenção, integridade, testes de restauração e cenários de desastre |
| [integracoes-externas](.github/skills/integracoes-externas/SKILL.md) | Timeouts, retries, rate limit, cache, dado desatualizado, jobs agendados e testes com mocks |
| [observabilidade-logs](.github/skills/observabilidade-logs/SKILL.md) | Logs estruturados sem dados pessoais, tratamento de erros, healthcheck, diagnóstico |
| [privacidade-dados](.github/skills/privacidade-dados/SKILL.md) | Inventário, minimização, mascaramento, exclusão e higiene de dados pessoais |
| [web-ux-acessibilidade](.github/skills/web-ux-acessibilidade/SKILL.md) | WCAG 2.2 AA, estados de tela, formulários pt-BR, responsividade (SPAs web) |
| [testes-e2e](.github/skills/testes-e2e/SKILL.md) | Playwright: matriz funcionalidade × cenário, dados fictícios, mocks, axe-core |
| [ci-cd-release](.github/skills/ci-cd-release/SKILL.md) | Pipeline (GitHub Actions/GitLab CI) com lint, testes, build, auditoria de dependências, secret scanning e release |
| [documentacao-funcional](.github/skills/documentacao-funcional/SKILL.md) | README, CHANGELOG, FAQ, regras de cálculo e API sincronizados com o código |

### Instructions e prompts (`.github/`)

| Arquivo | Quando atua |
|---|---|
| [app-ux.instructions.md](.github/instructions/app-ux.instructions.md) | Automático ao editar front-end de apps (`**/web/**`, `**/static/**`, `**/templates/**`, `**/App*.py`) |
| [commit-message.prompt.md](.github/prompts/commit-message.prompt.md) | Sob demanda (`/commit-message`): gera mensagem de commit no padrão |

> Para criar uma skill ou regra nova, siga o [CONTRIBUTING.md](CONTRIBUTING.md).

---

## Como usar

**Configuração (uma vez):**
1. Clone o repositório (requer [Git LFS](https://git-lfs.com/) para vídeos/GIFs) e abra a pasta no VS Code.
2. Recarregue a janela (`Ctrl+Shift+P` → **Developer: Reload Window**) para o Copilot carregar skills e instructions.

Não há hook local: a proteção de `homolog`/`main` no clone é aplicada pela skill
`git-workflow` (além das proteções obrigatórias do GitLab).
Exceções para MR, merge local e push normal em `main`/`homolog` exigem confirmação
específica após aviso dos riscos. Não liberam force-push nem superam permissões
do GitLab; veja o [protocolo](docs/git/branches.md#exceções-ao-fluxo).

**No dia a dia:**
1. Ao criar um novo app, leia os documentos de **UX/UI** acima.
2. Copie os trechos de HTML/CSS/Python indicados e ajuste títulos/cores.
3. Siga o checklist de cada documento antes de gerar o `.exe`.
4. Para o versionamento e o dia a dia no Git, siga os guias de **Git / Fluxo de trabalho**.

## Como acionar as skills

No chat do Copilot (modo **Agent**), há duas formas:

- **Direto:** digite `/` + nome da skill (ex.: `/gerar-pdf`) e descreva o pedido.
- **Por texto:** escreva o pedido normalmente; a skill é acionada pelas palavras-chave.

| Skill | O que digitar (exemplo) |
|---|---|
| `app-ux` | `/app-ux aplique a barra de título frameless neste app` |
| `gerar-exe` | `/gerar-exe gere o executável do MeuApp.py` |
| `git-workflow` | `/git-workflow gere a mensagem de commit das minhas alterações` |
| `salvar-senha` | `/salvar-senha implemente o "Lembrar senha" na tela de login` |
| `redigir-dados-sensiveis` | `/redigir-dados-sensiveis esconda Loja, PDV e NSU deste print` |
| `gerar-pdf` | `/gerar-pdf junte img1.png, img2.png e capa.svg em carrossel.pdf` |
| `qa-application-auditor` | `/qa-application-auditor review` (só analisa) · `test` (cria e roda testes) · `fix` (corrige) · `full` (tudo) — ex.: `/qa-application-auditor full neste projeto` |
| `software-engineering-refactoring` | `/software-engineering-refactoring refatore o módulo de exportação separando UI e regra de negócio` |

Prompt reutilizável: `/commit-message` gera a mensagem de commit no padrão.

> Se a skill não aparecer ao digitar `/`, recarregue a janela (`Ctrl+Shift+P` → **Developer: Reload Window**).

## Pontos de atenção rápidos

- **Espaçamento do ponto/ícone → título:** use `margin` (ex.: `.tb-dot { margin: 0 9px }`),
  **não** `gap`. O QtWebEngine 5.15.2 (Chromium 83) ignora `gap` em flexbox.
- **Ícone:** use `.ico`; em janela frameless, reaplique via `WM_SETICON`.

---

## Manutenção

Este repositório é a **fonte canônica** e é versionado com Git (tags `vX.Y.Z`, ver
[CHANGELOG.md](CHANGELOG.md)). Ainda existem cópias antigas nos projetos
(`ProjetoA/…`, `ProjetoB/…`) com os caminhos antigos
(`REGRAS-*.md`, `Gitlab/`). Ao alterar uma regra, atualize aqui primeiro (fluxo em
[CONTRIBUTING.md](CONTRIBUTING.md)) e replique com o script abaixo.

### Atualizar as cópias da pasta guia-skills nos projetos

[scripts/atualizar_skills.py](scripts/atualizar_skills.py) procura todas as pastas `guia-skills` (e as antigas
`Guia` e `Regras`) dentro de um diretório (e subpastas) e as atualiza com o conteúdo desta pasta.
Na primeira execução, cada pasta antiga é renomeada para `guia-skills` antes da atualização; se já
existir um `guia-skills` ao lado, a cópia antiga é ignorada com aviso, e se a pasta estiver em uso
(ex.: aberta no VS Code), a renomeação falha e o destino é pulado.
Além de atualizar cada pasta, instala `.github/skills`, `.github/instructions` e
`.github/prompts` no `.github` do projeto que contém essa pasta. Os documentos e recursos continuam
em `guia-skills/`; os links dos arquivos instalados são ajustados para esse local. As cópias dessas três
pastas de configuração são removidas de `guia-skills/.github/`, e outros arquivos no `.github` da raiz
do projeto são preservados.

```powershell
# Modo interativo: pergunta o diretório de busca
py "<caminho>\Guia\scripts\atualizar_skills.py"

# 1. Ver o que seria feito (não altera nada)
python "<caminho>\Guia\scripts\atualizar_skills.py" --raiz "C:\...\Automacao" --simular

# 2. Atualizar (mostra o plano e pede confirmação)
python "<caminho>\Guia\scripts\atualizar_skills.py" --raiz "C:\...\Automacao"

# Origem diferente (também espelha e remove arquivos antigos do destino)
python atualizar_skills.py --origem "D:\Guia" --raiz .
```

| Opção | Efeito |
|---|---|
| `--origem` | Pasta Guia atualizada (padrão: a pasta onde o script está) |
| `--raiz` | Onde procurar as cópias (se omitido, o script pergunta) |
| `--simular` | Só mostra o plano; `--detalhes` lista cada arquivo |
| `--sim` | Não pede confirmação |
| `--incluir-git` | Atualiza também cópias que são repositórios Git (por padrão são ignoradas: use `git pull`) |
| `--nome` | Nome da pasta procurada (padrão: `guia-skills`; as antigas `Guia` e `Regras` são renomeadas) |

O script substitui o conteúdo sincronizado do destino pelo da origem sem criar backup. Arquivos
removidos não são recuperáveis pelo script; a origem canônica deve estar commitada no Git antes da
execução. Rode primeiro com `--simular` e revise a lista, especialmente os itens `[remover]`.

Nunca copia `.git`, `.vscode`, `__pycache__`, `build/`, `dist/`, `.env`, `credencial.bin`,
`*.pem`/`*.key`, `*.zip` nem temporários — esses itens também são preservados no destino.
A pasta `scripts/` (com o próprio `atualizar_skills.py`) fica **somente na origem** e é preservada
nos destinos caso já exista. `--espelhar` continua aceito por compatibilidade, mas é redundante.

### Copiar a pasta Guia para um novo projeto

[scripts/copiar_skills.py](scripts/copiar_skills.py) cria `<projeto>\guia-skills` com o conteúdo desta
pasta (mesmos filtros do `atualizar_skills.py`, sem `scripts/`) e instala `.github/skills`,
`.github/instructions` e `.github/prompts` no `.github` do projeto, sem remover o que já existe lá.
Se `<projeto>\guia-skills`, `<projeto>\Guia` ou `<projeto>\Regras` já existir, nada é copiado:
use o `atualizar_skills.py`.

```powershell
# Modo interativo: pergunta o projeto de destino
py "<caminho>\Guia\scripts\copiar_skills.py"

# 1. Ver o que seria copiado (não altera nada)
python "<caminho>\Guia\scripts\copiar_skills.py" --destino "C:\...\MeuProjeto" --simular

# 2. Copiar (mostra o plano e pede confirmação)
python "<caminho>\Guia\scripts\copiar_skills.py" --destino "C:\...\MeuProjeto"
```

| Opção | Efeito |
|---|---|
| `--destino` | Pasta do projeto (ou `<projeto>\guia-skills`); se omitido, o script pergunta |
| `--origem` | Pasta Guia de origem (padrão: a pasta onde o script está) |
| `--simular` | Só mostra o plano; `--detalhes` lista cada arquivo |
| `--sim` | Não pede confirmação |
| `--nome` | Nome da pasta criada no destino (padrão: `guia-skills`) |

O script importa funções do `atualizar_skills.py`; mantenha os dois juntos em `scripts/`.
