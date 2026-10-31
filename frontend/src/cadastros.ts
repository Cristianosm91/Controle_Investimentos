import { useQuery, type QueryClient } from "@tanstack/react-query";
import { api, query } from "./api";
import type { Ativo, Corretora, Dominio, Ptax } from "./tipos";

const UMA_HORA = 60 * 60 * 1000;

/** Telas calculadas a partir de lançamentos e cotações. */
export function invalidarDerivados(cliente: QueryClient) {
  for (const chave of ["posicoes", "resumo", "rentabilidade", "proventos-matriz"]) {
    cliente.invalidateQueries({ queryKey: [chave] });
  }
}

export function useDominio() {
  return useQuery({ queryKey: ["dominio"], queryFn: () => api.get<Dominio>("/dominio"), staleTime: Infinity });
}

export function useAtivos() {
  return useQuery({ queryKey: ["ativos"], queryFn: () => api.get<Ativo[]>("/ativos"), staleTime: UMA_HORA });
}

export function useCorretoras() {
  return useQuery({ queryKey: ["corretoras"], queryFn: () => api.get<Corretora[]>("/corretoras"), staleTime: UMA_HORA });
}

/** PTAX de venda (Lei 14.754/2023, art. 15) para a data; só consulta quando a moeda não é BRL. */
export function usePtax(moeda: string, data: string) {
  return useQuery({
    queryKey: ["ptax", moeda, data],
    queryFn: () => api.get<Ptax>(`/cambio/ptax${query({ moeda, data })}`),
    enabled: moeda !== "BRL" && /^\d{4}-\d{2}-\d{2}$/.test(data),
    staleTime: UMA_HORA,
    retry: false,
  });
}
