import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { api, query } from "../api";
import { Modal } from "../components/Modal";
import { useExclusaoEmLote } from "../components/ExclusaoEmLote";
import { CampoData } from "../components/CampoData";
import { SeletorInvestidorIR, useInvestidorIR } from "../components/SeletorInvestidorIR";
import { invalidarDerivados, useAtivos, useDominio } from "../cadastros";
import { classeSinal, data, mesAno, moeda, numero } from "../formato";
import type { ApuracaoIR, Dirpf, DarfPago, MesIR, Rendimento } from "../tipos";

const ABAS = [
  { id: "apuracao", rotulo: "Apuração mensal" },
  { id: "darfs", rotulo: "DARFs pagos" },
  { id: "exterior", rotulo: "Exterior" },
  { id: "dirpf", rotulo: "DIRPF" },
] as const;

type AbaId = (typeof ABAS)[number]["id"];

const hoje = () => new Date().toLocaleDateString("sv-SE");
const soma = (meses: MesIR[], f: (m: MesIR) => number) => meses.reduce((t, m) => t + f(m), 0);

function useApuracao(investidor: number | undefined, ano?: number) {
  return useQuery({
    queryKey: ["ir-apuracao", investidor, ano],
    queryFn: () => api.get<ApuracaoIR>(`/ir/apuracao${query({ investidor, ano })}`),
    enabled: investidor !== undefined,
  });
}

function SeletorAno({ anos, valor, aoMudar }: { anos: number[]; valor: number; aoMudar: (a: number) => void }) {
  return (
    <label className="check">
      Ano
      <select value={valor} onChange={(e) => aoMudar(Number(e.target.value))}>
        {anos.map((a) => (
          <option key={a} value={a}>
            {a}
          </option>
        ))}
      </select>
    </label>
  );
}

// ---------- Pagamento de DARF ----------

function FormDarf({
  investidor,
  darf,
  competencia,
  valor,
  aoFechar,
}: {
  investidor: number;
  darf?: DarfPago;
  competencia?: string;
  valor?: number;
  aoFechar: () => void;
}) {
  const cliente = useQueryClient();
  const [form, setForm] = useState({
    competencia: (darf?.competencia ?? competencia ?? hoje()).slice(0, 7),
    data_pagamento: darf?.data_pagamento ?? hoje(),
    valor: String(darf?.valor ?? (valor ? Math.round(valor * 100) / 100 : "")),
  });
  const salvar = useMutation({
    mutationFn: () => {
      const corpo = { investidor_id: investidor, competencia: `${form.competencia}-01`, data_pagamento: form.data_pagamento, valor: Number(form.valor) };
      return darf ? api.put(`/ir/darfs/${darf.id}`, corpo) : api.post("/ir/darfs", corpo);
    },
    onSuccess: () => {
      cliente.invalidateQueries({ queryKey: ["ir-darfs"] });
      invalidarDerivados(cliente);
      aoFechar();
    },
  });
  const enviar = (e: FormEvent) => {
    e.preventDefault();
    salvar.mutate();
  };
  return (
    <Modal titulo={darf ? "Editar DARF pago" : "Registrar DARF pago"} aoFechar={aoFechar}>
      {salvar.error && <div className="erro">{(salvar.error as Error).message}</div>}
      <form className="formulario em-modal" onSubmit={enviar}>
        <label>
          Mês de apuração
          <input type="month" required value={form.competencia} onChange={(e) => setForm({ ...form, competencia: e.target.value })} />
        </label>
        <label>
          Data do pagamento
          <CampoData required valor={form.data_pagamento} aoMudar={(v) => setForm({ ...form, data_pagamento: v })} />
        </label>
        <label>
          Valor pago (R$)
          <input type="number" required min={0.01} step="0.01" value={form.valor} onChange={(e) => setForm({ ...form, valor: e.target.value })} />
        </label>
        <div className="acoes largura-total">
          <button type="submit" disabled={salvar.isPending}>
            Salvar
          </button>
        </div>
      </form>
    </Modal>
  );
}

// ---------- Apuração mensal ----------

