import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { api, query } from "../api";
import { AcoesLinha } from "../components/AcoesLinha";
import { FormCaixa } from "../components/FormLancamentos";
import { ListaPaginada, type ColunaLista } from "../components/ListaPaginada";
import { useDominio } from "../cadastros";
import { classeSinal, data, moeda } from "../formato";
import { useInvestidor } from "../InvestidorContext";
import type { CaixaSaldos, MovCaixa } from "../tipos";

function Saldos() {
  const { filtro } = useInvestidor();
  const { data: r, error } = useQuery({
    queryKey: ["caixa-saldos", filtro],
    queryFn: () => api.get<CaixaSaldos>(`/caixa/saldos${query({ investidores: filtro })}`),
  });
  if (error) return <div className="erro">{(error as Error).message}</div>;
  if (!r) return null;
  const integrado = r.integrado_desde !== null;
  return (
    <div className="painel">
      <div className="titulo-linha">
        <h3>Saldo por corretora</h3>
        <span className="sutil">
          {integrado ? (
            <>Integra compras, vendas e proventos desde {data(r.integrado_desde)}</>
          ) : (
            <>Só movimentações lançadas</>
          )}{" "}
          · <Link to="/configuracoes">ajustar em Parâmetros</Link>
        </span>
      </div>
      {r.saldos.length === 0 ? (
        <p className="sutil">Sem movimentações.</p>
      ) : (
        <table className="tabela">
          <thead>
            <tr>
              <th>Corretora</th>
              <th>Moeda</th>
              <th className="num">Movimentações</th>
              {integrado && <th className="num">Operações</th>}
              {integrado && <th className="num">Proventos</th>}
              <th className="num">Saldo</th>
              <th className="num">Saldo (R$)</th>
            </tr>
          </thead>
          <tbody>
            {r.saldos.map((s) => (
              <tr key={`${s.corretora_id ?? 0}-${s.moeda}`}>
                <td>{s.corretora ?? <span className="sutil">Sem corretora</span>}</td>
                <td>{s.moeda}</td>
                <td className="num">{moeda(s.movimentacoes, s.moeda)}</td>
                {integrado && <td className={`num ${classeSinal(s.operacoes)}`}>{moeda(s.operacoes, s.moeda)}</td>}
                {integrado && <td className="num">{moeda(s.proventos, s.moeda)}</td>}
                <td className={`num ${classeSinal(s.saldo)}`}>{moeda(s.saldo, s.moeda)}</td>
                <td className={`num ${classeSinal(s.saldo_brl)}`}>{moeda(s.saldo_brl)}</td>
              </tr>
            ))}
            <tr className="linha-grupo">
              <td colSpan={integrado ? 6 : 4}>Total</td>
              <td className={`num ${classeSinal(r.total_brl)}`}>
                <strong>{moeda(r.total_brl)}</strong>
              </td>
            </tr>
          </tbody>
        </table>
      )}
    </div>
  );
}

export function Caixa() {
  const [parametros] = useSearchParams();
  const navegar = useNavigate();
  const { filtro, investidores } = useInvestidor();
  const { data: dominio } = useDominio();
  const [edicao, setEdicao] = useState<MovCaixa | "nova" | null>(null);
  const apontamento = parametros.get("apontamento");
  const regraQualidade = parametros.get("regra");
  const explicacaoQualidade = parametros.get("explicacao");
  const retornoQualidade = parametros.get("retorno");
  const nome = (id: number) => investidores.find((i) => i.id === id)?.nome ?? id;

  const colunas: ColunaLista<MovCaixa>[] = [
    { titulo: "Data", render: (m) => data(m.data) },
    { titulo: "Investidor", render: (m) => nome(m.investidor_id) },
    { titulo: "Evento", render: (m) => dominio?.eventos_caixa[m.evento] ?? m.evento },
    { titulo: "Valor", numerica: true, render: (m) => <span className={classeSinal(m.valor)}>{moeda(m.valor, m.moeda)}</span> },
    { titulo: "Corretora", render: (m) => m.corretora ?? "—" },
    { titulo: "Obs.", render: (m) => <span className="sutil">{m.observacao}</span> },
  ];

  return (
    <>
      <ListaPaginada<MovCaixa>
        titulo="Caixa"
        recurso="caixa"
        filtroInvestidores={filtro}
        filtroTicker={false}
        filtrosFixos={apontamento ? { apontamento } : undefined}
        colunas={colunas}
        chave={(m) => m.id}
        cabecalho={<button onClick={() => setEdicao("nova")}>+ Nova movimentação</button>}
        topo={
          <>
            {apontamento && (
              <section className="aviso">
                <strong>Movimentações de caixa relacionadas à Qualidade de Dados</strong>
                {regraQualidade && <p>Regra: {regraQualidade}</p>}
                {explicacaoQualidade && <p>{explicacaoQualidade}</p>}
                <p>Somente as movimentações vinculadas ao apontamento são exibidas. Se nenhum registro aparecer, ele pode ter sido alterado ou excluído desde a análise.</p>
                <button className="secundario" onClick={() => navegar(retornoQualidade || "/configuracoes?secao=qualidade")}>
                  VOLTAR À QUALIDADE
                </button>
                <button className="secundario" onClick={() => navegar("/caixa")}>
                  REMOVER FILTRO
                </button>
              </section>
            )}
            <Saldos />
          </>
        }
        acoes={(m) => (
          <AcoesLinha
            recurso="caixa"
            id={m.id}
            descricao={`${dominio?.eventos_caixa[m.evento] ?? m.evento} de ${moeda(m.valor, m.moeda)} em ${data(m.data)}`}
            aoEditar={() => setEdicao(m)}
          />
        )}
      />
      {edicao && <FormCaixa mov={edicao === "nova" ? undefined : edicao} aoFechar={() => setEdicao(null)} />}
    </>
  );
}