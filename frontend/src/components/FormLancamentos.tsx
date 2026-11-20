import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useState, type FormEvent, type ReactNode } from "react";
import { api, query } from "../api";
import { invalidarDerivados, useAtivos, useDominio } from "../cadastros";
import { data as fmtData, moeda as fmtMoeda, numero } from "../formato";
import { useInvestidor } from "../InvestidorContext";
import type { Ativo, CambioCripto, Cota, MovCaixa, Operacao, Provento } from "../tipos";
import { CampoAtivo, CampoCorretora, CampoEvento, CampoInvestidor, CamposMoedaCambio } from "./Campos";
import { CampoData } from "./CampoData";
import { Modal } from "./Modal";
import { AjudaIndicador } from "./AjudaIndicador";

const hoje = () => new Date().toLocaleDateString("sv-SE"); // aaaa-mm-dd no fuso local
const opcional = (v: string) => (v === "" ? null : Number(v));
const texto = (v: number | null | undefined) => (v === null || v === undefined ? "" : String(v));

function useInvestidorPadrao(): string {
  const { selecionados, investidores } = useInvestidor();
  if (selecionados.length === 1) return String(selecionados[0]);
  const ativos = investidores.filter((i) => i.ativo);
  return ativos.length === 1 ? String(ativos[0].id) : "";
}

function useSalvar<T>(recurso: string, id: number | undefined, aoConcluir: () => void) {
  const cliente = useQueryClient();
  return useMutation({
    mutationFn: (corpo: T) => (id ? api.put(`/${recurso}/${id}`, corpo) : api.post(`/${recurso}`, corpo)),
    onSuccess: () => {
      cliente.invalidateQueries({ queryKey: [recurso] });
      invalidarDerivados(cliente);
      aoConcluir();
    },
  });
}

interface Moldura {
  titulo: string;
  aoFechar: () => void;
  aoEnviar: () => void;
  salvando: boolean;
  erro: unknown;
  bloqueado?: boolean;
  rodape?: ReactNode;
  children: ReactNode;
}

function MolduraForm({ titulo, aoFechar, aoEnviar, salvando, erro, bloqueado, rodape, children }: Moldura) {
  const enviar = (e: FormEvent) => {
    e.preventDefault();
    aoEnviar();
  };
  return (
    <Modal titulo={titulo} aoFechar={aoFechar}>
      <form className="formulario em-modal" onSubmit={enviar}>
        {children}
        {erro ? <div className="erro largura-total">{(erro as Error).message}</div> : null}
        <div className="acoes largura-total">
          <button type="submit" disabled={salvando || bloqueado}>
            {salvando ? "Salvando…" : "Salvar"}
          </button>
          <button type="button" className="secundario" onClick={aoFechar}>
            Cancelar
          </button>
          {rodape}
        </div>
      </form>
    </Modal>
  );
}

// ---------- Operação ----------

/** Convenção de sinal da API (dominio.py); o formulário trabalha sempre com valores positivos. */
const QTD_NEGATIVA = ["V", "VENDA_SUBSCRICAO"];
const PRECO_NEGATIVO = ["AMORTIZACAO", "CISAO", "R_CAP"];
const QTD_COM_SINAL: Record<string, string> = {
  DESDOBRAMENTO: "positivo = desdobramento; negativo = grupamento",
  TRANSFERENCIA: "positivo = entrada; negativo = saída",
};

interface FormOp {
  investidor_id: string;
  ativo_id: string;
  corretora_id: string;
  data: string;
  evento: string;
  quantidade: string;
  preco: string;
  taxas: string;
  irrf: string;
  moeda: string;
  cambio: string;
  cambioAuto: boolean;
  valorOriginal: string;
  cambioUsd: string;
  cambioUsdAuto: boolean;
  taxasMoeda: string;
  taxasCambioUsd: string;
  taxasCambioUsdAuto: boolean;
  daytrade: boolean;
  observacao: string;
}

