export class ErroApi extends Error {
  constructor(
    public status: number,
    mensagem: string,
    /** Código do erro inesperado (500) para cruzar com o log do servidor. */
    public erroId?: string,
  ) {
    super(mensagem);
  }
}

async function requisitar<T>(metodo: string, caminho: string, corpo?: unknown, arquivo?: File): Promise<T> {
  const resposta = await fetch(`/api${caminho}`, {
    method: metodo,
    headers: arquivo
      ? { "Content-Type": "application/octet-stream", "X-Nome-Arquivo": encodeURIComponent(arquivo.name) }
      : corpo === undefined
        ? undefined
        : { "Content-Type": "application/json" },
    body: arquivo ?? (corpo === undefined ? undefined : JSON.stringify(corpo)),
  });
  if (!resposta.ok) {
    let mensagem = resposta.statusText;
    let erroId: string | undefined;
    const texto = await resposta.text().catch(() => "");
    try {
      const json = JSON.parse(texto);
      mensagem = typeof json.detail === "string" ? json.detail : (json.detail?.[0]?.msg ?? mensagem);
      if (typeof json.erro_id === "string") {
        erroId = json.erro_id;
        mensagem = `${mensagem} (código do erro: ${erroId})`;
      }
    } catch {
      // corpo não-JSON: usa o texto curto devolvido ou o statusText
      if (texto.trim() && texto.length <= 300) mensagem = texto.trim();
    }
    throw new ErroApi(resposta.status, mensagem || `Erro ${resposta.status}`, erroId);
  }
  return resposta.status === 204 ? (undefined as T) : resposta.json();
}

export const api = {
  get: <T>(caminho: string) => requisitar<T>("GET", caminho),
  post: <T>(caminho: string, corpo?: unknown) => requisitar<T>("POST", caminho, corpo ?? {}),
  put: <T>(caminho: string, corpo: unknown) => requisitar<T>("PUT", caminho, corpo),
  patch: <T>(caminho: string, corpo: unknown) => requisitar<T>("PATCH", caminho, corpo),
  del: (caminho: string) => requisitar<void>("DELETE", caminho),
  enviar: <T>(caminho: string, arquivo: File) => requisitar<T>("POST", caminho, undefined, arquivo),
};

export function query(params: Record<string, string | number | boolean | null | undefined>): string {
  const p = new URLSearchParams();
  for (const [chave, valor] of Object.entries(params)) {
    if (valor !== null && valor !== undefined && valor !== "") p.set(chave, String(valor));
  }
  const s = p.toString();
  return s ? `?${s}` : "";
}
