import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api, query } from "../api";
import { classeSinal, data, moeda, numero, percentual } from "../formato";
import { useInvestidor } from "../InvestidorContext";
import type { ItemRendaFixa, RendaFixa as TRendaFixa } from "../tipos";

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
  const nome = (id: number) => investidores.find((i) => i.id === id)?.nome ?? id;
  const itens = r?.itens ?? [];
  const proximos = itens
    .filter((i) => i.dias_para_vencer !== null && i.dias_para_vencer >= 0)
    .sort((a, b) => (a.dias_para_vencer ?? 0) - (b.dias_para_vencer ?? 0))
    .slice(0, 6);
  const rendimento = r ? r.bruto - r.custo : 0;

  return (
    <section>
      <div className="titulo-linha">
        <h1>Renda fixa</h1>
        <span className="sutil">Valor líquido de IR regressivo e IOF, por aplicação · estimativa</span>
      </div>
      {error && <div className="erro">{(error as Error).message}</div>}
      {isLoading && <p>Carregando…</p>}
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
              <span>Aplicado</span>
              <strong>{moeda(r.custo)}</strong>
            </div>
            <div className="card">
              <span>Valor bruto</span>
              <strong>{moeda(r.bruto)}</strong>
              <small className={classeSinal(rendimento)}>Rendimento {moeda(rendimento)}</small>
            </div>
            <div className="card">
              <span>IR + IOF se resgatar hoje</span>
              <strong>{moeda(r.impostos)}</strong>
            </div>
            <div className="card">
              <span>Valor líquido hoje</span>
              <strong>{moeda(r.liquido)}</strong>
              <small className="sutil">{percentual(r.bruto ? r.liquido / r.bruto : null)} do bruto</small>
            </div>
            {r.liquido_vencimento !== null && (
              <div className="card">
                <span>Líquido projetado nos vencimentos</span>
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
