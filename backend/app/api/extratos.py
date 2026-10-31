from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.concurrency import run_in_threadpool

from ..models import Investidor
from ..schemas import PreviaExtratoOut, ResultadoExtratoOut
from ..services import extrato_b3
from .deps import SessaoDep, ler_corpo, nome_arquivo, obter_ou_404

router = APIRouter(tags=["extratos"])

InvestidorId = Annotated[int, Query(ge=1, description="Extrato da B3 é de um CPF: informe um único investidor")]


def _incluir(texto: str | None) -> set[int]:
    if not texto:
        return set()
    try:
        return {int(n) for n in texto.split(",") if n.strip()}
    except ValueError:
        raise HTTPException(422, "Parâmetro 'incluir' deve conter números de linha separados por vírgula") from None


@router.post("/extratos/b3/previa", response_model=PreviaExtratoOut)
async def previa_extrato(request: Request, sessao: SessaoDep, investidor_id: InvestidorId):
    obter_ou_404(sessao, Investidor, investidor_id)
    conteudo = await ler_corpo(request, extrato_b3.TAMANHO_MAXIMO)
    try:
        previa = await run_in_threadpool(extrato_b3.analisar, sessao, investidor_id, conteudo)
    except extrato_b3.ExtratoInvalido as erro:
        raise HTTPException(422, str(erro)) from erro
    return PreviaExtratoOut(
        relatorio=previa.relatorio, linhas=[asdict(linha) for linha in previa.linhas],
        ativos_novos=previa.ativos_novos, corretoras_novas=previa.corretoras_novas,
    )


@router.post("/extratos/b3/importar", response_model=ResultadoExtratoOut)
async def importar_extrato(
    request: Request, sessao: SessaoDep, investidor_id: InvestidorId, incluir: str | None = None,
):
    obter_ou_404(sessao, Investidor, investidor_id)
    linhas = _incluir(incluir)
    conteudo = await ler_corpo(request, extrato_b3.TAMANHO_MAXIMO)
    try:
        resultado = await run_in_threadpool(
            extrato_b3.importar, sessao, investidor_id, conteudo, linhas, nome_arquivo(request)
        )
    except extrato_b3.ExtratoInvalido as erro:
        raise HTTPException(422, str(erro)) from erro
    return ResultadoExtratoOut(**asdict(resultado))
