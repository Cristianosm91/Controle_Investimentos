import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { api, query } from "../../api";
import { invalidarDerivados, paraFracao, paraPercentual, useDominio } from "../../cadastros";
import { data as fmtData, numero, percentual } from "../../formato";
import type { Ativo, Cota } from "../../tipos";
import { CampoData } from "../CampoData";

const hoje = () => new Date().toLocaleDateString("sv-SE");

interface FormAtivo {
  id?: number;
  ticker: string;
  nome: string;
  classe: string;
  moeda: string;
  automatico: boolean;
  indexador: string;
  indexador_pct: string;
  taxa_aa: string;
  data_base: string;
  original?: Ativo;
}

const VAZIO: FormAtivo = {
  ticker: "", nome: "", classe: "R.FIXA", moeda: "BRL", automatico: true, indexador: "CDI", indexador_pct: "100",
  taxa_aa: "", data_base: hoje(),
};

const NOME_INDICE: Record<string, string> = { CDI: "CDI", SELIC: "SELIC", IPCA: "IPCA", IGPM: "IGP-M" };

function descricao(a: Ativo): string {
  if (!a.indexador) return "Saldo manual";
  const taxa = a.taxa_aa ? `${percentual(a.taxa_aa)} a.a.` : "";
  if (a.indexador === "PRE") return `Prefixado ${taxa}`;
  const pct = a.indexador_pct !== null && a.indexador_pct !== 1 ? `${percentual(a.indexador_pct)} do ` : "";
  return `${pct}${NOME_INDICE[a.indexador] ?? a.indexador}${taxa ? ` + ${taxa}` : ""}`;
}

function CotaAtual({ ativo }: { ativo: Ativo }) {
  const { data } = useQuery({
    queryKey: ["cota", ativo.id, hoje()],
    queryFn: () => api.get<Cota>(`/ativos/${ativo.id}/cota${query({ data: hoje() })}`),
  });
  return <>{data ? numero(data.cota, 6) : "—"}</>;
}

function SaldoManual({ ativo, aoSalvar }: { ativo: Ativo; aoSalvar: () => void }) {
  const [dia, setDia] = useState(hoje());
  const [saldo, setSaldo] = useState("");
  const enviar = useMutation({
    mutationFn: () => api.post<Cota>(`/ativos/${ativo.id}/saldo`, { data: dia, saldo: Number(saldo) }),
    onSuccess: () => {
      setSaldo("");
      aoSalvar();
    },
  });
  return (
    <form
      className="linha-form"
      onSubmit={(e) => {
        e.preventDefault();
        enviar.mutate();
      }}
    >
      <CampoData required valor={dia} aoMudar={setDia} />
      <input
        type="number"
        step="any"
        min="0.01"
        required
        placeholder={`Saldo total (${ativo.moeda})`}
        value={saldo}
        onChange={(e) => setSaldo(e.target.value)}
      />
      <button type="submit" className="secundario" disabled={enviar.isPending}>
        Atualizar saldo
      </button>
      {enviar.error && <span className="negativo">{(enviar.error as Error).message}</span>}
    </form>
  );
}

