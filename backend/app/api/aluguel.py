from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.concurrency import run_in_threadpool

from ..models import Investidor
from ..schemas import ItemAluguelOut, ResultadoAluguelOut, ResumoAluguelOut
from ..services import aluguel
from .deps import InvestidoresDep, SessaoDep, ler_corpo, nome_arquivo, obter_ou_404

router = APIRouter(tags=["aluguel (BTC)"])

InvestidorId = Annotated[int, Query(ge=1)]


@router.get("/aluguel", response_model=ResumoAluguelOut)
def resumo_aluguel(
    sessao: SessaoDep, investidores: InvestidoresDep, ano: Annotated[int | None, Query(ge=2000, le=2100)] = None,
    classe: Annotated[str | None, Query(max_length=30)] = None,
    classes_excluidas: Annotated[str | None, Query(max_length=2_000)] = None,
):
    excluidas = [c.strip() for c in (classes_excluidas or "").split(",") if c.strip()]
    return aluguel.resumo(sessao, investidores, ano, classe, excluidas)


@router.post("/aluguel/extrato/previa", response_model=list[ItemAluguelOut])
async def previa_aluguel(request: Request, sessao: SessaoDep, investidor_id: InvestidorId):
    await run_in_threadpool(obter_ou_404, sessao, Investidor, investidor_id)
    conteudo = await ler_corpo(request, aluguel.TAMANHO_MAXIMO)
    try:
        itens = await run_in_threadpool(aluguel.analisar, sessao, investidor_id, conteudo)
    except aluguel.ExtratoInvalido as erro:
        raise HTTPException(422, str(erro)) from erro
    return [asdict(i) for i in itens]


@router.post("/aluguel/extrato/importar", response_model=ResultadoAluguelOut)
async def importar_aluguel(
    request: Request, sessao: SessaoDep, investidor_id: InvestidorId,
    incluir: Annotated[str | None, Query(max_length=20_000)] = None,
):
    await run_in_threadpool(obter_ou_404, sessao, Investidor, investidor_id)
    conteudo = await ler_corpo(request, aluguel.TAMANHO_MAXIMO)
    hashes = {h for h in (incluir or "").split(",") if h.strip()}
    try:
        gravados, lote_id = await run_in_threadpool(
            aluguel.importar, sessao, investidor_id, conteudo, hashes, nome_arquivo(request)
        )
    except aluguel.ExtratoInvalido as erro:
        raise HTTPException(422, str(erro)) from erro
    return ResultadoAluguelOut(gravados=gravados, lote_id=lote_id)
