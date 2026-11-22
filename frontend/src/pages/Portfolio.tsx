import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api, ErroApi, query } from "../api";
import { invalidarDerivados, useAtivos, useParametros } from "../cadastros";
import { chaveGrupo, Exposicao, ROTULO_DIMENSAO, somarPor, valorExposicao, type Dimensao } from "../components/Exposicao";
import { AjudaTabela } from "../components/AjudaTabela";
import { SeloCotacaoAntiga } from "../components/SeloCotacaoAntiga";
import { AjudaIndicador } from "../components/AjudaIndicador";
import { margemSeguranca, precoReferencia, SeletorReferenciaValuation, type ReferenciaValuation } from "../components/ReferenciaValuation";
import { cotacaoDesatualizada } from "../cotacao";
import { classeSinal, data, moeda, numero, percentual } from "../formato";
import { useInvestidor } from "../InvestidorContext";
import { MODELOS_VALUATION } from "../referencias";
import type {
  CaixaSaldos,
  ExposicaoCorretora,
  HistoricoValuation,
  MetodologiaAlocacao,
  Posicao,
  ResumoAluguel,
  ValorInvestido,
} from "../tipos";

const AGRUPAMENTOS: Dimensao[] = ["estrategia", "book", "carteira", "classe", "setor", "moeda"];
const AJUDAS_COLUNAS: Record<string, string> = {
  peso: "Valor de mercado da posição dividido pelo valor de mercado total das posições consideradas.",
  preco_medio: "Preço médio contábil da posição calculado a partir das operações e dos ajustes registrados.",
  custo: "Custo contábil atual da posição, calculado a partir das operações registradas e dos ajustes aplicáveis.",
  valor_mercado: "Valor atual da posição pela cotação disponível. Se não houver cotação, o valor fica indisponível.",
  lucro_aberto: "Diferença entre o valor de mercado atual das posições e o custo contábil das posições abertas.",
  lucro_dia: "Variação do valor de mercado no dia, estimada pela variação percentual da cotação. Fica indisponível sem cotação ou variação diária.",
  proventos: "Proventos líquidos registrados para o ativo; o percentual abaixo compara esse valor ao capital investido.",
  aluguel: "Soma dos rendimentos líquidos registrados como aluguel para este ativo. O percentual é dividido pelo capital investido.",
  yoc_12m: "Proventos líquidos pagos nos últimos 365 dias divididos pelo custo contábil atual da posição.",
  tir_aa: "TIR anualizada calculada a partir das operações, dos proventos líquidos (incluindo aluguel) e do valor de mercado atual como valor final.",
  margem: "Diferença percentual entre o preço justo de referência selecionado e a cotação atual.",
};

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

