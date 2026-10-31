import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState, type FormEvent } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "../api";
import { AtivosPersonalizados } from "../components/config/AtivosPersonalizados";
import { BackupConfig } from "../components/config/Backup";
import { Carteiras } from "../components/config/Carteiras";
import { EstrategiasBooks } from "../components/config/EstrategiasBooks";
import { Importacoes } from "../components/config/Importacoes";
import { ImpostoRendaConfig } from "../components/config/ImpostoRenda";
import { Parametros } from "../components/config/Parametros";
import { QualidadeDados } from "../components/config/QualidadeDados";
import { PainelAtualizacoes } from "../components/PainelAtualizacoes";
import { useInvestidor } from "../InvestidorContext";
import type { Investidor } from "../tipos";

const SECOES = [
  { id: "investidores", rotulo: "Investidores" },
  { id: "estrategias", rotulo: "Estratégias & Books" },
  { id: "carteiras", rotulo: "Carteiras" },
  { id: "ativos", rotulo: "Ativos personalizados" },
  { id: "parametros", rotulo: "Parâmetros" },
  { id: "ir", rotulo: "Imposto de renda" },
  { id: "qualidade", rotulo: "Qualidade dos dados" },
  { id: "importacoes", rotulo: "Importações" },
  { id: "atualizacoes", rotulo: "Atualizações" },
  { id: "backup", rotulo: "Backup" },
] as const;

type SecaoId = (typeof SECOES)[number]["id"];

interface FormInvestidor {
  id?: number;
  nome: string;
  cpf: string;
  grupo_id: string;
  cor: string;
  ativo: boolean;
}

const VAZIO: FormInvestidor = { nome: "", cpf: "", grupo_id: "", cor: "#2563eb", ativo: true };

