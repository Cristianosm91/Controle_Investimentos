# Padrões Playwright

Exemplos genéricos. Adapte portas, comandos e rotas ao que for **confirmado** no projeto.

## 1. Inventário a partir do código (React Router como exemplo)

```powershell
# rotas declaradas
rg -n "path=|path:" frontend/src --glob "*.tsx"
# itens de navegação
rg -n "NavLink|<Link |to=\"" frontend/src --glob "*.tsx"
# ações destrutivas e confirmações
rg -n -i "excluir|remover|apagar|confirm" frontend/src --glob "*.tsx"
# chamadas HTTP (para mapear mocks)
rg -n "fetch\(|axios|/api/" frontend/src
```

Backend (FastAPI como exemplo): `rg -n "@router\.(get|post|put|patch|delete)" backend/`.
O OpenAPI da app (`/openapi.json`) também lista endpoints.

## 2. Configuração (Node/TypeScript)

```ts
// e2e/playwright.config.ts
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: '.',
  timeout: 30_000,
  expect: { timeout: 5_000 },
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  reporter: [['html', { open: 'never' }], ['junit', { outputFile: 'results/junit.xml' }]],
  use: {
    baseURL: 'http://127.0.0.1:8765',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    locale: 'pt-BR',
    timezoneId: 'America/Sao_Paulo',
  },
  webServer: {
    // comando confirmado no projeto, apontando para banco de TESTE
    command: 'python -m uvicorn app.main:app --port 8765',
    cwd: '../backend',
    url: 'http://127.0.0.1:8765/api/status',   // healthcheck real do projeto
    reuseExistingServer: !process.env.CI,
    env: { DATABASE_URL: 'sqlite:///./e2e.db', APP_MODO_TESTE: '1' }, // nomes ilustrativos
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    // { name: 'firefox', use: { ...devices['Desktop Firefox'] } },  // matriz opcional
  ],
});
```

## 3. Bloqueio de rede externa e mocks

```ts
// e2e/fixtures.ts
import { test as base, expect } from '@playwright/test';

export const test = base.extend({
  page: async ({ page }, use) => {
    await page.route('**/*', (route) => {
      const url = new URL(route.request().url());
      if (['127.0.0.1', 'localhost'].includes(url.hostname)) return route.continue();
      return route.abort('blockedbyclient');            // nunca tocar terceiros
    });
    await use(page);
  },
});
export { expect };
```

```ts
// mock de uma API consumida pelo frontend
await page.route('**/api/cotacoes**', (route) =>
  route.fulfill({ json: [{ codigo: 'TEST3', preco: 10.5 }] }));
```

> Chamadas feitas **pelo backend** não passam pelo browser: use modo de teste/injeção de
> dependência do backend ou servidor fake local. Se não existir, registre achado e proponha.

## 4. Seed via API e teste

```ts
import { test, expect } from './fixtures';

test.beforeEach(async ({ request }) => {
  await request.post('/api/registros', { data: { nome: 'Registro Fictício A', valor: 1234.56 } });
});

test('lista exibe registro cadastrado @smoke', async ({ page }) => {
  await page.goto('/registros');
  const linha = page.getByRole('row', { name: /Registro Fictício A/ });
  await expect(linha).toBeVisible();
  await expect(linha).toContainText('1.234,56');   // formato pt-BR
});

test('excluir pede confirmação e pode ser cancelado', async ({ page }) => {
  await page.goto('/registros');
  await page.getByRole('row', { name: /Registro Fictício A/ })
    .getByRole('button', { name: 'Excluir' }).click();
  const dialogo = page.getByRole('dialog');
  await expect(dialogo).toBeVisible();
  await dialogo.getByRole('button', { name: 'Cancelar' }).click();
  await expect(page.getByRole('row', { name: /Registro Fictício A/ })).toBeVisible();
});

test('erro da API exibe mensagem acionável', async ({ page }) => {
  await page.route('**/api/registros', (r) => r.fulfill({ status: 500, json: { detail: 'falha' } }));
  await page.goto('/registros');
  await expect(page.getByRole('alert')).toBeVisible();
});
```

## 5. Acessibilidade dentro do E2E

```ts
import AxeBuilder from '@axe-core/playwright';

test('página principal sem violações graves de a11y', async ({ page }) => {
  await page.goto('/');
  const r = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa']).analyze();
  const graves = r.violations.filter((v) => ['serious', 'critical'].includes(v.impact ?? ''));
  expect(graves, JSON.stringify(graves.map((v) => v.id))).toEqual([]);
});
```

## 6. Variante Python (pytest-playwright)

```python
# e2e/test_registros.py
import re
from playwright.sync_api import Page, expect

def test_lista_exibe_registro(page: Page, base_url: str, seed_registro) -> None:
    page.goto(f"{base_url}/registros")
    expect(page.get_by_role("row", name=re.compile("Registro Fictício A"))).to_be_visible()
```

Execução: `python -m pytest e2e --browser chromium --tracing retain-on-failure
--screenshot only-on-failure`. Marcação smoke: `@pytest.mark.smoke` + `-m smoke`.
Acessibilidade: pacote `axe-playwright-python`.

## 7. Comandos

| Objetivo | Node | Python |
|---|---|---|
| Instalar browser | `npx playwright install chromium` | `python -m playwright install chromium` |
| Smoke | `npx playwright test --grep @smoke` | `pytest e2e -m smoke` |
| Completa | `npx playwright test` | `pytest e2e` |
| Ver trace | `npx playwright show-trace <trace.zip>` | `playwright show-trace <trace.zip>` |
| Detectar instáveis | `npx playwright test --repeat-each=5` | `pytest e2e --count=5` (pytest-repeat) |

## 8. Regressão visual (opcional)
`await expect(page).toHaveScreenshot('painel.png', { mask: [page.locator('[data-dinamico]')] })`
— dados fixos, fontes e viewport definidos, baseline versionada e revisada em PR.
