import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
  type RefObject,
} from "react";
import { baixar, lerTabelas, nomeArquivo, type Aba, type Formato } from "../exportar";

/** Fonte extra de dados para a exportação (ex.: lista paginada devolve todos os registros, não só a página). */
type Fonte = () => Promise<Aba>;

interface ContextoExportacao {
  registrar: (fonte: Fonte) => () => void;
  fontes: () => Fonte[];
}

const Contexto = createContext<ContextoExportacao | null>(null);

export function ProvedorExportacao({ children }: { children: ReactNode }) {
  const fontes = useRef(new Set<Fonte>());
  const valor = useMemo<ContextoExportacao>(
    () => ({
      registrar: (fonte) => {
        fontes.current.add(fonte);
        return () => {
          fontes.current.delete(fonte);
        };
      },
      fontes: () => Array.from(fontes.current),
    }),
    [],
  );
  return <Contexto.Provider value={valor}>{children}</Contexto.Provider>;
}

export function useFonteExportacao(fonte: Fonte) {
  const contexto = useContext(Contexto);
  const atual = useRef(fonte);
  atual.current = fonte;
  useEffect(() => contexto?.registrar(() => atual.current()), [contexto]);
}

export function BotoesExportar({ alvo }: { alvo: RefObject<HTMLElement> }) {
  const contexto = useContext(Contexto);
  const [ocupado, setOcupado] = useState(false);

  const exportar = useCallback(
    async (formato: Formato) => {
      const container = alvo.current;
      if (!container) return;
      setOcupado(true);
      try {
        const extras = await Promise.all((contexto?.fontes() ?? []).map((f) => f()));
        const abas = [...lerTabelas(container), ...extras];
        if (!abas.length) {
          alert("Não há tabelas para exportar nesta página.");
          return;
        }
        const titulo = container.querySelector("h1")?.textContent ?? "investhub";
        await baixar(formato, nomeArquivo(titulo), abas);
      } catch (erro) {
        alert((erro as Error).message);
      } finally {
        setOcupado(false);
      }
    },
    [alvo, contexto],
  );

  return (
    <div className="exportar" title="Exporta as tabelas desta página">
      <span className="sutil">{ocupado ? "Exportando…" : "Exportar"}</span>
      <button className="secundario" disabled={ocupado} onClick={() => exportar("csv")}>
        CSV
      </button>
      <button className="secundario" disabled={ocupado} onClick={() => exportar("xlsx")}>
        XLSX
      </button>
    </div>
  );
}
