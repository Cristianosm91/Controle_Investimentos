# Exemplo — GitLab CI

> **Modelo, não verdade.** Substitua cada comando pelo equivalente **confirmado** no script local
> do projeto. Confirme que `.gitlab-ci.yml` não está ignorado (`git check-ignore -v .gitlab-ci.yml`).
> Em runners corporativos, use as imagens e registries internos já configurados — nunca
> credenciais no arquivo.

## `.gitlab-ci.yml`

```yaml
stages: [lint, test, build, e2e, audit, release]

default:
  interruptible: true
  timeout: 15m

workflow:
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
    - if: $CI_COMMIT_BRANCH == "homolog" || $CI_COMMIT_BRANCH == "main"
    - if: $CI_COMMIT_TAG =~ /^v\d+\.\d+\.\d+$/

.python:
  image: python:3.12-slim              # mesma versão documentada no projeto
  before_script:
    - cd backend
    - python -m pip install -r requirements-dev.txt
  cache:
    key:
      files: [backend/requirements.txt, backend/requirements-dev.txt]
    paths: [.cache/pip]
  variables:
    PIP_CACHE_DIR: $CI_PROJECT_DIR/.cache/pip

.node:
  image: node:22-slim
  before_script:
    - cd frontend
    - npm ci --cache ../.npm --prefer-offline
  cache:
    key:
      files: [frontend/package-lock.json]
    paths: [.npm]

lint-backend:
  extends: .python
  stage: lint
  script:
    - python -m ruff check .

tipos-frontend:
  extends: .node
  stage: lint
  script:
    - npm run lint                     # ex.: tsc -b --noEmit

migracoes:
  extends: .python
  stage: test
  variables:
    DATABASE_URL: sqlite:///./ci.db    # banco descartável, dados fictícios
  script:
    - python -m alembic upgrade head
    - python -m alembic check          # só se suportado pela versão instalada

testes-backend:
  extends: .python
  stage: test
  script:
    - python -m pytest -q --junitxml=../reports/pytest.xml
  artifacts:
    when: always
    reports:
      junit: reports/pytest.xml
    expire_in: 7 days

build-frontend:
  extends: .node
  stage: build
  script:
    - npm run build
  artifacts:
    paths: [frontend/dist/]
    expire_in: 3 days

e2e-smoke:
  stage: e2e
  image: mcr.microsoft.com/playwright:v1.48.0-jammy   # tag explícita, nunca latest
  needs: [build-frontend, testes-backend]
  script:
    # subir backend com banco de teste e servir o build, conforme o projeto
    - cd frontend && npm ci && npx playwright test --grep @smoke
  artifacts:
    when: on_failure
    paths: [frontend/playwright-report/, frontend/test-results/]
    expire_in: 7 days

auditoria-dependencias:
  stage: audit
  image: python:3.12-slim
  script:
    - python -m pip install pip-audit
    - pip-audit -r backend/requirements.txt
  # npm audit em job .node separado: npm audit --audit-level=high

segredos:
  stage: audit
  image:
    name: zricethezav/gitleaks:v8.21.2
    entrypoint: [""]
  variables:
    GIT_DEPTH: 0
  script:
    - gitleaks detect --source . --redact --verbose

release:
  stage: release
  image: registry.gitlab.com/gitlab-org/release-cli:latest-stable  # prefira tag fixa
  rules:
    - if: $CI_COMMIT_TAG =~ /^v\d+\.\d+\.\d+$/
  script:
    - echo "Release $CI_COMMIT_TAG"
  release:
    tag_name: $CI_COMMIT_TAG
    description: ./notas.md            # gerado do CHANGELOG em job anterior
```

## Alternativa: templates oficiais
`include: - template: Jobs/Secret-Detection.gitlab-ci.yml` e
`- template: Jobs/Dependency-Scanning.gitlab-ci.yml` — verifique disponibilidade na instância/plano.

## Proteção (recomendação — configuração é do Maintainer)
Settings → Merge requests → *Pipelines must succeed*; Settings → Repository → *Protected
branches* para `homolog`/`main` conforme `git-workflow`. Não altere essas configurações.
