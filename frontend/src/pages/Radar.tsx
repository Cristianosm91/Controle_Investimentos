import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api, query } from "../api";
import { classeSinal, data, moeda, percentual } from "../formato";
import { useInvestidor } from "../InvestidorContext";
import type { Ativo, ItemRadar } from "../tipos";

function Pct({ valor }: { valor: number | null }) {
  return <span className={classeSinal(valor)}>{percentual(valor)}</span>;
}

function PrecoAlvo({ item }: { item: ItemRadar }) {
  const cliente = useQueryClient();
  const [texto, setTexto] = useState(item.preco_alvo === null ? "" : String(item.preco_alvo));
  const salvar = useMutation({
    mutationFn: (valor: number | null) => api.put(`/radar/${item.ativo_id}/alvo`, { preco_alvo: valor }),
    onSuccess: () => {
      cliente.invalidateQueries({ queryKey: ["radar"] });
      cliente.invalidateQueries({ queryKey: ["alertas"] });
    },
  });
  const gravar = () => {
    const valor = texto.trim() === "" ? null : Number(texto.replace(",", "."));
    if (valor !== null && !(valor > 0)) return;
    if (valor !== item.preco_alvo) salvar.mutate(valor);
  };
  return (
    <>
      <input
        className="radar-alvo"
        inputMode="decimal"
        placeholder="—"
        aria-label={`Preço-alvo de ${item.ticker}`}
        title="Gera um alerta quando a cotação ficar igual ou abaixo deste preço"
        value={texto}
        onChange={(e) => setTexto(e.target.value)}
        onBlur={gravar}
        onKeyDown={(e) => e.key === "Enter" && (e.currentTarget as HTMLInputElement).blur()}
      />
      {item.atingiu_alvo && <div className="etiqueta alerta-media">atingiu</div>}
      {salvar.error && <div className="negativo">{(salvar.error as Error).message}</div>}
    </>
  );
}

