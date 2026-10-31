from typing import Annotated
from urllib.parse import unquote

from fastapi import Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from ..db import get_session

SessaoDep = Annotated[Session, Depends(get_session)]


def filtro_investidores(
    investidores: Annotated[str | None, Query(description="IDs separados por vírgula; vazio = todos")] = None,
) -> list[int] | None:
    if not investidores:
        return None
    try:
        return [int(i) for i in investidores.split(",") if i.strip()]
    except ValueError:
        raise HTTPException(422, "Parâmetro 'investidores' deve conter IDs numéricos separados por vírgula") from None


InvestidoresDep = Annotated[list[int] | None, Depends(filtro_investidores)]


def nome_arquivo(request: Request) -> str | None:
    """Nome original do arquivo enviado pelo front (cabeçalho X-Nome-Arquivo, codificado como URI)."""
    valor = request.headers.get("x-nome-arquivo")
    return unquote(valor)[:200] if valor else None


def obter_ou_404(sessao: Session, modelo, id_: int):
    obj = sessao.get(modelo, id_)
    if obj is None:
        raise HTTPException(404, f"{modelo.__name__} {id_} não encontrado")
    return obj


async def ler_corpo(request: Request, limite: int) -> bytes:
    """Lê o corpo bruto (upload de arquivo) recusando o que passar do limite antes de carregar tudo."""
    declarado = request.headers.get("content-length")
    mensagem = f"Arquivo maior que {limite // (1024 * 1024)} MB"
    if declarado and declarado.isdigit() and int(declarado) > limite:
        raise HTTPException(413, mensagem)
    partes, recebido = [], 0
    async for bloco in request.stream():
        recebido += len(bloco)
        if recebido > limite:
            raise HTTPException(413, mensagem)
        partes.append(bloco)
    if not recebido:
        raise HTTPException(422, "Arquivo vazio")
    return b"".join(partes)
