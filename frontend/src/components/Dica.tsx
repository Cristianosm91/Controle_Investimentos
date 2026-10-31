import { useState, type MouseEvent, type ReactNode } from "react";

export interface PosicaoDica {
  x: number;
  y: number;
}

/** Posição do mouse na janela, para a dica flutuante acompanhar o cursor. */
export function useDica() {
  const [posicao, setPosicao] = useState<PosicaoDica | null>(null);
  return {
    posicao,
    mover: (e: MouseEvent) => setPosicao({ x: e.clientX, y: e.clientY }),
    esconder: () => setPosicao(null),
  };
}

/** Dica exibida logo acima do cursor; vira para a esquerda perto da borda direita da janela. */
export function Dica({ posicao, children }: { posicao: PosicaoDica | null; children: ReactNode }) {
  if (!posicao) return null;
  const pertoDaDireita = posicao.x > window.innerWidth - 180;
  const pertoDoTopo = posicao.y < 70;
  return (
    <div
      className="dica-flutuante"
      role="tooltip"
      style={{
        left: posicao.x,
        top: pertoDoTopo ? posicao.y + 18 : posicao.y - 12,
        transform: `translate(${pertoDaDireita ? "-100%" : "-50%"}, ${pertoDoTopo ? "0" : "-100%"})`,
      }}
    >
      {children}
    </div>
  );
}
