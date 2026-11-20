import { useState, type FormEvent } from "react";
import { api } from "../api";
import { useAtivos } from "../cadastros";
import { CampoData } from "../components/CampoData";
import { moeda, numero, data } from "../formato";
import { useInvestidor } from "../InvestidorContext";
import type { ConciliacaoPosicao } from "../tipos";

const hoje = () => new Date().toLocaleDateString("sv-SE");

function Diferenca({ valor, formato }: { valor: number | null; formato: "moeda" | "numero" }) {
  if (valor === null) return <span>—</span>;
  const texto = formato === "moeda" ? moeda(valor) : numero(valor, 8);
  return (
    <span>
      {texto} · {valor > 0 ? "app acima" : valor < 0 ? "app abaixo" : "igual"}
    </span>
  );
}

export function Conciliacao() {
  const { investidores } = useInvestidor();
  const { data: ativos = [] } = useAtivos();
  const investidoresAtivos = investidores.filter((investidor) => investidor.ativo);
  const [investidorId, setInvestidorId] = useState("");
  const [ativoId, setAtivoId] = useState("");
  const [dataReferencia, setDataReferencia] = useState(hoje());
  const [quantidadeInformada, setQuantidadeInformada] = useState("");
  const [custoInformado, setCustoInformado] = useState("");
  const [resultado, setResultado] = useState<ConciliacaoPosicao | null>(null);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  const enviar = async (evento: FormEvent) => {
    evento.preventDefault();
    setCarregando(true);
    setErro(null);
    setResultado(null);
    try {
      const resposta = await api.post<ConciliacaoPosicao>("/conciliacao/posicao", {
        investidor_id: Number(investidorId),
        ativo_id: Number(ativoId),
        data_referencia: dataReferencia,
        quantidade_informada: Number(quantidadeInformada),
        custo_informado: Number(custoInformado),
      });
      setResultado(resposta);
    } catch (falha) {
      setErro((falha as Error).message);
    } finally {
      setCarregando(false);
    }
  };

  return (
    <section>
      <h1>Conciliação de posição</h1>
      <p className="sutil">
        Compare quantidade e custo total do extrato da corretora com os cálculos do app na data escolhida.
        A conciliação é somente de leitura: não altera lançamentos nem tenta ajustar diferenças automaticamente.
        Para ativos em moeda estrangeira, informe o custo equivalente em reais.
      </p>

      <form className="formulario simulador" onSubmit={enviar}>
        <label>
          Investidor
          <select required value={investidorId} onChange={(e) => setInvestidorId(e.target.value)}>
            <option value="">Selecione</option>
            {investidoresAtivos.map((investidor) => (
              <option key={investidor.id} value={investidor.id}>
                {investidor.nome}
              </option>
            ))}
          </select>
        </label>
        <label>
          Ativo
          <select required value={ativoId} onChange={(e) => setAtivoId(e.target.value)}>
            <option value="">Selecione</option>
            {ativos.map((ativo) => (
              <option key={ativo.id} value={ativo.id}>
                {ativo.ticker} · {ativo.classe}
              </option>
            ))}
          </select>
        </label>
        <label>
          Data de referência
          <CampoData required valor={dataReferencia} aoMudar={setDataReferencia} />
        </label>
        <label>
          Quantidade no extrato
          <input
            required
            type="number"
            min="0"
            step="any"
            value={quantidadeInformada}
            onChange={(e) => setQuantidadeInformada(e.target.value)}
          />
        </label>
        <label>
          Custo total no extrato (R$)
          <input
            required
            type="number"
            min="0"
            step="any"
            value={custoInformado}
            onChange={(e) => setCustoInformado(e.target.value)}
          />
        </label>
        <button type="submit" disabled={carregando || !investidoresAtivos.length || !ativos.length}>
          {carregando ? "Comparando…" : "Comparar"}
        </button>
      </form>

      {erro && <div className="erro">{erro}</div>}

      {resultado && (
        <>
          <h2>{resultado.ticker} · posição em {data(resultado.data_referencia)}</h2>
          <div className="tabela-container">
            <table className="tabela">
              <thead>
                <tr>
                  <th scope="col">Medida</th>
                  <th scope="col" className="num">Extrato informado</th>
                  <th scope="col" className="num">Calculado pelo app</th>
                  <th scope="col" className="num">Diferença (app − extrato)</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <th scope="row">Quantidade</th>
                  <td className="num">{numero(resultado.quantidade_informada, 8)}</td>
                  <td className="num">{numero(resultado.quantidade_calculada, 8)}</td>
                  <td className="num"><Diferenca valor={resultado.diferenca_quantidade} formato="numero" /></td>
                </tr>
                <tr>
                  <th scope="row">Custo total</th>
                  <td className="num">{moeda(resultado.custo_informado)}</td>
                  <td className="num">{moeda(resultado.custo_calculado)}</td>
                  <td className="num"><Diferenca valor={resultado.diferenca_custo} formato="moeda" /></td>
                </tr>
                <tr>
                  <th scope="row">Preço médio implícito</th>
                  <td className="num">{resultado.preco_medio_informado === null ? "—" : moeda(resultado.preco_medio_informado)}</td>
                  <td className="num">{resultado.preco_medio_calculado === null ? "—" : moeda(resultado.preco_medio_calculado)}</td>
                  <td className="num"><Diferenca valor={resultado.diferenca_preco_medio} formato="moeda" /></td>
                </tr>
              </tbody>
            </table>
          </div>

          <h2>Movimentações consideradas</h2>
          <p className="sutil">
            {resultado.operacoes_total > resultado.operacoes.length
              ? `Exibindo as ${resultado.operacoes.length} movimentações mais recentes de ${resultado.operacoes_total}.`
              : `${resultado.operacoes_total} movimentação(ões) até a data de referência.`}
            {" "}Os valores originais, taxas, IRRF e câmbio estão disponíveis para rastrear a origem da posição.
          </p>
          {resultado.operacoes.length ? (
            <div className="tabela-container">
              <table className="tabela">
                <thead>
                  <tr>
                    <th scope="col">Data</th>
                    <th scope="col">Evento</th>
                    <th scope="col" className="num">Quantidade</th>
                    <th scope="col" className="num">Preço</th>
                    <th scope="col" className="num">Taxas</th>
                    <th scope="col" className="num">IRRF</th>
                    <th scope="col">Moeda</th>
                    <th scope="col" className="num">Câmbio</th>
                    <th scope="col">Origem / observação</th>
                  </tr>
                </thead>
                <tbody>
                  {resultado.operacoes.map((operacao) => (
                    <tr key={operacao.id}>
                      <td>{data(operacao.data)}</td>
                      <td>{operacao.evento}</td>
                      <td className="num">{numero(operacao.quantidade, 8)}</td>
                      <td className="num">{moeda(operacao.preco, operacao.moeda)}</td>
                      <td className="num">{moeda(operacao.taxas, operacao.moeda)}</td>
                      <td className="num">{moeda(operacao.irrf, operacao.moeda)}</td>
                      <td>{operacao.moeda}</td>
                      <td className="num">{numero(operacao.cambio, 6)}</td>
                      <td>{[operacao.origem, operacao.observacao].filter(Boolean).join(" · ") || "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="aviso">Nenhuma operação encontrada para o ativo até essa data.</p>
          )}
        </>
      )}
    </section>
  );
}
