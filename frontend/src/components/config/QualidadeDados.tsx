import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useLocation } from "react-router-dom";
import { api, query } from "../../api";
import { useInvestidor } from "../../InvestidorContext";
import type { Verificacao } from "../../tipos";

const ROTULO: Record<Verificacao["severidade"], string> = { erro: "Erro", aviso: "Atenção", info: "Informativo" };

export function QualidadeDados() {
  const { filtro } = useInvestidor();
  const localizacao = useLocation();
  const cache = useQueryClient();
  const { data = [], isLoading, error, refetch, isFetching } = useQuery({
    queryKey: ["qualidade-dados", filtro],
    queryFn: () =>
      api.get<Verificacao[]>(
        `/qualidade-dados${query({ investidores: filtro, historico: true })}`,
      ),
  });
  const tratamento = useMutation({
    mutationFn: async ({ fingerprint, tratado }: { fingerprint: string; tratado: boolean }) => {
      if (tratado) {
        await api.post<Verificacao>(`/qualidade-dados/${fingerprint}/tratado`);
      } else {
        await api.del(`/qualidade-dados/${fingerprint}/tratado`);
      }
    },
    onSuccess: () => cache.invalidateQueries({ queryKey: ["qualidade-dados"] }),
  });
  const pendentes = data.filter((v) => v.status === "aberto");
  const erros = pendentes.filter((v) => v.severidade === "erro").length;
  const destinos = (v: Verificacao) => {
    const parametros = new URLSearchParams({
      apontamento: v.fingerprint,
      regra: v.titulo,
      explicacao: v.descricao,
      retorno: `${localizacao.pathname}${localizacao.search}`,
    });
    const consulta = parametros.toString();
    const links = [
      v.operacao_ids.length ? { caminho: `/operacoes?${consulta}`, rotulo: "Operações" } : null,
      v.provento_ids.length ? { caminho: `/proventos?${consulta}`, rotulo: "Proventos" } : null,
      v.caixa_ids.length ? { caminho: `/caixa?${consulta}`, rotulo: "Caixa" } : null,
    ].filter((link): link is { caminho: string; rotulo: string } => link !== null);
    return links.length ? links : v.link ? [{ caminho: v.link, rotulo: "Abrir" }] : [];
  };

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
      {tratamento.error && <div className="erro">{(tratamento.error as Error).message}</div>}
      {isLoading && <p>Verificando…</p>}
      {!isLoading && pendentes.length === 0 && <div className="aviso">Nenhuma pendência encontrada.</div>}
      {data.length > 0 && (
        <p>
          <strong>{pendentes.length}</strong> apontamento(s) pendente(s)
          {erros > 0 && <>, <strong className="negativo">{erros} erro(s)</strong></>}
          {data.length > pendentes.length && <> · {data.length - pendentes.length} tratado(s)/resolvido(s)</>}.
        </p>
      )}
      {data.map((v) => {
        const links = destinos(v);
        return (
        <div key={v.fingerprint} className={`painel verificacao severidade-${v.severidade}`}>
          <div className="titulo-linha">
            <h3>
              <span className={`etiqueta severidade-${v.severidade}`}>{ROTULO[v.severidade]}</span> {v.titulo}
            </h3>
            {links.map((link) => (
              <Link key={link.caminho} to={link.caminho} className="link">
                Abrir {link.rotulo} →
              </Link>
            ))}
          </div>
          <p className="sutil">{v.descricao}</p>
          <div className="etiquetas">
            {v.itens.map((item) => (
              <span key={item} className="etiqueta">
                {item}
              </span>
            ))}
          </div>
          <div className="titulo-linha" aria-live="polite">
            <span className={`etiqueta ${v.status === "aberto" ? "negativo" : "positivo"}`}>
              {v.status === "aberto"
                ? "Pendente"
                : v.status === "tratado"
                  ? `Tratado${v.tratado_em ? ` em ${new Date(v.tratado_em).toLocaleString("pt-BR")}` : ""}`
                  : "Tratado · não detectado atualmente"}
            </span>
            {v.status !== "resolvido" && (
              <button
                className="secundario"
                disabled={tratamento.isPending}
                onClick={() =>
                  tratamento.mutate({
                    fingerprint: v.fingerprint,
                    tratado: v.status === "aberto",
                  })
                }
              >
                {v.status === "aberto" ? "TRATAR APONTAMENTO" : "REABRIR APONTAMENTO"}
              </button>
            )}
          </div>
        </div>
        );
      })}
    </>
  );
}
