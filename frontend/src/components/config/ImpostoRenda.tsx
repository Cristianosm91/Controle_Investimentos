import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState, type FormEvent } from "react";
import { api, query } from "../../api";
import { invalidarDerivados, paraFracao, paraPercentual, useDominio, useParametros } from "../../cadastros";
import { data, moeda, percentual } from "../../formato";
import type { Parametros, PrejuizoInicial, RegraFiscal } from "../../tipos";
import { SeletorInvestidorIR, useInvestidorIR } from "../SeletorInvestidorIR";
import { CampoData } from "../CampoData";
import { useExclusaoEmLote } from "../ExclusaoEmLote";

function ParametrosIR() {
  const { data: atuais } = useParametros();
  const cliente = useQueryClient();
  const [form, setForm] = useState<Parametros | null>(null);
  const [salvo, setSalvo] = useState(false);

  useEffect(() => {
    if (atuais) setForm(atuais);
  }, [atuais]);

  const salvar = useMutation({
    mutationFn: (p: Parametros) => api.put<Parametros>("/parametros", p),
    onSuccess: (p) => {
      cliente.setQueryData(["parametros"], p);
      invalidarDerivados(cliente);
      setSalvo(true);
    },
  });

  if (!form) return null;
  const enviar = (e: FormEvent) => {
    e.preventDefault();
    setSalvo(false);
    salvar.mutate(form);
  };

  return (
    <form className="formulario" onSubmit={enviar}>
      <h3>Parâmetros de cálculo</h3>
      {salvar.error && <div className="erro largura-total">{(salvar.error as Error).message}</div>}
      {salvo && <div className="aviso largura-total">Parâmetros salvos.</div>}
      <label>
        Primeiro ano apurado
        <input
          type="number"
          min={1990}
          max={2100}
          placeholder="Desde a 1ª venda"
          value={form.ir_ano_inicio ?? ""}
          onChange={(e) => setForm({ ...form, ir_ano_inicio: e.target.value ? Number(e.target.value) : null })}
        />
        <small className="sutil">Vendas anteriores só formam o preço médio; informe abaixo o prejuízo trazido.</small>
      </label>
      <label className="check">
        <input type="checkbox" checked={form.ir_bdr_como_acao} onChange={(e) => setForm({ ...form, ir_bdr_como_acao: e.target.checked })} />
        Tratar BDR como ação (isenção de R$ 20 mil)
      </label>
      <label className="check">
        <input
          type="checkbox"
          checked={form.ir_daytrade_no_limite}
          onChange={(e) => setForm({ ...form, ir_daytrade_no_limite: e.target.checked })}
        />
        Somar vendas de day trade ao limite de R$ 20 mil
      </label>
      <label className="check">
        <input type="checkbox" checked={form.ir_opcoes_no_limite} onChange={(e) => setForm({ ...form, ir_opcoes_no_limite: e.target.checked })} />
        Somar vendas de opções ao limite de R$ 20 mil
      </label>
      <label className="check">
        <input
          type="checkbox"
          checked={form.ir_outras_classes_no_limite}
          onChange={(e) => setForm({ ...form, ir_outras_classes_no_limite: e.target.checked })}
        />
        Somar vendas de BDR e ETF ao limite de R$ 20 mil
      </label>
      <label className="check">
        <input
          type="checkbox"
          checked={form.ir_subscricao_fii_isenta}
          onChange={(e) => setForm({ ...form, ir_subscricao_fii_isenta: e.target.checked })}
        />
        Venda de direito de subscrição de FII até 28/09/2021 como isenta (padrão: 20% como FII)
      </label>
      <div className="acoes largura-total">
        <button type="submit" disabled={salvar.isPending}>
          Salvar
        </button>
      </div>
    </form>
  );
}

