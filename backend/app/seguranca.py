"""Proteção da API local contra páginas de outros sites abertas no navegador (CSRF e DNS rebinding).

A API só escuta em 127.0.0.1, mas o navegador do usuário alcança esse endereço a partir de qualquer site.
"""

from urllib.parse import urlsplit

from starlette.datastructures import Headers
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

METODOS_SEGUROS = frozenset({"GET", "HEAD", "OPTIONS"})
_SEC_FETCH_CONFIAVEIS = frozenset({"same-origin", "none"})


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
