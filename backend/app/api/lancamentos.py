import re
from datetime import date
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
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
    TrocaTickerIn,
    VinculoTransferenciaIn,
)
from .deps import InvestidoresDep, SessaoDep, obter_ou_404

router = APIRouter(tags=["lançamentos"])

Limite = Annotated[int, Query(ge=1, le=1000)]
Deslocamento = Annotated[int, Query(ge=0)]

Lancamento = Operacao | Provento | MovCaixa


def _saida(obj: Lancamento, schema: type[BaseModel]):
    dados = {
        c: getattr(obj, c)
        for c in schema.model_fields
        if c not in ("ticker", "corretora", "ticker_transferencia")
    }
    if "ticker" in schema.model_fields:
        dados["ticker"] = obj.ativo.ticker
    dados["corretora"] = obj.corretora.nome if obj.corretora else None
    if "transferencia_pareada_id" in schema.model_fields:
        pareada = obj.transferencia_pareada
        dados["ticker_transferencia"] = pareada.ativo.ticker if pareada else None
    return schema.model_validate(dados)


def _validar_refs(sessao: Session, dados: BaseModel) -> None:
    obter_ou_404(sessao, Investidor, dados.investidor_id)
    ativo_id = getattr(dados, "ativo_id", getattr(dados, "ativo_origem_id", None))
    if ativo_id is not None:
        obter_ou_404(sessao, Ativo, ativo_id)
    if dados.corretora_id is not None:
        obter_ou_404(sessao, Corretora, dados.corretora_id)


def _listar(
    sessao: Session, modelo, campo_data, schema, investidores, ticker, inicio, fim, limite, deslocamento, evento=None,
    classe=None, ids=None, corretora_id=None,
):
    base = select(modelo)
    if investidores:
        base = base.where(modelo.investidor_id.in_(investidores))
    if ids is not None:
        try:
            ids_lista = {int(valor) for valor in ids.split(",") if valor}
        except ValueError as erro:
            raise HTTPException(422, "IDs de lançamentos inválidos") from erro
        if not ids_lista or min(ids_lista) <= 0:
            raise HTTPException(422, "Informe pelo menos um ID de lançamento válido")
        base = base.where(modelo.id.in_(ids_lista))
    if evento:
        base = base.where(modelo.evento == evento)
    if (ticker or classe) and hasattr(modelo, "ativo_id"):
        base = base.join(Ativo, Ativo.id == modelo.ativo_id)
        if ticker:
            tickers = {valor.upper() for valor in re.split(r"[,;\s]+", ticker) if valor}
            base = base.where(Ativo.ticker == next(iter(tickers))) if len(tickers) == 1 else base.where(Ativo.ticker.in_(tickers))
        if classe:
            base = base.where(Ativo.classe == classe)
    if corretora_id is not None:
        base = base.where(modelo.corretora_id == corretora_id)
    if inicio:
        base = base.where(campo_data >= inicio)
    if fim:
        base = base.where(campo_data <= fim)

    total = sessao.scalar(select(func.count()).select_from(base.subquery()))
    opcoes = [joinedload(modelo.corretora)]
    if hasattr(modelo, "ativo"):
        opcoes.append(joinedload(modelo.ativo))
    if modelo is Operacao:
        opcoes.append(joinedload(Operacao.transferencia_pareada).joinedload(Operacao.ativo))
    itens = sessao.scalars(
        base.options(*opcoes).order_by(campo_data.desc(), modelo.id.desc()).limit(limite).offset(deslocamento)
    ).all()
    return Pagina[schema](total=total or 0, itens=[_saida(o, schema) for o in itens])


