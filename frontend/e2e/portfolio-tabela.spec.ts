import AxeBuilder from "@axe-core/playwright";
import { expect, selecionarInvestidorNoTopo, semear, test } from "./apoio";

test("metas individuais são configuradas e comparadas com a posição em Portfólio e Alocação", async ({ page, request }) => {
  const investidor = await semear.investidor(request);
  const outro = await semear.investidor(request);
  const acao = await semear.ativo(request);
  const fii = await semear.ativo(request, undefined, { classe: "FII" });
  for (const [ativo, preco] of [[acao, 10], [fii, 30]] as const) {
    await semear.operacao(request, {
      investidor_id: investidor.id, ativo_id: ativo.id, data: "2026-03-02", evento: "C", quantidade: 10, preco,
    });
  }
  await page.goto("/portfolio");
  await selecionarInvestidorNoTopo(page, investidor.nome);
  await page.goto("/configuracoes?secao=metas-metodologias");
  const formulario = (nome: string) => page.locator("form").filter({ has: page.getByRole("heading", { name: nome, exact: true }) });
  const arca = formulario("ARCA");
  const kraken = formulario("KRAKEN");
  await expect(arca.getByLabel("Ações BR (%)")).toHaveValue("");
  await expect(arca.getByRole("button", { name: "Salvar ARCA" })).toBeDisabled();
  for (const [categoria, valor] of [["Ações BR", "40,5"], ["FIIs", "19,5"], ["Caixa", "10"], ["Exterior", "20"]]) {
    await arca.getByLabel(`${categoria} (%)`).fill(valor);
  }
  await expect(arca.getByRole("button", { name: "Salvar ARCA" })).toBeDisabled();
  await arca.getByLabel("Exterior (%)").fill("30");
  await arca.getByRole("button", { name: "Salvar ARCA" }).click();
  await expect(page.getByText("Metas de ARCA salvas.")).toBeVisible();
  for (const [categoria, valor] of [["Caixa", "20"], ["FIIs", "20"], ["Ações BR", "20"], ["Cripto", "10"], ["Exterior", "20"], ["Negócios", "10"]]) {
    await kraken.getByLabel(`${categoria} (%)`).fill(valor);
  }
  await kraken.getByRole("button", { name: "Salvar KRAKEN" }).click();
  await expect(page.getByText("Metas de KRAKEN salvas.")).toBeVisible();
  await page.reload();
  await expect(arca.getByLabel("Ações BR (%)")).toHaveValue("40.5");
  await expect(kraken.getByLabel("Negócios (%)")).toHaveValue("10");
  const acessibilidadeConfig = await new AxeBuilder({ page }).include(".configuracoes-conteudo").analyze();
  expect(acessibilidadeConfig.violations.filter((item) => item.impact === "serious" || item.impact === "critical")).toEqual([]);

  await page.goto("/portfolio");
  const card = (nome: string) => page.locator(".card.exposicao").filter({ hasText: `Exposição ${nome}` });
  const linha = (nome: string, categoria: string) => card(nome).locator(".barra-linha").filter({ hasText: categoria });
  await expect(linha("ARCA", "Ações BR").locator(".barra-valor").nth(0)).toContainText("25,00%");
  await expect(linha("ARCA", "Ações BR").locator(".barra-valor").nth(1)).toContainText("40,50%");
  await expect(linha("KRAKEN", "FIIs").locator(".barra-valor").nth(1)).toContainText("20,00%");
  const acessibilidadeExposicoes = await new AxeBuilder({ page }).include(".exposicoes").analyze();
  expect(acessibilidadeExposicoes.violations.filter((item) => item.impact === "serious" || item.impact === "critical")).toEqual([]);
  await page.getByRole("button", { name: "Ajuda sobre Exposição ARCA" }).click();
  await expect(page.getByRole("tooltip")).toContainText("R = FIIs (Real Estate)");
  await page.keyboard.press("Escape");
  await page.getByRole("button", { name: "Ajuda sobre Exposição KRAKEN" }).click();
  await expect(page.getByRole("tooltip")).toContainText("K = Cripto; E = Exterior; N = Negócios");
  await page.keyboard.press("Escape");

  await page.goto("/alocacao");
  const painelArca = page.locator(".painel").filter({ has: page.getByRole("heading", { name: "ARCA", exact: true }) });
  await expect(painelArca.getByRole("columnheader", { name: "Meta" })).toBeVisible();
  const linhaFii = painelArca.getByRole("row", { name: /FIIs/ });
  await expect(linhaFii).toContainText("75,00%");
  await expect(linhaFii).toContainText("19,50%");

  await page.getByRole("banner").getByRole("button", { name: new RegExp(investidor.nome) }).click();
  const seletor = page.getByRole("group", { name: "Filtrar por investidores" });
  await seletor.getByRole("checkbox", { name: outro.nome }).check();
  await page.getByRole("heading", { name: "Alocação & Rebalanceamento" }).click();
  await expect(linhaFii.getByRole("cell").last()).toHaveText("—");
  await page.goto("/portfolio");
  await expect(linha("ARCA", "Ações BR").locator(".barra-valor").last()).toContainText("—");
  await page.setViewportSize({ width: 360, height: 900 });
  await expect(linha("KRAKEN", "Negócios")).toBeVisible();
  await page.goto("/configuracoes?secao=metas-metodologias");
  await page.getByRole("combobox", { name: "Investidor", exact: true }).selectOption(String(investidor.id));
  await expect(arca.getByLabel("Ações BR (%)")).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});

