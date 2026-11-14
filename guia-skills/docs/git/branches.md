# Guia de Branches

## Objetivo

Este documento define o fluxo de desenvolvimento, homologação e produção
utilizando três níveis de branches:

```text
feature/ | refactor/ | fix/ | docs/  →  homolog  →  main
             desenvolvimento       homologação   produção
```

Por padrão, as alterações devem ser integradas por Merge Request (MR). Commits são feitos
somente na branch de desenvolvimento; `homolog` e `main` recebem alterações
por MR.

## Branches do fluxo

### Desenvolvimento

Crie uma branch por tarefa, sempre a partir da versão atualizada de `homolog`.
Use somente um destes prefixos:

| Prefixo | Uso | Exemplo |
|---|---|---|
| `feature/` | Nova funcionalidade | `feature/excluir-itens-selecionados` |
| `refactor/` | Reorganização interna sem mudança funcional | `refactor/separar-camada-de-dados` |
| `fix/` | Correção de bug encontrado no desenvolvimento ou na homologação | `fix/corrigir-encerramento-ocorrencias` |
| `docs/` | Somente documentação, como README e guias | `docs/guia-instalacao` |

Não use outros prefixos para branches de desenvolvimento.

### Homologação — `homolog`

Branch compartilhada que recebe MRs das branches de desenvolvimento. É a etapa
de validação por 2 ou 3 pessoas e a origem do pacote piloto.

### Produção — `main`

Branch oficial. Só recebe MR de `homolog`, depois da aprovação do piloto e de
pelo menos 2 aprovações no MR. É a origem do pacote final.

## Fluxo de trabalho

### 1. Atualizar `homolog` e criar a branch da tarefa

```bash
git checkout homolog
git pull origin homolog
git checkout -b feature/exportacao-csv
```

Se `homolog` ainda não existir no GitLab, ela deve ser criada a partir da
`main` atual por um Maintainer/Owner e protegida conforme
[protecao-main.md](protecao-main.md). Não crie uma branch `homolog` baseada em
uma cópia desatualizada do projeto.

### 2. Desenvolver e validar

Faça os commits na branch de desenvolvimento usando o padrão de
[commits.md](commits.md). Quem desenvolveu executa os testes pertinentes; antes
do MR, o agente de IA revisa o código em busca de falhas de segurança, erros e
problemas de qualidade. O resultado da revisão não substitui os testes humanos
nem a aprovação do MR.

### 3. Abrir MR de desenvolvimento para `homolog`

Publique a branch e abra o MR com:

```text
feature/exportacao-csv  →  homolog
```

Revise o destino antes de criar o MR. Não abra diretamente para `main`.

### 4. Homologar e gerar o piloto

Após o merge em `homolog`, 2 ou 3 pessoas testam a aplicação. Registre o
resultado e corrija qualquer falha em uma nova branch de desenvolvimento,
seguindo novamente o fluxo de MR para `homolog`. Quando os testes não
identificarem falhas, gere e valide o pacote piloto a partir de `homolog`.

### 5. Aprovar para produção

Com o piloto aprovado, abra o MR:

```text
homolog  →  main
```

O MR para `main` exige pelo menos 2 aprovações. Após a aprovação e o merge,
gere e valide o pacote final a partir de `main` antes de publicar em produção.

### 6. Limpar a branch de desenvolvimento

Depois que o MR da branch de desenvolvimento for integrado em `homolog`, exclua
a branch de origem, se ela não for mais necessária. Não exclua `homolog` nem
`main`.

## Exceções ao fluxo

O destino padrão não pode ser alterado por conveniência ou inferência. Se o
desenvolvedor pedir explicitamente um fluxo diferente, o agente deve:

1. Informar qual regra será desviada e qual será o destino alternativo.
2. Avisar sobre os riscos de contornar homologação ou produção.
3. Distinguir MR, merge local e push; se o pedido estiver ambíguo, esclarecer.
4. Apresentar repositório, origem, destino, remoto e operações abrangidas e pedir
   confirmação explícita após o aviso, antes de criar/alterar o MR, executar o
   merge local ou fazer push normal.

Sem essa confirmação, mantenha o fluxo padrão. Após confirmação específica,
é permitido MR fora do fluxo, merge local e/ou push normal para `homolog` ou
`main`, somente no escopo apresentado. "Faça merge na main" é o pedido inicial,
não substitui a confirmação após o aviso. Merge e push podem ser confirmados
juntos se ambos forem discriminados. Não repita a pergunta sem mudança de escopo.

Não autoriza commits de desenvolvimento diretamente nessas branches, force-push,
reescrita de histórico, exclusão de branches nem alteração das proteções.
Não persista a exceção. O agente publica somente o push fast-forward para o
remoto/ref/SHAs confirmados; veja [protecao-main.md](protecao-main.md).
Se o servidor rejeitar, pare e informe o bloqueio; ofereça MR ou atuação de
alguém autorizado, sem tentar contorná-lo. Merge local não significa publicação
remota. A exceção não transforma testes ou aprovações pendentes em concluídos.

## O que não fazer

- Não trabalhar nem commitar diretamente em `homolog` ou `main`.
- Não abrir MR de uma branch de desenvolvimento diretamente para `main`, salvo
  exceção solicitada explicitamente e confirmada após o aviso.
- Não abrir MR de `homolog` para outro destino, salvo a mesma exceção.
- Não misturar tarefas independentes na mesma branch.
- Não usar nomes genéricos como `teste`, `alteracoes` ou `nova-versao`.

## Regra de ouro

```text
Atualiza homolog
      ↓
Cria feature/ | refactor/ | fix/ | docs/
      ↓
Desenvolve + commita + testa + revisão do agente
      ↓
MR da branch de desenvolvimento para homolog
      ↓
2 ou 3 pessoas homologam → pacote piloto
      ↓
MR de homolog para main (mínimo de 2 aprovações)
      ↓
Pacote final → produção
```
