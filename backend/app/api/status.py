from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query

from ..schemas import StatusAtivoOut
from ..services import status as servico
from .deps import InvestidoresDep, SessaoDep

router = APIRouter(prefix="/status", tags=["status do ativo"])


@router.get("", response_model=StatusAtivoOut)
def consultar_status(
    sessao: SessaoDep,
    investidores: InvestidoresDep,
    escopo: Literal["ativo", "carteira", "book"],
    id_: Annotated[int, Query(alias="id", gt=0)],
    limite: Annotated[int, Query(ge=1, le=500)] = 100,
    deslocamento: Annotated[int, Query(ge=0)] = 0,
):
    try:
        return servico.consultar(sessao, escopo, id_, investidores, limite, deslocamento)
    except LookupError as erro:
        raise HTTPException(404, str(erro)) from erro
