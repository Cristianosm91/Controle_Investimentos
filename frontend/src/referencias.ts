import type { Benchmark, ModeloValuation } from "./tipos";

export const CORES_BENCHMARK: Record<Benchmark, string> = { ibov: "#f59e0b", ifix: "#8b5cf6", cdi: "#64748b", ipca: "#ef4444" };
export const NOMES_BENCHMARK: Record<Benchmark, string> = { ibov: "IBOV", ifix: "IFIX", cdi: "CDI", ipca: "IPCA" };
export const BENCHMARKS = Object.keys(NOMES_BENCHMARK) as Benchmark[];

export const MODELOS_VALUATION: { id: ModeloValuation["id"]; rotulo: string }[] = [
  { id: "graham", rotulo: "Graham" },
  { id: "bazin", rotulo: "Bazin (DY de 6%)" },
  { id: "dcf_fcfe", rotulo: "DCF (FCFE, 5 anos)" },
  { id: "gordon", rotulo: "Gordon (dividendos)" },
  { id: "pl_historico", rotulo: "P/L histórico" },
  { id: "pl_setor", rotulo: "P/L do setor" },
  { id: "pvp_justificado", rotulo: "P/VP justificado" },
];
