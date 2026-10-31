"""Proteção da API local contra páginas de outros sites abertas no navegador (CSRF, DNS rebinding e clickjacking).

A API só escuta em 127.0.0.1, mas o navegador do usuário alcança esse endereço a partir de qualquer site.
"""

import io
import zipfile
from urllib.parse import urlsplit

from starlette.datastructures import Headers, MutableHeaders
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

METODOS_SEGUROS = frozenset({"GET", "HEAD", "OPTIONS"})
_SEC_FETCH_CONFIAVEIS = frozenset({"same-origin", "none"})

# Teto do conteúdo expandido de planilhas enviadas e de linhas lidas (relatórios reais ficam muito abaixo).
DESCOMPACTADO_MAXIMO = 200 * 1024 * 1024
LINHAS_MAXIMAS = 100_000

CABECALHOS_SEGURANCA = {
    "X-Frame-Options": "DENY",
    "Content-Security-Policy": "frame-ancestors 'none'; object-src 'none'; base-uri 'self'",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "Cross-Origin-Resource-Policy": "same-origin",
}


class CabecalhosSegurancaMiddleware:
    """Impede que outros sites enquadrem a interface (clickjacking) ou embutam respostas da API."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def enviar(mensagem: Message) -> None:
            if mensagem["type"] == "http.response.start":
                cabecalhos = MutableHeaders(scope=mensagem)
                for nome, valor in CABECALHOS_SEGURANCA.items():
                    cabecalhos.setdefault(nome, valor)
            await send(mensagem)

        await self.app(scope, receive, enviar)


def tamanho_descompactado_excedido(conteudo: bytes, limite: int = DESCOMPACTADO_MAXIMO) -> bool:
    """True se o ZIP (ex.: .xlsx) expandiria além do limite — evita bombas de descompressão."""
    with zipfile.ZipFile(io.BytesIO(conteudo)) as arquivo:
        return sum(info.file_size for info in arquivo.infolist()) > limite


class OrigemLocalMiddleware:
    """Recusa (403) escritas cuja origem declarada pelo navegador não é um dos hosts permitidos.

    Clientes fora do navegador (scripts, testes) não enviam `Origin` nem `Sec-Fetch-Site` e continuam aceitos.
    Qualquer porta do host é aceita, para cobrir o Vite (`:5173`) e portas alternativas da API.
    """

    def __init__(self, app: ASGIApp, hosts_permitidos: list[str]) -> None:
        self.app = app
        self.hosts = {h.lower() for h in hosts_permitidos}

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and scope["method"] not in METODOS_SEGUROS and not self._permitida(scope):
            resposta = JSONResponse({"detail": "Origem da requisição não permitida"}, status_code=403)
            await resposta(scope, receive, send)
            return
        await self.app(scope, receive, send)

    def _permitida(self, scope: Scope) -> bool:
        cabecalhos = Headers(scope=scope)
        origem = cabecalhos.get("origin")
        if origem is None:
            site = cabecalhos.get("sec-fetch-site")
            return site is None or site in _SEC_FETCH_CONFIAVEIS
        # "null" (iframe em sandbox, redirecionamentos) não tem hostname e é recusado.
        return (urlsplit(origem).hostname or "") in self.hosts
