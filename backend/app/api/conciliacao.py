from fastapi import APIRouter
from sqlalchemy import func, select

from ..models import Ativo, Investidor, Operacao
from ..schemas import (
    ConciliacaoPosicaoIn,
    ConciliacaoPosicaoOut,
    OperacaoConciliacaoOut,
)
from ..services.carteira import carregar_posicoes
from ..services.posicao import Posicao
from .deps import SessaoDep, obter_ou_404

router = APIRouter(tags=["conciliação"])

_LIMITE_HISTORICO = 500


@router.post("/conciliacao/posicao", response_model=ConciliacaoPosicaoOut)
def conciliar_posicao(dados: ConciliacaoPosicaoIn, sessao: SessaoDep):
    obter_ou_404(sessao, Investidor, dados.investidor_id)
    ativo = obter_ou_404(sessao, Ativo, dados.ativo_id)

    chave = (dados.investidor_id, dados.ativo_id)
    posicao = carregar_posicoes(
        sessao, [dados.investidor_id], ate=dados.data_referencia, ativo_ids={dados.ativo_id}
    ).get(chave, Posicao(*chave))
    preco_medio_informado = (
        dados.custo_informado / dados.quantidade_informada if dados.quantidade_informada else None
    )
    preco_medio_calculado = posicao.preco_medio if posicao.quantidade > 0 else None
    diferenca_preco_medio = (
        preco_medio_calculado - preco_medio_informado
        if preco_medio_calculado is not None and preco_medio_informado is not None
        else None
    )

    base = select(Operacao).where(
        Operacao.investidor_id == dados.investidor_id,
        Operacao.ativo_id == dados.ativo_id,
        Operacao.data <= dados.data_referencia,
    )
    operacoes_total = sessao.scalar(select(func.count()).select_from(base.subquery())) or 0
    operacoes = sessao.scalars(
        base.order_by(Operacao.data.desc(), Operacao.id.desc()).limit(_LIMITE_HISTORICO)
    ).all()

    return ConciliacaoPosicaoOut(
        ticker=ativo.ticker,
        data_referencia=dados.data_referencia,
        quantidade_informada=dados.quantidade_informada,
        custo_informado=dados.custo_informado,
        preco_medio_informado=preco_medio_informado,
        quantidade_calculada=posicao.quantidade,
        custo_calculado=posicao.custo,
        preco_medio_calculado=preco_medio_calculado,
        diferenca_quantidade=posicao.quantidade - dados.quantidade_informada,
        diferenca_custo=posicao.custo - dados.custo_informado,
        diferenca_preco_medio=diferenca_preco_medio,
        operacoes_total=operacoes_total,
        operacoes=[OperacaoConciliacaoOut.model_validate(op) for op in operacoes],
    )
