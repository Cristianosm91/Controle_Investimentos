/** Exportação genérica: lê as tabelas renderizadas e pede ao backend um CSV ou XLSX tipado. */

export type Celula =
  | string
  | null
  | { n: number; f: "moeda" | "percentual" | "numero"; moeda?: "R$" | "US$" | "€" }
  | { d: string };

export interface Aba {
  titulo: string;
  colunas: string[];
  linhas: Celula[][];
}

export type Formato = "csv" | "xlsx";

const MOEDA = /^([+-]?)\s*(R\$|US\$|€)\s*([+-]?)(\d{1,3}(?:\.\d{3})*|\d+)(,\d+)?$/;
const PERCENTUAL = /^([+-]?(?:\d{1,3}(?:\.\d{3})*|\d+)(?:,\d+)?)\s*%$/;
// Sem zero à esquerda (preserva códigos como "0001"); milhar com ponto, decimal com vírgula.
const NUMERO = /^[+-]?(?:0|[1-9]\d{0,2}(?:\.\d{3})+|[1-9]\d*)(?:,\d+)?$|^[+-]?0,\d+$/;
const DATA = /^(\d{2})\/(\d{2})\/(\d{4})$/;
const VAZIO = new Set(["", "—", "–", "-"]);

const paraNumero = (texto: string) => Number(texto.replace(/\./g, "").replace(",", "."));

export function converter(bruto: string): Celula {
  const texto = bruto.replace(/[\u00a0\u202f]/g, " ").replace(/\u2212/g, "-").replace(/\s+/g, " ").trim();
  if (VAZIO.has(texto)) return null;
  let m = MOEDA.exec(texto);
  if (m) {
    const negativo = m[1] === "-" || m[3] === "-";
    const valor = paraNumero(m[4] + (m[5] ?? ""));
    return { n: negativo ? -valor : valor, f: "moeda", moeda: m[2] as "R$" | "US$" | "€" };
  }
  m = PERCENTUAL.exec(texto);
  if (m) return { n: Math.round((paraNumero(m[1]) / 100) * 1e10) / 1e10, f: "percentual" };
  if (NUMERO.test(texto)) return { n: paraNumero(texto), f: "numero" };
  m = DATA.exec(texto);
  if (m) return { d: `${m[3]}-${m[2]}-${m[1]}` };
  return texto;
}

function segmentos(celula: Element): string[] {
  const copia = celula.cloneNode(true) as Element;
  copia.querySelectorAll("button, input, select, textarea, svg, .acoes-linha, [data-exportar='ignorar']").forEach((e) => e.remove());
  const textos: string[] = [];
  let paiAnterior: Node | null = null;
  const caminhar = document.createTreeWalker(copia, NodeFilter.SHOW_TEXT);
  for (let no = caminhar.nextNode(); no; no = caminhar.nextNode()) {
    const texto = no.textContent ?? "";
    if (no.parentNode === paiAnterior && textos.length) textos[textos.length - 1] += texto;
    else if (texto.trim()) {
      textos.push(texto);
      paiAnterior = no.parentNode;
    }
  }
  for (let i = 0; i < textos.length; i++) textos[i] = textos[i].replace(/\s+/g, " ").trim();
  if (!textos.length) {
    const campo = celula.querySelector<HTMLInputElement | HTMLSelectElement>("input:not([type=checkbox]), select");
    if (campo) textos.push(campo instanceof HTMLSelectElement ? (campo.selectedOptions[0]?.textContent ?? "") : campo.value);
  }
  return textos;
}

const SETAS = /\s*[▲▼↑↓⇅]\s*/g;

function expandir(linha: HTMLTableRowElement): string[][] {
  const saida: string[][] = [];
  for (const celula of Array.from(linha.cells)) {
    saida.push(segmentos(celula));
    for (let i = 1; i < celula.colSpan; i++) saida.push([]);
  }
  return saida;
}

const numerico = (c: Celula) => c !== null && typeof c !== "string";

