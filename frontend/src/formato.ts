const brl = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
const pct = new Intl.NumberFormat("pt-BR", { style: "percent", minimumFractionDigits: 2, maximumFractionDigits: 2 });

export function moeda(valor: number | null | undefined, codigo = "BRL"): string {
  if (valor === null || valor === undefined) return "—";
  if (codigo === "BRL") return brl.format(valor);
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency: codigo }).format(valor);
}

export function numero(valor: number | null | undefined, casas = 2): string {
  if (valor === null || valor === undefined) return "—";
  return valor.toLocaleString("pt-BR", { minimumFractionDigits: 0, maximumFractionDigits: casas });
}

export function percentual(valor: number | null | undefined): string {
  if (valor === null || valor === undefined || !Number.isFinite(valor)) return "—";
  return pct.format(valor);
}

/** "2024-03-05" -> "05/03/2024" sem passar por Date (evita deslocamento de fuso). */
export function data(iso: string | null | undefined): string {
  if (!iso) return "—";
  const [a, m, d] = iso.slice(0, 10).split("-");
  return `${d}/${m}/${a}`;
}

export function classeSinal(valor: number | null | undefined): string {
  if (!valor) return "";
  return valor > 0 ? "positivo" : "negativo";
}