def _ids_apontamento(
    sessao: Session,
    investidores: list[int],
    apontamento: str,
    campo: str,
    codigo: str | None = None,
) -> list[int]:
    if not re.fullmatch(r"[a-f0-9]{64}", apontamento):
        raise HTTPException(422, "Identificador de apontamento inválido")
    from ..services import qualidade

    verificacoes = qualidade.verificar(sessao, investidores)
    verificacao = next((v for v in verificacoes if v.fingerprint == apontamento), None)
    if verificacao is None and codigo:
        # Corrigir um registro muda o fingerprint; a regra continua listando as pendências restantes.
        verificacao = next((v for v in verificacoes if v.codigo == codigo), None)
    return getattr(verificacao, campo, []) if verificacao else []


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
    if modelo is Operacao and obj.transferencia_pareada is not None:
        campos_vinculados = ("investidor_id", "ativo_id", "data", "evento", "quantidade", "preco", "moeda", "cambio")
        if any(getattr(dados, campo) != getattr(obj, campo) for campo in campos_vinculados):
            raise HTTPException(409, "Desfaça o vínculo da transferência antes de alterar suas pernas")
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
    classe: str | None = None,
    evento: Annotated[str | None, Query(max_length=20)] = None,
    inicio: date | None = None,
    fim: date | None = None,
    ids: str | None = None,
    apontamento: str | None = None,
    codigo: Annotated[str | None, Query(max_length=50)] = None,
    corretora_id: Annotated[int | None, Query(ge=1)] = None,
    limite: Limite = 200,
    deslocamento: Deslocamento = 0,
):
    if apontamento:
        ids_relacionados = _ids_apontamento(
            sessao, investidores, apontamento, "operacao_ids", codigo
        )
        if not ids_relacionados:
            return Pagina[OperacaoOut](total=0, itens=[])
        ids = ",".join(str(id_) for id_ in ids_relacionados)
    return _listar(
        sessao, Operacao, Operacao.data, OperacaoOut, investidores, ticker, inicio, fim, limite, deslocamento,
        evento=evento, classe=classe, ids=ids, corretora_id=corretora_id,
    )


@router.post("/operacoes/troca-ticker", response_model=list[OperacaoOut], status_code=201)
def criar_troca_ticker(dados: TrocaTickerIn, sessao: SessaoDep):
    origem = obter_ou_404(sessao, Ativo, dados.ativo_origem_id)
    destino = obter_ou_404(sessao, Ativo, dados.ativo_destino_id)
    if origem.moeda != dados.moeda or destino.moeda != dados.moeda:
        raise HTTPException(422, "Origem e destino precisam usar a mesma moeda da operação")
    _validar_refs(sessao, dados)

    observacao = f"AT {origem.ticker}->{destino.ticker}"
    if dados.observacao:
        observacao = f"{observacao} | {dados.observacao}"
    if len(observacao) > 200:
        raise HTTPException(422, "Reduza a observação para identificar a troca de ticker")

    saida = Operacao(
        investidor_id=dados.investidor_id,
        ativo_id=origem.id,
        corretora_id=dados.corretora_id,
        data=dados.data,
        evento="TRANSFERENCIA",
        quantidade=-dados.quantidade_origem,
        preco=dados.preco_origem,
        taxas=dados.taxas,
        irrf=dados.irrf,
        moeda=dados.moeda,
        cambio=dados.cambio,
        observacao=observacao,
        origem="manual",
    )
    entrada = Operacao(
        investidor_id=dados.investidor_id,
        ativo_id=destino.id,
        corretora_id=dados.corretora_id,
        data=dados.data,
        evento="TRANSFERENCIA",
        quantidade=dados.quantidade_destino,
        preco=dados.quantidade_origem * dados.preco_origem / dados.quantidade_destino,
        moeda=dados.moeda,
        cambio=dados.cambio,
        observacao=observacao,
        origem="manual",
    )
    sessao.add_all((saida, entrada))
    sessao.flush()
    saida.transferencia_pareada_id = entrada.id
    entrada.transferencia_pareada_id = saida.id
    sessao.commit()
    sessao.refresh(saida)
    sessao.refresh(entrada)
    return [_saida(saida, OperacaoOut), _saida(entrada, OperacaoOut)]


