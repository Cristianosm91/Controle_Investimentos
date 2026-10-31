import type { Benchmark } from "./tipos";

export const CORES_BENCHMARK: Record<Benchmark, string> = { ibov: "#f59e0b", ifix: "#8b5cf6", cdi: "#10b981", ipca: "#ef4444" };
export const NOMES_BENCHMARK: Record<Benchmark, string> = { ibov: "IBOV", ifix: "IFIX", cdi: "CDI", ipca: "IPCA" };
export const BENCHMARKS = Object.keys(NOMES_BENCHMARK) as Benchmark[];
