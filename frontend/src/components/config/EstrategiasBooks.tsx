import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { api } from "../../api";
import { invalidarDerivados, paraFracao, paraPercentual, useAtivos, useBooks, useEstrategias } from "../../cadastros";
import { percentual } from "../../formato";
import type { Ativo, Book, ExcecaoBook } from "../../tipos";
import { CampoAtivo } from "../Campos";
import { useExclusaoEmLote } from "../ExclusaoEmLote";

function useRecarregar() {
  const cliente = useQueryClient();
  return () => {
    for (const chave of ["estrategias", "books", "books-excecoes", "classes"]) cliente.invalidateQueries({ queryKey: [chave] });
    invalidarDerivados(cliente);
  };
}

const somaOk = (soma: number) => Math.abs(soma - 1) < 1e-6;

// ---------- Estratégias ----------

interface FormEstr {
  id?: number;
  nome: string;
  peso: string;
  ordem: string;
}

const ESTR_VAZIA: FormEstr = { nome: "", peso: "", ordem: "0" };

function Estrategias() {
  const { data: estrategias = [] } = useEstrategias();
  const recarregar = useRecarregar();
  const [form, setForm] = useState<FormEstr>(ESTR_VAZIA);
  const salvar = useMutation({
    mutationFn: (f: FormEstr) => {
      const corpo = { nome: f.nome, peso: paraFracao(f.peso), ordem: Number(f.ordem || 0) };
      return f.id ? api.put(`/estrategias/${f.id}`, corpo) : api.post("/estrategias", corpo);
    },
    onSuccess: () => {
      setForm(ESTR_VAZIA);
      recarregar();
    },
  });
  const excluir = useMutation({ mutationFn: (id: number) => api.del(`/estrategias/${id}`), onSuccess: recarregar });
  const selecao = useExclusaoEmLote({
    itens: estrategias,
    chave: (e) => e.id,
    remover: (id) => api.del(`/estrategias/${id}`),
    titulo: "estratégias",
    consulta: "estrategias",
    aposExcluir: recarregar,
  });
  const soma = estrategias.reduce((s, e) => s + e.peso, 0);
  const erro = salvar.error ?? excluir.error;

  const enviar = (e: FormEvent) => {
    e.preventDefault();
    salvar.mutate(form);
  };

  return (
    <>
      <h2>Estratégias</h2>
      <p className="sutil">Divisão de primeiro nível do portfólio (ex.: renda variável × renda fixa). Os pesos devem somar 100%.</p>
      {erro && <div className="erro">{(erro as Error).message}</div>}
      {selecao.acoes}
      <table className="tabela compacta">
        <thead>
          <tr>
            <th />
            <th>Estratégia</th>
            <th className="num">Peso no portfólio</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {estrategias.map((e) => (
            <tr key={e.id}>
              <td>{selecao.checkbox(e.id)}</td>
              <td>{e.nome}</td>
              <td className="num">{percentual(e.peso)}</td>
              <td className="num">
                <button className="link" onClick={() => setForm({ id: e.id, nome: e.nome, peso: paraPercentual(e.peso), ordem: String(e.ordem) })}>
                  Editar
                </button>
                <button className="link perigo" onClick={() => confirm(`Excluir ${e.nome}?`) && excluir.mutate(e.id)}>
                  Excluir
                </button>
              </td>
            </tr>
          ))}
          <tr className="linha-grupo">
            <td />
            <td>Total</td>
            <td className={`num ${somaOk(soma) ? "" : "negativo"}`}>{percentual(soma)}</td>
            <td />
          </tr>
        </tbody>
      </table>
      <form className="formulario" onSubmit={enviar}>
        <h3>{form.id ? "Editar estratégia" : "Nova estratégia"}</h3>
        <label>
          Nome
          <input required maxLength={60} value={form.nome} onChange={(e) => setForm({ ...form, nome: e.target.value })} />
        </label>
        <label>
          Peso no portfólio (%)
          <input required type="number" step="any" min="0" max="100" value={form.peso} onChange={(e) => setForm({ ...form, peso: e.target.value })} />
        </label>
        <label>
          Ordem
          <input type="number" value={form.ordem} onChange={(e) => setForm({ ...form, ordem: e.target.value })} />
        </label>
        <div className="acoes">
          <button type="submit" disabled={salvar.isPending}>
            Salvar
          </button>
          {form.id && (
            <button type="button" className="secundario" onClick={() => setForm(ESTR_VAZIA)}>
              Cancelar
            </button>
          )}
        </div>
      </form>
    </>
  );
}

