import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api, query } from "../api";
import { GraficoBarras, GraficoLinhas } from "../components/Graficos";
import { classeSinal, data, moeda, moedaCompacta, percentual } from "../formato";
import { useInvestidor } from "../InvestidorContext";
import { BENCHMARKS, NOMES_BENCHMARK } from "../referencias";
import type { MesRentabilidade, Posicao, Resumo as TResumo } from "../tipos";

function Pct({ v }: { v: number | null | undefined }) {
  return <span className={classeSinal(v)}>{percentual(v)}</span>;
}

export function Resumo() {
  const { filtro } = useInvestidor();
  const resumo = useQuery({
    queryKey: ["resumo", filtro],
    queryFn: () => api.get<TResumo>(`/rentabilidade/resumo${query({ investidores: filtro })}`),
  });
  const mensal = useQuery({
    queryKey: ["rentabilidade", filtro, "todos"],
    queryFn: () => api.get<MesRentabilidade[]>(`/rentabilidade/mensal${query({ investidores: filtro })}`),
  });
  const posicoes = useQuery({
    queryKey: ["posicoes", filtro, false],
    queryFn: () => api.get<Posicao[]>(`/posicoes${query({ investidores: filtro, agrupar: "ativo", somente_abertas: false })}`),
  });

  const r = resumo.data;
  const meses = mensal.data ?? [];
  const abertas = (posicoes.data ?? []).filter((p) => p.quantidade > 0 && p.variacao_dia_pct !== null);
  const destaques = [...abertas].sort((a, b) => (b.variacao_dia_pct ?? 0) - (a.variacao_dia_pct ?? 0));
  const lucroTotal = r ? r.lucro_aberto + r.lucro_realizado + r.proventos_total : 0;

  return (
    <section>
      <div className="titulo-linha">
        <h1>Resumo</h1>
        {r?.data_referencia && <span className="sutil">Cotações até {data(r.data_referencia)}</span>}
      </div>
      {(resumo.error ?? mensal.error) && <div className="erro">{((resumo.error ?? mensal.error) as Error).message}</div>}
      {resumo.isLoading && <p>Carregando…</p>}

      {r && (
        <>
          <div className="cards">
            <div className="card">
              <span>Patrimônio</span>
              <strong>{moeda(r.patrimonio)}</strong>
              <small className="sutil">Investido {moeda(r.investido)}</small>
            </div>
            <div className="card">
              <span>Lucro aberto</span>
              <strong className={classeSinal(r.lucro_aberto)}>{moeda(r.lucro_aberto)}</strong>
              <small className={classeSinal(r.lucro_aberto)}>{percentual(r.investido ? r.lucro_aberto / r.investido : null)}</small>
            </div>
            <div className="card">
              <span>Lucro total</span>
              <strong className={classeSinal(lucroTotal)}>{moeda(lucroTotal)}</strong>
              <small className="sutil">aberto + realizado + proventos</small>
            </div>
            <div className="card">
              <span>Proventos (12 meses)</span>
              <strong>{moeda(r.proventos_12m)}</strong>
              <small className="sutil">YoC {percentual(r.yoc_12m)} · total {moeda(r.proventos_total)}</small>
            </div>
            <div className="card">
              <span>TIR</span>
              <strong className={classeSinal(r.tir_aa)}>{percentual(r.tir_aa)} a.a.</strong>
              <small className="sutil">{percentual(r.tir_am)} a.m.</small>
            </div>
          </div>

          <div className="paineis">
            <div className="painel">
              <h3>Rentabilidade (TWR) × referências</h3>
              <table className="tabela">
                <thead>
                  <tr>
                    <th>Período</th>
                    <th className="num">Carteira</th>
                    {BENCHMARKS.map((b) => (
                      <th key={b} className="num">
                        {NOMES_BENCHMARK[b]}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {r.janelas.map((j) => (
                    <tr key={j.nome}>
                      <td>
                        {j.nome}
                        <div className="sutil">desde {data(j.inicio)}</div>
                      </td>
                      <td className="num">
                        <strong>
                          <Pct v={j.twr} />
                        </strong>
                      </td>
                      {BENCHMARKS.map((b) => (
                        <td key={b} className="num">
                          <Pct v={j[b]} />
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
              <p className="sutil">
                <Link to="/dashboard">Ver rentabilidade detalhada →</Link>
              </p>
            </div>

            <div className="painel">
              <h3>Proventos dos últimos 12 meses</h3>
              <GraficoBarras
                datas={r.proventos_mensais.map(([d]) => d)}
                valores={r.proventos_mensais.map(([, v]) => v)}
                formatar={moedaCompacta}
                cor="#10b981"
              />
            </div>
          </div>
        </>
      )}

      {meses.length > 0 && (
        <div className="painel">
          <h3>Evolução patrimonial</h3>
          <GraficoLinhas
            datas={meses.map((m) => m.data)}
            series={[
              { nome: "Mercado", cor: "var(--primaria)", valores: meses.map((m) => m.mercado) },
              { nome: "Investido", cor: "#94a3b8", valores: meses.map((m) => m.investido), tracejada: true },
            ]}
            formatar={moedaCompacta}
          />
        </div>
      )}

      {destaques.length > 0 && (
        <div className="paineis">
          {[
            { titulo: "Maiores altas do dia", lista: destaques.slice(0, 5) },
            { titulo: "Maiores baixas do dia", lista: destaques.slice(-5).reverse() },
          ].map(({ titulo, lista }) => (
            <div key={titulo} className="painel">
              <h3>{titulo}</h3>
              <table className="tabela">
                <tbody>
                  {lista.map((p) => (
                    <tr key={p.ativo_id}>
                      <td>
                        <strong>{p.ticker}</strong>
                      </td>
                      <td className="num">{moeda(p.cotacao, p.moeda)}</td>
                      <td className="num">
                        <Pct v={p.variacao_dia_pct} />
                      </td>
                      <td className="num">
                        <span className={classeSinal(p.lucro_dia)}>{moeda(p.lucro_dia)}</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
