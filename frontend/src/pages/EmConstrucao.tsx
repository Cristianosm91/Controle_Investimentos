export function EmConstrucao({ titulo, fase }: { titulo: string; fase?: number }) {
  return (
    <section>
      <h1>{titulo}</h1>
      {fase !== undefined && (
        <div className="aviso">
          Página prevista para a <strong>Fase {fase}</strong> do plano de desenvolvimento.
        </div>
      )}
    </section>
  );
}
