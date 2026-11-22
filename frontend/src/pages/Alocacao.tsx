import { useQuery } from "@tanstack/react-query";
import { useDeferredValue, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api, query } from "../api";
import { AjudaIndicador } from "../components/AjudaIndicador";
import { CabecalhoAjuda } from "../components/AjudaTabela";
import { moeda, numero, percentual } from "../formato";
import { useInvestidor } from "../InvestidorContext";
import type { Alocacao as TAlocacao, GrupoAlocacao, ItemAlocacao, MetodologiaAlocacao } from "../tipos";

type Modo = "comprar" | "rebalancear";

function Desvio({ alvo, atual }: { alvo: number; atual: number }) {
  const desvio = atual - alvo;
  return <span title={desvio > 0 ? "Acima do alvo" : desvio < 0 ? "Abaixo do alvo" : undefined}>{percentual(desvio)}</span>;
}

function TabelaGrupos({ titulo, grupos }: { titulo: string; grupos: GrupoAlocacao[] }) {
  return (
    <div className="painel">
      <h3>{titulo}</h3>
      <div className="tabela-container">
        <table className="tabela">
          <thead>
            <tr>
              <th />
              <th className="num"><CabecalhoAjuda titulo="Alvo" texto="Percentual definido como objetivo para esta estratégia ou book, conforme os pesos configurados." /></th>
              <th className="num"><CabecalhoAjuda titulo="Atual" texto="Percentual da posição atual em relação ao patrimônio considerado no filtro." /></th>
              <th className="num"><CabecalhoAjuda titulo="Desvio" texto="Diferença entre o percentual atual e o alvo (atual menos alvo). Valor positivo indica acima do alvo; negativo, abaixo." /></th>
              <th className="num"><CabecalhoAjuda titulo="Valor atual" texto="Valor considerado para a posição; sem cotação disponível, a alocação usa o custo da posição." /></th>
              <th className="num"><CabecalhoAjuda titulo="Ajuste" texto="Valor sugerido para aproximar a posição do peso-alvo, considerando o aporte, o modo e as restrições do simulador." /></th>
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
                <td className="num">{moeda(g.ajuste)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function TabelaMetodologia({ metodologia, mostrarMeta }: { metodologia: MetodologiaAlocacao; mostrarMeta: boolean }) {
  const metas = metodologia.categorias.filter((categoria) => categoria.peso_alvo != null);
  return (
    <div className="painel">
      <h3>{metodologia.nome}</h3>
      <div className="tabela-container">
        <table className="tabela">
          <thead>
            <tr>
              <th scope="col">Categoria</th>
              <th scope="col" className="num"><CabecalhoAjuda titulo="Valor atual" texto="Valor atual das posições na categoria, calculado com os critérios de cotação e caixa descritos nesta tela." /></th>
              <th scope="col" className="num"><CabecalhoAjuda titulo="% atual" texto="Participação do valor da categoria no patrimônio considerado para esta metodologia." /></th>
              <th scope="col" className="num"><CabecalhoAjuda titulo="Meta" texto="Peso-alvo configurado para a categoria. As metas individuais são exibidas somente ao selecionar um investidor." /></th>
            </tr>
          </thead>
          <tbody>
            {metodologia.categorias.map((categoria) => (
              <tr key={categoria.nome}>
                <td>{categoria.nome}</td>
                <td className="num">{moeda(categoria.valor_atual)}</td>
                <td className="num">{percentual(categoria.peso_atual)}</td>
                <td className="num">{percentual(mostrarMeta ? categoria.peso_alvo : null)}</td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr>
              <th scope="row">TOTAL</th>
              <td className="num">{moeda(metodologia.total_atual)}</td>
              <td className="num">{percentual(metodologia.peso_total)}</td>
              <td className="num">{percentual(mostrarMeta && metas.length ? metas.reduce((total, categoria) => total + (categoria.peso_alvo ?? 0), 0) : null)}</td>
            </tr>
          </tfoot>
        </table>
      </div>
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
  const { filtro, selecionados } = useInvestidor();
  const [aporte, setAporte] = useState("");
  const [modo, setModo] = useState<Modo>("comprar");
  const [respeitarTeto, setRespeitarTeto] = useState(true);
  const [ordem, setOrdem] = useState("ajuste");
  const [soAjustes, setSoAjustes] = useState(false);
  const aporteAdiado = useDeferredValue(aporte);

  const { data: r, isLoading, isPlaceholderData, error } = useQuery({
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
  const metodologias =
    r && Array.isArray(r.metodologias) && r.metodologias.every((metodologia) => Array.isArray(metodologia.categorias))
      ? r.metodologias
      : null;

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
              <span>Patrimônio considerado <AjudaIndicador titulo="Patrimônio considerado" texto="Valor atual considerado pelo simulador para as posições e investidores selecionados." /></span>
              <strong>{moeda(r.total_atual)}</strong>
            </div>
            <div className="card">
              <span>Compras sugeridas <AjudaIndicador titulo="Compras sugeridas" texto="Soma dos ajustes positivos sugeridos pelo simulador, considerando o aporte, modo e restrições escolhidos." /></span>
              <strong>{moeda(compras)}</strong>
            </div>
            {modo === "rebalancear" && (
              <div className="card">
                <span>Vendas sugeridas <AjudaIndicador titulo="Vendas sugeridas" texto="Soma dos ajustes negativos sugeridos no modo de rebalanceamento." /></span>
                <strong className="negativo">{moeda(vendas)}</strong>
              </div>
            )}
            {modo === "comprar" && r.aporte > 0 && (
              <div className="card">
                <span>Aporte sem destino <AjudaIndicador titulo="Aporte sem destino" texto="Parcela do aporte que o simulador não distribuiu, por falta de déficit, cotação ou por restrição de preço-teto." /></span>
                <strong>{moeda(r.sobra)}</strong>
                <small className="sutil">Sem déficit, sem cotação ou acima do teto</small>
              </div>
            )}
          </div>

          <div className="paineis alinhado-topo alocacao-paineis">
            <div className="alocacao-estrategias">
              <TabelaGrupos titulo="Por estratégia" grupos={r.estrategias} />
              <h2>Metodologias de alocação</h2>
              {metodologias ? (
                <div className="alocacao-metodologias">
                  {metodologias.map((metodologia) => (
                    <TabelaMetodologia key={metodologia.nome} metodologia={metodologia} mostrarMeta={selecionados.length === 1 && !isPlaceholderData} />
                  ))}
                </div>
              ) : (
                <div className="aviso" role="status">
                  A API ainda não retornou os cálculos das metodologias. Reinicie a aplicação para carregar a versão atualizada e
                  recarregue esta página.
                </div>
              )}
              <p className="sutil">
                Calculado pelas posições abertas da carteira, usando o valor de mercado ou, sem cotação, o custo da posição. O
                saldo em caixa é incluído quando a opção correspondente estiver habilitada nas configurações do Portfólio. Classes
                sem classificação segura ficam em “Não classificado”; a categoria “Negócios” não é presumida. Criptoativos
                entram em Exterior na ARCA; GPUS11 entra em Exterior nas duas metodologias.
              </p>
              <p className="sutil">
                As metas são individuais e aparecem ao selecionar um único investidor. Defina-as em{" "}
                <Link to="/configuracoes?secao=metas-metodologias">Configurações → Metas ARCA e KRAKEN</Link>.
              </p>
            </div>
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
                  <th><CabecalhoAjuda titulo="Book" texto="Grupo de ativos usado para definir e acompanhar pesos-alvo dentro de cada estratégia." /></th>
                  <th><CabecalhoAjuda titulo="Carteira" texto="Carteira atribuída ao ativo para definir sua composição dentro do book; pode ficar vazia quando não houver vínculo." /></th>
                  <th className="num">Cotação</th>
                  <th className="num"><CabecalhoAjuda titulo="Preço-teto" texto="Limite de preço configurado para o ativo. Com a opção de respeitar o preço-teto ativa, o simulador não sugere compras acima desse valor." /></th>
                  <th className="num"><CabecalhoAjuda titulo="Alvo" texto="Peso-alvo do ativo, derivado da estratégia, do book e do peso definido para o ativo na carteira. Sem peso individual, o restante do book é dividido entre os ativos com posição." /></th>
                  <th className="num"><CabecalhoAjuda titulo="Atual" texto="Participação atual do ativo no patrimônio considerado pelo simulador." /></th>
                  <th className="num"><CabecalhoAjuda titulo="Desvio" texto="Diferença entre o percentual atual e o peso-alvo do ativo (atual menos alvo)." /></th>
                  <th className="num"><CabecalhoAjuda titulo="Valor atual" texto="Valor da posição considerado pelo simulador; sem cotação disponível, usa o custo da posição." /></th>
                  <th className="num"><CabecalhoAjuda titulo="Valor alvo" texto="Valor que corresponderia ao peso-alvo do ativo no patrimônio considerado." /></th>
                  <th className="num"><CabecalhoAjuda titulo="Ajuste" texto="Valor sugerido para comprar ou vender o ativo, conforme modo, aporte e restrições selecionados." /></th>
                  <th className="num"><CabecalhoAjuda titulo="Qtd" texto="Quantidade estimada a negociar a partir do ajuste e da cotação. Pode ser arredondada para baixo; na B3, é inteira." /></th>
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
                    <td className="num">{moeda(i.ajuste)}</td>
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
