import { useQuery } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api, query } from "../api";
import { useInvestidor } from "../InvestidorContext";
import type { Alerta } from "../tipos";

const CINCO_MINUTOS = 5 * 60 * 1000;
const CHAVE_ALERTAS_LIDAS = "investhub.alertas.lidas";

function lerAlertasLidas(): Set<string> {
  try {
    const valor = JSON.parse(localStorage.getItem(CHAVE_ALERTAS_LIDAS) ?? "[]");
    return new Set(Array.isArray(valor) ? valor.filter((item): item is string => typeof item === "string") : []);
  } catch {
    return new Set();
  }
}

export function Alertas() {
  const { filtro } = useInvestidor();
  const [aberto, setAberto] = useState(false);
  const [lidas, setLidas] = useState(lerAlertasLidas);
  const ref = useRef<HTMLDivElement>(null);
  const { data: alertas = [], isFetching } = useQuery({
    queryKey: ["alertas", filtro],
    queryFn: () => api.get<Alerta[]>(`/alertas${query({ investidores: filtro })}`),
    refetchInterval: CINCO_MINUTOS,
    staleTime: CINCO_MINUTOS,
  });

  useEffect(() => {
    localStorage.setItem(CHAVE_ALERTAS_LIDAS, JSON.stringify([...lidas]));
  }, [lidas]);

  useEffect(() => {
    const fechar = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setAberto(false);
    };
    document.addEventListener("mousedown", fechar);
    return () => document.removeEventListener("mousedown", fechar);
  }, []);

  const idAlerta = (codigo: string, titulo: string, detalhe: string) =>
    JSON.stringify([filtro ?? null, codigo, titulo, detalhe]);
  const naoLidos = alertas.filter((a) => !lidas.has(idAlerta(a.codigo, a.titulo, a.detalhe)));
  const importantes = naoLidos.filter((a) => a.severidade !== "info").length;

  const marcarComoLidas = (ids: string[]) => {
    if (ids.length) setLidas((atuais) => new Set([...atuais, ...ids]));
  };

  return (
    <div className="alertas" ref={ref}>
      <button
        className="seletor-botao alertas-botao"
        onClick={() => {
          marcarComoLidas(alertas.map((a) => idAlerta(a.codigo, a.titulo, a.detalhe)));
          setAberto(!aberto);
        }}
        aria-expanded={aberto}
        aria-label={`${naoLidos.length} alerta(s) não lido(s)`}
        title="Alertas"
      >
        🔔
        {naoLidos.length > 0 && (
          <span className={importantes ? "alertas-contador importante" : "alertas-contador"}>{naoLidos.length}</span>
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
              <Link
                key={a.codigo}
                to={a.link}
                className={`alerta alerta-${a.severidade}`}
                onClick={() => {
                  marcarComoLidas([idAlerta(a.codigo, a.titulo, a.detalhe)]);
                  setAberto(false);
                }}
              >
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
