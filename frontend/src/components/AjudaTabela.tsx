import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { AjudaInfo } from "./AjudaInfo";

const EVENTO_ABERTURA_AJUDA = "investhub:abrir-ajuda";

export function AjudaTabela({
  label,
  texto,
  children,
  classe,
}: {
  label: string;
  texto: ReactNode;
  children?: ReactNode;
  classe: string;
}) {
  const id = useId();
  const gatilho = useRef<HTMLButtonElement>(null);
  const dica = useRef<HTMLDivElement>(null);
  const fechamento = useRef<number | undefined>(undefined);
  const [aberta, setAberta] = useState(false);
  const [posicao, setPosicao] = useState<{ esquerda: number; topo: number; acima: boolean } | null>(null);

  const cancelarFechamento = () => {
    if (fechamento.current !== undefined) window.clearTimeout(fechamento.current);
    fechamento.current = undefined;
  };

  const agendarFechamento = () => {
    cancelarFechamento();
    fechamento.current = window.setTimeout(() => {
      const emFoco = gatilho.current === document.activeElement;
      const sobMouse = gatilho.current?.matches(":hover") || dica.current?.matches(":hover");
      if (!emFoco && !sobMouse) setAberta(false);
    }, 120);
  };

  const abrir = (elemento: HTMLButtonElement) => {
    cancelarFechamento();
    const caixa = elemento.getBoundingClientRect();
    const largura = Math.max(1, Math.min(280, window.innerWidth - 24));
    const acima = caixa.bottom + 100 > window.innerHeight && caixa.top > 100;
    setPosicao({
      esquerda: Math.max(12, Math.min(caixa.left, window.innerWidth - largura - 12)),
      topo: acima ? caixa.top - 8 : caixa.bottom + 8,
      acima,
    });
    document.dispatchEvent(new CustomEvent(EVENTO_ABERTURA_AJUDA, { detail: id }));
    setAberta(true);
  };

  useEffect(() => {
    const fecharOutra = (evento: Event) => {
      if (evento instanceof CustomEvent && evento.detail !== id) setAberta(false);
    };
    document.addEventListener(EVENTO_ABERTURA_AJUDA, fecharOutra);
    return () => document.removeEventListener(EVENTO_ABERTURA_AJUDA, fecharOutra);
  }, [id]);

  useEffect(() => {
    if (!aberta) return;
    const fecharAoMover = () => setAberta(false);
    window.addEventListener("scroll", fecharAoMover, true);
    window.addEventListener("resize", fecharAoMover);
    return () => {
      window.removeEventListener("scroll", fecharAoMover, true);
      window.removeEventListener("resize", fecharAoMover);
      cancelarFechamento();
    };
  }, [aberta]);

  const Gatilho = classe === "portfolio-ajuda-icone" ? AjudaInfo : "button";

  return (
    <>
      <Gatilho
        ref={gatilho}
        type="button"
        className={`portfolio-ajuda-gatilho ${classe}`}
        aria-label={label}
        aria-describedby={aberta ? id : undefined}
        onMouseEnter={(evento) => abrir(evento.currentTarget)}
        onMouseLeave={agendarFechamento}
        onFocus={(evento) => abrir(evento.currentTarget)}
        onBlur={agendarFechamento}
        onClick={(evento) => abrir(evento.currentTarget)}
        onKeyDown={(evento) => {
          if (evento.key === "Escape") setAberta(false);
        }}
      >
        {children}
      </Gatilho>
      {aberta && posicao && createPortal(
        <div
          ref={dica}
          id={id}
          role="tooltip"
          className="portfolio-ajuda-tooltip"
          style={{
            left: posicao.esquerda,
            top: posicao.topo,
            transform: posicao.acima ? "translateY(-100%)" : undefined,
          }}
          onMouseEnter={cancelarFechamento}
          onMouseLeave={agendarFechamento}
        >
          {texto}
        </div>,
        document.body,
      )}
    </>
  );
}

export function CabecalhoAjuda({ titulo, texto }: { titulo: string; texto: string }) {
  return (
    <span className="ajuda-tabela-cabecalho">
      {titulo}
      <AjudaTabela label={`Ajuda sobre ${titulo}`} texto={texto} classe="portfolio-ajuda-icone" />
    </span>
  );
}
