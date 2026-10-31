from fastapi import APIRouter, HTTPException

from ..schemas import PremissasValuationIn, ValuationOut
from ..services import valuation as servico
from .deps import InvestidoresDep, SessaoDep

router = APIRouter(prefix="/valuation", tags=["valuation"])


@router.get("/{ativo_id}", response_model=ValuationOut)
def consultar_valuation(ativo_id: int, sessao: SessaoDep, investidores: InvestidoresDep):
    try:
        return servico.consultar(sessao, ativo_id, investidores)
    except LookupError as erro:
        raise HTTPException(404, str(erro)) from erro


@router.put("/{ativo_id}/premissas", response_model=ValuationOut)
def salvar_premissas(
    ativo_id: int,
    dados: PremissasValuationIn,
    sessao: SessaoDep,
    investidores: InvestidoresDep,
):
    try:
        return servico.salvar_premissas(sessao, ativo_id, dados.model_dump(), investidores)
    except LookupError as erro:
        raise HTTPException(404, str(erro)) from erro
