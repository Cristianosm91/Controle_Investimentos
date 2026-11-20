import { useEffect, useMemo, useRef, useState } from "react";

export interface OpcaoFiltro {
  valor: string;
  rotulo: string;
  busca?: string;
}

interface Props {
  rotulo: string;
  resumoTodos?: string;
  resumoNenhum?: string;
  resumoMultiplos?: (quantidade: number) => string;
  opcoes: OpcaoFiltro[];
  selecionados: string[] | null;
  aoMudar: (valores: string[] | null) => void;
  pesquisar?: boolean;
}

export function FiltroMultisselecao({
  rotulo,
  resumoTodos = `Todos ${rotulo.toLocaleLowerCase()}`,
  resumoNenhum = `Nenhum ${rotulo.toLocaleLowerCase()}`,
  resumoMultiplos = (quantidade) => `${quantidade} ${rotulo.toLocaleLowerCase()} selecionados`,
  opcoes,
  selecionados,
  aoMudar,
  pesquisar,
}: Props) {
  const detalhes = useRef<HTMLDetailsElement>(null);
  const [termo, setTermo] = useState("");
  const exibirBusca = pesquisar ?? opcoes.length > 8;
  const visiveis = useMemo(() => {
    const busca = termo.trim().toLocaleLowerCase();
    return busca
      ? opcoes.filter((opcao) => `${opcao.rotulo} ${opcao.busca ?? ""}`.toLocaleLowerCase().includes(busca))
      : opcoes;
  }, [opcoes, termo]);
  const todosSelecionados = selecionados === null;
  const selecionadosValidos = selecionados?.filter((valor) => opcoes.some((opcao) => opcao.valor === valor)) ?? [];
  const resumo = todosSelecionados
    ? resumoTodos
    : selecionadosValidos.length === 0
      ? resumoNenhum
      : selecionadosValidos.length === 1
        ? opcoes.find((opcao) => opcao.valor === selecionadosValidos[0])?.rotulo ?? rotulo
        : selecionadosValidos.length === 2
          ? selecionadosValidos
              .map((valor) => opcoes.find((opcao) => opcao.valor === valor)?.rotulo ?? valor)
              .join(" + ")
          : resumoMultiplos(selecionadosValidos.length);

  useEffect(() => {
    const fecharFora = (evento: PointerEvent) => {
      if (!detalhes.current?.contains(evento.target as Node)) {
        if (detalhes.current) detalhes.current.open = false;
      }
    };
    const fecharEscape = (evento: KeyboardEvent) => {
      if (evento.key === "Escape" && detalhes.current?.open) {
        detalhes.current.open = false;
        detalhes.current.querySelector("summary")?.focus();
      }
    };
    document.addEventListener("pointerdown", fecharFora);
    document.addEventListener("keydown", fecharEscape);
    return () => {
      document.removeEventListener("pointerdown", fecharFora);
      document.removeEventListener("keydown", fecharEscape);
    };
  }, []);

  useEffect(() => {
    if (selecionados !== null) {
      const validos = selecionados.filter((valor) => opcoes.some((opcao) => opcao.valor === valor));
      if (validos.length !== selecionados.length) aoMudar(validos);
    }
  }, [aoMudar, opcoes, selecionados]);

  const alternar = (valor: string, marcado: boolean) => {
    const base = selecionados === null ? opcoes.map((opcao) => opcao.valor) : selecionados;
    aoMudar(marcado ? [...new Set([...base, valor])] : base.filter((item) => item !== valor));
  };

  return (
    <div className="campo-filtro">
      <span>{rotulo}</span>
      <details className="filtro-multi" ref={detalhes}>
        <summary aria-label={`${rotulo}: ${resumo}`}>{resumo}</summary>
        <div className="filtro-multi-opcoes" role="group" aria-label={rotulo}>
          <div className="filtro-multi-acoes">
            <button type="button" className="link" onClick={() => aoMudar(null)}>
              Todos
            </button>
            <button type="button" className="link" onClick={() => aoMudar([])}>
              Limpar seleção
            </button>
          </div>
          {exibirBusca && (
            <input
              type="search"
              aria-label={`Pesquisar ${rotulo.toLocaleLowerCase()}`}
              placeholder="Pesquisar…"
              value={termo}
              onChange={(evento) => setTermo(evento.target.value)}
            />
          )}
          <div className="filtro-multi-lista">
            {visiveis.map((opcao) => (
              <label className="check" key={opcao.valor}>
                <input
                  type="checkbox"
                  checked={todosSelecionados || selecionadosValidos.includes(opcao.valor)}
                  onChange={(evento) => alternar(opcao.valor, evento.target.checked)}
                />
                {opcao.rotulo}
              </label>
            ))}
            {visiveis.length === 0 && <span className="sutil">Nenhuma opção encontrada.</span>}
          </div>
        </div>
      </details>
    </div>
  );
}
