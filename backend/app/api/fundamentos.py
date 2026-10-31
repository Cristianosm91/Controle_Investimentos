from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import and_, func, select

from ..models import Ativo, Fundamento
from ..providers.fundamentus import FONTES
from ..schemas import FonteFundamentosOut, FundamentoOut
from .deps import SessaoDep

router = APIRouter(prefix="/fundamentos", tags=["fundamentos"])


@router.get("/fontes", response_model=list[FonteFundamentosOut])
def listar_fontes():
    return [FonteFundamentosOut(**asdict(fonte)) for fonte in FONTES]


@router.get("", response_model=list[FundamentoOut])
def listar_fundamentos(
    sessao: SessaoDep,
    ticker: Annotated[str | None, Query(min_length=1, max_length=20)] = None,
    limite: Annotated[int, Query(ge=1, le=500)] = 200,
):
    mais_recentes = (
        select(
            Fundamento.id.label("id"),
            func.row_number().over(
                partition_by=(Fundamento.ativo_id, Fundamento.fonte),
                order_by=(Fundamento.data_ref.desc(), Fundamento.id.desc()),
            ).label("ordem"),
        )
        .subquery()
    )
    consulta = (
        select(Fundamento, Ativo.ticker, Ativo.classe)
        .join(Ativo, Ativo.id == Fundamento.ativo_id)
        .join(
            mais_recentes,
            and_(mais_recentes.c.id == Fundamento.id, mais_recentes.c.ordem == 1),
        )
        .order_by(Ativo.ticker, Fundamento.fonte)
        .limit(limite)
    )
    if ticker:
        consulta = consulta.where(Ativo.ticker == ticker.strip().upper())
    return [
        FundamentoOut(
            ticker=ativo_ticker,
            classe=classe,
            **{
                campo: getattr(fundamento, campo)
                for campo in FundamentoOut.model_fields
                if campo not in {"ticker", "classe"}
            },
        )
        for fundamento, ativo_ticker, classe in sessao.execute(consulta)
    ]
