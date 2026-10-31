import { useState } from "react";
import { AcoesLinha } from "../components/AcoesLinha";
import { FormCaixa } from "../components/FormLancamentos";
import { ListaPaginada, type ColunaLista } from "../components/ListaPaginada";
import { useDominio } from "../cadastros";
import { classeSinal, data, moeda } from "../formato";
import { useInvestidor } from "../InvestidorContext";
import type { MovCaixa } from "../tipos";

export function Caixa() {
  const { filtro, investidores } = useInvestidor();
  const { data: dominio } = useDominio();
  const [edicao, setEdicao] = useState<MovCaixa | "nova" | null>(null);
  const nome = (id: number) => investidores.find((i) => i.id === id)?.nome ?? id;

  const colunas: ColunaLista<MovCaixa>[] = [
    { titulo: "Data", render: (m) => data(m.data) },
    { titulo: "Investidor", render: (m) => nome(m.investidor_id) },
    { titulo: "Evento", render: (m) => dominio?.eventos_caixa[m.evento] ?? m.evento },
    { titulo: "Valor", numerica: true, render: (m) => <span className={classeSinal(m.valor)}>{moeda(m.valor, m.moeda)}</span> },
    { titulo: "Corretora", render: (m) => m.corretora ?? "—" },
    { titulo: "Obs.", render: (m) => <span className="sutil">{m.observacao}</span> },
  ];

  return (
    <>
      <ListaPaginada<MovCaixa>
        titulo="Caixa"
        recurso="caixa"
        filtroInvestidores={filtro}
        filtroTicker={false}
        colunas={colunas}
        chave={(m) => m.id}
        cabecalho={<button onClick={() => setEdicao("nova")}>+ Nova movimentação</button>}
        acoes={(m) => (
          <AcoesLinha
            recurso="caixa"
            id={m.id}
            descricao={`${dominio?.eventos_caixa[m.evento] ?? m.evento} de ${moeda(m.valor, m.moeda)} em ${data(m.data)}`}
            aoEditar={() => setEdicao(m)}
          />
        )}
      />
      <p className="sutil">Saldo por corretora e integração ao portfólio: Fase 3.</p>
      {edicao && <FormCaixa mov={edicao === "nova" ? undefined : edicao} aoFechar={() => setEdicao(null)} />}
    </>
  );
}