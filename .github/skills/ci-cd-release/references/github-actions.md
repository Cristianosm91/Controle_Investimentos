# Exemplo — GitHub Actions

> **Modelo, não verdade.** Substitua cada comando pelo equivalente **confirmado** no script local
> do projeto (ex.: `lint.bat`, `Makefile`, `package.json`). Remova jobs que não se aplicam.
> Antes de criar o arquivo, confirme que `.github/` **não** está no `.gitignore`.

Estrutura assumida no exemplo: `backend/` (Python, ruff, pytest, Alembic) e `frontend/`
(Node, TypeScript, Vite, Playwright).

## `.github/workflows/ci.yml`

```yaml
name: ci

on:
  pull_request:
  push:
    branches: [homolog, main]   # ajuste ao fluxo definido em git-workflow

permissions:
  contents: read

concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true

jobs:
  backend:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    defaults:
      run:
        working-directory: backend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"            # mesma versão do README/manifestos
          cache: pip
          cache-dependency-path: backend/requirements*.txt
      - run: python -m pip install -r requirements-dev.txt
      - name: Lint
        run: python -m ruff check .
      - name: Migrações (banco limpo e descartável)
        run: |
          python -m alembic upgrade head
          python -m alembic check          # só se a versão do Alembic suportar
        env:
          DATABASE_URL: sqlite:///./ci.db  # banco temporário; nunca dados reais
      - name: Testes
        run: python -m pytest -q --junitxml=../reports/pytest.xml
      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: pytest-report
          path: reports/
          retention-days: 7

  frontend:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    defaults:
      run:
        working-directory: frontend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "22"
          cache: npm
          cache-dependency-path: frontend/package-lock.json
      - run: npm ci
      - name: Tipos
        run: npm run lint                  # ex.: tsc -b --noEmit
      - name: Build
        run: npm run build

  e2e-smoke:
    needs: [backend, frontend]
    runs-on: ubuntu-latest
    timeout-minutes: 20
    steps:
      - uses: actions/checkout@v4
      # instalar backend/frontend como nos jobs acima, subir a app com banco de teste
      - run: npx playwright install --with-deps chromium
        working-directory: frontend
      - run: npx playwright test --grep @smoke
        working-directory: frontend
      - uses: actions/upload-artifact@v4
        if: failure()
        with:
          name: playwright-report
          path: frontend/playwright-report/
          retention-days: 7

  supply-chain:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0                   # histórico completo para o gitleaks
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: python -m pip install pip-audit
      - run: pip-audit -r backend/requirements.txt
      - run: npm audit --audit-level=high
        working-directory: frontend
      - uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

## `.github/dependabot.yml`

```yaml
version: 2
updates:
  - package-ecosystem: pip
    directory: /backend
    schedule: { interval: weekly }
    open-pull-requests-limit: 5
  - package-ecosystem: npm
    directory: /frontend
    schedule: { interval: weekly }
    open-pull-requests-limit: 5
  - package-ecosystem: github-actions
    directory: /
    schedule: { interval: monthly }
```

> Defina `target-branch` conforme o fluxo de `git-workflow` (ex.: `homolog`), para que as
> atualizações sigam o mesmo caminho de homologação.

## Release (tag) — `.github/workflows/release.yml`

```yaml
name: release
on:
  push:
    tags: ["v*.*.*"]
permissions:
  contents: write
jobs:
  release:
    runs-on: ubuntu-latest
    timeout-minutes: 20
    steps:
      - uses: actions/checkout@v4
      # repetir os portões do ci.yml (ou reutilizar com workflow_call)
      - name: Conferir versão da tag × fonte única
        run: |
          TAG="${GITHUB_REF_NAME#v}"
          grep -q "\"version\": \"$TAG\"" frontend/package.json   # adapte à fonte única real
      - name: Gerar artefato e checksum
        run: |
          # comando de build/empacotamento confirmado no projeto
          sha256sum dist/* > dist/SHA256SUMS
      - name: Notas a partir do CHANGELOG
        run: awk "/^## \\[${GITHUB_REF_NAME#v}\\]/{f=1;next}/^## \\[/{f=0}f" CHANGELOG.md > notas.md
      - uses: softprops/action-gh-release@v2
        with:
          body_path: notas.md
          files: dist/*
```

## Checks obrigatórios (recomendação — configuração é do Maintainer)
Settings → Branches → regra para `homolog`/`main`: *Require status checks* com `backend`,
`frontend`, `e2e-smoke`, `supply-chain`; *Require branches to be up to date*.