function paraFormOp(o: Operacao): FormOp {
  const qtd = QTD_NEGATIVA.includes(o.evento) ? -o.quantidade : o.quantidade;
  const preco = PRECO_NEGATIVO.includes(o.evento) ? -o.preco : o.preco;
  return {
    investidor_id: String(o.investidor_id),
    ativo_id: String(o.ativo_id),
    corretora_id: texto(o.corretora_id),
    data: o.data,
    evento: o.evento,
    quantidade: String(qtd),
    preco: String(preco),
    taxas: String(o.taxas),
    irrf: String(o.irrf),
    moeda: o.moeda,
    cambio: String(o.cambio),
    cambioAuto: false,
    valorOriginal: String(o.cripto_valor_original ?? Math.abs(o.quantidade * o.preco)),
    cambioUsd: texto(o.cripto_cambio_usd),
    cambioUsdAuto: o.cripto_cambio_usd_fonte !== "Manual",
    taxasMoeda: o.taxas_moeda ?? o.moeda,
    taxasCambioUsd: texto(o.taxas_cambio_usd),
    taxasCambioUsdAuto: o.taxas_cambio_usd_fonte !== "Manual",
    daytrade: o.daytrade,
    observacao: o.observacao ?? "",
  };
}

/** Ativo personalizado (sem cotação de mercado): sugere a cota da data como preço de compra/venda. */
function useCotaPersonalizado(ativo: Ativo | undefined, dataIso: string, ativoParaPreco: boolean) {
  return useQuery({
    queryKey: ["cota", ativo?.id, dataIso],
    queryFn: () => api.get<Cota>(`/ativos/${ativo!.id}/cota${query({ data: dataIso })}`),
    enabled: !!ativo && !ativo.cotacao_automatica && ativoParaPreco && /^\d{4}-\d{2}-\d{2}$/.test(dataIso),
    retry: false,
  });
}

