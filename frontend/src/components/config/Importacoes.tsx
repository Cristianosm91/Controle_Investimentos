import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../../api";
import { invalidarDerivados } from "../../cadastros";
import { useInvestidor } from "../../InvestidorContext";
import type { LoteImportacao } from "../../tipos";

const TIPOS: Record<string, string> = {
  EXTRATO_B3: "Extrato B3",
  PLANILHA_OPERACOES: "Planilha de operações",
  ALUGUEL: "Extrato de aluguel (BTC)",
};

const dataHora = (iso: string) => new Date(iso).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });

export function Importacoes() {
  const { investidores } = useInvestidor();
  const cliente = useQueryClient();
  const { data: lotes = [], isLoading, error } = useQuery({
    queryKey: ["lotes"],
    queryFn: () => api.get<LoteImportacao[]>("/lotes"),
  });
  const desfazer = useMutation({
    mutationFn: (id: number) => api.post<{ operacoes: number; proventos: number; caixa: number }>(`/lotes/${id}/desfazer`),
    onSuccess: () => {
      for (const chave of ["lotes", "operacoes", "proventos", "caixa"]) cliente.invalidateQueries({ queryKey: [chave] });
      invalidarDerivados(cliente);
    },
  });
  const nome = (id: number | null) => (id === null ? "—" : (investidores.find((i) => i.id === id)?.nome ?? id));

  return (
    <>
      <h2>Importações</h2>
      <p className="sutil">
        Cada arquivo importado (extrato da B3 ou de aluguel) forma um lote. Desfazer apaga só os lançamentos gravados por ele — os
        lançados à mão ou por outras importações ficam intactos. Ativos e corretoras criados na importação são mantidos. Depois de
        desfeito, o mesmo arquivo pode ser importado de novo.
      </p>
      {(error ?? desfazer.error) && <div className="erro">{((error ?? desfazer.error) as Error).message}</div>}
      {desfazer.data && (
        <div className="aviso">
          Lote desfeito: {desfazer.data.operacoes} operação(ões), {desfazer.data.proventos} provento(s) e {desfazer.data.caixa}{" "}
          movimentação(ões) de caixa removidos.
        </div>
      )}
      {isLoading && <p>Carregando…</p>}
      {!isLoading && lotes.length === 0 && <div className="aviso">Nenhuma importação registrada ainda.</div>}
      {lotes.length > 0 && (
        <div className="tabela-container">
          <table className="tabela compacta">
            <thead>
              <tr>
                <th>Data</th>
                <th>Tipo</th>
                <th>Arquivo</th>
                <th>Investidor</th>
                <th className="num">Operações</th>
                <th className="num">Proventos</th>
                <th>Situação</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {lotes.map((l) => (
                <tr key={l.id}>
                  <td>{dataHora(l.criado_em)}</td>
                  <td>{TIPOS[l.tipo] ?? l.tipo}</td>
                  <td className="texto-limitado">{l.arquivo ?? "—"}</td>
                  <td>{nome(l.investidor_id)}</td>
                  <td className="num">{l.operacoes}</td>
                  <td className="num">{l.proventos}</td>
                  <td>{l.desfeito_em ? <span className="sutil">Desfeito em {dataHora(l.desfeito_em)}</span> : "Ativo"}</td>
                  <td className="num">
                    {!l.desfeito_em && (
                      <button
                        className="link perigo"
                        disabled={desfazer.isPending}
                        onClick={() =>
                          confirm(
                            `Desfazer a importação de ${l.arquivo ?? TIPOS[l.tipo] ?? l.tipo}? ` +
                              `${l.operacoes} operação(ões) e ${l.proventos} provento(s) serão excluídos.`,
                          ) && desfazer.mutate(l.id)
                        }
                      >
                        Desfazer
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
