import { moeda, percentual } from "../formato";
import type { Posicao } from "../tipos";

export type Dimensao = "classe" | "setor" | "ticker" | "estrategia" | "book" | "carteira";

export const ROTULO_DIMENSAO: Record<Dimensao, string> = {
  classe: "Classe",
  setor: "Setor",
  ticker: "Ativo",
  estrategia: "Estratégia",
  book: "Book",
  carteira: "Carteira",
};

const SEM_VALOR: Record<Exclude<Dimensao, "classe" | "ticker">, string> = {
  setor: "Sem setor",
  estrategia: "Sem estratégia",
  book: "Sem book",
  carteira: "Sem carteira",
};

export const chaveGrupo = (p: Posicao, d: Dimensao): string =>
  d === "classe" || d === "ticker" ? p[d] : p[d] ?? SEM_VALOR[d];

/** Valor de mercado; sem cotação, usa o custo para não sumir da exposição. */
export const valorExposicao = (p: Posicao) => p.valor_mercado ?? p.custo;

export function somarPor(posicoes: Posicao[], d: Dimensao): [string, number][] {
  const mapa = new Map<string, number>();
  for (const p of posicoes) mapa.set(chaveGrupo(p, d), (mapa.get(chaveGrupo(p, d)) ?? 0) + valorExposicao(p));
  return [...mapa].sort((a, b) => b[1] - a[1]);
}

const LIMITE = 10;

function Barras({ titulo, itens, total }: { titulo: string; itens: [string, number][]; total: number }) {
  const visiveis = itens.slice(0, LIMITE);
  const resto = itens.slice(LIMITE).reduce((s, [, v]) => s + v, 0);
  if (resto > 0) visiveis.push([`Outros (${itens.length - LIMITE})`, resto]);
  const maior = Math.max(...visiveis.map(([, v]) => v), 1);
  return (
    <div className="card exposicao">
      <span>{titulo}</span>
      {visiveis.map(([rotulo, valor]) => (
        <div key={rotulo} className="barra-linha" title={moeda(valor)}>
          <div className="barra-rotulo">{rotulo}</div>
          <div className="barra-trilho">
            <div className="barra" style={{ width: `${(valor / maior) * 100}%` }} />
          </div>
          <div className="barra-valor">{percentual(total ? valor / total : null)}</div>
        </div>
      ))}
    </div>
  );
}

export function Exposicao({ posicoes }: { posicoes: Posicao[] }) {
  const total = posicoes.reduce((s, p) => s + valorExposicao(p), 0);
  return (
    <div className="exposicoes">
      {(["book", "classe", "setor", "ticker"] as Dimensao[]).map((d) => (
        <Barras key={d} titulo={`Exposição por ${ROTULO_DIMENSAO[d].toLowerCase()}`} itens={somarPor(posicoes, d)} total={total} />
      ))}
    </div>
  );
}