test("exposições ARCA e KRAKEN seguem investidores e classes do portfólio", async ({ page, request }) => {
  const investidor = await semear.investidor(request);
  const outroInvestidor = await semear.investidor(request);
  const acao = await semear.ativo(request);
  const fii = await semear.ativo(request, undefined, { classe: "FII" });
  const cripto = await semear.ativo(request, undefined, { classe: "CRIPTO", mercado: null });
  for (const [ativo, dono, preco] of [
    [acao, investidor, 10], [fii, investidor, 30], [cripto, investidor, 10],
    [acao, outroInvestidor, 90],
  ] as const) {
    await semear.operacao(request, {
      investidor_id: dono.id, ativo_id: ativo.id, data: "2026-03-02", evento: "C", quantidade: 10, preco,
    });
  }

  await page.goto("/portfolio");
  await selecionarInvestidorNoTopo(page, investidor.nome);
  const arca = page.locator(".card.exposicao").filter({ hasText: "Exposição ARCA" });
  const kraken = page.locator(".card.exposicao").filter({ hasText: "Exposição KRAKEN" });
  const linha = (card: typeof arca, nome: string) => card.locator(".barra-linha").filter({ hasText: nome });
  await expect(linha(arca, "FIIs")).toContainText("60,00%");
  await expect(linha(arca, "Exterior")).toContainText("20,00%");
  await expect(linha(kraken, "Cripto")).toContainText("20,00%");
  await expect(linha(kraken, "Ações BR")).toContainText("20,00%");
  await expect(linha(kraken, "Negócios")).toBeVisible();

  await page.getByText("Classes: Todas", { exact: true }).click();
  await page.getByLabel("FII", { exact: true }).uncheck();
  await expect(linha(arca, "FIIs")).toContainText("0,00%");
  await expect(linha(arca, "Exterior")).toContainText("50,00%");
  await expect(linha(kraken, "Cripto")).toContainText("50,00%");

  await page.getByLabel("Exposição", { exact: true }).uncheck();
  await expect(arca).toHaveCount(0);
  await expect(kraken).toHaveCount(0);
});

for (const [status, mensagem] of [
  [503, "Não foi possível carregar ARCA e KRAKEN: Serviço temporariamente indisponível"],
  [404, "Não foi possível carregar ARCA e KRAKEN. Atualize e reinicie o servidor da aplicação."],
] as const) {
  test(`portfólio informa falha ${status} ao carregar as metodologias`, async ({ page, request, errosConhecidos }) => {
    const investidor = await semear.investidor(request);
    const ativo = await semear.ativo(request);
    await semear.operacao(request, {
      investidor_id: investidor.id, ativo_id: ativo.id, data: "2026-03-02", evento: "C", quantidade: 1, preco: 10,
    });
    errosConhecidos.push({ achado: "Falha de API simulada pelo teste", padrao: new RegExp(`Failed to load resource: the server responded with a status of ${status}`) });
    await page.route("**/api/alocacao/metodologias*", (route) =>
      route.fulfill({ status, json: { detail: "Serviço temporariamente indisponível" } }),
    );
    await page.goto("/portfolio");
    await expect(page.getByText(mensagem, { exact: true })).toBeVisible();
    await expect(page.locator(".card.exposicao").filter({ hasText: "Exposição ARCA" })).toHaveCount(0);
    await expect(page.getByText("Exposição por classe")).toBeVisible();
  });
}