// ---------- Books ----------

interface FormBook {
  id?: number;
  estrategia_id: string;
  nome: string;
  peso: string;
  ordem: string;
  classes: string[];
}

const BOOK_VAZIO: FormBook = { estrategia_id: "", nome: "", peso: "", ordem: "0", classes: [] };

function SeletorClasses({ valor, aoMudar }: { valor: string[]; aoMudar: (v: string[]) => void }) {
  const { data: classes = [] } = useQuery({ queryKey: ["classes"], queryFn: () => api.get<string[]>("/classes") });
  const [nova, setNova] = useState("");
  const adicionar = () => {
    const c = nova.trim().toUpperCase();
    if (c && !valor.includes(c)) aoMudar([...valor, c].sort());
    setNova("");
  };
  return (
    <div className="largura-total">
      <small className="sutil">Classes cujo book padrão é este (cada classe fica em um único book)</small>
      <div className="etiquetas">
        {valor.map((c) => (
          <span key={c} className="etiqueta">
            {c}
            <button type="button" className="link perigo" onClick={() => aoMudar(valor.filter((x) => x !== c))} aria-label={`Remover ${c}`}>
              ×
            </button>
          </span>
        ))}
      </div>
      <div className="linha-form">
        <input
          list="lista-classes"
          placeholder="Adicionar classe"
          value={nova}
          onChange={(e) => setNova(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              adicionar();
            }
          }}
        />
        <datalist id="lista-classes">
          {classes.map((c) => (
            <option key={c} value={c} />
          ))}
        </datalist>
        <button type="button" className="secundario" onClick={adicionar}>
          Adicionar
        </button>
      </div>
    </div>
  );
}

