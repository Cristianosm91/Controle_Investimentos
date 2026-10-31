from fastapi import APIRouter, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from ..models import Ativo, AtivoRadar
from ..schemas import PrecoAlvoIn, RadarNovoIn, RadarOut
from ..services import radar as servico
from .deps import InvestidoresDep, SessaoDep, obter_ou_404

router = APIRouter(prefix="/radar", tags=["radar"])


@router.post("", status_code=201)
def criar_e_adicionar(dados: RadarNovoIn, sessao: SessaoDep):
    ativo = Ativo(
        ticker=dados.ticker,
        classe=dados.classe,
        moeda="BRL",
        mercado="BVMF",
        cotacao_automatica=True,
    )
    sessao.add(ativo)
    try:
        sessao.flush()
        sessao.add(AtivoRadar(ativo_id=ativo.id))
        sessao.commit()
    except IntegrityError:
        sessao.rollback()
        raise HTTPException(409, f"Ativo {dados.ticker} já cadastrado; selecione-o na lista") from None
    return {"ativo_id": ativo.id, "ticker": ativo.ticker}


@router.get("", response_model=list[RadarOut])
def listar(sessao: SessaoDep, investidores: InvestidoresDep):
    return [
        RadarOut(
            ativo_id=linha.ativo.id,
            ticker=linha.ativo.ticker,
            nome=linha.ativo.nome,
            classe=linha.ativo.classe,
            moeda=linha.ativo.moeda,
            tem_posicao=linha.tem_posicao,
            cotacao=linha.cotacao.preco if linha.cotacao else None,
            cotacao_data=linha.cotacao.data if linha.cotacao else None,
            cotacao_fonte=linha.cotacao.fonte if linha.cotacao else None,
            variacao_1d_pct=linha.variacao_1d_pct,
            variacao_7d_pct=linha.variacao_7d_pct,
            variacao_14d_pct=linha.variacao_14d_pct,
            drawdown_60d_pct=linha.drawdown_60d_pct,
            minimo_52s=linha.minimo_52s,
            maximo_52s=linha.maximo_52s,
            preco_teto_graham=linha.preco_teto_graham,
            upside_graham_pct=linha.upside_graham_pct,
            preco_lucro=linha.fundamento.preco_lucro if linha.fundamento else None,
            preco_valor_patrimonial=linha.fundamento.preco_valor_patrimonial if linha.fundamento else None,
            dividend_yield=linha.fundamento.dividend_yield if linha.fundamento else None,
            roe=linha.fundamento.roe if linha.fundamento else None,
            roic=linha.fundamento.roic if linha.fundamento else None,
            fii_ffo_yield=linha.fundamento.fii_ffo_yield if linha.fundamento else None,
            data_ref_fundamentos=linha.fundamento.data_ref if linha.fundamento else None,
            yoc_12m=linha.yoc_12m,
            preco_alvo=linha.preco_alvo,
            atingiu_alvo=bool(linha.preco_alvo and linha.cotacao and linha.cotacao.preco <= linha.preco_alvo),
        )
        for linha in servico.listar(sessao, investidores)
    ]


@router.put("/{ativo_id}/alvo", status_code=204)
def definir_preco_alvo(ativo_id: int, dados: PrecoAlvoIn, sessao: SessaoDep):
    registro = sessao.scalar(select(AtivoRadar).where(AtivoRadar.ativo_id == ativo_id))
    if registro is None:
        raise HTTPException(404, "Ativo não está no Radar")
    registro.preco_alvo = dados.preco_alvo
    sessao.commit()
    return Response(status_code=204)


@router.post("/{ativo_id}", status_code=201)
def adicionar(ativo_id: int, sessao: SessaoDep):
    ativo = obter_ou_404(sessao, Ativo, ativo_id)
    if not ativo.cotacao_automatica or ativo.mercado != "BVMF":
        raise HTTPException(422, "O Radar aceita somente ativos B3 com cotação automática")
    if sessao.scalar(select(AtivoRadar.id).where(AtivoRadar.ativo_id == ativo_id)):
        raise HTTPException(409, f"{ativo.ticker} já está no Radar")
    sessao.add(AtivoRadar(ativo_id=ativo_id))
    try:
        sessao.commit()
    except IntegrityError:
        sessao.rollback()
        raise HTTPException(409, f"{ativo.ticker} já está no Radar") from None
    return {"ativo_id": ativo.id, "ticker": ativo.ticker}


@router.delete("/{ativo_id}", status_code=204)
def remover(ativo_id: int, sessao: SessaoDep):
    registro = sessao.scalar(select(AtivoRadar).where(AtivoRadar.ativo_id == ativo_id))
    if registro is None:
        raise HTTPException(404, "Ativo não está no Radar")
    sessao.delete(registro)
    sessao.commit()
    return Response(status_code=204)
