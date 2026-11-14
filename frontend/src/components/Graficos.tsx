import { useEffect, useRef, useState, type MouseEvent } from "react";
import { data, mesAno, moeda, moedaCompacta } from "../formato";
import { Dica, useDica } from "./Dica";

export interface SerieGrafico {
  nome: string;
  cor: string;
  valores: (number | null)[];
  tracejada?: boolean;
}

const LARGURA_INICIAL = 800;

/** Na dica, o valor exato; o formato compacto é só para caber no eixo. */
const formatoDica = (formatar: (v: number) => string) => (formatar === moedaCompacta ? (v: number) => moeda(v) : formatar);
const MARGEM = { topo: 12, direita: 30, base: 26, esquerda: 70 };

function useLarguraGrafico(ativo: boolean) {
  const ref = useRef<HTMLDivElement>(null);
  const [largura, setLargura] = useState(LARGURA_INICIAL);

  useEffect(() => {
    if (!ativo) return;
    const elemento = ref.current;
    if (!elemento) return;

    const atualizar = () => {
      const novaLargura = Math.round(elemento.clientWidth);
      if (novaLargura > 0) setLargura(novaLargura);
    };

    atualizar();
    if (typeof ResizeObserver === "undefined") {
      window.addEventListener("resize", atualizar);
      return () => window.removeEventListener("resize", atualizar);
    }

    const observador = new ResizeObserver(atualizar);
    observador.observe(elemento);
    return () => observador.disconnect();
  }, [ativo]);

  return { ref, largura };
}

function passoRedondo(bruto: number): number {
  const potencia = 10 ** Math.floor(Math.log10(bruto));
  const fracao = bruto / potencia;
  return (fracao >= Math.sqrt(50) ? 10 : fracao >= Math.sqrt(10) ? 5 : fracao >= Math.sqrt(2) ? 2 : 1) * potencia;
}

/** Eixo com marcas em valores redondos; não cruza o zero quando todos os dados estão do mesmo lado. */
function escala(minDados: number, maxDados: number, alvoMarcas = 5) {
  let min = minDados;
  let max = maxDados;
  if (min === max) {
    const folga = Math.abs(min) * 0.1 || 1;
    min = min >= 0 ? Math.max(0, min - folga) : min - folga;
    max = max <= 0 ? Math.min(0, max + folga) : max + folga;
  }
  const passo = passoRedondo((max - min) / (alvoMarcas - 1));
  const inicio = Math.floor(min / passo) * passo;
  const fim = Math.ceil(max / passo) * passo;
  const marcas: number[] = [];
  const total = Math.round((fim - inicio) / passo);
  for (let i = 0; i <= total; i++) {
    const v = inicio + i * passo;
    marcas.push(Math.abs(v) < passo / 1e6 ? 0 : v);
  }
  return { min: inicio, max: fim, marcas };
}

/** Índices dos rótulos do eixo X, no máximo ~8 para não sobrepor. */
function rotulosX(total: number): number[] {
  const passo = Math.max(1, Math.ceil(total / 8));
  const lista = [];
  for (let i = 0; i < total; i += passo) lista.push(i);
  if (lista[lista.length - 1] !== total - 1) lista.push(total - 1);
  return lista;
}

/** Datas mensais (uma por mês) aparecem como "mar./2024"; diárias, como dd/mm/aaaa. */
function formatoDatas(datas: string[]): (iso: string) => string {
  const meses = new Set(datas.map((d) => d.slice(0, 7)));
  return meses.size === datas.length ? mesAno : data;
}

function resumoGrafico(titulo: string | undefined, datas: string[], series: { nome: string }[]): string {
  const rotulo = formatoDatas(datas);
  const periodo =
    datas.length > 1 ? `de ${rotulo(datas[0])} a ${rotulo(datas[datas.length - 1])}` : `em ${rotulo(datas[0])}`;
  const nomes = series.map((s) => s.nome).filter(Boolean).join(", ");
  return `${titulo ?? "Gráfico"}${nomes ? ` — ${nomes}` : ""}, ${periodo}. Valores em "Ver dados do gráfico".`;
}

