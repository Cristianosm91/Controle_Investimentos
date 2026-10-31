import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState, type FormEvent } from "react";
import { api } from "../../api";
import { invalidarDerivados, useParametros } from "../../cadastros";
import type { Parametros as TParametros } from "../../tipos";
import { CampoData } from "../CampoData";

const PADRAO: TParametros = {
  caixa_data_inicio: null,
  caixa_no_portfolio: false,
  ir_ano_inicio: null,
  ir_bdr_como_acao: false,
  ir_daytrade_no_limite: false,
  ir_opcoes_no_limite: false,
  ir_outras_classes_no_limite: false,
  ir_subscricao_fii_isenta: false,
  alerta_desvio_pp: 5,
  alerta_vencimento_dias: 30,
  alerta_cotacao_dias: 5,
};

const inteiro = (texto: string) => (texto === "" ? null : Math.round(Number(texto)));

export function Parametros() {
  const { data } = useParametros();
  const cliente = useQueryClient();
  const [form, setForm] = useState<TParametros>(PADRAO);
  const [salvo, setSalvo] = useState(false);

  useEffect(() => {
    if (data) setForm(data);
  }, [data]);

  const salvar = useMutation({
    mutationFn: (p: TParametros) => api.put<TParametros>("/parametros", p),
    onSuccess: (p) => {
      cliente.setQueryData(["parametros"], p);
      invalidarDerivados(cliente);
      setSalvo(true);
    },
  });

  const enviar = (e: FormEvent) => {
    e.preventDefault();
    setSalvo(false);
    salvar.mutate(form);
  };

  return (
    <>
      <h2>Parâmetros</h2>
      {salvar.error && <div className="erro">{(salvar.error as Error).message}</div>}
      {salvo && <div className="aviso">Parâmetros salvos.</div>}
      <form className="formulario" onSubmit={enviar}>
        <h3>Caixa</h3>
        <label>
          Integrar lançamentos ao caixa a partir de
          <CampoData
            valor={form.caixa_data_inicio ?? ""}
            aoMudar={(v) => setForm({ ...form, caixa_data_inicio: v || null })}
          />
          <small className="sutil">
            Desta data em diante, compras, vendas, amortizações e proventos líquidos movimentam o saldo da corretora. Em branco = só as
            movimentações lançadas na tela Caixa. Lance o saldo inicial como aporte nessa data.
          </small>
        </label>
        <label className="check">
          <input
            type="checkbox"
            checked={form.caixa_no_portfolio}
            onChange={(e) => setForm({ ...form, caixa_no_portfolio: e.target.checked })}
          />
          Somar o saldo em caixa ao patrimônio do Portfólio
        </label>
        <h3>Alertas</h3>
        <label>
          Desvio da alocação (p.p.)
          <input
            type="number"
            min={1}
            max={100}
            value={form.alerta_desvio_pp ?? ""}
            onChange={(e) => setForm({ ...form, alerta_desvio_pp: inteiro(e.target.value) })}
          />
          <small className="sutil">Avisa quando o peso de um book se afasta do alvo por mais que isso.</small>
        </label>
        <label>
          Vencimento de renda fixa (dias)
          <input
            type="number"
            min={1}
            max={365}
            value={form.alerta_vencimento_dias ?? ""}
            onChange={(e) => setForm({ ...form, alerta_vencimento_dias: inteiro(e.target.value) })}
          />
          <small className="sutil">Antecedência do aviso de vencimento.</small>
        </label>
        <label>
          Cotação desatualizada (dias)
          <input
            type="number"
            min={1}
            max={60}
            value={form.alerta_cotacao_dias ?? ""}
            onChange={(e) => setForm({ ...form, alerta_cotacao_dias: inteiro(e.target.value) })}
          />
          <small className="sutil">Em branco desliga o alerta correspondente.</small>
        </label>
        <div className="acoes largura-total">
          <button type="submit" disabled={salvar.isPending}>
            Salvar
          </button>
        </div>
      </form>
      <p className="sutil">
        Câmbio dos lançamentos no exterior: PTAX de venda da data (Lei 14.754/2023), definido em <code>.env</code>{" "}
        (<code>INVESTHUB_PTAX_DIAS_UTEIS_ANTES</code>). Parâmetros de IR ficam em Configurações → Imposto de renda.
      </p>
    </>
  );
}
