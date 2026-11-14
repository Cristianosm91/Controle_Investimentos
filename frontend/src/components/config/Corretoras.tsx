import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { api } from "../../api";
import { invalidarDerivados, useCorretoras } from "../../cadastros";
import type { Corretora } from "../../tipos";

export function Corretoras() {
  const { data: corretoras, isLoading, error } = useCorretoras();
  const cliente = useQueryClient();
  const [editando, setEditando] = useState<Corretora | null>(null);
  const [nome, setNome] = useState("");
  const [cnpj, setCnpj] = useState("");
  const [destino, setDestino] = useState("");
  const [aviso, setAviso] = useState("");
  const apiDesatualizada = corretoras?.some((corretora) => !Array.isArray(corretora.apelidos)) ?? false;

  const recarregar = () => {
    for (const chave of ["corretoras", "operacoes", "proventos", "caixa"]) {
      cliente.invalidateQueries({ queryKey: [chave] });
    }
    invalidarDerivados(cliente);
  };
  const salvar = useMutation({
    mutationFn: (dados: { id: number; nome: string; cnpj: string | null }) =>
      api.put<Corretora>(`/corretoras/${dados.id}`, { nome: dados.nome, cnpj: dados.cnpj }),
    onSuccess: () => {
      setEditando(null);
      setAviso("Corretora atualizada.");
      recarregar();
    },
  });
  const unir = useMutation({
    mutationFn: (dados: { origem: number; destino: number }) =>
      api.post<Corretora>(`/corretoras/${dados.origem}/unir`, { destino_id: dados.destino }),
    onSuccess: (resultado) => {
      setEditando(null);
      setAviso(`Corretoras unidas em ${resultado.nome}.`);
      recarregar();
    },
  });
  const ocupada = salvar.isPending || unir.isPending;
  const iniciarEdicao = (corretora: Corretora) => {
    setEditando(corretora);
    setNome(corretora.nome);
    setCnpj(corretora.cnpj ?? "");
    setDestino("");
    setAviso("");
    salvar.reset();
    unir.reset();
  };
  const enviar = (evento: FormEvent) => {
    evento.preventDefault();
    if (editando) salvar.mutate({ id: editando.id, nome: nome.trim(), cnpj: cnpj || null });
  };
  const confirmarUniao = () => {
    const escolhida = corretoras?.find((c) => c.id === Number(destino));
    if (!editando || !escolhida) return;
    if (confirm(
      `Unir "${editando.nome}" em "${escolhida.nome}"? Todos os lançamentos passarão para a corretora de destino. ` +
      "O cadastro de origem será removido e seu nome preservado como apelido. Esta ação não pode ser desfeita automaticamente; faça um backup antes de continuar.",
    )) {
      unir.mutate({ origem: editando.id, destino: escolhida.id });
    }
  };

  return (
    <>
      <h2>Corretoras</h2>
      <p className="sutil">
        Edite os dados ou una cadastros da mesma instituição. As corretoras são compartilhadas por todos os investidores.
      </p>
      {error && <div className="erro">{(error as Error).message}</div>}
      {apiDesatualizada && <div className="erro">A API precisa ser atualizada. Faça backup e reinicie a aplicação para aplicar a migração.</div>}
      {(salvar.error || unir.error) && <div className="erro">{((salvar.error || unir.error) as Error).message}</div>}
      {aviso && <div className="aviso" role="status">{aviso}</div>}
      {isLoading && <p>Carregando corretoras…</p>}
      {corretoras && corretoras.length === 0 && <div className="aviso">Nenhuma corretora cadastrada.</div>}
      {corretoras?.map((corretora) => (
        <div className="painel" key={corretora.id}>
          <div className="titulo-linha">
            <h3>{corretora.nome}</h3>
            <button type="button" className="link" disabled={ocupada || apiDesatualizada} onClick={() => iniciarEdicao(corretora)}>
              Editar
            </button>
          </div>
          <p className="sutil">CNPJ: {corretora.cnpj ?? "Não informado"}</p>
          {(corretora.apelidos?.length ?? 0) > 0 && (
            <p className="sutil">Nomes anteriores: {corretora.apelidos?.map((apelido) => apelido.nome).join(", ")}</p>
          )}
        </div>
      ))}
      {editando && (
        <>
          <form className="formulario" onSubmit={enviar}>
            <h3>Editar {editando.nome}</h3>
            <label>
              Nome
              <input required maxLength={60} value={nome} onChange={(e) => setNome(e.target.value)} />
            </label>
            <label>
              CNPJ (14 dígitos, opcional)
              <input inputMode="numeric" pattern="[0-9]{14}" maxLength={14} value={cnpj} onChange={(e) => setCnpj(e.target.value)} />
            </label>
            <div className="acoes">
              <button type="submit" disabled={ocupada || !nome.trim()}>Salvar</button>
              <button type="button" className="secundario" disabled={ocupada} onClick={() => setEditando(null)}>Cancelar</button>
            </div>
          </form>
          <div className="formulario">
            <h3>Unir {editando.nome} a outra corretora</h3>
            <p className="sutil">O cadastro escolhido abaixo será mantido. A união é manual e afeta todos os investidores.</p>
            <label>
              Corretora de destino
              <select value={destino} onChange={(e) => setDestino(e.target.value)}>
                <option value="">Selecione</option>
                {corretoras?.filter((c) => c.id !== editando.id).map((c) => (
                  <option key={c.id} value={c.id}>{c.nome}</option>
                ))}
              </select>
            </label>
            <button type="button" disabled={ocupada || !destino} onClick={confirmarUniao}>Unir corretoras</button>
          </div>
        </>
      )}
    </>
  );
}
