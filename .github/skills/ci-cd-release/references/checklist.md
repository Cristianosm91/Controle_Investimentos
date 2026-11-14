# Checklist — CI/CD e Release

Marque cada item como `OK`, `ACHADO (CI-XXX)`, `N/A` ou `NÃO VERIFICADO` (com motivo).

## 1. Versionamento do pipeline
- [ ] Arquivo de pipeline existe (`.github/workflows/*.yml` ou `.gitlab-ci.yml`).
- [ ] Arquivo **não** está ignorado: `git check-ignore -v <arquivo>` sem saída. Se ignorado → achado Crítico, sem alterar `.gitignore`.
- [ ] Arquivo está rastreado: `git ls-files <arquivo>` retorna o caminho.
- [ ] YAML válido (lint da plataforma: `actionlint`, "CI Lint" do GitLab) quando disponível.

## 2. Paridade com o script local
- [ ] Script local de verificação identificado (ex.: `lint.bat`, `Makefile`, `npm run lint`).
- [ ] Cada comando local tem job/step equivalente, com os **mesmos argumentos** e diretório de trabalho.
- [ ] Versões de runtime (Python, Node) iguais às documentadas no README/manifestos.
- [ ] Mesmo arquivo de dependências de desenvolvimento usado localmente (ex.: `requirements-dev.txt`).

## 3. Portões de qualidade
- [ ] Lint backend (ex.: `python -m ruff check .`) — e `ruff format --check` só se já usado localmente.
- [ ] Checagem de tipos frontend (ex.: `tsc -b --noEmit` via script do `package.json`).
- [ ] Testes unitários/integração (ex.: `python -m pytest -q`) com relatório JUnit como artefato.
- [ ] Migrações: `upgrade head` em banco limpo e descartável; detecção de divergência modelo × migração (ex.: `alembic check`) quando suportado.
- [ ] Build do frontend (ex.: `npm ci` + `npm run build`).
- [ ] Smoke E2E headless (ver `testes-e2e`) com trace/screenshot em falha.
- [ ] Nenhum portão obrigatório com `continue-on-error: true` / `allow_failure: true`.
- [ ] Nenhum teste desabilitado/`skip` adicionado só para o pipeline passar.

## 4. Cadeia de suprimentos
- [ ] Lockfile versionado (`package-lock.json`, `poetry.lock`, `uv.lock`) ou versões fixadas (`==`) no `requirements*.txt`.
- [ ] Hashes quando aplicável (`pip install --require-hashes`, `pip-compile --generate-hashes`).
- [ ] Instalação determinística no CI (`npm ci`, nunca `npm install`).
- [ ] Auditoria: `pip-audit -r requirements.txt` e `npm audit --audit-level=high` (política de severidade definida).
- [ ] Varredura de segredos: `gitleaks detect --redact` (histórico) e/ou `gitleaks protect` no diff.
- [ ] SBOM opcional (`cyclonedx-py`, `@cyclonedx/cyclonedx-npm`) como artefato da release.
- [ ] Dependabot (`.github/dependabot.yml`) ou Renovate configurado para pip, npm e actions.
- [ ] Ações de terceiros fixadas por versão maior ou SHA; imagens Docker com tag explícita (nunca `latest`).

## 5. Segredos e permissões
- [ ] Nenhum segredo, token, senha ou URL com credencial em YAML, scripts ou artefatos.
- [ ] Segredos via `secrets.*` / variáveis CI mascaradas e protegidas.
- [ ] `permissions:` mínimas no GitHub Actions (padrão `contents: read`).
- [ ] Workflows de PR de fork não recebem segredos (`pull_request`, não `pull_request_target` com checkout do PR).
- [ ] Logs não imprimem variáveis de ambiente completas (`env`, `printenv`, `set -x` com segredos).

## 6. Eficiência e robustez
- [ ] Cache de pip/npm por hash do lockfile.
- [ ] `timeout-minutes` (GitHub) / `timeout` (GitLab) por job.
- [ ] `concurrency` com `cancel-in-progress` (GitHub) / `interruptible: true` (GitLab).
- [ ] Artefatos com `retention-days`/`expire_in` curtos; sem dados reais ou banco local nos artefatos.
- [ ] Jobs independentes em paralelo; dependências explícitas (`needs`).

## 7. Proteção do merge
- [ ] Checks obrigatórios definidos para as branches do fluxo (ex.: `homolog`, `main`).
- [ ] "Pipelines must succeed" (GitLab) / "Require status checks" (GitHub) recomendado.
- [ ] Recomendação registrada sem alterar configuração da plataforma (papel do Maintainer).

## 8. Release
- [ ] Versão em **fonte única** (ex.: `__version__`, `package.json`) e demais pontos derivados dela.
- [ ] Divergência de versão entre manifestos (backend × frontend × CHANGELOG) registrada como achado.
- [ ] CHANGELOG com seção da versão e data; `Unreleased` esvaziado na release.
- [ ] Tag `vX.Y.Z` anotada criada **depois** da integração na branch de produção (ver `git-workflow`).
- [ ] Artefatos gerados a partir da tag, com checksum (SHA-256) e, se houver, SBOM.
- [ ] Notas de release derivadas do CHANGELOG (sem dados internos, caminhos ou nomes pessoais).
- [ ] Release reproduzível: mesmo commit + lockfile → mesmo artefato.
