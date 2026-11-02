import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { api, query } from "../api";
import { invalidarDerivados, useDominio } from "../cadastros";
import { data, moeda, numero } from "../formato";
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
  PLANILHA_OPERACOES: "Planilha de operações",
};

export function ImportarExtrato({ aoFechar }: { aoFechar: () => void }) {
  const cliente = useQueryClient();
  const { investidores, selecionados } = useInvestidor();
  const { data: dominio } = useDominio();
  const [investidor, setInvestidor] = useState<string>(selecionados.length === 1 ? String(selecionados[0]) : "");
  const [arquivo, setArquivo] = useState<File | null>(null);
  const [incluir, setIncluir] = useState<Set<number>>(new Set());
  const [filtro, setFiltro] = useState<StatusExtrato | "">("");

  const parametros = (extra: Record<string, string> = {}) => query({ investidor_id: investidor, ...extra });
  const previa = useMutation({
    mutationFn: (f: File) => api.enviar<PreviaExtrato>(`/extratos/b3/previa${parametros()}`, f),
    onSuccess: () => setIncluir(new Set()),
  });
  const importar = useMutation({
    mutationFn: () =>
      api.enviar<ResultadoExtrato>(`/extratos/b3/importar${parametros({ incluir: [...incluir].join(",") })}`, arquivo!),
    onSuccess: () => {
      for (const chave of ["operacoes", "proventos", "ativos", "corretoras"]) cliente.invalidateQueries({ queryKey: [chave] });
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

  const analisar = (f: File | null) => {
    setArquivo(f);
    importar.reset();
    if (f && investidor) previa.mutate(f);
    else previa.reset();
  };
  const alternar = (n: number) =>
    setIncluir((atual) => {
      const novo = new Set(atual);
      if (novo.has(n)) novo.delete(n);
      else novo.add(n);
      return novo;
    });

  const evento = (l: LinhaExtrato) =>
    l.evento ? (l.tipo === "PROVENTO" ? dominio?.eventos_provento[l.evento] : dominio?.eventos_operacao[l.evento]) ?? l.evento : "";
  const erro = previa.error ?? importar.error;

  return (
    <Modal titulo="Importar extrato da B3" aoFechar={aoFechar} largo>
      <div className="importar-extrato">
        <p className="sutil">
          Na Área do Investidor da B3, exporte em Excel o relatório <strong>Negociação</strong> (compras e vendas),{" "}
          <strong>Movimentação</strong> (proventos, amortizações e desdobramentos) ou <strong>Proventos recebidos</strong>.
          Também é aceito o modelo de planilha de operações em BRL. 
          Nada é gravado antes da confirmação;
          lançamentos que já existem são ignorados. A B3 não informa corretagem/emolumentos: as taxas entram zeradas.
        </p>
        <ModelosImportacao
          modelos={[
            { nome: "planilha-operacoes", rotulo: "Planilha de operações" },
            { nome: "b3-negociacao", rotulo: "Negociação" },
            { nome: "b3-movimentacao", rotulo: "Movimentação" },
            { nome: "b3-proventos", rotulo: "Proventos recebidos" },
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
            Importados: <strong>{importar.data.operacoes}</strong> operações e{" "}
            <strong>{importar.data.proventos}</strong> proventos.
            {importar.data.ativos_criados.length > 0 && (
              <> Ativos cadastrados: {importar.data.ativos_criados.join(", ")} (confira a classe em Configurações).</>
            )}
            {importar.data.corretoras_criadas.length > 0 && <> Corretoras: {importar.data.corretoras_criadas.join(", ")}.</>}
            {importar.data.lote_id !== null && <> Para desfazer esta importação, use Configurações → Importações.</>}
            <div className="acoes">
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
                      <tr key={l.numero} className={`linha-${l.status}`}>
                        <td>{l.numero}</td>
                        <td>
                          {l.status === "verificar" ? (
                            <label className="check">
                              <input type="checkbox" checked={incluir.has(l.numero)} onChange={() => alternar(l.numero)} />
                              Importar
                            </label>
                          ) : (
                            <span className={`etiqueta status-${l.status}`}>{STATUS[l.status]}</span>
                          )}
                        </td>
                        <td>{data(l.data)}</td>
                        <td>{l.ticker ?? "—"}</td>
                        <td>
                          {evento(l) || <span className="sutil">{l.descricao}</span>}
                          {l.daytrade && <span className="etiqueta">day trade</span>}
                        </td>
                        <td className="num">{l.quantidade ? numero(l.quantidade, 8) : "—"}</td>
                        <td className="num">{l.preco ? moeda(l.preco) : "—"}</td>
                        <td className="num">{l.valor ? moeda(l.valor) : "—"}</td>
                        <td className="quebra">{l.instituicao ?? "—"}</td>
                        <td className="quebra sutil">{l.motivo}</td>
                      </tr>
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
