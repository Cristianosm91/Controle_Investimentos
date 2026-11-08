import { useQuery } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { api } from "../api";
import { Alertas } from "./Alertas";
import { BotoesExportar, ProvedorExportacao } from "./Exportacao";
import { SeletorInvestidor } from "./SeletorInvestidor";

export const PAGINAS = [
  { caminho: "/", rotulo: "Resumo", icone: "🏠" },
  { caminho: "/portfolio", rotulo: "Portfólio", icone: "💼" },
  { caminho: "/dashboard", rotulo: "Rentabilidade", icone: "📈" },
  { caminho: "/proventos", rotulo: "Proventos", icone: "💰" },
  { caminho: "/aluguel", rotulo: "Aluguel (BTC)", icone: "🤝" },
  { caminho: "/renda-fixa", rotulo: "Renda fixa", icone: "🏛️" },
  { caminho: "/operacoes", rotulo: "Operações", icone: "🔁" },
  { caminho: "/caixa", rotulo: "Caixa", icone: "🏦" },
  { caminho: "/alocacao", rotulo: "Alocação", icone: "⚖️" },
  { caminho: "/metas", rotulo: "Metas", icone: "🎯" },
  { caminho: "/radar", rotulo: "Radar", icone: "📡" },
  { caminho: "/cripto", rotulo: "Cripto", icone: "🪙" },
  { caminho: "/status", rotulo: "Status do ativo", icone: "🔎" },
  { caminho: "/ir", rotulo: "Imposto de Renda", icone: "🧾" },
  { caminho: "/valuation", rotulo: "Valuation", icone: "🧮" },
  { caminho: "/valuations-salvos", rotulo: "Valuations salvos", icone: "🗂️" },
] as const;

export function Layout() {
  return (
    <ProvedorExportacao>
      <Estrutura />
    </ProvedorExportacao>
  );
}

function Estrutura() {
  const conteudo = useRef<HTMLElement>(null);
  const [menuRecolhido, setMenuRecolhido] = useState(
    () => localStorage.getItem("investhub:menu-recolhido") === "true",
  );
  const [drawerAberto, setDrawerAberto] = useState(false);
  const { data: saude } = useQuery({
    queryKey: ["saude"],
    queryFn: () => api.get<{ versao: string }>("/saude"),
    staleTime: Infinity,
  });

  useEffect(() => {
    localStorage.setItem("investhub:menu-recolhido", String(menuRecolhido));
  }, [menuRecolhido]);

  useEffect(() => {
    if (!drawerAberto) return;
    const fecharComEscape = (evento: KeyboardEvent) => {
      if (evento.key === "Escape") setDrawerAberto(false);
    };
    window.addEventListener("keydown", fecharComEscape);
    return () => window.removeEventListener("keydown", fecharComEscape);
  }, [drawerAberto]);

  return (
    <div className={`app${menuRecolhido ? " menu-recolhido" : ""}${drawerAberto ? " drawer-aberto" : ""}`}>
      {drawerAberto && (
        <button
          className="menu-fundo"
          type="button"
          aria-label="Fechar menu"
          onClick={() => setDrawerAberto(false)}
        />
      )}
      <aside className="menu" id="navegacao-principal">
        <div className="marca">
          <span className="marca-titulo">InvestHub+</span>
          {saude?.versao && <small className="versao">v{saude.versao}</small>}
          <button
            className="menu-controle"
            type="button"
            aria-label={menuRecolhido ? "Expandir menu" : "Recolher menu"}
            aria-expanded={!menuRecolhido}
            aria-controls="navegacao-principal"
            title={menuRecolhido ? "Expandir menu" : "Recolher menu"}
            onClick={() => setMenuRecolhido((recolhido) => !recolhido)}
          >
            <span aria-hidden="true">{menuRecolhido ? "›" : "‹"}</span>
          </button>
        </div>
        <nav>
          {PAGINAS.map((p) => (
            <NavLink
              key={p.caminho}
              to={p.caminho}
              end={p.caminho === "/"}
              className="menu-item"
              title={p.rotulo}
              onClick={() => setDrawerAberto(false)}
            >
              <span className="menu-icone" aria-hidden="true">{p.icone}</span>
              <span className="menu-rotulo">{p.rotulo}</span>
            </NavLink>
          ))}
        </nav>
        <NavLink
          to="/configuracoes"
          className="menu-item menu-config"
          title="Configurações"
          onClick={() => setDrawerAberto(false)}
        >
          <span className="menu-icone" aria-hidden="true">⚙️</span>
          <span className="menu-rotulo">Configurações</span>
        </NavLink>
      </aside>
      <div className="principal">
        <header className="topo">
          <button
            className="menu-mobile-controle"
            type="button"
            aria-label="Abrir menu"
            aria-expanded={drawerAberto}
            aria-controls="navegacao-principal"
            onClick={() => setDrawerAberto(true)}
          >
            <span aria-hidden="true">☰</span>
          </button>
          <BotoesExportar alvo={conteudo} />
          <Alertas />
          <SeletorInvestidor />
        </header>
        <main className="conteudo" ref={conteudo}>
          <Outlet />
        </main>
      </div>
    </div>
  );
}