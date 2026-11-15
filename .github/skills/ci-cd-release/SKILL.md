---
name: ci-cd-release
description: 'Use ao criar, revisar ou validar pipeline de CI/CD como código (GitHub Actions ou GitLab CI) e o processo de release de uma aplicação — lint, checagem de tipos, testes unitários/integração, verificação de migrações, build do frontend, smoke E2E, auditoria de dependências, varredura de segredos, SBOM, dependências fixadas, checks obrigatórios antes do merge, versão em fonte única, CHANGELOG, tag vX.Y.Z, artefatos e notas de release — sem alterar regras de negócio. Modos review (padrão, somente leitura), test e fix. Palavras-gatilho: CI, CD, pipeline, GitHub Actions, GitLab CI, workflow, .gitlab-ci.yml, required checks, pip-audit, npm audit, gitleaks, SBOM, cyclonedx, Dependabot, Renovate, lockfile, hashes, cache, release, tag, changelog, notas de release, artefato.'
argument-hint: '[modo: review | test | fix] [caminho] [foco opcional]'
---

# CI/CD e Release

Garante que **toda mudança passe pelos mesmos portões automáticos** antes do merge e que cada
versão seja **reprodutível, rastreável e documentada**. A skill valida (e, só quando pedido,
cria) o pipeline como código executando **exatamente os mesmos comandos** do script local de
verificação do projeto — nunca comandos inventados — e audita o processo de release. Não altera
funcionalidades nem regras de negócio: o pipeline apenas **verifica** o que já existe.

## Quando usar
- Criar ou revisar workflows de CI (GitHub Actions) ou `.gitlab-ci.yml` (GitLab CI).
- Garantir paridade entre o script local de verificação (lint/testes/tipos) e o pipeline.
- Incluir auditoria de dependências, varredura de segredos, SBOM e verificação de migrações.
- Definir checks obrigatórios antes do merge e o roteiro de release (versão, CHANGELOG, tag, artefatos).
- Validar se uma nova funcionalidade está coberta pelos portões do pipeline.

## Quando NÃO usar
- Escrever mensagens de commit, nomear branches ou executar merge/push → `git-workflow` / `commit-message`.
- Deploy em infraestrutura de terceiros, publicação em lojas, licenciamento ou distribuição comercial.
- Corrigir falhas funcionais apontadas pelo pipeline → `qa-application-auditor` (modo `fix`).

---

## Princípios obrigatórios (inegociáveis)

1. **Não alterar regras de negócio, funcionalidades, textos de domínio ou comportamento visível**
   sem solicitação explícita do usuário. O pipeline verifica; não "conserta" o produto.
2. **Divergência vira achado** com evidência e proposta — nunca correção silenciosa (teste que
   falha não é desabilitado; `continue-on-error`/`allow_failure` não esconde portão obrigatório).
3. **Modo padrão `review` é somente leitura.** `fix` só com pedido explícito e confirmação;
   mudanças mínimas, verificadas antes/depois.
4. **Nunca inventar comandos**: confirme-os no script local (`lint.*`, `Makefile`, `package.json`,
   `pyproject.toml`, `pytest.ini`, README). O CI roda os **mesmos** comandos, na mesma ordem.
5. **Nunca colocar segredos em arquivos de workflow** (nem em `env:` literais, logs ou artefatos).
   Use o cofre da plataforma (`secrets.*`, variáveis protegidas/mascaradas).
6. **Pasta de CI ignorada pelo Git**: se `.github/` (ou o arquivo de pipeline) estiver no
   `.gitignore`, os workflows **não serão versionados nem executados**. Detecte e **reporte**;
   nunca altere o `.gitignore` sem confirmação explícita.
7. **Não atualizar dependências indiscriminadamente**: auditoria gera achados; atualização é
   proposta individual, com teste.
8. **Diferenciar análise teórica de execução**: YAML revisado ≠ pipeline executado. Registre
   `NÃO EXECUTADO` com motivo quando não houver runner disponível.
9. **Nunca usar dados reais/pessoais** em fixtures, seeds ou artefatos do CI — apenas fictícios.
10. **Informar limitações** (sem acesso à plataforma, sem permissão para proteção de branch,
    runner indisponível, rede corporativa bloqueando registries).
11. **Respeitar o fluxo de branches de `git-workflow`** — o pipeline se adapta ao fluxo, nunca o contrário.

---

## Modos de operação

Se nenhum modo for informado, use **`review`**. Pedido de "crie/corrija o pipeline" sem modo →
confirme antes de usar `fix`.

