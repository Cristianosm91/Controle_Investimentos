export interface ModeloImportacao {
  nome: string;
  rotulo: string;
}

/** Links para baixar os modelos .xlsx de importação (gerados no layout que o importador reconhece). */
export function ModelosImportacao({ modelos }: { modelos: ModeloImportacao[] }) {
  return (
    <p className="modelos-importacao">
      <span className="sutil">Não tem o arquivo? Baixe o modelo para preencher:</span>
      {modelos.map((m) => (
        <a key={m.nome} href={`/api/modelos/${m.nome}`} download>
          ⬇ {m.rotulo}
        </a>
      ))}
    </p>
  );
}
