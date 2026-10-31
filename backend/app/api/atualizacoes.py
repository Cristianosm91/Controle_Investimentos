from datetime import date
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from ..config import settings
from ..dominio import MOEDAS
from ..providers import bcb
from ..schemas import PtaxOut, TarefaOut
from ..services import jobs

router = APIRouter(tags=["atualizações"])


@router.get("/atualizacoes", response_model=list[TarefaOut])
def listar_tarefas():
    return [
        TarefaOut(
            nome=t.nome, descricao=t.descricao, em_execucao=t.em_execucao, inicio=t.inicio, fim=t.fim,
            sucesso=t.sucesso, mensagem=t.mensagem, duracao_s=t.duracao_s, proxima=jobs.proxima_execucao(t.nome),
        )
        for t in jobs.TAREFAS.values()
    ]


@router.post("/atualizacoes/{nome}", status_code=202)
def disparar_tarefa(nome: str):
    if nome not in jobs.TAREFAS:
        raise HTTPException(404, f"Tarefa {nome} não existe")
    try:
        jobs.disparar(nome)
    except jobs.TarefaOcupada as erro:
        raise HTTPException(409, str(erro)) from erro
    return {"status": "agendada"}


@router.get("/cambio/ptax", response_model=PtaxOut)
def consultar_ptax(
    data: date,
    moeda: Annotated[str, Query(pattern="^[A-Z]{3}$")] = "USD",
    dias_uteis_antes: Annotated[int | None, Query(ge=0, le=5)] = None,
):
    if moeda not in MOEDAS:
        raise HTTPException(422, f"Moeda deve ser uma de {MOEDAS}")
    defasagem = settings.ptax_dias_uteis_antes if dias_uteis_antes is None else dias_uteis_antes
    try:
        p = bcb.ptax(moeda, data, defasagem)
    except bcb.ErroPtax as erro:
        raise HTTPException(502, str(erro)) from erro
    return PtaxOut(moeda=moeda, data_solicitada=data, data_cotacao=p.data, compra=p.compra, venda=p.venda, fonte=bcb.FONTE)
