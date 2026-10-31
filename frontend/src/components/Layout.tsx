import { useRef } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { BotoesExportar, ProvedorExportacao } from "./Exportacao";
import { SeletorInvestidor } from "./SeletorInvestidor";

export const PAGINAS = [
  { caminho: "/", rotulo: "Resumo", icone: "🏠" },
  { caminho: "/portfolio", rotulo: "Portfólio", icone: "💼" },
  { caminho: "/dashboard", rotulo: "Rentabilidade", icone: "📈" },
  { caminho: "/proventos", rotulo: "Proventos", icone: "💰" },
  { caminho: "/operacoes", rotulo: "Operações", icone: "🔁" },
  { caminho: "/caixa", rotulo: "Caixa", icone: "🏦" },
  { caminho: "/alocacao", rotulo: "Alocação", icone: "⚖️" },
  { caminho: "/radar", rotulo: "Radar", icone: "📡", fase: 5 },
  { caminho: "/cripto", rotulo: "Cripto", icone: "🪙", fase: 5 },
  { caminho: "/status", rotulo: "Status do ativo", icone: "🔎", fase: 5 },
  { caminho: "/ir", rotulo: "Imposto de Renda", icone: "🧾" },
  { caminho: "/valuation", rotulo: "Valuation", icone: "🧮", fase: 5 },
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
  return (
    <div className="app">
      <aside className="menu">
        <div className="marca">InvestHub+</div>
        <nav>
          {PAGINAS.map((p) => (
            <NavLink key={p.caminho} to={p.caminho} end={p.caminho === "/"} className="menu-item">
              <span className="menu-icone">{p.icone}</span>
              {p.rotulo}
              {"fase" in p && <span className="menu-fase">F{p.fase}</span>}
            </NavLink>
          ))}
        </nav>
        <NavLink to="/configuracoes" className="menu-item menu-config">
          <span className="menu-icone">⚙️</span>
          Configurações
        </NavLink>
      </aside>
      <div className="principal">
        <header className="topo">
          <BotoesExportar alvo={conteudo} />
          <SeletorInvestidor />
        </header>
        <main className="conteudo" ref={conteudo}>
          <Outlet />
        </main>
      </div>
    </div>
  );
}