export function FormOperacao({ operacao, aoFechar }: { operacao?: Operacao; aoFechar: () => void }) {
  const cliente = useQueryClient();
  const investidorPadrao = useInvestidorPadrao();
  const { data: ativos = [] } = useAtivos();
  const [vincularDestino, setVincularDestino] = useState(true);
  const [destinoAtivoId, setDestinoAtivoId] = useState("");
  const [destinoQuantidade, setDestinoQuantidade] = useState("");
  const [f, setF] = useState<FormOp>(
    operacao
      ? paraFormOp(operacao)
      : {
          investidor_id: investidorPadrao, ativo_id: "", corretora_id: "", data: hoje(), evento: "C", quantidade: "",
          preco: "", taxas: "0", irrf: "0", moeda: "BRL", cambio: "1", cambioAuto: true,
          valorOriginal: "", cambioUsd: "", cambioUsdAuto: true, taxasMoeda: "BRL", taxasCambioUsd: "",
          taxasCambioUsdAuto: true, daytrade: false, observacao: "",
        },
  );
  const [precoAuto, setPrecoAuto] = useState(!operacao);
  const mudar = (parcial: Partial<FormOp>) => setF((atual) => ({ ...atual, ...parcial }));
  const mudarCambio = useCallback(
    (moeda: string, cambio: string, cambioAuto: boolean) => setF((a) => ({ ...a, moeda, cambio, cambioAuto })),
    [],
  );
  const ativo = ativos.find((a) => String(a.id) === f.ativo_id);
  const ehCripto = ativo?.classe === "CRIPTO";
  const cambioCripto = useQuery({
    queryKey: ["cripto-cambios", f.data],
    queryFn: () => api.get<CambioCripto>(`/cripto/cambios${query({ data: f.data })}`),
    enabled: ehCripto && /^\d{4}-\d{2}-\d{2}$/.test(f.data),
    staleTime: 60 * 60 * 1000,
    retry: false,
  });
  const taxaOperacao = cambioCripto.data?.moedas.find((item) => item.moeda === f.moeda);
  const taxaTaxas = cambioCripto.data?.moedas.find((item) => item.moeda === f.taxasMoeda);
  const salvar = useMutation({
    mutationFn: (corpo: object) => ehCripto
      ? operacao
        ? api.put<Operacao>(`/cripto/operacoes/${operacao.id}`, corpo)
        : api.post<Operacao>("/cripto/operacoes", corpo)
      : operacao
        ? api.put<Operacao>(`/operacoes/${operacao.id}`, corpo)
        : api.post<Operacao>("/operacoes", corpo),
    onSuccess: () => {
      cliente.invalidateQueries({ queryKey: ["operacoes"] });
      invalidarDerivados(cliente);
      aoFechar();
    },
  });
  const salvarTroca = useMutation({
    mutationFn: (dados: {
      investidor_id: number;
      ativo_origem_id: number;
      ativo_destino_id: number;
      corretora_id: number | null;
      data: string;
      quantidade_origem: number;
      quantidade_destino: number;
      preco_origem: number;
      taxas: number;
      irrf: number;
      moeda: string;
      cambio: number;
      observacao: string | null;
    }) => api.post<Operacao[]>("/operacoes/troca-ticker", dados),
    onSuccess: () => {
      cliente.invalidateQueries({ queryKey: ["operacoes"] });
      invalidarDerivados(cliente);
      aoFechar();
    },
  });
  const salvarTrocaCripto = useMutation({
    mutationFn: (dados: {
      investidor_id: number;
      ativo_origem_id: number;
      ativo_destino_id: number;
      corretora_id: number | null;
      data: string;
      quantidade_origem: number;
      quantidade_destino: number;
      preco_origem: number;
      taxas: number;
      irrf: number;
      moeda: string;
      cambio_usd: number | null;
      cambio_usd_manual: boolean;
      taxas_moeda: string;
      taxas_cambio_usd: number | null;
      taxas_cambio_usd_manual: boolean;
      observacao: string | null;
    }) => api.post<Operacao[]>("/cripto/troca-ticker", dados),
    onSuccess: () => {
      cliente.invalidateQueries({ queryKey: ["operacoes"] });
      invalidarDerivados(cliente);
      aoFechar();
    },
  });

  const destinoAtivo = ativos.find((a) => String(a.id) === destinoAtivoId);
  const ehCompraVenda = f.evento === "C" || f.evento === "V";
  const trocaVinculada = !operacao && f.evento === "TRANSFERENCIA" && vincularDestino;
  const trocaCripto = Boolean(trocaVinculada && ehCripto && destinoAtivo?.classe === "CRIPTO");
  const trocaIncompativel = Boolean(trocaVinculada && destinoAtivo && (
    ehCripto !== (destinoAtivo.classe === "CRIPTO")
    || (!ehCripto && destinoAtivo.moeda !== ativo?.moeda)
  ));
  const cota = useCotaPersonalizado(ativo, f.data, ehCompraVenda);
  useEffect(() => {
    if (precoAuto && cota.data) setF((a) => ({ ...a, preco: String(cota.data.cota) }));
  }, [precoAuto, cota.data]);
  useEffect(() => {
    if (!ehCripto) return;
    setF((atual) => ({
      ...atual,
      ...(taxaOperacao && atual.cambioUsdAuto && taxaOperacao.cambio_usd !== null
        ? { cambioUsd: String(taxaOperacao.cambio_usd) } : {}),
      ...(taxaOperacao?.cambio_brl !== null && taxaOperacao?.cambio_brl !== undefined
        ? { cambio: String(taxaOperacao.cambio_brl) } : {}),
      ...(taxaTaxas && atual.taxasCambioUsdAuto && taxaTaxas.cambio_usd !== null
        ? { taxasCambioUsd: String(taxaTaxas.cambio_usd) } : {}),
    }));
  }, [ehCripto, taxaOperacao, taxaTaxas]);

  const qtd = Number(f.quantidade || 0);
  const preco = Number(f.preco || 0);
  const valorBase = f.evento === "R_CAP" ? Math.abs(preco) : Math.abs(qtd * preco);
  const totalBrl = valorBase * Number(f.cambio || 1) + Number(f.taxas || 0) * Number(f.cambio || 1);
  const principalUsd = ehCompraVenda
    ? Number(f.valorOriginal || 0) * Number(f.cambioUsd || 0)
    : valorBase * Number(f.cambioUsd || 0);
  const totalUsd = principalUsd + Number(f.taxas || 0) * Number(f.taxasCambioUsd || 0)
    + Number(f.irrf || 0) * Number(f.cambioUsd || 0);

  const enviar = () => {
    if (trocaCripto) {
      salvarTrocaCripto.mutate({
        investidor_id: Number(f.investidor_id),
        ativo_origem_id: Number(f.ativo_id),
        ativo_destino_id: Number(destinoAtivoId),
        corretora_id: opcional(f.corretora_id),
        data: f.data,
        quantidade_origem: Math.abs(qtd),
        quantidade_destino: Number(destinoQuantidade),
        preco_origem: Math.abs(preco),
        taxas: Number(f.taxas || 0),
        irrf: Number(f.irrf || 0),
        moeda: f.moeda,
        cambio_usd: f.cambioUsd ? Number(f.cambioUsd) : null,
        cambio_usd_manual: !f.cambioUsdAuto,
        taxas_moeda: f.taxasMoeda,
        taxas_cambio_usd: f.taxasCambioUsd ? Number(f.taxasCambioUsd) : null,
        taxas_cambio_usd_manual: !f.taxasCambioUsdAuto,
        observacao: f.observacao || null,
      });
      return;
    }
    if (trocaVinculada) {
      salvarTroca.mutate({
        investidor_id: Number(f.investidor_id),
        ativo_origem_id: Number(f.ativo_id),
        ativo_destino_id: Number(destinoAtivoId),
        corretora_id: opcional(f.corretora_id),
        data: f.data,
        quantidade_origem: Math.abs(qtd),
        quantidade_destino: Number(destinoQuantidade),
        preco_origem: Math.abs(preco),
        taxas: Number(f.taxas || 0),
        irrf: Number(f.irrf || 0),
        moeda: f.moeda,
        cambio: f.moeda === "BRL" ? 1 : Number(f.cambio),
        observacao: f.observacao || null,
      });
      return;
    }
    if (ehCripto) {
      const magnitude = f.quantidade.trim().replace(/^[+-]/, "");
      const quantidade = f.evento === "R_CAP" ? "0"
        : QTD_NEGATIVA.includes(f.evento) ? `-${magnitude}`
          : f.evento in QTD_COM_SINAL ? f.quantidade : magnitude;
      salvar.mutate({
        investidor_id: f.investidor_id,
        ativo_id: f.ativo_id,
        corretora_id: opcional(f.corretora_id),
        data: f.data,
        evento: f.evento,
        quantidade,
        preco: ehCompraVenda ? "0" : PRECO_NEGATIVO.includes(f.evento) ? `-${f.preco.replace(/^[+-]/, "")}` : f.preco,
        taxas: f.taxas || "0",
        irrf: f.irrf || "0",
        moeda: f.moeda,
        daytrade: ehCompraVenda && f.daytrade,
        observacao: f.observacao || null,
        valor_original: ehCompraVenda ? f.valorOriginal : null,
        cambio_usd: f.cambioUsd || null,
        cambio_usd_manual: !f.cambioUsdAuto,
        taxas_moeda: f.taxasMoeda,
        taxas_cambio_usd: f.taxasCambioUsd || null,
        taxas_cambio_usd_manual: !f.taxasCambioUsdAuto,
      });
      return;
    }
    salvar.mutate({
      investidor_id: Number(f.investidor_id),
      ativo_id: Number(f.ativo_id),
      corretora_id: opcional(f.corretora_id),
      data: f.data,
      evento: f.evento,
      quantidade: f.evento === "R_CAP" ? 0 : QTD_NEGATIVA.includes(f.evento) ? -Math.abs(qtd) : qtd,
      preco: PRECO_NEGATIVO.includes(f.evento) ? -Math.abs(preco) : preco,
      taxas: Number(f.taxas || 0),
      irrf: Number(f.irrf || 0),
      moeda: f.moeda,
      cambio: f.moeda === "BRL" ? 1 : Number(f.cambio),
      daytrade: ehCompraVenda && f.daytrade,
      observacao: f.observacao || null,
    });
  };

  return (
    <MolduraForm
      titulo={operacao ? "Editar operação" : "Nova operação"}
      aoFechar={aoFechar}
      aoEnviar={enviar}
      salvando={salvar.isPending || salvarTroca.isPending || salvarTrocaCripto.isPending}
      erro={salvar.error ?? salvarTroca.error ?? salvarTrocaCripto.error}
      bloqueado={trocaIncompativel}
      rodape={<span className="sutil empurra">
        {ehCripto ? `Total estimado (USD): ${fmtMoeda(totalUsd, "USD")}` : `Total: ${fmtMoeda(totalBrl)}`}
      </span>}
    >
      <CampoInvestidor valor={f.investidor_id} aoMudar={(v) => mudar({ investidor_id: v })} />
      <label>
        Data
        <CampoData required valor={f.data} aoMudar={(v) => mudar({
          data: v, cambioAuto: true, cambioUsdAuto: true, taxasCambioUsdAuto: true,
        })} />
      </label>
      <CampoAtivo
        ativoId={f.ativo_id}
        aoMudar={(a) => {
          if (!a) {
            mudar({ ativo_id: "" });
            return;
          }
          const novaMoeda = a.classe === "CRIPTO"
            ? ativo?.classe === "CRIPTO" ? f.moeda : "USD"
            : a.moeda;
          mudar({
            ativo_id: String(a.id),
            moeda: novaMoeda,
            cambioAuto: true,
            cambioUsdAuto: true,
            taxasMoeda: a.classe === "CRIPTO"
              ? f.taxasMoeda === f.moeda ? novaMoeda : f.taxasMoeda
              : a.moeda,
            taxasCambioUsdAuto: true,
            ...(a.classe !== "CRIPTO" && a.moeda === "BRL" && { cambio: "1" }),
          });
        }}
      />
      <CampoEvento
        tipo="eventos_operacao"
        valor={f.evento}
        aoMudar={(v) => mudar({ evento: v, ...(v === "R_CAP" && { quantidade: "0" }) })}
      />
      {!operacao && f.evento === "TRANSFERENCIA" && (
        <label className="check largura-total">
          <input
            type="checkbox"
            checked={vincularDestino}
            onChange={(e) => setVincularDestino(e.target.checked)}
          />
          Informar e vincular o ticker de destino agora
        </label>
      )}
      <label>
        {trocaVinculada ? "Quantidade de saída" : "Quantidade"}
        <input
          required
          type="number"
          step="any"
          min={trocaVinculada ? "0.00000001" : f.evento in QTD_COM_SINAL ? undefined : "0"}
          readOnly={f.evento === "R_CAP"}
          value={f.quantidade}
          onChange={(e) => mudar({ quantidade: e.target.value })}
        />
        {trocaVinculada ? (
          <small className="sutil">A quantidade será registrada como saída; a nova perna será criada automaticamente.</small>
        ) : f.evento in QTD_COM_SINAL ? (
          <small className="sutil">{QTD_COM_SINAL[f.evento]}</small>
        ) : null}
      </label>
      {ehCripto && ehCompraVenda ? (
        <label>
          Valor total ({f.moeda})
          <input required type="number" step="any" min="0" value={f.valorOriginal}
            onChange={(e) => mudar({ valorOriginal: e.target.value })} />
        </label>
      ) : (
        <label>
          {f.evento === "R_CAP"
            ? "Valor devolvido"
            : PRECO_NEGATIVO.includes(f.evento)
            ? "Valor devolvido por cota"
            : trocaVinculada
              ? "Custo médio por cota de origem"
              : "Preço unitário"}
          <input
            type="number"
            step="any"
            min="0"
            required
            value={f.preco}
            onChange={(e) => {
              setPrecoAuto(false);
              mudar({ preco: e.target.value });
            }}
          />
          {trocaVinculada && (
            <small className="sutil">
              O custo total de origem será preservado; o custo unitário do destino é ajustado à quantidade recebida.
            </small>
          )}
          {cota.data && (
            <small className="sutil">
              Ativo personalizado: cota em {fmtData(cota.data.data)} = {numero(cota.data.cota, 6)}; quantidade = valor ÷ cota
              {String(cota.data.cota) !== f.preco && (
                <button type="button" className="link" onClick={() => setPrecoAuto(true)}>
                  usar
                </button>
              )}
            </small>
          )}
        </label>
      )}
      <label>
        Taxas
        <input type="number" step="any" min="0" value={f.taxas} onChange={(e) => mudar({ taxas: e.target.value })} />
      </label>
      {ehCripto && (
        <label>
          Moeda das taxas
          <select value={f.taxasMoeda} onChange={(e) => mudar({
            taxasMoeda: e.target.value, taxasCambioUsdAuto: true,
          })}>
            {["BRL", "USD", "EUR", "GBP"].map((codigo) => <option key={codigo}>{codigo}</option>)}
          </select>
        </label>
      )}
      <label>
        <span>IRRF <AjudaIndicador titulo="IRRF da operação" texto="IRRF é Imposto de Renda Retido na Fonte. Na bolsa, a retenção conhecida como dedo-duro costuma ser 0,005% sobre as vendas comuns ou 1% sobre o lucro do day trade. Informe o valor da nota, na moeda do lançamento. Reduz o lucro líquido da carteira; no fiscal é crédito do imposto, não despesa dedutível da base." /></span>
        <input type="number" step="any" min="0" value={f.irrf} onChange={(e) => mudar({ irrf: e.target.value })} />
      </label>
      {ehCripto ? (
        <>
          <label>
            Moeda da operação
            <select value={f.moeda} onChange={(e) => mudar({
              moeda: e.target.value,
              cambioUsdAuto: true,
              taxasMoeda: f.taxasMoeda === f.moeda ? e.target.value : f.taxasMoeda,
              taxasCambioUsdAuto: f.taxasMoeda === f.moeda ? true : f.taxasCambioUsdAuto,
            })}>
              {["BRL", "USD", "EUR", "GBP"].map((codigo) => <option key={codigo}>{codigo}</option>)}
            </select>
          </label>
          <label>
            Taxa da operação (USD por 1 {f.moeda})
            <input required type="number" step="any" min="0" value={f.cambioUsd}
              onChange={(e) => mudar({ cambioUsd: e.target.value, cambioUsdAuto: false })} />
            <small className="sutil">
              {cambioCripto.isFetching && "Consultando PTAX… "}
              {cambioCripto.error && `Câmbio automático indisponível: ${(cambioCripto.error as Error).message}. `}
              {taxaOperacao?.data_moeda && `PTAX ${f.moeda}: ${fmtData(taxaOperacao.data_moeda)}; `}
              {taxaOperacao?.data_usd && `USD: ${fmtData(taxaOperacao.data_usd)}. `}
              {f.cambioUsdAuto ? "Automática" : "Manual"}
              {!f.cambioUsdAuto && taxaOperacao?.cambio_usd !== null && taxaOperacao?.cambio_usd !== undefined && (
                <button type="button" className="link" onClick={() => mudar({ cambioUsdAuto: true })}>
                  usar PTAX
                </button>
              )}
            </small>
          </label>
          <label>
            Taxa das taxas (USD por 1 {f.taxasMoeda})
            <input required type="number" step="any" min="0" value={f.taxasCambioUsd}
              onChange={(e) => mudar({ taxasCambioUsd: e.target.value, taxasCambioUsdAuto: false })} />
            <small className="sutil">
              {taxaTaxas?.data_moeda && `PTAX ${f.taxasMoeda}: ${fmtData(taxaTaxas.data_moeda)}; `}
              {taxaTaxas?.data_usd && `USD: ${fmtData(taxaTaxas.data_usd)}. `}
              {f.taxasCambioUsdAuto ? "Automática" : "Manual"}
              {!f.taxasCambioUsdAuto && taxaTaxas?.cambio_usd !== null && taxaTaxas?.cambio_usd !== undefined && (
                <button type="button" className="link" onClick={() => mudar({ taxasCambioUsdAuto: true })}>
                  usar PTAX
                </button>
              )}
            </small>
          </label>
        </>
      ) : (
        <CamposMoedaCambio moeda={f.moeda} cambio={f.cambio} data={f.data} automatico={f.cambioAuto} aoMudar={mudarCambio} />
      )}
      {trocaVinculada && (
        <>
          <CampoAtivo
            ativoId={destinoAtivoId}
            aoMudar={(a) => setDestinoAtivoId(a ? String(a.id) : "")}
          />
          <label>
            Quantidade de entrada
            <input
              required
              type="number"
              step="any"
              min="0.00000001"
              value={destinoQuantidade}
              onChange={(e) => setDestinoQuantidade(e.target.value)}
            />
          </label>
          {trocaIncompativel && (
            <small className="negativo largura-total">
              Ativos cripto só podem ser vinculados a outro ativo cripto; nos demais casos, origem e destino precisam usar a mesma moeda.
            </small>
          )}
        </>
      )}
      <CampoCorretora valor={f.corretora_id} aoMudar={(v) => mudar({ corretora_id: v })} />
      <label className="largura-total">
        Observação
        <input
          maxLength={trocaVinculada ? 120 : 200}
          value={f.observacao}
          onChange={(e) => mudar({ observacao: e.target.value })}
        />
        {trocaVinculada && <small className="sutil">O sistema acrescentará os tickers de origem e destino à observação.</small>}
      </label>
      {ehCompraVenda && (
        <label className="check">
          <input type="checkbox" checked={f.daytrade} onChange={(e) => mudar({ daytrade: e.target.checked })} />
          Day trade
        </label>
      )}
    </MolduraForm>
  );
}

