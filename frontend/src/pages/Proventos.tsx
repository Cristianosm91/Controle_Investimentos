import { useQuery } from "@tanstack/react-query";
import { api } from "../api";
import { ListaPaginada, type ColunaLista } from "../components/ListaPaginada";
import { data, moeda } from "../formato";
import { useInvestidor } from "../InvestidorContext";
import type { Dominio, Provento } from "../tipos";

export function Proventos() {
  const { filtro, investidores } = useInvestidor();
  const { data: dominio } = useQuery({ queryKey: ["dominio"], queryFn: () => api.get<Dominio>("/dominio") });
  const nome = (id: number) => investidores.find((i) => i.id === id)?.nome ?? id;

  const colunas: ColunaLista<Provento>[] = [
    { titulo: "Pagamento", render: (p) => data(p.data_pagamento) },
    { titulo: "Data com", render: (p) => data(p.data_com) },
    { titulo: "Investidor", render: (p) => nome(p.investidor_id) },
    { titulo: "Ativo", render: (p) => <strong>{p.ticker}</strong> },
    { titulo: "Evento", render: (p) => dominio?.eventos_provento[p.evento] ?? p.evento },
    { titulo: "Bruto", numerica: true, render: (p) => moeda(p.valor, p.moeda) },
    { titulo: "IRRF", numerica: true, render: (p) => moeda(p.irrf, p.moeda) },
    { titulo: "Líquido (R$)", numerica: true, render: (p) => moeda((p.valor - p.irrf - p.taxas) * p.cambio) },
    { titulo: "Corretora", render: (p) => p.corretora ?? "—" },
  ];

  return (
    <ListaPaginada<Provento>
      titulo="Proventos"
      recurso="proventos"
      filtroInvestidores={filtro}
      colunas={colunas}
      chave={(p) => p.id}
    />
  );
}
