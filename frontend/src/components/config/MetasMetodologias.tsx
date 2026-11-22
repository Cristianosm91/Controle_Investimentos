import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { api } from "../../api";
import { invalidarDerivados, paraPercentual } from "../../cadastros";
import { percentual } from "../../formato";
import { useInvestidor } from "../../InvestidorContext";
import { LETRAS_METODOLOGIAS } from "../../metodologias";
import type { MetasMetodologia } from "../../tipos";

function unidadesPercentuais(texto: string): number | null {
  const normalizado = texto.trim().replace(",", ".");
  if (!/^\d{1,3}(\.\d{1,6})?$/.test(normalizado)) return null;
  const valor = Number(normalizado);
  return valor <= 100 ? Math.round(valor * 1_000_000) : null;
}

function FormularioMetodologia({ investidorId, metodologia }: { investidorId: number; metodologia: MetasMetodologia }) {
  const cliente = useQueryClient();
  const [valores, setValores] = useState(() =>
    Object.fromEntries(metodologia.categorias.map((categoria) => [categoria.nome, paraPercentual(categoria.peso_alvo)])),
  );
  const salvar = useMutation({
    mutationFn: (categorias: { nome: string; peso_alvo: string }[]) =>
      api.put<MetasMetodologia>(`/investidores/${investidorId}/metas-metodologias/${metodologia.nome}`, { categorias }),
    onSuccess: () => {
      cliente.invalidateQueries({ queryKey: ["metas-metodologias", String(investidorId)] });
      invalidarDerivados(cliente);
    },
  });
  const unidades = metodologia.categorias.map((categoria) => unidadesPercentuais(valores[categoria.nome] ?? ""));
  const completo = unidades.every((valor) => valor !== null);
  const soma = unidades.reduce<number>((total, valor) => total + (valor ?? 0), 0);
  const valido = completo && soma === 100_000_000;

  const enviar = (evento: FormEvent) => {
    evento.preventDefault();
    if (!valido) return;
    const categorias: { nome: string; peso_alvo: string }[] = [];
    for (const [indice, categoria] of metodologia.categorias.entries()) {
      const valor = unidades[indice];
      if (valor === null || valor === undefined) return;
      categorias.push({ nome: categoria.nome, peso_alvo: (valor / 100_000_000).toFixed(8) });
    }
    salvar.mutate(categorias);
  };

  return (
    <form className="formulario" onSubmit={enviar}>
      <h3>{metodologia.nome}</h3>
      {metodologia.categorias.map((categoria, indice) => (
        <label key={categoria.nome}>
          {LETRAS_METODOLOGIAS[metodologia.nome]?.[categoria.nome]} — {categoria.nome} (%)
          <input
            type="text"
            inputMode="decimal"
            required
            value={valores[categoria.nome] ?? ""}
            aria-invalid={valores[categoria.nome] !== "" && unidades[indice] === null}
            onChange={(evento) => {
              salvar.reset();
              setValores({ ...valores, [categoria.nome]: evento.target.value });
            }}
          />
        </label>
      ))}
      <p className="largura-total sutil">
        Total: {percentual(soma / 100_000_000)}. Preencha todas as categorias com valores entre 0 e 100; a soma deve ser 100%.
      </p>
      {salvar.error && <div className="erro largura-total" role="alert">{salvar.error.message}</div>}
      {salvar.isSuccess && <p className="largura-total" role="status">Metas de {metodologia.nome} salvas.</p>}
      <div className="acoes largura-total">
        <button type="submit" disabled={!valido || salvar.isPending}>
          {salvar.isPending ? "Salvando…" : `Salvar ${metodologia.nome}`}
        </button>
      </div>
    </form>
  );
}

export function MetasMetodologiasConfig() {
  const { investidores, selecionados } = useInvestidor();
  const [investidor, setInvestidor] = useState(selecionados.length === 1 ? String(selecionados[0]) : "");
  const consulta = useQuery({
    queryKey: ["metas-metodologias", investidor],
    queryFn: () => api.get<MetasMetodologia[]>(`/investidores/${investidor}/metas-metodologias`),
    enabled: investidor !== "",
    retry: false,
  });

  return (
    <>
      <h2>Metas ARCA e KRAKEN</h2>
      <p className="sutil">
        Defina os percentuais para cada investidor. Cada metodologia deve somar 100%; as metas não alteram o simulador de aportes.
      </p>
      <label>
        Investidor
        <select value={investidor} onChange={(evento) => setInvestidor(evento.target.value)}>
          <option value="">Selecione um investidor</option>
          {investidores.map((item) => <option key={item.id} value={item.id}>{item.nome}</option>)}
        </select>
      </label>
      {consulta.isLoading && <p role="status">Carregando metas…</p>}
      {consulta.error && <div className="erro" role="alert">Não foi possível carregar as metas: {consulta.error.message}</div>}
      {consulta.data?.map((metodologia) => (
        <FormularioMetodologia key={`${investidor}-${metodologia.nome}`} investidorId={Number(investidor)} metodologia={metodologia} />
      ))}
    </>
  );
}
