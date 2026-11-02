from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query

from ..schemas import JanelaOut, MatrizProventosOut, MesRentabilidadeOut, ResumoOut
from ..services import painel
from .deps import InvestidoresDep, SessaoDep

router = APIRouter(tags=["rentabilidade"])


def real(twr, ipca):
    """Retorno descontada a inflação: (1 + nominal) / (1 + IPCA) − 1."""
    return None if twr is None or ipca is None else (1 + twr) / (1 + ipca) - 1


@router.get("/rentabilidade/mensal", response_model=list[MesRentabilidadeOut])
def rentabilidade_mensal(
    sessao: SessaoDep, investidores: InvestidoresDep, inicio: date | None = None, fim: date | None = None,
    classe: Annotated[str | None, Query(max_length=30)] = None,
):
    return [
        MesRentabilidadeOut(
            data=l.mes.data, investido=l.mes.investido, mercado=l.mes.mercado, proventos=l.mes.proventos,
            lucro_trades=l.mes.lucro_trades, lucro_daytrade=l.mes.lucro_daytrade, fluxo=l.mes.fluxo, lucro=l.mes.lucro,
            twr=l.mes.twr, twr_acumulado=l.twr_acumulado, sem_cotacao=len(l.mes.sem_cotacao),
            ibov=l.benchmark.ibov, ifix=l.benchmark.ifix, cdi=l.benchmark.cdi, ipca=l.benchmark.ipca,
            ibov_acumulado=l.acumulados["ibov"], ifix_acumulado=l.acumulados["ifix"],
            cdi_acumulado=l.acumulados["cdi"], ipca_acumulado=l.acumulados["ipca"],
            real_acumulado=real(l.twr_acumulado, l.acumulados["ipca"]),
        )
        for l in painel.mensal(sessao, investidores, inicio, fim, classe)
    ]


@router.get("/rentabilidade/resumo", response_model=ResumoOut)
def rentabilidade_resumo(
    sessao: SessaoDep, investidores: InvestidoresDep, classe: Annotated[str | None, Query(max_length=30)] = None
):
    r = painel.resumo(sessao, investidores, classe)
    return ResumoOut(
        data_referencia=r.data_referencia,
        patrimonio=r.patrimonio,
        investido=r.investido,
        lucro_aberto=r.patrimonio - r.investido,
        lucro_realizado=r.lucro_realizado,
        proventos_total=r.proventos_total,
        aluguel_total=r.aluguel_total,
        proventos_12m=r.proventos_12m,
        yoc_12m=r.proventos_12m / r.investido if r.investido else None,
        tir_aa=r.tir_aa,
        tir_am=None if r.tir_aa is None else (1 + r.tir_aa) ** (1 / 12) - 1,
        janelas=[
            JanelaOut(nome=j.nome, inicio=j.inicio, twr=j.twr, **j.benchmarks, real=real(j.twr, j.benchmarks["ipca"]))
            for j in r.janelas
        ],
        proventos_mensais=r.proventos_mensais,
    )


@router.get("/proventos/matriz", response_model=MatrizProventosOut)
def matriz_de_proventos(
    sessao: SessaoDep,
    investidores: InvestidoresDep,
    ano: Annotated[int | None, Query(ge=1990, le=2100)] = None,
    classe: Annotated[str | None, Query(max_length=30)] = None,
):
    m = painel.matriz_proventos(sessao, investidores, ano, classe)
    totais_mes = [sum(linha[i] for linha in m.valores) for i in range(12)]
    return MatrizProventosOut(
        titulo_linhas=m.titulo_linhas,
        linhas=m.linhas,
        valores=m.valores,
        totais_linha=[sum(linha) for linha in m.valores],
        totais_mes=totais_mes,
        total=sum(totais_mes),
    )
