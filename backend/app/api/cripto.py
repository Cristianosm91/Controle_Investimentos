from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy.exc import IntegrityError

from ..models import Ativo
from ..providers import cripto as provedor
from ..schemas import (
    AtivoOut,
    CriptoIn,
    MoedaCriptoOut,
    MonitorCriptoOut,
    PainelCriptoOut,
    PontoCriptoOut,
)
from ..services import cripto, jobs
from .deps import InvestidoresDep, SessaoDep, obter_ou_404

router = APIRouter(prefix="/cripto", tags=["cripto"])


@router.get("", response_model=PainelCriptoOut)
def painel(sessao: SessaoDep, investidores: InvestidoresDep):
    return cripto.painel(sessao, investidores)


@router.get("/catalogo", response_model=list[MoedaCriptoOut])
def catalogo(busca: Annotated[str, Query(min_length=2, max_length=80)]):
    try:
        return [MoedaCriptoOut(id=m.id, ticker=m.symbol.upper(), nome=m.name) for m in provedor.buscar(busca)]
    except provedor.ErroCripto as erro:
        raise HTTPException(502, str(erro)) from erro


@router.post("/ativos", response_model=AtivoOut, status_code=201)
def adicionar(dados: CriptoIn, sessao: SessaoDep):
    mercados, avisos = provedor.mercados([dados.coingecko_id])
    mercado = mercados.get(dados.coingecko_id)
    if mercado is None or mercado.fonte != "CoinGecko":
        raise HTTPException(502, "Não foi possível confirmar a identidade no CoinGecko: " + "; ".join(avisos))
    if dados.ativo_id is not None:
        ativo = obter_ou_404(sessao, Ativo, dados.ativo_id)
        if ativo.classe != "CRIPTO" or ativo.coingecko_id is not None:
            raise HTTPException(409, "Só é possível vincular um ativo CRIPTO ainda sem ID CoinGecko")
    else:
        ativo = Ativo(ticker=dados.ticker.upper(), nome=mercado.name[:120], classe="CRIPTO", moeda="USD", mercado=None)
        sessao.add(ativo)
    ativo.coingecko_id = dados.coingecko_id
    try:
        sessao.commit()
    except IntegrityError as erro:
        sessao.rollback()
        raise HTTPException(
            409, "Ticker ou ID CoinGecko já cadastrado; escolha outro ticker ou vincule o ativo existente",
        ) from erro
    sessao.refresh(ativo)
    return ativo


@router.post("/atualizar")
def atualizar():
    try:
        resultado = jobs.executar("cripto")
    except jobs.TarefaOcupada as erro:
        raise HTTPException(409, str(erro)) from erro
    return {"atualizados": resultado.atualizados, "avisos": resultado.avisos}


@router.get("/monitor", response_model=MonitorCriptoOut)
def monitor(
    ano: Annotated[int, Query(ge=1990, le=2099)], sessao: SessaoDep, investidores: InvestidoresDep,
):
    return cripto.monitor(sessao, investidores, ano)


@router.get("/{ativo_id}/historico", response_model=list[PontoCriptoOut])
def historico(
    ativo_id: int, sessao: SessaoDep, dias: Annotated[int, Query(ge=1, le=90)] = 30,
):
    ativo = obter_ou_404(sessao, Ativo, ativo_id)
    if ativo.classe != "CRIPTO" or ativo.coingecko_id is None:
        raise HTTPException(422, "Ativo CRIPTO precisa de ID CoinGecko para consultar o histórico")
    try:
        return [
            PontoCriptoOut(instante=instante, preco_usd=preco)
            for instante, preco in provedor.historico(ativo.coingecko_id, dias)
        ]
    except provedor.ErroCripto as erro:
        raise HTTPException(502, str(erro)) from erro
