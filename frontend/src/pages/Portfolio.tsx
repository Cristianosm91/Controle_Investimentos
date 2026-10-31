import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { api, query } from "../api";
import { invalidarDerivados } from "../cadastros";
import { chaveGrupo, Exposicao, somarPor, valorExposicao } from "../components/Exposicao";
import { classeSinal, data, moeda, numero, percentual } from "../formato";
import { useInvestidor } from "../InvestidorContext";
import type { Posicao } from "../tipos";

type Coluna = {
  chave: string;
  titulo: string;
  valor: (p: Posicao) => number | string | null;
  render: (p: Posicao) => React.ReactNode;
  numerica?: boolean;
};

const lucroAbertoPct = (p: Posicao) => (p.lucro_aberto !== null && p.custo ? p.lucro_aberto / p.custo : null);

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
          <div className="sutil">{p.nome}</div>
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
    { chave: "custo", titulo: "Investido", numerica: true, valor: (p) => p.custo, render: (p) => moeda(p.custo) },
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
          <div className="sutil">{percentual(p.custo ? p.proventos / p.custo : null)}</div>
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
    { chave: "subsetor", titulo: "Subsetor", valor: (p) => p.subsetor, render: (p) => <span className="sutil">{p.subsetor ?? "—"}</span> },
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

export function Portfolio() {
  const { filtro, investidores } = useInvestidor();
  const [porInvestidor, setPorInvestidor] = useState(false);
  const [agrupar, setAgrupar] = useState<"" | "classe" | "setor">("");
  const [verExposicao, setVerExposicao] = useState(true);
  const [ordem, setOrdem] = useState<{ chave: string; desc: boolean }>({ chave: "classe", desc: false });
  const cliente = useQueryClient();

  const { data: todas = [], isLoading, error } = useQuery({
    queryKey: ["posicoes", filtro, porInvestidor],
    queryFn: () =>
      api.get<Posicao[]>(
        `/posicoes${query({ investidores: filtro, agrupar: porInvestidor ? "investidor" : "ativo", somente_abertas: false })}`,
      ),
  });
  const posicoes = useMemo(() => todas.filter((p) => p.quantidade > 0), [todas]);

  const atualizar = useMutation({
    mutationFn: () => api.post<{ atualizados: Record<string, string>; sem_cotacao: string[] }>("/cotacoes/atualizar"),
    onSuccess: () => invalidarDerivados(cliente),
  });

  const totais = useMemo(() => {
    const soma = (lista: Posicao[], f: (p: Posicao) => number | null) => lista.reduce((s, p) => s + (f(p) ?? 0), 0);
    return {
      custo: soma(posicoes, (p) => p.custo),
      mercado: soma(posicoes, (p) => p.valor_mercado),
      lucroDia: soma(posicoes, (p) => p.lucro_dia),
      lucroAberto: soma(posicoes, (p) => p.lucro_aberto),
      proventos: soma(todas, (p) => p.proventos),
      swing: soma(todas, (p) => p.lucro_realizado),
      daytrade: soma(todas, (p) => p.lucro_daytrade),
      semCotacao: posicoes.filter((p) => p.valor_mercado === null).length,
    };
  }, [posicoes, todas]);

  const nomes = useMemo(() => new Map(investidores.map((i) => [i.id, i.nome])), [investidores]);
  const cols = colunas(totais.mercado, nomes, porInvestidor);

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
    <tr key={`${p.investidor_id ?? 0}-${p.ativo_id}`}>
      {cols.map((c) => (
        <td key={c.chave} className={c.numerica ? "num" : ""}>
          {c.render(p)}
        </td>
      ))}
    </tr>
  );

  const totalExposicao = useMemo(() => posicoes.reduce((s, p) => s + valorExposicao(p), 0), [posicoes]);

  const subtotal = (nome: string, itens: Posicao[]) => {
    const mercado = itens.reduce((s, p) => s + valorExposicao(p), 0);
    const custo = itens.reduce((s, p) => s + p.custo, 0);
    const lucro = itens.reduce((s, p) => s + (p.lucro_aberto ?? 0), 0);
    return (
      <tr key={`grupo-${nome}`} className="linha-grupo">
        <td colSpan={cols.length}>
          <strong>{nome}</strong> · {itens.length} ativo(s) · {percentual(totalExposicao ? mercado / totalExposicao : null)} ·
          Investido {moeda(custo)} · Mercado {moeda(mercado)} ·{" "}
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
          <label className="check">
            Agrupar
            <select value={agrupar} onChange={(e) => setAgrupar(e.target.value as typeof agrupar)}>
              <option value="">—</option>
              <option value="classe">Classe</option>
              <option value="setor">Setor</option>
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
          <span>Valor investido</span>
          <strong>{moeda(totais.custo)}</strong>
        </div>
        <div className="card">
          <span>Valor de mercado</span>
          <strong>{moeda(totais.mercado)}</strong>
          {totais.semCotacao > 0 && <small className="sutil">{totais.semCotacao} ativo(s) sem cotação</small>}
        </div>
        <div className="card">
          <span>Lucro aberto</span>
          <strong className={classeSinal(totais.lucroAberto)}>{moeda(totais.lucroAberto)}</strong>
          <small className={classeSinal(totais.lucroAberto)}>{percentual(totais.custo ? totais.lucroAberto / totais.custo : null)}</small>
        </div>
        <div className="card">
          <span>Lucro do dia</span>
          <strong className={classeSinal(totais.lucroDia)}>{moeda(totais.lucroDia)}</strong>
        </div>
        <div className="card">
          <span>Proventos (histórico)</span>
          <strong>{moeda(totais.proventos)}</strong>
        </div>
        <div className="card">
          <span>Swing trade realizado</span>
          <strong className={classeSinal(totais.swing)}>{moeda(totais.swing)}</strong>
          <small className="sutil">Day trade: {moeda(totais.daytrade)}</small>
        </div>
        <div className="card">
          <span>Lucro total</span>
          <strong className={classeSinal(totais.lucroAberto + totais.proventos + totais.swing + totais.daytrade)}>
            {moeda(totais.lucroAberto + totais.proventos + totais.swing + totais.daytrade)}
          </strong>
        </div>
      </div>

      {isLoading && <p>Carregando…</p>}
      {error && <div className="erro">{(error as Error).message}</div>}
      {!isLoading && posicoes.length === 0 && <div className="aviso">Nenhuma posição aberta.</div>}

      {verExposicao && posicoes.length > 0 && <Exposicao posicoes={posicoes} />}

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
              </tr>
            </thead>
            <tbody>{grupos.flatMap((g) => [...(g.nome ? [subtotal(g.nome, g.itens)] : []), ...g.itens.map(linha)])}</tbody>
          </table>
        </div>
      )}
    </section>
  );
}