function PrejuizosIniciais() {
  const { data: dominio } = useDominio();
  const cliente = useQueryClient();
  const [investidor, setInvestidor] = useInvestidorIR();
  const [valores, setValores] = useState<Record<string, string>>({});
  const [salvo, setSalvo] = useState(false);
  const { data: atuais } = useQuery({
    queryKey: ["ir-prejuizos", investidor],
    queryFn: () => api.get<PrejuizoInicial[]>(`/ir/prejuizos-iniciais${query({ investidor })}`),
    enabled: investidor !== undefined,
  });

  useEffect(() => {
    setSalvo(false);
    setValores(Object.fromEntries((atuais ?? []).map((p) => [p.grupo, String(p.valor)])));
  }, [atuais]);

  const salvar = useMutation({
    mutationFn: () =>
      api.put<PrejuizoInicial[]>(
        `/ir/prejuizos-iniciais${query({ investidor })}`,
        Object.entries(valores).map(([grupo, v]) => ({ grupo, valor: Number(v || 0) })),
      ),
    onSuccess: (p) => {
      cliente.setQueryData(["ir-prejuizos", investidor], p);
      invalidarDerivados(cliente);
      setSalvo(true);
    },
  });

  if (!dominio || investidor === undefined) return null;
  return (
    <form
      className="formulario"
      onSubmit={(e) => {
        e.preventDefault();
        salvar.mutate();
      }}
    >
      <h3>Prejuízo a compensar trazido de antes do primeiro ano apurado</h3>
      <div className="largura-total">
        <SeletorInvestidorIR valor={investidor} aoMudar={setInvestidor} />
      </div>
      {salvar.error && <div className="erro largura-total">{(salvar.error as Error).message}</div>}
      {salvo && <div className="aviso largura-total">Prejuízos salvos.</div>}
      {Object.entries(dominio.grupos_prejuizo).map(([grupo, rotulo]) => (
        <label key={grupo}>
          {rotulo} (R$)
          <input
            type="number"
            min={0}
            step="0.01"
            value={valores[grupo] ?? ""}
            onChange={(e) => setValores({ ...valores, [grupo]: e.target.value })}
          />
        </label>
      ))}
      <div className="acoes largura-total">
        <button type="submit" disabled={salvar.isPending}>
          Salvar
        </button>
      </div>
    </form>
  );
}

interface FormRegra {
  id?: number;
  categoria: string;
  vigencia_inicio: string;
  vigencia_fim: string;
  aliquota: string;
  limite_isencao: string;
  apuracao: "MENSAL" | "ANUAL";
  observacao: string;
}

const REGRA_VAZIA: FormRegra = {
  categoria: "ACAO", vigencia_inicio: "", vigencia_fim: "", aliquota: "15", limite_isencao: "", apuracao: "MENSAL", observacao: "",
};

