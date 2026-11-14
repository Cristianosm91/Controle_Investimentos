import { data } from "../formato";

/** Selo textual (não só cor) para cotação anterior ao último pregão esperado. */
export function SeloCotacaoAntiga({ dataCotacao }: { dataCotacao: string }) {
  return (
    <span
      className="etiqueta cotacao-antiga"
      data-exportar="ignorar"
      title={`Cotação desatualizada: a última disponível é de ${data(dataCotacao)}.`}
    >
      Cotação de {data(dataCotacao).slice(0, 5)}
      <span className="visualmente-oculto"> (desatualizada)</span>
    </span>
  );
}
