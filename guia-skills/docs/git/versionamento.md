# Política de Versionamento

## Objetivo

Estabelecer um padrão simples e fácil de entender para controle de versões da aplicação.

---

# Formato da Versão

Utilizamos o modelo:

```text
MAJOR.MINOR.CORREÇÃO
```

Exemplos:

```text
1.0.0
1.1.0
1.1.1
2.0.0
```

---

# Como Atualizar a Versão

## MAJOR (Primeiro número)

Incrementar quando houver mudanças significativas na aplicação.

Exemplos:

- Reestruturação completa da aplicação.
- Mudanças que exigem nova configuração.
- Alterações incompatíveis com versões anteriores.
- Grandes mudanças arquiteturais.

Exemplo:

```text
1.5.3 → 2.0.0
```

---

## MINOR (Segundo número)

Incrementar quando forem adicionadas novas funcionalidades.

Exemplos:

- Nova tela.
- Novo relatório.
- Novo dashboard.
- Nova integração.
- Nova automação.
- Novo recurso para o usuário.

Exemplo:

```text
1.5.3 → 1.6.0
```

---

## CORREÇÃO (Terceiro número)

Incrementar quando houver ajustes ou correções.

Exemplos:

- Correção de bugs.
- Ajustes visuais.
- Melhorias de desempenho.
- Correções de logs.
- Tratamento de erros.

Exemplo:

```text
1.5.3 → 1.5.4
```

---

# Regra Resumida

```text
Nova funcionalidade = aumenta o segundo número

Correção = aumenta o terceiro número

Mudança grande = aumenta o primeiro número
```

---

# Controle de Versões no Git

Toda versão publicada em produção deve possuir uma tag.

Exemplos:

```text
v1.0.0
v1.1.0
v1.1.1
v1.2.0
```

---

# Registro de Alterações (Changelog)

Toda nova versão deve ser registrada no arquivo:

```text
CHANGELOG.md
```

---

# Identificação automática dos pacotes

Esta é a fonte de verdade para nomes de pacotes, executáveis e revisões de
piloto. A versão continua vindo da fonte única da aplicação (`__version__` ou
equivalente já existente); a branch e a revisão não alteram o versionamento
`MAJOR.MINOR.CORREÇÃO`, o header da aplicação nem a tag de produção `vX.Y.Z`.

## Branch de origem

Antes de cada build, identifique o repositório **da aplicação**, não o da cópia
de `Guia`, e use seu diretório como base dos comandos Git.

- **Build local:** execute `git symbolic-ref --quiet --short HEAD`. Verifique o
  código de saída e use o nome exato retornado, sem inferir pelo nome da pasta.
- **GitLab CI:** use `CI_COMMIT_BRANCH` em pipelines de branch e confirme que
  `git rev-parse HEAD` corresponde a `CI_COMMIT_SHA`. Se o checkout tiver uma
  branch simbólica, ela deve coincidir com `CI_COMMIT_BRANCH`. Um checkout
  detached é permitido somente com esses metadados válidos de pipeline de
  branch.
- **Sem Git, branch vazia/desconhecida, metadados divergentes, pipeline de
  tag/MR ou detached HEAD local:** interrompa a geração do pacote de
  distribuição com erro explícito. Não escolha `main` como fallback e não
  use uma branch que apenas contém o commit como prova da origem.

Não pergunte se o pacote é piloto ou produção e não aceite uma opção manual
que substitua a classificação da branch. Somente `main` pode gerar o pacote
definitivo. Builds de desenvolvimento existentes podem continuar para testes,
mas não podem usar os nomes reservados de distribuição abaixo.

## Nome-base único

| Origem | Nome-base | Exemplo |
|---|---|---|
| `homolog`, primeiro piloto da versão | `<aplicacao>-piloto-v<versao>` | `gwcel-piloto-v1.2.0` |
| `homolog`, novo piloto da mesma versão | `<aplicacao>-piloto-v<versao>-r<N>` | `gwcel-piloto-v1.2.0-r1` |
| `main` | `<aplicacao>-v<versao>` | `gwcel-v1.2.0` |