function Books() {
  const { data: estrategias = [] } = useEstrategias();
  const { data: books = [] } = useBooks();
  const { data: ativos = [] } = useAtivos();
  const recarregar = useRecarregar();
  const [form, setForm] = useState<FormBook>(BOOK_VAZIO);
  const salvar = useMutation({
    mutationFn: (f: FormBook) => {
      const corpo = {
        estrategia_id: Number(f.estrategia_id),
        nome: f.nome,
        peso: paraFracao(f.peso),
        ordem: Number(f.ordem || 0),
        classes: f.classes,
      };
      return f.id ? api.put(`/books/${f.id}`, corpo) : api.post("/books", corpo);
    },
    onSuccess: () => {
      setForm(BOOK_VAZIO);
      recarregar();
    },
  });
  const excluir = useMutation({ mutationFn: (id: number) => api.del(`/books/${id}`), onSuccess: recarregar });
  const selecao = useExclusaoEmLote({
    itens: books,
    chave: (b) => b.id,
    remover: (id) => api.del(`/books/${id}`),
    titulo: "books",
    consulta: "books",
    aposExcluir: recarregar,
  });
  const erro = salvar.error ?? excluir.error;

  const mapeadas = new Set(books.flatMap((b) => b.classes));
  const semBook = [...new Set(ativos.map((a) => a.classe))].filter((c) => !mapeadas.has(c)).sort();
  const editar = (b: Book) =>
    setForm({
      id: b.id,
      estrategia_id: String(b.estrategia_id),
      nome: b.nome,
      peso: paraPercentual(b.peso),
      ordem: String(b.ordem),
      classes: b.classes,
    });

  const enviar = (e: FormEvent) => {
    e.preventDefault();
    salvar.mutate(form);
  };

  return (
    <>
      <h2>Books</h2>
      <p className="sutil">
        Peso do book dentro da estratégia; o peso no portfólio é estratégia × book. Cada classe de ativo aponta para um book padrão.
      </p>
      {semBook.length > 0 && <div className="aviso">Classes em uso sem book (ficam fora da alocação): {semBook.join(", ")}</div>}
      {erro && <div className="erro">{(erro as Error).message}</div>}
      {selecao.acoes}
      <div className="tabela-container">
        <table className="tabela">
          <thead>
            <tr>
              <th />
              <th>Book</th>
              <th className="num">Peso na estratégia</th>
              <th className="num">Peso no portfólio</th>
              <th>Classes</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {estrategias.flatMap((e) => {
              const doGrupo = books.filter((b) => b.estrategia_id === e.id);
              const soma = doGrupo.reduce((s, b) => s + b.peso, 0);
              return [
                <tr key={`e-${e.id}`} className="linha-grupo">
                  <td colSpan={6}>
                    <strong>{e.nome}</strong> · {percentual(e.peso)} do portfólio ·{" "}
                    <span className={somaOk(soma) ? "" : "negativo"}>books somam {percentual(soma)}</span>
                  </td>
                </tr>,
                ...doGrupo.map((b) => (
                  <tr key={b.id}>
                    <td>{selecao.checkbox(b.id)}</td>
                    <td>{b.nome}</td>
                    <td className="num">{percentual(b.peso)}</td>
                    <td className="num">{percentual(b.peso * e.peso)}</td>
                    <td className="quebra">
                      <span className="sutil">{b.classes.join(", ") || "—"}</span>
                    </td>
                    <td className="num">
                      <button className="link" onClick={() => editar(b)}>
                        Editar
                      </button>
                      <button className="link perigo" onClick={() => confirm(`Excluir o book ${b.nome}?`) && excluir.mutate(b.id)}>
                        Excluir
                      </button>
                    </td>
                  </tr>
                )),
              ];
            })}
          </tbody>
        </table>
      </div>
      <form className="formulario" onSubmit={enviar}>
        <h3>{form.id ? `Editar book ${form.nome}` : "Novo book"}</h3>
        <label>
          Estratégia
          <select required value={form.estrategia_id} onChange={(e) => setForm({ ...form, estrategia_id: e.target.value })}>
            <option value="">—</option>
            {estrategias.map((e) => (
              <option key={e.id} value={e.id}>
                {e.nome}
              </option>
            ))}
          </select>
        </label>
        <label>
          Nome
          <input required maxLength={60} value={form.nome} onChange={(e) => setForm({ ...form, nome: e.target.value })} />
        </label>
        <label>
          Peso na estratégia (%)
          <input required type="number" step="any" min="0" max="100" value={form.peso} onChange={(e) => setForm({ ...form, peso: e.target.value })} />
        </label>
        <label>
          Ordem
          <input type="number" value={form.ordem} onChange={(e) => setForm({ ...form, ordem: e.target.value })} />
        </label>
        <SeletorClasses valor={form.classes} aoMudar={(classes) => setForm({ ...form, classes })} />
        <div className="acoes">
          <button type="submit" disabled={salvar.isPending}>
            Salvar
          </button>
          {form.id && (
            <button type="button" className="secundario" onClick={() => setForm(BOOK_VAZIO)}>
              Cancelar
            </button>
          )}
        </div>
      </form>
    </>
  );
}

// ---------- Exceções por ativo ----------

interface LinhaExcecao {
  book_id: string;
  percentual: string;
}

