import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api, query } from "../api";
import { AjudaIndicador } from "../components/AjudaIndicador";
import { AjudaInfo } from "../components/AjudaInfo";
import { classeSinal, data, moeda, numero, percentual } from "../formato";
import { useInvestidor } from "../InvestidorContext";
import type { Ativo, PremissasValuation, Valuation as ValuationTipo } from "../tipos";
import "./Valuation.css";

type CampoPremissa = keyof PremissasValuation;
type Formulario = Record<CampoPremissa, string>;
type CampoConfiguracao = { chave: CampoPremissa; rotulo: string; unidade: string; passo: string };
type BuscaPremissas = { premissas: PremissasValuation; avisos: string[] };

const CAMPOS_AUTOMATICOS: CampoPremissa[] = ["lpa", "vpa", "dividendo_anual", "roe", "payout", "g"];

const AJUDA_PREMISSAS: Record<CampoPremissa, string> = {
  lpa: "Lucro líquido por ação. Exemplo: lucro atribuível de R$ 1 bilhão dividido por 200 milhões de ações = R$ 5 por ação.",
  vpa: "Patrimônio líquido por ação. Exemplo: patrimônio líquido de R$ 4 bilhões dividido por 200 milhões de ações = R$ 20 por ação.",
  dividendo_anual: "Soma dos dividendos por ação nos últimos 12 meses. Exemplo: quatro pagamentos de R$ 0,50 = R$ 2,00 por ação.",
  roe: "Retorno sobre o patrimônio líquido, em percentual. Exemplo: ROE de 15% significa R$ 0,15 de lucro para cada R$ 1 de patrimônio.",
  payout: "Parcela do lucro distribuída aos acionistas, em percentual. Exemplo: payout de 60% indica distribuição de R$ 0,60 a cada R$ 1 de lucro.",
  g: "Crescimento anual perpétuo estimado depois do período projetado. Exemplo: 3% ao ano; use uma premissa conservadora.",
  ke: "Taxa anual usada para descontar os fluxos de caixa ao valor presente. Exemplo: custo de capital próprio de 12% ao ano.",
  pl_historico: "Múltiplo preço/lucro-alvo baseado no histórico da empresa. Exemplo: P/L-alvo de 10 significa preço igual a 10 vezes o lucro por ação.",
  pl_setor: "Múltiplo preço/lucro-alvo de referência para o setor. Exemplo: P/L setorial de 12 significa preço igual a 12 vezes o lucro por ação.",
  fcfe_1: "Fluxo de caixa livre para o acionista por ação no ano 1. Exemplo: R$ 2,00 por ação projetados para o próximo ano.",
  fcfe_2: "Fluxo de caixa livre para o acionista por ação no ano 2. Exemplo: R$ 2,20 por ação projetados para daqui a dois anos.",
  fcfe_3: "Fluxo de caixa livre para o acionista por ação no ano 3. Exemplo: R$ 2,40 por ação projetados para daqui a três anos.",
  fcfe_4: "Fluxo de caixa livre para o acionista por ação no ano 4. Exemplo: R$ 2,60 por ação projetados para daqui a quatro anos.",
  fcfe_5: "Fluxo de caixa livre para o acionista por ação no ano 5. Exemplo: R$ 2,80 por ação projetados para daqui a cinco anos.",
};

const CAMPOS: CampoConfiguracao[] = [
  { chave: "lpa", rotulo: "LPA", unidade: "por ação", passo: "any" },
  { chave: "vpa", rotulo: "VPA", unidade: "por ação", passo: "any" },
  { chave: "dividendo_anual", rotulo: "Dividendo anual", unidade: "por ação", passo: "any" },
  { chave: "roe", rotulo: "ROE", unidade: "%", passo: "0.01" },
  { chave: "payout", rotulo: "Payout", unidade: "%", passo: "0.01" },
  { chave: "g", rotulo: "Crescimento perpétuo (g)", unidade: "%", passo: "0.01" },
  { chave: "ke", rotulo: "Custo de capital (Ke)", unidade: "%", passo: "0.01" },
  { chave: "pl_historico", rotulo: "P/L histórico-alvo", unidade: "múltiplo", passo: "any" },
  { chave: "pl_setor", rotulo: "P/L do setor-alvo", unidade: "múltiplo", passo: "any" },
  { chave: "fcfe_1", rotulo: "FCFE por ação · ano 1", unidade: "por ação", passo: "any" },
  { chave: "fcfe_2", rotulo: "FCFE por ação · ano 2", unidade: "por ação", passo: "any" },
  { chave: "fcfe_3", rotulo: "FCFE por ação · ano 3", unidade: "por ação", passo: "any" },
  { chave: "fcfe_4", rotulo: "FCFE por ação · ano 4", unidade: "por ação", passo: "any" },
  { chave: "fcfe_5", rotulo: "FCFE por ação · ano 5", unidade: "por ação", passo: "any" },
];

