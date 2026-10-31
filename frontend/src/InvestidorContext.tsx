import { useQuery } from "@tanstack/react-query";
import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api } from "./api";
import type { Grupo, Investidor } from "./tipos";

const CHAVE = "controleinv.investidores";

interface ContextoInvestidor {
  investidores: Investidor[];
  grupos: Grupo[];
  /** IDs selecionados; vazio = todos. */
  selecionados: number[];
  setSelecionados: (ids: number[]) => void;
  /** Valor pronto para o parâmetro `investidores` da API. */
  filtro: string | undefined;
}

const Contexto = createContext<ContextoInvestidor | null>(null);

function lerSalvo(): number[] {
  try {
    const valor = JSON.parse(localStorage.getItem(CHAVE) ?? "[]");
    return Array.isArray(valor) ? valor.filter((n) => Number.isInteger(n)) : [];
  } catch {
    return [];
  }
}

export function ProvedorInvestidor({ children }: { children: ReactNode }) {
  const [selecionados, setSelecionados] = useState<number[]>(lerSalvo);
  const { data: investidores = [] } = useQuery({
    queryKey: ["investidores"],
    queryFn: () => api.get<Investidor[]>("/investidores"),
  });
  const { data: grupos = [] } = useQuery({ queryKey: ["grupos"], queryFn: () => api.get<Grupo[]>("/grupos") });

  useEffect(() => localStorage.setItem(CHAVE, JSON.stringify(selecionados)), [selecionados]);

  // Remove da seleção investidores excluídos.
  useEffect(() => {
    if (!investidores.length) return;
    const validos = selecionados.filter((id) => investidores.some((i) => i.id === id));
    if (validos.length !== selecionados.length) setSelecionados(validos);
  }, [investidores, selecionados]);

  const valor = useMemo(
    () => ({
      investidores,
      grupos,
      selecionados,
      setSelecionados,
      filtro: selecionados.length ? selecionados.join(",") : undefined,
    }),
    [investidores, grupos, selecionados],
  );
  return <Contexto.Provider value={valor}>{children}</Contexto.Provider>;
}

export function useInvestidor(): ContextoInvestidor {
  const ctx = useContext(Contexto);
  if (!ctx) throw new Error("useInvestidor fora de ProvedorInvestidor");
  return ctx;
}
