import { expect, semear, test } from "./apoio";

test("ajuda dos indicadores funciona com mouse e teclado", async ({ page }) => {
  await page.goto("/portfolio");
  const botao = page.getByRole("button", { name: "Ajuda sobre Valor investido" });
  await expect(botao).toBeVisible();
  await expect(page.getByRole("tooltip")).toHaveCount(0);
  const dimensoes = await botao.evaluate((elemento) => {
    const botao = elemento.getBoundingClientRect();
    const icone = elemento.querySelector("svg")!.getBoundingClientRect();
    const estilo = getComputedStyle(elemento);
    return { largura: botao.width, altura: botao.height, icone: icone.width, cor: estilo.color, borda: estilo.borderWidth };
  });
  expect(dimensoes).toEqual({ largura: 24, altura: 24, icone: 14, cor: "rgb(148, 163, 184)", borda: "0px" });
  await botao.hover();
  await expect(botao).toHaveCSS("color", "rgb(100, 116, 139)");
  await expect(botao).toHaveCSS("background-color", "rgba(0, 0, 0, 0)");
  const dica = page.getByRole("tooltip");
  await expect(dica).toContainText("Capital efetivamente desembolsado");
  await page.mouse.move(0, 0);
  await expect(dica).toHaveCount(0);

  await botao.focus();
  await expect(dica).toBeVisible();
  await expect(botao).toHaveAttribute("aria-describedby", await dica.getAttribute("id") as string);
  await page.keyboard.press("Escape");
  await expect(dica).toHaveCount(0);
});

test("ajudas de valuation e operações usam o mesmo ícone e preservam suas interações", async ({ page, request }) => {
  const ativo = await semear.ativo(request);
  await page.goto(`/valuation?ativo=${ativo.id}`);
  const lpa = page.getByRole("button", { name: /^Ajuda sobre LPA:/ });
  await expect(lpa).toBeVisible();
  await expect(lpa.locator("svg")).toHaveAttribute("width", "14");
  await expect(lpa.locator("svg circle")).toHaveCount(1);
  await expect(lpa).toHaveCSS("border-width", "0px");
  await expect(lpa).toHaveCSS("background-color", "rgba(0, 0, 0, 0)");
  await expect(lpa).toHaveCSS("color", "rgb(148, 163, 184)");
  const posicaoLpa = await lpa.evaluate((elemento) => {
    const texto = document.createRange();
    texto.selectNodeContents(elemento.parentElement!.firstChild!);
    const rotulo = texto.getBoundingClientRect();
    const icone = elemento.querySelector("svg")!.getBoundingClientRect();
    const alvo = getComputedStyle(elemento, "::before");
    const botao = elemento.getBoundingClientRect();
    return {
      distancia: icone.left - rotulo.right,
      desalinhamento: Math.abs(icone.top + icone.height / 2 - rotulo.top - rotulo.height / 2),
      larguraAlvo: botao.width - parseFloat(alvo.left) - parseFloat(alvo.right),
      alturaAlvo: botao.height - parseFloat(alvo.top) - parseFloat(alvo.bottom),
    };
  });
  expect(posicaoLpa.distancia).toBeGreaterThanOrEqual(4);
  expect(posicaoLpa.distancia).toBeLessThanOrEqual(6);
  expect(posicaoLpa.desalinhamento).toBeLessThan(2);
  expect(posicaoLpa.larguraAlvo).toBe(24);
  expect(posicaoLpa.alturaAlvo).toBe(24);
  await lpa.hover();
  await expect(lpa).toHaveCSS("color", "rgb(100, 116, 139)");
  expect(await lpa.evaluate((elemento) => getComputedStyle(elemento, "::after").content)).toContain("Lucro líquido por ação");
  expect(await lpa.evaluate((elemento) => getComputedStyle(elemento, "::after").display)).toBe("block");
  await page.mouse.move(0, 0);
  await lpa.focus();
  expect(await lpa.evaluate((elemento) => getComputedStyle(elemento, "::after").display)).toBe("block");
  await expect(lpa).toHaveCSS("outline-style", "solid");

  await page.goto("/operacoes");
  const ajuda = page.getByRole("button", { name: "Ajuda sobre os eventos de operações" });
  await expect(ajuda.locator("svg")).toHaveAttribute("width", "14");
  await expect(ajuda.locator("svg circle")).toHaveCount(1);
  await expect(ajuda).toHaveCSS("border-width", "0px");
  await expect(ajuda).toHaveCSS("color", "rgb(148, 163, 184)");
  await ajuda.focus();
  await expect(ajuda).toHaveCSS("outline-style", "solid");
  await page.keyboard.press("Enter");
  await expect(page.getByRole("dialog", { name: "Eventos de operações" })).toContainText("Entrada de ativos por compra");
});