const GRUPOS_CAMPOS: { titulo: string; chaves: CampoPremissa[] }[] = [
  { titulo: "Fundamentos", chaves: ["lpa", "vpa", "dividendo_anual", "roe", "payout"] },
  { titulo: "Premissas de valuation", chaves: ["ke", "g", "pl_historico", "pl_setor"] },
  { titulo: "FCFE", chaves: ["fcfe_1", "fcfe_2", "fcfe_3", "fcfe_4", "fcfe_5"] },
];

const CAMPOS_PERCENTUAIS = new Set<CampoPremissa>(["roe", "payout", "g", "ke"]);

function formularioVazio(): Formulario {
  return Object.fromEntries(CAMPOS.map(({ chave }) => [chave, ""])) as Formulario;
}

function preencherFormulario(premissas: PremissasValuation): Formulario {
  return Object.fromEntries(
    CAMPOS.map(({ chave }) => {
      const valor = premissas[chave];
      return [chave, valor === null ? "" : String(CAMPOS_PERCENTUAIS.has(chave) ? valor * 100 : valor)];
    }),
  ) as Formulario;
}

function valorNumerico(formulario: Formulario, chave: CampoPremissa): number | null {
  const texto = formulario[chave].trim();
  if (!texto) return null;
  const valor = Number(texto);
  if (!Number.isFinite(valor)) return null;
  return CAMPOS_PERCENTUAIS.has(chave) ? valor / 100 : valor;
}

function criarPremissas(formulario: Formulario): PremissasValuation {
  const premissas = {} as PremissasValuation;
  for (const { chave } of CAMPOS) premissas[chave] = valorNumerico(formulario, chave);
  return premissas;
}

