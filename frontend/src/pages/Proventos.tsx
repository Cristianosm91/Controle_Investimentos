import { useState } from "react";
import { AcoesLinha } from "../components/AcoesLinha";
import { AgendaProventos } from "../components/AgendaProventos";
import { FormProvento } from "../components/FormLancamentos";
import { ImportarExtrato } from "../components/ImportarExtrato";
import { ListaPaginada, type ColunaLista } from "../components/ListaPaginada";
import { MatrizProventos } from "../components/MatrizProventos";
import { useDominio } from "../cadastros";
import { data, moeda } from "../formato";
import { useInvestidor } from "../InvestidorContext";
import type { Provento } from "../tipos";

export function Proventos() {
  const { filtro, investidores } = useInvestidor();
  const { data: dominio } = useDominio();
  const [edicao, setEdicao] = useState<Provento | "novo" | null>(null);
  const [aba, setAba] = useState<"lancamentos" | "matriz" | "agenda">("lancamentos");
  const [importando, setImportando] = useState(false);
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

  const abas = (
    <div className="abas">
      <button className={aba === "lancamentos" ? "aba ativa" : "aba"} onClick={() => setAba("lancamentos")}>
        Lançamentos
      </button>
      <button className={aba === "matriz" ? "aba ativa" : "aba"} onClick={() => setAba("matriz")}>
        Matriz mensal
      </button>
      <button className={aba === "agenda" ? "aba ativa" : "aba"} onClick={() => setAba("agenda")}>
        Agenda e projeção
      </button>
    </div>
  );

  return (
    <>
      {aba !== "lancamentos" ? (
        <section>
          <h1>Proventos</h1>
          {abas}
          {aba === "matriz" ? <MatrizProventos filtro={filtro} /> : <AgendaProventos />}
        </section>
      ) : (
      <ListaPaginada<Provento>
        titulo="Proventos"
        recurso="proventos"
        filtroInvestidores={filtro}
        colunas={colunas}
        chave={(p) => p.id}
        cabecalho={
          <>
            <button className="secundario" onClick={() => setImportando(true)}>
              Importar extrato B3
            </button>
            <button onClick={() => setEdicao("novo")}>+ Novo provento</button>
          </>
        }
        topo={abas}
        acoes={(p) => (
          <AcoesLinha
            recurso="proventos"
            id={p.id}
            descricao={`${dominio?.eventos_provento[p.evento] ?? p.evento} de ${p.ticker} em ${data(p.data_pagamento)}`}
            aoEditar={() => setEdicao(p)}
          />
        )}
      />
      )}
      {edicao && <FormProvento provento={edicao === "novo" ? undefined : edicao} aoFechar={() => setEdicao(null)} />}
      {importando && <ImportarExtrato aoFechar={() => setImportando(false)} />}
    </>
  );
}