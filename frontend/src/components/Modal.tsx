import { useEffect, useId, useRef, type KeyboardEvent as KeyboardEventReact, type ReactNode } from "react";

interface Props {
  titulo: string;
  aoFechar: () => void;
  children: ReactNode;
  largo?: boolean;
}

const FOCAVEIS =
  'a[href], button:not([disabled]), input:not([disabled]):not([type="hidden"]), select:not([disabled]), textarea:not([disabled]), summary, [tabindex]:not([tabindex="-1"])';

/** Modais abertos, do mais antigo ao mais recente: só o do topo reage ao Esc. */
const pilha: HTMLElement[] = [];

function focaveis(raiz: HTMLElement): HTMLElement[] {
  return Array.from(raiz.querySelectorAll<HTMLElement>(FOCAVEIS)).filter(
    (el) => !el.closest("[aria-hidden='true']") && el.getClientRects().length > 0,
  );
}

export function Modal({ titulo, aoFechar, children, largo = false }: Props) {
  const dialogo = useRef<HTMLDivElement>(null);
  const idTitulo = useId();

  // Ao abrir, leva o foco para o primeiro campo do diálogo; ao fechar, devolve-o a quem abriu.
  useEffect(() => {
    const el = dialogo.current;
    if (!el) return;
    const gatilho = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    pilha.push(el);
    const corpo = focaveis(el).filter((f) => !f.closest(".modal-topo"));
    if (!el.contains(document.activeElement)) (corpo[0] ?? el).focus();
    return () => {
      const i = pilha.lastIndexOf(el);
      if (i >= 0) pilha.splice(i, 1);
      if (gatilho?.isConnected) gatilho.focus();
    };
  }, []);

  useEffect(() => {
    const tecla = (e: KeyboardEvent) => {
      if (e.key === "Escape" && pilha[pilha.length - 1] === dialogo.current) aoFechar();
    };
    window.addEventListener("keydown", tecla);
    return () => window.removeEventListener("keydown", tecla);
  }, [aoFechar]);

  const prenderFoco = (e: KeyboardEventReact<HTMLDivElement>) => {
    if (e.key !== "Tab" || !dialogo.current) return;
    const lista = focaveis(dialogo.current);
    if (!lista.length) {
      e.preventDefault();
      return;
    }
    const primeiro = lista[0];
    const ultimo = lista[lista.length - 1];
    const atual = document.activeElement;
    if (e.shiftKey && (atual === primeiro || atual === dialogo.current)) {
      e.preventDefault();
      ultimo.focus();
    } else if (!e.shiftKey && (atual === ultimo || !dialogo.current.contains(atual))) {
      e.preventDefault();
      primeiro.focus();
    }
  };

  return (
    <div className="modal-fundo" onMouseDown={(e) => e.target === e.currentTarget && aoFechar()}>
      <div
        ref={dialogo}
        className={largo ? "modal largo" : "modal"}
        role="dialog"
        aria-modal="true"
        aria-labelledby={idTitulo}
        tabIndex={-1}
        onKeyDown={prenderFoco}
      >
        <div className="modal-topo">
          <h3 id={idTitulo}>{titulo}</h3>
          <button type="button" className="link" onClick={aoFechar} aria-label="Fechar">
            ✕
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}
