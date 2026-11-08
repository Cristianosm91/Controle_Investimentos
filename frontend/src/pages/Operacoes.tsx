import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { AcoesLinha } from "../components/AcoesLinha";
import { FormOperacao } from "../components/FormLancamentos";
import { ImportarExtrato } from "../components/ImportarExtrato";
import { ListaPaginada, type ColunaLista } from "../components/ListaPaginada";
import { Modal } from "../components/Modal";
import { VincularTransferencia } from "../components/VincularTransferencia";
import { api } from "../api";
import { useAtivos, useCorretoras, useDominio } from "../cadastros";
import { invalidarDerivados } from "../cadastros";
import { classeSinal, data, moeda, numero } from "../formato";
import { useInvestidor } from "../InvestidorContext";
import type { Operacao } from "../tipos";

const NOMES_CLASSES: Record<string, string> = {
  "AÇÃO": "Ações",
  BDR: "BDRs",
  ETF: "ETFs",
  FII: "FIIs",
  FIAGRO: "Fiagro",
  CRIPTO: "Criptos",
  "R.FIXA": "Renda fixa",
};

const EVENTOS_CURTOS: Record<string, string> = {
  DESDOBRAMENTO: "Desd./Grup.",
  TRANSFERENCIA: "Troca Ticker",
  VENDA_SUBSCRICAO: "Venda subscr.",
};

const AJUDA_EVENTOS: Record<string, string> = {
  C: "Entrada de ativos por compra, incluindo IPO e subscrição.",
  V: "Saída de ativos por venda.",
  BONIFICACAO: "Recebimento de ativos em bonificação.",
  DESDOBRAMENTO: "Aumento (desdobramento) ou redução (grupamento) da quantidade, mantendo o custo total da posição.",
  TRANSFERENCIA: "Saída e entrada por transferência, troca de ticker ou incorporação (AT/TC). As duas pernas podem ser vinculadas.",
  AMORTIZACAO: "Redução do custo da posição por devolução de capital.",
  CISAO: "Ajuste de custo decorrente de cisão da empresa.",
  VENDA_SUBSCRICAO: "Venda de direitos de subscrição (V.SUB).",
};

