import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api, query } from "../api";
import { invalidarDerivados, useParametros } from "../cadastros";
import { chaveGrupo, Exposicao, ROTULO_DIMENSAO, somarPor, valorExposicao, type Dimensao } from "../components/Exposicao";
import { classeSinal, data, moeda, numero, percentual } from "../formato";
import { useInvestidor } from "../InvestidorContext";
import { MODELOS_VALUATION } from "../referencias";
import type {
  CaixaSaldos,
  ExposicaoCorretora,
  HistoricoValuation,
  ModeloValuation,
  Posicao,
  ResumoAluguel,
  ValorInvestido,
} from "../tipos";

const AGRUPAMENTOS: Dimensao[] = ["estrategia", "book", "carteira", "classe", "setor", "moeda"];

type Coluna = {
  chave: string;
  titulo: string;
  valor: (p: Posicao) => number | string | null;
  render: (p: Posicao) => React.ReactNode;
  numerica?: boolean;
};

const lucroAbertoPct = (p: Posicao) =>
  p.lucro_aberto !== null && p.valor_investido ? p.lucro_aberto / p.valor_investido : null;

function Sinal({ valor, children }: { valor: number | null; children: React.ReactNode }) {
  return <span className={classeSinal(valor)}>{children}</span>;
}

function colunas(total: number, nomes: Map<number, string>, porInvestidor: boolean): Coluna[] {
  const lista: Coluna[] = [
    {
      chave: "ticker",
      titulo: "Ativo",
      valor: (p) => p.ticker,
      render: (p) => (
        <div>
          <strong>{p.ticker}</strong>
          <div className="sutil texto-limitado">{p.nome}</div>
        </div>
      ),
    },
    { chave: "classe", titulo: "Classe", valor: (p) => p.classe, render: (p) => p.classe },
    {
      chave: "peso",
      titulo: "Peso",
      numerica: true,
      valor: (p) => (p.valor_mercado ?? 0) / (total || 1),
      render: (p) => percentual((p.valor_mercado ?? 0) / (total || 1)),
    },
    { chave: "quantidade", titulo: "Qtd", numerica: true, valor: (p) => p.quantidade, render: (p) => numero(p.quantidade, 8) },
    { chave: "preco_medio", titulo: "PM (R$)", numerica: true, valor: (p) => p.preco_medio, render: (p) => moeda(p.preco_medio) },
    {
      chave: "cotacao",
      titulo: "Cotação",
      numerica: true,
      valor: (p) => p.cotacao,
      render: (p) => (
        <span title={p.cotacao_fonte ? `${p.cotacao_fonte} · ${data(p.cotacao_data)}` : "sem cotação"}>
          {moeda(p.cotacao, p.moeda)}
        </span>
      ),
    },
    { chave: "custo", titulo: "Custo ajustado", numerica: true, valor: (p) => p.custo, render: (p) => moeda(p.custo) },
    { chave: "valor_mercado", titulo: "Mercado", numerica: true, valor: (p) => p.valor_mercado, render: (p) => moeda(p.valor_mercado) },
    {
      chave: "lucro_dia",
      titulo: "Lucro dia",
      numerica: true,
      valor: (p) => p.lucro_dia,
      render: (p) => (
        <Sinal valor={p.lucro_dia}>
          {moeda(p.lucro_dia)}
          <div className="sutil">{percentual(p.variacao_dia_pct)}</div>
        </Sinal>
      ),
    },
    {
      chave: "lucro_aberto",
      titulo: "Lucro aberto",
      numerica: true,
      valor: (p) => p.lucro_aberto,
      render: (p) => (
        <Sinal valor={p.lucro_aberto}>
          {moeda(p.lucro_aberto)}
          <div className="sutil">{percentual(lucroAbertoPct(p))}</div>
        </Sinal>
      ),
    },
    {
      chave: "proventos",
      titulo: "Proventos",
      numerica: true,
      valor: (p) => p.proventos,
      render: (p) => (
        <>
          {moeda(p.proventos)}
          <div className="sutil">{percentual(p.valor_investido ? p.proventos / p.valor_investido : null)}</div>
        </>
      ),
    },
    {
      chave: "yoc_12m",
      titulo: "YoC 12m",
      numerica: true,
      valor: (p) => p.yoc_12m,
      render: (p) => (
        <span title={`Proventos 12 meses: ${moeda(p.proventos_12m)}`}>{percentual(p.yoc_12m)}</span>
      ),
    },
    {
      chave: "tir_aa",
      titulo: "TIR a.a.",
      numerica: true,
      valor: (p) => p.tir_aa,
      render: (p) => <Sinal valor={p.tir_aa}>{percentual(p.tir_aa)}</Sinal>,
    },
    { chave: "subsetor", titulo: "Subsetor", valor: (p) => p.subsetor, render: (p) => <span className="sutil texto-limitado">{p.subsetor ?? "—"}</span> },
  ];
  if (porInvestidor) {
    lista.splice(1, 0, {
      chave: "investidor",
      titulo: "Investidor",
      valor: (p) => nomes.get(p.investidor_id ?? 0) ?? "",
      render: (p) => nomes.get(p.investidor_id ?? 0) ?? "—",
    });
  }
  return lista;
}

