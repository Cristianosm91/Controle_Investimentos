import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { api } from "../../api";
import { useExclusaoEmLote } from "../ExclusaoEmLote";
import type { Backup as TBackup, Backups, Restauracao } from "../../tipos";

const TIPO: Record<TBackup["tipo"], string> = {
  manual: "Manual",
  automatico: "Automático",
  "antes-restauracao": "Antes de restaurar",
};

const tamanho = (bytes: number) =>
  bytes >= 1024 * 1024 ? `${(bytes / 1024 / 1024).toFixed(1).replace(".", ",")} MB` : `${Math.ceil(bytes / 1024)} KB`;

const dataHora = (iso: string) => new Date(iso).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });

const AVISO_RESTAURAR =
  "Todos os dados atuais serão substituídos pelos do backup. Uma cópia do banco atual será guardada antes. Continuar?";

export function BackupConfig() {
  const cliente = useQueryClient();
  const arquivoRef = useRef<HTMLInputElement>(null);
  const [resultado, setResultado] = useState<Restauracao | null>(null);
  const { data, error } = useQuery({ queryKey: ["backups"], queryFn: () => api.get<Backups>("/backups") });

  const aposRestaurar = (r: Restauracao) => {
    setResultado(r);
    cliente.invalidateQueries();
  };
  const gerar = useMutation({
    mutationFn: () => api.post<TBackup>("/backups"),
    onSuccess: () => cliente.invalidateQueries({ queryKey: ["backups"] }),
  });
  const excluir = useMutation({
    mutationFn: (nome: string) => api.del(`/backups/${encodeURIComponent(nome)}`),
    onSuccess: () => cliente.invalidateQueries({ queryKey: ["backups"] }),
  });
  const selecao = useExclusaoEmLote({
    itens: data?.itens ?? [],
    chave: (backup) => backup.nome,
    remover: (nome) => api.del(`/backups/${encodeURIComponent(nome)}`),
    titulo: "backups",
    consulta: "backups",
    aposExcluir: () => cliente.invalidateQueries({ queryKey: ["backups"] }),
  });
  const restaurar = useMutation({
    mutationFn: (nome: string) => api.post<Restauracao>(`/backups/${encodeURIComponent(nome)}/restaurar`),
    onSuccess: aposRestaurar,
  });
  const enviar = useMutation({
    mutationFn: (arquivo: File) => api.enviar<Restauracao>("/backups/restaurar-arquivo", arquivo),
    onSuccess: aposRestaurar,
    onSettled: () => {
      if (arquivoRef.current) arquivoRef.current.value = "";
    },
  });

  const ocupado = gerar.isPending || excluir.isPending || restaurar.isPending || enviar.isPending;
  const falha = error ?? gerar.error ?? excluir.error ?? restaurar.error ?? enviar.error;

  return (
    <>
      <h2>Backup e restauração</h2>
      <p className="sutil">
        O app faz um backup automático por dia (mantém os 10 mais recentes). Use “Fazer backup agora” antes de mudanças
        grandes e guarde uma cópia fora deste computador. A restauração substitui todos os dados.
      </p>
      {falha && <div className="erro">{(falha as Error).message}</div>}
      {selecao.acoes}
      {resultado && (
        <div className="aviso">
          Banco restaurado de <strong>{resultado.restaurado}</strong>. Cópia dos dados anteriores:{" "}
          <strong>{resultado.copia_anterior}</strong>.
        </div>
      )}

      {data && !data.disponivel ? (
        <div className="aviso">{data.motivo}</div>
      ) : (
        <>
          <div className="acoes">
            <button disabled={ocupado} onClick={() => gerar.mutate()}>
              {gerar.isPending ? "Gerando…" : "Fazer backup agora"}
            </button>
            <label className="secundario botao-arquivo">
              Restaurar de arquivo…
              <input
                ref={arquivoRef}
                type="file"
                accept=".db,.sqlite,.sqlite3,application/vnd.sqlite3"
                disabled={ocupado}
                hidden
                onChange={(e) => {
                  const arquivo = e.target.files?.[0];
                  if (arquivo && confirm(AVISO_RESTAURAR)) enviar.mutate(arquivo);
                  else e.target.value = "";
                }}
              />
            </label>
          </div>
          {data?.pasta && (
            <p className="sutil">
              Pasta: <code>{data.pasta}</code>
            </p>
          )}

          <table className="tabela compacta">
            <thead>
              <tr>
                <th />
                <th>Data</th>
                <th>Tipo</th>
                <th className="num">Tamanho</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {data?.itens.length === 0 && (
                <tr>
                  <td colSpan={4} className="sutil">
                    Nenhum backup ainda.
                  </td>
                </tr>
              )}
              {data?.itens.map((b) => (
                <tr key={b.nome}>
                  <td>{selecao.checkbox(b.nome)}</td>
                  <td title={b.nome}>{dataHora(b.criado_em)}</td>
                  <td>{TIPO[b.tipo]}</td>
                  <td className="num">{tamanho(b.tamanho)}</td>
                  <td className="num">
                    <a className="link" href={`/api/backups/${encodeURIComponent(b.nome)}`} download={b.nome}>
                      Baixar
                    </a>
                    <button
                      className="link"
                      disabled={ocupado}
                      onClick={() => confirm(AVISO_RESTAURAR) && restaurar.mutate(b.nome)}
                    >
                      Restaurar
                    </button>
                    <button
                      className="link perigo"
                      disabled={ocupado}
                      onClick={() => confirm(`Excluir o backup de ${dataHora(b.criado_em)}?`) && excluir.mutate(b.nome)}
                    >
                      Excluir
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </>
  );
}