function Excecoes() {
  const { data: books = [] } = useBooks();
  const { data: excecoes = [] } = useQuery({ queryKey: ["books-excecoes"], queryFn: () => api.get<ExcecaoBook[]>("/books/excecoes") });
  const recarregar = useRecarregar();
  const [ativo, setAtivo] = useState<Pick<Ativo, "id" | "ticker"> | undefined>();
  const [linhas, setLinhas] = useState<LinhaExcecao[]>([]);
  const nomeBook = (id: number) => books.find((b) => b.id === id)?.nome ?? id;

  const salvar = useMutation({
    mutationFn: ({ id, itens }: { id: number; itens: LinhaExcecao[] }) =>
      api.put(
        `/ativos/${id}/books`,
        itens.map((l) => ({ book_id: Number(l.book_id), percentual: paraFracao(l.percentual) })),
      ),
    onSuccess: () => {
      setAtivo(undefined);
      setLinhas([]);
      recarregar();
    },
  });

  const editar = (e: ExcecaoBook) => {
    setAtivo({ id: e.ativo_id, ticker: e.ticker });
    setLinhas(e.books.map(([b, p]) => ({ book_id: String(b), percentual: paraPercentual(p) })));
  };
  const mudarLinha = (i: number, parcial: Partial<LinhaExcecao>) =>
    setLinhas(linhas.map((x, j) => (j === i ? { ...x, ...parcial } : x)));
  const soma = linhas.reduce((s, l) => s + Number(l.percentual || 0), 0);

  return (
    <>
      <h2>Exceções por ativo</h2>
      <p className="sutil">Distribui um ativo entre books (ex.: um ETF 50% Ações e 50% Invest Exterior). Substitui o book da classe.</p>
      {salvar.error && <div className="erro">{(salvar.error as Error).message}</div>}
      {excecoes.length > 0 && (
        <table className="tabela compacta">
          <tbody>
            {excecoes.map((e) => (
              <tr key={e.ativo_id}>
                <td>
                  <strong>{e.ticker}</strong>
                </td>
                <td>{e.books.map(([b, p]) => `${nomeBook(b)} ${percentual(p)}`).join(" · ")}</td>
                <td className="num">
                  <button className="link" onClick={() => editar(e)}>
                    Editar
                  </button>
                  <button className="link perigo" onClick={() => salvar.mutate({ id: e.ativo_id, itens: [] })}>
                    Remover
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <form
        className="formulario"
        onSubmit={(e) => {
          e.preventDefault();
          if (ativo) salvar.mutate({ id: ativo.id, itens: linhas });
        }}
      >
        <h3>{ativo ? `Exceção de ${ativo.ticker}` : "Nova exceção"}</h3>
        <CampoAtivo ativoId={ativo ? String(ativo.id) : ""} aoMudar={(a) => setAtivo(a)} />
        {linhas.map((l, i) => (
          <div key={i} className="linha-form largura-total">
            <select required value={l.book_id} onChange={(e) => mudarLinha(i, { book_id: e.target.value })}>
              <option value="">Book…</option>
              {books.map((b) => (
                <option key={b.id} value={b.id}>
                  {b.nome}
                </option>
              ))}
            </select>
            <input
              required
              type="number"
              step="any"
              min="0"
              max="100"
              placeholder="%"
              value={l.percentual}
              onChange={(e) => mudarLinha(i, { percentual: e.target.value })}
            />
            <button type="button" className="link perigo" onClick={() => setLinhas(linhas.filter((_, j) => j !== i))}>
              ×
            </button>
          </div>
        ))}
        <div className="acoes largura-total">
          <button type="button" className="secundario" onClick={() => setLinhas([...linhas, { book_id: "", percentual: "" }])}>
            + Book
          </button>
          <button type="submit" disabled={!ativo || linhas.length === 0 || salvar.isPending}>
            Salvar
          </button>
          {linhas.length > 0 && <span className={`sutil ${Math.abs(soma - 100) < 1e-6 ? "" : "negativo"}`}>Soma: {soma}%</span>}
        </div>
      </form>
    </>
  );
}

export function EstrategiasBooks() {
  return (
    <>
      <Estrategias />
      <Books />
      <Excecoes />
    </>
  );
}
