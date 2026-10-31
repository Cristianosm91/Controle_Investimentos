import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, query } from "../api";
import { invalidarDerivados, useAtivos } from "../cadastros";
import { GraficoLinhas } from "../components/Graficos";
import { classeSinal, data, mesAno, moeda, numero, percentual } from "../formato";
import { useInvestidor } from "../InvestidorContext";
import type { Ativo, MoedaCripto, MonitorCripto, PainelCripto, PontoCripto } from "../tipos";
import "./Cripto.css";

type Atualizacao = { atualizados: string[]; avisos: string[] };

export function Cripto() {
  const { filtro } = useInvestidor();
  const cliente = useQueryClient();
  const [busca, setBusca] = useState("");
  const [termo, setTermo] = useState("");
  const [selecionada, setSelecionada] = useState<MoedaCripto | null>(null);
  const [ticker, setTicker] = useState("");
  const [vinculo, setVinculo] = useState("");
  const [ativoId, setAtivoId] = useState("");
  const [dias, setDias] = useState(30);
  const [ano, setAno] = useState(new Date().getFullYear());
  const ativos = useAtivos();
  const painel = useQuery({
    queryKey: ["cripto", filtro],
    queryFn: () => api.get<PainelCripto>(`/cripto${query({ investidores: filtro })}`),
  });
  const catalogo = useQuery({
    queryKey: ["cripto-catalogo", termo],
    queryFn: () => api.get<MoedaCripto[]>(`/cripto/catalogo${query({ busca: termo })}`),
    enabled: termo.length >= 2,
    staleTime: 300_000,
    retry: false,
  });
  const monitor = useQuery({
    queryKey: ["cripto-monitor", filtro, ano],
    queryFn: () => api.get<MonitorCripto>(`/cripto/monitor${query({ investidores: filtro, ano })}`),
  });
  const historico = useQuery({
    queryKey: ["cripto-historico", ativoId, dias],
    queryFn: () => api.get<PontoCripto[]>(`/cripto/${ativoId}/historico${query({ dias })}`),
    enabled: Boolean(ativoId),
    staleTime: 900_000,
    retry: false,
  });
  const adicionar = useMutation({
    mutationFn: (dados: { coingecko_id: string; ticker: string; ativo_id?: number }) =>
      api.post<Ativo>("/cripto/ativos", dados),
    onSuccess: () => {
      setSelecionada(null);
      setVinculo("");
      cliente.invalidateQueries({ queryKey: ["ativos"] });
      cliente.invalidateQueries({ queryKey: ["cripto"] });
    },
  });
  const atualizar = useMutation({
    mutationFn: () => api.post<Atualizacao>("/cripto/atualizar"),
    onSuccess: () => {
      invalidarDerivados(cliente);
      cliente.invalidateQueries({ queryKey: ["cripto-historico"] });
      cliente.invalidateQueries({ queryKey: ["atualizacoes"] });
    },
  });
  const itens = painel.data?.itens ?? [];
  const comId = itens.filter((i) => i.coingecko_id);
  useEffect(() => {
    if (!comId.some((i) => String(i.ativo_id) === ativoId)) setAtivoId(comId.length ? String(comId[0].ativo_id) : "");
  }, [painel.data, ativoId]);

  const erro = painel.error ?? catalogo.error ?? ativos.error ?? monitor.error ?? adicionar.error ?? atualizar.error;
  const avisos = [...(painel.data?.avisos ?? []), ...(atualizar.data?.avisos ?? []), ...(monitor.data?.avisos ?? [])];
  const investido = itens.reduce((s, i) => s + i.investido_brl, 0);
  const mercadoCompleto = itens.every((i) => i.mercado_brl !== null);
  const mercado = mercadoCompleto ? itens.reduce((s, i) => s + (i.mercado_brl ?? 0), 0) : null;

  return (
    <section className="cripto">
      <div className="titulo-linha">
        <h1>Cripto</h1>
        <button onClick={() => atualizar.mutate()} disabled={atualizar.isPending || !itens.length}>
          {atualizar.isPending ? "Atualizando…" : "Atualizar cripto"}
        </button>
      </div>
      <p className="sutil">CoinGecko → Kraken · cotações USD; BRL convertido pela última PTAX disponível
        {painel.data?.cambio_data && <> de {data(painel.data.cambio_data)} ({moeda(painel.data.cambio_usd_brl)}/USD)</>}.
        Posições respeitam o filtro global de investidores.</p>
      {erro instanceof Error && <div className="erro" role="alert">{erro.message}</div>}
      {avisos.length > 0 && <div className="aviso">{[...new Set(avisos)].map((a) => <div key={a}>{a}</div>)}</div>}

      <div className="painel">
        <h3>Adicionar ou vincular moeda do catálogo</h3>
        <form className="cripto-controles" onSubmit={(e) => {
          e.preventDefault();
          setTermo(busca.trim());
          setSelecionada(null);
        }}>
          <label>Nome ou símbolo<input value={busca} onChange={(e) => setBusca(e.target.value)} minLength={2} maxLength={80} required /></label>
          <button disabled={catalogo.isFetching || busca.trim().length < 2}>Buscar</button>
        </form>
        {catalogo.isFetching && <p>Buscando no CoinGecko…</p>}
        {catalogo.data && !catalogo.data.length && <p>Nenhuma moeda encontrada.</p>}
        {catalogo.data && catalogo.data.length > 0 && (
          <label className="cripto-catalogo">Resultado (ID identifica a moeda, não apenas o símbolo)
            <select value={selecionada?.id ?? ""} onChange={(e) => {
              const moedaSelecionada = catalogo.data.find((m) => m.id === e.target.value) ?? null;
              setSelecionada(moedaSelecionada);
              setTicker(moedaSelecionada?.ticker.slice(0, 20) ?? "");
              setVinculo("");
            }}>
              <option value="">Selecione uma moeda</option>
              {catalogo.data.map((m) => <option key={m.id} value={m.id}>{m.ticker} — {m.nome} ({m.id})</option>)}
            </select>
          </label>
        )}
        {selecionada && <form className="cripto-controles" onSubmit={(e) => {
          e.preventDefault();
          adicionar.mutate({ coingecko_id: selecionada.id, ticker, ...(vinculo ? { ativo_id: Number(vinculo) } : {}) });
        }}>
          <label>Cadastro<select value={vinculo} onChange={(e) => setVinculo(e.target.value)}>
            <option value="">Criar novo ativo (moeda USD)</option>
            {ativos.data?.filter((a) => a.classe === "CRIPTO" && !a.coingecko_id).map((a) =>
              <option key={a.id} value={a.id}>Vincular {a.ticker} — {a.nome ?? a.moeda}</option>)}
          </select></label>
          {!vinculo && <label>Ticker local (único)<input value={ticker} onChange={(e) => setTicker(e.target.value.toUpperCase())}
            maxLength={20} pattern="[A-Za-z0-9_-]+" required /></label>}
          <button disabled={adicionar.isPending}>{vinculo ? "Vincular identidade" : "Adicionar ativo"}</button>
        </form>}
        <p className="sutil">Após adicionar, atualize as cotações. Registre compras/vendas em <Link to="/operacoes">Operações</Link>.
          O vínculo de um ativo existente preserva sua moeda e seus lançamentos.</p>
      </div>

      <div className="cards">
        <div className="card"><span>Investido</span><strong>{moeda(investido)}</strong></div>
        <div className="card"><span>Valor de mercado</span><strong>{moeda(mercado)}</strong></div>
        <div className="card"><span>Lucro aberto</span><strong className={classeSinal(mercado === null ? null : mercado - investido)}>
          {moeda(mercado === null ? null : mercado - investido)}</strong></div>
      </div>
      {painel.isLoading && <p>Carregando cripto…</p>}
      {!painel.isLoading && !itens.length && <p>Nenhum ativo CRIPTO cadastrado. Busque uma moeda para começar.</p>}
      {!!itens.length && <div className="tabela-container"><table className="tabela">
        <thead><tr><th>Ativo / fonte</th><th className="num">USD / BRL</th><th className="num">24h / 7d / 30d (USD)</th>
          <th className="num">Market cap (USD)</th><th className="num">Quantidade / PM (BRL)</th><th className="num">Investido / mercado (BRL)</th><th className="num">Lucro aberto</th></tr></thead>
        <tbody>{itens.map((i) => <tr key={i.ativo_id}>
          <td><strong>{i.ticker}</strong><div className="sutil">{i.nome}</div><div className="sutil">{i.fonte ?? "Sem fonte"} · {
            i.atualizado_em ? new Date(i.atualizado_em).toLocaleString("pt-BR") : "sem snapshot"}</div></td>
          <td className="num">{moeda(i.preco_usd, "USD")}<div>{moeda(i.preco_brl)}</div></td>
          <td className="num">{[i.variacao_24h, i.variacao_7d, i.variacao_30d].map((v, n) =>
            <span key={n}>{n > 0 && " / "}<span className={classeSinal(v)}>{percentual(v)}</span></span>)}</td>
          <td className="num">{moeda(i.market_cap_usd, "USD")}</td>
          <td className="num">{numero(i.quantidade, 8)}<div>{moeda(i.preco_medio_brl)}</div></td>
          <td className="num">{moeda(i.investido_brl)}<div>{moeda(i.mercado_brl)}</div></td>
          <td className={`num ${classeSinal(i.lucro_aberto_brl)}`}>{moeda(i.lucro_aberto_brl)}</td>
        </tr>)}</tbody>
      </table></div>}

      {comId.length > 0 && <div className="painel">
        <div className="cripto-controles">
          <h3>Histórico de preço · USD</h3>
          <label>Ativo<select value={ativoId} onChange={(e) => setAtivoId(e.target.value)}>
            {comId.map((i) => <option key={i.ativo_id} value={i.ativo_id}>{i.ticker}</option>)}
          </select></label>
          <label>Período<select value={dias} onChange={(e) => setDias(Number(e.target.value))}>
            {[7, 30, 90].map((d) => <option key={d} value={d}>{d} dias</option>)}
          </select></label>
        </div>
        <p className="sutil">Histórico CoinGecko em UTC; cache de 15 minutos. Não há gráfico substituto quando a fonte falha.</p>
        {historico.isLoading && <p>Carregando histórico…</p>}
        {historico.error instanceof Error && <div className="erro" role="alert">{historico.error.message}</div>}
        {historico.data && <GraficoLinhas datas={historico.data.map((p) => p.instante.slice(0, 10))}
          series={[{ nome: "Preço USD", cor: "var(--primaria)", valores: historico.data.map((p) => p.preco_usd) }]}
          formatar={(v) => moeda(v, "USD")} />}
      </div>}

      <div className="painel">
        <div className="cripto-controles"><h3>Monitor mensal de vendas e ganhos</h3>
          <label>Ano<input type="number" min={1990} max={2099} value={ano} onChange={(e) => {
            const valor = Number(e.target.value);
            if (valor >= 1990 && valor <= 2099) setAno(valor);
          }} /></label>
        </div>
        <p className="aviso">Informativo, por investidor: limite de referência de R$ 35 mil sobre vendas brutas somadas de todas as
          criptos, não sobre lucro. Estar abaixo dele não confirma isenção. Custódia, local de negociação e regime fiscal não
          estão classificados. Não calcula imposto/DARF nem altera P10; valide as obrigações com orientação fiscal.</p>
        {monitor.isLoading && <p>Carregando monitor…</p>}
        {monitor.data && !monitor.data.meses.length && <p>Sem vendas de cripto no ano selecionado.</p>}
        {!!monitor.data?.meses.length && <div className="tabela-container"><table className="tabela">
          <thead><tr><th>Investidor / mês</th><th className="num">Vendas brutas</th><th className="num">Ganhos / perdas</th>
            <th className="num">Resultado</th><th className="num">Saldo do limite</th><th>Referência de R$ 35 mil</th></tr></thead>
          <tbody>{monitor.data.meses.map((m) => <tr key={`${m.investidor_id}-${m.competencia}`}>
            <td>{m.investidor}<div className="sutil">{mesAno(m.competencia)}</div></td>
            <td className="num">{moeda(m.vendas_brl)}</td>
            <td className="num">{moeda(m.ganhos_brl)} / {moeda(m.perdas_brl)}</td>
            <td className={`num ${classeSinal(m.resultado_brl)}`}>{moeda(m.resultado_brl)}</td>
            <td className="num">{moeda(m.saldo_limite_brl)}</td>
            <td>{m.acima_limite ? "Acima do limite" : "Até o limite (não confirma isenção)"}</td>
          </tr>)}</tbody>
        </table></div>}
      </div>
    </section>
  );
}
