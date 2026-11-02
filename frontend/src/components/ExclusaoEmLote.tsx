import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { invalidarDerivados } from "../cadastros";

interface Props<T, K extends number | string> {
  itens: T[];
  chave: (item: T) => K;
  remover: (id: K) => Promise<unknown>;
  titulo: string;
  consulta: string;
  rotuloAcao?: string;
  rotuloResultado?: string;
  aposExcluir?: () => void;
}

export function useExclusaoEmLote<T, K extends number | string>({
  itens,
  chave,
  remover,
  titulo,
  consulta,
  rotuloAcao = "Excluir",
  rotuloResultado = "registro(s) excluído(s)",
  aposExcluir,
}: Props<T, K>) {
  const cliente = useQueryClient();
  const [selecionados, setSelecionados] = useState<Set<K>>(new Set());
  const [resultado, setResultado] = useState<string | null>(null);
  const mutacao = useMutation({
    mutationFn: async (ids: K[]) => {
      let excluidos = 0;
      const falhas: string[] = [];
      for (const id of ids) {
        try {
          await remover(id);
          excluidos += 1;
        } catch (erro) {
          falhas.push(`${id}: ${(erro as Error).message}`);
        }
      }
      return { excluidos, falhas };
    },
    onSuccess: ({ excluidos, falhas }) => {
      cliente.invalidateQueries({ queryKey: [consulta] });
      invalidarDerivados(cliente);
      aposExcluir?.();
      setSelecionados(new Set());
      setResultado(
        falhas.length
          ? `${excluidos} excluído(s); ${falhas.length} falha(s): ${falhas.join("; ")}`
          : `${excluidos} ${rotuloResultado}.`,
      );
    },
  });
  const ids = itens.map(chave);
  const idsSelecionados = ids.filter((id) => selecionados.has(id));
  const todosSelecionados = ids.length > 0 && ids.every((id) => selecionados.has(id));
  const alternar = (id: K) => {
    setSelecionados((atual) => {
      const proxima = new Set(atual);
      if (proxima.has(id)) proxima.delete(id);
      else proxima.add(id);
      return proxima;
    });
  };
  const alternarTodos = () => {
    setSelecionados((atual) => {
      const proxima = new Set(atual);
      if (todosSelecionados) ids.forEach((id) => proxima.delete(id));
      else ids.forEach((id) => proxima.add(id));
      return proxima;
    });
  };
  const executar = (alvos: K[], todos = false) => {
    if (!alvos.length) return;
    const texto = todos
      ? `${rotuloAcao} todos os ${alvos.length} registro(s) de ${titulo}?`
      : `${rotuloAcao} ${alvos.length} registro(s) selecionado(s) de ${titulo}?`;
    if (confirm(texto)) mutacao.mutate(alvos);
  };
  const checkbox = (id: K) => (
    <input
      type="checkbox"
      aria-label={`Selecionar registro ${id}`}
      checked={selecionados.has(id)}
      onChange={() => alternar(id)}
    />
  );
  const acoes = (
    <div className="acoes">
      <label className="check">
        <input type="checkbox" checked={todosSelecionados} onChange={alternarTodos} />
        Selecionar todos ({ids.length})
      </label>
      <button
        className="secundario"
        disabled={!idsSelecionados.length || mutacao.isPending}
        onClick={() => executar(idsSelecionados)}
      >
        {mutacao.isPending ? `${rotuloAcao}…` : `${rotuloAcao} selecionados (${idsSelecionados.length})`}
      </button>
      <button
        className="link perigo"
        disabled={!ids.length || mutacao.isPending}
        onClick={() => executar(ids, true)}
      >
        {rotuloAcao} todos
      </button>
      {resultado && <span className={resultado.includes("falha(s)") ? "negativo" : "positivo"}>{resultado}</span>}
    </div>
  );

  return { acoes, checkbox, erro: mutacao.error };
}
