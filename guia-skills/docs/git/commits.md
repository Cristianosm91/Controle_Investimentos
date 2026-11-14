# Guia de Mensagens de Commit

> Tutorial prático sobre como escrever boas mensagens de commit, usando o
> padrão mais adotado no mercado: **Conventional Commits**. Os exemplos foram
> retirados do histórico de um projeto de exemplo (`DownloadLogs`).

---

## 1. O que é um commit (e por que a mensagem importa)

Um **commit** é um "ponto de salvamento" no histórico do código. Cada commit
guarda *o que mudou*. A **mensagem** explica *o porquê* daquela mudança, em
poucas palavras.

Pense no histórico de commits como o **diário do projeto**. Daqui a 6 meses,
ninguém lembra por que uma linha foi alterada — a mensagem de commit é a
resposta.

> ❌ Mensagem ruim: `ajustes`, `correção`, `mudei o código`, `teste123`
> ✅ Mensagem boa: `fix: corrige travamento do segundo download no app desktop`

A segunda diz **o tipo** da mudança (correção), **onde** (download no app) e
**o quê** (travamento do segundo download) — tudo em uma linha.

---

## 2. O padrão mais usado no mercado: Conventional Commits

A maioria das empresas adota o padrão
[**Conventional Commits**](https://www.conventionalcommits.org). A estrutura é:

```
tipo(escopo opcional): descrição curta

corpo opcional explicando detalhes
```

Exemplo real deste projeto:

```
feat(download): achata logs do servidor em pasta única
└┬─┘ └───┬──┘   └──────────────┬──────────────────────┘
 │       │                     descrição (o que faz)
 │       escopo (onde mudou)
 tipo (categoria da mudança)
```

### Regras de ouro da descrição

- Em **minúsculas**, sem ponto final.
- No **imperativo/presente**: "adiciona", "corrige", "remove"
  (e não "adicionado", "corrigi").
  - Dica: imagine a frase *"Este commit vai ___"* → "vai **corrigir** o travamento".
- **Curta** (até ~50-72 caracteres). Detalhes vão no corpo.

---

## 3. Os tipos mais comuns (com exemplos do projeto)

| Tipo | Quando usar | Exemplo |
|------|-------------|---------|
| **feat** | Uma **funcionalidade nova** | `feat: app desktop para download de logs do servidor (PyQt5 + Flask)` |
| **fix** | **Correção de bug** | `fix: corrige travamento do segundo download no app desktop` |
| **chore** | Manutenção que **não muda comportamento** (ícone, dependência, config) | `chore: usa ícone app_icon.ico no app e build` |
| **docs** | Só **documentação** (README, comentários) | `docs: adiciona instruções de build no README` |
| **refactor** | Reorganiza código **sem mudar o que ele faz** | `refactor: separa backend de download em módulo próprio` |
| **style** | Formatação, espaços, ponto-e-vírgula (**sem lógica**) | `style: ajusta indentação do app.js` |
| **test** | Adiciona ou ajusta **testes** | `test: cobre filtro de logs por horário` |
| **perf** | Melhora de **desempenho** | `perf: reduz tempo de listagem de diretórios` |
| **build** / **ci** | Sistema de build ou automação | `build: inclui opengl32sw.dll no PyInstaller` |

> **Por que `chore` no commit do ícone?** Porque trocar o ícone **não adiciona
> função nova nem corrige bug** — é manutenção. Por isso não é `feat` nem `fix`.

---

## 4. O escopo (a parte entre parênteses)

O escopo é **opcional** e diz *qual parte do sistema* foi afetada. Ajuda a
filtrar o histórico.

```
feat(download): achata logs do servidor em pasta única
     └──┬───┘
     escopo: a área de "download"
```

Outros exemplos possíveis neste projeto: `feat(login)`, `fix(explorador)`,
`chore(build)`.

Use quando o projeto for grande. Em projetos pequenos, pode omitir
(como em `fix: corrige travamento...`).

---

## 5. O corpo da mensagem (quando explicar mais)

Para mudanças simples, **uma linha basta**. Para mudanças complexas, adicione
um **corpo** após uma linha em branco, explicando o **porquê** e o **como**.

Exemplo real (commit `fix`), encurtado:

```
fix: corrige travamento do segundo download no app desktop

Backend: resposta de streaming agora envia Connection: close,
evitando que o QtWebEngine reutilize a conexão keep-alive anterior.
Frontend: handler de submit envolto em try/catch/finally para
sempre reabilitar o botão Baixar.
```

Repare: o **título** diz o resultado ("corrige travamento"); o **corpo**
explica a causa técnica. Quem for ler depois entende sem abrir o código.

---

## 6. Mudanças que quebram compatibilidade (avançado)

Quando uma mudança **quebra** algo que já existia (ex: muda o nome de um
comando que outras pessoas usam), sinaliza-se com `!` ou com `BREAKING CHANGE:`
no corpo:

```
feat!: remove o campo "Subpasta" da API de download

BREAKING CHANGE: chamadas que enviavam "subpasta" precisam ser ajustadas.
```

Isso alerta a equipe de que **atenção extra** é necessária.

---

## 7. Por que vale a pena (benefícios práticos)

1. **Histórico legível** — dá para entender a evolução só lendo `git log`.
2. **Changelog automático** — ferramentas geram a lista de novidades a partir
   dos `feat`/`fix`.
3. **Versionamento automático** (SemVer): `fix` → versão 1.0.**1**,
   `feat` → 1.**1**.0, `BREAKING` → **2**.0.0.
4. **Facilita achar bugs** — `git log --grep "fix"` mostra todas as correções.
5. **Profissionalismo** — é o padrão esperado em equipes e em código aberto.

---

## 8. O histórico real deste projeto (estudo de caso)

Os 4 commits do `DownloadLogs`, do mais antigo ao mais novo:

```
76e818e  feat: app desktop para download de logs do servidor (PyQt5 + Flask)
6fe6bf1  fix: corrige travamento do segundo download no app desktop
3bb7644  feat(download): achata logs do servidor em pasta única
4fc2f48  chore: usa ícone app_icon.ico no app e build
```

O que cada um nos ensina:

- **`feat:`** (76e818e) — nasce o projeto: uma **funcionalidade nova** grande.
- **`fix:`** (6fe6bf1) — logo depois, um **bug** foi encontrado e corrigido.
- **`feat(download):`** (3bb7644) — **nova funcionalidade** com **escopo**,
  indicando que mexeu na área de download.
- **`chore:`** (4fc2f48) — **manutenção** visual (ícone), sem mudar
  comportamento.

Essa sequência conta uma história clara: *criou → corrigiu → melhorou →
poliu*. É exatamente isso que um bom histórico de commits deve fazer.

---

## 9. Resumo de bolso (cola para iniciantes)

```
tipo(escopo): descrição no imperativo, minúsculas, sem ponto final

Tipos: feat | fix | docs | style | refactor | perf | test | chore | build | ci

✅ feat: adiciona botão de exportar PDF
✅ fix: corrige cálculo de juros no extrato
✅ chore: atualiza dependências do projeto
❌ alterações feitas
❌ Corrigido o Bug.
❌ update
```

**Regra mental:** *"Se eu aplicar este commit, ele vai ___ "* — complete a
frase e essa é sua descrição.

## 10. Atribuição de coautoria

É proibido atribuir coautoria ao Copilot em qualquer operação ou artefato Git:
commits (inclusive squash e merge commits), merges, mensagens ou trailers,
PRs/MRs, releases, tags e demais registros. Não adicione, preserve nem sugira
essa atribuição em metadados, descrições ou textos relacionados.
