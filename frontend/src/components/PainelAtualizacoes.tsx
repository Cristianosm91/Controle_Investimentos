import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api";
import { invalidarDerivados } from "../cadastros";
import type { Tarefa } from "../tipos";

const dataHora = (iso: string | null) =>
  iso ? new Date(iso).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" }) : "—";

const ACAO: Record<string, string> = {
  cotacoes: "Atualizar agora",
  cotahist_diario: "Buscar pendentes",
  cotahist_historico: "Carregar histórico",
  indices_diario: "Atualizar agora",
  historico_complementar: "Carregar histórico",
};

export function PainelAtualizacoes() {
  const cliente = useQueryClient();
  const { data: tarefas = [], error } = useQuery({
    queryKey: ["atualizacoes"],
    queryFn: () => api.get<Tarefa[]>("/atualizacoes"),
    refetchInterval: (q) => (q.state.data?.some((t) => t.em_execucao) ? 3000 : 60_000),
  });
  const disparar = useMutation({
    mutationFn: (nome: string) => api.post(`/atualizacoes/${nome}`),
    onSettled: () => {
      cliente.invalidateQueries({ queryKey: ["atualizacoes"] });
      invalidarDerivados(cliente);
    },
  });

  return (
    <>
      <h2>Status das atualizações</h2>
      <p className="sutil">
        Cotações a cada 15 min no pregão (seg–sex, 10h–18h); fechamento oficial da B3 às 21h e 8h. A carga histórica
        baixa um arquivo da B3 por ano desde a primeira operação.
      </p>
      {(error ?? disparar.error) && <div className="erro">{((error ?? disparar.error) as Error).message}</div>}
      <table className="tabela compacta">
        <thead>
          <tr>
            <th>Tarefa</th>
            <th>Última execução</th>
            <th>Resultado</th>
            <th>Próxima</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {tarefas.map((t) => (
            <tr key={t.nome}>
              <td>{t.descricao}</td>
              <td>
                {dataHora(t.fim ?? t.inicio)}
                {t.duracao_s !== null && <div className="sutil">{t.duracao_s} s</div>}
              </td>
              <td className="quebra">
                {t.em_execucao ? (
                  <span className="etiqueta">em execução…</span>
                ) : t.sucesso === null ? (
                  "—"
                ) : (
                  <span className={t.sucesso ? "positivo" : "negativo"}>{t.mensagem}</span>
                )}
              </td>
              <td>{dataHora(t.proxima)}</td>
              <td className="num">
                <button
                  className="secundario"
                  disabled={t.em_execucao || disparar.isPending}
                  onClick={() => disparar.mutate(t.nome)}
                >
                  {ACAO[t.nome] ?? "Executar"}
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );
}
