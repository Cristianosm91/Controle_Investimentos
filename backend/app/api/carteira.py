from typing import Annotated

from fastapi import APIRouter, Query

from ..dominio import EVENTOS_CAIXA, EVENTOS_OPERACAO, EVENTOS_PROVENTO, MOEDAS
from ..providers.yahoo import ProvedorYahoo
from ..schemas import AtualizacaoCotacoesOut, PosicaoOut
from ..services.carteira import montar_carteira
from ..services.cotacoes import atualizar_cotacoes
from .deps import InvestidoresDep, SessaoDep

router = APIRouter(tags=["carteira"])


@router.get("/posicoes", response_model=list[PosicaoOut])
def listar_posicoes(
    sessao: SessaoDep,
    investidores: InvestidoresDep,
    agrupar: Annotated[str, Query(pattern="^(ativo|investidor)$")] = "ativo",
    somente_abertas: bool = True,
):
    linhas = montar_carteira(sessao, investidores, consolidado=agrupar == "ativo", somente_abertas=somente_abertas)
    return [
        PosicaoOut(
            investidor_id=l.investidor_id,
            ativo_id=l.ativo.id,
            ticker=l.ativo.ticker,
            nome=l.ativo.nome,
            classe=l.ativo.classe,
            setor=l.ativo.setor,
            subsetor=l.ativo.subsetor,
            moeda=l.ativo.moeda,
            quantidade=l.posicao.quantidade,
            preco_medio=l.posicao.preco_medio,
            custo=l.posicao.custo,
            cotacao=l.cotacao.preco if l.cotacao else None,
            cotacao_data=l.cotacao.data if l.cotacao else None,
            cotacao_fonte=l.cotacao.fonte if l.cotacao else None,
            variacao_dia_pct=l.cotacao.variacao_pct if l.cotacao else None,
            valor_mercado=l.valor_mercado,
            lucro_dia=l.lucro_dia,
            lucro_aberto=l.lucro_aberto,
            lucro_realizado=l.posicao.lucro_realizado,
            lucro_daytrade=l.posicao.lucro_daytrade,
            proventos=l.proventos,
            data_inicio=l.posicao.data_inicio,
        )
        for l in linhas
    ]


@router.post("/cotacoes/atualizar", response_model=AtualizacaoCotacoesOut)
def atualizar(sessao: SessaoDep):
    r = atualizar_cotacoes(sessao, [ProvedorYahoo()])
    return AtualizacaoCotacoesOut(atualizados=r.atualizados, sem_cotacao=r.sem_cotacao)


@router.get("/dominio")
def dominio():
    return {
        "eventos_operacao": EVENTOS_OPERACAO,
        "eventos_provento": EVENTOS_PROVENTO,
        "eventos_caixa": EVENTOS_CAIXA,
        "moedas": MOEDAS,
    }
