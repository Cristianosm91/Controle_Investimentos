import { expect, test } from "./apoio";

test("Alocação continua utilizável quando a API antiga não retorna metodologias", async ({ page }) => {
  await page.route("**/api/alocacao**", (rota) =>
    rota.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        total_atual: 0,
        aporte: 0,
        sobra: 0,
        estrategias: [],
        books: [],
        ativos: [],
        avisos: [],
      }),
    }),
  );

  await page.goto("/alocacao");

  await expect(page.getByRole("heading", { name: "Alocação & Rebalanceamento" })).toBeVisible();
  await expect(page.getByRole("status")).toContainText("Reinicie a aplicação");
});

test("ARCA e KRAKEN ficam abaixo de Por estratégia e se adaptam à largura", async ({ page }) => {
  await page.setViewportSize({ width: 1920, height: 900 });
  const grupo = { nome: "Grupo fictício", estrategia: null, peso_alvo: 1, peso_atual: 1, valor_atual: 100, valor_alvo: 100, ajuste: 0 };
  await page.route("**/api/alocacao**", (rota) =>
    rota.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        total_atual: 100,
        aporte: 0,
        sobra: 0,
        estrategias: [grupo],
        books: Array.from({ length: 10 }, (_, i) => ({ ...grupo, nome: `Book ${i}` })),
        ativos: [],
        avisos: [],
        metodologias: ["ARCA", "KRAKEN"].map((nome) => ({
          nome,
          categorias: ["Ações BR", "FIIs", "Caixa", "Cripto", "Exterior", "Negócios", "Não classificado"].map((categoria) => ({
            nome: categoria, valor_atual: 1234567.89, peso_atual: 0.125,
          })),
          total_atual: 8641975.23,
          peso_total: 1,
        })),
      }),
    }),
  );
  await page.goto("/alocacao");
  const painel = (nome: string) => page.locator(".painel").filter({ has: page.getByRole("heading", { name: nome, exact: true }) });
  const estrategia = await painel("Por estratégia").boundingBox();
  const arca = await painel("ARCA").boundingBox();
  const kraken = await painel("KRAKEN").boundingBox();
  const book = await painel("Por book").boundingBox();
  expect(estrategia).not.toBeNull();
  expect(arca).not.toBeNull();
  expect(kraken).not.toBeNull();
  expect(book).not.toBeNull();
  if (!estrategia || !arca || !kraken || !book) throw new Error("Painéis não encontrados");
  expect(arca.x).toBeCloseTo(estrategia.x, 0);
  expect(kraken.x).toBeGreaterThanOrEqual(arca.x + arca.width);
  expect(arca.y).toBeGreaterThanOrEqual(estrategia.y + estrategia.height);
  expect(kraken.y).toBeCloseTo(arca.y, 0);
  expect(arca.y).toBeLessThan(book.y + book.height);
  for (const nome of ["ARCA", "KRAKEN"]) {
    const medidas = await painel(nome).locator(".tabela-container").evaluate((el) => ({
      largura: el.clientWidth, conteudo: el.scrollWidth,
    }));
    expect(medidas.conteudo).toBeLessThanOrEqual(medidas.largura);
  }

  await page.setViewportSize({ width: 1440, height: 900 });
  const arcaIntermediaria = await painel("ARCA").boundingBox();
  const krakenIntermediaria = await painel("KRAKEN").boundingBox();
  if (!arcaIntermediaria || !krakenIntermediaria) throw new Error("Painéis não encontrados");
  expect(krakenIntermediaria.x).toBeGreaterThanOrEqual(arcaIntermediaria.x + arcaIntermediaria.width);
  for (const nome of ["ARCA", "KRAKEN"]) {
    const medidas = await painel(nome).locator(".tabela-container").evaluate((el) => ({
      largura: el.clientWidth, conteudo: el.scrollWidth,
    }));
    expect(medidas.conteudo).toBeLessThanOrEqual(medidas.largura);
  }

  await page.setViewportSize({ width: 360, height: 900 });
  const arcaMobile = await painel("ARCA").boundingBox();
  const krakenMobile = await painel("KRAKEN").boundingBox();
  expect(arcaMobile).not.toBeNull();
  expect(krakenMobile).not.toBeNull();
  if (!arcaMobile || !krakenMobile) throw new Error("Painéis não encontrados");
  expect(krakenMobile.x).toBeCloseTo(arcaMobile.x, 0);
  expect(krakenMobile.y).toBeGreaterThanOrEqual(arcaMobile.y + arcaMobile.height);
});

test("tabelas de alocação explicam métricas sem cortar as dicas", async ({ page }) => {
  const grupo = { nome: "Estratégia fictícia", estrategia: null, peso_alvo: 0.5, peso_atual: 0.4, valor_atual: 100, valor_alvo: 125, ajuste: 25 };
  await page.route("**/api/alocacao**", (rota) =>
    rota.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        total_atual: 250,
        aporte: 0,
        sobra: 0,
        estrategias: [grupo],
        books: [{ ...grupo, nome: "Book fictício" }],
        ativos: [{
          ativo_id: 999,
          ticker: "TST",
          nome: "Ativo fictício",
          classe: "AÇÃO",
          moeda: "BRL",
          book: "Book fictício",
          carteira: null,
          cotacao: 10,
          preco_teto: 12,
          acima_teto: false,
          peso_alvo: 0.5,
          peso_atual: 0.4,
          valor_atual: 100,
          valor_alvo: 125,
          ajuste: 25,
          quantidade: 2,
        }],
        avisos: [],
        metodologias: [{
          nome: "ARCA",
          categorias: [{ nome: "Ações BR", valor_atual: 100, peso_atual: 0.4, peso_alvo: 0.5 }],
          total_atual: 250,
          peso_total: 1,
        }],
      }),
    }),
  );
  await page.goto("/alocacao");

  const desvio = page.getByRole("button", { name: "Ajuda sobre Desvio" }).first();
  await expect(desvio).toBeVisible();
  await desvio.hover();
  const dica = page.getByRole("tooltip");
  await expect(dica).toContainText("atual menos alvo");
  await expect(dica).toBeVisible();
  expect(await dica.evaluate((elemento) => elemento.parentElement === document.body)).toBe(true);
  await desvio.focus();
  await expect(desvio).toHaveAttribute("aria-describedby", await dica.getAttribute("id") as string);
  await page.keyboard.press("Escape");
  await expect(dica).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Ajuda sobre % atual" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Ajuda sobre Qtd" })).toBeVisible();
});
