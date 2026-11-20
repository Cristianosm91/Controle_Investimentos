from datetime import date
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy.exc import IntegrityError

from ..dominio import MOEDAS_CRIPTO
from ..models import Ativo, Operacao
from ..providers import bcb
from ..providers import cripto as provedor
from ..schemas import (
    AtivoOut,
    CambioCriptoMoedaOut,
    CambioCriptoOut,
    CriptoIn,
    CriptoOperacaoIn,
    CriptoTrocaTickerIn,
    MoedaCriptoOut,
    MonitorCriptoOut,
    OperacaoOut,
    PainelCriptoOut,
    PontoCriptoOut,
)
from ..services import cripto, jobs
from .deps import InvestidoresDep, SessaoDep, obter_ou_404
from .lancamentos import _saida, _validar_refs

router = APIRouter(prefix="/cripto", tags=["cripto"])


@router.get("", response_model=PainelCriptoOut)
def painel(
    sessao: SessaoDep,
    investidores: InvestidoresDep,
    moeda_visualizacao: Annotated[str, Query(pattern="^(BRL|USD|EUR|GBP)$")] = "BRL",
):
    return cripto.painel(sessao, investidores, moeda_visualizacao)


@router.get("/cambios", response_model=CambioCriptoOut)
def consultar_cambios(data: date):
    cotacoes, avisos = cripto.ptax_historica(data)
    usd = cotacoes.get("USD")
    moedas = []
    for moeda in MOEDAS_CRIPTO:
        cotacao = cotacoes.get(moeda)
        cambio_brl = cotacao.venda if cotacao else Decimal(1) if moeda == "BRL" else None
        cambio_usd = (
            Decimal(1) if moeda == "USD"
            else cambio_brl / usd.venda if cambio_brl is not None and usd is not None
            else None
        )
        moedas.append(CambioCriptoMoedaOut(
            moeda=moeda,
            cambio_brl=cambio_brl,
            cambio_usd=cambio_usd,
            data_moeda=cotacao.data if cotacao else data if moeda == "BRL" else None,
            data_usd=usd.data if usd else None,
        ))
    return {"data_solicitada": data, "moedas": moedas, "avisos": avisos}


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


@router.post("/operacoes", response_model=OperacaoOut, status_code=201)
def criar_operacao(dados: CriptoOperacaoIn, sessao: SessaoDep):
    _validar_refs(sessao, dados)
    try:
        operacao = cripto.salvar_operacao(sessao, dados)
    except bcb.ErroPtax as erro:
        raise HTTPException(502, str(erro)) from erro
    except ValueError as erro:
        raise HTTPException(422, str(erro)) from erro
    return _saida(operacao, OperacaoOut)


@router.put("/operacoes/{id_}", response_model=OperacaoOut)
def alterar_operacao(id_: int, dados: CriptoOperacaoIn, sessao: SessaoDep):
    operacao = obter_ou_404(sessao, Operacao, id_)
    ativo = obter_ou_404(sessao, Ativo, operacao.ativo_id)
    if ativo.classe != "CRIPTO":
        raise HTTPException(422, "A operação informada não é de cripto")
    _validar_refs(sessao, dados)
    try:
        operacao = cripto.salvar_operacao(sessao, dados, operacao)
    except bcb.ErroPtax as erro:
        raise HTTPException(502, str(erro)) from erro
    except ValueError as erro:
        raise HTTPException(409, str(erro)) from erro
    return _saida(operacao, OperacaoOut)


@router.post("/troca-ticker", response_model=list[OperacaoOut], status_code=201)
def criar_troca_ticker(dados: CriptoTrocaTickerIn, sessao: SessaoDep):
    origem = obter_ou_404(sessao, Ativo, dados.ativo_origem_id)
    destino = obter_ou_404(sessao, Ativo, dados.ativo_destino_id)
    if origem.classe != "CRIPTO" or destino.classe != "CRIPTO":
        raise HTTPException(422, "Origem e destino da troca precisam ser ativos CRIPTO")
    _validar_refs(sessao, dados)
    try:
        pernas = cripto.salvar_troca_ticker(sessao, dados)
    except bcb.ErroPtax as erro:
        raise HTTPException(502, str(erro)) from erro
    except ValueError as erro:
        raise HTTPException(422, str(erro)) from erro
    return [_saida(perna, OperacaoOut) for perna in pernas]


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
