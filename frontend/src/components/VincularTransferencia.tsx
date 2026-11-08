import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { api, query } from "../api";
import { invalidarDerivados } from "../cadastros";
import { data, numero } from "../formato";
import type { Operacao, Pagina } from "../tipos";
import { Modal } from "./Modal";

export function VincularTransferencia({
  operacao,
  aoFechar,
}: {
  operacao: Operacao;
  aoFechar: () => void;
}) {
  const cliente = useQueryClient();
  const [operacaoId, setOperacaoId] = useState("");
  const [busca, setBusca] = useState("");
  const { data: candidatas = [], isLoading, error } = useQuery({
    queryKey: ["operacoes", "transferencias-vinculaveis", operacao.id],
    queryFn: async () => {
      const itens: Operacao[] = [];
      let total = 0;
      do {
        const pagina = await api.get<Pagina<Operacao>>(
          `/operacoes${query({
            investidores: operacao.investidor_id,
            evento: "TRANSFERENCIA",
            limite: 1000,
            deslocamento: itens.length,
          })}`,
        );
        itens.push(...pagina.itens);
        total = pagina.total;
        if (!pagina.itens.length) break;
      } while (itens.length < total);
      return itens.filter(
        (item) =>
          item.id !== operacao.id &&
          item.ativo_id !== operacao.ativo_id &&
          !item.transferencia_pareada_id &&
          Math.sign(item.quantidade) === -Math.sign(operacao.quantidade),
      );
    },
  });
  const filtradas = candidatas.filter((candidata) =>
    `${candidata.ticker} ${candidata.data} ${candidata.quantidade}`.toLowerCase().includes(busca.trim().toLowerCase()),
  );
  const vincular = useMutation({
    mutationFn: (id: number) =>
      api.post<Operacao[]>(`/operacoes/${operacao.id}/vinculo-transferencia`, { operacao_id: id }),
    onSuccess: () => {
      cliente.invalidateQueries({ queryKey: ["operacoes"] });
      invalidarDerivados(cliente);
      aoFechar();
    },
  });

  const enviar = (evento: FormEvent) => {
    evento.preventDefault();
    if (operacaoId) vincular.mutate(Number(operacaoId));
  };

  return (
    <Modal titulo="Vincular pernas da troca" aoFechar={aoFechar}>
      <form className="formulario em-modal" onSubmit={enviar}>
        <p className="sutil">
          {operacao.ticker} · {data(operacao.data)} · quantidade {numero(operacao.quantidade, 8)}
        </p>
        {error && <div className="erro">{(error as Error).message}</div>}
        {vincular.error && <div className="erro">{(vincular.error as Error).message}</div>}
        {isLoading ? (
          <p>Buscando operações compatíveis…</p>
        ) : candidatas.length ? (
          <>
            <label>
              Buscar ticker ou data
              <input value={busca} onChange={(e) => setBusca(e.target.value)} />
            </label>
            <label>
              Operação oposta
              <select required value={operacaoId} onChange={(e) => setOperacaoId(e.target.value)}>
                <option value="">Selecione</option>
                {filtradas.map((candidata) => (
                  <option key={candidata.id} value={candidata.id}>
                    {candidata.ticker} · {data(candidata.data)} · {numero(candidata.quantidade, 8)}
                  </option>
                ))}
              </select>
            </label>
            {!filtradas.length && <p className="sutil">Nenhuma operação corresponde à busca.</p>}
          </>
        ) : (
          <p className="sutil">Nenhuma entrada ou saída oposta, de outro ativo e ainda sem vínculo foi encontrada.</p>
        )}
        <div className="acoes largura-total">
          <button type="submit" disabled={!operacaoId || vincular.isPending}>
            {vincular.isPending ? "Vinculando…" : "Vincular"}
          </button>
          <button type="button" className="secundario" onClick={aoFechar}>
            Cancelar
          </button>
        </div>
      </form>
    </Modal>
  );
}
