import AxeBuilder from "@axe-core/playwright";
import { expect, listarBackups, responderConfirmacao, semear, test, tickerFicticio } from "./apoio";

test("Correção de moeda confirmada relabela lançamentos e gera backup", async ({ page, request }) => {
  const investidor = await semear.investidor(request);
  const ticker = tickerFicticio();
  const criada = await request.post("/api/ativos", {
    data: { ticker, classe: "STOCK", moeda: "USD", mercado: "NASDAQ" },
  });
  expect(criada.ok()).toBe(true);
  const ativo = await criada.json() as { id: number };
  const op = await request.post("/api/operacoes", {
    data: { investidor_id: investidor.id, ativo_id: ativo.id, data: "2025-01-03",
      evento: "C", quantidade: 10, preco: 3, taxas: 0.2, irrf: 0.01, moeda: "USD", cambio: 5 },
  });
  expect(op.ok()).toBe(true);
  const antes = await listarBackups(request);
  await page.goto("/configuracoes?secao=classes-ativos");
  await page.getByRole("combobox", { name: "Exibir", exact: true }).selectOption("todos");
  const campo = page.getByRole("combobox", { name: `Moeda de ${ticker}`, exact: true });
  await expect(campo).toHaveValue("USD");
  const texto = await responderConfirmacao(page, "cancelar", () => campo.selectOption("BRL"));
  expect(texto).toContain("Preços, taxas, IRRF e valores não serão convertidos");
  await expect(campo).toHaveValue("USD");
  await responderConfirmacao(page, "aceitar", () => campo.selectOption("BRL"));
  await expect(campo).toHaveValue("BRL");
  const resposta = await request.get(`/api/operacoes?ticker=${ticker}`);
  const dados = await resposta.json() as { itens: { moeda: string; cambio: number; preco: number; taxas: number; irrf: number }[] };
  expect(dados.itens).toHaveLength(1);
  expect(dados.itens[0]).toMatchObject({ moeda: "BRL", cambio: 1, preco: 3, taxas: 0.2, irrf: 0.01 });
  expect((await listarBackups(request)).length).toBe(antes.length + 1);
});

test("IRRF mostra lucro líquido, crédito e base sem dedução dupla", async ({ page, request }) => {
  const investidor = await semear.investidor(request);
  const ticker = tickerFicticio();
  const criada = await request.post("/api/ativos", { data: { ticker, classe: "ETF" } });
  expect(criada.ok()).toBe(true);
  const ativo = await criada.json() as { id: number };
  for (const [evento, quantidade, preco, taxas, irrf] of [
    ["C", 100, 10, 0, 2], ["V", -100, 12, 1, 3],
  ] as const) {
    const r = await request.post("/api/operacoes", {
      data: { investidor_id: investidor.id, ativo_id: ativo.id, data: "2025-01-03",
        evento, quantidade, preco, taxas, irrf },
    });
    expect(r.ok()).toBe(true);
  }
  await page.goto("/ir");
  await page.getByRole("combobox", { name: "Investidor (CPF)", exact: true }).selectOption(String(investidor.id));
  await page.getByRole("combobox", { name: "Ano", exact: true }).selectOption("2025");
  const linha = page.getByRole("row").filter({ hasText: "199,00" }).first();
  await expect(linha).toContainText("194,00");
  await expect(linha).toContainText("24,85");
  await page.getByRole("button", { name: "Ajuda sobre IRRF retido", exact: true }).focus();
  await expect(page.getByRole("tooltip")).toContainText("dedo-duro");
  expect((await new AxeBuilder({ page }).analyze()).violations.filter(
    (v) => v.impact === "serious" || v.impact === "critical",
  )).toEqual([]);
});

test("CDI mantém correção datada do saldo e continua capitalizando", async ({ page, request }) => {
  const investidor = await semear.investidor(request);
  const ticker = tickerFicticio();
  const criada = await request.post("/api/ativos", {
    data: { ticker, classe: "CDB", cotacao_automatica: false, indexador: "CDI",
      indexador_pct: 1.1, data_base: "2025-01-02" },
  });
  expect(criada.ok()).toBe(true);
  const ativo = await criada.json() as { id: number };
  await semear.operacao(request, { investidor_id: investidor.id, ativo_id: ativo.id,
    data: "2025-01-02", evento: "C", quantidade: 1000, preco: 1 });
  await page.goto("/configuracoes?secao=ativos");
  const linha = page.getByRole("row").filter({ hasText: ticker });
  await linha.getByRole("textbox", { name: `Data do saldo de ${ticker}`, exact: true }).fill("06/01/2025");
  await linha.getByRole("spinbutton", { name: `Saldo bruto total de ${ticker} (BRL)`, exact: true }).fill("1100");
  const resposta = page.waitForResponse((r) => r.url().endsWith(`/api/ativos/${ativo.id}/saldo`) && r.request().method() === "POST");
  await linha.getByRole("button", { name: "Corrigir saldo" }).click();
  expect((await resposta).ok()).toBe(true);
  const cota = await (await request.get(`/api/ativos/${ativo.id}/cota?data=2025-01-07`)).json() as { cota: number };
  expect(cota.cota).toBeCloseTo(1.100121, 8); // 1,1 × (1 + 0,0001 × 110%).
  const anterior = await (await request.get(`/api/ativos/${ativo.id}/cota?data=2025-01-03`)).json() as { cota: number };
  expect(anterior.cota).toBeCloseTo(1.00011, 8);
  await page.reload();
  const persistida = await (await request.get(`/api/ativos/${ativo.id}/cota?data=2025-01-07`)).json() as { cota: number };
  expect(persistida.cota).toBe(cota.cota);
  expect((await new AxeBuilder({ page }).analyze()).violations.filter(
    (v) => v.impact === "serious" || v.impact === "critical",
  )).toEqual([]);
});
