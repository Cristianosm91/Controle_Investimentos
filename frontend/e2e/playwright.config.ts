import { existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium, defineConfig, devices } from "@playwright/test";

const PASTA_E2E = path.dirname(fileURLToPath(import.meta.url));
const FRONTEND = path.resolve(PASTA_E2E, "..");
const RAIZ = path.resolve(FRONTEND, "..");
const PORTA = Number(process.env.E2E_PORTA ?? 8765);
const BASE_URL = `http://127.0.0.1:${PORTA}`;

// O backend serve a interface compilada: sem o build, os testes validariam uma versão antiga ou nada.
if (!existsSync(path.join(FRONTEND, "dist", "index.html"))) {
  throw new Error("E2E: frontend/dist não encontrado. Rode `npm --prefix frontend run build` (ou e2e.bat) antes dos testes.");
}

const python = process.env.E2E_PYTHON ?? path.join(RAIZ, ".venv", "Scripts", "python.exe");

/**
 * E2E_CHANNEL: "chromium" (navegador do Playwright), "msedge" ou "chrome" (instalados na máquina).
 * Padrão: chromium se `npx playwright install chromium` já foi feito; senão, o Microsoft Edge local.
 */
function canalNavegador(): string | undefined {
  const pedido = process.env.E2E_CHANNEL?.trim().toLowerCase();
  if (pedido) return pedido === "chromium" ? undefined : pedido;
  return existsSync(chromium.executablePath()) ? undefined : "msedge";
}

const canal = canalNavegador();
// Nesta rede, o Edge local é bloqueado por política: headless ("Headless mode is disallowed by the system admin")
// e com janela (launch não conclui). Use o chromium do Playwright; E2E_HEADED=1 mostra a janela do navegador.
const comJanela = process.env.E2E_HEADED === "1";

export default defineConfig({
  testDir: PASTA_E2E,
  outputDir: path.join(FRONTEND, "test-results"),
  timeout: 60_000,
  expect: { timeout: 10_000 },
  // Um único banco descartável por execução: os fluxos destrutivos (exclusão, restauração) rodam em série.
  fullyParallel: false,
  workers: 1,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  reporter: [
    ["list"],
    ["html", { open: "never", outputFolder: path.join(FRONTEND, "playwright-report") }],
  ],
  use: {
    baseURL: BASE_URL,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
    locale: "pt-BR",
    timezoneId: "America/Sao_Paulo",
  },
  webServer: {
    command: `"${python}" "${path.join(PASTA_E2E, "servidor_e2e.py")}"`,
    cwd: FRONTEND,
    url: `${BASE_URL}/api/saude`,
    reuseExistingServer: false,
    timeout: 120_000,
    stdout: "pipe",
    stderr: "pipe",
    env: { E2E_PORTA: String(PORTA), PYTHONIOENCODING: "utf-8" },
  },
  projects: [
    {
      name: "desktop",
      use: {
        ...devices["Desktop Chrome"],
        channel: canal,
        headless: !comJanela,
        viewport: { width: 1440, height: 900 },
      },
    },
  ],
});