type EscolhaValuation = "" | "mediana" | "todos" | ModeloValuation["id"];

const OPCOES_VALUATION: { id: Exclude<EscolhaValuation, "">; rotulo: string }[] = [
  { id: "mediana", rotulo: "Mediana dos modelos" },
  ...MODELOS_VALUATION,
  { id: "todos", rotulo: "Todos os modelos" },
];

function precoValuation(item: HistoricoValuation | undefined, id: Exclude<EscolhaValuation, "" | "todos">) {
  const calculo = item?.calculos[0];
  if (!calculo) return null;
  return id === "mediana" ? calculo.preco_mediano : calculo.modelos[id];
}

const diferenca = (preco: number | null, cotacao: number | null) =>
  preco !== null && cotacao ? preco / cotacao - 1 : null;

function colunaValuation(
  id: Exclude<EscolhaValuation, "" | "todos">,
  titulo: string,
  valuations: Map<number, HistoricoValuation>,
  alternar: (p: Posicao) => void,
): Coluna {
  return {
    chave: `valuation-${id}`,
    titulo,
    numerica: true,
    valor: (p) => precoValuation(valuations.get(p.ativo_id), id),
    render: (p) => {
      const preco = precoValuation(valuations.get(p.ativo_id), id);
      const dif = diferenca(preco, p.cotacao);
      return (
        <button
          type="button"
          className="link valuation-celula"
          title="Clique para ver todos os modelos deste ativo"
          onClick={() => alternar(p)}
        >
          {moeda(preco, p.moeda)}
          <span className={`sutil ${classeSinal(dif)}`}>{percentual(dif)}</span>
        </button>
      );
    },
  };
}

