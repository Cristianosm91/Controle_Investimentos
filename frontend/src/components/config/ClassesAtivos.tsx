import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, query } from "../../api";
import { invalidarDerivados, useAtivos } from "../../cadastros";
import { useInvestidor } from "../../InvestidorContext";
import type { Posicao } from "../../tipos";

const CLASSES_CONHECIDAS = [
  "AÇÃO", "BDR", "ETF", "ETF_US", "FII", "FIAGRO", "OPÇÃO", "REIT", "STOCK", "CRIPTO", "R.FIXA",
];
const BOLSAS = ["BVMF", "NASDAQ", "NYSE", "NYSEARCA", "NYSEAMERICAN", "BATS"];

export function ClassesAtivos() {
  const cliente = useQueryClient();
  const { filtro } = useInvestidor();
  const [mostrarTodos, setMostrarTodos] = useState(false);
  const [busca, setBusca] = useState("");
  const cadastros = useAtivos();
  const { data: ativos = [], isLoading, error } = useQuery({
    queryKey: ["posicoes", "classes", filtro],
    queryFn: () =>
      api.get<Posicao[]>(
        `/posicoes${query({ investidores: filtro, agrupar: "ativo", somente_abertas: true })}`,
      ),
  });
  const { data: classesDisponiveis = [] } = useQuery({
    queryKey: ["classes"],
    queryFn: () => api.get<string[]>("/classes"),
  });
  const alterarClasse = useMutation({
    mutationFn: ({ id, ...campos }: { id: number; classe?: string; mercado?: string | null }) =>
      api.patch(`/ativos/${id}/classe`, campos),
    onSuccess: () => {
      cliente.invalidateQueries({ queryKey: ["ativos"] });
      cliente.invalidateQueries({ queryKey: ["classes"] });
      cliente.invalidateQueries({ queryKey: ["valor-investido"] });
      cliente.invalidateQueries({ queryKey: ["operacoes"] });
      cliente.invalidateQueries({ queryKey: ["proventos"] });
      invalidarDerivados(cliente);
    },
  });
  const classes = [...new Set([...classesDisponiveis, ...CLASSES_CONHECIDAS])].sort();
  const idsAbertos = new Set(ativos.map((ativo) => ativo.ativo_id));
  const buscaNormalizada = busca.trim().toUpperCase();
  const itens = mostrarTodos
    ? (cadastros.data ?? [])
        .filter((ativo) => !buscaNormalizada || ativo.ticker.includes(buscaNormalizada))
        .map((ativo) => ({
          id: ativo.id,
          ticker: ativo.ticker,
          classe: ativo.classe,
          mercado: ativo.mercado,
          aberta: error ? null : idsAbertos.has(ativo.id),
        }))
    : ativos.map((ativo) => ({
        id: ativo.ativo_id,
        ticker: ativo.ticker,
        classe: ativo.classe,
        mercado: cadastros.data?.find((cadastro) => cadastro.id === ativo.ativo_id)?.mercado ?? null,
        aberta: true,
      }));

  const selecionarClasse = (ativo: { id: number; ticker: string; classe: string }, classe: string) => {
    if (
      classe !== ativo.classe &&
      confirm(
        `Alterar a classe de ${ativo.ticker} de ${ativo.classe} para ${classe}? ` +
          "A alteração afeta o histórico do ativo em operações, proventos e cálculos.",
      )
    ) {
      alterarClasse.mutate({ id: ativo.id, classe });
    }
  };

  return (
    <>
      {error && <div className="erro">{error.message}</div>}
      {cadastros.error && <div className="erro">{cadastros.error.message}</div>}
      {alterarClasse.error && <div className="erro">{alterarClasse.error.message}</div>}
      <div className="acoes">
        <label>
          Exibir
          <select value={mostrarTodos ? "todos" : "abertos"} onChange={(e) => setMostrarTodos(e.target.value === "todos")}>
            <option value="abertos">Posições abertas</option>
            <option value="todos">Todos os ativos</option>
          </select>
        </label>
        {mostrarTodos && (
          <input
            aria-label="Buscar ativo por ticker"
            placeholder="Buscar ticker"
            value={busca}
            onChange={(e) => setBusca(e.target.value.toUpperCase())}
          />
        )}
      </div>
      {isLoading || (mostrarTodos && cadastros.isLoading) ? (
        <p>Carregando…</p>
      ) : (
        <div className="tabela-container">
          <table className="tabela compacta">
            <thead>
              <tr>
                <th>Ticker</th>
                <th>Classe</th>
                <th>Bolsa</th>
              </tr>
            </thead>
            <tbody>
              {itens.map((ativo) => {
                const bolsa = ativo.mercado ?? "";
                return (
                <tr key={ativo.id}>
                  <td>
                    {ativo.ticker}
                    {ativo.aberta === false && (
                      <span className="etiqueta" title="Para os investidores selecionados">
                        Sem posição aberta
                      </span>
                    )}
                    {ativo.aberta === null && <span className="etiqueta">Situação indisponível</span>}
                  </td>
                  <td>
                    <select
                      aria-label={`Classe de ${ativo.ticker}`}
                      value={ativo.classe}
                      disabled={alterarClasse.isPending}
                      onChange={(e) => selecionarClasse(ativo, e.target.value)}
                    >
                      {!classes.includes(ativo.classe) && <option value={ativo.classe}>{ativo.classe}</option>}
                      {classes.map((classe) => (
                        <option key={classe} value={classe}>
                          {classe}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td>
                    <select
                      aria-label={`Bolsa de ${ativo.ticker}`}
                      value={bolsa}
                      disabled={alterarClasse.isPending}
                      onChange={(e) => {
                        const novaBolsa = e.target.value;
                        if (
                          novaBolsa !== bolsa &&
                          confirm(`Alterar a bolsa de ${ativo.ticker} para ${novaBolsa || "Sem bolsa"}?`)
                        ) {
                          alterarClasse.mutate({ id: ativo.id, mercado: novaBolsa || null });
                        }
                      }}
                    >
                      <option value="">Sem bolsa</option>
                      {bolsa && !BOLSAS.includes(bolsa) && <option value={bolsa}>{bolsa}</option>}
                      {BOLSAS.map((mercado) => (
                        <option key={mercado} value={mercado}>{mercado}</option>
                      ))}
                    </select>
                  </td>
                </tr>
                );
              })}
              {!itens.length && (
                <tr>
                  <td colSpan={3}>Nenhum ativo encontrado.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
