import { useState } from "react";
import { moeda, percentual } from "../formato";
import type { Posicao } from "../tipos";
import { Dica, useDica } from "./Dica";

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
  const [expandido, setExpandido] = useState(false);
  const [foco, setFoco] = useState<[string, number] | null>(null);
  const dica = useDica();
  const ocultos = itens.length - LIMITE;
  const visiveis = expandido || ocultos <= 0 ? itens : itens.slice(0, LIMITE);
  const resto = expandido ? 0 : itens.slice(LIMITE).reduce((s, [, v]) => s + v, 0);
  const maior = Math.max(...visiveis.map(([, v]) => v), resto, 1);
  const sair = () => {
    setFoco(null);
    dica.esconder();
  };

  const linha = (rotulo: string, valor: number, aoClicar?: () => void, rotuloDica = rotulo) => (
    <div
      key={rotulo}
      className={aoClicar ? "barra-linha clicavel" : "barra-linha"}
      onMouseMove={(e) => {
        setFoco([rotuloDica, valor]);
        dica.mover(e);
      }}
      onMouseLeave={sair}
      onClick={aoClicar}
      onKeyDown={
        aoClicar
          ? (e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                aoClicar();
              }
            }
          : undefined
      }
      role={aoClicar ? "button" : undefined}
      tabIndex={aoClicar ? 0 : undefined}
      aria-expanded={aoClicar ? expandido : undefined}
    >
      <div className="barra-rotulo">{rotulo}</div>
      <div className="barra-trilho">
        <div className="barra" style={{ width: `${(valor / maior) * 100}%` }} />
      </div>
      <div className="barra-valor">{percentual(total ? valor / total : null)}</div>
    </div>
  );

  return (
    <div className="card exposicao">
      <span>{titulo}</span>
      {visiveis.map(([rotulo, valor]) => linha(rotulo, valor))}
      {resto > 0 && linha(`Outros (${ocultos}) ▸`, resto, () => setExpandido(true), `Outros (${ocultos})`)}
      {expandido && ocultos > 0 && (
        <button type="button" className="link exposicao-recolher" onClick={() => setExpandido(false)}>
          Mostrar menos ▴
        </button>
      )}
      {foco && (
        <Dica posicao={dica.posicao}>
          <div className="dica-titulo">{foco[0]}</div>
          <strong>{moeda(foco[1])}</strong> · {percentual(total ? foco[1] / total : null)}
        </Dica>
      )}
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
