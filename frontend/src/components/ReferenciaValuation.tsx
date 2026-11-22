import { MODELOS_VALUATION } from "../referencias";
import type { CalculoValuation, ModeloValuation } from "../tipos";

export type ReferenciaValuation = "media" | ModeloValuation["id"];

export function precoReferencia(calculo: CalculoValuation | undefined, referencia: ReferenciaValuation): number | null {
  if (!calculo) return null;
  if (referencia !== "media") return calculo.modelos[referencia] ?? null;
  const valores = MODELOS_VALUATION.map((modelo) => calculo.modelos[modelo.id])
    .filter((valor): valor is number => valor !== null && Number.isFinite(valor));
  return valores.length ? valores.reduce((soma, valor) => soma + valor, 0) / valores.length : null;
}

export function margemSeguranca(preco: number | null, cotacao: number | null): number | null {
  return preco !== null && Number.isFinite(preco) && preco > 0 &&
    cotacao !== null && Number.isFinite(cotacao) && cotacao >= 0
    ? (preco - cotacao) / preco
    : null;
}

export function SeletorReferenciaValuation({
  valor,
  onChange,
}: {
  valor: ReferenciaValuation;
  onChange: (valor: ReferenciaValuation) => void;
}) {
  return (
    <label className="check valuation-referencia">
      Referência da margem
      <select value={valor} onChange={(evento) => onChange(evento.target.value as ReferenciaValuation)}>
        <option value="media">Média dos modelos disponíveis</option>
        {MODELOS_VALUATION.map((modelo) => (
          <option key={modelo.id} value={modelo.id}>{modelo.rotulo}</option>
        ))}
      </select>
    </label>
  );
}
