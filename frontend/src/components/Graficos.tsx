import { useState, type MouseEvent } from "react";
import { mesAno } from "../formato";

export interface SerieGrafico {
  nome: string;
  cor: string;
  valores: (number | null)[];
  tracejada?: boolean;
}

const LARGURA = 800;
const MARGEM = { topo: 12, direita: 30, base: 26, esquerda: 70 };

function escala(min: number, max: number) {
  if (min === max) return { min: min - 1, max: max + 1 };
  const folga = (max - min) * 0.06;
  return { min: min - folga, max: max + folga };
}

function marcas(min: number, max: number, n = 5): number[] {
  const passo = (max - min) / (n - 1);
  return Array.from({ length: n }, (_, i) => min + passo * i);
}

/** Índices dos rótulos do eixo X, no máximo ~8 para não sobrepor. */
function rotulosX(total: number): number[] {
  const passo = Math.max(1, Math.ceil(total / 8));
  const lista = [];
  for (let i = 0; i < total; i += passo) lista.push(i);
  if (lista[lista.length - 1] !== total - 1) lista.push(total - 1);
  return lista;
}

interface PropsLinhas {
  datas: string[];
  series: SerieGrafico[];
  formatar: (v: number) => string;
  altura?: number;
  zero?: boolean;
}

export function GraficoLinhas({ datas, series, formatar, altura = 260, zero = false }: PropsLinhas) {
  const [foco, setFoco] = useState<number | null>(null);
  const todos = series.flatMap((s) => s.valores.filter((v): v is number => v !== null));
  if (!datas.length || !todos.length) return <p className="sutil">Sem dados para o período.</p>;

  const { min, max } = escala(Math.min(...todos, ...(zero ? [0] : [])), Math.max(...todos, ...(zero ? [0] : [])));
  const w = LARGURA - MARGEM.esquerda - MARGEM.direita;
  const h = altura - MARGEM.topo - MARGEM.base;
  const x = (i: number) => MARGEM.esquerda + (datas.length === 1 ? w / 2 : (i / (datas.length - 1)) * w);
  const y = (v: number) => MARGEM.topo + h - ((v - min) / (max - min)) * h;

  const caminho = (valores: (number | null)[]) => {
    let d = "";
    let aberto = false;
    valores.forEach((v, i) => {
      if (v === null) {
        aberto = false;
        return;
      }
      d += `${aberto ? "L" : "M"}${x(i).toFixed(1)},${y(v).toFixed(1)}`;
      aberto = true;
    });
    return d;
  };

  const mover = (e: MouseEvent<SVGSVGElement>) => {
    const caixa = e.currentTarget.getBoundingClientRect();
    const px = ((e.clientX - caixa.left) / caixa.width) * LARGURA;
    const i = Math.round(((px - MARGEM.esquerda) / w) * (datas.length - 1));
    setFoco(Math.min(datas.length - 1, Math.max(0, i)));
  };

  return (
    <div className="grafico">
      <svg viewBox={`0 0 ${LARGURA} ${altura}`} onMouseMove={mover} onMouseLeave={() => setFoco(null)} role="img">
        {marcas(min, max).map((v) => (
          <g key={v}>
            <line x1={MARGEM.esquerda} x2={LARGURA - MARGEM.direita} y1={y(v)} y2={y(v)} className="grade" />
            <text x={MARGEM.esquerda - 6} y={y(v) + 4} textAnchor="end" className="eixo">
              {formatar(v)}
            </text>
          </g>
        ))}
        {zero && min < 0 && max > 0 && (
          <line x1={MARGEM.esquerda} x2={LARGURA - MARGEM.direita} y1={y(0)} y2={y(0)} className="linha-zero" />
        )}
        {rotulosX(datas.length).map((i) => (
          <text key={i} x={x(i)} y={altura - 6} textAnchor="middle" className="eixo">
            {mesAno(datas[i])}
          </text>
        ))}
        {series.map((s) => (
          <path
            key={s.nome}
            d={caminho(s.valores)}
            fill="none"
            stroke={s.cor}
            strokeWidth={2}
            strokeDasharray={s.tracejada ? "5 4" : undefined}
          />
        ))}
        {foco !== null && (
          <>
            <line x1={x(foco)} x2={x(foco)} y1={MARGEM.topo} y2={MARGEM.topo + h} className="cursor" />
            {series.map((s) =>
              s.valores[foco] === null ? null : (
                <circle key={s.nome} cx={x(foco)} cy={y(s.valores[foco]!)} r={3.5} fill={s.cor} />
              ),
            )}
          </>
        )}
      </svg>
      <div className="legenda">
        {series.map((s) => (
          <span key={s.nome}>
            <span className="bolinha" style={{ background: s.cor }} /> {s.nome}
            {foco !== null && s.valores[foco] !== null && <strong> {formatar(s.valores[foco]!)}</strong>}
          </span>
        ))}
        {foco !== null && <span className="sutil">{mesAno(datas[foco])}</span>}
      </div>
    </div>
  );
}

interface PropsBarras {
  datas: string[];
  valores: number[];
  formatar: (v: number) => string;
  cor?: string;
  altura?: number;
}

export function GraficoBarras({ datas, valores, formatar, cor = "var(--primaria)", altura = 200 }: PropsBarras) {
  const [foco, setFoco] = useState<number | null>(null);
  if (!valores.length) return <p className="sutil">Sem dados para o período.</p>;
  const { min, max } = escala(Math.min(0, ...valores), Math.max(0, ...valores));
  const w = LARGURA - MARGEM.esquerda - MARGEM.direita;
  const h = altura - MARGEM.topo - MARGEM.base;
  const largura = w / valores.length;
  const y = (v: number) => MARGEM.topo + h - ((v - min) / (max - min)) * h;

  return (
    <div className="grafico">
      <svg viewBox={`0 0 ${LARGURA} ${altura}`} onMouseLeave={() => setFoco(null)} role="img">
        {marcas(min, max, 4).map((v) => (
          <g key={v}>
            <line x1={MARGEM.esquerda} x2={LARGURA - MARGEM.direita} y1={y(v)} y2={y(v)} className="grade" />
            <text x={MARGEM.esquerda - 6} y={y(v) + 4} textAnchor="end" className="eixo">
              {formatar(v)}
            </text>
          </g>
        ))}
        {valores.map((v, i) => (
          <rect
            key={datas[i]}
            x={MARGEM.esquerda + i * largura + largura * 0.15}
            width={largura * 0.7}
            y={Math.min(y(v), y(0))}
            height={Math.max(1, Math.abs(y(v) - y(0)))}
            fill={v < 0 ? "var(--negativo)" : cor}
            opacity={foco === null || foco === i ? 1 : 0.5}
            onMouseEnter={() => setFoco(i)}
          />
        ))}
        {rotulosX(datas.length).map((i) => (
          <text key={i} x={MARGEM.esquerda + (i + 0.5) * largura} y={altura - 6} textAnchor="middle" className="eixo">
            {mesAno(datas[i])}
          </text>
        ))}
      </svg>
      <div className="legenda">
        {foco !== null ? (
          <span>
            {mesAno(datas[foco])}: <strong>{formatar(valores[foco])}</strong>
          </span>
        ) : (
          <span className="sutil">Passe o mouse sobre as barras</span>
        )}
      </div>
    </div>
  );
}