/** Alternativa textual ao gráfico: a mesma série em tabela, acessível por teclado e leitor de tela. */
function DadosGrafico({
  titulo,
  datas,
  series,
  formatar,
}: {
  titulo?: string;
  datas: string[];
  series: { nome: string; valores: (number | null)[] }[];
  formatar: (v: number) => string;
}) {
  const [aberto, setAberto] = useState(false);
  const rotulo = formatoDatas(datas);
  const valor = formatoDica(formatar);
  return (
    <details className="grafico-dados nao-imprimir" data-exportar="ignorar" onToggle={(e) => setAberto(e.currentTarget.open)}>
      <summary>Ver dados do gráfico</summary>
      {aberto && (
        <div className="grafico-dados-rolagem" tabIndex={0} role="region" aria-label={`Dados: ${titulo ?? "gráfico"}`}>
          <table className="tabela">
            {titulo && <caption className="visualmente-oculto">{titulo}</caption>}
            <thead>
              <tr>
                <th scope="col">Data</th>
                {series.map((s) => (
                  <th key={s.nome} scope="col" className="num">
                    {s.nome}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {datas.map((d, i) => (
                <tr key={`${d}-${i}`}>
                  <th scope="row">{rotulo(d)}</th>
                  {series.map((s) => (
                    <td key={s.nome} className="num">
                      {s.valores[i] === null || s.valores[i] === undefined ? "—" : valor(s.valores[i]!)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </details>
  );
}

interface PropsLinhas {
  datas: string[];
  series: SerieGrafico[];
  formatar: (v: number) => string;
  altura?: number;
  zero?: boolean;
  /** Nome acessível do gráfico (ex.: o título do painel). */
  titulo?: string;
}

export function GraficoLinhas({ datas, series, formatar, altura = 210, zero = false, titulo }: PropsLinhas) {
  const [foco, setFoco] = useState<number | null>(null);
  const dica = useDica();
  const todos = series.flatMap((s) => s.valores.filter((v): v is number => v !== null));
  const { ref, largura } = useLarguraGrafico(Boolean(datas.length && todos.length));
  if (!datas.length || !todos.length) return <p className="sutil">Sem dados para o período.</p>;

  const { min, max, marcas } = escala(Math.min(...todos, ...(zero ? [0] : [])), Math.max(...todos, ...(zero ? [0] : [])));
  const w = largura - MARGEM.esquerda - MARGEM.direita;
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
    const px = ((e.clientX - caixa.left) / caixa.width) * largura;
    const i = Math.round(((px - MARGEM.esquerda) / w) * (datas.length - 1));
    setFoco(Math.min(datas.length - 1, Math.max(0, i)));
    dica.mover(e);
  };
  const sair = () => {
    setFoco(null);
    dica.esconder();
  };

  return (
    <div className="grafico" ref={ref}>
      <svg
        viewBox={`0 0 ${largura} ${altura}`}
        onMouseMove={mover}
        onMouseLeave={sair}
        role="img"
        aria-label={resumoGrafico(titulo, datas, series)}
      >
        {marcas.map((v) => (
          <g key={v}>
            <line x1={MARGEM.esquerda} x2={largura - MARGEM.direita} y1={y(v)} y2={y(v)} className="grade" />
            <text x={MARGEM.esquerda - 6} y={y(v) + 4} textAnchor="end" className="eixo">
              {formatar(v)}
            </text>
          </g>
        ))}
        {zero && min < 0 && max > 0 && (
          <line x1={MARGEM.esquerda} x2={largura - MARGEM.direita} y1={y(0)} y2={y(0)} className="linha-zero" />
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
            strokeWidth={1.6}
            strokeDasharray={s.tracejada ? "4 3" : undefined}
          />
        ))}
        {foco !== null && (
          <>
            <line x1={x(foco)} x2={x(foco)} y1={MARGEM.topo} y2={MARGEM.topo + h} className="cursor" />
            {series.map((s) =>
              s.valores[foco] === null ? null : (
                <circle key={s.nome} cx={x(foco)} cy={y(s.valores[foco]!)} r={3} fill={s.cor} />
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
      <DadosGrafico titulo={titulo} datas={datas} series={series} formatar={formatar} />
      {foco !== null && (
        <Dica posicao={dica.posicao}>
          <div className="dica-titulo">{mesAno(datas[foco])}</div>
          {series.map((s) =>
            s.valores[foco] === null ? null : (
              <div key={s.nome}>
                <span className="bolinha" style={{ background: s.cor }} /> {s.nome}: <strong>{formatoDica(formatar)(s.valores[foco]!)}</strong>
              </div>
            ),
          )}
        </Dica>
      )}
    </div>
  );
}

interface PropsBarras {
  datas: string[];
  valores: number[];
  formatar: (v: number) => string;
  cor?: string;
  altura?: number;
  /** Nome acessível do gráfico (ex.: o título do painel). */
  titulo?: string;
  /** Nome da série na tabela de dados alternativa. */
  rotuloValor?: string;
}

export function GraficoBarras({
  datas,
  valores,
  formatar,
  cor = "var(--primaria)",
  altura = 170,
  titulo,
  rotuloValor = "Valor",
}: PropsBarras) {
  const [foco, setFoco] = useState<number | null>(null);
  const dica = useDica();
  const { ref, largura: larguraTotal } = useLarguraGrafico(Boolean(valores.length));
  if (!valores.length) return <p className="sutil">Sem dados para o período.</p>;
  const { min, max, marcas } = escala(Math.min(0, ...valores), Math.max(0, ...valores), 4);
  const w = larguraTotal - MARGEM.esquerda - MARGEM.direita;
  const h = altura - MARGEM.topo - MARGEM.base;
  const largura = w / valores.length;
  const y = (v: number) => MARGEM.topo + h - ((v - min) / (max - min)) * h;

  // Toda a coluna da barra responde ao mouse, não só o retângulo (barras pequenas ficariam difíceis de acertar).
  const mover = (e: MouseEvent<SVGSVGElement>) => {
    const caixa = e.currentTarget.getBoundingClientRect();
    const px = ((e.clientX - caixa.left) / caixa.width) * larguraTotal;
    const i = Math.floor((px - MARGEM.esquerda) / largura);
    if (i < 0 || i >= valores.length) {
      setFoco(null);
      dica.esconder();
      return;
    }
    setFoco(i);
    dica.mover(e);
  };
  const sair = () => {
    setFoco(null);
    dica.esconder();
  };

  return (
    <div className="grafico" ref={ref}>
      <svg
        viewBox={`0 0 ${larguraTotal} ${altura}`}
        onMouseMove={mover}
        onMouseLeave={sair}
        role="img"
        aria-label={resumoGrafico(titulo, datas, [])}
      >
        {marcas.map((v) => (
          <g key={v}>
            <line x1={MARGEM.esquerda} x2={larguraTotal - MARGEM.direita} y1={y(v)} y2={y(v)} className="grade" />
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
          />
        ))}
        {rotulosX(datas.length).map((i) => (
          <text key={i} x={MARGEM.esquerda + (i + 0.5) * largura} y={altura - 6} textAnchor="middle" className="eixo">
            {mesAno(datas[i])}
          </text>
        ))}
      </svg>
      <DadosGrafico titulo={titulo} datas={datas} series={[{ nome: rotuloValor, valores }]} formatar={formatar} />
      {foco !== null && (
        <Dica posicao={dica.posicao}>
          <div className="dica-titulo">{mesAno(datas[foco])}</div>
          <strong>{formatoDica(formatar)(valores[foco])}</strong>
        </Dica>
      )}
    </div>
  );
}
