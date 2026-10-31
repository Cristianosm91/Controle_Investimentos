from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from ..schemas import AlocacaoOut, CaixaSaldosOut, GrupoAlocacaoOut, ItemAlocacaoOut, SaldoCaixaOut
from ..services import alocacao, caixa
from .deps import InvestidoresDep, SessaoDep

router = APIRouter(tags=["alocação"])


@router.get("/alocacao", response_model=AlocacaoOut)
def calcular_alocacao(
    sessao: SessaoDep,
    investidores: InvestidoresDep,
    aporte: Annotated[Decimal, Query(ge=0)] = Decimal(0),
    modo: Annotated[str, Query(pattern="^(comprar|rebalancear)$")] = "comprar",
    respeitar_teto: bool = True,
):
    try:
        r = alocacao.calcular(sessao, investidores, aporte, modo, respeitar_teto)
    except ValueError as erro:
        raise HTTPException(422, str(erro))
    return AlocacaoOut(
        total_atual=r.total_atual,
        aporte=r.aporte,
        sobra=r.sobra,
        estrategias=[GrupoAlocacaoOut(**vars(g)) for g in r.estrategias],
        books=[GrupoAlocacaoOut(**vars(g)) for g in r.books],
        ativos=[
            ItemAlocacaoOut(
                ativo_id=i.candidato.ativo_id, ticker=i.candidato.ticker, nome=i.candidato.nome,
                classe=i.candidato.classe, moeda=i.candidato.moeda, book=i.book, carteira=i.candidato.carteira,
                cotacao=i.candidato.cotacao, preco_teto=i.candidato.preco_teto, acima_teto=i.acima_teto,
                peso_alvo=i.peso_alvo, peso_atual=i.peso_atual, valor_atual=i.candidato.valor_atual,
                valor_alvo=i.valor_alvo, ajuste=i.ajuste, quantidade=i.quantidade,
            )
            for i in r.ativos
        ],
        avisos=r.avisos,
    )


@router.get("/caixa/saldos", response_model=CaixaSaldosOut)
def saldos_caixa(sessao: SessaoDep, investidores: InvestidoresDep):
    r = caixa.calcular(sessao, investidores)
    return CaixaSaldosOut(
        integrado_desde=r.integrado_desde,
        total_brl=r.total_brl,
        saldos=[SaldoCaixaOut(**vars(s), saldo=s.saldo, saldo_brl=s.saldo_brl) for s in r.saldos],
    )
