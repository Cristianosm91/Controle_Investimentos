import { useState } from "react";
import { moeda, percentual } from "../formato";
import { explicarLetras } from "../metodologias";
import type { MetodologiaAlocacao, Posicao } from "../tipos";
import { Dica, useDica } from "./Dica";
import { AjudaIndicador } from "./AjudaIndicador";

export type Dimensao = "classe" | "setor" | "ticker" | "estrategia" | "book" | "carteira" | "moeda";

export const ROTULO_DIMENSAO: Record<Dimensao, string> = {
  classe: "Classe",
  setor: "Setor",
  ticker: "Ativo",
  estrategia: "Estratégia",
  book: "Book",
  carteira: "Carteira",
  moeda: "Moeda",
};

const SEM_VALOR: Record<Exclude<Dimensao, "classe" | "ticker" | "moeda">, string> = {
  setor: "Sem setor",
  estrategia: "Sem estratégia",
  book: "Sem book",
  carteira: "Sem carteira",
};

export const chaveGrupo = (p: Posicao, d: Dimensao): string =>
  d === "classe" || d === "ticker" || d === "moeda" ? p[d] : p[d] ?? SEM_VALOR[d];

/** Valor de mercado; sem cotação, usa o custo para não sumir da exposição. */
export const valorExposicao = (p: Posicao) => p.valor_mercado ?? p.custo;

export function somarPor(posicoes: Posicao[], d: Dimensao): [string, number][] {
  const mapa = new Map<string, number>();
  for (const p of posicoes) mapa.set(chaveGrupo(p, d), (mapa.get(chaveGrupo(p, d)) ?? 0) + valorExposicao(p));
  return [...mapa].sort((a, b) => b[1] - a[1]);
}

const LIMITE = 10;

function Barras({ titulo, itens, total, ajuda, metas }: {
  titulo: string;
  itens: [string, number][];
  total: number;
  ajuda?: string;
  metas?: Map<string, number | null>;
}) {
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
      className={`barra-linha${metas ? " com-meta" : ""}${aoClicar ? " clicavel" : ""}`}
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
        <div className="barra" style={{ width: `${(Math.max(valor, 0) / maior) * 100}%` }} />
      </div>
      <div className="barra-valor"><span className="visualmente-oculto">Atual: </span>{percentual(total ? valor / total : null)}</div>
      {metas && <div className="barra-valor"><span className="visualmente-oculto">Meta: </span>{percentual(metas.get(rotulo) ?? null)}</div>}
    </div>
  );

  return (
    <div className="card exposicao">
      <span>{titulo} <AjudaIndicador titulo={titulo} texto={ajuda ?? (titulo === "Exposição por corretora"
        ? "Valor atribuído a cada corretora dividido pelo total atribuído às corretoras exibidas."
        : "Soma do valor de mercado das posições do grupo dividida pelo total das posições. Quando falta cotação, usa o custo da posição.")} /></span>
      {metas && (
        <div className="barra-linha com-meta barra-cabecalho" aria-hidden="true">
          <span>Categoria</span><span /><span className="barra-valor">Atual</span><span className="barra-valor">Meta</span>
        </div>
      )}
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

export function Exposicao({ posicoes, corretoras, metodologias }: {
  posicoes: Posicao[];
  corretoras?: [string, number][];
  metodologias?: MetodologiaAlocacao[];
}) {
  const total = posicoes.reduce((s, p) => s + valorExposicao(p), 0);
  return (
    <div className="exposicoes">
      {(["book", "classe", "setor", "moeda", "ticker"] as Dimensao[]).map((d) => (
        <Barras key={d} titulo={`Exposição por ${ROTULO_DIMENSAO[d].toLowerCase()}`} itens={somarPor(posicoes, d)} total={total} />
      ))}
      {corretoras && corretoras.length > 0 && (
        <Barras titulo="Exposição por corretora" itens={corretoras} total={corretoras.reduce((s, [, v]) => s + v, 0)} />
      )}
      {metodologias?.map((metodologia) => (
        <Barras
          key={metodologia.nome}
          titulo={`Exposição ${metodologia.nome}`}
          itens={metodologia.categorias.map((categoria) => [categoria.nome, categoria.valor_atual])}
          total={metodologia.total_atual}
          metas={new Map(metodologia.categorias.map((categoria) => [categoria.nome, categoria.peso_alvo ?? null]))}
          ajuda={`${explicarLetras(metodologia.nome)}Atual é a proporção da categoria na carteira; meta é o percentual definido para o investidor. Usa o custo quando falta cotação e inclui o saldo de caixa conforme a configuração do Portfólio, exceto ao filtrar classes.`}
        />
      ))}
    </div>
  );
}
