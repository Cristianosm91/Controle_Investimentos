import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Fragment, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { useExclusaoEmLote } from "../components/ExclusaoEmLote";
import { classeSinal, data, moeda, numero, percentual } from "../formato";
import { MODELOS_VALUATION as MODELOS } from "../referencias";
import type { CalculoValuation, HistoricoValuation, PremissasValuation } from "../tipos";
import "./Valuation.css";

const ROTULOS_CALCULO = ["Último cálculo", "Anterior", "Anterior (2)"];
const PREMISSAS_HISTORICO: { chave: keyof PremissasValuation; rotulo: string; percentual?: boolean }[] = [
  { chave: "lpa", rotulo: "LPA" },
  { chave: "vpa", rotulo: "VPA" },
  { chave: "dividendo_anual", rotulo: "Dividendo anual" },
  { chave: "roe", rotulo: "ROE", percentual: true },
  { chave: "payout", rotulo: "Payout", percentual: true },
  { chave: "g", rotulo: "Crescimento perpétuo (g)", percentual: true },
  { chave: "ke", rotulo: "Custo de capital próprio (Ke)", percentual: true },
  { chave: "pl_historico", rotulo: "P/L histórico" },
  { chave: "pl_setor", rotulo: "P/L do setor" },
  { chave: "fcfe_1", rotulo: "FCFE por ação · ano 1" },
  { chave: "fcfe_2", rotulo: "FCFE por ação · ano 2" },
  { chave: "fcfe_3", rotulo: "FCFE por ação · ano 3" },
  { chave: "fcfe_4", rotulo: "FCFE por ação · ano 4" },
  { chave: "fcfe_5", rotulo: "FCFE por ação · ano 5" },
];

function dataHora(iso: string): string {
  return `${data(iso)} ${iso.slice(11, 16)}`;
}

function Calculo({ calculo, moedaAtivo, anterior }: { calculo?: CalculoValuation; moedaAtivo: string; anterior?: boolean }) {
  if (!calculo) return <span className="sutil">—</span>;
  return (
    <div className={anterior ? "valuation-anterior" : undefined}>
      <strong>{moeda(calculo.preco_mediano, moedaAtivo)}</strong>
      <div className="sutil">{dataHora(calculo.calculado_em)}</div>
      <div className="sutil">
        Cotação {moeda(calculo.cotacao, moedaAtivo)} ·{" "}
        <span className={classeSinal(calculo.upside)}>{percentual(calculo.upside)}</span>
      </div>
    </div>
  );
}