function Investidores() {
  const { investidores, grupos } = useInvestidor();
  const cliente = useQueryClient();
  const [form, setForm] = useState<FormInvestidor>(VAZIO);
  const [novoGrupo, setNovoGrupo] = useState("");
  const recarregar = () => {
    cliente.invalidateQueries({ queryKey: ["investidores"] });
    cliente.invalidateQueries({ queryKey: ["grupos"] });
  };

  const salvar = useMutation({
    mutationFn: (f: FormInvestidor) => {
      const corpo = { nome: f.nome, cpf: f.cpf || null, grupo_id: f.grupo_id ? Number(f.grupo_id) : null, cor: f.cor, ativo: f.ativo };
      return f.id ? api.put(`/investidores/${f.id}`, corpo) : api.post("/investidores", corpo);
    },
    onSuccess: () => {
      setForm(VAZIO);
      recarregar();
    },
  });
  const excluir = useMutation({ mutationFn: (id: number) => api.del(`/investidores/${id}`), onSuccess: recarregar });
  const criarGrupo = useMutation({
    mutationFn: (nome: string) => api.post("/grupos", { nome }),
    onSuccess: () => {
      setNovoGrupo("");
      recarregar();
    },
  });
  const excluirGrupo = useMutation({ mutationFn: (id: number) => api.del(`/grupos/${id}`), onSuccess: recarregar });

  const editar = (i: Investidor) =>
    setForm({ id: i.id, nome: i.nome, cpf: "", grupo_id: i.grupo_id ? String(i.grupo_id) : "", cor: i.cor, ativo: i.ativo });

  const enviar = (e: FormEvent) => {
    e.preventDefault();
    salvar.mutate(form);
  };

  const erro = salvar.error ?? excluir.error ?? criarGrupo.error ?? excluirGrupo.error;

  return (
    <>
      <h2>Investidores</h2>
      <p className="sutil">
        Cada investidor tem posições, preço médio e IR próprios (por CPF). O seletor no topo filtra todas as páginas.
      </p>
      {erro && <div className="erro">{(erro as Error).message}</div>}

      <table className="tabela compacta">
        <thead>
          <tr>
            <th>Nome</th>
            <th>CPF</th>
            <th>Grupo</th>
            <th>Situação</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {investidores.map((i) => (
            <tr key={i.id}>
              <td>
                <span className="bolinha" style={{ background: i.cor }} /> {i.nome}
              </td>
              <td>{i.cpf_mascarado ?? "—"}</td>
              <td>{grupos.find((g) => g.id === i.grupo_id)?.nome ?? "—"}</td>
              <td>{i.ativo ? "Ativo" : "Inativo"}</td>
              <td className="num">
                <button className="link" onClick={() => editar(i)}>
                  Editar
                </button>
                <button
                  className="link perigo"
                  onClick={() => confirm(`Excluir ${i.nome}?`) && excluir.mutate(i.id)}
                >
                  Excluir
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <form className="formulario" onSubmit={enviar}>
        <h3>{form.id ? "Editar investidor" : "Novo investidor"}</h3>
        <label>
          Nome
          <input required maxLength={80} value={form.nome} onChange={(e) => setForm({ ...form, nome: e.target.value })} />
        </label>
        <label>
          CPF {form.id && <small className="sutil">(em branco = manter)</small>}
          <input inputMode="numeric" maxLength={14} value={form.cpf} onChange={(e) => setForm({ ...form, cpf: e.target.value })} />
        </label>
        <label>
          Grupo
          <select value={form.grupo_id} onChange={(e) => setForm({ ...form, grupo_id: e.target.value })}>
            <option value="">—</option>
            {grupos.map((g) => (
              <option key={g.id} value={g.id}>
                {g.nome}
              </option>
            ))}
          </select>
        </label>
        <label>
          Cor
          <input type="color" value={form.cor} onChange={(e) => setForm({ ...form, cor: e.target.value })} />
        </label>
        <label className="check">
          <input type="checkbox" checked={form.ativo} onChange={(e) => setForm({ ...form, ativo: e.target.checked })} />
          Ativo
        </label>
        <div className="acoes">
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

      <h2>Grupos</h2>
      <p className="sutil">Agrupam investidores (ex.: Família) para seleção rápida no topo.</p>
      <div className="etiquetas">
        {grupos.map((g) => (
          <span key={g.id} className="etiqueta">
            {g.nome}
            <button className="link perigo" onClick={() => excluirGrupo.mutate(g.id)} aria-label={`Excluir ${g.nome}`}>
              ×
            </button>
          </span>
        ))}
      </div>
      <form
        className="linha-form"
        onSubmit={(e) => {
          e.preventDefault();
          if (novoGrupo.trim()) criarGrupo.mutate(novoGrupo.trim());
        }}
      >
        <input placeholder="Novo grupo" maxLength={60} value={novoGrupo} onChange={(e) => setNovoGrupo(e.target.value)} />
        <button type="submit">Adicionar</button>
      </form>
    </>
  );
}

export function Configuracoes() {
  const [params] = useSearchParams();
  const inicial = SECOES.find((s) => s.id === params.get("secao"))?.id ?? "investidores";
  const [secao, setSecao] = useState<SecaoId>(inicial);
  useEffect(() => setSecao(inicial), [inicial]);
  const conteudo: Record<SecaoId, JSX.Element> = {
    investidores: <Investidores />,
    estrategias: <EstrategiasBooks />,
    carteiras: <Carteiras />,
    ativos: <AtivosPersonalizados />,
    parametros: <Parametros />,
    ir: <ImpostoRendaConfig />,
    qualidade: <QualidadeDados />,
    importacoes: <Importacoes />,
    atualizacoes: <PainelAtualizacoes />,
    backup: <BackupConfig />,
  };

  return (
    <section>
      <h1>Configurações</h1>
      <div className="abas">
        {SECOES.map((s) => (
          <button key={s.id} className={s.id === secao ? "aba ativa" : "aba"} onClick={() => setSecao(s.id)}>
            {s.rotulo}
          </button>
        ))}
      </div>
      {conteudo[secao]}
    </section>
  );
}
