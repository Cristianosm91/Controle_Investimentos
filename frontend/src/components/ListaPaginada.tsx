import { useQuery } from "@tanstack/react-query";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { api, query } from "../api";
import { lerTabela } from "../exportar";
import type { Pagina } from "../tipos";
import { CampoData } from "./CampoData";
import { useFonteExportacao } from "./Exportacao";

const POR_PAGINA = 100;
const LOTE_EXPORTACAO = 1000;

export interface ColunaLista<T> {
  titulo: string;
  render: (item: T) => ReactNode;
  numerica?: boolean;
}

interface Props<T> {
  titulo: string;
  recurso: string;
  filtroInvestidores: string | undefined;
  colunas: ColunaLista<T>[];
  chave: (item: T) => number;
  /** Botões à direita dos filtros (ex.: "+ Nova operação"). */
  cabecalho?: ReactNode;
  /** Conteúdo entre o título e a tabela (ex.: resumo de saldos). */
  topo?: ReactNode;
  /** Conteúdo da última coluna de cada linha (ex.: editar/excluir). */
  acoes?: (item: T) => ReactNode;
  filtroTicker?: boolean;
}

export function ListaPaginada<T>({
  titulo,
  recurso,
  filtroInvestidores,
  colunas,
  chave,
  cabecalho,
  topo,
  acoes,
  filtroTicker = true,
}: Props<T>) {
  const [ticker, setTicker] = useState("");
  const [inicio, setInicio] = useState("");
  const [fim, setFim] = useState("");
  const [pagina, setPagina] = useState(0);

  const params = { investidores: filtroInvestidores, ticker, inicio, fim, limite: POR_PAGINA, deslocamento: pagina * POR_PAGINA };
  const { data, isLoading, error } = useQuery({
    queryKey: [recurso, params],
    queryFn: () => api.get<Pagina<T>>(`/${recurso}${query(params)}`),
    placeholderData: (anterior) => anterior,
  });

  // Exportação: carrega todas as páginas do filtro atual e lê de uma tabela oculta com as mesmas colunas.
  const [completos, setCompletos] = useState<T[] | null>(null);
  const tabelaOculta = useRef<HTMLTableElement>(null);
  const aoRenderizar = useRef<((tabela: HTMLTableElement) => void) | null>(null);
  useEffect(() => {
    if (completos && tabelaOculta.current && aoRenderizar.current) {
      aoRenderizar.current(tabelaOculta.current);
      aoRenderizar.current = null;
    }
  }, [completos]);
  useFonteExportacao(async () => {
    const todos: T[] = [];
    for (let deslocamento = 0; ; ) {
      const lote = await api.get<Pagina<T>>(
        `/${recurso}${query({ ...params, limite: LOTE_EXPORTACAO, deslocamento })}`,
      );
      todos.push(...lote.itens);
      deslocamento += lote.itens.length;
      if (!lote.itens.length || deslocamento >= lote.total) break;
    }
    const tabela = await new Promise<HTMLTableElement>((resolver) => {
      aoRenderizar.current = resolver;
      setCompletos(todos);
    });
    try {
      return lerTabela(tabela, titulo);
    } finally {
      setCompletos(null);
    }
  });

  const total = data?.total ?? 0;
  const paginas = Math.max(1, Math.ceil(total / POR_PAGINA));
  const filtrar = (f: () => void) => {
    f();
    setPagina(0);
  };

  return (
    <section>
      <div className="titulo-linha">
        <h1>{titulo}</h1>
        <div className="acoes filtros">
          {filtroTicker && (
            <input placeholder="Ticker" value={ticker} onChange={(e) => filtrar(() => setTicker(e.target.value.toUpperCase()))} />
          )}
          <CampoData valor={inicio} aoMudar={(v) => filtrar(() => setInicio(v))} title="Data inicial" />
          <CampoData valor={fim} aoMudar={(v) => filtrar(() => setFim(v))} title="Data final" />
          {cabecalho}
        </div>
      </div>

      {topo}
      {error && <div className="erro">{(error as Error).message}</div>}
      {isLoading && <p>Carregando…</p>}

      {data && (
        <>
          <div className="tabela-container" data-exportar="ignorar">
            <table className="tabela">
              <thead>
                <tr>
                  {colunas.map((c) => (
                    <th key={c.titulo} className={c.numerica ? "num" : ""}>
                      {c.titulo}
                    </th>
                  ))}
                  {acoes && <th />}
                </tr>
              </thead>
              <tbody>
                {data.itens.map((item) => (
                  <tr key={chave(item)}>
                    {colunas.map((c) => (
                      <td key={c.titulo} className={c.numerica ? "num" : ""}>
                        {c.render(item)}
                      </td>
                    ))}
                    {acoes && <td className="num acoes-linha">{acoes(item)}</td>}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="paginacao">
            <button disabled={pagina === 0} onClick={() => setPagina(pagina - 1)}>
              ‹ Anterior
            </button>
            <span>
              Página {pagina + 1} de {paginas} · {total} registros
            </span>
            <button disabled={pagina + 1 >= paginas} onClick={() => setPagina(pagina + 1)}>
              Próxima ›
            </button>
          </div>
        </>
      )}

      {completos && (
        <div hidden data-exportar="ignorar">
          <table ref={tabelaOculta}>
            <thead>
              <tr>
                {colunas.map((c) => (
                  <th key={c.titulo}>{c.titulo}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {completos.map((item) => (
                <tr key={chave(item)}>
                  {colunas.map((c) => (
                    <td key={c.titulo}>{c.render(item)}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
