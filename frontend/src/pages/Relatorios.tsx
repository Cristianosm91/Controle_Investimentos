import { useMemo, useState, type FormEvent } from "react";
import { useQuery } from "@tanstack/react-query";
import { api, query } from "../api";
import { useAtivos, useCorretoras, useDominio } from "../cadastros";
import { CampoData } from "../components/CampoData";
import { data, moeda, numero } from "../formato";
import { useInvestidor } from "../InvestidorContext";
import { baixar, nomeArquivo, type Aba, type Celula } from "../exportar";
import type { HistoricoLancamento, MovCaixa, Operacao, Pagina, Provento } from "../tipos";

type Fonte = "operacoes" | "proventos" | "caixa";
type Registro = Operacao | Provento | MovCaixa;
type ValorRegistro = string | number | null;
type Linha = Record<string, ValorRegistro>;
type TipoColuna = "texto" | "data" | "numero" | "moeda";

interface Coluna {
  chave: string;
  titulo: string;
  tipo: TipoColuna;
}

const COLUNAS: Record<Fonte, Coluna[]> = {
  operacoes: [
    { chave: "data", titulo: "Data", tipo: "data" },
    { chave: "investidor", titulo: "Investidor", tipo: "texto" },
    { chave: "ticker", titulo: "Ativo", tipo: "texto" },
    { chave: "classe", titulo: "Classe", tipo: "texto" },
    { chave: "evento", titulo: "Evento", tipo: "texto" },
    { chave: "quantidade", titulo: "Quantidade", tipo: "numero" },
    { chave: "preco", titulo: "Preço unitário", tipo: "moeda" },
    { chave: "taxas", titulo: "Taxas", tipo: "moeda" },
    { chave: "irrf", titulo: "IRRF", tipo: "moeda" },
    { chave: "moeda", titulo: "Moeda", tipo: "texto" },
    { chave: "cambio", titulo: "Câmbio", tipo: "numero" },
    { chave: "corretora", titulo: "Corretora", tipo: "texto" },
    { chave: "origem", titulo: "Origem", tipo: "texto" },
    { chave: "observacao", titulo: "Observação", tipo: "texto" },
  ],
  proventos: [
    { chave: "data_pagamento", titulo: "Pagamento", tipo: "data" },
    { chave: "data_com", titulo: "Data com", tipo: "data" },
    { chave: "investidor", titulo: "Investidor", tipo: "texto" },
    { chave: "ticker", titulo: "Ativo", tipo: "texto" },
    { chave: "classe", titulo: "Classe", tipo: "texto" },
    { chave: "evento", titulo: "Evento", tipo: "texto" },
    { chave: "valor", titulo: "Valor bruto", tipo: "moeda" },
    { chave: "irrf", titulo: "IRRF", tipo: "moeda" },
    { chave: "taxas", titulo: "Taxas", tipo: "moeda" },
    { chave: "moeda", titulo: "Moeda", tipo: "texto" },
    { chave: "cambio", titulo: "Câmbio", tipo: "numero" },
    { chave: "corretora", titulo: "Corretora", tipo: "texto" },
    { chave: "observacao", titulo: "Observação", tipo: "texto" },
  ],
  caixa: [
    { chave: "data", titulo: "Data", tipo: "data" },
    { chave: "investidor", titulo: "Investidor", tipo: "texto" },
    { chave: "evento", titulo: "Evento", tipo: "texto" },
    { chave: "valor", titulo: "Valor", tipo: "moeda" },
    { chave: "moeda", titulo: "Moeda", tipo: "texto" },
    { chave: "corretora", titulo: "Corretora", tipo: "texto" },
    { chave: "origem", titulo: "Origem", tipo: "texto" },
    { chave: "observacao", titulo: "Observação", tipo: "texto" },
  ],
};

const NOMES_FONTES: Record<Fonte, string> = {
  operacoes: "Operações",
  proventos: "Proventos",
  caixa: "Movimentações de caixa",
};

const SIMBOLOS: Record<string, "R$" | "US$" | "€"> = { BRL: "R$", USD: "US$", EUR: "€" };