| Modo | Faz | Não faz |
|---|---|---|
| `review` (padrão) | Inventaria comandos locais, workflows, lockfiles, proteção de branch e release; aponta lacunas | Não cria nem altera arquivos |
| `test` | Executa localmente os comandos do pipeline (lint, tipos, testes, build, auditorias) e registra evidências; valida sintaxe do YAML | Não altera código produtivo nem workflows |
| `fix` | Cria/ajusta workflows, Dependabot/Renovate e roteiro de release, com diff e justificativa | Não altera regra de negócio, `.gitignore` ou proteção de branch sem confirmação |

---

## Fluxo de trabalho

1. **Descoberta** — stack, gerenciadores (pip/uv/poetry, npm/pnpm), script local de verificação,
   testes, migrações, build, plataforma Git (GitHub/GitLab), fluxo de branches (`git-workflow`).
   Verifique se a pasta/arquivo de CI está ignorado: `git check-ignore -v .github/workflows/ci.yml`.
2. **Paridade local × CI** — tabela "comando local → job do pipeline". Todo comando local deve
   existir no CI; jobs extras (auditoria, segredos) são acréscimos, não substituições.
3. **Portões de qualidade** — lint, tipos, testes, migrações, build, smoke E2E (`testes-e2e`).
4. **Cadeia de suprimentos** — lockfiles/hashes, auditoria de dependências, varredura de
   segredos, SBOM opcional, Dependabot/Renovate, ações/imagens fixadas por versão ou SHA.
5. **Eficiência** — cache por hash do lockfile, `concurrency`/`interruptible`, timeout por job,
   artefatos com retenção curta.
6. **Proteção do merge** — checks obrigatórios nas branches do fluxo (ex.: `homolog`/`main`),
   pipeline obrigatório para MR/PR. Só recomende; configuração na plataforma é do Maintainer.
7. **Release** — versão em fonte única, CHANGELOG, tag `vX.Y.Z`, artefatos e notas.
   Detalhes: [references/release.md](references/release.md).
8. **Execução (`test`)** — rode cada comando com timeout; registre saída, código de retorno e duração.
9. **Relatório** — achados `CI-XXX` em [templates/relatorio.md](templates/relatorio.md).

Exemplos: [references/github-actions.md](references/github-actions.md) e
[references/gitlab-ci.md](references/gitlab-ci.md) — adapte **somente** com comandos confirmados.

## Checklist

Lista completa e verificável: [references/checklist.md](references/checklist.md).

## Validação de novas funcionalidades

Para cada funcionalidade nova ou alterada, confirme antes do merge:
- Testes novos rodam no job de testes (sem `skip` injustificado).
- Mudança de esquema tem migração e o job de migrações passa em banco limpo.
- Fluxo principal tem cenário no smoke E2E (`testes-e2e`) quando houver UI.
- Dependência nova está no manifesto **e** no lockfile, sem vulnerabilidade conhecida aberta.
- CHANGELOG tem entrada em `Unreleased` (`documentacao-funcional`).
- Nenhum segredo, dado real ou caminho pessoal introduzido (gitleaks + revisão).

## Entregáveis

Relatório em `qa-report/ci-cd-release/` (não comitar sem o usuário pedir), usando
[templates/relatorio.md](templates/relatorio.md): achados com **ID** (`CI-001`…), **severidade**
(Crítica/Alta/Média/Baixa/Informativa), **evidência**, **proposta** e **status**; tabela de
paridade local × CI; evidências em `qa-report/ci-cd-release/evidencias/`.

| Severidade | Exemplo |
|---|---|
| Crítica | Segredo em workflow/histórico; pipeline não versionado por `.gitignore`; merge sem nenhum check |
| Alta | Testes ou lint ausentes no CI; vulnerabilidade alta em dependência; migração não verificada |
| Média | Sem lockfile/hashes; ações sem versão fixada; sem cache/timeout; CHANGELOG desatualizado |
| Baixa | SBOM ausente; nomes de jobs inconsistentes; retenção de artefatos longa |
| Informativa | Otimizações sem risco |

## Integração com outras skills

| Skill | Relação |
|---|---|
| `prontidao-producao` | Orquestrador: consome o parecer desta skill como portão de CI/release |
| `git-workflow` / `commit-message` | Fluxo de branches, tags e commits — esta skill **não altera** essas regras |
| `qa-application-auditor` | Corrige falhas funcionais/estabilidade reveladas pelo pipeline |
| `qa-appsec` | Aprofunda achados de dependências, segredos e cadeia de suprimentos |
| `testes-e2e` | Fornece a suíte smoke executada no pipeline |
| `migracoes-banco` | Define a verificação de migrações usada no job |
| `documentacao-funcional` | CHANGELOG e notas de release |
| `software-engineering-refactoring` | Ajustes estruturais para tornar o build reprodutível |
| `web-ux-acessibilidade` | Checagens de a11y automatizadas que podem virar job |
| `observabilidade-logs`, `backup-recuperacao`, `privacidade-dados` | Checks adicionais quando aplicáveis |