Preserve o identificador existente da aplicação; não use `gwcel` como nome
fixo para outros apps. A versão deve ser válida no formato `MAJOR.MINOR.CORREÇÃO`,
sem duplicar o prefixo `v`.

Calcule o nome-base uma única vez antes do build e reutilize-o no gerador
(`--name` do PyInstaller ou `name` do `.spec`), no launcher, na pasta/arquivo
de distribuição e nos anexos de publicação, quando existirem. As extensões
não fazem parte do nome-base: por exemplo, `gwcel-piloto-v1.2.0-r1.exe`,
`gwcel-piloto-v1.2.0-r1.bat` e `gwcel-piloto-v1.2.0-r1.zip`.

Um pacote de `homolog` **sempre** contém `-piloto-`. Não o renomeie para
produção: após o merge aprovado, faça um novo build a partir de `main`.
O pacote da `main` não contém `piloto` nem a revisão `-r<N>` do piloto.

## Incremento das revisões

1. Reutilize o histórico persistente de pacotes do projeto (registro de builds
   ou repositório de artefatos). A chave é **aplicação + versão + canal piloto**;
   não use um contador global nem altere `__version__` para subir uma revisão.
2. Sem piloto anterior, reserve o nome sem sufixo (revisão interna `0`).
   Nas próximas gerações, reserve a maior revisão já registrada + 1:
   sem sufixo → `r1` → `r2` → `r3`. Para uma nova versão, comece sem sufixo.
3. A consulta e a reserva devem ser atômicas ou protegidas pelo mecanismo de
   exclusão do projeto, inclusive entre pipelines/máquinas. Registre nome,
   branch, versão, commit e estado do build; ao concluir, associe o artefato.
   Não sobrescreva um piloto anterior.
4. Uma reserva cujo build falhou permanece registrada e não é reutilizada:
   pode haver lacunas na sequência, mas nunca dois builds com a mesma revisão.
5. Limpar `dist`/`build`, apagar um artefato ou trocar de máquina não pode
   reiniciar o contador. Se o projeto ainda não tiver histórico, implemente
   persistência fora dessas pastas e compartilhe-a entre os geradores usados.
   Ao migrar, importe também os pilotos já gerados para a mesma versão.
6. Se não for possível consultar/reservar a revisão com segurança, interrompa
   com erro explícito. Não gere automaticamente um novo primeiro piloto.

A revisão é automática; não peça ao desenvolvedor para informar `r1`/`r2`.
Regerar em `main` mantém o nome de produção e a política existente de
republicação; não consome nem reinicia o histórico de revisões de piloto.

## Validação obrigatória ao aplicar a regra em um app

- `homolog` + `1.2.0`, sem histórico → `gwcel-piloto-v1.2.0`.
- Mais dois builds da mesma versão → `gwcel-piloto-v1.2.0-r1` e `-r2`.
- `homolog` + `1.2.1`, sem histórico → `gwcel-piloto-v1.2.1`.
- `main` + `1.2.0` → `gwcel-v1.2.0`, independentemente dos pilotos anteriores.
- Branch desconhecida, detached sem metadados válidos ou histórico
  indisponível → erro explícito, nunca um pacote definitivo por fallback.
- Builds concorrentes → nomes distintos; falha e limpeza de `dist` não
  permitem reutilização da revisão.
- Confira o nome de todos os artefatos e a correspondência entre o executável
  e seu launcher, preservando os recursos e o comportamento existentes.

---

# Boas Práticas

Antes de publicar uma nova versão:

- Validar o funcionamento da aplicação.
- Atualizar o CHANGELOG.md.
- Criar a tag correspondente no Git.
- Informar a equipe sobre a nova versão.
- Registrar alterações importantes na documentação.

---

# Fluxo Recomendado

```text
Desenvolvimento
      ↓
Testes
      ↓
Homologação
      ↓
Produção
```

---

# Exemplo de Evolução

```text
1.0.0 → Primeira versão
1.1.0 → Nova funcionalidade
1.1.1 → Correção
1.2.0 → Nova funcionalidade
2.0.0 → Grande mudança estrutural
```
