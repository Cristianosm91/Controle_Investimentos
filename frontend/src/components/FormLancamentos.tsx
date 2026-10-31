import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useState, type FormEvent, type ReactNode } from "react";
import { api, query } from "../api";
import { invalidarDerivados, useAtivos, useDominio } from "../cadastros";
import { data as fmtData, moeda as fmtMoeda, numero } from "../formato";
import { useInvestidor } from "../InvestidorContext";
import type { Ativo, Cota, MovCaixa, Operacao, Provento } from "../tipos";
import { CampoAtivo, CampoCorretora, CampoEvento, CampoInvestidor, CamposMoedaCambio } from "./Campos";
import { CampoData } from "./CampoData";
import { Modal } from "./Modal";

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
  rodape?: ReactNode;
  children: ReactNode;
}

function MolduraForm({ titulo, aoFechar, aoEnviar, salvando, erro, rodape, children }: Moldura) {
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
          <button type="submit" disabled={salvando}>
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
const PRECO_NEGATIVO = ["AMORTIZACAO", "CISAO"];
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
  const investidorPadrao = useInvestidorPadrao();
  const { data: ativos = [] } = useAtivos();
  const [f, setF] = useState<FormOp>(
    operacao
      ? paraFormOp(operacao)
      : {
          investidor_id: investidorPadrao, ativo_id: "", corretora_id: "", data: hoje(), evento: "C", quantidade: "",
          preco: "", taxas: "0", irrf: "0", moeda: "BRL", cambio: "1", cambioAuto: true, daytrade: false, observacao: "",
        },
  );
  const [precoAuto, setPrecoAuto] = useState(!operacao);
  const mudar = (parcial: Partial<FormOp>) => setF((atual) => ({ ...atual, ...parcial }));
  const mudarCambio = useCallback(
    (moeda: string, cambio: string, cambioAuto: boolean) => setF((a) => ({ ...a, moeda, cambio, cambioAuto })),
    [],
  );
  const salvar = useSalvar("operacoes", operacao?.id, aoFechar);

  const ativo = ativos.find((a) => String(a.id) === f.ativo_id);
  const ehCompraVenda = f.evento === "C" || f.evento === "V";
  const cota = useCotaPersonalizado(ativo, f.data, ehCompraVenda);
  useEffect(() => {
    if (precoAuto && cota.data) setF((a) => ({ ...a, preco: String(cota.data.cota) }));
  }, [precoAuto, cota.data]);

  const qtd = Number(f.quantidade || 0);
  const preco = Number(f.preco || 0);
  const total = Math.abs(qtd * preco) * Number(f.cambio || 1) + Number(f.taxas || 0) * Number(f.cambio || 1);

  const enviar = () =>
    salvar.mutate({
      investidor_id: Number(f.investidor_id),
      ativo_id: Number(f.ativo_id),
      corretora_id: opcional(f.corretora_id),
      data: f.data,
      evento: f.evento,
      quantidade: QTD_NEGATIVA.includes(f.evento) ? -Math.abs(qtd) : qtd,
      preco: PRECO_NEGATIVO.includes(f.evento) ? -Math.abs(preco) : preco,
      taxas: Number(f.taxas || 0),
      irrf: Number(f.irrf || 0),
      moeda: f.moeda,
      cambio: f.moeda === "BRL" ? 1 : Number(f.cambio),
      daytrade: ehCompraVenda && f.daytrade,
      observacao: f.observacao || null,
    });

  return (
    <MolduraForm
      titulo={operacao ? "Editar operação" : "Nova operação"}
      aoFechar={aoFechar}
      aoEnviar={enviar}
      salvando={salvar.isPending}
      erro={salvar.error}
      rodape={<span className="sutil empurra">Total: {fmtMoeda(total)}</span>}
    >
      <CampoInvestidor valor={f.investidor_id} aoMudar={(v) => mudar({ investidor_id: v })} />
      <label>
        Data
        <CampoData required valor={f.data} aoMudar={(v) => mudar({ data: v, cambioAuto: true })} />
      </label>
      <CampoAtivo
        ativoId={f.ativo_id}
        aoMudar={(a) => mudar(a ? { ativo_id: String(a.id), moeda: a.moeda, cambioAuto: true, ...(a.moeda === "BRL" && { cambio: "1" }) } : { ativo_id: "" })}
      />
      <CampoEvento tipo="eventos_operacao" valor={f.evento} aoMudar={(v) => mudar({ evento: v })} />
      <label>
        Quantidade
        <input
          required
          type="number"
          step="any"
          min={f.evento in QTD_COM_SINAL ? undefined : "0"}
          value={f.quantidade}
          onChange={(e) => mudar({ quantidade: e.target.value })}
        />
        {f.evento in QTD_COM_SINAL && <small className="sutil">{QTD_COM_SINAL[f.evento]}</small>}
      </label>
      <label>
        {PRECO_NEGATIVO.includes(f.evento) ? "Valor devolvido por cota" : "Preço unitário"}
        <input
          type="number"
          step="any"
          min="0"
          value={f.preco}
          onChange={(e) => {
            setPrecoAuto(false);
            mudar({ preco: e.target.value });
          }}
        />
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
      <label>
        Taxas
        <input type="number" step="any" min="0" value={f.taxas} onChange={(e) => mudar({ taxas: e.target.value })} />
      </label>
      <label>
        IRRF
        <input type="number" step="any" min="0" value={f.irrf} onChange={(e) => mudar({ irrf: e.target.value })} />
      </label>
      <CamposMoedaCambio moeda={f.moeda} cambio={f.cambio} data={f.data} automatico={f.cambioAuto} aoMudar={mudarCambio} />
      <CampoCorretora valor={f.corretora_id} aoMudar={(v) => mudar({ corretora_id: v })} />
      <label className="largura-total">
        Observação
        <input maxLength={200} value={f.observacao} onChange={(e) => mudar({ observacao: e.target.value })} />
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

export function FormProvento({ provento: p, aoFechar }: { provento?: Provento; aoFechar: () => void }) {
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
          evento: "DIVIDENDO", valor: "", irrf: "0", taxas: "0", moeda: "BRL", cambio: "1", cambioAuto: true, observacao: "",
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
      <CampoEvento tipo="eventos_provento" valor={f.evento} aoMudar={(v) => mudar({ evento: v })} />
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
        IRRF
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
