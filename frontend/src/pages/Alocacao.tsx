import { useQuery } from "@tanstack/react-query";
import { useDeferredValue, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api, query } from "../api";
import { classeSinal, moeda, numero, percentual } from "../formato";
import { useInvestidor } from "../InvestidorContext";
import type { Alocacao as TAlocacao, GrupoAlocacao, ItemAlocacao } from "../tipos";

type Modo = "comprar" | "rebalancear";

function Desvio({ alvo, atual }: { alvo: number; atual: number }) {
  const desvio = atual - alvo;
  return <span title={desvio > 0 ? "Acima do alvo" : desvio < 0 ? "Abaixo do alvo" : undefined}>{percentual(desvio)}</span>;
}

function TabelaGrupos({ titulo, grupos }: { titulo: string; grupos: GrupoAlocacao[] }) {
  return (
    <div className="painel">
      <h3>{titulo}</h3>
      <table className="tabela">
        <thead>
          <tr>
            <th />
            <th className="num">Alvo</th>
            <th className="num">Atual</th>
            <th className="num">Desvio</th>
            <th className="num">Valor atual</th>
            <th className="num">Ajuste</th>
          </tr>
        </thead>
        <tbody>
          {grupos.map((g) => (
            <tr key={g.nome}>
              <td>
                {g.nome}
                {g.estrategia && <div className="sutil">{g.estrategia}</div>}
              </td>
              <td className="num">{percentual(g.peso_alvo)}</td>
              <td className="num">{percentual(g.peso_atual)}</td>
              <td className="num">
                <Desvio alvo={g.peso_alvo} atual={g.peso_atual} />
              </td>
              <td className="num">{moeda(g.valor_atual)}</td>
              <td className={`num ${classeSinal(g.ajuste)}`}>{moeda(g.ajuste)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

const ORDENS: Record<string, { rotulo: string; chave: (i: ItemAlocacao) => number | string }> = {
  ajuste: { rotulo: "Ajuste", chave: (i) => -i.ajuste },
  desvio: { rotulo: "Desvio", chave: (i) => i.peso_atual - i.peso_alvo },
  ticker: { rotulo: "Alfabética", chave: (i) => i.ticker },
  book: { rotulo: "Book", chave: (i) => `${i.book} ${i.ticker}` },
  mercado: { rotulo: "Valor atual", chave: (i) => -i.valor_atual },
};

export function Alocacao() {
  const { filtro } = useInvestidor();
  const [aporte, setAporte] = useState("");
  const [modo, setModo] = useState<Modo>("comprar");
  const [respeitarTeto, setRespeitarTeto] = useState(true);
  const [ordem, setOrdem] = useState("ajuste");
  const [soAjustes, setSoAjustes] = useState(false);
  const aporteAdiado = useDeferredValue(aporte);

  const { data: r, isLoading, error } = useQuery({
    queryKey: ["alocacao", filtro, aporteAdiado, modo, respeitarTeto],
    queryFn: () =>
      api.get<TAlocacao>(
        `/alocacao${query({ investidores: filtro, aporte: Number(aporteAdiado || 0), modo, respeitar_teto: respeitarTeto })}`,
      ),
    placeholderData: (anterior) => anterior,
  });

  const ativos = useMemo(() => {
    const lista = (r?.ativos ?? []).filter((i) => !soAjustes || Math.abs(i.ajuste) >= 0.01);
    const chave = ORDENS[ordem].chave;
    return [...lista].sort((a, b) => {
      const va = chave(a);
      const vb = chave(b);
      return typeof va === "number" && typeof vb === "number" ? va - vb : String(va).localeCompare(String(vb));
    });
  }, [r, ordem, soAjustes]);

  const compras = (r?.ativos ?? []).filter((i) => i.ajuste > 0).reduce((s, i) => s + i.ajuste, 0);
  const vendas = (r?.ativos ?? []).filter((i) => i.ajuste < 0).reduce((s, i) => s + i.ajuste, 0);

  return (
    <section>
      <div className="titulo-linha">
        <h1>Alocação & Rebalanceamento</h1>
        <span className="sutil">
          Pesos-alvo em <Link to="/configuracoes">Configurações</Link> (Estratégias & Books e Carteiras)
        </span>
      </div>

      <form className="formulario simulador" onSubmit={(e) => e.preventDefault()}>
        <h3>Simulador</h3>
        <label>
          Aporte (R$)
          <input type="number" step="any" min="0" value={aporte} onChange={(e) => setAporte(e.target.value)} />
        </label>
        <label>
          Modo
          <select value={modo} onChange={(e) => setModo(e.target.value as Modo)}>
            <option value="comprar">Só comprar (distribui o aporte)</option>
            <option value="rebalancear">Comprar e vender (rebalanceamento completo)</option>
          </select>
        </label>
        <label className="check">
          <input type="checkbox" checked={respeitarTeto} onChange={(e) => setRespeitarTeto(e.target.checked)} />
          Não comprar acima do preço-teto
        </label>
      </form>

      {error && <div className="erro">{(error as Error).message}</div>}
      {isLoading && <p>Calculando…</p>}
      {r?.avisos.map((a) => (
        <div key={a} className="aviso">
          {a}
        </div>
      ))}

      {r && (
        <>
          <div className="cards">
            <div className="card">
              <span>Patrimônio considerado</span>
              <strong>{moeda(r.total_atual)}</strong>
            </div>
            <div className="card">
              <span>Compras sugeridas</span>
              <strong className={classeSinal(compras)}>{moeda(compras)}</strong>
            </div>
            {modo === "rebalancear" && (
              <div className="card">
                <span>Vendas sugeridas</span>
                <strong className="negativo">{moeda(vendas)}</strong>
              </div>
            )}
            {modo === "comprar" && r.aporte > 0 && (
              <div className="card">
                <span>Aporte sem destino</span>
                <strong>{moeda(r.sobra)}</strong>
                <small className="sutil">Sem déficit, sem cotação ou acima do teto</small>
              </div>
            )}
          </div>

          <div className="paineis alinhado-topo">
            <TabelaGrupos titulo="Por estratégia" grupos={r.estrategias} />
            <TabelaGrupos titulo="Por book" grupos={r.books.filter((b) => b.peso_alvo > 0 || b.valor_atual > 0)} />
          </div>

          <div className="titulo-linha">
            <h2>Por ativo</h2>
            <div className="acoes">
              <label className="check">
                Ordenar
                <select value={ordem} onChange={(e) => setOrdem(e.target.value)}>
                  {Object.entries(ORDENS).map(([k, o]) => (
                    <option key={k} value={k}>
                      {o.rotulo}
                    </option>
                  ))}
                </select>
              </label>
              <label className="check">
                <input type="checkbox" checked={soAjustes} onChange={(e) => setSoAjustes(e.target.checked)} />
                Só com ajuste
              </label>
            </div>
          </div>
          <div className="tabela-container">
            <table className="tabela">
              <thead>
                <tr>
                  <th>Ativo</th>
                  <th>Book</th>
                  <th>Carteira</th>
                  <th className="num">Cotação</th>
                  <th className="num">Preço-teto</th>
                  <th className="num">Alvo</th>
                  <th className="num">Atual</th>
                  <th className="num">Desvio</th>
                  <th className="num">Valor atual</th>
                  <th className="num">Valor alvo</th>
                  <th className="num">Ajuste</th>
                  <th className="num">Qtd</th>
                </tr>
              </thead>
              <tbody>
                {ativos.map((i) => (
                  <tr key={i.ativo_id}>
                    <td>
                      <strong>{i.ticker}</strong>
                      <div className="sutil">{i.nome}</div>
                    </td>
                    <td>{i.book}</td>
                    <td>{i.carteira ?? <span className="sutil">—</span>}</td>
                    <td className="num">{moeda(i.cotacao, i.moeda)}</td>
                    <td className={`num ${i.acima_teto ? "negativo" : ""}`} title={i.acima_teto ? "Cotação acima do preço-teto" : undefined}>
                      {moeda(i.preco_teto, i.moeda)}
                    </td>
                    <td className="num">{percentual(i.peso_alvo)}</td>
                    <td className="num">{percentual(i.peso_atual)}</td>
                    <td className="num">
                      <Desvio alvo={i.peso_alvo} atual={i.peso_atual} />
                    </td>
                    <td className="num">{moeda(i.valor_atual)}</td>
                    <td className="num">{moeda(i.valor_alvo)}</td>
                    <td className={`num ${classeSinal(i.ajuste)}`}>{moeda(i.ajuste)}</td>
                    <td className="num">{i.quantidade ? numero(i.quantidade, 4) : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="sutil">
            Alvo do ativo = estratégia × book × peso no book (carteira) — sem peso definido, o restante do book é dividido igualmente entre
            os ativos com posição. Quantidade arredondada para baixo (inteira na B3). Ativo sem cotação usa o custo como valor atual.
          </p>
        </>
      )}
    </section>
  );
}
