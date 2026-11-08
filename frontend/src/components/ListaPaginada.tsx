import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { api, query } from "../api";
import { lerTabela } from "../exportar";
import type { Pagina } from "../tipos";
import { invalidarDerivados } from "../cadastros";
import { CampoData } from "./CampoData";
import { useFonteExportacao } from "./Exportacao";

const POR_PAGINA = 100;
const LOTE_EXPORTACAO = 1000;
const TODAS_PAGINAS = "todas";

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
  linhaClasse?: (item: T) => string | undefined;
  filtroTicker?: boolean;
  classes?: { valor: string; rotulo: string }[];
  corretoras?: { id: number; nome: string }[];
  eventos?: { valor: string; rotulo: string }[];
  classeFiltro?: string;
  aoMudarClasse?: (valor: string) => void;
  /** Parâmetros fixos da consulta (ex.: { evento: "ALUGUEL" }). */
  filtrosFixos?: Record<string, string>;
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
  linhaClasse,
  filtroTicker = true,
  classes,
  corretoras,
  eventos,
  classeFiltro,
  aoMudarClasse,
  filtrosFixos,
}: Props<T>) {
  const [ticker, setTicker] = useState("");
  const [tamanhoPagina, setTamanhoPagina] = useState<number | typeof TODAS_PAGINAS>(POR_PAGINA);
  const [classe, setClasse] = useState("");
  const [evento, setEvento] = useState("");
  const [corretoraId, setCorretoraId] = useState("");
  const [inicio, setInicio] = useState("");
  const [fim, setFim] = useState("");
  const [pagina, setPagina] = useState(0);
  const [selecionados, setSelecionados] = useState<Set<number>>(new Set());
  const [erroExclusao, setErroExclusao] = useState<string | null>(null);
  const [carregandoTodos, setCarregandoTodos] = useState(false);
  const [resultadoExclusao, setResultadoExclusao] = useState<string | null>(null);
  const ultimaSelecao = useRef<number | null>(null);
  const cliqueComShift = useRef(false);
  const cliente = useQueryClient();
  const classeSelecionada = classeFiltro ?? classe;

  const params = {
    ...filtrosFixos,
    investidores: filtroInvestidores,
    ticker,
    ...(classes || classeFiltro !== undefined ? { classe: classeSelecionada } : {}),
    evento,
    corretora_id: corretoraId || undefined,
    inicio,
    fim,
    limite: tamanhoPagina === TODAS_PAGINAS ? LOTE_EXPORTACAO : tamanhoPagina,
    deslocamento: tamanhoPagina === TODAS_PAGINAS ? 0 : pagina * tamanhoPagina,
  };
  const { data, isFetching, error } = useQuery({
    queryKey: [recurso, params],
    queryFn: async () => {
      const primeira = await api.get<Pagina<T>>(`/${recurso}${query(params)}`);
      if (tamanhoPagina !== TODAS_PAGINAS || primeira.itens.length >= primeira.total) return primeira;
      const itens = [...primeira.itens];
      while (itens.length < primeira.total) {
        const proxima = await api.get<Pagina<T>>(`/${recurso}${query({ ...params, deslocamento: itens.length })}`);
        if (!proxima.itens.length) break;
        itens.push(...proxima.itens);
      }
      return { ...primeira, itens };
    },
    placeholderData: (anterior) => anterior,
  });
  const excluirSelecionados = useMutation({
    mutationFn: async (ids: number[]) => {
      let excluidos = 0;
      const falhas: string[] = [];
      for (const id of ids) {
        try {
          await api.del(`/${recurso}/${id}`);
          excluidos += 1;
        } catch (erro) {
          falhas.push(`${id}: ${(erro as Error).message}`);
        }
      }
      return { excluidos, falhas };
    },
    onSuccess: ({ excluidos, falhas }) => {
      cliente.invalidateQueries({ queryKey: [recurso] });
      invalidarDerivados(cliente);
      setSelecionados(new Set());
      ultimaSelecao.current = null;
      setResultadoExclusao(
        falhas.length
          ? `${excluidos} registro(s) excluído(s); ${falhas.length} falha(s): ${falhas.join("; ")}`
          : `${excluidos} registro(s) excluído(s).`,
      );
      setErroExclusao(null);
    },
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
  useEffect(() => {
    setPagina(0);
    setSelecionados(new Set());
    ultimaSelecao.current = null;
    setResultadoExclusao(null);
  }, [classeFiltro, filtroInvestidores]);
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
  const paginas = tamanhoPagina === TODAS_PAGINAS ? 1 : Math.max(1, Math.ceil(total / tamanhoPagina));
  const filtrar = (f: () => void) => {
    f();
    setPagina(0);
    setSelecionados(new Set());
    ultimaSelecao.current = null;
    cliqueComShift.current = false;
    setResultadoExclusao(null);
  };
  const alternarSelecao = (id: number) =>
    setSelecionados((atual) => {
      const proxima = new Set(atual);
      if (proxima.has(id)) proxima.delete(id);
      else proxima.add(id);
      return proxima;
    });
  const selecionar = (id: number) => {
    const idsPagina = data?.itens.map(chave) ?? [];
    const ancora = ultimaSelecao.current;
    const inicioIntervalo = ancora === null ? -1 : idsPagina.indexOf(ancora);
    const fimIntervalo = idsPagina.indexOf(id);
    if (cliqueComShift.current && inicioIntervalo >= 0 && fimIntervalo >= 0) {
      const primeiro = Math.min(inicioIntervalo, fimIntervalo);
      const ultimo = Math.max(inicioIntervalo, fimIntervalo);
      setSelecionados((atual) => new Set([...atual, ...idsPagina.slice(primeiro, ultimo + 1)]));
    } else {
      alternarSelecao(id);
    }
    cliqueComShift.current = false;
    ultimaSelecao.current = id;
  };
  const selecionarPagina = () => {
    const idsPagina = data?.itens.map(chave) ?? [];
    ultimaSelecao.current = null;
    setSelecionados((atual) =>
      idsPagina.every((id) => atual.has(id))
        ? new Set([...atual].filter((id) => !idsPagina.includes(id)))
        : new Set([...atual, ...idsPagina]),
    );
  };
  const carregarIdsFiltrados = async () => {
    const ids: number[] = [];
    for (let deslocamento = 0; ; deslocamento += LOTE_EXPORTACAO) {
      const lote = await api.get<Pagina<T>>(
        `/${recurso}${query({ ...params, limite: LOTE_EXPORTACAO, deslocamento })}`,
      );
      ids.push(...lote.itens.map(chave));
      if (!lote.itens.length || deslocamento + lote.itens.length >= lote.total) break;
    }
    return ids;
  };
  const excluirTodosFiltrados = async () => {
    setCarregandoTodos(true);
    setErroExclusao(null);
    try {
      const ids = await carregarIdsFiltrados();
      if (ids.length && confirm(`Excluir todos os ${ids.length} registro(s) de ${titulo} correspondentes aos filtros atuais?`)) {
        excluirSelecionados.mutate(ids);
      }
    } catch (erro) {
      setErroExclusao((erro as Error).message);
    } finally {
      setCarregandoTodos(false);
    }
  };

  return (
    <section>
      <div className="titulo-linha">
        <h1>{titulo}</h1>
        <div className="acoes filtros">
          {filtroTicker && (
            <input
              placeholder="Ativos (ex.: PETR4, VALE3)"
              aria-label="Filtrar por um ou mais ativos"
              value={ticker}
              onChange={(e) => filtrar(() => setTicker(e.target.value.toUpperCase()))}
            />
          )}
          {classes && (
            <select
              aria-label="Classe do ativo"
              value={classeSelecionada}
              onChange={(e) =>
                filtrar(() => (aoMudarClasse ? aoMudarClasse(e.target.value) : setClasse(e.target.value)))
              }
            >
              <option value="">Todas as classes</option>
              {classes.map((opcao) => (
                <option key={opcao.valor} value={opcao.valor}>
                  {opcao.rotulo}
                </option>
              ))}
            </select>
          )}
          {eventos && (
            <select
              aria-label="Filtrar por evento"
              value={evento}
              onChange={(e) => filtrar(() => setEvento(e.target.value))}
            >
              <option value="">Todos os eventos</option>
              {eventos.map((opcao) => (
                <option key={opcao.valor} value={opcao.valor}>
                  {opcao.rotulo}
                </option>
              ))}
            </select>
          )}
          {corretoras && (
            <label>
              Corretora
              <select
                aria-label="Filtrar por corretora"
                value={corretoraId}
                onChange={(e) => filtrar(() => setCorretoraId(e.target.value))}
              >
                <option value="">Todas as corretoras</option>
                {corretoras.map((corretora) => (
                  <option key={corretora.id} value={corretora.id}>
                    {corretora.nome}
                  </option>
                ))}
              </select>
            </label>
          )}
          <CampoData valor={inicio} aoMudar={(v) => filtrar(() => setInicio(v))} title="Data inicial" />
          <CampoData valor={fim} aoMudar={(v) => filtrar(() => setFim(v))} title="Data final" />
          {cabecalho}
        </div>
      </div>

      {topo}
      {error && <div className="erro">{(error as Error).message}</div>}
      {acoes && (
        <div className="acoes">
          <span className="sutil">{selecionados.size} selecionado(s)</span>
          <span className="sutil">Shift+clique seleciona intervalo; Ctrl/Cmd alterna linhas.</span>
          <button
            className="secundario"
            disabled={!selecionados.size || excluirSelecionados.isPending}
            onClick={() => {
              if (confirm(`Excluir ${selecionados.size} registro(s) selecionado(s) de ${titulo}?`)) {
                excluirSelecionados.mutate([...selecionados]);
              }
            }}
          >
            {excluirSelecionados.isPending ? "Excluindo…" : "Excluir selecionados"}
          </button>
          <button
            className="link perigo"
            disabled={!total || isFetching || carregandoTodos || excluirSelecionados.isPending}
            onClick={excluirTodosFiltrados}
          >
            {carregandoTodos ? "Carregando…" : `Excluir todos os ${total} filtrados`}
          </button>
          {resultadoExclusao && <span className={resultadoExclusao.includes("falha(s)") ? "negativo" : "positivo"}>{resultadoExclusao}</span>}
        </div>
      )}
      {erroExclusao && <div className="erro">{erroExclusao}</div>}
      {isFetching && <p>Carregando…</p>}

      {data && (
        <>
          <div className="tabela-container" data-exportar="ignorar">
            <table className="tabela">
              <thead>
                <tr>
                  {acoes && (
                    <th>
                      <input
                        type="checkbox"
                        aria-label="Selecionar página"
                        checked={data.itens.length > 0 && data.itens.every((item) => selecionados.has(chave(item)))}
                        onChange={selecionarPagina}
                      />
                    </th>
                  )}
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
                  <tr key={chave(item)} className={linhaClasse?.(item)}>
                    {acoes && (
                      <td>
                        <input
                          type="checkbox"
                          aria-label={`Selecionar registro ${chave(item)}`}
                          checked={selecionados.has(chave(item))}
                          onClick={(e) => {
                            cliqueComShift.current = e.shiftKey;
                          }}
                          onChange={() => selecionar(chave(item))}
                        />
                      </td>
                    )}
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
            <label>
              Linhas por página
              <select
                aria-label="Linhas por página"
                value={tamanhoPagina}
                onChange={(e) => {
                  setTamanhoPagina(e.target.value === TODAS_PAGINAS ? TODAS_PAGINAS : Number(e.target.value));
                  setPagina(0);
                  setSelecionados(new Set());
                  ultimaSelecao.current = null;
                }}
              >
                <option value={100}>100</option>
                <option value={TODAS_PAGINAS}>Todas</option>
              </select>
            </label>
            {tamanhoPagina !== TODAS_PAGINAS ? (
              <>
                <button
                  disabled={pagina === 0}
                  onClick={() => {
                    setPagina(pagina - 1);
                    ultimaSelecao.current = null;
                  }}
                >
                  ‹ Anterior
                </button>
                <span>
                  Página {pagina + 1} de {paginas} · {total} registros
                </span>
                <button
                  disabled={pagina + 1 >= paginas}
                  onClick={() => {
                    setPagina(pagina + 1);
                    ultimaSelecao.current = null;
                  }}
                >
                  Próxima ›
                </button>
              </>
            ) : (
              <span>{total} registros</span>
            )}
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
