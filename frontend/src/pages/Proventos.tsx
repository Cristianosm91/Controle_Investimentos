import { useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { AcoesLinha } from "../components/AcoesLinha";
import { AgendaProventos } from "../components/AgendaProventos";
import { FormProvento } from "../components/FormLancamentos";
import { ImportarExtrato } from "../components/ImportarExtrato";
import { ListaPaginada, type ColunaLista } from "../components/ListaPaginada";
import { MatrizProventos } from "../components/MatrizProventos";
import { useAtivosDisponiveis, useCorretoras, useDominio } from "../cadastros";
import { data, moeda } from "../formato";
import { filtrarAtivos, opcoesAtivos, opcoesClasses, OPCOES_MERCADO, valorFiltro } from "../filtrosAtivos";
import { FiltroMultisselecao } from "../components/FiltroMultisselecao";
import { useInvestidor } from "../InvestidorContext";
import type { Provento } from "../tipos";

export function Proventos() {
  const [parametros] = useSearchParams();
  const navegar = useNavigate();
  const { filtro, investidores } = useInvestidor();
  const { data: dominio } = useDominio();
  const { data: ativos = [] } = useAtivosDisponiveis(filtro);
  const { data: corretoras } = useCorretoras();
  const [edicao, setEdicao] = useState<Provento | "novo" | null>(null);
  const [aba, setAba] = useState<"lancamentos" | "matriz" | "agenda">("lancamentos");
  const [mercados, setMercados] = useState<string[] | null>(null);
  const [classesSelecionadas, setClassesSelecionadas] = useState<string[] | null>(null);
  const [ativosSelecionados, setAtivosSelecionados] = useState<string[] | null>(null);
  const [importando, setImportando] = useState(false);
  const apontamento = parametros.get("apontamento");
  const codigoQualidade = parametros.get("codigo");
  const regraQualidade = parametros.get("regra");
  const explicacaoQualidade = parametros.get("explicacao");
  const retornoQualidade = parametros.get("retorno");
  const nome = (id: number) => investidores.find((i) => i.id === id)?.nome ?? id;
  const ativosPorMercado = useMemo(() => filtrarAtivos(ativos, mercados, null), [ativos, mercados]);
  const opcoesDeClasse = useMemo(() => opcoesClasses(ativosPorMercado), [ativosPorMercado]);
  const ativosFiltrados = useMemo(
    () => filtrarAtivos(ativos, mercados, classesSelecionadas),
    [ativos, mercados, classesSelecionadas],
  );
  const opcoesDeAtivo = useMemo(() => opcoesAtivos(ativosFiltrados), [ativosFiltrados]);
  const filtrosComuns = {
    mercados: valorFiltro(mercados),
    classes: valorFiltro(classesSelecionadas),
    ativo_ids: valorFiltro(ativosSelecionados),
  };

  const colunas: ColunaLista<Provento>[] = [
    { titulo: "Pagamento", render: (p) => data(p.data_pagamento) },
    { titulo: "Data com", render: (p) => data(p.data_com) },
    { titulo: "Investidor", render: (p) => nome(p.investidor_id) },
    { titulo: "Ativo", render: (p) => <strong>{p.ticker}</strong> },
    { titulo: "Evento", render: (p) => dominio?.eventos_provento[p.evento] ?? p.evento },
    { titulo: "Bruto", numerica: true, render: (p) => moeda(p.valor, p.moeda) },
    { titulo: "Moeda", render: (p) => p.moeda },
    { titulo: "IRRF", numerica: true, render: (p) => p.irrf ? moeda(p.irrf, p.moeda) : "—" },
    { titulo: "Taxas", numerica: true, render: (p) => p.taxas ? moeda(p.taxas, p.moeda) : "—" },
    { titulo: "Líquido (R$)", numerica: true, render: (p) => moeda((p.valor - p.irrf - p.taxas) * p.cambio) },
    { titulo: "Corretora", render: (p) => p.corretora ?? "—" },
    { titulo: "Observação", render: (p) => <span className="quebra sutil">{p.observacao || "—"}</span> },
  ];

  const abas = (
    <div className="abas-controles">
      <div className="abas">
        <button className={aba === "lancamentos" ? "aba ativa" : "aba"} onClick={() => setAba("lancamentos")}>
          Lançamentos
        </button>
        <button className={aba === "matriz" ? "aba ativa" : "aba"} onClick={() => setAba("matriz")}>
          Matriz mensal
        </button>
        <button className={aba === "agenda" ? "aba ativa" : "aba"} onClick={() => setAba("agenda")}>
          Agenda e projeção
        </button>
      </div>
      <FiltroMultisselecao
        rotulo="Mercados"
        resumoTodos="Todos os mercados"
        resumoNenhum="Nenhum mercado"
        resumoMultiplos={(quantidade) => `${quantidade} mercados selecionados`}
        opcoes={OPCOES_MERCADO}
        selecionados={mercados}
        aoMudar={setMercados}
      />
      <FiltroMultisselecao
        rotulo="Classes"
        resumoTodos="Todas as classes"
        resumoNenhum="Nenhuma classe"
        resumoMultiplos={(quantidade) => `${quantidade} classes selecionadas`}
        opcoes={opcoesDeClasse}
        selecionados={classesSelecionadas}
        aoMudar={setClassesSelecionadas}
      />
      <FiltroMultisselecao
        rotulo="Ativos"
        resumoTodos="Todos os ativos"
        resumoNenhum="Nenhum ativo"
        resumoMultiplos={(quantidade) => `${quantidade} ativos selecionados`}
        opcoes={opcoesDeAtivo}
        selecionados={ativosSelecionados}
        aoMudar={setAtivosSelecionados}
      />
    </div>
  );

  return (
    <>
      {aba !== "lancamentos" ? (
        <section>
          <h1>Proventos</h1>
          {abas}
          {aba === "matriz"
            ? <MatrizProventos filtro={filtro} filtros={filtrosComuns} />
            : <AgendaProventos filtros={filtrosComuns} />}
        </section>
      ) : (
      <ListaPaginada<Provento>
        titulo="Proventos"
        recurso="proventos"
        filtroInvestidores={filtro}
        colunas={colunas}
        filtroTicker={false}
        corretoras={corretoras}
        filtrosFixos={{
          ...filtrosComuns,
          ...(apontamento ? { apontamento, ...(codigoQualidade ? { codigo: codigoQualidade } : {}) } : {}),
        }}
        chave={(p) => p.id}
        cabecalho={
          <>
            <button className="secundario" onClick={() => setImportando(true)}>
              Importar extrato B3
            </button>
            <button onClick={() => setEdicao("novo")}>+ Novo provento</button>
          </>
        }
        topo={
          <>
            {apontamento && (
              <section className="aviso">
                <strong>Proventos relacionados à Qualidade de Dados</strong>
                {regraQualidade && <p>Regra: {regraQualidade}</p>}
                {explicacaoQualidade && <p>{explicacaoQualidade}</p>}
                <p>Somente os proventos vinculados ao apontamento são exibidos. Se nenhum registro aparecer, ele pode ter sido alterado ou excluído desde a análise.</p>
                <button className="secundario" onClick={() => navegar(retornoQualidade || "/configuracoes?secao=qualidade")}>
                  VOLTAR À QUALIDADE
                </button>
                <button className="secundario" onClick={() => navegar("/proventos")}>
                  REMOVER FILTRO
                </button>
              </section>
            )}
            {abas}
          </>
        }
        acoes={(p) => (
          <AcoesLinha
            recurso="proventos"
            id={p.id}
            descricao={`${dominio?.eventos_provento[p.evento] ?? p.evento} de ${p.ticker} em ${data(p.data_pagamento)}`}
            aoEditar={() => setEdicao(p)}
          />
        )}
      />
      )}
      {edicao && (
        <FormProvento
          provento={edicao === "novo" ? undefined : edicao}
          ocultarAluguel
          aoFechar={() => setEdicao(null)}
        />
      )}
      {importando && <ImportarExtrato aoFechar={() => setImportando(false)} />}
    </>
  );
}