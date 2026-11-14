/** Regras de defasagem da cotação exibida (INT-008). Funções puras: recebem "hoje" para facilitar teste. */

function isoLocal(dia: Date): string {
  const a = dia.getFullYear();
  const m = String(dia.getMonth() + 1).padStart(2, "0");
  const d = String(dia.getDate()).padStart(2, "0");
  return `${a}-${m}-${d}`;
}

function somarDias(dia: Date, dias: number): Date {
  return new Date(dia.getFullYear(), dia.getMonth(), dia.getDate() + dias);
}

/**
 * Último pregão cujo fechamento já deveria estar disponível: o dia útil (seg–sex) anterior a hoje.
 * Sábado, domingo e segunda → sexta anterior. Feriados de bolsa não são considerados.
 */
export function ultimoPregaoEsperado(hoje: Date = new Date()): string {
  let dia = somarDias(hoje, -1);
  while (dia.getDay() === 0 || dia.getDay() === 6) dia = somarDias(dia, -1);
  return isoLocal(dia);
}

/**
 * Indica se a cotação está desatualizada: anterior ao último pregão esperado ou, para cripto
 * (negociada todos os dias), com mais de 1 dia. Sem data de cotação não há o que sinalizar.
 */
export function cotacaoDesatualizada(
  dataCotacao: string | null | undefined,
  classe: string,
  hoje: Date = new Date(),
): boolean {
  if (!dataCotacao) return false;
  const dia = dataCotacao.slice(0, 10);
  const limite = classe === "CRIPTO" ? isoLocal(somarDias(hoje, -1)) : ultimoPregaoEsperado(hoje);
  return dia < limite;
}