test("meus valuations inclui ativos fora da carteira e o portfólio respeita o investidor", async ({ page, request }) => {
    const investidor = await semear.investidor(request);
    const outroInvestidor = await semear.investidor(request);
    const primeiro = await semear.ativo(request);
    const segundo = await semear.ativo(request);
    const semCalculo = await semear.ativo(request);
    const fora = await semear.ativo(request);
    const outro = await semear.ativo(request);
    for (const [ativo, dono] of [
      [primeiro, investidor], [segundo, investidor], [semCalculo, investidor], [outro, outroInvestidor],
    ] as const) {
      await semear.operacao(request, {
        investidor_id: dono.id, ativo_id: ativo.id, data: "2026-03-02", evento: "C", quantidade: 10, preco: 25,
      });
    }
    const calculo = (graham: number, bazin: number) => ({
      calculado_em: "2026-03-03T10:00:00", cotacao: 80, preco_mediano: (graham + bazin) / 2, upside: null,
      modelos_disponiveis: 2,
      modelos: { graham, bazin, dcf_fcfe: null, gordon: null, pl_historico: null, pl_setor: null, pvp_justificado: null },
      premissas: {},
    });
    const item = (ativo: typeof primeiro, graham: number, bazin: number) => ({
      ativo_id: ativo.id, ticker: ativo.ticker, nome: ativo.ticker, classe: "AÇÃO", moeda: "BRL",
      cotacao: 80, cotacao_data: "2026-03-03", upside_atual: null, calculos: [calculo(graham, bazin)],
    });
    await page.route("**/api/valuation/historico", (route) => route.fulfill({
      json: [item(primeiro, 100, 200), item(segundo, 200, 200), item(fora, 100, 200), item(outro, 100, 200)],
    }));
    await page.route("**/api/posicoes?*", async (route) => {
      const resposta = await route.fetch();
      const posicoes = await resposta.json() as { ativo_id: number; cotacao: number | null }[];
      for (const posicao of posicoes) {
        if ([primeiro.id, segundo.id, semCalculo.id, outro.id].includes(posicao.ativo_id)) posicao.cotacao = 80;
      }
      await route.fulfill({ response: resposta, json: posicoes });
    });

    await page.goto(`/valuation?ativo=${primeiro.id}`);
    await expect(page).toHaveURL(new RegExp(`/novo-valuation\\?ativo=${primeiro.id}$`));
    await page.goto("/valuations-salvos");
    await expect(page).toHaveURL(/\/meus-valuations$/);
    await expect(page.getByRole("row", { name: new RegExp(fora.ticker) })).toBeVisible();

    await page.goto("/portfolio");
    await selecionarInvestidorNoTopo(page, investidor.nome);
    await page.getByRole("group", { name: "Visões do portfólio" }).getByRole("button", { name: "Valuation" }).click();
    const tabela = page.getByRole("table", { name: "Posições do portfólio" });
    await expect(tabela.getByRole("row", { name: new RegExp(primeiro.ticker) })).toContainText("46,67%");
    await page.getByLabel("Referência da margem").selectOption("graham");
    await expect(tabela.getByRole("row", { name: new RegExp(primeiro.ticker) })).toContainText("20,00%");

    await expect(tabela.getByRole("row", { name: new RegExp(semCalculo.ticker) })).toBeVisible();
    await expect(tabela.getByRole("row", { name: new RegExp(fora.ticker) })).toHaveCount(0);
    await expect(tabela.getByRole("row", { name: new RegExp(outro.ticker) })).toHaveCount(0);
    await page.goto("/meus-valuations");
    await expect(page.getByRole("row", { name: new RegExp(primeiro.ticker) })).toBeVisible();
    await expect(page.getByRole("row", { name: new RegExp(fora.ticker) })).toBeVisible();
    await expect(page.getByRole("row", { name: new RegExp(outro.ticker) })).toBeVisible();
    await expect(page.getByRole("complementary").getByRole("link", { name: /Valuation da carteira/ })).toHaveCount(0);
});

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
  await selecionarInvestidorNoTopo(page, investidor.nome);
  const tabela = page.getByRole("table", { name: "Posições do portfólio" });
  const linha = tabela.getByRole("row", { name: new RegExp(ativo.ticker) });
  await expect(linha).toBeVisible();

  for (const titulo of [
    "Ativo",
    "Classe",
    "Peso",
    "Qtd",
    "Cotação",
    "Mercado",
    "Setor",
  ]) {
    await expect(tabela.getByRole("columnheader", { name: titulo })).toBeVisible();
  }
  await expect(linha.getByText("Energia", { exact: true })).toBeVisible();
  await expect(linha.getByText("AÇÃO", { exact: true })).toBeVisible();
  await expect(tabela.getByRole("columnheader", { name: "Ações" })).toHaveCount(0);
  await expect(linha.getByRole("button", { name: `Ações de ${ativo.ticker}` })).toHaveCount(0);
  await expect(linha.getByText("Petróleo", { exact: true })).toHaveCount(0);
  const indisponibilidade = linha.getByRole("button", {
    name: `Motivo da indisponibilidade de Mercado para ${ativo.ticker}`,
  });
  await indisponibilidade.scrollIntoViewIfNeeded();
  await indisponibilidade.focus();
  await expect(page.getByRole("tooltip")).toContainText("A cotação atual do ativo não está disponível.");
  await page.keyboard.press("Escape");

  const visoes = page.getByRole("group", { name: "Visões do portfólio" });
  await visoes.getByRole("button", { name: "Rentabilidade" }).click();
  await expect(tabela.getByRole("columnheader", { name: "Classe", exact: true })).toBeVisible();
  await expect(linha.getByText("AÇÃO", { exact: true })).toBeVisible();
  await expect(tabela.getByRole("columnheader", { name: "Ações" })).toHaveCount(0);
  await expect(linha.getByRole("button", { name: `Ações de ${ativo.ticker}` })).toHaveCount(0);
  for (const titulo of ["PM (R$)", "Custo ajustado", "Mercado", "Lucro dia", "Lucro aberto", "TIR a.a."]) {
    await expect(tabela.getByRole("columnheader", { name: titulo })).toBeVisible();
  }
  await expect(tabela.getByRole("columnheader", { name: "Proventos" })).toHaveCount(0);
  await expect(linha.getByText(/c\/ renda/)).toBeVisible();

  await visoes.getByRole("button", { name: "Proventos" }).click();
  await expect(tabela.getByRole("columnheader", { name: "Classe", exact: true })).toBeVisible();
  await expect(linha.getByText("AÇÃO", { exact: true })).toBeVisible();
  await expect(tabela.getByRole("columnheader", { name: "Ações" })).toHaveCount(0);
  await expect(linha.getByRole("button", { name: `Ações de ${ativo.ticker}` })).toHaveCount(0);
  for (const titulo of ["Proventos", "Aluguel", "YoC 12m"]) {
    await expect(tabela.getByRole("columnheader", { name: titulo })).toBeVisible();
  }
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

  await visoes.getByRole("button", { name: "Valuation" }).click();
  await expect(tabela.getByRole("columnheader", { name: "Classe", exact: true })).toBeVisible();
  await expect(linha.getByText("AÇÃO", { exact: true })).toBeVisible();
  await expect(tabela.getByRole("columnheader", { name: "Graham" })).toBeVisible();
  await expect(tabela.getByRole("columnheader", { name: "Margem de segurança" })).toBeVisible();
  await expect(tabela.getByRole("columnheader", { name: "Proventos" })).toHaveCount(0);
  await expect(tabela.getByRole("columnheader", { name: "Ações" })).toBeVisible();
  const acoes = linha.getByRole("button", { name: `Ações de ${ativo.ticker}` });
  await acoes.focus();
  await page.keyboard.press("Enter");
  await expect(linha.getByRole("link", { name: "Abrir valuation" })).toBeVisible();
  await expect(linha.getByRole("button", { name: "Ver modelos" })).toHaveCount(0);

  await page.getByLabel("Agrupar").selectOption("classe");
  const subtotal = tabela.locator("tr.linha-grupo td").first();
  await expect(subtotal).toHaveAttribute("colspan", String(await tabela.getByRole("columnheader").count()));
  await visoes.getByRole("button", { name: "Resumo" }).click();
  await expect(subtotal).toHaveAttribute("colspan", String(await tabela.getByRole("columnheader").count()));
  await visoes.getByRole("button", { name: "Valuation" }).click();

  await page.setViewportSize({ width: 360, height: 640 });
  const dimensoes = await page.locator(".portfolio-tabela-container").evaluate((container) => ({
    largura: container.clientWidth,
    rolagem: container.scrollWidth,
    pagina: document.documentElement.scrollWidth,
  }));
  expect(dimensoes.rolagem).toBeGreaterThan(dimensoes.largura);
  expect(dimensoes.pagina).toBeLessThanOrEqual(360);
});
