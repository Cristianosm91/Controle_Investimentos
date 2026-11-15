import { useMutation, useQuery } from "@tanstack/react-query";
import { useId, useState } from "react";
import { api } from "../../api";
import type { Investidor, PreviaExclusaoInvestidor, ResultadoExclusaoInvestidor } from "../../tipos";
import { Modal } from "../Modal";

interface Props {
  investidor: Investidor;
  aoFechar: () => void;
  aoExcluir: (resultado: ResultadoExclusaoInvestidor) => void;
}

/** Exclusão do investidor com todos os dados vinculados (PRI-001): prévia, backup obrigatório e confirmação pelo nome. */
export function ExclusaoInvestidor({ investidor, aoFechar, aoExcluir }: Props) {
  const [confirmacao, setConfirmacao] = useState("");
  const idAjuda = useId();
  const previa = useQuery({
    queryKey: ["investidor-exclusao", investidor.id],
    queryFn: () => api.get<PreviaExclusaoInvestidor>(`/investidores/${investidor.id}/exclusao`),
    staleTime: 0,
    gcTime: 0,
    retry: false,
  });
  const excluir = useMutation({
    // api.del é tipado como void, mas devolve o corpo JSON quando a resposta não é 204.
    mutationFn: async () =>
      (await api.del(`/investidores/${investidor.id}/completo`)) as unknown as ResultadoExclusaoInvestidor,
    onSuccess: aoExcluir,
  });

  const nome = previa.data?.investidor.nome ?? investidor.nome;
  const contagens = Object.entries(previa.data?.contagens ?? {});
  const total = contagens.reduce((s, [, n]) => s + n, 0);
  const backupDisponivel = previa.data?.backup_disponivel ?? false;
  const nomeConfere = confirmacao.trim() === nome.trim();
  const podeExcluir = !!previa.data && backupDisponivel && nomeConfere && !excluir.isPending;

  return (
    <Modal titulo={`Excluir ${nome} com todos os dados`} aoFechar={aoFechar}>
      {previa.isLoading && <p role="status">Carregando os dados vinculados…</p>}
      {previa.error && (
        <div className="erro" role="alert">
          Não foi possível consultar os dados vinculados: {(previa.error as Error).message}
        </div>
      )}
      {previa.data && (
        <form
          className="formulario em-modal"
          onSubmit={(e) => {
            e.preventDefault();
            if (podeExcluir) excluir.mutate();
          }}
        >
          <div className="erro largura-total" role="note">
            <strong>Esta ação é irreversível.</strong> O investidor <strong>{nome}</strong> e todos os registros
            vinculados a ele serão excluídos definitivamente.
          </div>
          <div className="largura-total">
            {contagens.length ? (
              <table className="tabela compacta">
                <caption className="visualmente-oculto">Registros que serão excluídos</caption>
                <thead>
                  <tr>
                    <th scope="col">Dados vinculados</th>
                    <th scope="col" className="num">
                      Registros
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {contagens.map(([rotulo, n]) => (
                    <tr key={rotulo}>
                      <td>{rotulo}</td>
                      <td className="num">{n.toLocaleString("pt-BR")}</td>
                    </tr>
                  ))}
                </tbody>
                <tfoot>
                  <tr>
                    <td>
                      <strong>Total</strong>
                    </td>
                    <td className="num">
                      <strong>{total.toLocaleString("pt-BR")}</strong>
                    </td>
                  </tr>
                </tfoot>
              </table>
            ) : (
              <p className="sutil">Nenhum registro vinculado além do cadastro do investidor.</p>
            )}
          </div>
          {backupDisponivel ? (
            <p className="largura-total">
              Antes de excluir, um backup completo do banco será criado automaticamente. A exclusão só acontece se o
              backup for gerado com sucesso.
            </p>
          ) : (
            <div className="aviso largura-total" role="alert">
              O backup automático não está disponível neste momento, e ele é obrigatório para esta exclusão. Verifique a
              seção Backup das Configurações e tente novamente.
            </div>
          )}
          <label className="largura-total">
            Para confirmar, digite o nome do investidor: <strong>{nome}</strong>
            <input
              value={confirmacao}
              onChange={(e) => setConfirmacao(e.target.value)}
              autoComplete="off"
              spellCheck={false}
              disabled={!backupDisponivel}
              aria-describedby={idAjuda}
              aria-invalid={confirmacao !== "" && !nomeConfere}
            />
            <small id={idAjuda} className="sutil">
              O botão de exclusão só é liberado quando o nome digitado for igual ao cadastrado.
            </small>
          </label>
          {excluir.error && (
            <div className="erro largura-total" role="alert">
              {(excluir.error as Error).message}
            </div>
          )}
          <div className="acoes largura-total">
            <button type="button" className="secundario" onClick={aoFechar}>
              Cancelar
            </button>
            <button type="submit" className="botao-perigo" disabled={!podeExcluir}>
              {excluir.isPending ? "Criando backup e excluindo…" : "Excluir com todos os dados"}
            </button>
          </div>
        </form>
      )}
    </Modal>
  );
}
