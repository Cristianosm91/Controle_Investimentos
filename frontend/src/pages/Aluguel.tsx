import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api, query } from "../api";
import { invalidarDerivados } from "../cadastros";
import { AcoesLinha } from "../components/AcoesLinha";
import { FormProvento } from "../components/FormLancamentos";
import { GraficoBarras } from "../components/Graficos";
import { ListaPaginada, type ColunaLista } from "../components/ListaPaginada";
import { Modal } from "../components/Modal";
import { ModelosImportacao } from "../components/ModelosImportacao";
import { data, mesAno, moeda, moedaCompacta, numero } from "../formato";
import { useInvestidor } from "../InvestidorContext";
import type { ItemAluguel, Provento, ResumoAluguel } from "../tipos";

const STATUS: Record<ItemAluguel["status"], string> = {
  novo: "Novo",
  duplicado: "Já existe",
  verificar: "Verificar",
  sem_ativo: "Sem ativo",
};
const CLASSE_STATUS: Record<ItemAluguel["status"], string> = {
  novo: "novo",
  duplicado: "duplicado",
  verificar: "verificar",
  sem_ativo: "ignorado",
};

function ImportarAluguel({ aoFechar }: { aoFechar: () => void }) {
  const cliente = useQueryClient();
  const { investidores, selecionados } = useInvestidor();
  const [investidor, setInvestidor] = useState(selecionados.length === 1 ? String(selecionados[0]) : "");
  const [arquivo, setArquivo] = useState<File | null>(null);
  const [incluir, setIncluir] = useState<Set<string>>(new Set());

  const previa = useMutation({
    mutationFn: (f: File) => api.enviar<ItemAluguel[]>(`/aluguel/extrato/previa${query({ investidor_id: investidor })}`, f),
    onSuccess: () => setIncluir(new Set()),
  });
  const importar = useMutation({
    mutationFn: () =>
      api.enviar<{ gravados: number }>(
        `/aluguel/extrato/importar${query({ investidor_id: investidor, incluir: [...incluir].join(",") })}`,
        arquivo!,
      ),
    onSuccess: () => {
      for (const chave of ["aluguel", "proventos"]) cliente.invalidateQueries({ queryKey: [chave] });
      invalidarDerivados(cliente);
    },
  });
  const itens = previa.data ?? [];
  const aGravar = itens.filter((i) => i.status === "novo").length + incluir.size;
  const erro = previa.error ?? importar.error;

  return (
    <Modal titulo="Importar aluguel (BTC) do extrato da corretora" aoFechar={aoFechar} largo>
      <div className="importar-extrato">
        <p className="sutil">
          Envie o extrato da conta da corretora (.xlsx ou .csv) com as colunas de data (Liquidação/Data), Lançamento ou
          Histórico e Valor. São usadas só as linhas “Crédito Ref. Taxa de Remuneração BTC”, “Taxa de intermediação
          doador” e “DEBITO CBLC IRRF S/ RENDIMENTO DE BTC”, agrupadas por data e ativo.
        </p>
        <ModelosImportacao modelos={[{ nome: "aluguel", rotulo: "Extrato de aluguel (BTC)" }]} />
        <div className="formulario em-linha">
          <label>
            Investidor
            <select
              value={investidor}
              onChange={(e) => {
                setInvestidor(e.target.value);
                previa.reset();
                importar.reset();
              }}
            >
              <option value="">Selecione…</option>
              {investidores.map((i) => (
                <option key={i.id} value={i.id}>
                  {i.nome}
                </option>
              ))}
            </select>
          </label>
          <label>
            Arquivo (.xlsx ou .csv)
            <input
              key={investidor}
              type="file"
              accept=".xlsx,.csv,text/csv"
              disabled={!investidor || previa.isPending || importar.isPending}
              onChange={(e) => {
                const f = e.target.files?.[0] ?? null;
                setArquivo(f);
                importar.reset();
                if (f) previa.mutate(f);
              }}
            />
          </label>
        </div>
        {erro && <div className="erro">{(erro as Error).message}</div>}
        {previa.isPending && <p>Analisando…</p>}

        {importar.data ? (
          <div className="aviso">
            {importar.data.gravados} lançamento(s) de aluguel gravado(s).
            <div className="acoes">
              <button onClick={aoFechar}>Fechar</button>
            </div>
          </div>
        ) : (
          itens.length > 0 && (
            <>
              <div className="tabela-container rolagem" data-exportar="ignorar">
                <table className="tabela compacta">
                  <thead>
                    <tr>
                      <th>Situação</th>
                      <th>Data</th>
                      <th>Ativo</th>
                      <th className="num">Remuneração</th>
                      <th className="num">Taxa</th>
                      <th className="num">IRRF</th>
                      <th className="num">Líquido</th>
                      <th>Linhas</th>
                      <th>Observação</th>
                    </tr>
                  </thead>
                  <tbody>
                    {itens.map((i) => (
                      <tr key={i.hash} className={`linha-${CLASSE_STATUS[i.status]}`}>
                        <td>
                          {i.status === "verificar" ? (
                            <label className="check">
                              <input
                                type="checkbox"
                                checked={incluir.has(i.hash)}
                                onChange={() =>
                                  setIncluir((atual) => {
                                    const novo = new Set(atual);
                                    if (novo.has(i.hash)) novo.delete(i.hash);
                                    else novo.add(i.hash);
                                    return novo;
                                  })
                                }
                              />
                              Importar
                            </label>
                          ) : (
                            <span className={`etiqueta status-${CLASSE_STATUS[i.status]}`}>{STATUS[i.status]}</span>
                          )}
                        </td>
                        <td>{data(i.data)}</td>
                        <td>{i.ticker ?? i.raiz}</td>
                        <td className="num">{moeda(i.valor)}</td>
                        <td className="num">{moeda(i.taxas)}</td>
                        <td className="num">{moeda(i.irrf)}</td>
                        <td className="num">{moeda(i.valor - i.taxas - i.irrf)}</td>
                        <td>{i.linhas.join(", ")}</td>
                        <td className="quebra sutil">{i.motivo}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="acoes">
                <button disabled={!aGravar || importar.isPending} onClick={() => importar.mutate()}>
                  {importar.isPending ? "Importando…" : `Importar ${aGravar} lançamento(s)`}
                </button>
                <button className="secundario" onClick={aoFechar}>
                  Cancelar
                </button>
              </div>
            </>
          )
        )}
      </div>
    </Modal>
  );
}

function Resumo({ filtro }: { filtro: string | undefined }) {
  const [ano, setAno] = useState("");
  const { data: r, error } = useQuery({
    queryKey: ["aluguel", filtro, ano],
    queryFn: () => api.get<ResumoAluguel>(`/aluguel${query({ investidores: filtro, ano })}`),
  });
  if (error) return <div className="erro">{(error as Error).message}</div>;
  if (!r) return <p>Carregando…</p>;

  return (
    <>
      <div className="linha-form">
        <label>
          Período do resumo{" "}
          <select value={ano} onChange={(e) => setAno(e.target.value)}>
            <option value="">Todo o histórico</option>
            {r.anos.map((a) => (
              <option key={a} value={a}>
                {a}
              </option>
            ))}
          </select>
        </label>
      </div>
      <div className="cards">
        <div className="card">
          <span>Remuneração bruta</span>
          <strong>{moeda(r.totais.bruto)}</strong>
        </div>
        <div className="card">
          <span>Taxa de intermediação</span>
          <strong>{moeda(r.totais.taxas)}</strong>
        </div>
        <div className="card">
          <span>IRRF</span>
          <strong>{moeda(r.totais.irrf)}</strong>
        </div>
        <div className="card">
          <span>Líquido</span>
          <strong className={r.totais.liquido >= 0 ? "positivo" : "negativo"}>{moeda(r.totais.liquido)}</strong>
          <small className="sutil">{r.lancamentos} lançamento(s)</small>
        </div>
      </div>

      {r.lancamentos > 0 && (
        <div className="paineis alinhado-topo">
          <div className="painel">
            <h3>Líquido por mês</h3>
            <GraficoBarras
              datas={r.por_mes.map((m) => `${m.mes}-01`)}
              valores={r.por_mes.map((m) => m.liquido)}
              formatar={moedaCompacta}
            />
          </div>
          <div className="painel">
            <h3>Por ativo</h3>
            <div className="tabela-container">
            <table className="tabela compacta">
              <thead>
                <tr>
                  <th>Ativo</th>
                  <th className="num">Bruto</th>
                  <th className="num">Taxa</th>
                  <th className="num">IRRF</th>
                  <th className="num">Líquido</th>
                  <th className="num">Lanç.</th>
                  <th>Último</th>
                </tr>
              </thead>
              <tbody>
                {r.por_ativo.map((a) => (
                  <tr key={a.ticker}>
                    <td>
                      <strong>{a.ticker}</strong>
                    </td>
                    <td className="num">{moeda(a.bruto)}</td>
                    <td className="num">{moeda(a.taxas)}</td>
                    <td className="num">{moeda(a.irrf)}</td>
                    <td className="num">{moeda(a.liquido)}</td>
                    <td className="num">{numero(a.lancamentos, 0)}</td>
                    <td>{data(a.ultimo)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            </div>
          </div>
        </div>
      )}
      {r.por_mes.length > 0 && (
        <p className="sutil">
          Período com aluguel: {mesAno(`${r.por_mes[0].mes}-01`)} a {mesAno(`${r.por_mes[r.por_mes.length - 1].mes}-01`)}.
          A remuneração do BTC é rendimento tributável (IRRF retido na fonte) e aparece na DIRPF em tributação exclusiva.
        </p>
      )}
      <h2>Lançamentos</h2>
    </>
  );
}

export function Aluguel() {
  const { filtro, investidores } = useInvestidor();
  const [edicao, setEdicao] = useState<Provento | "novo" | null>(null);
  const [importando, setImportando] = useState(false);
  const nome = (id: number) => investidores.find((i) => i.id === id)?.nome ?? id;

  const colunas: ColunaLista<Provento>[] = [
    { titulo: "Data", render: (p) => data(p.data_pagamento) },
    { titulo: "Investidor", render: (p) => nome(p.investidor_id) },
    { titulo: "Ativo", render: (p) => <strong>{p.ticker}</strong> },
    { titulo: "Remuneração", numerica: true, render: (p) => moeda(p.valor, p.moeda) },
    { titulo: "Taxa", numerica: true, render: (p) => moeda(p.taxas, p.moeda) },
    { titulo: "IRRF", numerica: true, render: (p) => moeda(p.irrf, p.moeda) },
    { titulo: "Líquido (R$)", numerica: true, render: (p) => moeda((p.valor - p.irrf - p.taxas) * p.cambio) },
    { titulo: "Corretora", render: (p) => p.corretora ?? "—" },
  ];

  return (
    <>
      <ListaPaginada<Provento>
        titulo="Aluguel de ações (BTC)"
        recurso="proventos"
        filtrosFixos={{ evento: "ALUGUEL" }}
        filtroInvestidores={filtro}
        colunas={colunas}
        chave={(p) => p.id}
        topo={<Resumo filtro={filtro} />}
        cabecalho={
          <>
            <button className="secundario" onClick={() => setImportando(true)}>
              Importar extrato da corretora
            </button>
            <button onClick={() => setEdicao("novo")}>+ Novo aluguel</button>
          </>
        }
        acoes={(p) => (
          <AcoesLinha
            recurso="proventos"
            id={p.id}
            descricao={`aluguel de ${p.ticker} em ${data(p.data_pagamento)}`}
            aoEditar={() => setEdicao(p)}
          />
        )}
      />
      {edicao && (
        <FormProvento
          provento={edicao === "novo" ? undefined : edicao}
          eventoInicial="ALUGUEL"
          aoFechar={() => setEdicao(null)}
        />
      )}
      {importando && <ImportarAluguel aoFechar={() => setImportando(false)} />}
    </>
  );
}
