import { useQuery } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api, query } from "../api";
import { useInvestidor } from "../InvestidorContext";
import type { Alerta } from "../tipos";

const CINCO_MINUTOS = 5 * 60 * 1000;

export function Alertas() {
  const { filtro } = useInvestidor();
  const [aberto, setAberto] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const { data: alertas = [], isFetching } = useQuery({
    queryKey: ["alertas", filtro],
    queryFn: () => api.get<Alerta[]>(`/alertas${query({ investidores: filtro })}`),
    refetchInterval: CINCO_MINUTOS,
    staleTime: CINCO_MINUTOS,
  });

  useEffect(() => {
    const fechar = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setAberto(false);
    };
    document.addEventListener("mousedown", fechar);
    return () => document.removeEventListener("mousedown", fechar);
  }, []);

  const importantes = alertas.filter((a) => a.severidade !== "info").length;

  return (
    <div className="alertas" ref={ref}>
      <button
        className="seletor-botao alertas-botao"
        onClick={() => setAberto(!aberto)}
        aria-expanded={aberto}
        aria-label={`${alertas.length} alerta(s)`}
        title="Alertas"
      >
        🔔
        {alertas.length > 0 && (
          <span className={importantes ? "alertas-contador importante" : "alertas-contador"}>{alertas.length}</span>
        )}
      </button>
      {aberto && (
        <div className="seletor-menu alertas-menu" role="menu">
          <div className="seletor-titulo">Alertas {isFetching && <span className="sutil">· atualizando…</span>}</div>
          {alertas.length === 0 && <div className="seletor-vazio">Nenhum alerta no momento.</div>}
          {alertas.map((a) => {
            const conteudo = (
              <>
                <strong>{a.titulo}</strong>
                <small>{a.detalhe}</small>
              </>
            );
            return a.link ? (
              <Link key={a.codigo} to={a.link} className={`alerta alerta-${a.severidade}`} onClick={() => setAberto(false)}>
                {conteudo}
              </Link>
            ) : (
              <div key={a.codigo} className={`alerta alerta-${a.severidade}`}>
                {conteudo}
              </div>
            );
          })}
          <div className="seletor-vazio">
            Limiares em <Link to="/configuracoes?secao=parametros" onClick={() => setAberto(false)}>Configurações → Parâmetros</Link>.
          </div>
        </div>
      )}
    </div>
  );
}
