import AxeBuilder from "@axe-core/playwright";
import { esperarPaginaSemErro, expect, semear, test } from "./apoio";

const PAGINAS = [
  { caminho: "/", titulo: "Resumo" },
  { caminho: "/portfolio", titulo: "Portfólio" },
  { caminho: "/operacoes", titulo: "Operações" },
  { caminho: "/proventos", titulo: "Proventos" },
  { caminho: "/caixa", titulo: "Caixa" },
  { caminho: "/dashboard", titulo: "Rentabilidade" },
  { caminho: "/cripto", titulo: "Cripto" },
  { caminho: "/ir", titulo: "Imposto de Renda" },
  { caminho: "/radar", titulo: "Radar" },
  { caminho: "/configuracoes", titulo: "Configurações" },
] as const;

/**
 * Violações já registradas como achado no relatório (qa-report/testes-e2e). Não falham o teste, viram anotação;
 * qualquer outra violação serious/critical falha. Remova a entrada quando o achado for corrigido.
 */
const VIOLACOES_CONHECIDAS: Record<string, { regra: string; achado: string }[]> = {};

test.describe("Acessibilidade (axe-core, WCAG 2.x A/AA)", () => {
  test.beforeAll(async ({ request }) => {
    const investidor = await semear.investidor(request);
    const ativo = await semear.ativo(request);
    await semear.operacao(request, { investidor_id: investidor.id, ativo_id: ativo.id, data: "2026-03-02", evento: "C", quantidade: 10, preco: 25 });
    await semear.provento(request, { investidor_id: investidor.id, ativo_id: ativo.id, data_pagamento: "2026-04-01", valor: 3.2 });
    await semear.noRadar(request, ativo.id);
  });

  for (const { caminho, titulo } of PAGINAS) {
    test(`E2E-T-046 ${titulo} sem violações graves ou críticas`, async ({ page }, testInfo) => {
      await page.goto(caminho);
      await esperarPaginaSemErro(page, /.+/);
      await expect(page).toHaveTitle(`${titulo} · InvestHub+`);
      await expect(page.getByText("Carregando…")).toHaveCount(0);

      const raiosBotoes = await page
        .locator("button:not(.aba):not(.campo-data-calendario)")
        .evaluateAll((botoes) =>
          botoes.flatMap((botao) => {
            const estilo = getComputedStyle(botao);
            return [
              estilo.borderTopLeftRadius,
              estilo.borderTopRightRadius,
              estilo.borderBottomRightRadius,
              estilo.borderBottomLeftRadius,
            ];
          }),
        );
      expect(raiosBotoes.every((raio) => raio === "6px"), "raio dos botões fora do padrão").toBe(true);

      const resultado = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"]).analyze();
      await testInfo.attach("axe.json", { body: JSON.stringify(resultado.violations, null, 2), contentType: "application/json" });
      const conhecidas = VIOLACOES_CONHECIDAS[caminho] ?? [];
      const graves = resultado.violations
        .filter((v) => v.impact === "serious" || v.impact === "critical")
        .filter((v) => {
          const conhecida = conhecidas.find((c) => c.regra === v.id);
          if (conhecida) testInfo.annotations.push({ type: `achado ${conhecida.achado}`, description: `${v.id}: ${v.help}` });
          return !conhecida;
        })
        .map((v) => `${v.id} (${v.impact}, ${v.nodes.length} nó(s)): ${v.nodes.slice(0, 3).map((n) => n.target.join(" ")).join(" | ")}`);
      expect(graves, "violações axe serious/critical").toEqual([]);
    });
  }
});
