from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import func, select
from sqlalchemy.orm import joinedload

from ..models import Ativo, Investidor, Operacao, Provento
from ..schemas import OperacaoIn, OperacaoOut, Pagina, ProventoIn, ProventoOut
from .deps import InvestidoresDep, SessaoDep, obter_ou_404

router = APIRouter(tags=["lançamentos"])

Limite = Annotated[int, Query(ge=1, le=1000)]
Deslocamento = Annotated[int, Query(ge=0)]


def _filtrar(consulta, modelo, campo_data, investidores, ticker, inicio, fim):
    if investidores:
        consulta = consulta.where(modelo.investidor_id.in_(investidores))
    if ticker:
        consulta = consulta.join(Ativo, Ativo.id == modelo.ativo_id).where(Ativo.ticker == ticker.strip().upper())
    if inicio:
        consulta = consulta.where(campo_data >= inicio)
    if fim:
        consulta = consulta.where(campo_data <= fim)
    return consulta


def _saida(obj: Operacao | Provento, schema):
    dados = {c: getattr(obj, c) for c in schema.model_fields if c not in ("ticker", "corretora")}
    return schema.model_validate(
        {**dados, "ticker": obj.ativo.ticker, "corretora": obj.corretora.nome if obj.corretora else None}
    )


def _operacao_out(o: Operacao) -> OperacaoOut:
    return _saida(o, OperacaoOut)


def _provento_out(p: Provento) -> ProventoOut:
    return _saida(p, ProventoOut)


def _validar_refs(sessao, dados) -> None:
    obter_ou_404(sessao, Investidor, dados.investidor_id)
    obter_ou_404(sessao, Ativo, dados.ativo_id)


# ---------- Operações ----------

@router.get("/operacoes", response_model=Pagina[OperacaoOut])
def listar_operacoes(
    sessao: SessaoDep,
    investidores: InvestidoresDep,
    ticker: str | None = None,
    inicio: date | None = None,
    fim: date | None = None,
    limite: Limite = 200,
    deslocamento: Deslocamento = 0,
):
    base = _filtrar(select(Operacao), Operacao, Operacao.data, investidores, ticker, inicio, fim)
    total = sessao.scalar(select(func.count()).select_from(base.subquery()))
    itens = sessao.scalars(
        base.options(joinedload(Operacao.ativo), joinedload(Operacao.corretora))
        .order_by(Operacao.data.desc(), Operacao.id.desc())
        .limit(limite)
        .offset(deslocamento)
    ).all()
    return Pagina[OperacaoOut](total=total or 0, itens=[_operacao_out(o) for o in itens])


@router.post("/operacoes", response_model=OperacaoOut, status_code=201)
def criar_operacao(dados: OperacaoIn, sessao: SessaoDep):
    _validar_refs(sessao, dados)
    obj = Operacao(**dados.model_dump(), origem="manual")
    sessao.add(obj)
    sessao.commit()
    sessao.refresh(obj)
    return _operacao_out(obj)


@router.put("/operacoes/{id_}", response_model=OperacaoOut)
def alterar_operacao(id_: int, dados: OperacaoIn, sessao: SessaoDep):
    obj = obter_ou_404(sessao, Operacao, id_)
    _validar_refs(sessao, dados)
    for campo, valor in dados.model_dump().items():
        setattr(obj, campo, valor)
    sessao.commit()
    sessao.refresh(obj)
    return _operacao_out(obj)


@router.delete("/operacoes/{id_}", status_code=204)
def excluir_operacao(id_: int, sessao: SessaoDep):
    sessao.delete(obter_ou_404(sessao, Operacao, id_))
    sessao.commit()


# ---------- Proventos ----------

@router.get("/proventos", response_model=Pagina[ProventoOut])
def listar_proventos(
    sessao: SessaoDep,
    investidores: InvestidoresDep,
    ticker: str | None = None,
    inicio: date | None = None,
    fim: date | None = None,
    limite: Limite = 200,
    deslocamento: Deslocamento = 0,
):
    base = _filtrar(select(Provento), Provento, Provento.data_pagamento, investidores, ticker, inicio, fim)
    total = sessao.scalar(select(func.count()).select_from(base.subquery()))
    itens = sessao.scalars(
        base.options(joinedload(Provento.ativo), joinedload(Provento.corretora))
        .order_by(Provento.data_pagamento.desc(), Provento.id.desc())
        .limit(limite)
        .offset(deslocamento)
    ).all()
    return Pagina[ProventoOut](total=total or 0, itens=[_provento_out(p) for p in itens])


@router.post("/proventos", response_model=ProventoOut, status_code=201)
def criar_provento(dados: ProventoIn, sessao: SessaoDep):
    _validar_refs(sessao, dados)
    obj = Provento(**dados.model_dump(), origem="manual")
    sessao.add(obj)
    sessao.commit()
    sessao.refresh(obj)
    return _provento_out(obj)


@router.delete("/proventos/{id_}", status_code=204)
def excluir_provento(id_: int, sessao: SessaoDep):
    sessao.delete(obter_ou_404(sessao, Provento, id_))
    sessao.commit()
