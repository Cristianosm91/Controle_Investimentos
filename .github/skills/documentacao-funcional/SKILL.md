---
name: documentacao-funcional
description: 'Use para revisar, validar ou (com confirmação) atualizar a documentação de uma aplicação para que acompanhe as funcionalidades reais — README (instalação, configuração, uso), CHANGELOG no estilo Keep a Changelog, FAQ/solução de problemas, regras de cálculo, documentação de API (OpenAPI com descrições e exemplos), textos de ajuda na interface, ADRs, runbook de operação (iniciar, parar, atualizar, backup, restaurar), limitações e avisos — com verificação de divergência documentação × código, sem inventar comportamento. Modos review (padrão, somente leitura), test e fix. Palavras-gatilho: documentação, README, CHANGELOG, Keep a Changelog, FAQ, troubleshooting, solução de problemas, regras de cálculo, OpenAPI, Swagger, docstring, ajuda in-app, tooltip, ADR, decisão de arquitetura, runbook, operação, limitações, aviso, drift, documentação desatualizada.'
argument-hint: '[modo: review | test | fix] [caminho] [foco opcional]'
---

# Documentação Funcional

Mantém a documentação **fiel ao que o código faz** e **completa para cada funcionalidade
visível ao usuário**. A skill inventaria funcionalidades e documentos, cruza os dois (matriz
funcionalidade × documentação), detecta **drift** — funcionalidade sem documentação e
documentação de comportamento inexistente ou diferente — e propõe atualizações. Documentação
**descreve** o comportamento; nunca o define nem o "corrige" por conta própria.

## Quando usar
- Antes de homologação/release: conferir README, CHANGELOG, FAQ, runbook e ajuda in-app.
- Ao concluir uma funcionalidade: garantir que a documentação entra **no mesmo change**.
- Documentar regras de cálculo, decisões de arquitetura (ADR) ou procedimentos de operação.
- Melhorar descrições/exemplos do OpenAPI sem alterar contratos.

## Quando NÃO usar
- Mensagens de commit, branches e tags → `git-workflow` / `commit-message`.
- Termos legais, licenciamento, contratos ou material comercial (fora do escopo).
- Definir/alterar regra de negócio — aqui só se documenta o que existe.

---

## Princípios obrigatórios (inegociáveis)

1. **Não alterar regras de negócio, funcionalidades, textos de domínio ou comportamento visível**
   sem solicitação explícita do usuário. Textos de ajuda in-app são parte da UI: mudança só com confirmação.
2. **Não inventar comportamento**: cada afirmação documentada tem fonte no código, teste ou
   execução (arquivo:linha). Sem fonte → "a confirmar", nunca suposição.
3. **Divergência vira achado** com evidência (trecho do doc × trecho do código) e proposta —
   nunca correção silenciosa. Se o código parece errado e o doc certo, **não** mude o código:
   reporte a quem decide.
4. **Modo padrão `review` é somente leitura.** `fix` só com pedido explícito e confirmação;
   mudanças mínimas, verificadas antes/depois (links, comandos e exemplos testados).
5. **Diferenciar análise teórica de teste executado**: comando do README executado ≠ lido.
6. **Nunca usar dados reais/pessoais** em exemplos, prints e logs; caminhos com usuário da
   máquina, nomes e valores reais são substituídos por fictícios (`redigir-dados-sensiveis`).
7. **Nunca documentar segredos** (senhas, tokens, chaves) — apenas o nome da variável e onde configurar.
8. **Informar limitações** (comando não executável no ambiente, funcionalidade sem acesso, dados ausentes).

---

## Modos de operação

| Modo | Faz | Não faz |
|---|---|---|
| `review` (padrão) | Inventaria funcionalidades e documentos, monta a matriz, aponta lacunas e drift | Não altera arquivos |
| `test` | Executa comandos do README/runbook em ambiente isolado, valida links, exemplos de API e trechos de código; compara com saídas reais | Não altera código nem documentação |
| `fix` | Atualiza/cria documentos com base em evidência, item a item confirmado | Não altera código, regra de negócio ou texto da UI sem confirmação |

---

## Fluxo de trabalho

1. **Inventário de documentos** — README, CHANGELOG, `docs/`, FAQ, ADRs, runbook, OpenAPI
   (`/openapi.json`, docstrings, `description`/`examples` dos schemas), textos de ajuda na UI
   (tooltips, estados vazios, telas de ajuda), comentários de regra de cálculo.
2. **Inventário funcional** — rotas/páginas/menus, endpoints, comandos/scripts, configurações
   (variáveis, arquivos), jobs, importações/exportações, cálculos. Reutilize o de `testes-e2e`.
3. **Matriz** — [templates/matriz-documentacao.md](templates/matriz-documentacao.md): cada
   funcionalidade × onde está documentada × status (`ok`, `ausente`, `divergente`, `parcial`).
