import { expect, semear, test } from "./apoio";

test("tabela do portfólio mantém os dados e oferece ações e ajuda acessíveis", async ({ page, request }) => {
  const investidor = await semear.investidor(request);
  const ativo = await semear.ativo(request, undefined, { setor: "Energia", subsetor: "Petróleo" });
  await semear.operacao(request, {
    investidor_id: investidor.id,
    ativo_id: ativo.id,
    data: "2026-03-02",
    evento: "C",
    quantidade: 10,
    preco: 25,
  });

  await page.goto("/portfolio");
  const tabela = page.getByRole("table", { name: "Posições do portfólio" });
  const linha = tabela.getByRole("row", { name: new RegExp(ativo.ticker) });
  await expect(linha).toBeVisible();

  for (const titulo of [
    "Ativo",
    "Classe",
    "Peso",
    "Qtd",
    "PM (R$)",
    "Cotação",
    "Custo ajustado",
    "Mercado",
    "Lucro dia",
    "Lucro aberto",
    "Proventos",
    "Aluguel",
    "YoC 12m",
    "TIR a.a.",
    "Setor",
    "Ações",
  ]) {
    await expect(tabela.getByRole("columnheader", { name: titulo })).toBeVisible();
  }
  await expect(linha.getByText("Energia", { exact: true })).toBeVisible();
  await expect(linha.getByText("Petróleo", { exact: true })).toHaveCount(0);
  await expect(tabela.locator("thead .portfolio-ajuda-gatilho")).toHaveCount(4);
  await expect(linha.getByText(/c\/ renda/)).toBeVisible();

  const ajuda = tabela.getByRole("button", { name: "Ajuda sobre YoC 12m" });
  await ajuda.hover();
  await expect(page.getByRole("tooltip")).toContainText(
    "Proventos líquidos pagos nos últimos 365 dias divididos pelo custo contábil atual da posição.",
  );
  await page.mouse.move(0, 0);
  await expect(page.getByRole("tooltip")).toHaveCount(0);
  await ajuda.focus();
  await expect(page.getByRole("tooltip")).toContainText(
    "Proventos líquidos pagos nos últimos 365 dias divididos pelo custo contábil atual da posição.",
  );
  await page.keyboard.press("Escape");
  await expect(page.getByRole("tooltip")).toHaveCount(0);

  const indisponibilidade = linha.getByRole("button", {
    name: `Motivo da indisponibilidade de Mercado para ${ativo.ticker}`,
  });
  await indisponibilidade.scrollIntoViewIfNeeded();
  await indisponibilidade.focus();
  await expect(page.getByRole("tooltip")).toContainText("A cotação atual do ativo não está disponível.");
  await page.keyboard.press("Escape");

  const acoes = linha.getByRole("button", { name: `Ações de ${ativo.ticker}` });
  await acoes.focus();
  await page.keyboard.press("Enter");
  await expect(linha.getByRole("link", { name: "Abrir valuation" })).toBeVisible();
  await linha.getByRole("button", { name: "Ver modelos" }).click();
  await expect(page.getByText(new RegExp(`Sem valuation salvo para ${ativo.ticker}`))).toBeVisible();
  await expect(linha.locator("details[open]")).toHaveCount(0);

  await page.setViewportSize({ width: 360, height: 640 });
  const dimensoes = await page.locator(".portfolio-tabela-container").evaluate((container) => ({
    largura: container.clientWidth,
    rolagem: container.scrollWidth,
    pagina: document.documentElement.scrollWidth,
  }));
  expect(dimensoes.rolagem).toBeGreaterThan(dimensoes.largura);
  expect(dimensoes.pagina).toBeLessThanOrEqual(360);
});