test("ajuda nos cabeçalhos mantém ícone discreto e linha compacta", async ({ page, request }) => {
  const investidor = await semear.investidor(request);
  const ativo = await semear.ativo(request);
  await semear.operacao(request, {
    investidor_id: investidor.id,
    ativo_id: ativo.id,
    data: "2025-01-01",
    evento: "C",
    quantidade: 10,
    preco: 10,
  });
  await page.goto("/portfolio");
  await page.getByRole("group", { name: "Visões do portfólio" }).getByRole("button", { name: "Rentabilidade" }).click();
  const cabecalho = page.getByRole("columnheader", { name: "Custo ajustado" });
  const ajuda = cabecalho.getByRole("button", { name: "Ajuda sobre Custo ajustado" });
  const medidas = await ajuda.evaluate((elemento) => {
    const rotulo = elemento.parentElement!.querySelector(".ordenar")!.getBoundingClientRect();
    const icone = elemento.querySelector("svg")!.getBoundingClientRect();
    const linha = elemento.closest("tr")!.getBoundingClientRect();
    return {
      distancia: icone.left - rotulo.right,
      desalinhamento: Math.abs(icone.top + icone.height / 2 - rotulo.top - rotulo.height / 2),
      alturaLinha: linha.height,
    };
  });
  expect(medidas.distancia).toBeGreaterThanOrEqual(4);
  expect(medidas.distancia).toBeLessThanOrEqual(6);
  expect(medidas.desalinhamento).toBeLessThan(2);
  expect(medidas.alturaLinha).toBeLessThanOrEqual(48);
  await expect(ajuda.locator("svg")).toHaveAttribute("width", "14");
  await expect(ajuda.locator("svg circle")).toHaveCount(1);
  await expect(ajuda).toHaveCSS("border-width", "0px");
  await ajuda.hover();
  await expect(ajuda).toHaveCSS("color", "rgb(100, 116, 139)");
  await expect(page.getByRole("tooltip")).toContainText("Custo contábil atual da posição");
});

test("apenas uma ajuda fica aberta e exposição usa o mesmo ícone", async ({ page, request }) => {
  const investidor = await semear.investidor(request);
  const ativo = await semear.ativo(request);
  await semear.operacao(request, {
    investidor_id: investidor.id,
    ativo_id: ativo.id,
    data: "2025-01-01",
    evento: "C",
    quantidade: 10,
    preco: 10,
  });
  await page.goto("/portfolio");
  const primeiro = page.getByRole("button", { name: "Ajuda sobre Valor investido" });
  const exposicao = page.getByRole("button", { name: "Ajuda sobre Exposição por classe" });
  await expect(exposicao).toBeVisible();
  await primeiro.focus();
  await expect(page.getByRole("tooltip")).toHaveCount(1);
  await exposicao.hover();
  await expect(page.getByRole("tooltip")).toHaveCount(1);
  await expect(page.getByRole("tooltip")).toContainText("Soma do valor de mercado");
  await expect(exposicao.locator("svg")).toHaveAttribute("width", "14");
  await exposicao.click();
  await expect(page.getByRole("tooltip")).toHaveCount(1);
  await expect(exposicao).toHaveAttribute("aria-expanded", "true");
});

test("ajuda permanece visível em tela estreita", async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 640 });
  await page.goto("/portfolio");
  const botao = page.getByRole("button", { name: "Ajuda sobre Lucro total" });
  await botao.focus();
  const dica = page.getByRole("tooltip");
  await expect(dica).toContainText("Resultado das posições abertas");
  const caixa = await dica.boundingBox();
  expect(caixa).not.toBeNull();
  expect(caixa!.x).toBeGreaterThanOrEqual(0);
  expect(caixa!.x + caixa!.width).toBeLessThanOrEqual(360);
});

test("ajuda acompanha o fim do título quebrado", async ({ page }) => {
  await page.goto("/portfolio");
  for (const width of [360, 768, 1024, 1280, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    for (const [titulo, palavraFinal] of [
      ["Resultado das posições abertas", "abertas"],
      ["Custo contábil das posições", "posições"],
    ]) {
      const botao = page.getByRole("button", { name: `Ajuda sobre ${titulo}` });
      const posicoes = await botao.evaluate((elemento, palavraFinal) => {
        const texto = elemento.closest(".ajuda-indicador-grupo")!.firstChild!;
        const faixa = document.createRange();
        const conteudo = texto.textContent ?? "";
        const inicio = conteudo.lastIndexOf(palavraFinal);
        faixa.setStart(texto, inicio);
        faixa.setEnd(texto, inicio + palavraFinal.length);
        const palavra = faixa.getBoundingClientRect();
        const icone = elemento.getBoundingClientRect();
        return { palavraY: palavra.top + palavra.height / 2, iconeY: icone.top + icone.height / 2 };
      }, palavraFinal);
      expect(Math.abs(posicoes.palavraY - posicoes.iconeY), `${titulo}, largura ${width}px`).toBeLessThan(12);
    }
  }
});
