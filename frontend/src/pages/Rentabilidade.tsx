import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useRef, useState } from "react";
import { api, query } from "../api";
import { invalidarDerivados, useAtivosDisponiveis } from "../cadastros";
import { GraficoBarras, GraficoLinhas } from "../components/Graficos";
import { AjudaIndicador } from "../components/AjudaIndicador";
import { FiltroMultisselecao } from "../components/FiltroMultisselecao";
import { classeSinal, mesAno, MESES, moeda, moedaCompacta, percentual } from "../formato";
import { filtrarAtivos, opcoesAtivos, opcoesClasses, OPCOES_MERCADO, valorFiltro } from "../filtrosAtivos";
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
    <div className={carregando ? "aviso titulo-linha" : "aviso atencao titulo-linha"}>
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
  const { data: ativos = [] } = useAtivosDisponiveis(filtro);
  const [mercados, setMercados] = useState<string[] | null>(null);
  const [classes, setClasses] = useState<string[] | null>(null);
  const [ativoIds, setAtivoIds] = useState<string[] | null>(null);
  const [periodo, setPeriodo] = useState<Periodo>("12m");
  const [referencias, setReferencias] = useState<Benchmark[]>(["cdi", "ibov"]);
  const [verReal, setVerReal] = useState(false);
  const inicio = inicioDoPeriodo(periodo);
  const ativosPorMercado = useMemo(() => filtrarAtivos(ativos, mercados, null), [ativos, mercados]);
  const opcoesDeClasse = useMemo(() => opcoesClasses(ativosPorMercado), [ativosPorMercado]);
  const ativosFiltrados = useMemo(() => filtrarAtivos(ativos, mercados, classes), [ativos, mercados, classes]);
  const opcoesDeAtivo = useMemo(() => opcoesAtivos(ativosFiltrados), [ativosFiltrados]);
  const filtros = {
    mercados: valorFiltro(mercados),
    classes: valorFiltro(classes),
    ativo_ids: valorFiltro(ativoIds),
  };

  const periodoQ = useQuery({
    queryKey: ["rentabilidade", filtro, filtros, inicio ?? "todos"],
    queryFn: () => api.get<MesRentabilidade[]>(`/rentabilidade/mensal${query({ investidores: filtro, ...filtros, inicio })}`),
    placeholderData: (anterior) => anterior,
  });
  const todosQ = useQuery({
    queryKey: ["rentabilidade", filtro, filtros, "todos"],
    queryFn: () => api.get<MesRentabilidade[]>(`/rentabilidade/mensal${query({ investidores: filtro, ...filtros })}`),
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
        <div className="abas-controles">
          <div className="abas sem-borda">
            {PERIODOS.map((p) => (
              <button key={p.id} className={p.id === periodo ? "aba ativa" : "aba"} onClick={() => setPeriodo(p.id)}>
                {p.rotulo}
              </button>
            ))}
          </div>
          <FiltroMultisselecao
            rotulo="Mercados"
            resumoTodos="Todos os mercados"
            resumoNenhum="Nenhum mercado"
            resumoMultiplos={(quantidade) => `${quantidade} mercados selecionados`}
            opcoes={OPCOES_MERCADO}
            selecionados={mercados}
            aoMudar={setMercados}
          />
          <FiltroMultisselecao
            rotulo="Classes"
            resumoTodos="Todas as classes"
            resumoNenhum="Nenhuma classe"
            resumoMultiplos={(quantidade) => `${quantidade} classes selecionadas`}
            opcoes={opcoesDeClasse}
            selecionados={classes}
            aoMudar={setClasses}
          />
          <FiltroMultisselecao
            rotulo="Ativos"
            resumoTodos="Todos os ativos"
            resumoNenhum="Nenhum ativo"
            resumoMultiplos={(quantidade) => `${quantidade} ativos selecionados`}
            opcoes={opcoesDeAtivo}
            selecionados={ativoIds}
            aoMudar={setAtivoIds}
          />
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
              <span>TWR no período <AjudaIndicador titulo="TWR no período" texto="Retorno acumulado da carteira no período, composto a partir dos retornos mensais e separado dos fluxos de aportes e retiradas. CDI e IBOV são referências acumuladas." /></span>
              <strong className={classeSinal(ultimo.twr_acumulado)}>{percentual(ultimo.twr_acumulado)}</strong>
              <small className="sutil">
                CDI {percentual(ultimo.cdi_acumulado)} · IBOV {percentual(ultimo.ibov_acumulado)}
              </small>
            </div>
            <div className="card">
              <span>Retorno real no período <AjudaIndicador titulo="Retorno real no período" texto="TWR acumulada ajustada pela inflação medida pelo IPCA no período." /></span>
              <strong className={classeSinal(ultimo.real_acumulado)}>{percentual(ultimo.real_acumulado)}</strong>
              <small className="sutil">TWR descontada a inflação · IPCA {percentual(ultimo.ipca_acumulado)}</small>
            </div>
            <div className="card">
              <span>Patrimônio em {mesAno(ultimo.data)} <AjudaIndicador titulo="Patrimônio no último mês" texto="Valor de mercado da carteira no último mês exibido; o valor investido no mesmo mês aparece abaixo. Sem cotação histórica, usa-se o custo." /></span>
              <strong>{moeda(ultimo.mercado)}</strong>
              <small className="sutil">Investido {moeda(ultimo.investido)}</small>
            </div>
            <div className="card">
              <span>Resultado no período <AjudaIndicador titulo="Resultado no período" texto="Soma dos resultados mensais do período: valorização, proventos, aluguel e resultados de operações." /></span>
              <strong className={classeSinal(soma((m) => m.lucro))}>{moeda(soma((m) => m.lucro))}</strong>
              <small className="sutil">valorização + proventos + aluguel + trades</small>
            </div>
            <div className="card">
              <span>Fluxo líquido <AjudaIndicador titulo="Fluxo líquido" texto="Soma dos fluxos mensais: aportes menos retiradas no período. Os proventos e aluguéis do período são informados separadamente abaixo." /></span>
              <strong>{moeda(soma((m) => m.fluxo))}</strong>
              <small className="sutil">
                aportes − retiradas · proventos {moeda(soma((m) => m.proventos))} · aluguel {moeda(soma((m) => m.aluguel))}
              </small>
            </div>
          </div>

          <div className="painel">
            <div className="titulo-linha">
              <h3>TWR acumulado × referências <AjudaIndicador titulo="TWR acumulado e referências" texto="Compara a evolução da TWR acumulada da carteira com as referências selecionadas; a série real ajusta a carteira pelo IPCA." /></h3>
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
              titulo="TWR acumulado × referências"
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
              <h3>Evolução patrimonial <AjudaIndicador titulo="Evolução patrimonial" texto="Compara o valor de mercado e o investido em cada mês. Sem cotação histórica, o cálculo pode usar o custo." /></h3>
              <GraficoLinhas
                titulo="Evolução patrimonial"
                datas={datas}
                formatar={moedaCompacta}
                series={[
                  { nome: "Mercado", cor: "var(--primaria)", valores: meses.map((m) => m.mercado) },
                  { nome: "Investido", cor: "#94a3b8", valores: meses.map((m) => m.investido), tracejada: true },
                ]}
              />
            </div>
            <div className="painel">
              <h3>Resultado mensal <AjudaIndicador titulo="Resultado mensal" texto="Cada barra representa o resultado do mês, incluindo valorização, proventos, aluguel e trades." /></h3>
              <GraficoBarras datas={datas} valores={meses.map((m) => m.lucro)} formatar={moedaCompacta} titulo="Resultado mensal" rotuloValor="Resultado" />
            </div>
          </div>
        </>
      )}

      {todosQ.data && todosQ.data.length > 0 && (
        <div className="painel">
          <h3>TWR mensal <AjudaIndicador titulo="TWR mensal" texto="Cada célula mostra a TWR do mês; o total anual compõe os retornos mensais. CDI e IBOV mostram as referências anuais compostas." /></h3>
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