export function Radar() {
  const { filtro } = useInvestidor();
  const cliente = useQueryClient();
  const [ativoSelecionado, setAtivoSelecionado] = useState("");
  const [tickerNovo, setTickerNovo] = useState("");
  const [classeNova, setClasseNova] = useState<"AÇÃO" | "FII" | "FIAGRO">("AÇÃO");
  const radar = useQuery({
    queryKey: ["radar", filtro],
    queryFn: () => api.get<ItemRadar[]>(`/radar${query({ investidores: filtro })}`),
  });
  const ativos = useQuery({
    queryKey: ["ativos"],
    queryFn: () => api.get<Ativo[]>("/ativos"),
  });

  const idsNoRadar = useMemo(() => new Set((radar.data ?? []).map((item) => item.ativo_id)), [radar.data]);
  const elegiveis = (ativos.data ?? []).filter(
    (ativo) => ativo.mercado === "BVMF" && ativo.cotacao_automatica && !idsNoRadar.has(ativo.id),
  );
  const adicionar = useMutation({
    mutationFn: (ativoId: number) => api.post<{ ativo_id: number; ticker: string }>(`/radar/${ativoId}`),
    onSuccess: () => {
      setAtivoSelecionado("");
      cliente.invalidateQueries({ queryKey: ["radar"] });
    },
  });
  const cadastrar = useMutation({
    mutationFn: () =>
      api.post<{ ativo_id: number; ticker: string }>("/radar", {
        ticker: tickerNovo.trim().toUpperCase(),
        classe: classeNova,
      }),
    onSuccess: () => {
      setTickerNovo("");
      cliente.invalidateQueries({ queryKey: ["radar"] });
      cliente.invalidateQueries({ queryKey: ["ativos"] });
    },
  });
  const remover = useMutation({
    mutationFn: (ativoId: number) => api.del(`/radar/${ativoId}`),
    onSuccess: () => cliente.invalidateQueries({ queryKey: ["radar"] }),
  });
  const erro = radar.error ?? ativos.error ?? adicionar.error ?? cadastrar.error ?? remover.error;

  return (
    <section className="radar">
      <div className="titulo-linha">
        <h1>Radar</h1>
        <span className="sutil">Acompanhe ativos B3 com ou sem posição</span>
      </div>

      {erro && <div className="erro">{(erro as Error).message}</div>}

      <div className="painel">
        <div className="radar-controles">
          <form
            onSubmit={(evento) => {
              evento.preventDefault();
              if (ativoSelecionado) adicionar.mutate(Number(ativoSelecionado));
            }}
          >
            <label>
              Ativo cadastrado
              <select
                value={ativoSelecionado}
                onChange={(evento) => setAtivoSelecionado(evento.target.value)}
                disabled={ativos.isLoading || !elegiveis.length}
              >
                <option value="">Selecione um ativo B3</option>
                {elegiveis.map((ativo) => (
                  <option key={ativo.id} value={ativo.id}>
                    {ativo.ticker} — {ativo.nome ?? ativo.classe}
                  </option>
                ))}
              </select>
            </label>
            <button className="radar-adicionar" disabled={!ativoSelecionado || adicionar.isPending}>
              {adicionar.isPending ? "ADICIONANDO…" : "ADICIONAR AO RADAR"}
            </button>
          </form>
          <form
            onSubmit={(evento) => {
              evento.preventDefault();
              if (tickerNovo.trim()) cadastrar.mutate();
            }}
          >
            <label>
              Novo ticker B3
              <input
                value={tickerNovo}
                onChange={(evento) => setTickerNovo(evento.target.value.toUpperCase())}
                maxLength={16}
                pattern="[A-Z0-9]{4,16}"
                title="Use de 4 a 16 letras ou números"
                required
              />
            </label>
            <label>
              Classe
              <select value={classeNova} onChange={(evento) => setClasseNova(evento.target.value as typeof classeNova)}>
                <option value="AÇÃO">Ação</option>
                <option value="FII">FII</option>
                <option value="FIAGRO">Fiagro</option>
              </select>
            </label>
            <button className="radar-adicionar" disabled={cadastrar.isPending}>
              {cadastrar.isPending ? "CADASTRANDO…" : "CADASTRAR E ADICIONAR"}
            </button>
          </form>
        </div>
        <p className="sutil radar-ajuda">
          Métricas de 60 dias e 52 semanas só aparecem quando o histórico armazenado cobre o período completo. Use a
          tela <Link to="/configuracoes">Atualizações</Link> para carregar o histórico da B3.
        </p>
      </div>

      {radar.isLoading ? (
        <p>Carregando Radar…</p>
      ) : radar.data?.length ? (
        <div className="tabela-container">
          <table className="tabela radar-tabela">
            <thead>
              <tr>
                <th>Ativo</th>
                <th className="num">Cotação</th>
                <th className="num">Preço-alvo</th>
                <th className="num">Variação 1d / 7d / 14d</th>
                <th className="num">Drawdown 60d</th>
                <th className="num">Mín. / máx. 52s</th>
                <th className="num">Graham / upside</th>
                <th className="num">P/L</th>
                <th className="num">P/VP</th>
                <th className="num">DY</th>
                <th className="num">ROE</th>
                <th className="num">YoC 12m</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {radar.data.map((item) => (
                <tr key={item.ativo_id}>
                  <td>
                    <strong>{item.ticker}</strong>
                    <div className="sutil">{item.nome ?? item.classe}</div>
                    <span className="sutil">{item.tem_posicao ? "Com posição" : "Só no Radar"}</span>
                    <div className="sutil">Fundamentos {data(item.data_ref_fundamentos)}</div>
                  </td>
                  <td className="num" title={item.cotacao_fonte ?? "Sem cotação"}>
                    {moeda(item.cotacao, item.moeda)}
                    <div className="sutil">{data(item.cotacao_data)}</div>
                  </td>
                  <td className="num">
                    <PrecoAlvo item={item} />
                  </td>
                  <td className="num">
                    <Pct valor={item.variacao_1d_pct} /> / <Pct valor={item.variacao_7d_pct} /> /{" "}
                    <Pct valor={item.variacao_14d_pct} />
                  </td>
                  <td className="num">
                    <Pct valor={item.drawdown_60d_pct} />
                  </td>
                  <td className="num">
                    {moeda(item.minimo_52s, item.moeda)} / {moeda(item.maximo_52s, item.moeda)}
                  </td>
                  <td
                    className="num"
                    title="Estimativa pela fórmula de Graham; não representa recomendação de investimento"
                  >
                    {moeda(item.preco_teto_graham, item.moeda)}
                    <div className="sutil">
                      <Pct valor={item.upside_graham_pct} />
                    </div>
                  </td>
                  <td className="num">{item.preco_lucro?.toLocaleString("pt-BR") ?? "—"}</td>
                  <td className="num">{item.preco_valor_patrimonial?.toLocaleString("pt-BR") ?? "—"}</td>
                  <td className="num">
                    {percentual(item.dividend_yield === null ? null : item.dividend_yield / 100)}
                    {(item.classe === "FII" || item.classe === "FIAGRO") && (
                      <div className="sutil">
                        FFO {percentual(item.fii_ffo_yield === null ? null : item.fii_ffo_yield / 100)}
                      </div>
                    )}
                  </td>
                  <td className="num">
                    {percentual(item.roe === null ? null : item.roe / 100)}
                    <div className="sutil">
                      ROIC {percentual(item.roic === null ? null : item.roic / 100)}
                    </div>
                  </td>
                  <td className="num">
                    <Pct valor={item.yoc_12m} />
                  </td>
                  <td className="num">
                    <button
                      className="radar-remover"
                      disabled={remover.isPending}
                      onClick={() => remover.mutate(item.ativo_id)}
                    >
                      REMOVER
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="painel">
          <p>Nenhum ativo acompanhado. Selecione um ativo B3 cadastrado para começar.</p>
        </div>
      )}
    </section>
  );
}
