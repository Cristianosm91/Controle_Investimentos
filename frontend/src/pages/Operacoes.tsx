import { useQuery } from "@tanstack/react-query";
import { api } from "../api";
import { ListaPaginada, type ColunaLista } from "../components/ListaPaginada";
import { classeSinal, data, moeda, numero } from "../formato";
import { useInvestidor } from "../InvestidorContext";
import type { Dominio, Operacao } from "../tipos";

export function Operacoes() {
  const { filtro, investidores } = useInvestidor();
  const { data: dominio } = useQuery({ queryKey: ["dominio"], queryFn: () => api.get<Dominio>("/dominio") });
  const nome = (id: number) => investidores.find((i) => i.id === id)?.nome ?? id;

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
    <ListaPaginada<Operacao>
      titulo="Operações"
      recurso="operacoes"
      filtroInvestidores={filtro}
      colunas={colunas}
      chave={(o) => o.id}
    />
  );
}
