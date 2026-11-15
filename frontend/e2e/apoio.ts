import { test as base, expect, type APIRequestContext, type Page } from "@playwright/test";

/** Único destino que o navegador pode acessar nos testes: o backend descartável do E2E. */
const HOST_PERMITIDO = `127.0.0.1:${process.env.E2E_PORTA ?? 8765}`;

interface Fixtures {
  /** Erros do console e exceções não tratadas da página: o teste falha se sobrar algum não conhecido. */
  errosConsole: string[];
  /**
   * Erros já registrados como achado (com ID no relatório): não falham o teste, mas viram anotação.
   * Cada teste acrescenta os seus; nunca use para esconder erro novo.
   */
  errosConhecidos: { achado: string; padrao: RegExp }[];
  /** URLs externas que a página tentou acessar e foram bloqueadas. */
  requisicoesBloqueadas: string[];
}

export const test = base.extend<Fixtures>({
  errosConsole: async ({}, use) => {
    await use([]);
  },
  errosConhecidos: async ({}, use) => {
    await use([]);
  },
  requisicoesBloqueadas: async ({}, use) => {
    await use([]);
  },
  page: async ({ page, errosConsole, errosConhecidos, requisicoesBloqueadas }, use, testInfo) => {
    await page.route("**/*", (rota) => {
      const url = new URL(rota.request().url());
      if (url.host === HOST_PERMITIDO) return rota.continue();
      requisicoesBloqueadas.push(url.href);
      return rota.abort("blockedbyclient");
    });
    page.on("console", (mensagem) => {
      if (mensagem.type() !== "error") return;
      const origem = mensagem.location().url;
      errosConsole.push(`console: ${mensagem.text()}${origem ? ` [${origem}]` : ""}`);
    });
    page.on("pageerror", (erro) => errosConsole.push(`pageerror: ${erro.message}`));
    await use(page);
    if (requisicoesBloqueadas.length) {
      testInfo.annotations.push({ type: "rede externa bloqueada", description: requisicoesBloqueadas.join(", ") });
    }
    const inesperados = errosConsole.filter((erro) => {
      const conhecido = errosConhecidos.find(({ padrao }) => padrao.test(erro));
      if (conhecido) testInfo.annotations.push({ type: `achado ${conhecido.achado}`, description: erro });
      return !conhecido;
    });
    expect(inesperados, "erros no console do navegador").toEqual([]);
  },
});
export { expect };

// ---------- Dados fictícios ----------

const EXECUCAO = Date.now().toString(36).toUpperCase().slice(-4);
let contador = 0;

/** Identificador único na execução (o banco é novo a cada execução, mas os testes compartilham o mesmo banco). */
export function unico(prefixo: string): string {
  contador += 1;
  return `${prefixo}${EXECUCAO}${contador}`;
}

export const tickerFicticio = () => unico("TST");
export const nomeFicticio = (rotulo = "Investidor") => `${rotulo} E2E Fictício ${unico("")}`;

async function enviar<T>(request: APIRequestContext, metodo: "post" | "delete", caminho: string, dados?: unknown) {
  const resposta = await request[metodo](`/api${caminho}`, dados === undefined ? {} : { data: dados });
  expect(resposta.ok(), `${metodo.toUpperCase()} ${caminho}: ${resposta.status()} ${await resposta.text()}`).toBe(true);
  return (resposta.status() === 204 ? undefined : await resposta.json()) as T;
}

export interface Registro {
  id: number;
}

export const semear = {
  investidor: (request: APIRequestContext, nome = nomeFicticio()) =>
    enviar<Registro & { nome: string }>(request, "post", "/investidores", { nome, cor: "#2563eb" }),
  grupo: (request: APIRequestContext, nome = `Grupo E2E ${unico("")}`) =>
    enviar<Registro & { nome: string }>(request, "post", "/grupos", { nome }),
  ativo: (request: APIRequestContext, ticker = tickerFicticio()) =>
    enviar<Registro & { ticker: string }>(request, "post", "/ativos", {
      ticker,
      nome: `Ativo fictício ${ticker}`,
      classe: "AÇÃO",
      mercado: "BVMF",
      moeda: "BRL",
    }),
  operacao: (
    request: APIRequestContext,
    dados: { investidor_id: number; ativo_id: number; data: string; evento: "C" | "V"; quantidade: number; preco: number },
  ) => enviar<Registro>(request, "post", "/operacoes", { ...dados, quantidade: dados.evento === "V" ? -Math.abs(dados.quantidade) : dados.quantidade }),
  provento: (
    request: APIRequestContext,
    dados: { investidor_id: number; ativo_id: number; data_pagamento: string; valor: number },
  ) => enviar<Registro>(request, "post", "/proventos", { ...dados, evento: "DIVIDENDO" }),
  noRadar: (request: APIRequestContext, ativoId: number) => enviar<unknown>(request, "post", `/radar/${ativoId}`),
};

export async function listarBackups(request: APIRequestContext) {
  const resposta = await request.get("/api/backups");
  expect(resposta.ok()).toBe(true);
  return ((await resposta.json()) as { itens: { nome: string; tipo: string }[] }).itens;
}

// ---------- Interação ----------

/**
 * Executa uma ação que abre `confirm()` nativo e responde a ele. Devolve o texto exibido ao usuário.
 * Sem um tratador, o Playwright recusaria o diálogo silenciosamente.
 */
export async function responderConfirmacao(page: Page, resposta: "aceitar" | "cancelar", acao: () => Promise<unknown>) {
  let mensagem = "";
  const tratado = new Promise<void>((resolver) => {
    page.once("dialog", async (dialogo) => {
      mensagem = dialogo.message();
      if (resposta === "aceitar") await dialogo.accept();
      else await dialogo.dismiss();
      resolver();
    });
  });
  await acao();
  await tratado;
  return mensagem;
}

/** Marca um único investidor no seletor global do topo. */
export async function selecionarInvestidorNoTopo(page: Page, nome: string) {
  await page.getByRole("banner").getByRole("button", { name: /Todos os investidores/ }).click();
  await page.getByRole("menu").getByRole("checkbox", { name: nome }).check();
  await page.getByRole("heading", { level: 1 }).first().click();
  await expect(page.getByRole("menu")).toBeHidden();
  await expect(page.getByRole("banner").getByRole("button", { name: new RegExp(nome) })).toBeVisible();
}

/** Esperada a resposta do filtro (a lista mantém os dados anteriores na tela enquanto busca). */
export async function filtrarPorAtivo(page: Page, ticker: string, total: number) {
  await page.getByLabel("Filtrar por um ou mais ativos").fill(ticker);
  await expect(page.getByText(new RegExp(`Página 1 de 1 · ${total} registros`))).toBeVisible();
  await expect(page.getByText("Carregando…")).toHaveCount(0);
}

/** Página aberta sem o fallback de erro do LimiteErro. */
export async function esperarPaginaSemErro(page: Page, titulo: string | RegExp) {
  await expect(page.getByRole("heading", { level: 1, name: titulo }).first()).toBeVisible();
  await expect(page.getByRole("heading", { name: "Não foi possível exibir esta página" })).toHaveCount(0);
}