export function AtivosPersonalizados() {
  const { data: dominio } = useDominio();
  const indexadores = dominio?.indexadores ?? {};
  const { data: ativos = [] } = useQuery({
    queryKey: ["ativos", "personalizados"],
    queryFn: () => api.get<Ativo[]>(`/ativos${query({ personalizados: true })}`),
  });
  const { data: classes = [] } = useQuery({ queryKey: ["classes"], queryFn: () => api.get<string[]>("/classes") });
  const cliente = useQueryClient();
  const [form, setForm] = useState<FormAtivo>(VAZIO);

  const recarregar = () => {
    cliente.invalidateQueries({ queryKey: ["ativos"] });
    cliente.invalidateQueries({ queryKey: ["cota"] });
    invalidarDerivados(cliente);
  };
  const salvar = useMutation({
    mutationFn: (f: FormAtivo) => {
      const corpo = {
        ticker: f.ticker,
        nome: f.nome || null,
        classe: f.classe,
        setor: f.original?.setor ?? null,
        subsetor: f.original?.subsetor ?? null,
        moeda: f.moeda,
        mercado: null,
        cotacao_automatica: false,
        indexador: f.automatico ? f.indexador : null,
        indexador_pct: f.automatico && f.indexador !== "PRE" ? paraFracao(f.indexador_pct) : null,
        taxa_aa: f.automatico && f.taxa_aa !== "" ? paraFracao(f.taxa_aa) : null,
        data_base: f.automatico ? f.data_base : null,
      };
      return f.id ? api.put(`/ativos/${f.id}`, corpo) : api.post("/ativos", corpo);
    },
    onSuccess: () => {
      setForm(VAZIO);
      recarregar();
    },
  });

  const editar = (a: Ativo) =>
    setForm({
      id: a.id,
      ticker: a.ticker,
      nome: a.nome ?? "",
      classe: a.classe,
      moeda: a.moeda,
      automatico: a.indexador !== null,
      indexador: a.indexador ?? "CDI",
      indexador_pct: a.indexador_pct === null ? "100" : paraPercentual(a.indexador_pct),
      taxa_aa: paraPercentual(a.taxa_aa),
      data_base: a.data_base ?? hoje(),
      original: a,
    });

  const enviar = (e: FormEvent) => {
    e.preventDefault();
    salvar.mutate(form);
  };

  return (
    <>
      <h2>Ativos personalizados</h2>
      <p className="sutil">
        Ativos sem cotação de mercado (CDB, Tesouro, poupança, previdência…). Funcionam como cotas: lance cada aplicação como compra de{" "}
        <em>valor aplicado ÷ cota da data</em> ao preço da cota (o formulário de operação preenche a cota automaticamente).
      </p>
      <ul className="sutil">
        <li>
          <strong>Rendimento automático</strong>: cota = 1 na data-base, corrigida pelo índice mensal (CDI, SELIC, IPCA, IGP-M do BCB) ×
          % do índice + taxa a.a. Mês ainda sem índice repete o último conhecido (estimativa).
        </li>
        <li>
          <strong>Saldo manual</strong>: informe o saldo total do ativo na data; a cota passa a ser saldo ÷ quantidade.
        </li>
      </ul>
      {salvar.error && <div className="erro">{(salvar.error as Error).message}</div>}

      {ativos.length > 0 && (
        <div className="tabela-container">
          <table className="tabela">
            <thead>
              <tr>
                <th>Ativo</th>
                <th>Classe</th>
                <th>Rendimento</th>
                <th>Data-base</th>
                <th className="num">Cota hoje</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {ativos.map((a) => (
                <tr key={a.id}>
                  <td>
                    <strong>{a.ticker}</strong>
                    <div className="sutil">{a.nome}</div>
                  </td>
                  <td>{a.classe}</td>
                  <td>
                    {descricao(a)}
                    {!a.indexador && <SaldoManual ativo={a} aoSalvar={recarregar} />}
                  </td>
                  <td>{fmtData(a.data_base)}</td>
                  <td className="num">
                    <CotaAtual ativo={a} />
                  </td>
                  <td className="num">
                    <button className="link" onClick={() => editar(a)}>
                      Editar
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <form className="formulario" onSubmit={enviar}>
        <h3>{form.id ? `Editar ${form.ticker}` : "Novo ativo personalizado"}</h3>
        <label>
          Código
          <input required maxLength={20} value={form.ticker} onChange={(e) => setForm({ ...form, ticker: e.target.value.toUpperCase() })} />
        </label>
        <label>
          Nome
          <input maxLength={120} value={form.nome} onChange={(e) => setForm({ ...form, nome: e.target.value })} />
        </label>
        <label>
          Classe
          <input required list="classes-personalizados" value={form.classe} onChange={(e) => setForm({ ...form, classe: e.target.value.toUpperCase() })} />
          <datalist id="classes-personalizados">
            {classes.map((c) => (
              <option key={c} value={c} />
            ))}
          </datalist>
        </label>
        <label>
          Moeda
          <select value={form.moeda} onChange={(e) => setForm({ ...form, moeda: e.target.value })}>
            {(dominio?.moedas ?? ["BRL"]).map((m) => (
              <option key={m}>{m}</option>
            ))}
          </select>
        </label>
        <label>
          Tipo
          <select value={form.automatico ? "auto" : "manual"} onChange={(e) => setForm({ ...form, automatico: e.target.value === "auto" })}>
            <option value="auto">Rendimento automático</option>
            <option value="manual">Saldo manual</option>
          </select>
        </label>
        {form.automatico && (
          <>
            <label>
              Indexador
              <select value={form.indexador} onChange={(e) => setForm({ ...form, indexador: e.target.value })}>
                {Object.entries(indexadores).map(([codigo, rotulo]) => (
                  <option key={codigo} value={codigo}>
                    {rotulo}
                  </option>
                ))}
              </select>
            </label>
            {form.indexador !== "PRE" && (
              <label>
                % do índice
                <input required type="number" step="any" min="0.01" value={form.indexador_pct} onChange={(e) => setForm({ ...form, indexador_pct: e.target.value })} />
              </label>
            )}
            <label>
              Taxa a.a. (%) {form.indexador !== "PRE" && <small className="sutil">adicional</small>}
              <input
                type="number"
                step="any"
                required={form.indexador === "PRE"}
                value={form.taxa_aa}
                onChange={(e) => setForm({ ...form, taxa_aa: e.target.value })}
              />
            </label>
            <label>
              Data-base (cota = 1)
              <CampoData required valor={form.data_base} aoMudar={(v) => setForm({ ...form, data_base: v })} />
            </label>
          </>
        )}
        <div className="acoes largura-total">
          <button type="submit" disabled={salvar.isPending}>
            Salvar
          </button>
          {form.id && (
            <button type="button" className="secundario" onClick={() => setForm(VAZIO)}>
              Cancelar
            </button>
          )}
        </div>
      </form>
    </>
  );
}
