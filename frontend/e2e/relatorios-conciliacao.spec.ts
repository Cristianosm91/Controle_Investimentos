import { expect, selecionarInvestidorNoTopo, semear, test } from "./apoio";

test("conciliação compara posição na data e lista as operações consideradas", async ({ page, request }) => {
  const investidor = await semear.investidor(request);
  const ativo = await semear.ativo(request);
  await semear.operacao(request, {
    investidor_id: investidor.id,
    ativo_id: ativo.id,
    data: "2026-01-12",
    evento: "C",
    quantidade: 10,
    preco: 15,
  });

  await page.goto("/conciliacao");
  const formulario = page.getByRole("main");
  await formulario.getByLabel("Investidor").selectOption(String(investidor.id));
  await formulario.getByLabel("Ativo").selectOption(String(ativo.id));
  await page.getByLabel("Data de referência").fill("31/01/2026");
  await page.getByLabel("Quantidade no extrato").fill("10");
  await page.getByLabel("Custo total no extrato (R$)").fill("150");
  await page.getByRole("button", { name: "Comparar" }).click();

  await expect(page.getByRole("heading", { name: `${ativo.ticker} · posição em 31/01/2026` })).toBeVisible();
  await expect(page.getByRole("row", { name: /Custo total/ })).toContainText("150,00");
  await expect(page.getByText("1 movimentação(ões) até a data de referência.")).toBeVisible();
});

test("montador gera relatório filtrado para Excel e PDF", async ({ page, request }) => {
  const investidor = await semear.investidor(request);
  const ativo = await semear.ativo(request);
  await semear.operacao(request, {
    investidor_id: investidor.id,
    ativo_id: ativo.id,
    data: "2026-01-12",
    evento: "C",
    quantidade: 10,
    preco: 15,
  });

  await page.goto("/relatorios");
  await selecionarInvestidorNoTopo(page, investidor.nome);
  await page.getByRole("button", { name: "Gerar prévia" }).click();
  await expect(page.getByRole("heading", { name: "Operações · 1 registro(s)" })).toBeVisible();

  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "Excel (.xlsx)" }).click();
  expect((await download).suggestedFilename()).toMatch(/\.xlsx$/);

  const popup = page.waitForEvent("popup");
  await page.getByRole("button", { name: "PDF / Imprimir" }).click();
  await expect(await popup).toHaveTitle("Relatório · Operações");
});
