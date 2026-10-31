import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { api, query } from "../api";
import { classeSinal, data, moeda, numero, percentual } from "../formato";
import { useInvestidor } from "../InvestidorContext";
import type { Ativo, Book, Carteira, StatusAtivo as StatusAtivoTipo } from "../tipos";

type Escopo = "ativo" | "carteira" | "book";
const LIMITE = 50;

function Sinal({ valor, children }: { valor: number | null; children: React.ReactNode }) {
  return <span className={classeSinal(valor)}>{children}</span>;
}

export function StatusAtivo() {
  const { filtro, investidores } = useInvestidor();
  const nomesInvestidores = useMemo(() => new Map(investidores.map((item) => [item.id, item.nome])), [investidores]);
  const [escopo, setEscopo] = useState<Escopo>("ativo");
  const [escopoId, setEscopoId] = useState("");
  const [deslocamento, setDeslocamento] = useState(0);
  const ativos = useQuery({ queryKey: ["ativos"], queryFn: () => api.get<Ativo[]>("/ativos") });
  const carteiras = useQuery({ queryKey: ["carteiras"], queryFn: () => api.get<Carteira[]>("/carteiras") });
  const books = useQuery({ queryKey: ["books"], queryFn: () => api.get<Book[]>("/books") });

  const opcoes = useMemo(() => {
    if (escopo === "ativo") return (ativos.data ?? []).map((item) => ({ id: item.id, nome: item.ticker }));
    if (escopo === "carteira")
      return (carteiras.data ?? []).map((item) => ({ id: item.id, nome: item.nome }));
    return (books.data ?? []).map((item) => ({ id: item.id, nome: item.nome }));
  }, [ativos.data, books.data, carteiras.data, escopo]);

  useEffect(() => {
    if (opcoes.length && !opcoes.some((item) => String(item.id) === escopoId)) {
      setEscopoId(String(opcoes[0].id));
      setDeslocamento(0);
    }
  }, [escopoId, opcoes]);

  const status = useQuery({
    queryKey: ["status-ativo", escopo, escopoId, filtro, deslocamento],
    queryFn: () =>
      api.get<StatusAtivoTipo>(
        `/status${query({
          escopo,
          id: Number(escopoId),
          investidores: filtro,
          limite: LIMITE,
          deslocamento,
        })}`,
      ),
    enabled: Boolean(escopoId),
  });
  const erro = ativos.error ?? carteiras.error ?? books.error ?? status.error;
  const totalPaginas = Math.ceil((status.data?.total_eventos ?? 0) / LIMITE);
  const paginaAtual = Math.floor(deslocamento / LIMITE) + 1;

  return (
    <section className="status-ativo">
      <div className="titulo-linha">
        <h1>Status do ativo</h1>
        <span className="sutil">Visão consolidada, respeitando o filtro de investidores</span>
      </div>

      {erro && <div className="erro">{(erro as Error).message}</div>}

      <div className="painel status-filtros">
        <label>
          Analisar
          <select
            value={escopo}
            onChange={(evento) => {
              setEscopo(evento.target.value as Escopo);
              setEscopoId("");
              setDeslocamento(0);
            }}
          >
            <option value="ativo">Ativo</option>
            <option value="carteira">Carteira</option>
            <option value="book">Book</option>
          </select>
        </label>
        <label>
          {escopo === "ativo" ? "Ativo" : escopo === "carteira" ? "Carteira" : "Book"}
          <select
            value={escopoId}
            onChange={(evento) => {
              setEscopoId(evento.target.value);
              setDeslocamento(0);
            }}
            disabled={!opcoes.length}
          >
            {!opcoes.length && <option value="">Nenhuma opção cadastrada</option>}
            {opcoes.map((item) => (
              <option key={item.id} value={item.id}>
                {item.nome}
              </option>
            ))}
          </select>
        </label>
        {status.data && <span className="sutil">{status.data.ativos} ativo(s) no escopo</span>}
      </div>

      {status.isLoading && <p>Carregando status…</p>}
      {status.data && (
        <>
          <div className="status-resumo">
            <div className="painel">
              <span className="sutil">Investido</span>
              <strong>{moeda(status.data.investido)}</strong>
            </div>
            <div className="painel">
              <span className="sutil">Valor de mercado</span>
              <strong>{moeda(status.data.mercado)}</strong>
            </div>
            <div className="painel">
              <span className="sutil">Lucro aberto</span>
              <strong>
                <Sinal valor={status.data.lucro_aberto}>{moeda(status.data.lucro_aberto)}</Sinal>
              </strong>
            </div>
            <div className="painel">
              <span className="sutil">Proventos líquidos · últimos 12 meses</span>
              <strong>{moeda(status.data.proventos_12m)}</strong>
              <span className="sutil">YoC {percentual(status.data.yoc_12m)}</span>
            </div>
            <div className="painel">
              <span className="sutil">Lucro total calculado</span>
              <strong>
                <Sinal valor={status.data.lucro_total}>{moeda(status.data.lucro_total)}</Sinal>
              </strong>
            </div>
          </div>

          <div className="painel">
            <h2>Distribuição do resultado</h2>
            <div className="tabela-container">
              <table className="tabela status-distribuicao">
                <thead>
                  <tr>
                    <th>Componente</th>
                    <th className="num">Valor</th>
                  </tr>
                </thead>
                <tbody>
                  {status.data.distribuicao.map((parte) => (
                    <tr key={parte.categoria}>
                      <td>{parte.rotulo}</td>
                      <td className="num">
                        <Sinal valor={parte.valor}>{moeda(parte.valor)}</Sinal>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="painel">
            <div className="titulo-linha status-titulo-eventos">
              <h2>Linha do tempo</h2>
              <span className="sutil">{numero(status.data.total_eventos, 0)} evento(s)</span>
            </div>
            {status.data.eventos.length ? (
              <>
                <div className="tabela-container">
                  <table className="tabela status-eventos">
                    <thead>
                      <tr>
                        <th>Data</th>
                        <th>Ativo</th>
                        <th>Evento</th>
                        <th className="num">Investidor</th>
                        <th className="num">Quantidade</th>
                        <th className="num">Preço</th>
                        <th className="num">Fluxo líquido</th>
                        {escopo === "book" && <th className="num">Participação</th>}
                      </tr>
                    </thead>
                    <tbody>
                      {status.data.eventos.map((evento) => (
                        <tr key={`${evento.tipo}-${evento.id}`}>
                          <td>{data(evento.data)}</td>
                          <td>{evento.ticker}</td>
                          <td>
                            {evento.rotulo}
                            {evento.daytrade && <div className="sutil">Day trade</div>}
                          </td>
                          <td>{nomesInvestidores.get(evento.investidor_id) ?? `Investidor ${evento.investidor_id}`}</td>
                          <td className="num">{numero(evento.quantidade, 8)}</td>
                          <td className="num">{moeda(evento.preco, evento.moeda)}</td>
                          <td className="num">{moeda(evento.valor_brl)}</td>
                          {escopo === "book" && <td className="num">{percentual(evento.participacao)}</td>}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div className="status-paginacao">
                  <button
                    className="secundario"
                    disabled={deslocamento === 0}
                    onClick={() => setDeslocamento(Math.max(0, deslocamento - LIMITE))}
                  >
                    ANTERIOR
                  </button>
                  <span className="sutil">
                    Página {paginaAtual} de {totalPaginas || 1}
                  </span>
                  <button
                    className="secundario"
                    disabled={deslocamento + LIMITE >= status.data.total_eventos}
                    onClick={() => setDeslocamento(deslocamento + LIMITE)}
                  >
                    PRÓXIMA
                  </button>
                </div>
              </>
            ) : (
              <p>Nenhuma operação ou evento encontrado para este escopo e filtro de investidores.</p>
            )}
          </div>
        </>
      )}
    </section>
  );
}
