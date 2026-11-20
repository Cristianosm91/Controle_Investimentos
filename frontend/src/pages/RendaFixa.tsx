import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api, query } from "../api";
import { AjudaIndicador } from "../components/AjudaIndicador";
import { classeSinal, data, moeda, numero, percentual } from "../formato";
import { useInvestidor } from "../InvestidorContext";
import type { AgendaProventos, ItemRendaFixa, RendaFixa as TRendaFixa } from "../tipos";

function Vencimento({ item }: { item: ItemRendaFixa }) {
  if (!item.data_vencimento) return <span className="sutil">—</span>;
  const dias = item.dias_para_vencer ?? 0;
  const classe = dias < 0 ? "negativo" : dias <= 30 ? "etiqueta alerta-media" : "sutil";
  return (
    <>
      {data(item.data_vencimento)}
      <div className={classe}>{dias < 0 ? `venceu há ${-dias} dia(s)` : `em ${numero(dias, 0)} dia(s)`}</div>
    </>
  );
}

export function RendaFixa() {
  const { filtro, investidores } = useInvestidor();
  const { data: r, isLoading, error } = useQuery({
    queryKey: ["renda-fixa", filtro],
    queryFn: () => api.get<TRendaFixa>(`/renda-fixa${query({ investidores: filtro })}`),
  });
  const agenda = useQuery({
    queryKey: ["agenda-proventos", filtro],
    queryFn: () => api.get<AgendaProventos>(`/proventos/agenda${query({ investidores: filtro })}`),
  });
  const nome = (id: number) => investidores.find((i) => i.id === id)?.nome ?? id;
  const itens = r?.itens ?? [];
  const proximos = itens
    .filter((i) => i.dias_para_vencer !== null && i.dias_para_vencer >= 0)
    .sort((a, b) => (a.dias_para_vencer ?? 0) - (b.dias_para_vencer ?? 0))
    .slice(0, 6);
  const rendimento = r ? r.bruto - r.custo : 0;
  const hoje = new Date().toLocaleDateString("sv-SE");
  const eventosRegistrados = [
    ...(agenda.data?.a_receber ?? []).map((item) => ({
      chave: `provento-${item.id}`,
      data: item.data_pagamento,
      ticker: item.ticker,
      investidor: nome(item.investidor_id),
      descricao: `Provento registrado · ${item.evento}`,
      valor: item.liquido,
    })),
    ...itens
      .filter((item) => item.data_vencimento && item.data_vencimento >= hoje)
      .map((item) => ({
        chave: `vencimento-${item.investidor_id}-${item.ativo_id}`,
        data: item.data_vencimento!,
        ticker: item.ticker,
        investidor: nome(item.investidor_id),
        descricao: "Vencimento cadastrado",
        valor: null,
      })),
  ].sort((a, b) => a.data.localeCompare(b.data) || a.ticker.localeCompare(b.ticker)).slice(0, 20);

  return (
    <section>
      <div className="titulo-linha">
        <h1>Renda fixa</h1>
        <span className="sutil">Valor líquido de IR regressivo e IOF, por aplicação · estimativa</span>
      </div>
      {error && <div className="erro">{(error as Error).message}</div>}
      {isLoading && <p>Carregando…</p>}
      {agenda.error && <div className="erro">{(agenda.error as Error).message}</div>}
      <div className="painel">
        <h2>Eventos futuros cadastrados</h2>
        <p className="sutil">
          Exibe pagamentos futuros registrados e datas de vencimento cadastradas. Não projeta valores para vencimentos;
          quando não há valor registrado, ele permanece em branco.
        </p>
        {eventosRegistrados.length > 0 ? (
          <div className="tabela-container">
            <table className="tabela compacta">
              <thead>
                <tr>
                  <th scope="col">Data</th>
                  <th scope="col">Evento</th>
                  <th scope="col">Ativo</th>
                  <th scope="col">Investidor</th>
                  <th scope="col" className="num">Valor registrado</th>
                </tr>
              </thead>
              <tbody>
                {eventosRegistrados.map((evento) => (
                  <tr key={evento.chave}>
                    <td>{data(evento.data)}</td>
                    <td>{evento.descricao}</td>
                    <td>{evento.ticker}</td>
                    <td>{evento.investidor}</td>
                    <td className="num">{evento.valor === null ? "Não cadastrado" : moeda(evento.valor)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="aviso">
            {agenda.isLoading ? "Carregando eventos…" : "Nenhum pagamento futuro ou vencimento cadastrado para os filtros atuais."}
          </p>
        )}
        {eventosRegistrados.some((evento) => evento.descricao.startsWith("Provento")) && (
          <p className="sutil">Valores de proventos conforme os lançamentos futuros cadastrados; não são previsões de pagamentos.</p>
        )}
      </div>
      {r && itens.length === 0 && (
        <div className="aviso">
          Nenhuma posição em ativos personalizados. Cadastre CDB, LCI, Tesouro etc. em{" "}
          <Link to="/configuracoes">Configurações → Ativos personalizados</Link> e lance as aplicações em Operações.
        </div>
      )}

      {r && itens.length > 0 && (
        <>
          <div className="cards">
            <div className="card">
              <span>Aplicado <AjudaIndicador titulo="Aplicado em renda fixa" texto="Soma dos custos das aplicações de renda fixa consideradas." /></span>
              <strong>{moeda(r.custo)}</strong>
            </div>
            <div className="card">
              <span>Valor bruto <AjudaIndicador titulo="Valor bruto" texto="Soma dos valores brutos das aplicações. O rendimento mostrado abaixo é o valor bruto menos o custo aplicado." /></span>
              <strong>{moeda(r.bruto)}</strong>
              <small className={classeSinal(rendimento)}>Rendimento {moeda(rendimento)}</small>
            </div>
            <div className="card">
              <span>IR + IOF se resgatar hoje <AjudaIndicador titulo="IR e IOF estimados" texto="Soma do IR e IOF estimados por aplicação para resgate na data atual. É uma estimativa." /></span>
              <strong>{moeda(r.impostos)}</strong>
            </div>
            <div className="card">
              <span>Valor líquido hoje <AjudaIndicador titulo="Valor líquido hoje" texto="Valor bruto das aplicações menos os impostos estimados para resgate hoje. O percentual compara o líquido com o bruto." /></span>
              <strong>{moeda(r.liquido)}</strong>
              <small className="sutil">{percentual(r.bruto ? r.liquido / r.bruto : null)} do bruto</small>
            </div>
            {r.liquido_vencimento !== null && (
              <div className="card">
                <span>Líquido projetado nos vencimentos <AjudaIndicador titulo="Líquido projetado nos vencimentos" texto="Soma das projeções líquidas dos títulos com rendimento automático e data de vencimento; não é valor garantido." /></span>
                <strong>{moeda(r.liquido_vencimento)}</strong>
                <small className="sutil">títulos com rendimento automático e vencimento</small>
              </div>
            )}
          </div>

          {proximos.length > 0 && (
            <div className="painel">
              <h3>Próximos vencimentos</h3>
              <div className="linha-tempo">
                {proximos.map((i) => (
                  <div key={`${i.investidor_id}-${i.ativo_id}`} className="linha-tempo-item">
                    <strong>{data(i.data_vencimento)}</strong>
                    <span>{i.ticker}</span>
                    <small className="sutil">
                      {i.liquido_vencimento !== null ? `≈ ${moeda(i.liquido_vencimento)} líquido` : moeda(i.liquido)}
                    </small>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="tabela-container">
            <table className="tabela">
              <thead>
                <tr>
                  <th>Ativo</th>
                  <th>Investidor</th>
                  <th>Rendimento</th>
                  <th>Vencimento</th>
                  <th className="num">Aplicado</th>
                  <th className="num">Bruto</th>
                  <th className="num">IOF</th>
                  <th className="num">IR</th>
                  <th className="num">Líquido hoje</th>
                  <th className="num">Líquido no vencimento</th>
                </tr>
              </thead>
              <tbody>
                {itens.map((i) => (
                  <tr key={`${i.investidor_id}-${i.ativo_id}`}>
                    <td>
                      <strong>{i.ticker}</strong>
                      <div className="sutil">{i.nome ?? i.classe}</div>
                    </td>
                    <td>{nome(i.investidor_id)}</td>
                    <td>
                      {i.descricao}
                      {i.isento_ir && <span className="etiqueta">isento de IR</span>}
                    </td>
                    <td>
                      <Vencimento item={i} />
                    </td>
                    <td className="num">{moeda(i.custo)}</td>
                    <td className="num">
                      {moeda(i.bruto)}
                      <div className={classeSinal(i.bruto - i.custo)}>{percentual(i.custo ? i.bruto / i.custo - 1 : null)}</div>
                    </td>
                    <td className="num">{moeda(i.iof)}</td>
                    <td className="num">
                      {moeda(i.ir)}
                      {i.aliquota_ir !== null && <div className="sutil">{percentual(i.aliquota_ir)}</div>}
                    </td>
                    <td className="num">
                      <strong>{moeda(i.liquido)}</strong>
                    </td>
                    <td className="num">{moeda(i.liquido_vencimento)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      <p className="sutil">
        IR regressivo sobre o rendimento de cada aplicação: 22,5% até 180 dias, 20% até 360, 17,5% até 720 e 15% acima. IOF regressivo
        nos primeiros 29 dias. Resgates consomem as aplicações mais antigas. A projeção no vencimento repete o último índice publicado
        (CDI, IPCA…) até a data e vale para ativos com rendimento automático. Marque LCI, LCA, CRI, CRA e poupança como isentos em
        Configurações → Ativos personalizados.
      </p>
    </section>
  );
}