function Apuracao({ investidor }: { investidor: number }) {
  const { data: dominio } = useDominio();
  const [ano, setAno] = useState<number | undefined>();
  const [pagar, setPagar] = useState<MesIR | null>(null);
  const { data: todos } = useApuracao(investidor);
  const anos = todos?.anos ?? [];
  const anoSel = ano && anos.includes(ano) ? ano : anos.find((a) => todos?.meses.some((m) => m.competencia.startsWith(String(a)))) ?? anos[0];
  const { data: r, error } = useApuracao(investidor, anoSel);

  if (error) return <div className="erro">{(error as Error).message}</div>;
  if (!todos) return <p className="sutil">Carregando…</p>;
  if (!r || !anoSel || r.meses.length === 0) return <p className="sutil">Nenhuma venda de renda variável para apurar.</p>;

  const meses = r.meses;
  const categorias = Object.keys(dominio?.categorias_ir ?? {}).filter(
    (c) => c !== "EXTERIOR" && meses.some((m) => m.categorias.some((x) => x.categoria === c && (x.vendas || x.lucro))),
  );
  const ultimo = meses[meses.length - 1];
  const grupos = Object.keys(dominio?.grupos_prejuizo ?? {}).filter((g) => g !== "EXTERIOR");
  const cat = (m: MesIR, c: string) => m.categorias.find((x) => x.categoria === c)!;

  return (
    <>
      <div className="titulo-linha">
        <SeletorAno anos={anos} valor={anoSel} aoMudar={setAno} />
        <span className="sutil">DARF código 6015 · vencimento no último dia útil do mês seguinte · estimativa, confira no e-CAC</span>
      </div>
      {r.nao_apurados.length > 0 && (
        <div className="aviso">Vendas fora da apuração de renda variável (renda fixa, cripto, outros): {r.nao_apurados.join(", ")}</div>
      )}
      <div className="cards valores-alinhados">
        <div className="card">
          <span>DARF no ano</span>
          <strong>{moeda(soma(meses, (m) => m.darf))}</strong>
        </div>
        <div className="card">
          <span>Pago no ano</span>
          <strong>{moeda(soma(meses, (m) => m.pago))}</strong>
        </div>
        <div className="card">
          <span>Saldo a pagar</span>
          <strong className={classeSinal(-soma(meses, (m) => m.saldo))}>{moeda(soma(meses, (m) => m.saldo))}</strong>
        </div>
        {grupos.map((g) => (
          <div className="card" key={g}>
            <span>Prejuízo a compensar · {dominio?.grupos_prejuizo[g]}</span>
            <strong>{moeda(ultimo.prejuizo[g] ?? 0)}</strong>
          </div>
        ))}
        {ultimo.darf_transportado > 0 && (
          <div className="card">
            <span>DARF abaixo de R$ 10 a acumular</span>
            <strong>{moeda(ultimo.darf_transportado)}</strong>
          </div>
        )}
      </div>

      <div className="tabela-container">
        <table className="tabela matriz">
          <thead>
            <tr>
              <th>Mês</th>
              <th className="num">Vendas ações</th>
              {categorias.map((c) => (
                <th key={c} className="num">
                  Lucro {dominio?.categorias_ir[c]}
                </th>
              ))}
              <th className="num">Base tributável</th>
              <th className="num">IR devido</th>
              <th className="num">IRRF abatido</th>
              <th className="num">DARF</th>
              <th className="num">Pago</th>
              <th className="num">Saldo</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {meses.map((m) => {
              const base = m.categorias.reduce((t, x) => t + x.base, 0);
              return (
                <tr key={m.competencia}>
                  <td>{mesAno(m.competencia)}</td>
                  <td className="num">{cat(m, "ACAO").vendas ? moeda(cat(m, "ACAO").vendas) : ""}</td>
                  {categorias.map((c) => {
                    const x = cat(m, c);
                    return (
                      <td key={c} className={`num ${classeSinal(x.lucro)}`}>
                        {x.vendas || x.lucro ? moeda(x.lucro) : ""}
                        {x.isento && x.lucro > 0 && <span className="etiqueta">isento</span>}
                      </td>
                    );
                  })}
                  <td className="num">{base ? moeda(base) : ""}</td>
                  <td className="num">{m.imposto ? moeda(m.imposto) : ""}</td>
                  <td className="num">{m.irrf_compensado ? moeda(m.irrf_compensado) : ""}</td>
                  <td className="num">
                    {m.darf ? <strong>{moeda(m.darf)}</strong> : ""}
                    {m.darf_transportado > 0 && (
                      <span className="etiqueta" title="Abaixo de R$ 10: soma ao mês seguinte">
                        {moeda(m.darf_transportado)} acumula
                      </span>
                    )}
                  </td>
                  <td className="num">{m.pago ? moeda(m.pago) : ""}</td>
                  <td className={`num ${classeSinal(-m.saldo)}`}>{m.darf || m.pago ? moeda(m.saldo) : ""}</td>
                  <td className="num">
                    {m.saldo > 0.005 && (
                      <button className="link" onClick={() => setPagar(m)}>
                        Registrar pagamento
                      </button>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
          <tfoot>
            <tr>
              <td>Total {anoSel}</td>
              <td className="num">{moeda(soma(meses, (m) => cat(m, "ACAO").vendas))}</td>
              {categorias.map((c) => (
                <td key={c} className="num">
                  {moeda(soma(meses, (m) => cat(m, c).lucro))}
                </td>
              ))}
              <td className="num">{moeda(soma(meses, (m) => m.categorias.reduce((t, x) => t + x.base, 0)))}</td>
              <td className="num">{moeda(soma(meses, (m) => m.imposto))}</td>
              <td className="num">{moeda(soma(meses, (m) => m.irrf_compensado))}</td>
              <td className="num">{moeda(soma(meses, (m) => m.darf))}</td>
              <td className="num">{moeda(soma(meses, (m) => m.pago))}</td>
              <td className="num">{moeda(soma(meses, (m) => m.saldo))}</td>
              <td />
            </tr>
          </tfoot>
        </table>
      </div>
      <p className="sutil">
        Ações com vendas até R$ 20 mil no mês: lucro isento (prejuízo continua compensável). IRRF (0,005% e 1% no day trade) abate o
        imposto até dezembro do mesmo ano. Regras e alíquotas em <Link to="/configuracoes">Configurações → Imposto de renda</Link>.
      </p>
      {pagar && (
        <FormDarf investidor={investidor} competencia={pagar.competencia} valor={pagar.saldo} aoFechar={() => setPagar(null)} />
      )}
    </>
  );
}

// ---------- DARFs pagos ----------

function Darfs({ investidor }: { investidor: number }) {
  const cliente = useQueryClient();
  const [edicao, setEdicao] = useState<DarfPago | "novo" | null>(null);
  const { data: darfs = [], error } = useQuery({
    queryKey: ["ir-darfs", investidor],
    queryFn: () => api.get<DarfPago[]>(`/ir/darfs${query({ investidor })}`),
  });
  const excluir = useMutation({
    mutationFn: (id: number) => api.del(`/ir/darfs/${id}`),
    onSuccess: () => {
      cliente.invalidateQueries({ queryKey: ["ir-darfs"] });
      invalidarDerivados(cliente);
    },
  });
  const selecao = useExclusaoEmLote({
    itens: darfs,
    chave: (d) => d.id,
    remover: (id) => api.del(`/ir/darfs/${id}`),
    titulo: "DARFs pagos",
    consulta: "ir-darfs",
    aposExcluir: () => {
      cliente.invalidateQueries({ queryKey: ["ir-darfs"] });
      invalidarDerivados(cliente);
    },
  });
  const erro = error ?? excluir.error;
  return (
    <>
      <div className="titulo-linha">
        <span className="sutil">Pagamentos abatem o DARF do mês de apuração.</span>
        <button onClick={() => setEdicao("novo")}>+ Registrar DARF pago</button>
      </div>
      {erro && <div className="erro">{(erro as Error).message}</div>}
      {darfs.length === 0 ? (
        <p className="sutil">Nenhum DARF registrado.</p>
      ) : (
        <>
        {selecao.acoes}
        <table className="tabela compacta">
          <thead>
            <tr>
              <th />
              <th>Mês de apuração</th>
              <th>Pagamento</th>
              <th className="num">Valor</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {darfs.map((d) => (
              <tr key={d.id}>
                <td>{selecao.checkbox(d.id)}</td>
                <td>{mesAno(d.competencia)}</td>
                <td>{data(d.data_pagamento)}</td>
                <td className="num">{moeda(d.valor)}</td>
                <td className="num acoes-linha">
                  <button className="link" onClick={() => setEdicao(d)}>
                    Editar
                  </button>
                  <button className="link perigo" onClick={() => confirm(`Excluir DARF de ${mesAno(d.competencia)}?`) && excluir.mutate(d.id)}>
                    Excluir
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        </>
      )}
      {edicao && <FormDarf investidor={investidor} darf={edicao === "novo" ? undefined : edicao} aoFechar={() => setEdicao(null)} />}
    </>
  );
}

// ---------- Exterior ----------

function Exterior({ investidor }: { investidor: number }) {
  const { data: r, error } = useApuracao(investidor);
  if (error) return <div className="erro">{(error as Error).message}</div>;
  if (!r) return <p className="sutil">Carregando…</p>;
  if (r.exterior.length === 0) return <p className="sutil">Sem operações ou proventos no exterior.</p>;
  return (
    <>
      <p className="sutil">
        Até 2023: ganho de capital mensal (GCAP), isento com vendas no mês até R$ 35 mil, sem compensação de prejuízo; dividendos
        aparecem só como informação (carnê-leão mensal pela tabela progressiva, calculado no programa da Receita). Desde 2024 (Lei
        14.754/2023): lucros e dividendos somados no ano, alíquota de 15% na DIRPF, com compensação de prejuízo e dedução do imposto pago no
        exterior (limitada ao imposto brasileiro sobre os dividendos). Valores em reais pela PTAX de cada data.
      </p>
      <table className="tabela compacta">
        <thead>
          <tr>
            <th>Ano</th>
            <th>Regime</th>
            <th className="num">Vendas</th>
            <th className="num">Lucro</th>
            <th className="num">Dividendos</th>
            <th className="num">Imposto pago no exterior</th>
            <th className="num">Base</th>
            <th className="num">IR estimado</th>
            <th className="num">Prejuízo a compensar</th>
          </tr>
        </thead>
        <tbody>
          {[...r.exterior].reverse().map((e) => (
            <tr key={e.ano}>
              <td>{e.ano}</td>
              <td>{e.regimes.map((x) => (x === "ANUAL" ? "Anual" : "GCAP mensal")).join(" + ")}</td>
              <td className="num">{moeda(e.vendas)}</td>
              <td className={`num ${classeSinal(e.lucro)}`}>{moeda(e.lucro)}</td>
              <td className="num">{moeda(e.dividendos)}</td>
              <td className="num">{moeda(e.imposto_pago_exterior)}</td>
              <td className="num">{moeda(e.base)}</td>
              <td className="num">
                <strong>{moeda(e.imposto)}</strong>
              </td>
              <td className="num">{moeda(e.prejuizo)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );
}

// ---------- DIRPF ----------

const FICHAS: Record<Rendimento["ficha"], string> = {
  ISENTO: "Rendimentos isentos e não tributáveis",
  EXCLUSIVO: "Rendimentos sujeitos à tributação exclusiva/definitiva",
  OUTROS: "A classificar",
};

function formatarCnpj(cnpj: string | null) {
  return cnpj ? cnpj.replace(/^(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})$/, "$1.$2.$3/$4-$5") : "";
}

function DirpfRelatorio({ investidor }: { investidor: number }) {
  const { data: dominio } = useDominio();
  const { data: ativos = [] } = useAtivos();
  const cliente = useQueryClient();
  const anoPadrao = new Date().getFullYear() - 1;
  const [ano, setAno] = useState(anoPadrao);
  const { data: r, error } = useQuery({
    queryKey: ["ir-dirpf", investidor, ano],
    queryFn: () => api.get<Dirpf>(`/ir/dirpf${query({ investidor, ano })}`),
  });
  const cnpj = useMutation({
    mutationFn: ({ id, valor }: { id: number; valor: string }) => {
      const ativo = ativos.find((a) => a.id === id);
      if (!ativo) throw new Error("Ativo não encontrado");
      return api.put(`/ativos/${id}`, { ...ativo, cnpj: valor || null });
    },
    onSuccess: () => {
      cliente.invalidateQueries({ queryKey: ["ativos"] });
      cliente.invalidateQueries({ queryKey: ["ir-dirpf"] });
    },
  });
  const editarCnpj = (id: number, ticker: string, atual: string | null) => {
    const valor = prompt(`CNPJ de ${ticker} (14 dígitos; vazio para remover)`, formatarCnpj(atual));
    if (valor !== null) cnpj.mutate({ id, valor });
  };

  const anos = Array.from({ length: 10 }, (_, i) => anoPadrao + 1 - i);
  const erro = error ?? cnpj.error;
  return (
    <>
      <div className="titulo-linha nao-imprimir">
        <SeletorAno anos={anos} valor={ano} aoMudar={setAno} />
        <div className="acoes">
          <a className="botao secundario" href={`/api/ir/dirpf.csv${query({ investidor, ano })}`} download>
            Exportar CSV
          </a>
          <button onClick={() => window.print()}>Imprimir / PDF</button>
        </div>
      </div>
      {erro && <div className="erro">{(erro as Error).message}</div>}
      {!r ? (
        <p className="sutil">Carregando…</p>
      ) : (
        <div className="relatorio">
          <h2>
            DIRPF {r.ano + 1} · ano-calendário {r.ano}
          </h2>
          <p className="sutil">
            Apoio ao preenchimento — escolha o grupo/código de cada bem no programa da Receita. Estimativa: confira com os informes das
            corretoras.
          </p>
          {r.avisos.map((a) => (
            <div key={a} className="aviso nao-imprimir">
              {a}
            </div>
          ))}

          <h3>Bens e direitos (custo de aquisição)</h3>
          <div className="tabela-container">
          <table className="tabela">
            <thead>
              <tr>
                <th>Tipo</th>
                <th>Ticker</th>
                <th>CNPJ</th>
                <th className="num">Quantidade</th>
                <th className="num">31/12/{r.ano - 1}</th>
                <th className="num">31/12/{r.ano}</th>
                <th>Discriminação</th>
              </tr>
            </thead>
            <tbody>
              {r.bens.map((b) => (
                <tr key={b.ativo_id}>
                  <td>{b.tipo}</td>
                  <td>{b.ticker}</td>
                  <td>
                    {formatarCnpj(b.cnpj)}
                    {b.tipo !== "Ativo no exterior" && (
                      <button className="link nao-imprimir" onClick={() => editarCnpj(b.ativo_id, b.ticker, b.cnpj)}>
                        {b.cnpj ? "alterar" : "informar"}
                      </button>
                    )}
                  </td>
                  <td className="num">{numero(b.quantidade, 8)}</td>
                  <td className="num">{moeda(b.custo_anterior)}</td>
                  <td className="num">{moeda(b.custo_atual)}</td>
                  <td className="quebra">{b.discriminacao}</td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr>
                <td colSpan={4}>Total</td>
                <td className="num">{moeda(r.bens.reduce((t, b) => t + b.custo_anterior, 0))}</td>
                <td className="num">{moeda(r.bens.reduce((t, b) => t + b.custo_atual, 0))}</td>
                <td />
              </tr>
            </tfoot>
          </table>
          </div>

          {(["ISENTO", "EXCLUSIVO", "OUTROS"] as const).map((ficha) => {
            const itens = r.rendimentos.filter((x) => x.ficha === ficha);
            if (itens.length === 0) return null;
            return (
              <div key={ficha}>
                <h3>{FICHAS[ficha]}</h3>
                <table className="tabela compacta">
                  <thead>
                    <tr>
                      <th>Tipo</th>
                      <th>Fonte</th>
                      <th>CNPJ</th>
                      <th className="num">Valor</th>
                      {ficha !== "ISENTO" && <th className="num">IR retido</th>}
                    </tr>
                  </thead>
                  <tbody>
                    {itens.map((x) => (
                      <tr key={`${x.tipo}-${x.ativo_id}`}>
                        <td className="quebra">{x.tipo}</td>
                        <td>{x.ticker ?? "—"}</td>
                        <td>{formatarCnpj(x.cnpj)}</td>
                        <td className="num">{moeda(x.valor)}</td>
                        {ficha !== "ISENTO" && <td className="num">{moeda(x.irrf)}</td>}
                      </tr>
                    ))}
                  </tbody>
                  <tfoot>
                    <tr>
                      <td colSpan={3}>Total</td>
                      <td className="num">{moeda(itens.reduce((t, x) => t + x.valor, 0))}</td>
                      {ficha !== "ISENTO" && <td className="num">{moeda(itens.reduce((t, x) => t + x.irrf, 0))}</td>}
                    </tr>
                  </tfoot>
                </table>
              </div>
            );
          })}

          <h3>Renda variável</h3>
          <div className="cards">
            <div className="card">
              <span>DARF no ano</span>
              <strong>{moeda(soma(r.meses, (m) => m.darf))}</strong>
            </div>
            <div className="card">
              <span>Pago no ano</span>
              <strong>{moeda(soma(r.meses, (m) => m.pago))}</strong>
            </div>
            <div className="card">
              <span>IRRF não compensado no ano</span>
              <strong>{moeda(r.irrf_saldo_final)}</strong>
            </div>
            {Object.entries(r.prejuizo_final).map(([g, v]) => (
              <div className="card" key={g}>
                <span>Prejuízo em 31/12 · {dominio?.grupos_prejuizo[g] ?? g}</span>
                <strong>{moeda(v)}</strong>
              </div>
            ))}
          </div>

          {r.exterior && (
            <>
              <h3>Exterior (Lei 14.754/2023)</h3>
              <div className="cards">
                <div className="card">
                  <span>Lucro nas vendas</span>
                  <strong className={classeSinal(r.exterior.lucro)}>{moeda(r.exterior.lucro)}</strong>
                </div>
                <div className="card">
                  <span>Dividendos</span>
                  <strong>{moeda(r.exterior.dividendos)}</strong>
                </div>
                <div className="card">
                  <span>Imposto pago no exterior</span>
                  <strong>{moeda(r.exterior.imposto_pago_exterior)}</strong>
                </div>
                <div className="card">
                  <span>IR estimado</span>
                  <strong>{moeda(r.exterior.imposto)}</strong>
                </div>
              </div>
            </>
          )}
        </div>
      )}
    </>
  );
}

// ---------- Página ----------

export function ImpostoRenda() {
  const [investidor, setInvestidor] = useInvestidorIR();
  const [aba, setAba] = useState<AbaId>("apuracao");

  return (
    <section>
      <div className="titulo-linha nao-imprimir">
        <h1>Imposto de Renda</h1>
        <SeletorInvestidorIR valor={investidor} aoMudar={setInvestidor} />
      </div>
      <div className="abas nao-imprimir">
        {ABAS.map((a) => (
          <button key={a.id} className={a.id === aba ? "aba ativa" : "aba"} onClick={() => setAba(a.id)}>
            {a.rotulo}
          </button>
        ))}
      </div>
      {investidor === undefined ? (
        <p className="sutil">Cadastre um investidor em Configurações.</p>
      ) : (
        <>
          {aba === "apuracao" && <Apuracao investidor={investidor} />}
          {aba === "darfs" && <Darfs investidor={investidor} />}
          {aba === "exterior" && <Exterior investidor={investidor} />}
          {aba === "dirpf" && <DirpfRelatorio investidor={investidor} />}
        </>
      )}
    </section>
  );
}
