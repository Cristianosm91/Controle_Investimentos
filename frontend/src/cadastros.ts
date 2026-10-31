import { useQuery, type QueryClient } from "@tanstack/react-query";
import { api, query } from "./api";
import type { Ativo, Book, Corretora, Dominio, Estrategia, Parametros, Ptax } from "./tipos";

const UMA_HORA = 60 * 60 * 1000;

/** Telas calculadas a partir de lançamentos, cotações e configurações. */
export function invalidarDerivados(cliente: QueryClient) {
  for (const chave of ["posicoes", "resumo", "rentabilidade", "proventos-matriz", "alocacao", "caixa-saldos", "ir-apuracao", "ir-dirpf", "cripto", "cripto-monitor", "aluguel"]) {
    cliente.invalidateQueries({ queryKey: [chave] });
  }
}

export function useEstrategias() {
  return useQuery({ queryKey: ["estrategias"], queryFn: () => api.get<Estrategia[]>("/estrategias") });
}

export function useBooks() {
  return useQuery({ queryKey: ["books"], queryFn: () => api.get<Book[]>("/books") });
}

export function useParametros() {
  return useQuery({ queryKey: ["parametros"], queryFn: () => api.get<Parametros>("/parametros") });
}

/** Percentual digitado (30) ↔ fração da API (0.3), sem resíduo de ponto flutuante. */
export const paraFracao = (texto: string) => Math.round(Number(texto || 0) * 1e6) / 1e8;
export const paraPercentual = (fracao: number | null | undefined) =>
  fracao === null || fracao === undefined ? "" : String(Math.round(fracao * 1e8) / 1e6);

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
