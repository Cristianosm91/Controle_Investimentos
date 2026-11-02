import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useRef, useState } from "react";
import { api, query } from "../api";
import { invalidarDerivados, useAtivos } from "../cadastros";
import { GraficoBarras, GraficoLinhas } from "../components/Graficos";
import { classeSinal, mesAno, MESES, moeda, moedaCompacta, percentual } from "../formato";
import { useInvestidor } from "../InvestidorContext";
import { BENCHMARKS, CORES_BENCHMARK, NOMES_BENCHMARK } from "../referencias";
import type { Benchmark, MesRentabilidade, Tarefa } from "../tipos";

const CARGA_HISTORICA = ["cotahist_historico", "historico_complementar"];

const PERIODOS = [
  { id: "12m", rotulo: "12 meses" },
  { id: "ano", rotulo: "Ano atual" },
  { id: "36m", rotulo: "36 meses" },
  { id: "tudo", rotulo: "Desde o início" },
] as const;
type Periodo = (typeof PERIODOS)[number]["id"];

function inicioDoPeriodo(p: Periodo): string | undefined {
  const hoje = new Date();
  if (p === "tudo") return undefined;
  if (p === "ano") return `${hoje.getFullYear()}-01-01`;
  const meses = p === "12m" ? 11 : 35;
  const d = new Date(hoje.getFullYear(), hoje.getMonth() - meses, 1);
  return d.toLocaleDateString("sv-SE");
}

/** Acumula variações mensais (para o ano do mapa de calor). */
const compor = (vs: (number | null)[]) =>
  vs.some((v) => v !== null) ? vs.reduce<number>((acc, v) => acc * (1 + (v ?? 0)), 1) - 1 : null;

