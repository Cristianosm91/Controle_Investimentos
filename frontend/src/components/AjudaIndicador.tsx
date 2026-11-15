import { useEffect, useId, useState } from "react";
import { AjudaInfo } from "./AjudaInfo";

const EVENTO_ABERTURA = "investhub:abrir-ajuda";

export function AjudaIndicador({ titulo, texto }: { titulo: string; texto: string }) {
  const id = useId();
  const [aberta, setAberta] = useState(false);
  const [posicao, setPosicao] = useState({ esquerda: 0, acima: false });

  useEffect(() => {
    const fecharOutra = (evento: Event) => {
      if (evento instanceof CustomEvent && evento.detail !== id) setAberta(false);
    };
    document.addEventListener(EVENTO_ABERTURA, fecharOutra);
    return () => document.removeEventListener(EVENTO_ABERTURA, fecharOutra);
  }, [id]);

  const abrir = (elemento: HTMLElement) => {
    const caixa = elemento.getBoundingClientRect();
    const largura = Math.min(300, window.innerWidth * 0.75);
    setPosicao({
      esquerda: Math.min(0, window.innerWidth - caixa.left - largura - 12),
      acima: caixa.bottom + 180 > window.innerHeight && caixa.top > 180,
    });
    document.dispatchEvent(new CustomEvent(EVENTO_ABERTURA, { detail: id }));
    setAberta(true);
  };

  return (
    <span className="ajuda-indicador" onMouseEnter={(evento) => abrir(evento.currentTarget)} onMouseLeave={(evento) => {
      if (!evento.currentTarget.contains(document.activeElement)) setAberta(false);
    }}>
      <AjudaInfo
        className="ajuda-indicador-botao"
        aria-label={`Ajuda sobre ${titulo}`}
        aria-describedby={aberta ? id : undefined}
        aria-expanded={aberta}
        onFocus={(evento) => abrir(evento.currentTarget)}
        onBlur={() => setAberta(false)}
        onClick={(evento) => abrir(evento.currentTarget)}
        onKeyDown={(evento) => {
          if (evento.key === "Escape") setAberta(false);
        }}
      />
      {aberta && (
        <span
          id={id}
          role="tooltip"
          className="ajuda-indicador-texto"
          style={{ left: posicao.esquerda, top: posicao.acima ? "auto" : "100%", bottom: posicao.acima ? "100%" : "auto" }}
        >
          {texto}
        </span>
      )}
    </span>
  );
}