// ---------- Provento ----------

interface FormProv {
  investidor_id: string;
  ativo_id: string;
  corretora_id: string;
  data_pagamento: string;
  data_com: string;
  evento: string;
  valor: string;
  irrf: string;
  taxas: string;
  moeda: string;
  cambio: string;
  cambioAuto: boolean;
  observacao: string;
}

export function FormProvento({
  provento: p,
  eventoInicial = "DIVIDENDO",
  ocultarAluguel = false,
  aoFechar,
}: {
  provento?: Provento;
  eventoInicial?: string;
  ocultarAluguel?: boolean;
  aoFechar: () => void;
}) {
  const investidorPadrao = useInvestidorPadrao();
  const [f, setF] = useState<FormProv>(
    p
      ? {
          investidor_id: String(p.investidor_id), ativo_id: String(p.ativo_id), corretora_id: texto(p.corretora_id),
          data_pagamento: p.data_pagamento, data_com: p.data_com ?? "", evento: p.evento, valor: String(p.valor),
          irrf: String(p.irrf), taxas: String(p.taxas), moeda: p.moeda, cambio: String(p.cambio), cambioAuto: false,
          observacao: p.observacao ?? "",
        }
      : {
          investidor_id: investidorPadrao, ativo_id: "", corretora_id: "", data_pagamento: hoje(), data_com: "",
          evento: eventoInicial, valor: "", irrf: "0", taxas: "0", moeda: "BRL", cambio: "1", cambioAuto: true, observacao: "",
        },
  );
  const mudar = (parcial: Partial<FormProv>) => setF((atual) => ({ ...atual, ...parcial }));
  const mudarCambio = useCallback(
    (moeda: string, cambio: string, cambioAuto: boolean) => setF((a) => ({ ...a, moeda, cambio, cambioAuto })),
    [],
  );
  const salvar = useSalvar("proventos", p?.id, aoFechar);
  const liquido = (Number(f.valor || 0) - Number(f.irrf || 0) - Number(f.taxas || 0)) * Number(f.cambio || 1);

  const enviar = () =>
    salvar.mutate({
      investidor_id: Number(f.investidor_id),
      ativo_id: Number(f.ativo_id),
      corretora_id: opcional(f.corretora_id),
      data_pagamento: f.data_pagamento,
      data_com: f.data_com || null,
      evento: f.evento,
      valor: Number(f.valor),
      irrf: Number(f.irrf || 0),
      taxas: Number(f.taxas || 0),
      moeda: f.moeda,
      cambio: f.moeda === "BRL" ? 1 : Number(f.cambio),
      observacao: f.observacao || null,
    });

  return (
    <MolduraForm
      titulo={p ? "Editar provento" : "Novo provento"}
      aoFechar={aoFechar}
      aoEnviar={enviar}
      salvando={salvar.isPending}
      erro={salvar.error}
      rodape={<span className="sutil empurra">Líquido: {fmtMoeda(liquido)}</span>}
    >
      <CampoInvestidor valor={f.investidor_id} aoMudar={(v) => mudar({ investidor_id: v })} />
      <CampoAtivo
        ativoId={f.ativo_id}
        aoMudar={(a) => mudar(a ? { ativo_id: String(a.id), moeda: a.moeda, cambioAuto: true, ...(a.moeda === "BRL" && { cambio: "1" }) } : { ativo_id: "" })}
      />
      <CampoEvento
        tipo="eventos_provento"
        valor={f.evento}
        aoMudar={(v) => mudar({ evento: v })}
        excluir={ocultarAluguel ? ["ALUGUEL"] : undefined}
      />
      <label>
        Pagamento
        <CampoData required valor={f.data_pagamento} aoMudar={(v) => mudar({ data_pagamento: v, cambioAuto: true })} />
      </label>
      <label>
        Data com
        <CampoData valor={f.data_com} aoMudar={(v) => mudar({ data_com: v })} />
      </label>
      <label>
        Valor bruto
        <input required type="number" step="any" min="0" value={f.valor} onChange={(e) => mudar({ valor: e.target.value })} />
      </label>
      <label>
        <span>IRRF <AjudaIndicador titulo="IRRF do provento" texto="Imposto de Renda Retido na Fonte sobre o rendimento, informado na moeda do lançamento. É descontado do valor bruto para chegar ao líquido. As alíquotas e o tratamento dependem do tipo de rendimento; não é necessariamente a retenção dedo-duro da bolsa." /></span>
        <input type="number" step="any" min="0" value={f.irrf} onChange={(e) => mudar({ irrf: e.target.value })} />
      </label>
      <label>
        Taxas
        <input type="number" step="any" min="0" value={f.taxas} onChange={(e) => mudar({ taxas: e.target.value })} />
      </label>
      <CamposMoedaCambio
        moeda={f.moeda}
        cambio={f.cambio}
        data={f.data_pagamento}
        automatico={f.cambioAuto}
        aoMudar={mudarCambio}
      />
      <CampoCorretora valor={f.corretora_id} aoMudar={(v) => mudar({ corretora_id: v })} />
      <label className="largura-total">
        Observação
        <input maxLength={200} value={f.observacao} onChange={(e) => mudar({ observacao: e.target.value })} />
      </label>
    </MolduraForm>
  );
}