function colunas(total: number, nomes: Map<number, string>, porInvestidor: boolean, defasadas: Set<number>): Coluna[] {
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
    {
      chave: "preco_medio",
      titulo: "PM (R$)",
      numerica: true,
      valor: (p) => p.preco_medio,
      render: (p) => {
        const pmComRenda = p.quantidade
          ? p.preco_medio - (p.proventos + p.aluguel) / p.quantidade
          : null;
        return (
          <>
            <strong>{moeda(p.preco_medio)}</strong>
            <div className="sutil" title="PM descontando proventos e aluguel líquidos recebidos">
              c/ renda {moeda(pmComRenda)}
            </div>
          </>
        );
      },
    },
    {
      chave: "cotacao",
      titulo: "Cotação",
      numerica: true,
      valor: (p) => p.cotacao,
      render: (p) => (
        <>
          <span title={p.cotacao_fonte ? `${p.cotacao_fonte} · ${data(p.cotacao_data)}` : "sem cotação"}>
            {moeda(p.cotacao, p.moeda)}
          </span>
          {defasadas.has(p.ativo_id) && p.cotacao_data && (
            <div>
              <SeloCotacaoAntiga dataCotacao={p.cotacao_data} />
            </div>
          )}
        </>
      ),
    },
    {
      chave: "custo",
      titulo: "Custo ajustado",
      numerica: true,
      valor: (p) => p.custo,
      render: (p) => (
        <>
          <strong>{moeda(p.custo)}</strong>
          <div
            className="sutil"
            title="Desembolso ainda associado à posição, conforme as operações registradas"
          >
            Capital investido {moeda(p.valor_investido)}
          </div>
        </>
      ),
    },
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
      chave: "aluguel",
      titulo: "Aluguel",
      numerica: true,
      valor: (p) => p.aluguel,
      render: (p) => (
        <>
          {moeda(p.aluguel)}
          <div className="sutil">{percentual(p.valor_investido ? p.aluguel / p.valor_investido : null)}</div>
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
    { chave: "setor", titulo: "Setor", valor: (p) => p.setor, render: (p) => <span className="sutil texto-limitado">{p.setor ?? "—"}</span> },
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

type AbaPortfolio = "Resumo" | "Rentabilidade" | "Proventos" | "Valuation";
const COLUNAS_ABAS: Record<Exclude<AbaPortfolio, "Valuation">, string[]> = {
  Resumo: ["ticker", "investidor", "classe", "setor", "peso", "quantidade", "cotacao", "valor_mercado"],
  Rentabilidade: ["ticker", "investidor", "classe", "quantidade", "preco_medio", "custo", "valor_mercado", "lucro_dia", "lucro_aberto", "tir_aa"],
  Proventos: ["ticker", "investidor", "classe", "quantidade", "preco_medio", "proventos", "aluguel", "yoc_12m"],
};

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
  const [aba, setAba] = useState<AbaPortfolio>("Resumo");
  const [referencia, setReferencia] = useState<ReferenciaValuation>("media");
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
  const { data: valuations, isLoading: carregandoValuations, error: erroValuations } = useQuery({
    queryKey: ["valuation-historico"],
    queryFn: () => api.get<HistoricoValuation[]>("/valuation/historico"),
    enabled: aba === "Valuation",
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
  const metodologias = useQuery({
    queryKey: ["alocacao", "metodologias", filtro, classesExcluidas],
    queryFn: () =>
      api.get<MetodologiaAlocacao[]>(
        `/alocacao/metodologias${query({ investidores: filtro, classes_excluidas: classesExcluidas.join(",") })}`,
      ),
    enabled: verExposicao && posicoes.length > 0,
    retry: false,
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
  const lucroTotal =
    lucroAberto === null || !aluguel.data
      ? null
      : lucroAberto + totais.proventos + totais.swing + totais.daytrade + aluguel.data.totais.liquido;

  const nomes = useMemo(() => new Map(investidores.map((i) => [i.id, i.nome])), [investidores]);
  const { data: ativosCadastro } = useAtivos();
  // Só ativos com cotação automática; sem o cadastro carregado, nada é sinalizado (evita falso alerta).
  const defasadas = useMemo(() => {
    const automaticos = new Set((ativosCadastro ?? []).filter((a) => a.cotacao_automatica).map((a) => a.id));
    return new Set(
      posicoes
        .filter((p) => automaticos.has(p.ativo_id) && cotacaoDesatualizada(p.cotacao_data, p.classe))
        .map((p) => p.ativo_id),
    );
  }, [ativosCadastro, posicoes]);
  const tickersDefasados = useMemo(
    () => [...new Set(posicoes.filter((p) => defasadas.has(p.ativo_id)).map((p) => p.ticker))].sort(),
    [posicoes, defasadas],
  );
  const chaveLinha = (p: Posicao) => `${p.investidor_id ?? 0}-${p.ativo_id}`;
  const mapaValuations = valuations ?? new Map<number, HistoricoValuation>();
  const colunasBase = colunas(totais.mercado, nomes, porInvestidor, defasadas);
  const cols: Coluna[] = aba === "Valuation"
    ? [
        ...colunasBase.filter((coluna) => ["ticker", "investidor", "classe", "cotacao"].includes(coluna.chave)),
        ...MODELOS_VALUATION.map((modelo): Coluna => ({
          chave: `valuation-${modelo.id}`,
          titulo: modelo.rotulo,
          numerica: true,
          valor: (p) => mapaValuations.get(p.ativo_id)?.calculos[0]?.modelos[modelo.id] ?? null,
          render: (p) => moeda(mapaValuations.get(p.ativo_id)?.calculos[0]?.modelos[modelo.id] ?? null, p.moeda),
        })),
        {
          chave: "margem",
          titulo: "Margem de segurança",
          numerica: true,
          valor: (p) => margemSeguranca(precoReferencia(mapaValuations.get(p.ativo_id)?.calculos[0], referencia), p.cotacao),
          render: (p) => {
            const margem = margemSeguranca(precoReferencia(mapaValuations.get(p.ativo_id)?.calculos[0], referencia), p.cotacao);
            return <span className={classeSinal(margem)}>{percentual(margem)}</span>;
          },
        },
      ]
    : colunasBase.filter((coluna) => COLUNAS_ABAS[aba].includes(coluna.chave));

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

  const linha = (p: Posicao) => (
    <tr key={chaveLinha(p)}>
      {cols.map((c) => {
        const valor = c.valor(p);
        const indisponivel = valor === null || valor === "—";
        const motivoCotacaoAusente =
          c.chave === "valor_mercado" && p.valor_mercado === null && p.cotacao === null;
        return (
          <td key={c.chave} className={[c.numerica ? "num" : "", indisponivel ? "indisponivel" : ""].filter(Boolean).join(" ")}>
            {motivoCotacaoAusente ? (
              <AjudaTabela
                label={`Motivo da indisponibilidade de Mercado para ${p.ticker}`}
                texto={<><strong>Valor indisponível</strong><br />A cotação atual do ativo não está disponível.</>}
                classe="portfolio-ajuda-valor"
              >
                —
              </AjudaTabela>
            ) : c.render(p)}
          </td>
        );
      })}
      {aba === "Valuation" && (
        <td className="portfolio-acoes-celula">
          <details className="portfolio-acoes">
            <summary role="button" aria-label={`Ações de ${p.ticker}`} title={`Ações de ${p.ticker}`}>
              <span aria-hidden="true">⋯</span>
            </summary>
            <div className="portfolio-acoes-menu">
              <Link to={`/novo-valuation?ativo=${p.ativo_id}`} onClick={(evento) => evento.currentTarget.closest("details")?.removeAttribute("open")}>
                Abrir valuation
              </Link>
            </div>
          </details>
        </td>
      )}
    </tr>
  );

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
        <td colSpan={cols.length + (aba === "Valuation" ? 1 : 0)}>
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

      <div className="cards cards-portfolio">
        <div className="card">
          <span>Valor investido <AjudaIndicador titulo="Valor investido" texto="Capital efetivamente desembolsado que permanece associado às posições abertas, considerando os investidores e classes selecionados." /></span>
          <strong>
            {carregandoInvestimento
              ? "Carregando…"
              : erroInvestimento
                ? "Indisponível"
                : moeda(valorInvestido?.valor_investido_posicoes_abertas ?? 0)}
          </strong>
        </div>
        <div className="card">
          <span>
            Custo contábil das <span className="ajuda-indicador-grupo">posições <AjudaIndicador titulo="Custo contábil das posições" texto="Soma do custo das posições abertas. Pode incluir valores atribuídos a bonificações, cisões e outros eventos sem novo desembolso, diferindo do valor investido." /></span>
          </span>
          <strong>{moeda(totais.custoContabil)}</strong>
        </div>
        <div className="card">
          <span>Valor atual <AjudaIndicador titulo="Valor atual" texto="Soma dos valores de mercado das posições abertas. Fica indisponível se algum ativo não tiver cotação." /></span>
          <strong>{moeda(totais.semCotacao > 0 ? null : totais.mercado)}</strong>
          {totais.semCotacao > 0 && <small className="sutil">{totais.semCotacao} ativo(s) sem cotação</small>}
        </div>
        {caixaNoPortfolio && caixa && (
          <div className="card">
            <span>Caixa · Patrimônio <AjudaIndicador titulo="Caixa e patrimônio" texto="Soma do valor de mercado disponível das posições e do saldo de caixa convertido em reais. Abaixo aparece o saldo em caixa." /></span>
            <strong>{moeda(totais.mercado + caixa.total_brl)}</strong>
            <small className={classeSinal(caixa.total_brl)}>Saldo em caixa: {moeda(caixa.total_brl)}</small>
          </div>
        )}
        <div className="card">
          <span>Resultado das posições <span className="ajuda-indicador-grupo">abertas <AjudaIndicador titulo="Resultado das posições abertas" texto="Valor atual menos o capital efetivamente investido nas posições abertas. O percentual divide esse resultado pelo valor investido. Indisponível quando falta cotação ou investimento." /></span></span>
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
          <span>Lucro do dia <AjudaIndicador titulo="Lucro do dia" texto="Soma das variações diárias em reais das posições abertas com informação disponível." /></span>
          <strong className={classeSinal(totais.lucroDia)}>{moeda(totais.lucroDia)}</strong>
        </div>
        <div className="card">
          <span>Proventos (histórico) <AjudaIndicador titulo="Proventos histórico" texto="Soma dos proventos líquidos das posições, inclusive posições encerradas, respeitando os filtros." /></span>
          <strong>{moeda(totais.proventos)}</strong>
        </div>
        <div className="card">
          <span>Aluguel BTC <AjudaIndicador titulo="Aluguel BTC" texto="Resultado líquido histórico dos lançamentos de aluguel de ações, já incluído no lucro total." /></span>
          <strong className={classeSinal(aluguel.data?.totais.liquido ?? null)}>
            {aluguel.isLoading ? "Carregando…" : moeda(aluguel.data?.totais.liquido ?? null)}
          </strong>
          {aluguel.error && <small className="negativo">{(aluguel.error as Error).message}</small>}
        </div>
        <div className="card">
          <span>Swing trade realizado <AjudaIndicador titulo="Swing trade realizado" texto="Soma dos resultados realizados em operações que não são day trade, inclusive posições encerradas." /></span>
          <strong className={classeSinal(totais.swing)}>{moeda(totais.swing)}</strong>
        </div>
        <div className="card">
          <span>Day trade realizado <AjudaIndicador titulo="Day trade realizado" texto="Soma dos resultados realizados em operações de day trade, inclusive posições encerradas." /></span>
          <strong className={classeSinal(totais.daytrade)}>{moeda(totais.daytrade)}</strong>
        </div>
        <div className="card">
          <span>Lucro total <AjudaIndicador titulo="Lucro total" texto="Resultado das posições abertas + proventos históricos + swing trade + day trade + aluguel BTC líquido. Depende de cotação, investimento e dados de aluguel disponíveis." /></span>
          <strong className={classeSinal(lucroTotal)}>{moeda(lucroTotal)}</strong>
        </div>
      </div>

      {isLoading && <p>Carregando…</p>}
      {error && <div className="erro">{(error as Error).message}</div>}
      {!isLoading && posicoes.length === 0 && <div className="aviso">Nenhuma posição aberta.</div>}

      {verExposicao && posicoes.length > 0 && (
        <>
          <Exposicao posicoes={posicoes} corretoras={filtrandoClasses ? undefined : corretoras} metodologias={metodologias.error ? undefined : metodologias.data} />
          {metodologias.data && !metodologias.error && (
            <p className="sutil">
              As metas são individuais e aparecem ao selecionar um único investidor. Defina-as em{" "}
              <Link to="/configuracoes?secao=metas-metodologias">Configurações → Metas ARCA e KRAKEN</Link>.
              {filtrandoClasses && " O percentual atual considera as classes visíveis; as metas permanecem iguais."}
            </p>
          )}
          {metodologias.isLoading && <p>Carregando exposições ARCA e KRAKEN…</p>}
          {metodologias.error && (
            <div className="erro">
              {metodologias.error instanceof ErroApi && metodologias.error.status === 404
                ? "Não foi possível carregar ARCA e KRAKEN. Atualize e reinicie o servidor da aplicação."
                : `Não foi possível carregar ARCA e KRAKEN: ${metodologias.error.message}`}
            </div>
          )}
        </>
      )}

      {posicoes.length > 0 && (
        <>
        {tickersDefasados.length > 0 && (
          <div className="aviso" role="status">
            {tickersDefasados.length === 1
              ? "1 ativo com cotação desatualizada"
              : `${tickersDefasados.length} ativos com cotação desatualizada`}
            : {tickersDefasados.join(", ")}. A data da última cotação aparece abaixo do preço.
          </div>
        )}
        <div className="abas" role="group" aria-label="Visões do portfólio">
          {(["Resumo", "Rentabilidade", "Proventos", "Valuation"] as const).map((visao) => (
            <button key={visao} type="button" className={`aba${aba === visao ? " ativa" : ""}`}
              aria-pressed={aba === visao} onClick={() => { setAba(visao); setOrdem({ chave: "ticker", desc: false }); }}>
              {visao}
            </button>
          ))}
        </div>
        {aba === "Valuation" && (
          <>
            <SeletorReferenciaValuation valor={referencia} onChange={setReferencia} />
            <p className="sutil">Margem = (preço justo de referência − cotação atual) / preço justo de referência. Média dos modelos disponíveis quando selecionada.</p>
            {carregandoValuations && <p>Carregando valuations…</p>}
            {erroValuations && <div className="erro">{(erroValuations as Error).message}</div>}
          </>
        )}
        <div className="tabela-container portfolio-tabela-container" role="region" aria-label="Posições do portfólio" tabIndex={0}>
          <table className={`tabela tabela-posicoes${aba === "Valuation" ? " portfolio-tabela-valuation" : ""}`} aria-label="Posições do portfólio">
            <thead>
              <tr>
                {cols.map((c) => (
                  <th
                    key={c.chave}
                    className={c.numerica ? "num" : ""}
                    scope="col"
                    aria-sort={ordem.chave === c.chave ? (ordem.desc ? "descending" : "ascending") : undefined}
                  >
                    <span className="portfolio-cabecalho">
                      <button type="button" className="ordenar" onClick={() => ordenarPor(c.chave)}>
                        {c.titulo}
                        {ordem.chave === c.chave && <span aria-hidden="true">{ordem.desc ? " ▼" : " ▲"}</span>}
                      </button>
                      {AJUDAS_COLUNAS[c.chave] && (
                        <AjudaTabela
                          label={`Ajuda sobre ${c.titulo}`}
                          texto={AJUDAS_COLUNAS[c.chave]}
                          classe="portfolio-ajuda-icone"
                        />
                      )}
                    </span>
                  </th>
                ))}
                {aba === "Valuation" && <th scope="col" className="portfolio-acoes-cabecalho">Ações</th>}
              </tr>
            </thead>
            <tbody>{grupos.flatMap((g) => [...(g.nome ? [subtotal(g.nome, g.itens)] : []), ...g.itens.map(linha)])}</tbody>
          </table>
        </div>
        </>
      )}
    </section>
  );
}
