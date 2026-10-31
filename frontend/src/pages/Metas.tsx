import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { api } from "../api";
import { paraFracao, paraPercentual } from "../cadastros";
import { CampoData } from "../components/CampoData";
import { GraficoLinhas } from "../components/Graficos";
import { Modal } from "../components/Modal";
import { data, mesAno, moeda, moedaCompacta, percentual } from "../formato";
import { useInvestidor } from "../InvestidorContext";
import type { Meta, TipoMeta } from "../tipos";

interface FormMeta {
  id?: number;
  nome: string;
  tipo: TipoMeta;
  valor_alvo: string;
  data_alvo: string;
  aporte_mensal: string;
  rentabilidade_aa: string;
  rendimento_aa: string;
  investidores: number[];
}

const daquiDezAnos = () => {
  const d = new Date();
  return `${d.getFullYear() + 10}-${String(d.getMonth() + 1).padStart(2, "0")}-01`;
};

const VAZIO: FormMeta = {
  nome: "", tipo: "PATRIMONIO", valor_alvo: "", data_alvo: daquiDezAnos(), aporte_mensal: "0", rentabilidade_aa: "4",
  rendimento_aa: "", investidores: [],
};

const ROTULO_TIPO: Record<TipoMeta, string> = { PATRIMONIO: "Patrimônio", RENDA: "Renda mensal de proventos" };

function FormularioMeta({ inicial, aoFechar }: { inicial: FormMeta; aoFechar: () => void }) {
  const { investidores } = useInvestidor();
  const cliente = useQueryClient();
  const [form, setForm] = useState(inicial);
  const salvar = useMutation({
    mutationFn: (f: FormMeta) => {
      const corpo = {
        nome: f.nome,
        tipo: f.tipo,
        valor_alvo: Number(f.valor_alvo),
        data_alvo: f.data_alvo,
        aporte_mensal: Number(f.aporte_mensal || 0),
        rentabilidade_aa: paraFracao(f.rentabilidade_aa),
        rendimento_aa: f.tipo === "RENDA" && f.rendimento_aa !== "" ? paraFracao(f.rendimento_aa) : null,
        investidores: f.investidores.length ? f.investidores : null,
      };
      return f.id ? api.put<Meta>(`/metas/${f.id}`, corpo) : api.post<Meta>("/metas", corpo);
    },
    onSuccess: () => {
      cliente.invalidateQueries({ queryKey: ["metas"] });
      aoFechar();
    },
  });
  const alternar = (id: number) =>
    setForm({
      ...form,
      investidores: form.investidores.includes(id) ? form.investidores.filter((i) => i !== id) : [...form.investidores, id],
    });
  const enviar = (e: FormEvent) => {
    e.preventDefault();
    salvar.mutate(form);
  };

  return (
    <Modal titulo={form.id ? "Editar meta" : "Nova meta"} aoFechar={aoFechar}>
      <form className="formulario em-modal" onSubmit={enviar}>
        {salvar.error && <div className="erro largura-total">{(salvar.error as Error).message}</div>}
        <label>
          Nome
          <input required maxLength={80} value={form.nome} onChange={(e) => setForm({ ...form, nome: e.target.value })} />
        </label>
        <label>
          Tipo
          <select value={form.tipo} onChange={(e) => setForm({ ...form, tipo: e.target.value as TipoMeta })}>
            {Object.entries(ROTULO_TIPO).map(([valor, rotulo]) => (
              <option key={valor} value={valor}>
                {rotulo}
              </option>
            ))}
          </select>
        </label>
        <label>
          {form.tipo === "RENDA" ? "Renda mensal desejada (R$)" : "Patrimônio desejado (R$)"}
          <input
            required
            type="number"
            min="1"
            step="any"
            value={form.valor_alvo}
            onChange={(e) => setForm({ ...form, valor_alvo: e.target.value })}
          />
        </label>
        <label>
          Data-alvo
          <CampoData required valor={form.data_alvo} aoMudar={(v) => setForm({ ...form, data_alvo: v })} />
        </label>
        <label>
          Aporte mensal (R$)
          <input
            type="number"
            min="0"
            step="any"
            value={form.aporte_mensal}
            onChange={(e) => setForm({ ...form, aporte_mensal: e.target.value })}
          />
        </label>
        <label>
          Rentabilidade real a.a. (%)
          <input
            required
            type="number"
            step="any"
            min="-49"
            max="100"
            value={form.rentabilidade_aa}
            onChange={(e) => setForm({ ...form, rentabilidade_aa: e.target.value })}
          />
          <small className="sutil">Acima da inflação. Os valores ficam em reais de hoje.</small>
        </label>
        {form.tipo === "RENDA" && (
          <label>
            Dividend yield a.a. (%)
            <input
              type="number"
              step="any"
              min="0.01"
              max="100"
              placeholder="atual da carteira"
              value={form.rendimento_aa}
              onChange={(e) => setForm({ ...form, rendimento_aa: e.target.value })}
            />
            <small className="sutil">Converte patrimônio em renda. Em branco = rendimento dos últimos 12 meses.</small>
          </label>
        )}
        <fieldset className="largura-total">
          <legend>Investidores (nenhum marcado = todos)</legend>
          {investidores
            .filter((i) => i.ativo)
            .map((i) => (
              <label key={i.id} className="check">
                <input type="checkbox" checked={form.investidores.includes(i.id)} onChange={() => alternar(i.id)} />
                {i.nome}
              </label>
            ))}
        </fieldset>
        <div className="acoes largura-total">
          <button type="submit" disabled={salvar.isPending}>
            Salvar
          </button>
          <button type="button" className="secundario" onClick={aoFechar}>
            Cancelar
          </button>
        </div>
      </form>
    </Modal>
  );
}

