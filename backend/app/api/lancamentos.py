from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from ..models import Ativo, Corretora, Investidor, MovCaixa, Operacao, Provento
from ..schemas import (
    MovCaixaIn,
    MovCaixaOut,
    OperacaoIn,
    OperacaoOut,
    Pagina,
    ProventoIn,
    ProventoOut,
)
from .deps import InvestidoresDep, SessaoDep, obter_ou_404

router = APIRouter(tags=["lançamentos"])

Limite = Annotated[int, Query(ge=1, le=1000)]
Deslocamento = Annotated[int, Query(ge=0)]

Lancamento = Operacao | Provento | MovCaixa


def _saida(obj: Lancamento, schema: type[BaseModel]):
    dados = {c: getattr(obj, c) for c in schema.model_fields if c not in ("ticker", "corretora")}
    if "ticker" in schema.model_fields:
        dados["ticker"] = obj.ativo.ticker
    dados["corretora"] = obj.corretora.nome if obj.corretora else None
    return schema.model_validate(dados)


def _validar_refs(sessao: Session, dados: BaseModel) -> None:
    obter_ou_404(sessao, Investidor, dados.investidor_id)
    if getattr(dados, "ativo_id", None) is not None:
        obter_ou_404(sessao, Ativo, dados.ativo_id)
    if dados.corretora_id is not None:
        obter_ou_404(sessao, Corretora, dados.corretora_id)


def _listar(sessao: Session, modelo, campo_data, schema, investidores, ticker, inicio, fim, limite, deslocamento):
    base = select(modelo)
    if investidores:
        base = base.where(modelo.investidor_id.in_(investidores))
    if ticker and hasattr(modelo, "ativo_id"):
        base = base.join(Ativo, Ativo.id == modelo.ativo_id).where(Ativo.ticker == ticker.strip().upper())
    if inicio:
        base = base.where(campo_data >= inicio)
    if fim:
        base = base.where(campo_data <= fim)

    total = sessao.scalar(select(func.count()).select_from(base.subquery()))
    opcoes = [joinedload(modelo.corretora)]
    if hasattr(modelo, "ativo"):
        opcoes.append(joinedload(modelo.ativo))
    itens = sessao.scalars(
        base.options(*opcoes).order_by(campo_data.desc(), modelo.id.desc()).limit(limite).offset(deslocamento)
    ).all()
    return Pagina[schema](total=total or 0, itens=[_saida(o, schema) for o in itens])


def _criar(sessao: Session, modelo, dados: BaseModel, schema):
    _validar_refs(sessao, dados)
    obj = modelo(**dados.model_dump(), origem="manual")
    sessao.add(obj)
    sessao.commit()
    sessao.refresh(obj)
    return _saida(obj, schema)


def _alterar(sessao: Session, modelo, id_: int, dados: BaseModel, schema):
    obj = obter_ou_404(sessao, modelo, id_)
    _validar_refs(sessao, dados)
    for campo, valor in dados.model_dump().items():
        setattr(obj, campo, valor)
    sessao.commit()
    sessao.refresh(obj)
    return _saida(obj, schema)


def _excluir(sessao: Session, modelo, id_: int) -> None:
    sessao.delete(obter_ou_404(sessao, modelo, id_))
    sessao.commit()


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
    return _listar(sessao, Operacao, Operacao.data, OperacaoOut, investidores, ticker, inicio, fim, limite, deslocamento)


@router.post("/operacoes", response_model=OperacaoOut, status_code=201)
def criar_operacao(dados: OperacaoIn, sessao: SessaoDep):
    return _criar(sessao, Operacao, dados, OperacaoOut)


@router.put("/operacoes/{id_}", response_model=OperacaoOut)
def alterar_operacao(id_: int, dados: OperacaoIn, sessao: SessaoDep):
    return _alterar(sessao, Operacao, id_, dados, OperacaoOut)


@router.delete("/operacoes/{id_}", status_code=204)
def excluir_operacao(id_: int, sessao: SessaoDep):
    _excluir(sessao, Operacao, id_)


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
    return _listar(
        sessao, Provento, Provento.data_pagamento, ProventoOut, investidores, ticker, inicio, fim, limite, deslocamento
    )


@router.post("/proventos", response_model=ProventoOut, status_code=201)
def criar_provento(dados: ProventoIn, sessao: SessaoDep):
    return _criar(sessao, Provento, dados, ProventoOut)


@router.put("/proventos/{id_}", response_model=ProventoOut)
def alterar_provento(id_: int, dados: ProventoIn, sessao: SessaoDep):
    return _alterar(sessao, Provento, id_, dados, ProventoOut)


@router.delete("/proventos/{id_}", status_code=204)
def excluir_provento(id_: int, sessao: SessaoDep):
    _excluir(sessao, Provento, id_)


# ---------- Caixa ----------

@router.get("/caixa", response_model=Pagina[MovCaixaOut])
def listar_caixa(
    sessao: SessaoDep,
    investidores: InvestidoresDep,
    inicio: date | None = None,
    fim: date | None = None,
    limite: Limite = 200,
    deslocamento: Deslocamento = 0,
):
    return _listar(sessao, MovCaixa, MovCaixa.data, MovCaixaOut, investidores, None, inicio, fim, limite, deslocamento)


@router.post("/caixa", response_model=MovCaixaOut, status_code=201)
def criar_mov_caixa(dados: MovCaixaIn, sessao: SessaoDep):
    return _criar(sessao, MovCaixa, dados, MovCaixaOut)


@router.put("/caixa/{id_}", response_model=MovCaixaOut)
def alterar_mov_caixa(id_: int, dados: MovCaixaIn, sessao: SessaoDep):
    return _alterar(sessao, MovCaixa, id_, dados, MovCaixaOut)


@router.delete("/caixa/{id_}", status_code=204)
def excluir_mov_caixa(id_: int, sessao: SessaoDep):
    _excluir(sessao, MovCaixa, id_)
