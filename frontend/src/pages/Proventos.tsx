import { useState } from "react";
import { AcoesLinha } from "../components/AcoesLinha";
import { FormProvento } from "../components/FormLancamentos";
import { ListaPaginada, type ColunaLista } from "../components/ListaPaginada";
import { useDominio } from "../cadastros";
import { data, moeda } from "../formato";
import { useInvestidor } from "../InvestidorContext";
import type { Provento } from "../tipos";

export function Proventos() {
  const { filtro, investidores } = useInvestidor();
  const { data: dominio } = useDominio();
  const [edicao, setEdicao] = useState<Provento | "novo" | null>(null);
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
    <>
      <ListaPaginada<Provento>
        titulo="Proventos"
        recurso="proventos"
        filtroInvestidores={filtro}
        colunas={colunas}
        chave={(p) => p.id}
        cabecalho={<button onClick={() => setEdicao("novo")}>+ Novo provento</button>}
        acoes={(p) => (
          <AcoesLinha
            recurso="proventos"
            id={p.id}
            descricao={`${dominio?.eventos_provento[p.evento] ?? p.evento} de ${p.ticker} em ${data(p.data_pagamento)}`}
            aoEditar={() => setEdicao(p)}
          />
        )}
      />
      {edicao && <FormProvento provento={edicao === "novo" ? undefined : edicao} aoFechar={() => setEdicao(null)} />}
    </>
  );
}