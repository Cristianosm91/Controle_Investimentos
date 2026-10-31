import { useQuery } from "@tanstack/react-query";
import { useRef } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { api } from "../api";
import { BotoesExportar, ProvedorExportacao } from "./Exportacao";
import { SeletorInvestidor } from "./SeletorInvestidor";

export const PAGINAS = [
  { caminho: "/", rotulo: "Resumo", icone: "🏠" },
  { caminho: "/portfolio", rotulo: "Portfólio", icone: "💼" },
  { caminho: "/dashboard", rotulo: "Rentabilidade", icone: "📈" },
  { caminho: "/proventos", rotulo: "Proventos", icone: "💰" },
  { caminho: "/aluguel", rotulo: "Aluguel (BTC)", icone: "🤝" },
  { caminho: "/operacoes", rotulo: "Operações", icone: "🔁" },
  { caminho: "/caixa", rotulo: "Caixa", icone: "🏦" },
  { caminho: "/alocacao", rotulo: "Alocação", icone: "⚖️" },
  { caminho: "/radar", rotulo: "Radar", icone: "📡" },
  { caminho: "/cripto", rotulo: "Cripto", icone: "🪙" },
  { caminho: "/status", rotulo: "Status do ativo", icone: "🔎" },
  { caminho: "/ir", rotulo: "Imposto de Renda", icone: "🧾" },
  { caminho: "/valuation", rotulo: "Valuation", icone: "🧮" },
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
  const { data: saude } = useQuery({
    queryKey: ["saude"],
    queryFn: () => api.get<{ versao: string }>("/saude"),
    staleTime: Infinity,
  });
  return (
    <div className="app">
      <aside className="menu">
        <div className="marca">
          InvestHub+
          {saude?.versao && <small className="versao">v{saude.versao}</small>}
        </div>
        <nav>
          {PAGINAS.map((p) => (
            <NavLink key={p.caminho} to={p.caminho} end={p.caminho === "/"} className="menu-item">
              <span className="menu-icone">{p.icone}</span>
              {p.rotulo}
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