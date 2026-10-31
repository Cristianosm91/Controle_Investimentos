import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../api";
import { invalidarDerivados } from "../cadastros";

interface Props {
  recurso: string;
  id: number;
  descricao: string;
  aoEditar: () => void;
}

export function AcoesLinha({ recurso, id, descricao, aoEditar }: Props) {
  const cliente = useQueryClient();
  const excluir = useMutation({
    mutationFn: () => api.del(`/${recurso}/${id}`),
    onSuccess: () => {
      cliente.invalidateQueries({ queryKey: [recurso] });
      invalidarDerivados(cliente);
    },
    onError: (erro) => alert((erro as Error).message),
  });
  return (
    <>
      <button className="link" onClick={aoEditar}>
        Editar
      </button>
      <button
        className="link perigo"
        disabled={excluir.isPending}
        onClick={() => confirm(`Excluir ${descricao}?`) && excluir.mutate()}
      >
        Excluir
      </button>
    </>
  );
}
