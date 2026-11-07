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

  const selecionarClasse = (ativo: Pick<Posicao, "ativo_id" | "ticker" | "classe">, classe: string) => {
    if (
      classe !== ativo.classe &&
      confirm(
        `Alterar a classe de ${ativo.ticker} de ${ativo.classe} para ${classe}? ` +
          "A alteração afeta o histórico do ativo em operações, proventos e cálculos.",
      )
    ) {
      alterarClasse.mutate({ id: ativo.ativo_id, classe });
    }
  };

  return (
    <>
      {error && <div className="erro">{error.message}</div>}
      {cadastros.error && <div className="erro">{cadastros.error.message}</div>}
      {alterarClasse.error && <div className="erro">{alterarClasse.error.message}</div>}
      {isLoading ? (
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
              {ativos.map((ativo) => {
                const cadastro = cadastros.data?.find((item) => item.id === ativo.ativo_id);
                const bolsa = cadastro?.mercado ?? "";
                return (
                <tr key={ativo.ativo_id}>
                  <td>{ativo.ticker}</td>
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
                      disabled={!cadastro || alterarClasse.isPending}
                      onChange={(e) => {
                        const novaBolsa = e.target.value;
                        if (
                          novaBolsa !== bolsa &&
                          confirm(`Alterar a bolsa de ${ativo.ticker} para ${novaBolsa || "Sem bolsa"}?`)
                        ) {
                          alterarClasse.mutate({ id: ativo.ativo_id, mercado: novaBolsa || null });
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
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