function RegrasFiscais() {
  const { data: dominio } = useDominio();
  const cliente = useQueryClient();
  const [form, setForm] = useState<FormRegra | null>(null);
  const { data: regras = [], error } = useQuery({ queryKey: ["ir-regras"], queryFn: () => api.get<RegraFiscal[]>("/ir/regras") });

  const aposGravar = () => {
    setForm(null);
    cliente.invalidateQueries({ queryKey: ["ir-regras"] });
    invalidarDerivados(cliente);
  };
  const salvar = useMutation({
    mutationFn: (f: FormRegra) => {
      const corpo = {
        categoria: f.categoria,
        vigencia_inicio: f.vigencia_inicio,
        vigencia_fim: f.vigencia_fim || null,
        aliquota: paraFracao(f.aliquota),
        limite_isencao: f.limite_isencao ? Number(f.limite_isencao) : null,
        apuracao: f.apuracao,
        observacao: f.observacao || null,
      };
      return f.id ? api.put(`/ir/regras/${f.id}`, corpo) : api.post("/ir/regras", corpo);
    },
    onSuccess: aposGravar,
  });
  const excluir = useMutation({ mutationFn: (id: number) => api.del(`/ir/regras/${id}`), onSuccess: aposGravar });
  const selecao = useExclusaoEmLote({
    itens: regras,
    chave: (r) => r.id,
    remover: (id) => api.del(`/ir/regras/${id}`),
    titulo: "regras fiscais",
    consulta: "ir-regras",
    aposExcluir: aposGravar,
  });

  const editar = (r: RegraFiscal) =>
    setForm({
      id: r.id, categoria: r.categoria, vigencia_inicio: r.vigencia_inicio, vigencia_fim: r.vigencia_fim ?? "",
      aliquota: paraPercentual(r.aliquota), limite_isencao: r.limite_isencao === null ? "" : String(r.limite_isencao),
      apuracao: r.apuracao, observacao: r.observacao ?? "",
    });

  const erro = error ?? salvar.error ?? excluir.error;
  const nome = (c: string) => dominio?.categorias_ir[c] ?? c;

  return (
    <>
      <div className="titulo-linha">
        <h3>Regras fiscais com vigência</h3>
        <button onClick={() => setForm(REGRA_VAZIA)}>+ Nova regra</button>
      </div>
      <p className="sutil">
        Alíquota e isenção por categoria e período. Ao mudar a legislação, encerre a vigência da regra atual e cadastre a nova.
        {regras.length === 0 && " Sem regras cadastradas: o cálculo usa as regras padrão da RFB."}
      </p>
      {erro && <div className="erro">{(erro as Error).message}</div>}
      {selecao.acoes}
      <table className="tabela compacta">
        <thead>
          <tr>
            <th />
            <th>Categoria</th>
            <th>Vigência</th>
            <th className="num">Alíquota</th>
            <th className="num">Isenção até (vendas/mês)</th>
            <th>Apuração</th>
            <th>Observação</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {regras.map((r) => (
            <tr key={r.id}>
              <td>{selecao.checkbox(r.id)}</td>
              <td>{nome(r.categoria)}</td>
              <td>
                {data(r.vigencia_inicio)} – {r.vigencia_fim ? data(r.vigencia_fim) : "atual"}
              </td>
              <td className="num">{percentual(r.aliquota)}</td>
              <td className="num">{r.limite_isencao === null ? "—" : moeda(r.limite_isencao)}</td>
              <td>{r.apuracao === "ANUAL" ? "Anual" : "Mensal"}</td>
              <td className="quebra sutil">{r.observacao}</td>
              <td className="num acoes-linha">
                <button className="link" onClick={() => editar(r)}>
                  Editar
                </button>
                <button className="link perigo" onClick={() => confirm(`Excluir regra de ${nome(r.categoria)}?`) && excluir.mutate(r.id)}>
                  Excluir
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {form && (
        <form
          className="formulario"
          onSubmit={(e) => {
            e.preventDefault();
            salvar.mutate(form);
          }}
        >
          <h3>{form.id ? "Editar regra" : "Nova regra"}</h3>
          <label>
            Categoria
            <select value={form.categoria} onChange={(e) => setForm({ ...form, categoria: e.target.value })}>
              {Object.entries(dominio?.categorias_ir ?? {}).map(([c, rotulo]) => (
                <option key={c} value={c}>
                  {rotulo}
                </option>
              ))}
            </select>
          </label>
          <label>
            Início da vigência
            <CampoData required valor={form.vigencia_inicio} aoMudar={(v) => setForm({ ...form, vigencia_inicio: v })} />
          </label>
          <label>
            Fim da vigência
            <CampoData valor={form.vigencia_fim} aoMudar={(v) => setForm({ ...form, vigencia_fim: v })} />
          </label>
          <label>
            Alíquota (%)
            <input type="number" required min={0} max={100} step="0.01" value={form.aliquota} onChange={(e) => setForm({ ...form, aliquota: e.target.value })} />
          </label>
          <label>
            Isenção até (R$ vendas/mês)
            <input type="number" min={0} step="0.01" value={form.limite_isencao} onChange={(e) => setForm({ ...form, limite_isencao: e.target.value })} />
          </label>
          <label>
            Apuração
            <select value={form.apuracao} onChange={(e) => setForm({ ...form, apuracao: e.target.value as FormRegra["apuracao"] })}>
              <option value="MENSAL">Mensal</option>
              <option value="ANUAL">Anual (exterior)</option>
            </select>
          </label>
          <label className="largura-total">
            Observação
            <input maxLength={200} value={form.observacao} onChange={(e) => setForm({ ...form, observacao: e.target.value })} />
          </label>
          <div className="acoes largura-total">
            <button type="submit" disabled={salvar.isPending}>
              Salvar
            </button>
            <button type="button" className="secundario" onClick={() => setForm(null)}>
              Cancelar
            </button>
          </div>
        </form>
      )}
    </>
  );
}

export function ImpostoRendaConfig() {
  return (
    <>
      <h2>Imposto de renda</h2>
      <p className="sutil">
        Apuração mensal por CPF (DARF 6015). Prejuízo compensa só dentro do mesmo grupo: operações comuns (ações, BDR, ETF, opções), day
        trade, FII e exterior.
      </p>
      <ParametrosIR />
      <PrejuizosIniciais />
      <h2>Regras</h2>
      <RegrasFiscais />
    </>
  );
}
