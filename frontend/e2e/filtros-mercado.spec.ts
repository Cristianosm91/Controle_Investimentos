import { expect, nomeFicticio, selecionarInvestidorNoTopo, semear, test } from "./apoio";

const ativoIds: number[] = [];
const operacaoIds: number[] = [];
const proventoIds: number[] = [];
let investidorId: number | undefined;

test.afterEach(async ({ request }) => {
  for (const id of operacaoIds.splice(0)) {
    const resposta = await request.delete(`/api/operacoes/${id}`);
    expect(resposta.status()).toBe(204);
  }
  for (const id of proventoIds.splice(0)) {
    const resposta = await request.delete(`/api/proventos/${id}`);
    expect(resposta.status()).toBe(204);
  }
  for (const id of ativoIds.splice(0)) {
    const resposta = await request.delete(`/api/ativos/${id}`);
    expect(resposta.status()).toBe(204);
  }
  if (investidorId !== undefined) {
    const resposta = await request.delete(`/api/investidores/${investidorId}`);
    expect(resposta.status()).toBe(204);
    investidorId = undefined;
  }
});

test("filtros multisseleção combinam mercado, classe e ativos e persistem nas abas de proventos", async ({
  page,
  request,
}) => {
  const investidor = await semear.investidor(request, nomeFicticio("Filtros"));
  investidorId = investidor.id;
  const brasileiros = [];
  for (let indice = 0; indice < 9; indice += 1) {
    brasileiros.push(await semear.ativo(request));
    ativoIds.push(brasileiros[brasileiros.length - 1].id);
  }
  const americano = await semear.ativo(request, undefined, { mercado: "NASDAQ" });
  ativoIds.push(americano.id);
  const cripto = await semear.ativo(request, undefined, {
    classe: "CRIPTO",
    mercado: null,
    moeda: "EUR",
    coingecko_id: `btc-${Date.now().toString(36)}`,
  });
  ativoIds.push(cripto.id);
  const ativos = [...brasileiros, americano, cripto];
  for (const ativo of ativos) {
    const operacao = await semear.operacao(request, {
      investidor_id: investidor.id,
      ativo_id: ativo.id,
      data: "2026-03-12",
      evento: "C",
      quantidade: 1,
      preco: 10,
      ...(ativo.id === cripto.id ? { moeda: "EUR", cambio: 1.1 } : {}),
    });
    operacaoIds.push(operacao.id);
    const provento = await semear.provento(request, {
      investidor_id: investidor.id,
      ativo_id: ativo.id,
      data_pagamento: "2026-03-20",
      valor: 1,
    });
    proventoIds.push(provento.id);
  }
  await page.goto("/operacoes");
  await selecionarInvestidorNoTopo(page, investidor.nome);

  const mercados = page.getByRole("group", { name: "Mercados" });
  await page.getByText("Todos os mercados", { exact: true }).click();
  await mercados.getByRole("button", { name: "Limpar seleção" }).click();
  await mercados.getByRole("checkbox", { name: "Brasil" }).check();
  await expect(page.getByRole("row", { name: new RegExp(brasileiros[0].ticker) })).toBeVisible();
  await expect(page.getByRole("row", { name: new RegExp(americano.ticker) })).toHaveCount(0);
  await expect(page.getByRole("row", { name: new RegExp(cripto.ticker) })).toHaveCount(0);

  const classes = page.getByRole("group", { name: "Classes" });
  await page.getByText("Todas as classes", { exact: true }).click();
  await classes.getByRole("button", { name: "Limpar seleção" }).click();
  await classes.getByRole("checkbox", { name: "Ações" }).check();

  const ativosFiltro = page.getByRole("group", { name: "Ativos" });
  await page.getByText("Todos os ativos", { exact: true }).click();
  const busca = ativosFiltro.getByRole("searchbox", { name: "Pesquisar ativos" });
  await busca.fill(brasileiros[0].ticker);
  await expect(ativosFiltro.getByRole("checkbox")).toHaveCount(1);
  await busca.fill("");
  await ativosFiltro.getByRole("button", { name: "Limpar seleção" }).click();
  await ativosFiltro.getByRole("checkbox", { name: brasileiros[0].ticker }).check();
  await ativosFiltro.getByRole("checkbox", { name: brasileiros[1].ticker }).check();
  await expect(page.getByRole("row", { name: new RegExp(brasileiros[0].ticker) })).toBeVisible();
  await expect(page.getByRole("row", { name: new RegExp(brasileiros[2].ticker) })).toHaveCount(0);

  await page.getByLabel("Mercados: Brasil").click();
  await mercados.getByRole("checkbox", { name: "EUA" }).check();
  await page.getByLabel(`Ativos: ${brasileiros[0].ticker} + ${brasileiros[1].ticker}`).click();
  await ativosFiltro.getByRole("checkbox", { name: americano.ticker }).check();
  await expect(page.getByRole("row", { name: new RegExp(americano.ticker) })).toBeVisible();
  await page.getByLabel("Mercados: Brasil + EUA").click();
  await mercados.getByRole("checkbox", { name: "EUA" }).uncheck();
  await expect(page.getByRole("row", { name: new RegExp(americano.ticker) })).toHaveCount(0);

  await page.goto("/proventos");
  const filtrosProventos = page.getByRole("group", { name: "Mercados" });
  await page.getByText("Todos os mercados", { exact: true }).click();
  await filtrosProventos.getByRole("button", { name: "Limpar seleção" }).click();
  await filtrosProventos.getByRole("checkbox", { name: "Brasil" }).check();
  await expect(page.getByRole("row", { name: new RegExp(brasileiros[0].ticker) })).toBeVisible();

  await page.getByRole("button", { name: "Matriz mensal" }).click();
  await expect(page.getByLabel("Mercados: Brasil")).toBeVisible();
  await page.getByRole("button", { name: "Agenda e projeção" }).click();
  await expect(page.getByLabel("Mercados: Brasil")).toBeVisible();
});