export function lerTabela(tabela: HTMLTableElement, titulo: string): Aba {
  const cabecalhos = tabela.tHead ? Array.from(tabela.tHead.rows) : [];
  const ultima = cabecalhos[cabecalhos.length - 1];
  const titulos = ultima ? expandir(ultima).map((s) => s.join(" ").replace(SETAS, " ").trim()) : [];
  const corpo = [...Array.from(tabela.tBodies).flatMap((b) => Array.from(b.rows)), ...(tabela.tFoot ? Array.from(tabela.tFoot.rows) : [])];
  // Linha única com colspan total = mensagem ("Nenhum registro"), não dado.
  const linhas = corpo.filter((l) => !(l.cells.length === 1 && l.cells[0].colSpan > 1)).map(expandir);
  const largura = Math.max(titulos.length, ...linhas.map((l) => l.length));

  const colunas: string[] = [];
  const saida: Celula[][] = linhas.map(() => []);
  for (let i = 0; i < largura; i++) {
    const celulas = linhas.map((l) => (l[i] ?? []).map(converter));
    const titulo = titulos[i] ?? "";
    // Sem título e sem conteúdo: coluna de ações (editar/excluir).
    if (!titulo && celulas.every((c) => c.every((v) => v === null))) continue;
    const partes = Math.max(1, ...celulas.map((c) => c.length));
    // Célula com vários valores numéricos (ex.: "R$ 30,00" e "-5,00%") vira subcolunas; texto é unido.
    if (partes > 1 && celulas.every((c) => c.every((v) => v === null || numerico(v)))) {
      for (let k = 0; k < partes; k++) {
        const exemplo = celulas.find((c) => c[k] && numerico(c[k]))?.[k];
        const percentual = k > 0 && exemplo && typeof exemplo === "object" && "f" in exemplo && exemplo.f === "percentual";
        colunas.push(k === 0 ? titulo : percentual ? `${titulo} %` : `${titulo} (${k + 1})`);
        celulas.forEach((c, j) => saida[j].push(c[k] ?? null));
      }
    } else {
      colunas.push(titulo);
      celulas.forEach((c, j) =>
        saida[j].push(c.length <= 1 ? (c[0] ?? null) : converter((linhas[j][i] ?? []).join(" · "))),
      );
    }
  }
  return { titulo, colunas, linhas: saida };
}

function visivel(e: HTMLElement): boolean {
  return e.getClientRects().length > 0;
}

/** Tabelas visíveis dentro do container, com o título do cabeçalho (h1–h3/caption) mais próximo acima. */
export function lerTabelas(container: HTMLElement): Aba[] {
  const abas: Aba[] = [];
  let titulo = "";
  for (const el of Array.from(container.querySelectorAll<HTMLElement>("h1, h2, h3, table"))) {
    if (el.tagName !== "TABLE") {
      titulo = (el.textContent ?? "").trim();
      continue;
    }
    const tabela = el as HTMLTableElement;
    if (!visivel(tabela) || tabela.closest("[data-exportar='ignorar']")) continue;
    const aba = lerTabela(tabela, tabela.caption?.textContent?.trim() || titulo || `Tabela ${abas.length + 1}`);
    if (aba.colunas.length) abas.push(aba);
  }
  return abas;
}

export async function baixar(formato: Formato, nome: string, abas: Aba[]): Promise<void> {
  const resposta = await fetch(`/api/exportacao/${formato}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ nome, abas }),
  });
  if (!resposta.ok) throw new Error(`Falha ao exportar (${resposta.status})`);
  const disposicao = resposta.headers.get("Content-Disposition") ?? "";
  const arquivo = decodeURIComponent(/filename\*=UTF-8''([^;]+)/.exec(disposicao)?.[1] ?? `${nome}.${formato}`);
  const url = URL.createObjectURL(await resposta.blob());
  const link = document.createElement("a");
  link.href = url;
  link.download = arquivo;
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export function nomeArquivo(titulo: string): string {
  const limpo = titulo
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^\w\- ]+/g, " ")
    .trim()
    .replace(/\s+/g, "-")
    .toLowerCase();
  return (limpo || "investhub").slice(0, 60);
}
