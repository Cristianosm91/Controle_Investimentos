import { useEffect, useRef, useState } from "react";

/** "dd/mm/aaaa" completo e válido → "aaaa-mm-dd"; vazio → ""; incompleto/inválido → null. */
function paraIso(texto: string): string | null {
  if (!texto) return "";
  const m = /^(\d{2})\/(\d{2})\/(\d{4})$/.exec(texto);
  if (!m) return null;
  const [, dia, mes, ano] = m;
  const d = new Date(Number(ano), Number(mes) - 1, Number(dia));
  if (d.getFullYear() !== Number(ano) || d.getMonth() !== Number(mes) - 1 || d.getDate() !== Number(dia)) return null;
  return `${ano}-${mes}-${dia}`;
}

function paraTexto(iso: string): string {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso);
  return m ? `${m[3]}/${m[2]}/${m[1]}` : "";
}

function mascarar(bruto: string): string {
  const d = bruto.replace(/\D/g, "").slice(0, 8);
  return [d.slice(0, 2), d.slice(2, 4), d.slice(4)].filter(Boolean).join("/");
}

interface Props {
  /** Data ISO (aaaa-mm-dd) ou "". */
  valor: string;
  aoMudar: (iso: string) => void;
  required?: boolean;
  title?: string;
}

/** Campo de data sempre em dd/mm/aaaa, independente do idioma do navegador; o calendário nativo segue disponível. */
export function CampoData({ valor, aoMudar, required, title }: Props) {
  const [texto, setTexto] = useState(() => paraTexto(valor));
  const nativo = useRef<HTMLInputElement>(null);

  useEffect(() => {
    setTexto((atual) => (paraIso(atual) === valor ? atual : paraTexto(valor)));
  }, [valor]);

  const digitar = (bruto: string) => {
    const formatado = mascarar(bruto);
    setTexto(formatado);
    const iso = paraIso(formatado);
    if (iso !== null && iso !== valor) aoMudar(iso);
  };

  const abrirCalendario = () => {
    const campo = nativo.current;
    if (!campo) return;
    if (typeof campo.showPicker === "function") campo.showPicker();
    else campo.focus();
  };

  return (
    <span className="campo-data">
      <input
        type="text"
        inputMode="numeric"
        placeholder="dd/mm/aaaa"
        pattern="\d{2}/\d{2}/\d{4}"
        required={required}
        title={title}
        aria-label={title}
        value={texto}
        onChange={(e) => digitar(e.target.value)}
        onBlur={() => paraIso(texto) === null && setTexto(paraTexto(valor))}
      />
      <button type="button" className="campo-data-calendario" onClick={abrirCalendario} aria-label="Abrir calendário" title="Abrir calendário">
        📅
      </button>
      <input
        ref={nativo}
        type="date"
        className="campo-data-nativo"
        tabIndex={-1}
        aria-hidden="true"
        value={valor}
        onChange={(e) => aoMudar(e.target.value)}
      />
    </span>
  );
}
