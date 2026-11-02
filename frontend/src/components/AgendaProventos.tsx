import { useQuery } from "@tanstack/react-query";
import { api, query } from "../api";
import { useDominio } from "../cadastros";
import { data, mesAno, moeda, moedaCompacta, percentual } from "../formato";
import { useInvestidor } from "../InvestidorContext";
import type { AgendaProventos as TAgenda } from "../tipos";
import { GraficoBarras } from "./Graficos";

export function AgendaProventos({ classe }: { classe?: string }) {
  const { filtro, investidores } = useInvestidor();
  const { data: dominio } = useDominio();
  const { data: a, isLoading, error } = useQuery({
    queryKey: ["proventos-agenda", filtro, classe],
    queryFn: () => api.get<TAgenda>(`/proventos/agenda${query({ investidores: filtro, classe })}`),
  });
  const nome = (id: number) => investidores.find((i) => i.id === id)?.nome ?? id;

  if (isLoading) return <p>Carregando…</p>;
  if (error) return <div className="erro">{(error as Error).message}</div>;
  if (!a) return null;

  return (
    <>
      <div className="cards">
        <div className="card">
          <span>A receber (lançados)</span>
          <strong>{moeda(a.total_a_receber)}</strong>
          <small className="sutil">{a.a_receber.length} pagamento(s) futuro(s)</small>
        </div>
        <div className="card">
          <span>Recebidos nos últimos 12 meses</span>
          <strong>{moeda(a.total_recebido_12m)}</strong>
          <small className="sutil">total efetivamente recebido</small>
        </div>
        <div className="card">
          <span>Média mensal (12 meses)</span>
          <strong>{moeda(a.media_mensal)}</strong>
          <small className="sutil">total recebido ÷ 12</small>
        </div>
        <div className="card">
          <span>Yield on Cost atual</span>
          <strong>{percentual(a.yoc_atual)}</strong>
          <small className="sutil">recebidos nos últimos 12 meses ÷ custo atual da carteira</small>
        </div>
        <div className="card">
          <span>Projeção (próximos 12 meses)</span>
          <strong>{moeda(a.total_12m)}</strong>
          <small className="sutil">estimativa com lançamentos confirmados e projeção histórica</small>
        </div>
        <div className="card">
          <span>Yield on Cost projetado</span>
          <strong>{percentual(a.yoc_projetado)}</strong>
          <small className="sutil">projeção 12 meses ÷ custo atual da carteira</small>
        </div>
      </div>

      <div className="paineis alinhado-topo">
        <div className="painel">
          <h3>Projeção mensal</h3>
          <GraficoBarras
            datas={a.meses.map((m) => m.mes)}
            valores={a.meses.map((m) => m.confirmado + m.estimado)}
            formatar={moedaCompacta}
            cor="var(--primaria)"
          />
          <table className="tabela compacta">
            <thead>
              <tr>
                <th>Mês</th>
                <th className="num">Confirmado</th>
                <th className="num">Estimado</th>
                <th className="num">Total</th>
              </tr>
            </thead>
            <tbody>
              {a.meses.map((m) => (
                <tr key={m.mes}>
                  <td>{mesAno(m.mes)}</td>
                  <td className="num">{moeda(m.confirmado)}</td>
                  <td className="num sutil">{moeda(m.estimado)}</td>
                  <td className="num">
                    <strong>{moeda(m.confirmado + m.estimado)}</strong>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="painel">
          <h3>Agenda: pagamentos lançados a receber</h3>
          {a.a_receber.length === 0 ? (
            <p className="sutil">
              Nenhum provento com pagamento futuro. Ao ver um anúncio (data-com e pagamento), lance-o em Proventos com a data de pagamento
              futura: ele aparece aqui e substitui a estimativa do mês.
            </p>
          ) : (
            <table className="tabela compacta">
              <thead>
                <tr>
                  <th>Pagamento</th>
                  <th>Data com</th>
                  <th>Ativo</th>
                  <th>Investidor</th>
                  <th>Evento</th>
                  <th className="num">Líquido</th>
                </tr>
              </thead>
              <tbody>
                {a.a_receber.map((p) => (
                  <tr key={p.id}>
                    <td>{data(p.data_pagamento)}</td>
                    <td>{data(p.data_com)}</td>
                    <td>
                      <strong>{p.ticker}</strong>
                    </td>
                    <td>{nome(p.investidor_id)}</td>
                    <td>{dominio?.eventos_provento[p.evento] ?? p.evento}</td>
                    <td className="num">{moeda(p.liquido)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          <h3>Projeção por ativo</h3>
          {a.por_ativo.length === 0 ? (
            <p className="sutil">Sem proventos nos últimos 12 meses para os ativos em carteira.</p>
          ) : (
            <table className="tabela compacta">
              <thead>
                <tr>
                  <th>Ativo</th>
                  <th className="num">12 meses</th>
                  <th className="num">YoC</th>
                </tr>
              </thead>
              <tbody>
                {a.por_ativo.map((p) => (
                  <tr key={p.ativo_id}>
                    <td>
                      <strong>{p.ticker}</strong> <span className="sutil">{p.classe}</span>
                    </td>
                    <td className="num">{moeda(p.total)}</td>
                    <td className="num">{percentual(p.yoc)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
      <p className="sutil">
        Estimativa: repete os proventos dos últimos 12 meses no mesmo mês do ano seguinte, pelo valor por cota da data-com × quantidade
        atual. Amortizações e aluguel (BTC) ficam fora. Empresas mudam valores e calendários — não é promessa de pagamento.
      </p>
    </>
  );
}
