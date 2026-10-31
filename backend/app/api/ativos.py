from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import exists, select
from sqlalchemy.exc import IntegrityError

from ..models import Ativo, Operacao
from ..schemas import AtivoIn, AtivoOut
from .deps import SessaoDep, obter_ou_404

router = APIRouter(prefix="/ativos", tags=["ativos"])


@router.get("", response_model=list[AtivoOut])
def listar_ativos(sessao: SessaoDep, busca: Annotated[str | None, Query(max_length=40)] = None):
    consulta = select(Ativo).order_by(Ativo.ticker)
    if busca:
        termo = f"%{busca.strip()}%"
        consulta = consulta.where(Ativo.ticker.ilike(termo) | Ativo.nome.ilike(termo))
    return sessao.scalars(consulta).all()


@router.post("", response_model=AtivoOut, status_code=201)
def criar_ativo(dados: AtivoIn, sessao: SessaoDep):
    obj = Ativo(**dados.model_dump())
    sessao.add(obj)
    try:
        sessao.commit()
    except IntegrityError:
        sessao.rollback()
        raise HTTPException(409, f"Ativo {dados.ticker} já cadastrado")
    sessao.refresh(obj)
    return obj


@router.put("/{id_}", response_model=AtivoOut)
def alterar_ativo(id_: int, dados: AtivoIn, sessao: SessaoDep):
    obj = obter_ou_404(sessao, Ativo, id_)
    for campo, valor in dados.model_dump().items():
        setattr(obj, campo, valor)
    try:
        sessao.commit()
    except IntegrityError:
        sessao.rollback()
        raise HTTPException(409, f"Ativo {dados.ticker} já cadastrado")
    return obj


@router.delete("/{id_}", status_code=204)
def excluir_ativo(id_: int, sessao: SessaoDep):
    obj = obter_ou_404(sessao, Ativo, id_)
    if sessao.scalar(select(exists().where(Operacao.ativo_id == id_))):
        raise HTTPException(409, "Ativo possui operações e não pode ser excluído")
    sessao.delete(obj)
    sessao.commit()
