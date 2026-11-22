export const LETRAS_METODOLOGIAS: Record<string, Record<string, string>> = {
  ARCA: { "Ações BR": "A", FIIs: "R", Caixa: "C", Exterior: "A" },
  KRAKEN: { Caixa: "K", FIIs: "R", "Ações BR": "A", Cripto: "K", Exterior: "E", Negócios: "N" },
};

export function explicarLetras(nome: string): string {
  const letras = LETRAS_METODOLOGIAS[nome];
  if (!letras) return "";
  const categorias = Object.entries(letras)
    .map(([categoria, letra]) => `${letra} = ${categoria === "FIIs" ? "FIIs (Real Estate)" : categoria}`)
    .join("; ");
  return `${nome}: ${categorias}. `;
}
