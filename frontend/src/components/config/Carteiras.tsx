import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { api } from "../../api";
import { invalidarDerivados, paraFracao, paraPercentual, useAtivos, useDominio } from "../../cadastros";
import { moeda, percentual } from "../../formato";
import type { Carteira } from "../../tipos";

interface LinhaForm {
  ticker: string;
  peso: string;
  preco_teto: string;
  ranking: string;
  entra_preco_teto: boolean;
}

interface FormCarteira {
  id?: number;
  nome: string;
  categoria: string;
  ativa: boolean;
  ordem: string;
  ativos: LinhaForm[];
}

const VAZIA: FormCarteira = { nome: "", categoria: "", ativa: true, ordem: "0", ativos: [] };
const LINHA_VAZIA: LinhaForm = { ticker: "", peso: "", preco_teto: "", ranking: "", entra_preco_teto: true };

const opcional = (v: string) => (v === "" ? null : Number(v));

function paraForm(c: Carteira): FormCarteira {
  return {
    id: c.id,
    nome: c.nome,
    categoria: c.categoria ?? "",
    ativa: c.ativa,
    ordem: String(c.ordem),
    ativos: c.ativos.map((a) => ({
      ticker: a.ticker,
      peso: paraPercentual(a.peso),
      preco_teto: a.preco_teto === null ? "" : String(a.preco_teto),
      ranking: a.ranking === null ? "" : String(a.ranking),
      entra_preco_teto: a.entra_preco_teto,
    })),
  };
}

