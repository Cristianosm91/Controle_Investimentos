import { esperarPaginaSemErro, expect, selecionarInvestidorNoTopo, semear, test } from "./apoio";

/** Rotas do menu (frontend/src/components/Layout.tsx → PAGINAS) + Configurações. */
const ROTAS = [
  { caminho: "/", rotulo: "Resumo" },
  { caminho: "/portfolio", rotulo: "Portfólio" },
  { caminho: "/dashboard", rotulo: "Rentabilidade" },
  { caminho: "/proventos", rotulo: "Proventos" },
  { caminho: "/aluguel", rotulo: "Aluguel (BTC)" },
  { caminho: "/renda-fixa", rotulo: "Renda fixa" },
  { caminho: "/operacoes", rotulo: "Operações" },
  { caminho: "/caixa", rotulo: "Caixa" },
  { caminho: "/alocacao", rotulo: "Alocação" },
  { caminho: "/metas", rotulo: "Metas" },
  { caminho: "/radar", rotulo: "Radar" },
  { caminho: "/cripto", rotulo: "Cripto" },
  { caminho: "/status", rotulo: "Status do ativo" },
  { caminho: "/ir", rotulo: "Imposto de Renda" },
  { caminho: "/valuation", rotulo: "Valuation" },
  { caminho: "/valuations-salvos", rotulo: "Valuations salvos" },
  { caminho: "/configuracoes", rotulo: "Configurações" },
] as const;

test.describe("Smoke: navegação", { tag: "@smoke" }, () => {
  test("E2E-T-001 menu lista as páginas e a versão do app", async ({ page }) => {
    await page.goto("/");
    const menu = page.getByRole("complementary");
    for (const { rotulo } of ROTAS) {
      await expect(menu.getByRole("link", { name: rotulo, exact: true })).toBeVisible();
    }
    await expect(menu.getByText(/^v\d+\.\d+\.\d+/)).toBeVisible();
  });

  for (const { caminho, rotulo } of ROTAS) {
    test(`E2E-T-040 ${rotulo} (${caminho}) abre sem erro`, async ({ page }) => {
      await page.goto(caminho);
      await esperarPaginaSemErro(page, /.+/);
      await expect(page).toHaveTitle(`${rotulo} · InvestHub+`);
      await expect(page.getByRole("link", { name: rotulo, exact: true })).toHaveAttribute("aria-current", "page");
    });
  }

  test("E2E-T-041 todas as páginas abrem sem erro com dados fictícios semeados", async ({ page, request }) => {
    const investidor = await semear.investidor(request);
    const ativo = await semear.ativo(request);
    await semear.operacao(request, { investidor_id: investidor.id, ativo_id: ativo.id, data: "2026-01-12", evento: "C", quantidade: 30, preco: 15 });
    await semear.operacao(request, { investidor_id: investidor.id, ativo_id: ativo.id, data: "2026-02-12", evento: "V", quantidade: 10, preco: 18 });
    await semear.provento(request, { investidor_id: investidor.id, ativo_id: ativo.id, data_pagamento: "2026-03-12", valor: 4.5 });
    await semear.noRadar(request, ativo.id);

    for (const { caminho, rotulo } of ROTAS) {
      await page.goto(caminho);
      await esperarPaginaSemErro(page, /.+/);
      await expect(page).toHaveTitle(`${rotulo} · InvestHub+`);
    }
    await selecionarInvestidorNoTopo(page, investidor.nome);
    for (const { caminho, rotulo } of ROTAS) {
      await page.goto(caminho);
      await esperarPaginaSemErro(page, /.+/);
      await expect(page).toHaveTitle(`${rotulo} · InvestHub+`);
    }
  });

  test("E2E-T-002 navegação pelo menu e deep link em rota inexistente", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("link", { name: "Operações", exact: true }).click();
    await expect(page).toHaveURL(/\/operacoes$/);
    await esperarPaginaSemErro(page, "Operações");
    await page.reload();
    await esperarPaginaSemErro(page, "Operações");

    await page.goto("/rota-que-nao-existe");
    await expect(page.getByRole("heading", { level: 1, name: "Página não encontrada" })).toBeVisible();
    await expect(page).toHaveTitle("Página não encontrada · InvestHub+");
  });
});
