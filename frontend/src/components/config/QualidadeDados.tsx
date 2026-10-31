import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api, query } from "../../api";
import { useInvestidor } from "../../InvestidorContext";
import type { Verificacao } from "../../tipos";

const ROTULO: Record<Verificacao["severidade"], string> = { erro: "Erro", aviso: "Atenção", info: "Informativo" };

export function QualidadeDados() {
  const { filtro } = useInvestidor();
  const { data = [], isLoading, error, refetch, isFetching } = useQuery({
    queryKey: ["qualidade-dados", filtro],
    queryFn: () => api.get<Verificacao[]>(`/qualidade-dados${query({ investidores: filtro })}`),
  });
  const erros = data.filter((v) => v.severidade === "erro").length;

  return (
    <>
      <div className="titulo-linha">
        <h2>Qualidade dos dados</h2>
        <button className="secundario" onClick={() => refetch()} disabled={isFetching}>
          {isFetching ? "Verificando…" : "↻ Verificar de novo"}
        </button>
      </div>
      <p className="sutil">
        Pendências que distorcem posição, preço médio, rentabilidade ou IR, para os investidores selecionados no topo. Erros devem ser
        corrigidos; os demais itens melhoram a precisão das telas.
      </p>
      {error && <div className="erro">{(error as Error).message}</div>}
      {isLoading && <p>Verificando…</p>}
      {!isLoading && data.length === 0 && <div className="aviso">Nenhuma pendência encontrada.</div>}
      {data.length > 0 && (
        <p>
          <strong>{data.length}</strong> verificação(ões) com pendência{erros > 0 && <>, <strong className="negativo">{erros} erro(s)</strong></>}.
        </p>
      )}
      {data.map((v) => (
        <div key={v.codigo} className={`painel verificacao severidade-${v.severidade}`}>
          <div className="titulo-linha">
            <h3>
              <span className={`etiqueta severidade-${v.severidade}`}>{ROTULO[v.severidade]}</span> {v.titulo}
            </h3>
            {v.link && (
              <Link to={v.link} className="link">
                Abrir →
              </Link>
            )}
          </div>
          <p className="sutil">{v.descricao}</p>
          <div className="etiquetas">
            {v.itens.map((item) => (
              <span key={item} className="etiqueta">
                {item}
              </span>
            ))}
          </div>
        </div>
      ))}
    </>
  );
}