export function Valuation() {
  const { filtro } = useInvestidor();
  const cliente = useQueryClient();
  const [params, setParams] = useSearchParams();
  const ativoId = params.get("ativo") ?? "";
  const [ticker, setTicker] = useState("");
  const [classeNova, setClasseNova] = useState<"AÇÃO" | "FII" | "FIAGRO">("AÇÃO");
  const [avisos, setAvisos] = useState<string[]>([]);
  const [mensagemBusca, setMensagemBusca] = useState("");
  const [formulario, setFormulario] = useState<Formulario>(formularioVazio);
  const ativos = useQuery({ queryKey: ["ativos"], queryFn: () => api.get<Ativo[]>("/ativos") });

  const selecionar = (id: number | string) => setParams({ ativo: String(id) }, { replace: true });

  const ativoAtual = ativos.data?.find((ativo) => String(ativo.id) === ativoId);
  const tickerAtual = ativoAtual?.ticker;
  useEffect(() => {
    if (tickerAtual) setTicker(tickerAtual);
  }, [ativoId, tickerAtual]);

  const preparar = useMutation({
    mutationFn: (dados: { ticker: string; classe: string }) =>
      api.post<{ ativo_id: number; ticker: string; criado: boolean; avisos: string[] }>("/valuation/ativo", dados),
    onSuccess: async (resultado) => {
      setAvisos(resultado.avisos);
      if (resultado.criado) await cliente.invalidateQueries({ queryKey: ["ativos"] });
      cliente.invalidateQueries({ queryKey: ["valuation", String(resultado.ativo_id)] });
      selecionar(resultado.ativo_id);
    },
  });

  const buscarTicker = () => {
    const alvo = ticker.trim().toUpperCase();
    if (!alvo) return;
    setAvisos([]);
    preparar.mutate({ ticker: alvo, classe: classeNova });
  };

  const valuation = useQuery({
    queryKey: ["valuation", ativoId, filtro],
    queryFn: () =>
      api.get<ValuationTipo>(`/valuation/${Number(ativoId)}${query({ investidores: filtro })}`),
    enabled: Boolean(ativoAtual),
  });

  useEffect(() => {
    if (valuation.data) setFormulario(preencherFormulario(valuation.data.premissas));
  }, [valuation.data]);

  const salvar = useMutation({
    mutationFn: ({ id, premissas }: { id: number; premissas: PremissasValuation }) =>
      api.put<ValuationTipo>(`/valuation/${id}/premissas${query({ investidores: filtro })}`, premissas),
    onSuccess: (resultado, variaveis) => {
      cliente.setQueryData(["valuation", String(variaveis.id), filtro], resultado);
      cliente.invalidateQueries({ queryKey: ["valuation-historico"] });
    },
  });
  const buscarPremissas = useMutation({
    mutationFn: (id: number) => api.post<BuscaPremissas>(`/valuation/${id}/buscar-premissas`),
    onSuccess: (resultado) => {
      setFormulario((atual) => {
        const proximo = { ...atual };
        for (const chave of CAMPOS_AUTOMATICOS) {
          const valor = resultado.premissas[chave];
          if (valor !== null) proximo[chave] = String(CAMPOS_PERCENTUAIS.has(chave) ? valor * 100 : valor);
        }
        return proximo;
      });
      setAvisos(resultado.avisos);
      setMensagemBusca("Premissas disponíveis atualizadas. Campos sem dados automáticos foram mantidos.");
    },
    onError: () => setMensagemBusca("Não foi possível buscar as premissas."),
  });
  const erro = ativos.error ?? preparar.error ?? valuation.error ?? salvar.error ?? buscarPremissas.error;
  const detalhe = valuation.data;
  const mensagemErro = erro instanceof Error ? erro.message : erro ? String(erro) : null;

  return (
    <section className="valuation">
      <div className="titulo-linha">
        <h1>Valuation</h1>
        <span className="sutil">Modelos indicativos por ativo; não constituem recomendação de investimento</span>
        <Link to="/valuations-salvos" className="link">
          Ver valuations salvos →
        </Link>
      </div>

      {mensagemErro && <div className="erro">{mensagemErro}</div>}
      {avisos.map((aviso) => (
        <div key={aviso} className="aviso">
          {aviso}
        </div>
      ))}

      <form
        className="painel valuation-selecao"
        onSubmit={(evento) => {
          evento.preventDefault();
          buscarTicker();
        }}
      >
        <label>
          Ativo
          <input
            value={ticker}
            onChange={(evento) => setTicker(evento.target.value.toUpperCase())}
            placeholder="Digite um ticker, ex.: PETR4"
            maxLength={16}
            pattern="[A-Za-z0-9]{4,16}"
            title="Use de 4 a 16 letras ou números"
            required
          />
        </label>
        <label className="valuation-classe">
          Classe (se novo)
          <select value={classeNova} onChange={(evento) => setClasseNova(evento.target.value as typeof classeNova)}>
            <option value="AÇÃO">Ação</option>
            <option value="FII">FII</option>
            <option value="FIAGRO">Fiagro</option>
          </select>
        </label>
        <button className="valuation-salvar" disabled={preparar.isPending}>
          {preparar.isPending ? "BUSCANDO…" : "CALCULAR"}
        </button>
        {detalhe && (
          <div className="sutil valuation-fontes">
            {detalhe.ticker}
            {detalhe.nome ? ` — ${detalhe.nome}` : ""} · Cotação {detalhe.cotacao_fonte ?? "sem fonte"}, de{" "}
            {data(detalhe.cotacao_data)} · Fundamentos {detalhe.fundamento_fonte ?? "indisponíveis"}, de{" "}
            {data(detalhe.fundamento_data)}
            {detalhe.premissas_salvas_em && <> · Premissas salvas em {data(detalhe.premissas_salvas_em)}</>}
          </div>
        )}
      </form>

      {ativos.isLoading || (ativoAtual && valuation.isLoading) ? <p>Carregando valuation…</p> : null}
      {!ativos.isLoading && !ativos.data?.length && <p>Digite um ticker para iniciar a análise.</p>}

      {detalhe && (
        <>
          <div className="valuation-resumo">
            <div className="painel">
              <span className="sutil">Cotação atual <AjudaIndicador titulo="Cotação atual" texto="Última cotação disponível para o ativo na moeda apresentada." /></span>
              <strong>{moeda(detalhe.cotacao, detalhe.moeda)}</strong>
            </div>
            <div className="painel">
              <span className="sutil">Mediana dos modelos disponíveis <AjudaIndicador titulo="Mediana dos modelos" texto="Mediana dos preços justos dos modelos calculáveis com os dados e premissas disponíveis; não é recomendação nem preço-alvo." /></span>
              <strong>{moeda(detalhe.analise.preco_mediano, detalhe.moeda)}</strong>
            </div>
            <div className="painel">
              <span className="sutil">Diferença para a mediana <AjudaIndicador titulo="Diferença para a mediana" texto="Mediana dos preços justos dividida pela cotação, menos um; apresentada em percentual." /></span>
              <strong className={classeSinal(detalhe.analise.upside_mediano)}>
                {percentual(detalhe.analise.upside_mediano)}
              </strong>
            </div>
            <div className="painel">
              <span className="sutil">Modelos calculáveis <AjudaIndicador titulo="Modelos calculáveis" texto="Quantidade de modelos com resultado disponível em relação ao total de modelos." /></span>
              <strong>
                {numero(detalhe.analise.modelos_disponiveis, 0)} / {numero(detalhe.analise.total_modelos, 0)}
              </strong>
            </div>
          </div>

          <div className="valuation-colunas">
            <form
              className="painel valuation-premissas"
              onSubmit={(evento) => {
                evento.preventDefault();
                if (ativoId) salvar.mutate({ id: Number(ativoId), premissas: criarPremissas(formulario) });
              }}
            >
              <h2>Premissas</h2>
              <p className="sutil">
                LPA, VPA e dividendo anual são estimados pela cotação e pelos múltiplos/DY publicados; ROE vem do
                fundamento mais recente. Revise esses valores e informe Ke, múltiplos-alvo e projeções de FCFE quando
                disponíveis. As premissas ficam salvas por ativo e cada cálculo salvo entra no histórico de valuations
                (último e dois anteriores). Use “Buscar premissas” para atualizar automaticamente os campos com dados
                disponíveis; os demais podem ser preenchidos manualmente.
              </p>
              <button
                type="button"
                className="valuation-salvar"
                disabled={buscarPremissas.isPending}
                onClick={() => {
                  setMensagemBusca("");
                  setAvisos([]);
                  buscarPremissas.mutate(Number(ativoId));
                }}
              >
                {buscarPremissas.isPending ? "BUSCANDO…" : "BUSCAR PREMISSAS"}
              </button>
              {mensagemBusca && <p className="sutil" role="status">{mensagemBusca}</p>}
              <div className="valuation-grupos">
                {GRUPOS_CAMPOS.map((grupo) => (
                  <section key={grupo.titulo} className="valuation-grupo">
                    <h3>{grupo.titulo}</h3>
                    <div className="valuation-campos">
                      {grupo.chaves.map((chave) => {
                        const { rotulo, unidade, passo } = CAMPOS.find((campo) => campo.chave === chave)!;
                        return (
                          <label key={chave}>
                            <span className="valuation-campo-titulo">
                              {rotulo}
                              <AjudaInfo
                                className="valuation-ajuda-premissa"
                                data-tooltip={AJUDA_PREMISSAS[chave]}
                                aria-label={`Ajuda sobre ${rotulo}: ${AJUDA_PREMISSAS[chave]}`}
                              />
                            </span>
                            <span className="valuation-unidade">{unidade}</span>
                            <input
                              type="number"
                              step={passo}
                              value={formulario[chave]}
                              onChange={(evento) =>
                                setFormulario((atual) => ({ ...atual, [chave]: evento.target.value }))
                              }
                            />
                          </label>
                        );
                      })}
                    </div>
                  </section>
                ))}
              </div>
              <button className="valuation-salvar" disabled={salvar.isPending}>
                {salvar.isPending ? "SALVANDO…" : "CALCULAR E SALVAR"}
              </button>
            </form>

            <div className="painel">
              <h2>Comparação dos modelos</h2>
              <div className="tabela-container">
                <table className="tabela valuation-modelos">
                  <thead>
                    <tr>
                      <th>Modelo</th>
                      <th className="num">Preço justo</th>
                      <th className="num">Diferença vs. cotação</th>
                    </tr>
                  </thead>
                  <tbody>
                    {detalhe.modelos.map((modelo) => (
                      <tr key={modelo.id}>
                        <td>
                          {modelo.rotulo}
                          {modelo.preco_justo === null && (
                            <div className="valuation-modelo-indisponivel">
                              <span className="etiqueta valuation-indisponivel-badge">Indisponível</span>
                              {modelo.motivo && <span className="sutil">{modelo.motivo}</span>}
                            </div>
                          )}
                        </td>
                        <td className="num">{moeda(modelo.preco_justo, detalhe.moeda)}</td>
                        <td className="num">
                          <span className={classeSinal(
                            modelo.preco_justo !== null && detalhe.cotacao
                              ? modelo.preco_justo / detalhe.cotacao - 1
                              : null,
                          )}>
                            {modelo.preco_justo !== null && detalhe.cotacao
                              ? percentual(modelo.preco_justo / detalhe.cotacao - 1)
                              : "—"}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="sutil valuation-ajuda">
                A mediana resume apenas modelos calculáveis e não representa preço-alvo ou recomendação. O motivo de
                indisponibilidade aparece junto ao modelo.
              </p>
            </div>
          </div>

          <div className="painel">
            <h2>TIR e TWR do ativo</h2>
            <div className="valuation-resumo valuation-retorno">
              <div>
                <span className="sutil">TIR anual <AjudaIndicador titulo="TIR anual do ativo" texto="Taxa interna de retorno anualizada a partir das operações, proventos líquidos e valor de mercado final em reais." /></span>
                <strong className={classeSinal(detalhe.rentabilidade.tir_aa)}>
                  {percentual(detalhe.rentabilidade.tir_aa)}
                </strong>
              </div>
              <div>
                <span className="sutil">TIR mensal equivalente <AjudaIndicador titulo="TIR mensal equivalente" texto="Taxa mensal equivalente à TIR anual, calculada por capitalização composta." /></span>
                <strong className={classeSinal(detalhe.rentabilidade.tir_am)}>
                  {percentual(detalhe.rentabilidade.tir_am)}
                </strong>
              </div>
              <div>
                <span className="sutil">TWR acumulado <AjudaIndicador titulo="TWR acumulado do ativo" texto="Composição dos retornos mensais do ativo, separando o efeito dos fluxos. Na falta de cotação mensal, usa-se o custo como aproximação." /></span>
                <strong className={classeSinal(detalhe.rentabilidade.twr_acumulado)}>
                  {percentual(detalhe.rentabilidade.twr_acumulado)}
                </strong>
              </div>
            </div>
            {detalhe.rentabilidade.meses.length ? (
              <>
                <details className="valuation-metodologia">
                  <summary>Como TIR e TWR são calculados</summary>
                  <p className="sutil valuation-ajuda">
                    Cálculos respeitam o filtro global de investidores. TIR usa operações, proventos líquidos e valor de
                    mercado final em BRL; meses sem cotação são marcados e seguem a convenção mensal do app, que usa o
                    custo como aproximação de mercado.
                  </p>
                </details>
                <div className="tabela-container">
                  <table className="tabela valuation-retorno-tabela">
                    <thead>
                      <tr>
                        <th>Mês</th>
                        <th className="num">Investido</th>
                        <th className="num">Mercado</th>
                        <th className="num">TWR mensal</th>
                        <th className="num">TWR acumulado</th>
                        <th>Cotação</th>
                      </tr>
                    </thead>
                    <tbody>
                      {detalhe.rentabilidade.meses.map((mes) => (
                        <tr key={mes.data}>
                          <td>{data(mes.data)}</td>
                          <td className="num">{moeda(mes.investido)}</td>
                          <td className="num">{moeda(mes.mercado)}</td>
                          <td className="num">
                            <span className={classeSinal(mes.twr)}>{percentual(mes.twr)}</span>
                          </td>
                          <td className="num">
                            <span className={classeSinal(mes.twr_acumulado)}>{percentual(mes.twr_acumulado)}</span>
                          </td>
                          <td>{mes.sem_cotacao ? "Sem cotação · custo" : "Cotado"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            ) : (
              <div className="valuation-sem-retorno">
                <strong>Não foi possível calcular TIR e TWR.</strong>
                <p>Não existem operações para este ativo considerando os investidores selecionados.</p>
                <details className="valuation-metodologia">
                  <summary>Como TIR e TWR são calculados</summary>
                  <p className="sutil valuation-ajuda">
                    Cálculos respeitam o filtro global de investidores. TIR usa operações, proventos líquidos e valor de
                    mercado final em BRL; meses sem cotação são marcados e seguem a convenção mensal do app, que usa o
                    custo como aproximação de mercado.
                  </p>
                </details>
              </div>
            )}
          </div>
        </>
      )}
    </section>
  );
}