@router.post("/operacoes/{id_}/vinculo-transferencia", response_model=list[OperacaoOut])
def vincular_transferencia(id_: int, dados: VinculoTransferenciaIn, sessao: SessaoDep):
    primeira = obter_ou_404(sessao, Operacao, id_)
    segunda = obter_ou_404(sessao, Operacao, dados.operacao_id)
    if primeira.id == segunda.id:
        raise HTTPException(422, "Selecione outra operação para vincular")
    if primeira.evento != "TRANSFERENCIA" or segunda.evento != "TRANSFERENCIA":
        raise HTTPException(422, "Somente operações de transferência podem ser vinculadas")
    if primeira.investidor_id != segunda.investidor_id:
        raise HTTPException(422, "As operações precisam pertencer ao mesmo investidor")
    if primeira.ativo_id == segunda.ativo_id or primeira.quantidade * segunda.quantidade >= 0:
        raise HTTPException(422, "Vincule uma saída a uma entrada de outro ativo")
    if primeira.transferencia_pareada_id or segunda.transferencia_pareada_id:
        raise HTTPException(409, "Uma das operações já está vinculada")

    primeira.transferencia_pareada_id = segunda.id
    segunda.transferencia_pareada_id = primeira.id
    sessao.commit()
    sessao.refresh(primeira)
    sessao.refresh(segunda)
    return [_saida(primeira, OperacaoOut), _saida(segunda, OperacaoOut)]


@router.delete("/operacoes/{id_}/vinculo-transferencia", status_code=204)
def desvincular_transferencia(id_: int, sessao: SessaoDep):
    operacao = obter_ou_404(sessao, Operacao, id_)
    pareada = operacao.transferencia_pareada
    if pareada is not None:
        operacao.transferencia_pareada_id = None
        pareada.transferencia_pareada_id = None
        sessao.commit()


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
    evento: Annotated[str | None, Query(max_length=20)] = None,
    classe: str | None = None,
    apontamento: str | None = None,
    codigo: Annotated[str | None, Query(max_length=50)] = None,
    corretora_id: Annotated[int | None, Query(ge=1)] = None,
):
    ids = None
    if apontamento:
        ids_relacionados = _ids_apontamento(
            sessao, investidores, apontamento, "provento_ids", codigo
        )
        if not ids_relacionados:
            return Pagina[ProventoOut](total=0, itens=[])
        ids = ",".join(str(id_) for id_ in ids_relacionados)
    return _listar(
        sessao, Provento, Provento.data_pagamento, ProventoOut, investidores, ticker, inicio, fim, limite, deslocamento,
        evento, classe=classe, ids=ids, corretora_id=corretora_id,
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
    apontamento: str | None = None,
    codigo: Annotated[str | None, Query(max_length=50)] = None,
):
    ids = None
    if apontamento:
        ids_relacionados = _ids_apontamento(
            sessao, investidores, apontamento, "caixa_ids", codigo
        )
        if not ids_relacionados:
            return Pagina[MovCaixaOut](total=0, itens=[])
        ids = ",".join(str(id_) for id_ in ids_relacionados)
    return _listar(
        sessao, MovCaixa, MovCaixa.data, MovCaixaOut, investidores, None, inicio, fim,
        limite, deslocamento, ids=ids,
    )


@router.post("/caixa", response_model=MovCaixaOut, status_code=201)
def criar_mov_caixa(dados: MovCaixaIn, sessao: SessaoDep):
    return _criar(sessao, MovCaixa, dados, MovCaixaOut)


@router.put("/caixa/{id_}", response_model=MovCaixaOut)
def alterar_mov_caixa(id_: int, dados: MovCaixaIn, sessao: SessaoDep):
    return _alterar(sessao, MovCaixa, id_, dados, MovCaixaOut)


@router.delete("/caixa/{id_}", status_code=204)
def excluir_mov_caixa(id_: int, sessao: SessaoDep):
    _excluir(sessao, MovCaixa, id_)