4. **Drift doc × código** — para cada afirmação verificável (comando, porta, variável, caminho,
   fórmula, limite, formato): confirme no código; registre divergências com as duas evidências.
   Técnicas: [references/checklist.md](references/checklist.md#7-detecção-de-drift).
5. **Execução (`test`)** — rode comandos documentados com timeout e dados fictícios; valide links.
6. **Propostas** — texto sugerido, localização, fonte (arquivo:linha) e se exige confirmação.
7. **Relatório** — achados `DOC-XXX` em [templates/relatorio.md](templates/relatorio.md).

Estruturas recomendadas de cada documento: [references/modelos.md](references/modelos.md).

## Documentos avaliados (resumo)

| Documento | Deve conter |
|---|---|
| README | Objetivo, requisitos, instalação, configuração (nomes de variáveis, sem valores sensíveis), uso, testes, estrutura, links |
| CHANGELOG | Keep a Changelog: `Unreleased` + versões com data; Adicionado/Alterado/Corrigido/Removido/Obsoleto/Segurança |
| FAQ / solução de problemas | Sintoma → causa → solução, para erros reais e mensagens exibidas pela app |
| Regras de cálculo | Fórmula, entradas, arredondamento, datas de corte, fontes de dados, exemplos numéricos fictícios, referência ao código e ao teste |
| API (OpenAPI) | `summary`, `description`, exemplos de request/response, códigos de erro — sem mudar contrato |
| Ajuda in-app | Coerente com o comportamento e com a documentação; terminologia única |
| ADR | Contexto, decisão, alternativas, consequências, status, data |
| Runbook | Iniciar, parar, atualizar, migrar, backup, restaurar, verificar saúde, logs, problemas comuns |
| Limitações e avisos | O que a app não faz, dependências externas, precisão dos dados, caráter informativo dos resultados |

## Checklist

Lista completa: [references/checklist.md](references/checklist.md).

## Validação de novas funcionalidades

Toda funcionalidade nova ou alterada deve, **no mesmo change**:
- Ter entrada no CHANGELOG (`Unreleased`) na seção correta.
- Atualizar README/guia de uso se muda instalação, configuração ou uso.
- Documentar regra de cálculo nova/alterada com exemplo e referência ao teste.
- Atualizar OpenAPI (descrição/exemplo) de endpoints novos/alterados.
- Atualizar FAQ/runbook se cria erro novo, configuração ou passo operacional.
- Registrar ADR se envolve decisão arquitetural (nova dependência, armazenamento, integração).
- Ter screenshots (se houver) com dados fictícios.
Ausência → achado (Alta se visível ao usuário ou operacional; Média nos demais).

## Entregáveis

Relatório em `qa-report/documentacao-funcional/` (não comitar sem pedido) com
[templates/relatorio.md](templates/relatorio.md) e
[templates/matriz-documentacao.md](templates/matriz-documentacao.md): achados com **ID**
(`DOC-001`…), **severidade** (Crítica/Alta/Média/Baixa/Informativa), **evidência** (doc × código),
**proposta** e **status**.

| Severidade | Exemplo |
|---|---|
| Crítica | Procedimento documentado causa perda de dados (restauração/atualização errada); segredo ou dado real em documento |
| Alta | Instalação/execução documentada não funciona; regra de cálculo documentada diverge do código; funcionalidade principal sem documentação |
| Média | CHANGELOG sem a versão atual; FAQ desatualizado; OpenAPI sem descrições |
| Baixa | Links quebrados internos, terminologia inconsistente |
| Informativa | Sugestões de organização |

## Integração com outras skills

| Skill | Relação |
|---|---|
| `prontidao-producao` | Orquestrador: usa a matriz de documentação como portão |
| `ci-cd-release` | CHANGELOG e notas de release; versão em fonte única |
| `git-workflow` / `commit-message` | Commits `docs(...)`, branch `docs/...`, tag e changelog |
| `testes-e2e` | Inventário funcional compartilhado; comportamento confirmado por execução |
| `calculos-financeiros-fiscais` | Fonte das regras de cálculo documentadas |
| `backup-recuperacao` / `migracoes-banco` | Procedimentos do runbook |
| `integracoes-externas` | Dependências, limites e indisponibilidade documentados |
| `observabilidade-logs` | Onde estão os logs e como interpretá-los no runbook/FAQ |
| `privacidade-dados` / `redigir-dados-sensiveis` | Exemplos e screenshots com dados fictícios |
| `web-ux-acessibilidade` | Ajuda in-app e microtextos |
| `qa-application-auditor` / `qa-appsec` | Achados que geram limitações/avisos documentados |
| `software-engineering-refactoring` | ADRs de mudanças estruturais |
