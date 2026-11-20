import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";
import { api, query } from "../api";
import { useAtivos } from "../cadastros";
import { GraficoBarras, GraficoLinhas } from "../components/Graficos";
import { AjudaIndicador } from "../components/AjudaIndicador";
import { SeloCotacaoAntiga } from "../components/SeloCotacaoAntiga";
import { cotacaoDesatualizada } from "../cotacao";
import { classeSinal, data, moeda, moedaCompacta, percentual } from "../formato";
import { useInvestidor } from "../InvestidorContext";
import { BENCHMARKS, NOMES_BENCHMARK } from "../referencias";
import type { MesRentabilidade, Posicao, Resumo as TResumo } from "../tipos";

function Pct({ v }: { v: number | null | undefined }) {
  return <span className={classeSinal(v)}>{percentual(v)}</span>;
}

export function Resumo() {
  const { filtro, investidores } = useInvestidor();
  const { data: ativos = [] } = useAtivos();
  const [classe, setClasse] = useState("");
  const classes = [...new Set(ativos.map((ativo) => ativo.classe))].sort();
  const resumo = useQuery({
    queryKey: ["resumo", filtro, classe],
    queryFn: () => api.get<TResumo>(`/rentabilidade/resumo${query({ investidores: filtro, classe })}`),
  });
  const mensal = useQuery({
    queryKey: ["rentabilidade", filtro, classe, "todos"],
    queryFn: () => api.get<MesRentabilidade[]>(`/rentabilidade/mensal${query({ investidores: filtro, classe })}`),
  });
  const posicoes = useQuery({
    queryKey: ["posicoes", filtro, false],
    queryFn: () => api.get<Posicao[]>(`/posicoes${query({ investidores: filtro, agrupar: "ativo", somente_abertas: false })}`),
  });

  const r = resumo.data;
  const meses = mensal.data ?? [];
  const automaticos = new Set(ativos.filter((a) => a.cotacao_automatica).map((a) => a.id));
  const posicoesAbertas = (posicoes.data ?? []).filter((p) => p.quantidade > 0 && (!classe || p.classe === classe));
  const cotacoesMonitoradas = posicoesAbertas.filter((p) => automaticos.has(p.ativo_id));
  const cotacoesAusentes = cotacoesMonitoradas.filter((p) => !p.cotacao_data);
  const cotacoesDefasadas = cotacoesMonitoradas.filter(
    (p) => p.cotacao_data && cotacaoDesatualizada(p.cotacao_data, p.classe),
  );
  const cotacaoMaisRecente = [...cotacoesMonitoradas]
    .filter((p) => p.cotacao_data)
    .sort((a, b) => (b.cotacao_data ?? "").localeCompare(a.cotacao_data ?? ""))[0];
  const primeiroAcessoSemInvestidor = posicoes.isSuccess && investidores.filter((i) => i.ativo).length === 0;
  const carteiraSemPosicoes =
    posicoes.isSuccess && investidores.some((i) => i.ativo) && (posicoes.data ?? []).length === 0;
  const abertas = (posicoes.data ?? []).filter(
    (p) => p.quantidade > 0 && p.variacao_dia_pct !== null && (!classe || p.classe === classe),
  );
  const defasada = (p: Posicao) => automaticos.has(p.ativo_id) && cotacaoDesatualizada(p.cotacao_data, p.classe);
  const destaques = [...abertas].sort((a, b) => (b.variacao_dia_pct ?? 0) - (a.variacao_dia_pct ?? 0));
  const lucroTotal = r ? r.lucro_aberto + r.lucro_realizado + r.proventos_total + r.aluguel_total : 0;

  return (
    <section>
      <div className="titulo-linha">
        <h1>Resumo</h1>
        <div className="acoes">
          <label>
            Classe
            <select aria-label="Filtrar resumo por classe" value={classe} onChange={(e) => setClasse(e.target.value)}>
              <option value="">Todas as classes</option>
              {classes.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </label>
          {r?.data_referencia && <span className="sutil">Cotações até {data(r.data_referencia)}</span>}
        </div>
      </div>
      {(resumo.error ?? mensal.error) && <div className="erro">{((resumo.error ?? mensal.error) as Error).message}</div>}
      {resumo.isLoading && <p>Carregando…</p>}

      {primeiroAcessoSemInvestidor && (
        <div className="painel">
          <h2>Comece por aqui</h2>
          <p>Cadastre um investidor e depois traga seu histórico para preencher a carteira.</p>
          <ol>
            <li><Link to="/configuracoes">Cadastrar investidor</Link></li>
            <li><Link to="/operacoes">Cadastrar operações ou importar um extrato</Link></li>
            <li><Link to="/portfolio">Conferir a carteira</Link></li>
          </ol>
        </div>
      )}
      {carteiraSemPosicoes && (
        <div className="painel">
          <h2>Carteira ainda sem posições</h2>
          <p>Para começar a acompanhar patrimônio e rentabilidade, registre operações ou importe um arquivo da B3.</p>
          <p><Link to="/operacoes">Ir para Operações e importações</Link></p>
        </div>
      )}

      {r && (
        <>
          <div className="cards">
            <div className="card">
              <span>Patrimônio <AjudaIndicador titulo="Patrimônio" texto="Valor de mercado da carteira no último mês da série. O investido abaixo corresponde ao capital calculado para os filtros selecionados." /></span>
              <strong>{moeda(r.patrimonio)}</strong>
              <small className="sutil">Investido {moeda(r.investido)}</small>
            </div>
            <div className="card">
              <span>Lucro aberto <AjudaIndicador titulo="Lucro aberto" texto="Patrimônio menos o valor investido. O percentual divide o lucro aberto pelo investido." /></span>
              <strong className={classeSinal(r.lucro_aberto)}>{moeda(r.lucro_aberto)}</strong>
              <small className={classeSinal(r.lucro_aberto)}>{percentual(r.investido ? r.lucro_aberto / r.investido : null)}</small>
            </div>
            <div className="card">
              <span>Lucro total <AjudaIndicador titulo="Lucro total" texto="Soma do lucro aberto, resultado realizado nas operações, proventos e aluguel BTC líquido." /></span>
              <strong className={classeSinal(lucroTotal)}>{moeda(lucroTotal)}</strong>
              <small className="sutil">aberto + realizado + proventos + aluguel BTC</small>
            </div>
            <div className="card">
              <span>Aluguel BTC <AjudaIndicador titulo="Aluguel BTC" texto="Soma dos rendimentos líquidos de aluguel de ações registrados; já está incluída no lucro total." /></span>
              <strong className={classeSinal(r.aluguel_total)}>{moeda(r.aluguel_total)}</strong>
              <small className="sutil">resultado líquido já incluído no lucro total</small>
            </div>
            <div className="card">
              <span>Proventos (12 meses) <AjudaIndicador titulo="Proventos (12 meses)" texto="Soma dos proventos líquidos nos últimos 365 dias. O YoC relaciona esse valor ao investido; o total abaixo considera o histórico." /></span>
              <strong>{moeda(r.proventos_12m)}</strong>
              <small className="sutil">YoC {percentual(r.yoc_12m)} · total {moeda(r.proventos_total)}</small>
            </div>
            <div className="card">
              <span>TIR <AjudaIndicador titulo="TIR" texto="Taxa interna de retorno anualizada calculada a partir das datas e valores das movimentações, rendimentos e patrimônio atual. A taxa mensal equivalente aparece abaixo." /></span>
              <strong className={classeSinal(r.tir_aa)}>{percentual(r.tir_aa)} a.a.</strong>
              <small className="sutil">{percentual(r.tir_am)} a.m.</small>
            </div>
          </div>

          {posicoes.isSuccess && posicoesAbertas.length > 0 && (
            <div className="painel" aria-labelledby="qualidade-cotacoes">
              <h2 id="qualidade-cotacoes">Qualidade das cotações</h2>
              <p className="sutil">
                Status baseado na origem e data disponíveis. A indicação de defasagem reutiliza a regra já usada no Portfólio;
                não representa uma validação de feriados nem uma garantia de atualização intradiária.
              </p>
              {cotacoesMonitoradas.length > 0 ? (
                <>
                  <dl className="lista-resumo">
                    <div><dt>Sem cotação registrada</dt><dd>{cotacoesAusentes.length}</dd></div>
                    <div><dt>Anterior ao limite atual</dt><dd>{cotacoesDefasadas.length}</dd></div>
                    <div>
                      <dt>Última data disponível</dt>
                      <dd>
                        {cotacaoMaisRecente
                          ? `${data(cotacaoMaisRecente.cotacao_data)} · ${cotacaoMaisRecente.cotacao_fonte ?? "fonte não informada"}`
                          : "—"}
                      </dd>
                    </div>
                  </dl>
                  <p className="sutil">
                    Ativos sem preço registrado ou com cotação defasada podem afetar a leitura do patrimônio e da rentabilidade.
                    Em meses sem cotação histórica, a série existente usa o custo. Confira os tickers no{" "}
                    <Link to="/portfolio">Portfólio</Link>.
                  </p>
                </>
              ) : (
                <p>Não há posições com cotação automática para monitorar.</p>
              )}
            </div>
          )}

          <div className="paineis">
            <div className="painel">
              <h3>Rentabilidade (TWR) × referências <AjudaIndicador titulo="Rentabilidade (TWR) e referências" texto="A TWR acumula os retornos da carteira no período, separando o efeito de aportes e retiradas. A coluna real desconta o IPCA; as demais mostram as referências correspondentes." /></h3>
              <div className="tabela-container">
                <table className="tabela">
                  <thead>
                    <tr>
                      <th>Período</th>
                      <th className="num">Carteira</th>
                      <th className="num" title="Rentabilidade da carteira descontada a inflação (IPCA)">
                        Real
                      </th>
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
                        <td className="num">
                          <Pct v={j.real} />
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
              </div>
              <p className="sutil">
                <Link to="/dashboard">Ver rentabilidade detalhada →</Link>
              </p>
            </div>

            <div className="painel">
              <h3>Proventos dos últimos 12 meses <AjudaIndicador titulo="Proventos dos últimos 12 meses" texto="Cada barra mostra os proventos líquidos registrados no respectivo mês da série, para os filtros selecionados." /></h3>
              <GraficoBarras
                datas={r.proventos_mensais.map(([d]) => d)}
                valores={r.proventos_mensais.map(([, v]) => v)}
                formatar={moedaCompacta}
                cor="var(--primaria)"
                titulo="Proventos dos últimos 12 meses"
                rotuloValor="Proventos"
              />
            </div>
          </div>
        </>
      )}

      {meses.length > 0 && (
        <div className="painel">
          <h3>Evolução patrimonial <AjudaIndicador titulo="Evolução patrimonial" texto="Compara, em cada mês da série, o valor de mercado da carteira com o valor investido. Na falta de cotação histórica, o cálculo pode usar o custo." /></h3>
          <GraficoLinhas
            titulo="Evolução patrimonial"
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
              <h3>{titulo} <AjudaIndicador titulo={titulo} texto="Posições abertas ordenadas pela variação percentual diária da cotação. A lista mostra até cinco ativos e seus respectivos preços, variações e resultados do dia." /></h3>
              <div className="tabela-container">
                <table className="tabela">
                  <tbody>
                    {lista.map((p) => (
                      <tr key={p.ativo_id}>
                        <td>
                          <strong>{p.ticker}</strong>
                        </td>
                        <td className="num">
                          {moeda(p.cotacao, p.moeda)}
                          {defasada(p) && p.cotacao_data && (
                            <div>
                              <SeloCotacaoAntiga dataCotacao={p.cotacao_data} />
                            </div>
                          )}
                        </td>
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
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
