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
  expect(dimensoes).toEqual({ largura: 24, altura: 24, icone: 16, cor: "rgb(148, 163, 184)", borda: "0px" });
  await botao.hover();
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
  await expect(exposicao.locator("svg")).toHaveAttribute("width", "16");
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
