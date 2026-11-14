import { Component, type ErrorInfo, type ReactNode } from "react";

interface Props {
  children: ReactNode;
}

interface Estado {
  erro: Error | null;
}

/** Captura erros de renderização de uma página e mostra uma mensagem amigável no lugar dela (o menu continua). */
export class LimiteErro extends Component<Props, Estado> {
  state: Estado = { erro: null };

  static getDerivedStateFromError(erro: Error): Estado {
    return { erro };
  }

  componentDidCatch(erro: Error, info: ErrorInfo) {
    console.error("Erro ao exibir a página:", erro, info.componentStack);
  }

  render() {
    const { erro } = this.state;
    if (!erro) return this.props.children;
    return (
      <section className="erro-pagina" role="alert">
        <h1>Não foi possível exibir esta página</h1>
        <p>
          Ocorreu um erro inesperado ao montar a tela. Recarregue a página para tentar novamente; se o problema
          continuar, use o menu para abrir outra página.
        </p>
        <p>
          <button type="button" onClick={() => window.location.reload()}>
            Recarregar
          </button>
        </p>
        <details>
          <summary>Detalhes técnicos do erro</summary>
          <pre>
            {erro.name}: {erro.message}
            {erro.stack ? `\n\n${erro.stack}` : ""}
          </pre>
        </details>
      </section>
    );
  }
}
