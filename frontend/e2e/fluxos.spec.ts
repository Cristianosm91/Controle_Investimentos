import { execFileSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";
import {
  esperarPaginaSemErro,
  expect,
  filtrarPorAtivo,
  listarBackups,
  nomeFicticio,
  responderConfirmacao,
  selecionarInvestidorNoTopo,
  semear,
  test,
  tickerFicticio,
} from "./apoio";

const PASTA_E2E = path.dirname(fileURLToPath(import.meta.url));
const PYTHON = process.env.E2E_PYTHON ?? path.resolve(PASTA_E2E, "..", "..", ".venv", "Scripts", "python.exe");

test.describe("Fluxos críticos", () => {
  test("E2E-T-027/008 cadastrar investidor, lançar compra e venda e ver a posição no Portfólio", { tag: "@smoke" }, async ({ page }) => {
    const nome = nomeFicticio();
    const ticker = tickerFicticio();

    await page.goto("/configuracoes");
    await esperarPaginaSemErro(page, "Configurações");
    const form = page.locator("form").filter({ has: page.getByRole("heading", { name: "Novo investidor" }) });
    await form.getByLabel("Nome", { exact: true }).fill(nome);
    await form.getByRole("button", { name: "Salvar" }).click();
    await expect(page.getByRole("row", { name: new RegExp(nome) })).toBeVisible();

    await page.getByRole("link", { name: "Operações", exact: true }).click();
    await esperarPaginaSemErro(page, "Operações");

    // Compra, com cadastro rápido do ativo fictício pelo próprio formulário.
    await page.getByRole("button", { name: "+ Nova operação" }).click();
    let dialogo = page.getByRole("dialog", { name: "Nova operação" });
    await dialogo.getByRole("combobox", { name: "Investidor", exact: true }).selectOption({ label: nome });
    await dialogo.getByRole("textbox", { name: /^Data Abrir calendário$/ }).fill("10/03/2026");
    await dialogo.getByRole("combobox", { name: "Ativo", exact: true }).fill(ticker);
    await dialogo.getByRole("button", { name: "Cadastrar ativo…" }).click();
    await dialogo.getByRole("combobox", { name: "Classe", exact: true }).selectOption("AÇÃO");
    await dialogo.getByRole("combobox", { name: "Mercado", exact: true }).selectOption("BVMF");
    await dialogo.getByRole("button", { name: `Cadastrar ${ticker}` }).click();
    await expect(dialogo.getByText("Ativo não cadastrado.")).toBeHidden();
    await expect(dialogo.getByRole("combobox", { name: "Evento", exact: true })).toHaveValue("C");
    await dialogo.getByRole("spinbutton", { name: "Quantidade", exact: true }).fill("100");
    await dialogo.getByRole("spinbutton", { name: "Preço unitário", exact: true }).fill("50");
    await dialogo.getByRole("button", { name: "Salvar" }).click();
    await expect(dialogo).toBeHidden();

    // Venda parcial.
    await page.getByRole("button", { name: "+ Nova operação" }).click();
    dialogo = page.getByRole("dialog", { name: "Nova operação" });
    await dialogo.getByRole("combobox", { name: "Investidor", exact: true }).selectOption({ label: nome });
    await dialogo.getByRole("textbox", { name: /^Data Abrir calendário$/ }).fill("15/04/2026");
    await dialogo.getByRole("combobox", { name: "Ativo", exact: true }).fill(ticker);
    await expect(dialogo.getByText("Ativo não cadastrado.")).toBeHidden();
    await dialogo.getByRole("combobox", { name: "Evento", exact: true }).selectOption("V");
    await dialogo.getByRole("spinbutton", { name: "Quantidade", exact: true }).fill("40");
    await dialogo.getByRole("spinbutton", { name: "Preço unitário", exact: true }).fill("60");
    await dialogo.getByRole("button", { name: "Salvar" }).click();
    await expect(dialogo).toBeHidden();

    await filtrarPorAtivo(page, ticker, 2);
    const linhas = page.getByRole("row").filter({ hasText: ticker });
    await expect(linhas).toHaveCount(2);
    await expect(linhas.filter({ hasText: "10/03/2026" })).toContainText(nome);
    await expect(linhas.filter({ hasText: "15/04/2026" })).toContainText("-40");

    await selecionarInvestidorNoTopo(page, nome);
    await page.getByRole("link", { name: "Portfólio", exact: true }).click();
    await esperarPaginaSemErro(page, "Portfólio");
    const posicao = page.getByRole("row").filter({ hasText: ticker });
    await expect(posicao.first()).toBeVisible();
    await expect(posicao.first()).toContainText("60");
  });

  test("E2E-T-009 validação: campos obrigatórios bloqueiam o envio da operação", async ({ page, request }) => {
    const antes = ((await (await request.get("/api/operacoes")).json()) as { total: number }).total;
    await page.goto("/operacoes");
    await esperarPaginaSemErro(page, "Operações");
    await page.getByRole("button", { name: "+ Nova operação" }).click();
    const dialogo = page.getByRole("dialog", { name: "Nova operação" });
    await dialogo.getByRole("combobox", { name: "Investidor", exact: true }).selectOption("");
    await dialogo.getByRole("button", { name: "Salvar" }).click();
    await expect(dialogo).toBeVisible();
    for (const campo of [
      dialogo.getByRole("combobox", { name: "Investidor", exact: true }),
      dialogo.getByRole("combobox", { name: "Ativo", exact: true }),
      dialogo.getByRole("spinbutton", { name: "Quantidade", exact: true }),
    ]) {
      expect(await campo.evaluate((el: HTMLInputElement | HTMLSelectElement) => el.checkValidity())).toBe(false);
    }
    await dialogo.getByRole("button", { name: "Cancelar" }).click();
    await expect(dialogo).toBeHidden();
    expect(((await (await request.get("/api/operacoes")).json()) as { total: number }).total).toBe(antes);
  });

  test("E2E-T-006 erro da API na lista de operações exibe mensagem", async ({ page, errosConhecidos }) => {
    errosConhecidos.push({ achado: "esperado: erro 500 simulado pelo teste", padrao: /status of 500 .*\/api\/operacoes\?/ });
    await page.route("**/api/operacoes?**", (rota) =>
      rota.fulfill({ status: 500, json: { detail: "Falha simulada pelo teste E2E", erro_id: "e2e0000000000001" } }),
    );
    await page.goto("/operacoes");
    await esperarPaginaSemErro(page, "Operações");
    await expect(page.getByText("Falha simulada pelo teste E2E (código do erro: e2e0000000000001)")).toBeVisible();
  });

  test("E2E-T-011 exclusão em lote com Shift+clique e confirmação", async ({ page, request }) => {
    const investidor = await semear.investidor(request);
    const ativo = await semear.ativo(request);
    for (const [dia, quantidade] of [["2026-01-05", 1], ["2026-01-06", 2], ["2026-01-07", 3], ["2026-01-08", 4]] as const) {
      await semear.operacao(request, { investidor_id: investidor.id, ativo_id: ativo.id, data: dia, evento: "C", quantidade, preco: 10 });
    }

    await page.goto("/operacoes");
    await esperarPaginaSemErro(page, "Operações");
    await filtrarPorAtivo(page, ativo.ticker, 4);
    const linhas = page.getByRole("row").filter({ hasText: ativo.ticker });
    await expect(linhas).toHaveCount(4);

    const caixas = page.getByRole("checkbox", { name: /^Selecionar registro \d+$/ });
    await caixas.nth(0).click();
    await caixas.nth(2).click({ modifiers: ["Shift"] });
    await expect(page.getByText("3 selecionado(s)")).toBeVisible();
    await expect(caixas.nth(1)).toBeChecked();
    await expect(caixas.nth(3)).not.toBeChecked();

    const excluir = page.getByRole("button", { name: "Excluir selecionados" });
    const pergunta = await responderConfirmacao(page, "cancelar", () => excluir.click());
    expect(pergunta).toBe("Excluir 3 registro(s) selecionado(s) de Operações?");
    await expect(linhas).toHaveCount(4);

    await responderConfirmacao(page, "aceitar", () => excluir.click());
    await expect(page.getByText("3 registro(s) excluído(s).")).toBeVisible();
    await expect(linhas).toHaveCount(1);
    await expect(page.getByText("0 selecionado(s)")).toBeVisible();
  });

  test("E2E-T-013 lançar provento pela interface e ver na lista", { tag: "@smoke" }, async ({ page, request }) => {
    const investidor = await semear.investidor(request);
    const ativo = await semear.ativo(request);

    await page.goto("/proventos");
    await esperarPaginaSemErro(page, "Proventos");
    await page.getByRole("button", { name: "+ Novo provento" }).click();
    const dialogo = page.getByRole("dialog", { name: "Novo provento" });
    await dialogo.getByRole("combobox", { name: "Investidor", exact: true }).selectOption({ label: investidor.nome });
    await dialogo.getByRole("combobox", { name: "Ativo", exact: true }).fill(ativo.ticker);
    await expect(dialogo.getByText("Ativo não cadastrado.")).toBeHidden();
    await dialogo.getByRole("textbox", { name: /^Pagamento Abrir calendário$/ }).fill("20/05/2026");
    await dialogo.getByRole("spinbutton", { name: "Valor bruto", exact: true }).fill("123.45");
    await expect(dialogo.getByText(/Líquido: R\$\s123,45/)).toBeVisible();
    await dialogo.getByRole("button", { name: "Salvar" }).click();
    await expect(dialogo).toBeHidden();

    await filtrarPorAtivo(page, ativo.ticker, 1);
    const linha = page.getByRole("row").filter({ hasText: ativo.ticker });
    await expect(linha).toHaveCount(1);
    await expect(linha).toContainText("20/05/2026");
    await expect(linha).toContainText(investidor.nome);
    await expect(linha).toContainText(/R\$\s123,45/);
  });

  test("E2E-T-037 backup manual: gerar, ver na lista, cancelar e confirmar restauração", { tag: "@smoke" }, async ({ page, request }) => {
    const antes = new Set((await listarBackups(request)).map((b) => b.nome));

    await page.goto("/configuracoes?secao=backup");
    await expect(page.getByRole("heading", { name: "Backup e restauração" })).toBeVisible();
    await page.getByRole("button", { name: "Fazer backup agora" }).click();
    await expect(page.getByRole("button", { name: "Fazer backup agora" })).toBeEnabled();

    await expect.poll(async () => (await listarBackups(request)).filter((b) => !antes.has(b.nome)).length).toBe(1);
    const novo = (await listarBackups(request)).find((b) => !antes.has(b.nome))!;
    expect(novo.tipo).toBe("manual");
    const linha = page.getByRole("row").filter({ has: page.getByTitle(novo.nome, { exact: true }) });
    await expect(linha).toContainText("Manual");
    await expect(linha.getByRole("link", { name: "Baixar" })).toBeVisible();

    // Banco isolado do E2E: restaurar o backup recém-criado devolve o mesmo estado.
    const restaurar = linha.getByRole("button", { name: "Restaurar" });
    const aviso = await responderConfirmacao(page, "cancelar", () => restaurar.click());
    expect(aviso).toContain("Todos os dados atuais serão substituídos");
    await expect(page.getByText(/Banco restaurado de/)).toHaveCount(0);

    await responderConfirmacao(page, "aceitar", () => restaurar.click());
    await expect(page.getByText(/Banco restaurado de/)).toContainText(novo.nome);
    await expect(page.getByRole("row").filter({ hasText: "Antes de restaurar" }).first()).toBeVisible();
  });

  test("E2E-T-023 IR: apuração mostra o mês da venda com valores", { tag: "@smoke" }, async ({ page, request }) => {
    const investidor = await semear.investidor(request);
    const ativo = await semear.ativo(request);
    await semear.operacao(request, { investidor_id: investidor.id, ativo_id: ativo.id, data: "2026-03-10", evento: "C", quantidade: 1000, preco: 20 });
    await semear.operacao(request, { investidor_id: investidor.id, ativo_id: ativo.id, data: "2026-04-15", evento: "V", quantidade: 500, preco: 50 });

    await page.goto("/ir");
    await esperarPaginaSemErro(page, "Imposto de Renda");
    await selecionarInvestidorNoTopo(page, investidor.nome);
    const seletorIR = page.getByRole("combobox", { name: "Investidor (CPF)", exact: true });
    if (await seletorIR.count()) await expect(seletorIR).toHaveValue(String(investidor.id));

    await expect(page.getByRole("combobox", { name: "Ano", exact: true })).toHaveValue("2026");
    const mes = page.getByRole("row").filter({ has: page.getByRole("cell", { name: "abr./2026", exact: true }) });
    await expect(mes).toBeVisible();
    await expect(mes).toContainText(/R\$\s25\.000,00/); // vendas do mês (500 × R$ 50), só presença
    await expect(mes.getByRole("cell").filter({ hasText: /R\$/ }).first()).toBeVisible();
    for (const card of ["DARF no ano", "Pago no ano", "Saldo a pagar"]) {
      await expect(page.getByRole("main")).toContainText(new RegExp(`${card}\\W*R\\$\\s[\\d.]+,\\d{2}`));
    }
  });

  test("E2E-T-047 excluir investidor com todos os dados (PRI-001)", { tag: "@smoke" }, async ({ page, request }) => {
    const investidor = await semear.investidor(request);
    const ativo = await semear.ativo(request);
    await semear.operacao(request, { investidor_id: investidor.id, ativo_id: ativo.id, data: "2026-02-02", evento: "C", quantidade: 10, preco: 10 });
    await semear.operacao(request, { investidor_id: investidor.id, ativo_id: ativo.id, data: "2026-02-03", evento: "C", quantidade: 5, preco: 11 });
    await semear.provento(request, { investidor_id: investidor.id, ativo_id: ativo.id, data_pagamento: "2026-03-01", valor: 7.5 });
    const backupsAntes = new Set((await listarBackups(request)).map((b) => b.nome));

    await page.goto("/configuracoes");
    await esperarPaginaSemErro(page, "Configurações");
    const linha = page.getByRole("row", { name: new RegExp(investidor.nome) });
    await linha.getByRole("button", { name: "Excluir com todos os dados" }).click();

    const dialogo = page.getByRole("dialog", { name: `Excluir ${investidor.nome} com todos os dados` });
    await expect(dialogo).toBeVisible();
    const contagens = dialogo.getByRole("table", { name: "Registros que serão excluídos" });
    await expect(contagens.getByRole("row", { name: "Operações 2" })).toBeVisible();
    await expect(contagens.getByRole("row", { name: "Proventos 1" })).toBeVisible();
    await expect(contagens.getByRole("row", { name: "Total 3" })).toBeVisible();

    const confirmar = dialogo.getByRole("button", { name: "Excluir com todos os dados" });
    const campo = dialogo.getByRole("textbox", { name: /Para confirmar, digite o nome do investidor/ });
    await expect(confirmar).toBeDisabled();
    await campo.fill(`${investidor.nome} errado`);
    await expect(campo).toHaveAttribute("aria-invalid", "true");
    await expect(confirmar).toBeDisabled();
    await campo.fill(investidor.nome);
    await expect(confirmar).toBeEnabled();
    await confirmar.click();

    await expect(dialogo).toBeHidden();
    const aviso = page.getByRole("status").filter({ hasText: "foi excluído com todos os dados" });
    await expect(aviso).toContainText(`${investidor.nome} foi excluído com todos os dados. Backup criado antes da exclusão:`);
    await expect(page.getByRole("row", { name: new RegExp(investidor.nome) })).toHaveCount(0);

    const novos = (await listarBackups(request)).filter((b) => !backupsAntes.has(b.nome));
    expect(novos).toHaveLength(1);
    await expect(aviso).toContainText(novos[0].nome);

    await page.getByRole("banner").getByRole("button", { name: /Todos os investidores/ }).click();
    await expect(page.getByRole("menu")).toBeVisible();
    await expect(page.getByRole("menu").getByRole("checkbox", { name: investidor.nome })).toHaveCount(0);

    const resposta = await request.get(`/api/operacoes?investidores=${investidor.id}`);
    expect(((await resposta.json()) as { total: number }).total).toBe(0);
  });

  test("E2E-T-027b excluir grupo pede confirmação (cancelar mantém)", async ({ page, request }) => {
    const grupo = await semear.grupo(request);

    await page.goto("/configuracoes");
    await esperarPaginaSemErro(page, "Configurações");
    const excluir = page.getByRole("button", { name: `Excluir ${grupo.nome}`, exact: true });
    await expect(excluir).toBeVisible();

    const pergunta = await responderConfirmacao(page, "cancelar", () => excluir.click());
    expect(pergunta).toBe(`Excluir o grupo ${grupo.nome}?`);
    await expect(excluir).toBeVisible();

    await responderConfirmacao(page, "aceitar", () => excluir.click());
    await expect(excluir).toHaveCount(0);
  });

  test("E2E-T-020 remover do Radar pede confirmação (cancelar mantém)", async ({ page, request }) => {
    const ativo = await semear.ativo(request);
    await semear.noRadar(request, ativo.id);

    await page.goto("/radar");
    await esperarPaginaSemErro(page, "Radar");
    const linha = page.getByRole("row").filter({ hasText: ativo.ticker });
    await expect(linha).toHaveCount(1);
    await expect(linha).toContainText("Só no Radar");

    const remover = linha.getByRole("button", { name: "REMOVER" });
    const pergunta = await responderConfirmacao(page, "cancelar", () => remover.click());
    expect(pergunta).toBe(`Remover ${ativo.ticker} do Radar?`);
    await expect(linha).toHaveCount(1);

    await responderConfirmacao(page, "aceitar", () => remover.click());
    await expect(linha).toHaveCount(0);
  });

  test("E2E-T-014 importar extrato B3 fictício: prévia, importar e desfazer", { tag: "@smoke" }, async ({ page, request }, testInfo) => {
    const investidor = await semear.investidor(request);
    const ticker = tickerFicticio();
    const arquivo = testInfo.outputPath("negociacao-ficticia.xlsx");
    execFileSync(PYTHON, [path.join(PASTA_E2E, "gerar_extrato.py"), arquivo, ticker]);

    await page.goto("/operacoes");
    await esperarPaginaSemErro(page, "Operações");
    await page.getByRole("button", { name: "Importar extrato B3" }).click();
    const dialogo = page.getByRole("dialog", { name: "Importar extrato da B3" });
    await dialogo.getByRole("combobox", { name: "Investidor (CPF do extrato)", exact: true }).selectOption({ label: investidor.nome });
    await dialogo.getByLabel("Arquivo (.xlsx)").setInputFiles(arquivo);

    await expect(dialogo.getByText("Relatório: Negociação")).toBeVisible();
    await expect(dialogo.getByRole("button", { name: "Novo: 2" })).toBeVisible();
    await expect(dialogo.getByRole("row").filter({ hasText: ticker })).toHaveCount(2);
    await dialogo.getByRole("button", { name: "Importar 2 lançamento(s)" }).click();
    await expect(dialogo.getByText(/Importados:\s*2\s*operações/)).toBeVisible();
    const totalOperacoes = async () =>
      ((await (await request.get(`/api/operacoes?investidores=${investidor.id}`)).json()) as { total: number }).total;
    expect(await totalOperacoes()).toBe(2);

    const desfazer = dialogo.getByRole("button", { name: "Desfazer esta importação" });
    const pergunta = await responderConfirmacao(page, "cancelar", () => desfazer.click());
    expect(pergunta).toBe("Desfazer esta importação e remover os lançamentos gravados por ela?");
    expect(await totalOperacoes()).toBe(2);
    await responderConfirmacao(page, "aceitar", () => desfazer.click());
    await expect(dialogo.getByText(/Importação desfeita:\s*2\s*operação\(ões\)/)).toBeVisible();

    await dialogo.getByRole("button", { name: "Fechar", exact: true }).last().click();
    await expect(dialogo).toBeHidden();
    await filtrarPorAtivo(page, ticker, 0);
    await expect(page.getByRole("row").filter({ hasText: ticker })).toHaveCount(0);
    expect(await totalOperacoes()).toBe(0);
  });
});