// ---------- Caixa ----------

/** Igual a EVENTOS_CAIXA_ENTRADA no backend: entradas > 0, saídas < 0. */
export const ENTRADAS_CAIXA = ["APORTE", "CREDITO"];

interface FormCx {
  investidor_id: string;
  corretora_id: string;
  data: string;
  evento: string;
  valor: string;
  moeda: string;
  observacao: string;
}

export function FormCaixa({ mov, aoFechar }: { mov?: MovCaixa; aoFechar: () => void }) {
  const investidorPadrao = useInvestidorPadrao();
  const { data: dominio } = useDominio();
  const [f, setF] = useState<FormCx>(
    mov
      ? {
          investidor_id: String(mov.investidor_id), corretora_id: texto(mov.corretora_id), data: mov.data,
          evento: mov.evento, valor: String(Math.abs(mov.valor)), moeda: mov.moeda, observacao: mov.observacao ?? "",
        }
      : { investidor_id: investidorPadrao, corretora_id: "", data: hoje(), evento: "APORTE", valor: "", moeda: "BRL", observacao: "" },
  );
  const mudar = (parcial: Partial<FormCx>) => setF((atual) => ({ ...atual, ...parcial }));
  const salvar = useSalvar("caixa", mov?.id, aoFechar);

  const enviar = () => {
    const valor = Math.abs(Number(f.valor));
    salvar.mutate({
      investidor_id: Number(f.investidor_id),
      corretora_id: opcional(f.corretora_id),
      data: f.data,
      evento: f.evento,
      valor: ENTRADAS_CAIXA.includes(f.evento) ? valor : -valor,
      moeda: f.moeda,
      observacao: f.observacao || null,
    });
  };

  return (
    <MolduraForm
      titulo={mov ? "Editar movimentação" : "Nova movimentação de caixa"}
      aoFechar={aoFechar}
      aoEnviar={enviar}
      salvando={salvar.isPending}
      erro={salvar.error}
    >
      <CampoInvestidor valor={f.investidor_id} aoMudar={(v) => mudar({ investidor_id: v })} />
      <label>
        Data
        <CampoData required valor={f.data} aoMudar={(v) => mudar({ data: v })} />
      </label>
      <CampoEvento tipo="eventos_caixa" valor={f.evento} aoMudar={(v) => mudar({ evento: v })} />
      <label>
        Valor
        <input required type="number" step="any" min="0.01" value={f.valor} onChange={(e) => mudar({ valor: e.target.value })} />
      </label>
      <label>
        Moeda
        <select value={f.moeda} onChange={(e) => mudar({ moeda: e.target.value })}>
          {(dominio?.moedas ?? ["BRL"]).map((m) => (
            <option key={m}>{m}</option>
          ))}
        </select>
      </label>
      <CampoCorretora valor={f.corretora_id} aoMudar={(v) => mudar({ corretora_id: v })} />
      <label className="largura-total">
        Observação
        <input maxLength={200} value={f.observacao} onChange={(e) => mudar({ observacao: e.target.value })} />
      </label>
    </MolduraForm>
  );
}