export function Operacoes() {
  const [parametros] = useSearchParams();
  const localizacao = useLocation();
  const navegar = useNavigate();
  const cliente = useQueryClient();
  const { filtro, investidores } = useInvestidor();
  const { data: dominio, error: erroDominio } = useDominio();
  const { data: ativos } = useAtivos();
  const { data: corretoras } = useCorretoras();
  const [edicao, setEdicao] = useState<Operacao | "nova" | null>(null);
  const [vinculo, setVinculo] = useState<Operacao | null>(null);
  const [importando, setImportando] = useState(false);
  const [ajudaEventos, setAjudaEventos] = useState(false);
  const localizacaoEdicao = useRef("/operacoes");
  const desvincular = useMutation({
    mutationFn: (id: number) => api.del(`/operacoes/${id}/vinculo-transferencia`),
    onSuccess: () => {
      cliente.invalidateQueries({ queryKey: ["operacoes"] });
      invalidarDerivados(cliente);
    },
  });
  const abrirEdicao = (operacao: Operacao | "nova") => {
    localizacaoEdicao.current = `${localizacao.pathname}${localizacao.search}`;
    setEdicao(operacao);
  };
  const fecharEdicao = () => {
    setEdicao(null);
    const atual = `${window.location.pathname}${window.location.search}`;
    if (atual !== localizacaoEdicao.current) {
      navegar(localizacaoEdicao.current, { replace: true });
    }
  };
  const idsQualidade = parametros.get("ids");
  const apontamentoQualidade = parametros.get("apontamento");
  const codigoQualidade = parametros.get("codigo");
  const veioDaQualidade = Boolean(idsQualidade || apontamentoQualidade);
  const idsRelacionados = new Set(
    (idsQualidade ?? "")
      .split(",")
      .map((id) => Number(id))
      .filter((id) => Number.isInteger(id) && id > 0),
  );
  const regraQualidade = parametros.get("regra");
  const explicacaoQualidade = parametros.get("explicacao");
  const retornoQualidade = parametros.get("retorno");
  const nome = (id: number) => investidores.find((i) => i.id === id)?.nome ?? id;
  const classes = [...new Set(ativos?.map((ativo) => ativo.classe) ?? [])]
    .sort()
    .map((valor) => ({
      valor,
      rotulo: NOMES_CLASSES[valor] ?? valor.charAt(0) + valor.slice(1).toLowerCase(),
    }));
  const eventos = Object.entries(dominio?.eventos_operacao ?? {}).map(([valor, rotulo]) => ({
    valor,
    rotulo,
  }));
  const renderEvento = (o: Operacao, abreviar = false) => (
    <span className="operacoes-evento">
      <span title={dominio?.eventos_operacao[o.evento] ?? o.evento}>
        {(abreviar && EVENTOS_CURTOS[o.evento]) || dominio?.eventos_operacao[o.evento] || o.evento}
      </span>
      {o.ticker_transferencia && <span className="etiqueta">Ligada a {o.ticker_transferencia}</span>}
      {o.daytrade && <span className="etiqueta">day trade</span>}
    </span>
  );

  const colunas: ColunaLista<Operacao>[] = [
    { titulo: "Data", render: (o) => data(o.data) },
    { titulo: "Investidor", render: (o) => <span className="operacoes-texto">{nome(o.investidor_id)}</span> },
    { titulo: "Ativo", render: (o) => <strong>{o.ticker}</strong> },
    {
      titulo: "Evento",
      cabecalho: (
        <span className="operacoes-evento-cabecalho">
          Evento
          <button
            type="button"
            className="link operacoes-ajuda"
            aria-label="Ajuda sobre os eventos de operações"
            onClick={() => setAjudaEventos(true)}
          >
            ?
          </button>
        </span>
      ),
      render: (o) => renderEvento(o, true),
      renderExportacao: (o) => renderEvento(o),
    },
    { titulo: "Qtd", numerica: true, render: (o) => <span className={classeSinal(o.quantidade)}>{numero(o.quantidade, 8)}</span> },
    { titulo: "Preço", numerica: true, render: (o) => moeda(o.preco, o.moeda) },
    { titulo: "Taxas", numerica: true, render: (o) => moeda(o.taxas, o.moeda) },
    { titulo: "IRRF", numerica: true, render: (o) => moeda(o.irrf, o.moeda) },
    { titulo: "Total (R$)", numerica: true, render: (o) => moeda(Math.abs(o.quantidade * o.preco) * o.cambio) },
    { titulo: "Corretora", render: (o) => <span className="operacoes-texto">{o.corretora ?? "—"}</span> },
    { titulo: "Obs.", render: (o) => <span className="sutil operacoes-observacao" title={o.observacao ?? undefined}>{o.observacao}</span> },
  ];

  return (
    <>
      <ListaPaginada<Operacao>
        titulo="Operações"
        recurso="operacoes"
        filtroInvestidores={filtro}
        colunas={colunas}
        classes={classes}
        corretoras={corretoras}
        eventos={eventos}
        filtrosFixos={
          apontamentoQualidade
            ? { apontamento: apontamentoQualidade, ...(codigoQualidade ? { codigo: codigoQualidade } : {}) }
            : idsQualidade
              ? { ids: idsQualidade }
              : undefined
        }
        linhaClasse={(operacao) =>
          apontamentoQualidade || idsRelacionados.has(operacao.id)
            ? "qualidade-relacionada"
            : undefined
        }
        topo={
          veioDaQualidade ? (
            <section className="aviso">
              <strong>Operações relacionadas à Qualidade de Dados</strong>
              {regraQualidade && <p>Regra: {regraQualidade}</p>}
              {explicacaoQualidade && <p>{explicacaoQualidade}</p>}
              <p>
                {idsRelacionados.size > 0
                  ? `Somente os IDs ${Array.from(idsRelacionados).join(", ")} são exibidos e destacados.`
                  : "Somente as operações vinculadas a este apontamento são exibidas e destacadas."}
                {" "}Se nenhum registro aparecer, ele pode ter sido alterado ou excluído desde a análise.
              </p>
              <button
                className="secundario"
                onClick={() =>
                  navegar(retornoQualidade || "/configuracoes?secao=qualidade")
                }
              >
                VOLTAR À QUALIDADE
              </button>
              <button className="secundario" onClick={() => navegar("/operacoes")}>
                REMOVER FILTRO
              </button>
            </section>
          ) : undefined
        }
        chave={(o) => o.id}
        cabecalho={
          <>
            <button className="secundario" onClick={() => setImportando(true)}>
              Importar extrato B3
            </button>
            <button onClick={() => abrirEdicao("nova")}>+ Nova operação</button>
          </>
        }
        acoes={(o) => (
          <span className="operacoes-acoes">
            <AcoesLinha
              recurso="operacoes"
              id={o.id}
              descricao={`${dominio?.eventos_operacao[o.evento] ?? o.evento} de ${o.ticker} em ${data(o.data)}`}
              aoEditar={() => abrirEdicao(o)}
            />
            {o.evento === "TRANSFERENCIA" && (
              <button
                className="link"
                disabled={desvincular.isPending}
                onClick={() => {
                  if (o.transferencia_pareada_id) {
                    if (
                      confirm(
                        `Desvincular ${o.ticker} de ${o.ticker_transferencia ?? "outra operação"}?`,
                      )
                    ) {
                      desvincular.mutate(o.id);
                    }
                  } else {
                    setVinculo(o);
                  }
                }}
              >
                {o.transferencia_pareada_id ? "Desvincular" : "Vincular"}
              </button>
            )}
          </span>
        )}
      />
      {ajudaEventos && (
        <Modal titulo="Eventos de operações" aoFechar={() => setAjudaEventos(false)}>
          <dl className="operacoes-legenda">
            {eventos.map(({ valor, rotulo }) => (
              <div key={valor}>
                <dt><strong>{EVENTOS_CURTOS[valor] ? `${EVENTOS_CURTOS[valor]} — ${rotulo}` : rotulo}</strong></dt>
                <dd>{AJUDA_EVENTOS[valor] ?? rotulo}</dd>
              </div>
            ))}
          </dl>
          <p className="sutil">Day trade identifica compra ou venda realizada no mesmo dia; não é um evento separado.</p>
        </Modal>
      )}
      {erroDominio && <div className="erro">{erroDominio.message}</div>}
      {desvincular.error && <div className="erro">{(desvincular.error as Error).message}</div>}
      {edicao && <FormOperacao operacao={edicao === "nova" ? undefined : edicao} aoFechar={fecharEdicao} />}
      {vinculo && <VincularTransferencia operacao={vinculo} aoFechar={() => setVinculo(null)} />}
      {importando && <ImportarExtrato aoFechar={() => setImportando(false)} />}
    </>
  );
}