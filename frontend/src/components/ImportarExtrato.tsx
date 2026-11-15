import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Fragment, useMemo, useState } from "react";
import { api, query } from "../api";
import { invalidarDerivados, useDominio } from "../cadastros";
import { data, numero } from "../formato";
import { useInvestidor } from "../InvestidorContext";
import type { LinhaExtrato, PreviaExtrato, ResultadoExtrato, StatusExtrato } from "../tipos";
import { Modal } from "./Modal";
import { ModelosImportacao } from "./ModelosImportacao";

const STATUS: Record<StatusExtrato, string> = {
  novo: "Novo",
  duplicado: "Já existe",
  verificar: "Verificar",
  ignorado: "Não importado",
};

const RELATORIO = {
  NEGOCIACAO: "Negociação",
  MOVIMENTACAO: "Movimentação",
  PROVENTOS: "Proventos recebidos",
  PLANILHA_OPERACOES: "Modelo de operações personalizado",
  PLANILHA_PROVENTOS: "Modelo de proventos personalizado",
};

export function ImportarExtrato({ aoFechar }: { aoFechar: () => void }) {
  const cliente = useQueryClient();
  const { investidores, selecionados } = useInvestidor();
  const { data: dominio } = useDominio();
  const [investidor, setInvestidor] = useState<string>(selecionados.length === 1 ? String(selecionados[0]) : "");
  const [arquivo, setArquivo] = useState<File | null>(null);
  const [incluir, setIncluir] = useState<Set<number>>(new Set());
  const [filtro, setFiltro] = useState<StatusExtrato | "">("");
  const [correcoes, setCorrecoes] = useState<Record<number, Record<string, string>>>({});
  const [linhaAberta, setLinhaAberta] = useState<number | null>(null);

  const parametros = (extra: Record<string, string> = {}) => query({ investidor_id: investidor, ...extra });
  const previa = useMutation({
    mutationFn: ({ arquivo: f, dados }: { arquivo: File; dados: Record<number, Record<string, string>> }) =>
      api.enviar<PreviaExtrato>(`/extratos/b3/previa${parametros({ correcoes: JSON.stringify(dados) })}`, f),
    onSuccess: () => setIncluir(new Set()),
  });
  const importar = useMutation({
    mutationFn: () =>
      api.enviar<ResultadoExtrato>(
        `/extratos/b3/importar${parametros({ incluir: [...incluir].join(","), correcoes: JSON.stringify(correcoes) })}`,
        arquivo!,
      ),
    onSuccess: () => {
      for (const chave of ["operacoes", "proventos", "ativos", "corretoras"]) cliente.invalidateQueries({ queryKey: [chave] });
      invalidarDerivados(cliente);
    },
  });
  const desfazer = useMutation({
    mutationFn: (loteId: number) =>
      api.post<{ operacoes: number; proventos: number; caixa: number }>(`/lotes/${loteId}/desfazer`),
    onSuccess: () => {
      for (const chave of ["lotes", "operacoes", "proventos", "caixa"]) cliente.invalidateQueries({ queryKey: [chave] });
      invalidarDerivados(cliente);
    },
  });

  const linhas = previa.data?.linhas ?? [];
  const contagem = useMemo(() => {
    const c: Record<StatusExtrato, number> = { novo: 0, duplicado: 0, verificar: 0, ignorado: 0 };
    for (const l of linhas) c[l.status]++;
    return c;
  }, [linhas]);
  const aImportar = contagem.novo + incluir.size;
  const visiveis = filtro ? linhas.filter((l) => l.status === filtro) : linhas;
  const loteImportado = importar.data?.lote_id;

  const analisar = (f: File | null) => {
    setArquivo(f);
    setCorrecoes({});
    setLinhaAberta(null);
    importar.reset();
    if (f && investidor) previa.mutate({ arquivo: f, dados: {} });
    else previa.reset();
  };
  const alternar = (n: number) =>
    setIncluir((atual) => {
      const novo = new Set(atual);
      if (novo.has(n)) novo.delete(n);
      else novo.add(n);
      return novo;
    });
  const editarCampo = (numeroLinha: number, campo: string, valor: string) =>
    setCorrecoes((atuais) => ({ ...atuais, [numeroLinha]: { ...atuais[numeroLinha], [campo]: valor } }));
  const revalidar = (linha: LinhaExtrato) => {
    if (!arquivo) return;
    const dados = { ...linha.campos, ...correcoes[linha.numero] };
    const atualizadas = { ...correcoes, [linha.numero]: dados };
    setCorrecoes(atualizadas);
    previa.mutate({ arquivo, dados: atualizadas });
  };

  const evento = (l: LinhaExtrato) =>
    l.evento ? (l.tipo === "PROVENTO" ? dominio?.eventos_provento[l.evento] : dominio?.eventos_operacao[l.evento]) ?? l.evento : "";
  const erro = previa.error ?? importar.error ?? desfazer.error;

  return (
    <Modal titulo="Importar extrato da B3" aoFechar={aoFechar} largo>
      <div className="importar-extrato">
        <p className="sutil">
          Na Área do Investidor da B3, exporte em Excel o relatório <strong>Negociação</strong> (compras e vendas),{" "}
          <strong>Movimentação</strong> (proventos, amortizações e desdobramentos) ou <strong>Proventos recebidos</strong>.
          Também são aceitos os modelos personalizados de operações e proventos em BRL, USD ou EUR.
          Nada é gravado antes da confirmação;
          lançamentos que já existem são ignorados. Nos relatórios B3, corretagem e emolumentos não são informados e as taxas entram zeradas.
        </p>
        <ModelosImportacao
          modelos={[
            { nome: "planilha-operacoes", rotulo: "Modelo de operações personalizado" },
            { nome: "b3-negociacao", rotulo: "Modelo B3 de negociação" },
            { nome: "b3-movimentacao", rotulo: "Modelo B3 de movimentação" },
            { nome: "b3-proventos", rotulo: "Modelo B3 de proventos recebidos" },
            { nome: "proventos-planilha-personalizada", rotulo: "Modelo de proventos personalizado" },
          ]}
        />

        <div className="formulario em-linha">
          <label>
            Investidor (CPF do extrato)
            <select
              value={investidor}
              onChange={(e) => {
                setInvestidor(e.target.value);
                previa.reset();
                importar.reset();
                setArquivo(null);
                setCorrecoes({});
                setLinhaAberta(null);
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
            Arquivo (.xlsx)
            <input
              key={investidor}
              type="file"
              accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
              disabled={!investidor || previa.isPending || importar.isPending}
              onChange={(e) => analisar(e.target.files?.[0] ?? null)}
            />
          </label>
        </div>

        {erro && <div className="erro">{(erro as Error).message}</div>}
        {previa.isPending && <p>Analisando…</p>}

        {importar.data ? (
          <div className="aviso">
            {desfazer.data ? (
              <>
                Importação desfeita: <strong>{desfazer.data.operacoes}</strong> operação(ões),{" "}
                <strong>{desfazer.data.proventos}</strong> provento(s) e{" "}
                <strong>{desfazer.data.caixa}</strong> movimentação(ões) de caixa removidos.
              </>
            ) : (
              <>
                Importados: <strong>{importar.data.operacoes}</strong> operações e{" "}
                <strong>{importar.data.proventos}</strong> proventos.
                {importar.data.ativos_criados.length > 0 && (
                  <> Ativos cadastrados: {importar.data.ativos_criados.join(", ")} (confira a classe em Configurações).</>
                )}
                {importar.data.corretoras_criadas.length > 0 && <> Corretoras: {importar.data.corretoras_criadas.join(", ")}.</>}
              </>
            )}
            <div className="acoes">
              {!desfazer.data && loteImportado != null && (
                <button
                  className="secundario"
                  disabled={desfazer.isPending}
                  onClick={() =>
                    confirm("Desfazer esta importação e remover os lançamentos gravados por ela?") &&
                    desfazer.mutate(loteImportado)
                  }
                >
                  {desfazer.isPending ? "Desfazendo…" : "Desfazer esta importação"}
                </button>
              )}
              <button onClick={aoFechar}>Fechar</button>
            </div>
          </div>
        ) : (
          previa.data && (
            <>
              <div className="etiquetas">
                <span className="etiqueta">Relatório: {RELATORIO[previa.data.relatorio]}</span>
                {(Object.keys(STATUS) as StatusExtrato[]).map((s) => (
                  <button
                    key={s}
                    className={`etiqueta status-${s} ${filtro === s ? "ativa" : ""}`}
                    onClick={() => setFiltro(filtro === s ? "" : s)}
                  >
                    {STATUS[s]}: {contagem[s]}
                  </button>
                ))}
              </div>
              {Object.keys(previa.data.ativos_novos).length > 0 && (
                <p className="sutil">
                  Ativos novos:{" "}
                  {Object.entries(previa.data.ativos_novos)
                    .map(([t, c]) => `${t} (${c})`)
                    .join(", ")}
                  . Confira a classe depois em Configurações.
                </p>
              )}
              {previa.data.corretoras_novas.length > 0 && (
                <p className="sutil">Corretoras novas: {previa.data.corretoras_novas.join(", ")}.</p>
              )}

              <div className="tabela-container rolagem" data-exportar="ignorar">
                <table className="tabela compacta">
                  <thead>
                    <tr>
                      <th>Linha</th>
                      <th>Situação</th>
                      <th>Data</th>
                      <th>Ativo</th>
                      <th>Evento</th>
                      <th className="num">Qtd</th>
                      <th className="num">Preço</th>
                      <th className="num">Valor</th>
                      <th>Instituição</th>
                      <th>Observação</th>
                    </tr>
                  </thead>
                  <tbody>
                    {visiveis.map((l) => (
                      <Fragment key={l.numero}>
                      <tr className={`linha-${l.status}`}>
                        <td>{l.numero}</td>
                        <td>
                          {l.status === "verificar" ? (
                            <label className="check">
                              <input type="checkbox" checked={incluir.has(l.numero)} onChange={() => alternar(l.numero)} />
                              Importar
                            </label>
                          ) : (
                            <>
                              <span className={`etiqueta status-${l.status}`}>{STATUS[l.status]}</span>
                              {l.status === "ignorado" && previa.data?.relatorio === "PLANILHA_OPERACOES" && (
                                <button className="link" onClick={() => setLinhaAberta(linhaAberta === l.numero ? null : l.numero)}>
                                  {linhaAberta === l.numero ? "Fechar" : "Corrigir"}
                                </button>
                              )}
                            </>
                          )}
                        </td>
                        <td>{data(l.data)}</td>
                        <td>{l.ticker ?? "—"}</td>
                        <td>
                          {evento(l) || <span className="sutil">{l.descricao}</span>}
                          {l.daytrade && <span className="etiqueta">day trade</span>}
                        </td>
                        <td className="num">{l.quantidade ? numero(l.quantidade, 8) : "—"}</td>
                        <td className="num">{l.preco ? `${l.moeda} ${numero(l.preco, 8)}` : "—"}</td>
                        <td className="num">{l.valor ? `${l.moeda} ${numero(l.valor, 8)}` : "—"}</td>
                        <td className="quebra">{l.instituicao ?? "—"}</td>
                        <td className="quebra sutil">{l.motivo}</td>
                      </tr>
                      {linhaAberta === l.numero && previa.data?.relatorio === "PLANILHA_OPERACOES" && (
                        <tr className="linha-correcao">
                          <td colSpan={10}>
                            <div className="formulario editar-importacao">
                              <label>
                                Ativo
                                <input value={correcoes[l.numero]?.ticker ?? l.campos.ticker ?? ""} onChange={(e) => editarCampo(l.numero, "ticker", e.target.value.toUpperCase())} />
                              </label>
                              <label>
                                Classe
                                <input value={correcoes[l.numero]?.classe ?? l.campos.classe ?? ""} onChange={(e) => editarCampo(l.numero, "classe", e.target.value.toUpperCase())} />
                              </label>
                              <label>
                                Data
                                <input type="date" value={correcoes[l.numero]?.data ?? l.campos.data ?? ""} onChange={(e) => editarCampo(l.numero, "data", e.target.value)} />
                              </label>
                              <label>
                                Evento
                                <input value={correcoes[l.numero]?.evento ?? l.campos.evento ?? ""} onChange={(e) => editarCampo(l.numero, "evento", e.target.value.toUpperCase())} />
                              </label>
                              <label>
                                Quantidade
                                <input type="number" step="any" value={correcoes[l.numero]?.quantidade ?? l.campos.quantidade ?? ""} onChange={(e) => editarCampo(l.numero, "quantidade", e.target.value)} />
                              </label>
                              <label>
                                Preço
                                <input type="number" step="any" value={correcoes[l.numero]?.preco ?? l.campos.preco ?? ""} onChange={(e) => editarCampo(l.numero, "preco", e.target.value)} />
                              </label>
                              <label>
                                Taxas
                                <input type="number" step="any" value={correcoes[l.numero]?.taxas ?? l.campos.taxas ?? ""} onChange={(e) => editarCampo(l.numero, "taxas", e.target.value)} />
                              </label>
                              <label>
                                Corretora
                                <input value={correcoes[l.numero]?.instituicao ?? l.campos.instituicao ?? ""} onChange={(e) => editarCampo(l.numero, "instituicao", e.target.value)} />
                              </label>
                              <label>
                                IRRF
                                <input type="number" step="any" value={correcoes[l.numero]?.irrf ?? l.campos.irrf ?? ""} onChange={(e) => editarCampo(l.numero, "irrf", e.target.value)} />
                              </label>
                              <label>
                                Moeda
                                <select value={correcoes[l.numero]?.moeda ?? l.campos.moeda ?? "BRL"} onChange={(e) => editarCampo(l.numero, "moeda", e.target.value)}>
                                  <option>BRL</option>
                                  <option>USD</option>
                                  <option>EUR</option>
                                </select>
                              </label>
                              <div className="acoes">
                                <button disabled={previa.isPending} onClick={() => revalidar(l)}>
                                  {previa.isPending ? "Validando…" : "Validar linha"}
                                </button>
                              </div>
                            </div>
                          </td>
                        </tr>
                      )}
                      </Fragment>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="acoes">
                <button disabled={!aImportar || importar.isPending} onClick={() => importar.mutate()}>
                  {importar.isPending ? "Importando…" : `Importar ${aImportar} lançamento(s)`}
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