function CartaoMeta({ meta, aoEditar }: { meta: Meta; aoEditar: () => void }) {
  const cliente = useQueryClient();
  const { investidores } = useInvestidor();
  const excluir = useMutation({
    mutationFn: () => api.del(`/metas/${meta.id}`),
    onSuccess: () => cliente.invalidateQueries({ queryKey: ["metas"] }),
  });
  const renda = meta.tipo === "RENDA";
  const sufixo = renda ? "/mês" : "";
  const quem = meta.investidores
    ? meta.investidores.map((id) => investidores.find((i) => i.id === id)?.nome ?? id).join(", ")
    : "Todos os investidores";
  const progresso = Math.max(0, Math.min(1, meta.progresso));

  return (
    <div className="painel meta">
      <div className="titulo-linha">
        <h3>
          🎯 {meta.nome} <span className="etiqueta">{ROTULO_TIPO[meta.tipo]}</span>
        </h3>
        <div className="acoes">
          <button className="link" onClick={aoEditar}>
            Editar
          </button>
          <button className="link perigo" onClick={() => confirm(`Excluir a meta ${meta.nome}?`) && excluir.mutate()}>
            Excluir
          </button>
        </div>
      </div>
      <p className="sutil">
        {quem} · alvo {moeda(meta.valor_alvo)}
        {sufixo} até {data(meta.data_alvo)} ({meta.meses_restantes} meses) · aporte {moeda(meta.aporte_mensal)}/mês · rentabilidade real{" "}
        {percentual(meta.rentabilidade_aa)} a.a.
        {renda && <> · dividend yield {percentual(meta.rendimento_usado)} a.a.</>}
      </p>

      <div className="meta-progresso" role="progressbar" aria-valuenow={Math.round(progresso * 100)} aria-valuemin={0} aria-valuemax={100}>
        <div className="meta-progresso-barra" style={{ width: `${progresso * 100}%` }} />
      </div>
      <p>
        Hoje: <strong>{moeda(meta.valor_atual)}</strong>
        {sufixo} · <strong>{percentual(meta.progresso)}</strong> do alvo
      </p>

      <div className="cards">
        <div className="card">
          <span>Projeção na data-alvo</span>
          <strong className={meta.atinge ? undefined : "negativo"}>
            {moeda(meta.projetado_base)}
            {sufixo}
          </strong>
          <small className="sutil">
            {meta.atinge ? "atinge o alvo" : "abaixo do alvo"} · cenários: {moeda(meta.projetado_pessimista)} a{" "}
            {moeda(meta.projetado_otimista)}
          </small>
        </div>
        <div className="card">
          <span>Atinge o alvo em</span>
          <strong>{meta.data_estimada ? mesAno(meta.data_estimada) : "não atinge em 50 anos"}</strong>
          <small className="sutil">mantendo aporte e rentabilidade</small>
        </div>
        <div className="card">
          <span>Aporte necessário para o prazo</span>
          <strong>{moeda(meta.aporte_necessario)}/mês</strong>
          <small className="sutil">{meta.aporte_necessario <= meta.aporte_mensal ? "o aporte atual é suficiente" : "acima do aporte atual"}</small>
        </div>
      </div>

      <GraficoLinhas
        datas={meta.serie.map((p) => p.mes)}
        formatar={moedaCompacta}
        series={[
          { nome: "Otimista (+2 p.p.)", cor: "#93c5fd", valores: meta.serie.map((p) => p.otimista), tracejada: true },
          { nome: "Base", cor: "var(--primaria)", valores: meta.serie.map((p) => p.base) },
          { nome: "Pessimista (−2 p.p.)", cor: "#94a3b8", valores: meta.serie.map((p) => p.pessimista), tracejada: true },
          { nome: "Alvo", cor: "#f59e0b", valores: meta.serie.map(() => meta.valor_alvo), tracejada: true },
        ]}
      />
    </div>
  );
}

