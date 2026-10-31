import { useEffect, useState } from "react";
import { useInvestidor } from "../InvestidorContext";

/** IR é por CPF: parte da seleção do topo quando há um único investidor marcado. */
export function useInvestidorIR(): [number | undefined, (id: number) => void] {
  const { investidores, selecionados } = useInvestidor();
  const [id, setId] = useState<number | undefined>();

  useEffect(() => {
    if (selecionados.length === 1) setId(selecionados[0]);
  }, [selecionados]);

  useEffect(() => {
    if (id === undefined || !investidores.some((i) => i.id === id)) {
      setId(selecionados.length === 1 ? selecionados[0] : investidores[0]?.id);
    }
  }, [investidores, selecionados, id]);

  return [id, setId];
}

export function SeletorInvestidorIR({ valor, aoMudar }: { valor: number | undefined; aoMudar: (id: number) => void }) {
  const { investidores } = useInvestidor();
  if (investidores.length < 2) return null;
  return (
    <label className="check">
      Investidor (CPF)
      <select value={valor ?? ""} onChange={(e) => aoMudar(Number(e.target.value))}>
        {investidores.map((i) => (
          <option key={i.id} value={i.id}>
            {i.nome}
          </option>
        ))}
      </select>
    </label>
  );
}