function valorMoeda(valor: ValorRegistro, moedaAtivo: ValorRegistro): string {
  return valor === null ? "—" : moeda(Number(valor), String(moedaAtivo ?? "BRL"));
}

function celulaExcel(coluna: Coluna, linha: Linha): Celula {
  const valor = linha[coluna.chave];
  if (valor === null || valor === undefined) return null;
  if (coluna.tipo === "data") return { d: String(valor) };
  if (coluna.tipo === "moeda") {
    const simbolo = SIMBOLOS[String(linha.moeda ?? "BRL")];
    return { n: Number(valor), f: "moeda", ...(simbolo ? { moeda: simbolo } : {}) };
  }
  if (coluna.tipo === "numero") return { n: Number(valor), f: "numero" };
  return String(valor);
}

function textoCelula(coluna: Coluna, linha: Linha): string {
  const valor = linha[coluna.chave];
  if (valor === null || valor === undefined || valor === "") return "—";
  if (coluna.tipo === "data") return data(String(valor));
  if (coluna.tipo === "moeda") return valorMoeda(valor, linha.moeda);
  if (coluna.tipo === "numero") return numero(Number(valor), coluna.chave === "quantidade" ? 8 : 6);
  return String(valor);
}

function escapar(texto: string): string {
  return texto.replace(/[&<>"']/g, (caractere) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  })[caractere] ?? caractere);
}

async function carregarTodos<T>(fonte: Fonte, parametros: Record<string, string | number | undefined>): Promise<T[]> {
  const resultado: T[] = [];
  let deslocamento = 0;
  let total = 0;
  do {
    const pagina = await api.get<Pagina<T>>(
      `/${fonte}${query({ ...parametros, limite: 1000, deslocamento })}`,
    );
    resultado.push(...pagina.itens);
    total = pagina.total;
    deslocamento += pagina.itens.length;
    if (!pagina.itens.length) break;
    if (resultado.length > 100_000) throw new Error("O relatório excede o limite de 100.000 registros.");
  } while (deslocamento < total);
  return resultado;
}

function imprimir(titulo: string, filtros: string, cabecalhos: string[], linhas: string[][]): void {
  const janela = window.open("", "_blank");
  if (!janela) throw new Error("O navegador bloqueou a janela do relatório. Permita pop-ups e tente novamente.");
  const th = cabecalhos.map((coluna) => `<th>${escapar(coluna)}</th>`).join("");
  const trs = linhas.map((linha) => `<tr>${linha.map((celula) => `<td>${escapar(celula)}</td>`).join("")}</tr>`).join("");
  janela.document.write(`<!doctype html>
    <html lang="pt-BR"><head><meta charset="utf-8"><title>${escapar(titulo)}</title>
    <style>
      body{font:12px Arial,sans-serif;color:#111;margin:18mm}
      h1{font-size:18px} p{font-size:11px;color:#444}
      table{border-collapse:collapse;width:100%;font-size:10px}
      th,td{border:1px solid #bbb;padding:4px;text-align:left;overflow-wrap:anywhere}
      th{background:#eee} thead{display:table-header-group}
      tr{break-inside:avoid}
      @page{size:landscape;margin:12mm}
    </style></head><body><h1>${escapar(titulo)}</h1>
    <p>${escapar(filtros)}</p><p>Gerado em ${new Date().toLocaleString("pt-BR")}</p>
    <table><thead><tr>${th}</tr></thead><tbody>${trs}</tbody></table>
    <script>window.onload=()=>window.print();</script></body></html>`);
  janela.document.close();
}

export function Relatorios() {
  const { filtro, investidores } = useInvestidor();
  const historico = useQuery({
    queryKey: ["historico-lancamentos", filtro],
    queryFn: () => api.get<HistoricoLancamento[]>(`/historico-lancamentos${query({ investidores: filtro, limite: 200 })}`),
  });
  const { data: ativos = [] } = useAtivos();
  const { data: corretoras = [] } = useCorretoras();
  const { data: dominio } = useDominio();
  const [fonte, setFonte] = useState<Fonte>("operacoes");
  const [inicio, setInicio] = useState("");
  const [fim, setFim] = useState("");
  const [ticker, setTicker] = useState("");
  const [classe, setClasse] = useState("");
  const [corretoraId, setCorretoraId] = useState("");
  const [evento, setEvento] = useState("");
  const [selecionadas, setSelecionadas] = useState<string[]>(COLUNAS.operacoes.map((c) => c.chave));
  const [linhas, setLinhas] = useState<Linha[] | null>(null);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  const colunas = COLUNAS[fonte];
  const ativas = useMemo(() => colunas.filter((coluna) => selecionadas.includes(coluna.chave)), [colunas, selecionadas]);
  const opcoesEvento = fonte === "operacoes" ? dominio?.eventos_operacao : fonte === "proventos" ? dominio?.eventos_provento : dominio?.eventos_caixa;
  const classePorTicker = new Map(ativos.map((ativo) => [ativo.ticker, ativo.classe]));
  const nomeInvestidor = new Map(investidores.map((investidor) => [investidor.id, investidor.nome]));
  const descricaoFiltros = [
    `Investidores: ${filtro ? filtro.split(",").map((id) => nomeInvestidor.get(Number(id)) ?? id).join(", ") : "todos"}`,
    `Período: ${inicio ? data(inicio) : "sem limite"} – ${fim ? data(fim) : "sem limite"}`,
    ticker && fonte !== "caixa" ? `Ativo: ${ticker}` : "",
    classe && fonte !== "caixa" ? `Classe: ${classe}` : "",
    corretoraId ? `Corretora: ${corretoras.find((c) => String(c.id) === corretoraId)?.nome ?? corretoraId}` : "",
    evento ? `Evento: ${opcoesEvento?.[evento] ?? evento}` : "",
  ].filter(Boolean).join(" · ");

  const buscar = async (eventoForm: FormEvent) => {
    eventoForm.preventDefault();
    setErro(null);
    setLinhas(null);
    if (inicio && fim && inicio > fim) {
      setErro("A data inicial deve ser anterior ou igual à data final.");
      return;
    }
    if (!ativas.length) {
      setErro("Selecione ao menos uma coluna para o relatório.");
      return;
    }
    setCarregando(true);
    try {
      const parametros: Record<string, string | number | undefined> = {
        investidores: filtro,
        inicio: inicio || undefined,
        fim: fim || undefined,
        evento: evento || undefined,
        corretora_id: corretoraId ? Number(corretoraId) : undefined,
      };
      if (fonte !== "caixa") {
        parametros.ticker = ticker || undefined;
        parametros.classe = classe || undefined;
      }
      const dados = await carregarTodos<Registro>(fonte, parametros);
      setLinhas(
        dados.map((registro): Linha => {
          if ("data_pagamento" in registro) {
            return {
              data_pagamento: registro.data_pagamento,
              data_com: registro.data_com,
              investidor: nomeInvestidor.get(registro.investidor_id) ?? String(registro.investidor_id),
              ticker: registro.ticker,
              classe: classePorTicker.get(registro.ticker) ?? "",
              evento: dominio?.eventos_provento[registro.evento] ?? registro.evento,
              valor: registro.valor,
              irrf: registro.irrf,
              taxas: registro.taxas,
              moeda: registro.moeda,
              cambio: registro.cambio,
              corretora: registro.corretora,
              observacao: registro.observacao,
            };
          }
          if ("ticker" in registro) {
            return {
              data: registro.data,
              investidor: nomeInvestidor.get(registro.investidor_id) ?? String(registro.investidor_id),
              ticker: registro.ticker,
              classe: classePorTicker.get(registro.ticker) ?? "",
              evento: dominio?.eventos_operacao[registro.evento] ?? registro.evento,
              quantidade: registro.quantidade,
              preco: registro.preco,
              taxas: registro.taxas,
              irrf: registro.irrf,
              moeda: registro.moeda,
              cambio: registro.cambio,
              corretora: registro.corretora,
              origem: registro.origem,
              observacao: registro.observacao,
            };
          }
          return {
            data: registro.data,
            investidor: nomeInvestidor.get(registro.investidor_id) ?? String(registro.investidor_id),
            evento: dominio?.eventos_caixa[registro.evento] ?? registro.evento,
            valor: registro.valor,
            moeda: registro.moeda,
            corretora: registro.corretora,
            origem: registro.origem,
            observacao: registro.observacao,
          };
        }),
      );
    } catch (falha) {
      setErro((falha as Error).message);
    } finally {
      setCarregando(false);
    }
  };

  const exportarExcel = async () => {
    if (!linhas || !ativas.length) return;
    setErro(null);
    try {
      const aba: Aba = {
        titulo: NOMES_FONTES[fonte],
        colunas: ativas.map((coluna) => coluna.titulo),
        linhas: linhas.map((linha) => ativas.map((coluna) => celulaExcel(coluna, linha))),
      };
      const filtros: Aba = {
        titulo: "Filtros",
        colunas: ["Filtro", "Valor"],
        linhas: [
          ["Investidores", filtro ? filtro.split(",").map((id) => nomeInvestidor.get(Number(id)) ?? id).join(", ") : "Todos"],
          ["Período", `${inicio ? data(inicio) : "Sem limite"} a ${fim ? data(fim) : "Sem limite"}`],
          ...(ticker && fonte !== "caixa" ? [["Ativo", ticker]] : []),
          ...(classe && fonte !== "caixa" ? [["Classe", classe]] : []),
          ...(corretoraId ? [["Corretora", corretoras.find((c) => String(c.id) === corretoraId)?.nome ?? corretoraId]] : []),
          ...(evento ? [["Evento", opcoesEvento?.[evento] ?? evento]] : []),
        ],
      };
      await baixar("xlsx", nomeArquivo(`relatorio-${fonte}`), [aba, filtros]);
    } catch (falha) {
      setErro((falha as Error).message);
    }
  };

  const exportarPdf = () => {
    if (!linhas || !ativas.length) return;
    try {
      imprimir(
        `Relatório · ${NOMES_FONTES[fonte]}`,
        descricaoFiltros,
        ativas.map((coluna) => coluna.titulo),
        linhas.map((linha) => ativas.map((coluna) => textoCelula(coluna, linha))),
      );
    } catch (falha) {
      setErro((falha as Error).message);
    }
  };

  const alterarFonte = (valor: Fonte) => {
    setFonte(valor);
    setSelecionadas(COLUNAS[valor].map((coluna) => coluna.chave));
    setLinhas(null);
  };

  return (
    <section>
      <h1>Relatórios</h1>
      <p className="sutil">Escolha a fonte, os filtros e as colunas. O escopo de investidores segue o seletor global.</p>

      <form className="formulario simulador" onSubmit={buscar}>
        <label>
          Dados
          <select value={fonte} onChange={(e) => alterarFonte(e.target.value as Fonte)}>
            {Object.entries(NOMES_FONTES).map(([valor, rotulo]) => (
              <option key={valor} value={valor}>{rotulo}</option>
            ))}
          </select>
        </label>
        <label>Data inicial<CampoData valor={inicio} aoMudar={setInicio} /></label>
        <label>Data final<CampoData valor={fim} aoMudar={setFim} /></label>
        {fonte !== "caixa" && (
          <>
            <label>
              Ativo
              <input aria-label="Filtrar por ativo" value={ticker} onChange={(e) => setTicker(e.target.value.toUpperCase())} placeholder="Ticker" />
            </label>
            <label>
              Classe
              <select value={classe} onChange={(e) => setClasse(e.target.value)}>
                <option value="">Todas</option>
                {[...new Set(ativos.map((ativo) => ativo.classe))].sort().map((valor) => (
                  <option key={valor} value={valor}>{valor}</option>
                ))}
              </select>
            </label>
          </>
        )}
        <label>
          Corretora
          <select value={corretoraId} onChange={(e) => setCorretoraId(e.target.value)}>
            <option value="">Todas</option>
            {corretoras.map((corretora) => <option key={corretora.id} value={corretora.id}>{corretora.nome}</option>)}
          </select>
        </label>
        <label>
          Evento
          <select value={evento} onChange={(e) => setEvento(e.target.value)}>
            <option value="">Todos</option>
            {Object.entries(opcoesEvento ?? {}).map(([valor, rotulo]) => (
              <option key={valor} value={valor}>{rotulo}</option>
            ))}
          </select>
        </label>
        <button type="submit" disabled={carregando}>
          {carregando ? "Gerando…" : "Gerar prévia"}
        </button>
      </form>

      <div className="painel">
        <h2>Colunas do relatório</h2>
        <div className="acoes">
          {colunas.map((coluna) => (
            <label className="check" key={coluna.chave}>
              <input
                type="checkbox"
                checked={selecionadas.includes(coluna.chave)}
                onChange={() => setSelecionadas((atual) =>
                  atual.includes(coluna.chave)
                    ? atual.filter((chave) => chave !== coluna.chave)
                    : [...atual, coluna.chave],
                )}
              />
              {coluna.titulo}
            </label>
          ))}
        </div>
      </div>

      {erro && <div className="erro">{erro}</div>}
      {linhas && (
        <>
          <div className="titulo-linha">
            <h2>{NOMES_FONTES[fonte]} · {linhas.length} registro(s)</h2>
            <div className="acoes">
              <button type="button" className="secundario" disabled={!linhas.length} onClick={exportarPdf}>PDF / Imprimir</button>
              <button type="button" disabled={!linhas.length} onClick={() => void exportarExcel()}>Excel (.xlsx)</button>
            </div>
          </div>
          {linhas.length ? (
            <div className="tabela-container">
              <table className="tabela">
                <thead>
                  <tr>{ativas.map((coluna) => <th scope="col" key={coluna.chave}>{coluna.titulo}</th>)}</tr>
                </thead>
                <tbody>
                  {linhas.slice(0, 100).map((linha, indice) => (
                    <tr key={indice}>
                      {ativas.map((coluna) => <td key={coluna.chave}>{textoCelula(coluna, linha)}</td>)}
                    </tr>
                  ))}
                </tbody>
              </table>
              {linhas.length > 100 && <p className="sutil">A prévia mostra 100 registros; PDF e Excel incluem todos os {linhas.length}.</p>}
            </div>
          ) : (
            <p className="aviso">Nenhum registro corresponde aos filtros.</p>
          )}
        </>
      )}

      <div className="painel">
        <h2>Histórico de alterações financeiras</h2>
        <p className="sutil">
          Registro local das criações, edições e exclusões de operações, proventos e movimentos de caixa.
          Os valores ficam no banco configurado para a aplicação e não são enviados a serviços externos.
        </p>
        {historico.error && <div className="erro">{(historico.error as Error).message}</div>}
        {historico.isLoading && <p>Carregando histórico…</p>}
        {historico.data && historico.data.length > 0 ? (
          <>
            <div className="tabela-container">
              <table className="tabela compacta">
                <thead>
                  <tr>
                    <th scope="col">Data e hora</th>
                    <th scope="col">Tipo</th>
                    <th scope="col">Ação</th>
                    <th scope="col">Registro</th>
                    <th scope="col">Detalhes</th>
                  </tr>
                </thead>
                <tbody>
                  {historico.data.map((item) => (
                    <tr key={item.id}>
                      <td>{new Date(item.ocorrido_em).toLocaleString("pt-BR")}</td>
                      <td>{item.entidade === "movcaixa" ? "Movimento de caixa" : item.entidade === "operacao" ? "Operação" : "Provento"}</td>
                      <td>{item.acao}</td>
                      <td>{item.registro_id}</td>
                      <td>
                        <details>
                          <summary>Ver valores</summary>
                          <dl>
                            {item.anterior && (
                              <div><dt>Antes</dt><dd><pre>{JSON.stringify(item.anterior, null, 2)}</pre></dd></div>
                            )}
                            {item.novo && (
                              <div><dt>Depois</dt><dd><pre>{JSON.stringify(item.novo, null, 2)}</pre></dd></div>
                            )}
                          </dl>
                        </details>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {historico.data.length === 200 && <p className="sutil">Exibindo até 200 alterações mais recentes.</p>}
          </>
        ) : (
          !historico.isLoading && <p className="aviso">Nenhuma alteração registrada para os investidores selecionados.</p>
        )}
      </div>
    </section>
  );
}