export function Metas() {
  const [edicao, setEdicao] = useState<FormMeta | null>(null);
  const { data: metas = [], isLoading, error } = useQuery({ queryKey: ["metas"], queryFn: () => api.get<Meta[]>("/metas") });

  const editar = (m: Meta) =>
    setEdicao({
      id: m.id,
      nome: m.nome,
      tipo: m.tipo,
      valor_alvo: String(m.valor_alvo),
      data_alvo: m.data_alvo,
      aporte_mensal: String(m.aporte_mensal),
      rentabilidade_aa: paraPercentual(m.rentabilidade_aa),
      rendimento_aa: paraPercentual(m.rendimento_aa),
      investidores: m.investidores ?? [],
    });

  return (
    <section>
      <div className="titulo-linha">
        <h1>Metas</h1>
        <button onClick={() => setEdicao({ ...VAZIO, data_alvo: daquiDezAnos() })}>+ Nova meta</button>
      </div>
      {error && <div className="erro">{(error as Error).message}</div>}
      {isLoading && <p>Carregando…</p>}
      {!isLoading && metas.length === 0 && (
        <div className="aviso">
          Defina um objetivo — patrimônio (ex.: R$ 1 milhão em 2040) ou renda mensal de proventos (ex.: R$ 5 mil/mês) — e acompanhe o
          progresso, a projeção com seus aportes e o aporte necessário para chegar lá.
        </div>
      )}
      {metas.map((m) => (
        <CartaoMeta key={m.id} meta={m} aoEditar={() => editar(m)} />
      ))}
      <p className="sutil">
        Projeção em valores de hoje: aportes mensais constantes e rentabilidade real (acima da inflação) composta mês a mês; cenários
        variam a rentabilidade em 2 p.p. a.a. O valor atual usa o mercado das posições abertas (metas de patrimônio) ou os proventos
        líquidos dos últimos 12 meses ÷ 12 (metas de renda). É simulação, não recomendação de investimento.
      </p>
      {edicao && <FormularioMeta inicial={edicao} aoFechar={() => setEdicao(null)} />}
    </section>
  );
}
