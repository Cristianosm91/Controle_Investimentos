from fastapi import APIRouter, HTTPException, Response

from ..schemas import (
    HistoricoValuationOut,
    PremissasValuationIn,
    ValuationAtivoIn,
    ValuationAtivoOut,
    ValuationOut,
)
from ..services import valuation as servico
from .deps import InvestidoresDep, SessaoDep

router = APIRouter(prefix="/valuation", tags=["valuation"])


@router.post("/ativo", response_model=ValuationAtivoOut)
def preparar_ativo(dados: ValuationAtivoIn, sessao: SessaoDep):
    """Seleciona qualquer ticker digitado, cadastrando-o como ativo B3 se ainda não existir."""
    return servico.preparar_ativo(sessao, dados.ticker, dados.classe)


@router.get("/historico", response_model=list[HistoricoValuationOut])
def listar_historico(sessao: SessaoDep):
    return servico.historico(sessao)


@router.delete("/{ativo_id}/historico", status_code=204)
def remover_historico(ativo_id: int, sessao: SessaoDep):
    servico.remover_historico(sessao, ativo_id)
    return Response(status_code=204)


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
