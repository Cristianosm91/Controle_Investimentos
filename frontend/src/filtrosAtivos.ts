import type { AtivoFiltro } from "./tipos";
import type { OpcaoFiltro } from "./components/FiltroMultisselecao";

export const OPCOES_MERCADO: OpcaoFiltro[] = [
  { valor: "BRASIL", rotulo: "Brasil" },
  { valor: "EUA", rotulo: "EUA" },
  { valor: "CRIPTO", rotulo: "Criptomoedas" },
];

export function valorFiltro(valores: string[] | null): string | undefined {
  if (valores === null) return undefined;
  return valores.length ? valores.join(",") : "__NENHUM__";
}

export function filtrarAtivos(
  ativos: AtivoFiltro[],
  mercados: string[] | null,
  classes: string[] | null,
): AtivoFiltro[] {
  return ativos.filter(
    (ativo) =>
      (mercados === null || mercados.includes(ativo.mercado_tipo ?? "")) &&
      (classes === null || classes.includes(ativo.classe)),
  );
}

export function opcoesAtivos(ativos: AtivoFiltro[]): OpcaoFiltro[] {
  return ativos.map((ativo) => ({
    valor: String(ativo.id),
    rotulo: ativo.ticker,
    busca: ativo.nome ?? "",
  }));
}

export function opcoesClasses(ativos: AtivoFiltro[]): OpcaoFiltro[] {
  return [...new Set(ativos.map((ativo) => ativo.classe))]
    .sort()
    .map((classe) => ({
      valor: classe,
      rotulo: classe.charAt(0) + classe.slice(1).toLowerCase(),
    }));
}
