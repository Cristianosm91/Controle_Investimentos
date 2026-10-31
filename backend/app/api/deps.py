from typing import Annotated

from fastapi import Depends, HTTPException, Query
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
        raise HTTPException(422, "Parâmetro 'investidores' deve conter IDs numéricos separados por vírgula")


InvestidoresDep = Annotated[list[int] | None, Depends(filtro_investidores)]


def obter_ou_404(sessao: Session, modelo, id_: int):
    obj = sessao.get(modelo, id_)
    if obj is None:
        raise HTTPException(404, f"{modelo.__name__} {id_} não encontrado")
    return obj
