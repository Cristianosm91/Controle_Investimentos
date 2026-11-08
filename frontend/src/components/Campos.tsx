import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useId, useState } from "react";
import { api } from "../api";
import { useAtivos, useCorretoras, useDominio, usePtax } from "../cadastros";
import { data as fmtData, numero } from "../formato";
import { useInvestidor } from "../InvestidorContext";
import type { Ativo } from "../tipos";

interface Selecao {
  valor: string;
  aoMudar: (valor: string) => void;
}

export function CampoInvestidor({ valor, aoMudar }: Selecao) {
  const { investidores } = useInvestidor();
  return (
    <label>
      Investidor
      <select required value={valor} onChange={(e) => aoMudar(e.target.value)}>
        <option value="">—</option>
        {investidores
          .filter((i) => i.ativo || String(i.id) === valor)
          .map((i) => (
            <option key={i.id} value={i.id}>
              {i.nome}
            </option>
          ))}
      </select>
    </label>
  );
}

export function CampoCorretora({ valor, aoMudar }: Selecao) {
  const { data: corretoras = [] } = useCorretoras();
  return (
    <label>
      Corretora
      <select value={valor} onChange={(e) => aoMudar(e.target.value)}>
        <option value="">—</option>
        {corretoras.map((c) => (
          <option key={c.id} value={c.id}>
            {c.nome}
          </option>
        ))}
      </select>
    </label>
  );
}

export function CampoEvento({ valor, aoMudar, tipo }: Selecao & { tipo: "eventos_operacao" | "eventos_provento" | "eventos_caixa" }) {
  const { data: dominio } = useDominio();
  return (
    <label>
      Evento
      <select required value={valor} onChange={(e) => aoMudar(e.target.value)}>
        {Object.entries(dominio?.[tipo] ?? {}).map(([codigo, rotulo]) => (
          <option key={codigo} value={codigo}>
            {rotulo}
          </option>
        ))}
      </select>
    </label>
  );
}

const CLASSES_CADASTRO_ATIVO = ["AÇÃO", "BDR", "ETF", "ETF_US", "FII", "FIAGRO", "OPÇÃO", "REIT", "STOCK"];
const MERCADOS_CADASTRO_ATIVO = ["BVMF", "NASDAQ", "NYSE", "NYSEARCA", "NYSEAMERICAN", "BATS"];

