from dataclasses import asdict
import json
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


def _correcoes(texto: str | None) -> dict[int, dict[str, str]]:
    if not texto:
        return {}
    if len(texto) > 30_000:
        raise HTTPException(422, "Correções de linhas excedem o limite permitido")
    try:
        bruto = json.loads(texto)
    except json.JSONDecodeError:
        raise HTTPException(422, "Correções de linhas inválidas") from None
    campos_validos = {"ticker", "data", "evento", "quantidade", "preco", "taxas", "instituicao", "irrf", "moeda"}
    if not isinstance(bruto, dict):
        raise HTTPException(422, "Correções de linhas inválidas")
    resultado = {}
    for numero, campos in bruto.items():
        if not str(numero).isdigit() or int(numero) < 1 or not isinstance(campos, dict):
            raise HTTPException(422, "Correções de linhas inválidas")
        if not campos or set(campos) - campos_validos or any(not isinstance(valor, str) for valor in campos.values()):
            raise HTTPException(422, "Campos de correção inválidos")
        if any(len(valor) > 200 for valor in campos.values()):
            raise HTTPException(422, "Valor de correção excede o limite permitido")
        resultado[int(numero)] = campos
    return resultado


@router.post("/extratos/b3/previa", response_model=PreviaExtratoOut)
async def previa_extrato(
    request: Request, sessao: SessaoDep, investidor_id: InvestidorId, correcoes: str | None = None,
):
    await run_in_threadpool(obter_ou_404, sessao, Investidor, investidor_id)
    conteudo = await ler_corpo(request, extrato_b3.TAMANHO_MAXIMO)
    try:
        previa = await run_in_threadpool(extrato_b3.analisar, sessao, investidor_id, conteudo, _correcoes(correcoes))
    except extrato_b3.ExtratoInvalido as erro:
        raise HTTPException(422, str(erro)) from erro
    return PreviaExtratoOut(
        relatorio=previa.relatorio, linhas=[asdict(linha) for linha in previa.linhas],
        ativos_novos=previa.ativos_novos, corretoras_novas=previa.corretoras_novas,
    )


@router.post("/extratos/b3/importar", response_model=ResultadoExtratoOut)
async def importar_extrato(
    request: Request, sessao: SessaoDep, investidor_id: InvestidorId, incluir: str | None = None,
    correcoes: str | None = None,
):
    await run_in_threadpool(obter_ou_404, sessao, Investidor, investidor_id)
    linhas = _incluir(incluir)
    conteudo = await ler_corpo(request, extrato_b3.TAMANHO_MAXIMO)
    try:
        resultado = await run_in_threadpool(
            extrato_b3.importar, sessao, investidor_id, conteudo, linhas, nome_arquivo(request), _correcoes(correcoes)
        )
    except extrato_b3.ExtratoInvalido as erro:
        raise HTTPException(422, str(erro)) from erro
    return ResultadoExtratoOut(**asdict(resultado))