function DetalheValuation({ p, item }: { p: Posicao; item: HistoricoValuation | undefined }) {
  const calculo = item?.calculos[0];
  if (!calculo) {
    return (
      <div className="valuation-detalhe">
        Sem valuation salvo para {p.ticker}.{" "}
        <Link to={`/valuation?ativo=${p.ativo_id}`} className="link">
          Calcular agora →
        </Link>
      </div>
    );
  }
  const linhas = [
    { rotulo: "Mediana dos modelos", preco: calculo.preco_mediano },
    ...MODELOS_VALUATION.map((m) => ({ rotulo: m.rotulo, preco: calculo.modelos[m.id] })),
  ];
  return (
    <div className="valuation-detalhe">
      <div className="sutil">
        Valuation de {p.ticker} calculado em {data(calculo.calculado_em)} {calculo.calculado_em.slice(11, 16)} ·
        cotação de então {moeda(calculo.cotacao, p.moeda)} ·{" "}
        <Link to={`/valuation?ativo=${p.ativo_id}`} className="link">
          Recalcular
        </Link>{" "}
        ·{" "}
        <Link to="/valuations-salvos" className="link">
          Histórico
        </Link>
      </div>
      <table className="tabela">
        <thead>
          <tr>
            <th>Modelo</th>
            <th className="num">Preço justo</th>
            <th className="num">Diferença vs. cotação atual</th>
          </tr>
        </thead>
        <tbody>
          {linhas.map(({ rotulo, preco }) => {
            const dif = diferenca(preco, p.cotacao);
            return (
              <tr key={rotulo}>
                <td>{rotulo}</td>
                <td className="num">{moeda(preco, p.moeda)}</td>
                <td className="num">
                  <span className={classeSinal(dif)}>{percentual(dif)}</span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function FiltroClasses({
  classes,
  excluidas,
  setExcluidas,
}: {
  classes: string[];
  excluidas: string[];
  setExcluidas: (valor: string[]) => void;
}) {
  const visiveis = classes.filter((c) => !excluidas.includes(c));
  const resumo =
    excluidas.length === 0
      ? "Todas"
      : visiveis.length <= 2
        ? visiveis.join(", ") || "Nenhuma"
        : `Todas exceto ${excluidas.join(", ")}`;
  return (
    <details className="filtro-multi">
      <summary>Classes: {resumo}</summary>
      <div className="filtro-multi-opcoes">
        {classes.map((c) => (
          <div key={c} className="filtro-multi-linha">
            <label className="check">
              <input
                type="checkbox"
                checked={!excluidas.includes(c)}
                onChange={(e) => setExcluidas(e.target.checked ? excluidas.filter((x) => x !== c) : [...excluidas, c])}
              />
              {c}
            </label>
            <button type="button" className="link" onClick={() => setExcluidas(classes.filter((x) => x !== c))}>
              só esta
            </button>
          </div>
        ))}
        <button type="button" className="link" onClick={() => setExcluidas([])} disabled={!excluidas.length}>
          Mostrar todas
        </button>
      </div>
    </details>
  );
}

export function Portfolio() {
  const { filtro, investidores } = useInvestidor();
  const [porInvestidor, setPorInvestidor] = useState(false);
  const [agrupar, setAgrupar] = useState<Dimensao | "">("");
  const [verExposicao, setVerExposicao] = useState(true);
  const [ordem, setOrdem] = useState<{ chave: string; desc: boolean }>({ chave: "classe", desc: false });
  const [classesExcluidas, setClassesExcluidas] = useState<string[]>([]);
  const [escolhaValuation, setEscolhaValuation] = useState<EscolhaValuation>("");
  const [expandidos, setExpandidos] = useState<string[]>([]);
  const cliente = useQueryClient();

  const { data: todasClasses = [], isLoading, error } = useQuery({
    queryKey: ["posicoes", filtro, porInvestidor],
    queryFn: () =>
      api.get<Posicao[]>(
        `/posicoes${query({ investidores: filtro, agrupar: porInvestidor ? "investidor" : "ativo", somente_abertas: false })}`,
      ),
  });
  const {
    data: valorInvestido,
    isLoading: carregandoInvestimento,
    error: erroInvestimento,
  } = useQuery({
    queryKey: ["valor-investido", filtro, classesExcluidas],
    queryFn: () =>
      api.get<ValorInvestido>(
        `/carteira/valor-investido${query({ investidores: filtro, classes_excluidas: classesExcluidas.join(",") })}`,
      ),
  });
  const aluguel = useQuery({
    queryKey: ["aluguel", filtro, classesExcluidas],
    queryFn: () =>
      api.get<ResumoAluguel>(
        `/aluguel${query({ investidores: filtro, classes_excluidas: classesExcluidas.join(",") })}`,
      ),
  });
  const classes = useMemo(
    () => [...new Set(todasClasses.filter((p) => p.quantidade > 0).map((p) => p.classe))].sort(),
    [todasClasses],
  );
  const filtrandoClasses = classesExcluidas.length > 0;
  const todas = useMemo(
    () => (filtrandoClasses ? todasClasses.filter((p) => !classesExcluidas.includes(p.classe)) : todasClasses),
    [todasClasses, classesExcluidas, filtrandoClasses],
  );
  const posicoes = useMemo(() => todas.filter((p) => p.quantidade > 0), [todas]);
  const { data: valuations } = useQuery({
    queryKey: ["valuation-historico"],
    queryFn: () => api.get<HistoricoValuation[]>("/valuation/historico"),
    enabled: escolhaValuation !== "" || expandidos.length > 0,
    select: (lista) => new Map(lista.map((item) => [item.ativo_id, item])),
  });
  const { data: parametros } = useParametros();
  const caixaNoPortfolio = (parametros?.caixa_no_portfolio ?? false) && !filtrandoClasses;
  const { data: caixa } = useQuery({
    queryKey: ["caixa-saldos", filtro],
    queryFn: () => api.get<CaixaSaldos>(`/caixa/saldos${query({ investidores: filtro })}`),
    enabled: caixaNoPortfolio,
  });
  const { data: corretoras } = useQuery({
    queryKey: ["exposicao-corretoras", filtro],
    queryFn: () => api.get<ExposicaoCorretora[]>(`/exposicao/corretoras${query({ investidores: filtro })}`),
    enabled: verExposicao,
    select: (lista): [string, number][] => lista.map((e) => [e.corretora, e.valor]),
  });

  const atualizar = useMutation({
    mutationFn: () => api.post<{ atualizados: Record<string, string>; sem_cotacao: string[] }>("/cotacoes/atualizar"),
    onSuccess: () => invalidarDerivados(cliente),
  });

  const totais = useMemo(() => {
    const soma = (lista: Posicao[], f: (p: Posicao) => number | null) => lista.reduce((s, p) => s + (f(p) ?? 0), 0);
    return {
      mercado: soma(posicoes, (p) => p.valor_mercado),
      custoContabil: soma(posicoes, (p) => p.custo),
      lucroDia: soma(posicoes, (p) => p.lucro_dia),
      proventos: soma(todas, (p) => p.proventos),
      swing: soma(todas, (p) => p.lucro_realizado),
      daytrade: soma(todas, (p) => p.lucro_daytrade),
      semCotacao: posicoes.filter((p) => p.valor_mercado === null).length,
    };
  }, [posicoes, todas]);
  const lucroAberto =
    totais.semCotacao > 0 || carregandoInvestimento || erroInvestimento || !valorInvestido
      ? null
      : totais.mercado - valorInvestido.valor_investido_posicoes_abertas;
  const proventosSemAluguel = totais.proventos - (aluguel.data?.totais.liquido ?? 0);
  const lucroTotal =
    lucroAberto === null || !aluguel.data
      ? null
      : lucroAberto + proventosSemAluguel + totais.swing + totais.daytrade + aluguel.data.totais.liquido;

  const nomes = useMemo(() => new Map(investidores.map((i) => [i.id, i.nome])), [investidores]);
  const chaveLinha = (p: Posicao) => `${p.investidor_id ?? 0}-${p.ativo_id}`;
  const alternarDetalhe = (p: Posicao) => {
    const chave = chaveLinha(p);
    setExpandidos((atual) => (atual.includes(chave) ? atual.filter((c) => c !== chave) : [...atual, chave]));
  };
  const mapaValuations = valuations ?? new Map<number, HistoricoValuation>();
  const colsValuation: Coluna[] =
    escolhaValuation === ""
      ? []
      : escolhaValuation === "todos"
        ? [{ id: "mediana" as const, rotulo: "Mediana" }, ...MODELOS_VALUATION].map((m) =>
            colunaValuation(m.id, m.rotulo, mapaValuations, alternarDetalhe),
          )
        : [
            colunaValuation(
              escolhaValuation,
              `Valuation · ${OPCOES_VALUATION.find((o) => o.id === escolhaValuation)?.rotulo ?? ""}`,
              mapaValuations,
              alternarDetalhe,
            ),
          ];
  const cols = [...colunas(totais.mercado, nomes, porInvestidor), ...colsValuation];

  const ordenadas = useMemo(() => {
    const col = cols.find((c) => c.chave === ordem.chave) ?? cols[0];
    return [...posicoes].sort((a, b) => {
      const va = col.valor(a);
      const vb = col.valor(b);
      const r =
        va === null ? 1 : vb === null ? -1 : typeof va === "number" && typeof vb === "number" ? va - vb : String(va).localeCompare(String(vb));
      return ordem.desc ? -r : r;
    });
  }, [posicoes, ordem, cols]);

  const ordenarPor = (chave: string) =>
    setOrdem((o) => ({ chave, desc: o.chave === chave ? !o.desc : false }));

  const grupos = useMemo(() => {
    if (!agrupar) return [{ nome: "", itens: ordenadas }];
    const mapa = new Map<string, Posicao[]>();
    for (const p of ordenadas) {
      const g = chaveGrupo(p, agrupar);
      mapa.set(g, [...(mapa.get(g) ?? []), p]);
    }
    return somarPor(posicoes, agrupar).map(([nome]) => ({ nome, itens: mapa.get(nome) ?? [] }));
  }, [agrupar, ordenadas, posicoes]);

  const linha = (p: Posicao) => [
    <tr key={chaveLinha(p)}>
      {cols.map((c) => (
        <td key={c.chave} className={c.numerica ? "num" : ""}>
          {c.render(p)}
        </td>
      ))}
      <td>
        <div className="acoes-linha">
          <Link to={`/valuation?ativo=${p.ativo_id}`} className="link" title={`Calcular o valuation de ${p.ticker}`}>
            🧮 Valuation
          </Link>
          <button
            type="button"
            className="link"
            title="Mostrar o preço justo de todos os modelos"
            onClick={() => alternarDetalhe(p)}
          >
            {expandidos.includes(chaveLinha(p)) ? "▴ Modelos" : "▾ Modelos"}
          </button>
        </div>
      </td>
    </tr>,
    ...(expandidos.includes(chaveLinha(p))
      ? [
          <tr key={`${chaveLinha(p)}-valuation`} className="linha-detalhe">
            <td colSpan={cols.length + 1}>
              {valuations ? <DetalheValuation p={p} item={valuations.get(p.ativo_id)} /> : <p>Carregando valuation…</p>}
            </td>
          </tr>,
        ]
      : []),
  ];

  const totalExposicao = useMemo(() => posicoes.reduce((s, p) => s + valorExposicao(p), 0), [posicoes]);

  const subtotal = (nome: string, itens: Posicao[]) => {
    const mercado = itens.reduce((s, p) => s + valorExposicao(p), 0);
    const investido = itens.reduce((s, p) => s + p.valor_investido, 0);
    const lucro =
      itens.some((p) => p.quantidade > 0 && p.lucro_aberto === null)
        ? null
        : itens.reduce((s, p) => s + (p.lucro_aberto ?? 0), 0);
    return (
      <tr key={`grupo-${nome}`} className="linha-grupo">
        <td colSpan={cols.length + 1}>
          <strong>{nome}</strong> · {itens.length} ativo(s) · {percentual(totalExposicao ? mercado / totalExposicao : null)} ·
          Investido {moeda(investido)} · Mercado {moeda(mercado)} ·{" "}
          <span className={classeSinal(lucro)}>Lucro aberto {moeda(lucro)}</span>
        </td>
      </tr>
    );
  };

  return (
    <section>
      <div className="titulo-linha">
        <h1>Portfólio</h1>
        <div className="acoes">
          {classes.length > 1 && (
            <FiltroClasses classes={classes} excluidas={classesExcluidas} setExcluidas={setClassesExcluidas} />
          )}
          <label className="check" title="Mostra o preço justo do último valuation salvo de cada ativo">
            Valuation
            <select
              value={escolhaValuation}
              onChange={(e) => setEscolhaValuation(e.target.value as EscolhaValuation)}
            >
              <option value="">—</option>
              {OPCOES_VALUATION.map((o) => (
                <option key={o.id} value={o.id}>
                  {o.rotulo}
                </option>
              ))}
            </select>
          </label>
          <label className="check">
            Agrupar
            <select value={agrupar} onChange={(e) => setAgrupar(e.target.value as typeof agrupar)}>
              <option value="">—</option>
              {AGRUPAMENTOS.map((d) => (
                <option key={d} value={d}>
                  {ROTULO_DIMENSAO[d]}
                </option>
              ))}
            </select>
          </label>
          <label className="check">
            <input type="checkbox" checked={verExposicao} onChange={(e) => setVerExposicao(e.target.checked)} />
            Exposição
          </label>
          <label className="check">
            <input type="checkbox" checked={porInvestidor} onChange={(e) => setPorInvestidor(e.target.checked)} />
            Separar por investidor
          </label>
          <button onClick={() => atualizar.mutate()} disabled={atualizar.isPending}>
            {atualizar.isPending ? "Atualizando…" : "↻ Atualizar cotações"}
          </button>
        </div>
      </div>

      {atualizar.data && atualizar.data.sem_cotacao.length > 0 && (
        <div className="aviso">Sem cotação: {atualizar.data.sem_cotacao.join(", ")}</div>
      )}
      {atualizar.error && <div className="erro">{(atualizar.error as Error).message}</div>}

      <div className="cards">
        <div className="card">
          <span title="Capital desembolsado que continua associado às posições abertas.">Valor investido</span>
          <strong>
            {carregandoInvestimento
              ? "Carregando…"
              : erroInvestimento
                ? "Indisponível"
                : moeda(valorInvestido?.valor_investido_posicoes_abertas ?? 0)}
          </strong>
        </div>
        <div className="card">
          <span title="O custo contábil pode incluir valores atribuídos a bonificações, cisões e outros eventos sem novo desembolso. Valor investido considera apenas o capital efetivamente desembolsado que continua aplicado.">
            Custo contábil das posições
          </span>
          <strong>{moeda(totais.custoContabil)}</strong>
        </div>
        <div className="card">
          <span>Valor atual</span>
          <strong>{moeda(totais.semCotacao > 0 ? null : totais.mercado)}</strong>
          {totais.semCotacao > 0 && <small className="sutil">{totais.semCotacao} ativo(s) sem cotação</small>}
        </div>
        {caixaNoPortfolio && caixa && (
          <div className="card">
            <span>Caixa · Patrimônio</span>
            <strong>{moeda(totais.mercado + caixa.total_brl)}</strong>
            <small className={classeSinal(caixa.total_brl)}>Saldo em caixa: {moeda(caixa.total_brl)}</small>
          </div>
        )}
        <div className="card">
          <span>Resultado das posições abertas</span>
          <strong className={classeSinal(lucroAberto)}>{moeda(lucroAberto)}</strong>
          <small className={classeSinal(lucroAberto)}>
            {percentual(
              valorInvestido?.valor_investido_posicoes_abertas && lucroAberto !== null
                ? lucroAberto / valorInvestido.valor_investido_posicoes_abertas
                : null,
            )}
          </small>
        </div>
        <div className="card">
          <span>Lucro do dia</span>
          <strong className={classeSinal(totais.lucroDia)}>{moeda(totais.lucroDia)}</strong>
        </div>
        <div className="card">
          <span>Proventos (histórico)</span>
          <strong>{moeda(proventosSemAluguel)}</strong>
        </div>
        <div className="card">
          <span title="Resultado líquido de aluguel de ações BTC; já incluído no lucro total.">Aluguel BTC</span>
          <strong className={classeSinal(aluguel.data?.totais.liquido ?? null)}>
            {aluguel.isLoading ? "Carregando…" : moeda(aluguel.data?.totais.liquido ?? null)}
          </strong>
          {aluguel.error && <small className="negativo">{(aluguel.error as Error).message}</small>}
        </div>
        <div className="card">
          <span>Swing trade realizado</span>
          <strong className={classeSinal(totais.swing)}>{moeda(totais.swing)}</strong>
        </div>
        <div className="card">
          <span>Day trade realizado</span>
          <strong className={classeSinal(totais.daytrade)}>{moeda(totais.daytrade)}</strong>
        </div>
        <div className="card">
          <span>Lucro total</span>
          <strong className={classeSinal(lucroTotal)}>{moeda(lucroTotal)}</strong>
        </div>
      </div>

      {isLoading && <p>Carregando…</p>}
      {error && <div className="erro">{(error as Error).message}</div>}
      {!isLoading && posicoes.length === 0 && <div className="aviso">Nenhuma posição aberta.</div>}

      {verExposicao && posicoes.length > 0 && (
        <Exposicao posicoes={posicoes} corretoras={filtrandoClasses ? undefined : corretoras} />
      )}

      {posicoes.length > 0 && (
        <div className="tabela-container">
          <table className="tabela">
            <thead>
              <tr>
                {cols.map((c) => (
                  <th key={c.chave} className={c.numerica ? "num" : ""} onClick={() => ordenarPor(c.chave)}>
                    {c.titulo}
                    {ordem.chave === c.chave && (ordem.desc ? " ▼" : " ▲")}
                  </th>
                ))}
                <th aria-label="Ações" />
              </tr>
            </thead>
            <tbody>{grupos.flatMap((g) => [...(g.nome ? [subtotal(g.nome, g.itens)] : []), ...g.itens.flatMap(linha)])}</tbody>
          </table>
        </div>
      )}
    </section>
  );
}