/** Ticker digitado com sugestões e cadastro rápido com classe, mercado e moeda explícitos. */
export function CampoAtivo({ ativoId, aoMudar }: { ativoId: string; aoMudar: (ativo: Ativo | undefined) => void }) {
  const { data: ativos = [] } = useAtivos();
  const cliente = useQueryClient();
  const listaId = useId();
  const atual = ativos.find((a) => String(a.id) === ativoId);
  const [texto, setTexto] = useState(atual?.ticker ?? "");
  const [mostrarCadastro, setMostrarCadastro] = useState(false);
  const [classe, setClasse] = useState("");
  const [mercado, setMercado] = useState("");
  const [moeda, setMoeda] = useState("BRL");

  useEffect(() => {
    if (atual) setTexto(atual.ticker);
  }, [atual]);

  const ticker = texto.trim().toUpperCase();
  const encontrado = ativos.find((a) => a.ticker === ticker);

  const cadastrar = useMutation({
    mutationFn: () =>
      api.post<Ativo>("/ativos", {
        ticker,
        classe,
        mercado: mercado || null,
        moeda,
      }),
    onSuccess: (novo) => {
      cliente.setQueryData<Ativo[]>(["ativos"], (lista = []) => [...lista, novo]);
      aoMudar(novo);
      setMostrarCadastro(false);
    },
  });

  return (
    <div className="campo-ativo">
      <label>
        Ativo
        <input
          required
          list={listaId}
          value={texto}
          onChange={(e) => {
            const valor = e.target.value.toUpperCase();
            setTexto(valor);
            setMostrarCadastro(false);
            cadastrar.reset();
            aoMudar(ativos.find((a) => a.ticker === valor.trim()));
          }}
        />
        <datalist id={listaId}>
          {ativos.map((a) => (
            <option key={a.id} value={a.ticker}>
              {a.nome ?? ""}
            </option>
          ))}
        </datalist>
      </label>
      {ticker && !encontrado && (
        <div>
          <small>
            Ativo não cadastrado.{" "}
            {!mostrarCadastro && (
              <button type="button" className="link" onClick={() => setMostrarCadastro(true)}>
                Cadastrar ativo…
              </button>
            )}
            {cadastrar.error && <span className="negativo"> {(cadastrar.error as Error).message}</span>}
          </small>
          {mostrarCadastro && (
            <div className="campos-cadastro-ativo">
              <label>
                Classe
                <select required value={classe} onChange={(e) => setClasse(e.target.value)}>
                  <option value="">Selecione</option>
                  {CLASSES_CADASTRO_ATIVO.map((opcao) => (
                    <option key={opcao} value={opcao}>{opcao}</option>
                  ))}
                </select>
              </label>
              <label>
                Mercado
                <select value={mercado} onChange={(e) => setMercado(e.target.value)}>
                  <option value="">Sem bolsa</option>
                  {MERCADOS_CADASTRO_ATIVO.map((opcao) => (
                    <option key={opcao} value={opcao}>{opcao}</option>
                  ))}
                </select>
              </label>
              <label>
                Moeda
                <select value={moeda} onChange={(e) => setMoeda(e.target.value)}>
                  <option value="BRL">BRL</option>
                  <option value="USD">USD</option>
                  <option value="EUR">EUR</option>
                </select>
              </label>
              <button
                type="button"
                disabled={!classe || cadastrar.isPending}
                onClick={() => cadastrar.mutate()}
              >
                {cadastrar.isPending ? "Cadastrando…" : `Cadastrar ${ticker}`}
              </button>
              <button type="button" className="secundario" onClick={() => setMostrarCadastro(false)}>
                Cancelar
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

interface MoedaCambio {
  moeda: string;
  cambio: string;
  data: string;
  /** Preenche o câmbio com a PTAX assim que ela chega (desligado ao editar um lançamento existente). */
  automatico: boolean;
  aoMudar: (moeda: string, cambio: string, automatico: boolean) => void;
}

export function CamposMoedaCambio({ moeda, cambio, data, automatico, aoMudar }: MoedaCambio) {
  const { data: dominio } = useDominio();
  const ptax = usePtax(moeda, data);

  useEffect(() => {
    if (automatico && ptax.data && String(ptax.data.venda) !== cambio) aoMudar(moeda, String(ptax.data.venda), true);
  }, [automatico, ptax.data, cambio, moeda, aoMudar]);

  return (
    <>
      <label>
        Moeda
        <select value={moeda} onChange={(e) => aoMudar(e.target.value, e.target.value === "BRL" ? "1" : cambio, true)}>
          {(dominio?.moedas ?? ["BRL"]).map((m) => (
            <option key={m}>{m}</option>
          ))}
        </select>
      </label>
      {moeda !== "BRL" && (
        <label>
          Câmbio (R$)
          <input
            required
            type="number"
            step="any"
            min="0"
            value={cambio}
            onChange={(e) => aoMudar(moeda, e.target.value, false)}
          />
          <small className="sutil">
            {ptax.isFetching && "Consultando PTAX…"}
            {ptax.error && <span className="negativo">{(ptax.error as Error).message}</span>}
            {ptax.data && (
              <>
                PTAX venda {fmtData(ptax.data.data_cotacao)}: {numero(ptax.data.venda, 4)}
                {String(ptax.data.venda) !== cambio && (
                  <button type="button" className="link" onClick={() => aoMudar(moeda, String(ptax.data.venda), true)}>
                    usar
                  </button>
                )}
              </>
            )}
          </small>
        </label>
      )}
    </>
  );
}
