import { useState } from "react";
import { AcoesLinha } from "../components/AcoesLinha";
import { FormOperacao } from "../components/FormLancamentos";
import { ImportarExtrato } from "../components/ImportarExtrato";
import { ListaPaginada, type ColunaLista } from "../components/ListaPaginada";
import { useAtivos, useDominio } from "../cadastros";
import { classeSinal, data, moeda, numero } from "../formato";
import { useInvestidor } from "../InvestidorContext";
import type { Operacao } from "../tipos";

const NOMES_CLASSES: Record<string, string> = {
  "AÇÃO": "Ações",
  BDR: "BDRs",
  ETF: "ETFs",
  FII: "FIIs",
  FIAGRO: "Fiagro",
  CRIPTO: "Criptos",
  "R.FIXA": "Renda fixa",
};

export function Operacoes() {
  const { filtro, investidores } = useInvestidor();
  const { data: dominio } = useDominio();
  const { data: ativos } = useAtivos();
  const [edicao, setEdicao] = useState<Operacao | "nova" | null>(null);
  const [importando, setImportando] = useState(false);
  const nome = (id: number) => investidores.find((i) => i.id === id)?.nome ?? id;
  const classes = [...new Set(ativos?.map((ativo) => ativo.classe) ?? [])]
    .sort()
    .map((valor) => ({
      valor,
      rotulo: NOMES_CLASSES[valor] ?? valor.charAt(0) + valor.slice(1).toLowerCase(),
    }));

  const colunas: ColunaLista<Operacao>[] = [
    { titulo: "Data", render: (o) => data(o.data) },
    { titulo: "Investidor", render: (o) => nome(o.investidor_id) },
    { titulo: "Ativo", render: (o) => <strong>{o.ticker}</strong> },
    {
      titulo: "Evento",
      render: (o) => (
        <>
          {dominio?.eventos_operacao[o.evento] ?? o.evento}
          {o.daytrade && <span className="etiqueta">day trade</span>}
        </>
      ),
    },
    { titulo: "Qtd", numerica: true, render: (o) => <span className={classeSinal(o.quantidade)}>{numero(o.quantidade, 8)}</span> },
    { titulo: "Preço", numerica: true, render: (o) => moeda(o.preco, o.moeda) },
    { titulo: "Taxas", numerica: true, render: (o) => moeda(o.taxas, o.moeda) },
    { titulo: "Total (R$)", numerica: true, render: (o) => moeda(Math.abs(o.quantidade * o.preco) * o.cambio) },
    { titulo: "Corretora", render: (o) => o.corretora ?? "—" },
    { titulo: "Obs.", render: (o) => <span className="sutil">{o.observacao}</span> },
  ];

  return (
    <>
      <ListaPaginada<Operacao>
        titulo="Operações"
        recurso="operacoes"
        filtroInvestidores={filtro}
        colunas={colunas}
        classes={classes}
        chave={(o) => o.id}
        cabecalho={
          <>
            <button className="secundario" onClick={() => setImportando(true)}>
              Importar extrato B3
            </button>
            <button onClick={() => setEdicao("nova")}>+ Nova operação</button>
          </>
        }
        acoes={(o) => (
          <AcoesLinha
            recurso="operacoes"
            id={o.id}
            descricao={`${dominio?.eventos_operacao[o.evento] ?? o.evento} de ${o.ticker} em ${data(o.data)}`}
            aoEditar={() => setEdicao(o)}
          />
        )}
      />
      {edicao && <FormOperacao operacao={edicao === "nova" ? undefined : edicao} aoFechar={() => setEdicao(null)} />}
      {importando && <ImportarExtrato aoFechar={() => setImportando(false)} />}
    </>
  );
}