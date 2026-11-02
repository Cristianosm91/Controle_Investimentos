import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { api, query } from "../api";
import { MESES, moeda } from "../formato";
import type { MatrizProventos as TMatriz } from "../tipos";

export function MatrizProventos({ filtro, classe }: { filtro: string | undefined; classe?: string }) {
  const [ano, setAno] = useState<string>("");
  const anos = useQuery({
    queryKey: ["proventos-matriz", filtro, classe, ""],
    queryFn: () => api.get<TMatriz>(`/proventos/matriz${query({ investidores: filtro, classe })}`),
  });
  const { data: m, isLoading, error } = useQuery({
    queryKey: ["proventos-matriz", filtro, classe, ano],
    queryFn: () => api.get<TMatriz>(`/proventos/matriz${query({ investidores: filtro, ano, classe })}`),
    placeholderData: (anterior) => anterior,
  });
  const meses = m?.linhas.length ?? 0;
  const media = m && m.totais_mes.some(Boolean) ? m.total / m.totais_mes.filter(Boolean).length : 0;

  return (
    <>
      <div className="acoes filtros">
        <label className="check">
          Visão
          <select value={ano} onChange={(e) => setAno(e.target.value)}>
            <option value="">Ano × mês</option>
            {[...(anos.data?.linhas ?? [])].reverse().map((a) => (
              <option key={a} value={a}>
                {a}: ativo × mês
              </option>
            ))}
          </select>
        </label>
        {m && (
          <span className="sutil">
            Total {moeda(m.total)} · média por mês com proventos {moeda(media)} · valores líquidos em R$
          </span>
        )}
      </div>
      {error && <div className="erro">{(error as Error).message}</div>}
      {isLoading && <p>Carregando…</p>}
      {m && meses === 0 && <div className="aviso">Nenhum provento no período.</div>}
      {m && meses > 0 && (
        <div className="tabela-container">
          <table className="tabela matriz">
            <thead>
              <tr>
                <th>{m.titulo_linhas}</th>
                {MESES.map((nome) => (
                  <th key={nome} className="num">
                    {nome}
                  </th>
                ))}
                <th className="num">Total</th>
              </tr>
            </thead>
            <tbody>
              {m.linhas.map((rotulo, i) => (
                <tr key={rotulo}>
                  <td>
                    <strong>{rotulo}</strong>
                  </td>
                  {m.valores[i].map((v, j) => (
                    <td key={j} className="num">
                      {v ? moeda(v) : ""}
                    </td>
                  ))}
                  <td className="num">
                    <strong>{moeda(m.totais_linha[i])}</strong>
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr>
                <td>
                  <strong>Total</strong>
                </td>
                {m.totais_mes.map((v, j) => (
                  <td key={j} className="num">
                    <strong>{v ? moeda(v) : ""}</strong>
                  </td>
                ))}
                <td className="num">
                  <strong>{moeda(m.total)}</strong>
                </td>
              </tr>
            </tfoot>
          </table>
        </div>
      )}
    </>
  );
}