export function ValuationsSalvos() {
  const cliente = useQueryClient();
  const [aberto, setAberto] = useState<number | null>(null);
  const historico = useQuery({
    queryKey: ["valuation-historico"],
    queryFn: () => api.get<HistoricoValuation[]>("/valuation/historico"),
  });
  const remover = useMutation({
    mutationFn: (ativoId: number) => api.del(`/valuation/${ativoId}/historico`),
    onSuccess: () => cliente.invalidateQueries({ queryKey: ["valuation-historico"] }),
  });
  const selecao = useExclusaoEmLote({
    itens: historico.data ?? [],
    chave: (item) => item.ativo_id,
    remover: (id) => api.del(`/valuation/${id}/historico`),
    titulo: "valuations salvos",
    consulta: "valuation-historico",
    aposExcluir: () => cliente.invalidateQueries({ queryKey: ["valuation-historico"] }),
  });
  const erro = historico.error ?? remover.error;

  return (
    <section className="valuation">
      <div className="titulo-linha">
        <h1>Valuations salvos</h1>
        <span className="sutil">Último cálculo de cada ativo e os dois anteriores; não constituem recomendação</span>
        <Link to="/valuation" className="link">
          Calcular novo →
        </Link>
      </div>

      {erro && <div className="erro">{(erro as Error).message}</div>}
      {selecao.acoes}
      {historico.isLoading && <p>Carregando…</p>}
      {historico.data?.length === 0 && (
        <div className="aviso">
          Nenhum valuation salvo ainda. Calcule em <Link to="/valuation">Valuation</Link> e clique em “Calcular e
          salvar”.
        </div>
      )}

      {!!historico.data?.length && (
        <div className="painel">
          <div className="tabela-container">
            <table className="tabela valuation-historico">
              <thead>
                <tr>
                  <th />
                  <th>Ativo</th>
                  <th className="num">Cotação atual</th>
                  <th className="num">Diferença hoje</th>
                  {ROTULOS_CALCULO.map((rotulo) => (
                    <th key={rotulo}>{rotulo}</th>
                  ))}
                  <th aria-label="Ações" />
                </tr>
              </thead>
              <tbody>
                {historico.data.map((item) => (
                  <Fragment key={item.ativo_id}>
                    <tr>
                      <td>{selecao.checkbox(item.ativo_id)}</td>
                      <td>
                        <strong>{item.ticker}</strong>
                        <div className="sutil texto-limitado">{item.nome ?? item.classe}</div>
                      </td>
                      <td className="num">
                        {moeda(item.cotacao, item.moeda)}
                        <div className="sutil">{data(item.cotacao_data)}</div>
                      </td>
                      <td className="num">
                        <strong className={classeSinal(item.upside_atual)}>{percentual(item.upside_atual)}</strong>
                        <div className="sutil">vs. último preço justo</div>
                      </td>
                      {ROTULOS_CALCULO.map((rotulo, indice) => (
                        <td key={rotulo}>
                          <Calculo calculo={item.calculos[indice]} moedaAtivo={item.moeda} anterior={indice > 0} />
                        </td>
                      ))}
                      <td>
                        <div className="acoes-linha">
                          <Link to={`/valuation?ativo=${item.ativo_id}`} className="link">
                            Recalcular
                          </Link>
                          <button
                            className="link"
                            onClick={() => setAberto(aberto === item.ativo_id ? null : item.ativo_id)}
                          >
                            {aberto === item.ativo_id ? "Ocultar detalhes" : "Ver detalhes"}
                          </button>
                          <button
                            className="link perigo"
                            disabled={remover.isPending}
                            onClick={() =>
                              confirm(`Remover o histórico de valuation de ${item.ticker}?`) &&
                              remover.mutate(item.ativo_id)
                            }
                          >
                            Remover
                          </button>
                        </div>
                      </td>
                    </tr>
                    {aberto === item.ativo_id && (
                      <tr>
                        <td colSpan={7}>
                          <table className="tabela valuation-modelos">
                            <thead>
                              <tr>
                                <th>Modelo</th>
                                {item.calculos.map((calculo) => (
                                  <th key={calculo.calculado_em} className="num">
                                    {dataHora(calculo.calculado_em)}
                                  </th>
                                ))}
                              </tr>
                            </thead>
                            <tbody>
                              {MODELOS.map((modelo) => (
                                <tr key={modelo.id}>
                                  <td>{modelo.rotulo}</td>
                                  {item.calculos.map((calculo) => (
                                    <td key={calculo.calculado_em} className="num">
                                      {moeda(calculo.modelos[modelo.id], item.moeda)}
                                    </td>
                                  ))}
                                </tr>
                              ))}
                              <tr>
                                <td>Modelos calculáveis</td>
                                {item.calculos.map((calculo) => (
                                  <td key={calculo.calculado_em} className="num">
                                    {numero(calculo.modelos_disponiveis, 0)} / {MODELOS.length}
                                  </td>
                                ))}
                              </tr>
                            </tbody>
                          </table>
                          <h3>Premissas usadas em cada cálculo</h3>
                          <table className="tabela valuation-modelos">
                            <thead>
                              <tr>
                                <th>Premissa</th>
                                {item.calculos.map((calculo) => (
                                  <th key={calculo.calculado_em} className="num">
                                    {dataHora(calculo.calculado_em)}
                                  </th>
                                ))}
                              </tr>
                            </thead>
                            <tbody>
                              {PREMISSAS_HISTORICO.map(({ chave, rotulo, percentual: ehPercentual }) => (
                                <tr key={chave}>
                                  <td>{rotulo}</td>
                                  {item.calculos.map((calculo) => {
                                    const valor = calculo.premissas[chave];
                                    return (
                                      <td key={calculo.calculado_em} className="num">
                                        {valor === null
                                          ? "—"
                                          : ehPercentual
                                            ? percentual(valor)
                                            : numero(valor)}
                                      </td>
                                    );
                                  })}
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </td>
                      </tr>
                    )}
                  </Fragment>
                ))}
              </tbody>
            </table>
          </div>
          <p className="sutil valuation-ajuda">
            O preço justo é a mediana dos modelos calculáveis em cada cálculo. “Diferença hoje” compara o último preço
            justo com a cotação mais recente; a diferença de cada cálculo usa a cotação vigente naquele momento.
            Premissas de cálculos anteriores à atualização podem aparecer como “—”.
          </p>
        </div>
      )}
    </section>
  );
}
