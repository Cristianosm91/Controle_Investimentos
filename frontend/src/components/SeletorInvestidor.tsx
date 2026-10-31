import { useEffect, useRef, useState } from "react";
import { useInvestidor } from "../InvestidorContext";

export function SeletorInvestidor() {
  const { investidores, grupos, selecionados, setSelecionados } = useInvestidor();
  const [aberto, setAberto] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const ativos = investidores.filter((i) => i.ativo);

  useEffect(() => {
    const fechar = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setAberto(false);
    };
    document.addEventListener("mousedown", fechar);
    return () => document.removeEventListener("mousedown", fechar);
  }, []);

  const rotulo =
    selecionados.length === 0
      ? "Todos os investidores"
      : selecionados.length === 1
        ? (investidores.find((i) => i.id === selecionados[0])?.nome ?? "1 investidor")
        : `${selecionados.length} investidores`;

  const alternar = (id: number) =>
    setSelecionados(selecionados.includes(id) ? selecionados.filter((s) => s !== id) : [...selecionados, id]);

  const selecionarGrupo = (grupoId: number) =>
    setSelecionados(ativos.filter((i) => i.grupo_id === grupoId).map((i) => i.id));

  return (
    <div className="seletor" ref={ref}>
      <button className="seletor-botao" onClick={() => setAberto(!aberto)} aria-expanded={aberto}>
        <span className="seletor-icone">👤</span> {rotulo} ▾
      </button>
      {aberto && (
        <div className="seletor-menu" role="menu">
          <label className="seletor-item">
            <input type="checkbox" checked={selecionados.length === 0} onChange={() => setSelecionados([])} />
            <strong>Todos</strong>
          </label>
          {grupos.length > 0 && <div className="seletor-titulo">Grupos</div>}
          {grupos.map((g) => (
            <button key={g.id} className="seletor-item seletor-grupo" onClick={() => selecionarGrupo(g.id)}>
              {g.nome}
            </button>
          ))}
          <div className="seletor-titulo">Investidores</div>
          {ativos.map((i) => (
            <label key={i.id} className="seletor-item">
              <input type="checkbox" checked={selecionados.includes(i.id)} onChange={() => alternar(i.id)} />
              <span className="bolinha" style={{ background: i.cor }} />
              {i.nome}
            </label>
          ))}
          {ativos.length === 0 && <div className="seletor-vazio">Cadastre investidores em Configurações</div>}
        </div>
      )}
    </div>
  );
}
