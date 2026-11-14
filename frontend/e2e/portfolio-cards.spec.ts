import { expect, test } from "./apoio";

test("quadros do portfólio usam até cinco colunas conforme o espaço disponível", async ({ page }) => {
  await page.goto("/portfolio");
  const grade = page.locator(".cards-portfolio");
  const cards = page.locator(".cards-portfolio > .card");
  await expect(cards).toHaveCount(10);

  for (const [largura, colunas] of [[200, 1], [360, 2], [560, 3], [740, 4], [920, 5], [1800, 5]]) {
    await grade.evaluate((elemento, valor) => { elemento.style.width = `${valor}px`; }, largura);
    const medidas = await grade.evaluate((elemento) => ({
      colunas: getComputedStyle(elemento).gridTemplateColumns.split(" ").length,
      largura: elemento.clientWidth,
      conteudo: elemento.scrollWidth,
    }));
    expect(medidas.colunas, `largura ${largura}px`).toBe(colunas);
    expect(medidas.conteudo).toBeLessThanOrEqual(medidas.largura);
  }
  await grade.evaluate((elemento) => { elemento.style.width = ""; });

  for (const width of [360, 780, 1440, 2400]) {
    await page.setViewportSize({ width, height: 900 });
    for (const zoom of [0.5, 1, 1.75, 2]) {
      await page.evaluate((valor) => { document.documentElement.style.zoom = String(valor); }, zoom);
      const medidas = await grade.evaluate((elemento) => ({
        colunas: getComputedStyle(elemento).gridTemplateColumns.split(" ").length,
        largura: elemento.clientWidth,
        conteudo: elemento.scrollWidth,
      }));
      expect(medidas.colunas, `largura ${width}, zoom ${zoom}`).toBeLessThanOrEqual(5);
      expect(medidas.conteudo, `largura ${width}, zoom ${zoom}`).toBeLessThanOrEqual(medidas.largura + 1);
    }
  }
});
