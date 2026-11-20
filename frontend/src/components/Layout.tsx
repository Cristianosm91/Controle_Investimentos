import { useQuery } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { api } from "../api";
import { Alertas } from "./Alertas";
import { BotoesExportar, ProvedorExportacao } from "./Exportacao";
import { Icone } from "./Icone";
import { SeletorInvestidor } from "./SeletorInvestidor";

export const PAGINAS = [
  { caminho: "/", rotulo: "Resumo", icone: "home" },
  { caminho: "/portfolio", rotulo: "Portfólio", icone: "briefcase" },
  { caminho: "/dashboard", rotulo: "Rentabilidade", icone: "chart" },
  { caminho: "/conciliacao", rotulo: "Conciliação", icone: "search" },
  { caminho: "/proventos", rotulo: "Proventos", icone: "dollar" },
  { caminho: "/aluguel", rotulo: "Aluguel (BTC)", icone: "handshake" },
  { caminho: "/renda-fixa", rotulo: "Renda fixa", icone: "landmark" },
  { caminho: "/operacoes", rotulo: "Operações", icone: "transfer" },
  { caminho: "/caixa", rotulo: "Caixa", icone: "wallet" },
  { caminho: "/relatorios", rotulo: "Relatórios", icone: "file" },
  { caminho: "/alocacao", rotulo: "Alocação", icone: "scale" },
  { caminho: "/metas", rotulo: "Metas", icone: "target" },
  { caminho: "/radar", rotulo: "Radar", icone: "telescope" },
  { caminho: "/cripto", rotulo: "Cripto", icone: "bitcoin" },
  { caminho: "/status", rotulo: "Status do ativo", icone: "search" },
  { caminho: "/ir", rotulo: "Imposto de Renda", icone: "receipt" },
  { caminho: "/valuation", rotulo: "Valuation", icone: "calculator" },
  { caminho: "/valuations-salvos", rotulo: "Valuations salvos", icone: "folder" },
] as const;

export function Layout() {
  return (
    <ProvedorExportacao>
      <Estrutura />
    </ProvedorExportacao>
  );
}

const MOBILE = "(max-width: 720px)";

function tituloDaPagina(caminho: string): string {
  if (caminho === "/configuracoes") return "Configurações";
  return PAGINAS.find((p) => p.caminho === caminho)?.rotulo ?? "Página não encontrada";
}

function Estrutura() {
  const conteudo = useRef<HTMLElement>(null);
  const menu = useRef<HTMLElement>(null);
  const botaoMenuMobile = useRef<HTMLButtonElement>(null);
  const { pathname } = useLocation();
  const rotaAnterior = useRef(pathname);
  const [mobile, setMobile] = useState(() => window.matchMedia(MOBILE).matches);
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

  // Título da aba por rota e foco no conteúdo após navegar (leitor de tela anuncia a nova página).
  useEffect(() => {
    document.title = `${tituloDaPagina(pathname)} · InvestHub+`;
    if (rotaAnterior.current === pathname) return;
    rotaAnterior.current = pathname;
    conteudo.current?.focus({ preventScroll: true });
  }, [pathname]);

  useEffect(() => {
    const consulta = window.matchMedia(MOBILE);
    const mudar = () => setMobile(consulta.matches);
    consulta.addEventListener("change", mudar);
    return () => consulta.removeEventListener("change", mudar);
  }, []);

  // No mobile, o menu fechado fica fora da ordem de Tab e da árvore de acessibilidade.
  const menuInerte = mobile && !drawerAberto;
  useEffect(() => {
    const el = menu.current;
    if (!el) return;
    if (menuInerte) el.setAttribute("inert", "");
    else el.removeAttribute("inert");
  }, [menuInerte]);

  const drawerJaAberto = useRef(false);
  useEffect(() => {
    if (!mobile) return;
    if (drawerAberto) {
      drawerJaAberto.current = true;
      menu.current?.querySelector<HTMLElement>("nav a")?.focus();
    } else if (drawerJaAberto.current) {
      drawerJaAberto.current = false;
      if (menu.current?.contains(document.activeElement) || document.activeElement === document.body) {
        botaoMenuMobile.current?.focus();
      }
    }
  }, [drawerAberto, mobile]);

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
      <a
        className="pular-conteudo"
        href="#conteudo"
        onClick={(e) => {
          e.preventDefault();
          conteudo.current?.focus();
        }}
      >
        Pular para o conteúdo
      </a>
      {drawerAberto && (
        <button
          className="menu-fundo"
          type="button"
          aria-label="Fechar menu"
          onClick={() => setDrawerAberto(false)}
        />
      )}
      <aside className="menu" id="navegacao-principal" ref={menu}>
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
            <Icone nome={menuRecolhido ? "panelOpen" : "panelClose"} size={18} aria-hidden="true" />
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
              <Icone nome={p.icone} className="menu-icone" size={18} aria-hidden="true" />
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
          <Icone nome="settings" className="menu-icone" size={18} aria-hidden="true" />
          <span className="menu-rotulo">Configurações</span>
        </NavLink>
      </aside>
      <div className="principal">
        <header className="topo">
          <button
            ref={botaoMenuMobile}
            className="menu-mobile-controle"
            type="button"
            aria-label="Abrir menu"
            aria-expanded={drawerAberto}
            aria-controls="navegacao-principal"
            onClick={() => setDrawerAberto(true)}
          >
            <span className="visualmente-oculto">Abrir menu</span>
            <Icone nome="panelOpen" size={19} aria-hidden="true" />
          </button>
          <BotoesExportar alvo={conteudo} />
          <Alertas />
          <SeletorInvestidor />
        </header>
        <main className="conteudo" id="conteudo" tabIndex={-1} ref={conteudo}>
          <Outlet />
        </main>
      </div>
    </div>
  );
}