export function Carteiras() {
  const { data: carteiras = [] } = useQuery({ queryKey: ["carteiras"], queryFn: () => api.get<Carteira[]>("/carteiras") });
  const { data: ativos = [] } = useAtivos();
  const { data: dominio } = useDominio();
  const cliente = useQueryClient();
  const [form, setForm] = useState<FormCarteira>(VAZIA);
  const [aviso, setAviso] = useState("");

  const recarregar = () => {
    cliente.invalidateQueries({ queryKey: ["carteiras"] });
    invalidarDerivados(cliente);
  };
  const salvar = useMutation({
    mutationFn: (f: FormCarteira) => {
      const porTicker = new Map(ativos.map((a) => [a.ticker, a.id]));
      const desconhecidos = f.ativos.filter((l) => !porTicker.has(l.ticker.trim().toUpperCase())).map((l) => l.ticker);
      if (desconhecidos.length) throw new Error(`Ativo não cadastrado: ${desconhecidos.join(", ")}`);
      const corpo = {
        nome: f.nome,
        categoria: f.categoria || null,
        ativa: f.ativa,
        ordem: Number(f.ordem || 0),
        ativos: f.ativos.map((l) => ({
          ativo_id: porTicker.get(l.ticker.trim().toUpperCase()),
          peso: l.peso === "" ? null : paraFracao(l.peso),
          preco_teto: opcional(l.preco_teto),
          ranking: opcional(l.ranking),
          entra_preco_teto: l.entra_preco_teto,
        })),
      };
      return f.id ? api.put(`/carteiras/${f.id}`, corpo) : api.post("/carteiras", corpo);
    },
    onSuccess: () => {
      setAviso(`Carteira ${form.nome} salva.`);
      setForm(VAZIA);
      recarregar();
    },
  });
  const excluir = useMutation({ mutationFn: (id: number) => api.del(`/carteiras/${id}`), onSuccess: recarregar });
  const erro = salvar.error ?? excluir.error;

  const mudarLinha = (i: number, parcial: Partial<LinhaForm>) =>
    setForm({ ...form, ativos: form.ativos.map((l, j) => (j === i ? { ...l, ...parcial } : l)) });

  const enviar = (e: FormEvent) => {
    e.preventDefault();
    setAviso("");
    salvar.mutate(form);
  };

  return (
    <>
      <h2>Carteiras</h2>
      <p className="sutil">
        Agrupam ativos (cada ativo em no máximo uma carteira) e definem o peso-alvo do ativo dentro do seu book e o preço-teto usados na
        Alocação. Ativos sem peso dividem igualmente o restante do book. Carteira inativa é ignorada.
      </p>
      {erro && <div className="erro">{(erro as Error).message}</div>}
      {aviso && <div className="aviso">{aviso}</div>}
      {carteiras.length === 0 && <div className="aviso">Nenhuma carteira cadastrada.</div>}

      {carteiras.map((c) => (
        <div key={c.id} className="painel">
          <div className="titulo-linha">
            <h3>
              {c.nome} {c.categoria && <span className="etiqueta">{c.categoria}</span>}
              {!c.ativa && <span className="etiqueta">inativa</span>}
            </h3>
            <div className="acoes">
              <button className="link" onClick={() => setForm(paraForm(c))}>
                Editar
              </button>
              <button className="link perigo" onClick={() => confirm(`Excluir a carteira ${c.nome}?`) && excluir.mutate(c.id)}>
                Excluir
              </button>
            </div>
          </div>
          {c.ativos.length === 0 ? (
            <p className="sutil">Sem ativos.</p>
          ) : (
            <table className="tabela">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Ativo</th>
                  <th className="num">Peso no book</th>
                  <th className="num">Preço-teto</th>
                  <th>Usa preço-teto</th>
                </tr>
              </thead>
              <tbody>
                {c.ativos.map((a) => (
                  <tr key={a.ativo_id}>
                    <td>{a.ranking ?? "—"}</td>
                    <td>
                      <strong>{a.ticker}</strong>
                    </td>
                    <td className="num">{a.peso === null ? <span className="sutil">restante</span> : percentual(a.peso)}</td>
                    <td className="num">{moeda(a.preco_teto)}</td>
                    <td>{a.entra_preco_teto ? "Sim" : "Não"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      ))}

      <form className="formulario" onSubmit={enviar}>
        <h3>{form.id ? `Editar carteira ${form.nome}` : "Nova carteira"}</h3>
        <label>
          Nome
          <input required maxLength={60} value={form.nome} onChange={(e) => setForm({ ...form, nome: e.target.value })} />
        </label>
        <label>
          Categoria
          <input list="categorias-carteira" maxLength={30} value={form.categoria} onChange={(e) => setForm({ ...form, categoria: e.target.value })} />
          <datalist id="categorias-carteira">
            {(dominio?.categorias_carteira ?? []).map((c) => (
              <option key={c} value={c} />
            ))}
          </datalist>
        </label>
        <label>
          Ordem
          <input type="number" value={form.ordem} onChange={(e) => setForm({ ...form, ordem: e.target.value })} />
        </label>
        <label className="check">
          <input type="checkbox" checked={form.ativa} onChange={(e) => setForm({ ...form, ativa: e.target.checked })} />
          Ativa
        </label>

        {form.ativos.length > 0 && (
          <table className="tabela largura-total">
            <thead>
              <tr>
                <th>Ativo</th>
                <th>Peso no book (%)</th>
                <th>Preço-teto</th>
                <th>Ranking</th>
                <th>Usa teto</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {form.ativos.map((l, i) => (
                <tr key={i}>
                  <td>
                    <input required list="lista-ativos-carteira" value={l.ticker} onChange={(e) => mudarLinha(i, { ticker: e.target.value.toUpperCase() })} />
                  </td>
                  <td>
                    <input type="number" step="any" min="0" max="100" placeholder="restante" value={l.peso} onChange={(e) => mudarLinha(i, { peso: e.target.value })} />
                  </td>
                  <td>
                    <input type="number" step="any" min="0" value={l.preco_teto} onChange={(e) => mudarLinha(i, { preco_teto: e.target.value })} />
                  </td>
                  <td>
                    <input type="number" step="1" value={l.ranking} onChange={(e) => mudarLinha(i, { ranking: e.target.value })} />
                  </td>
                  <td>
                    <input type="checkbox" checked={l.entra_preco_teto} onChange={(e) => mudarLinha(i, { entra_preco_teto: e.target.checked })} />
                  </td>
                  <td>
                    <button type="button" className="link perigo" onClick={() => setForm({ ...form, ativos: form.ativos.filter((_, j) => j !== i) })}>
                      ×
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        <datalist id="lista-ativos-carteira">
          {ativos.map((a) => (
            <option key={a.id} value={a.ticker}>
              {a.nome ?? ""}
            </option>
          ))}
        </datalist>
        <div className="acoes largura-total">
          <button type="button" className="secundario" onClick={() => setForm({ ...form, ativos: [...form.ativos, LINHA_VAZIA] })}>
            + Ativo
          </button>
          <button type="submit" disabled={salvar.isPending}>
            Salvar
          </button>
          {form.id && (
            <button type="button" className="secundario" onClick={() => setForm(VAZIA)}>
              Cancelar
            </button>
          )}
        </div>
      </form>
    </>
  );
}