function MapaDeCalor({ meses }: { meses: MesRentabilidade[] }) {
  const anos = useMemo(() => {
    const mapa = new Map<number, (MesRentabilidade | null)[]>();
    for (const m of meses) {
      const [a, mm] = m.data.split("-").map(Number);
      if (!mapa.has(a)) mapa.set(a, Array(12).fill(null));
      mapa.get(a)![mm - 1] = m;
    }
    return [...mapa].sort((a, b) => b[0] - a[0]);
  }, [meses]);

  const cor = (v: number | null) => {
    if (v === null) return undefined;
    const intensidade = Math.min(1, Math.abs(v) / 0.08);
    return v >= 0 ? `rgb(21 128 61 / ${0.08 + intensidade * 0.45})` : `rgb(185 28 28 / ${0.08 + intensidade * 0.45})`;
  };

  return (
    <div className="tabela-container">
      <table className="tabela calor">
        <thead>
          <tr>
            <th>Ano</th>
            {MESES.map((m) => (
              <th key={m} className="num">
                {m}
              </th>
            ))}
            <th className="num">Ano</th>
            <th className="num">CDI</th>
            <th className="num">IBOV</th>
          </tr>
        </thead>
        <tbody>
          {anos.map(([ano, lista]) => {
            const twrAno = compor(lista.map((m) => m?.twr ?? null));
            return (
              <tr key={ano}>
                <td>
                  <strong>{ano}</strong>
                </td>
                {lista.map((m, i) => (
                  <td key={i} className="num" style={{ background: cor(m?.twr ?? null) }}>
                    {m ? percentual(m.twr) : ""}
                  </td>
                ))}
                <td className="num" style={{ background: cor(twrAno) }}>
                  <strong>{percentual(twrAno)}</strong>
                </td>
                <td className="num sutil">{percentual(compor(lista.map((m) => m?.cdi ?? null)))}</td>
                <td className="num sutil">{percentual(compor(lista.map((m) => m?.ibov ?? null)))}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function AvisoSemHistorico({ meses }: { meses: number }) {
  const cliente = useQueryClient();
  const { data: tarefas = [] } = useQuery({
    queryKey: ["atualizacoes"],
    queryFn: () => api.get<Tarefa[]>("/atualizacoes"),
    refetchInterval: (q) => (q.state.data?.some((t) => t.em_execucao) ? 3000 : 60_000),
  });
  const carregando = tarefas.some((t) => CARGA_HISTORICA.includes(t.nome) && t.em_execucao);
  const falha = tarefas.find((t) => CARGA_HISTORICA.includes(t.nome) && t.sucesso === false);
  const disparar = useMutation({
    mutationFn: () => api.post("/atualizacoes/carga-historica"),
    onSettled: () => cliente.invalidateQueries({ queryKey: ["atualizacoes"] }),
  });

  // Ao terminar a carga, recalcula a rentabilidade com os preços históricos.
  const estavaCarregando = useRef(false);
  useEffect(() => {
    if (estavaCarregando.current && !carregando) invalidarDerivados(cliente);
    estavaCarregando.current = carregando;
  }, [carregando, cliente]);

  return (
    <div className="aviso titulo-linha">
      <span>
        {carregando ? (
          <>Carregando o histórico de cotações (B3, exterior e câmbio)… pode levar alguns minutos.</>
        ) : (
          <>
            {meses} mês(es) do período sem cotação histórica: neles o valor de mercado é igual ao custo investido.
            {falha && <span className="negativo"> Última tentativa falhou: {falha.mensagem}</span>}
          </>
        )}
        {disparar.error && <span className="negativo"> {(disparar.error as Error).message}</span>}
      </span>
      <button disabled={carregando || disparar.isPending} onClick={() => disparar.mutate()}>
        {carregando ? "Carregando…" : "Carregar histórico de cotações"}
      </button>
    </div>
  );
}

export function Rentabilidade() {
  const { filtro } = useInvestidor();
  const { data: ativos = [] } = useAtivos();
  const [classe, setClasse] = useState("");
  const [periodo, setPeriodo] = useState<Periodo>("12m");
  const [referencias, setReferencias] = useState<Benchmark[]>(["cdi", "ibov"]);
  const [verReal, setVerReal] = useState(false);
  const inicio = inicioDoPeriodo(periodo);

  const periodoQ = useQuery({
    queryKey: ["rentabilidade", filtro, classe, inicio ?? "todos"],
    queryFn: () => api.get<MesRentabilidade[]>(`/rentabilidade/mensal${query({ investidores: filtro, classe, inicio })}`),
    placeholderData: (anterior) => anterior,
  });
  const todosQ = useQuery({
    queryKey: ["rentabilidade", filtro, classe, "todos"],
    queryFn: () => api.get<MesRentabilidade[]>(`/rentabilidade/mensal${query({ investidores: filtro, classe })}`),
  });

  const meses = periodoQ.data ?? [];
  const ultimo = meses[meses.length - 1];
  const datas = meses.map((m) => m.data);
  const soma = (f: (m: MesRentabilidade) => number) => meses.reduce((s, m) => s + f(m), 0);
  const alternar = (b: Benchmark) =>
    setReferencias((atual) => (atual.includes(b) ? atual.filter((x) => x !== b) : [...atual, b]));

  return (
    <section>
      <div className="titulo-linha">
        <h1>Rentabilidade</h1>
        <div className="abas sem-borda">
          {PERIODOS.map((p) => (
            <button key={p.id} className={p.id === periodo ? "aba ativa" : "aba"} onClick={() => setPeriodo(p.id)}>
              {p.rotulo}
            </button>
          ))}
          <label>
            Classe
            <select aria-label="Filtrar rentabilidade por classe" value={classe} onChange={(e) => setClasse(e.target.value)}>
              <option value="">Todas as classes</option>
              {[...new Set(ativos.map((ativo) => ativo.classe))].sort().map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </label>
        </div>
      </div>
      {periodoQ.error && <div className="erro">{(periodoQ.error as Error).message}</div>}
      {periodoQ.isLoading && <p>Carregando…</p>}
      {meses.some((m) => m.sem_cotacao > 0) && (
        <AvisoSemHistorico meses={meses.filter((m) => m.sem_cotacao > 0).length} />
      )}

      {ultimo && (
        <>
          <div className="cards">
            <div className="card">
              <span>TWR no período</span>
              <strong className={classeSinal(ultimo.twr_acumulado)}>{percentual(ultimo.twr_acumulado)}</strong>
              <small className="sutil">
                CDI {percentual(ultimo.cdi_acumulado)} · IBOV {percentual(ultimo.ibov_acumulado)}
              </small>
            </div>
            <div className="card">
              <span>Retorno real no período</span>
              <strong className={classeSinal(ultimo.real_acumulado)}>{percentual(ultimo.real_acumulado)}</strong>
              <small className="sutil">TWR descontada a inflação · IPCA {percentual(ultimo.ipca_acumulado)}</small>
            </div>
            <div className="card">
              <span>Patrimônio em {mesAno(ultimo.data)}</span>
              <strong>{moeda(ultimo.mercado)}</strong>
              <small className="sutil">Investido {moeda(ultimo.investido)}</small>
            </div>
            <div className="card">
              <span>Resultado no período</span>
              <strong className={classeSinal(soma((m) => m.lucro))}>{moeda(soma((m) => m.lucro))}</strong>
              <small className="sutil">valorização + proventos + trades</small>
            </div>
            <div className="card">
              <span>Fluxo líquido</span>
              <strong>{moeda(soma((m) => m.fluxo))}</strong>
              <small className="sutil">aportes − retiradas · proventos {moeda(soma((m) => m.proventos))}</small>
            </div>
          </div>

          <div className="painel">
            <div className="titulo-linha">
              <h3>TWR acumulado × referências</h3>
              <div className="acoes">
                {BENCHMARKS.map((b) => (
                  <label key={b} className="check">
                    <input type="checkbox" checked={referencias.includes(b)} onChange={() => alternar(b)} />
                    {NOMES_BENCHMARK[b]}
                  </label>
                ))}
                <label className="check">
                  <input type="checkbox" checked={verReal} onChange={(e) => setVerReal(e.target.checked)} />
                  Carteira real
                </label>
              </div>
            </div>
            <GraficoLinhas
              datas={datas}
              zero
              formatar={(v) => percentual(v)}
              series={[
                { nome: "Carteira", cor: "var(--primaria)", valores: meses.map((m) => m.twr_acumulado) },
                ...(verReal ? [{ nome: "Carteira real (− IPCA)", cor: "#7c3aed", valores: meses.map((m) => m.real_acumulado) }] : []),
                ...referencias.map((b) => ({
                  nome: NOMES_BENCHMARK[b],
                  cor: CORES_BENCHMARK[b],
                  valores: meses.map((m) => m[`${b}_acumulado`]),
                  tracejada: true,
                })),
              ]}
            />
          </div>

          <div className="paineis">
            <div className="painel">
              <h3>Evolução patrimonial</h3>
              <GraficoLinhas
                datas={datas}
                formatar={moedaCompacta}
                series={[
                  { nome: "Mercado", cor: "var(--primaria)", valores: meses.map((m) => m.mercado) },
                  { nome: "Investido", cor: "#94a3b8", valores: meses.map((m) => m.investido), tracejada: true },
                ]}
              />
            </div>
            <div className="painel">
              <h3>Resultado mensal</h3>
              <GraficoBarras datas={datas} valores={meses.map((m) => m.lucro)} formatar={moedaCompacta} />
            </div>
          </div>
        </>
      )}

      {todosQ.data && todosQ.data.length > 0 && (
        <div className="painel">
          <h3>TWR mensal</h3>
          <MapaDeCalor meses={todosQ.data} />
          {todosQ.data.some((m) => m.sem_cotacao > 0) && (
            <p className="sutil">
              Meses com ativos sem cotação usam o custo como valor de mercado. Carregue o histórico em Configurações →
              Atualizações.
            </p>
          )}
        </div>
      )}
    </section>
  );
}
