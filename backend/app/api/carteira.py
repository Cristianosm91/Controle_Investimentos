from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from ..dominio import CATEGORIAS_CARTEIRA, EVENTOS_CAIXA, EVENTOS_OPERACAO, EVENTOS_PROVENTO, INDEXADORES, MOEDAS
from ..schemas import AtualizacaoCotacoesOut, PosicaoOut
from ..services import configuracao, jobs, painel
from ..services.carteira import montar_carteira
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
    classificacao = configuracao.carregar(sessao)
    metricas = painel.metricas_posicoes(
        sessao,
        investidores,
        {
            # Posição encerrada não precisa de cotação: o valor final é zero.
            (l.investidor_id, l.ativo.id): (l.posicao.custo, l.valor_mercado if l.posicao.aberta else Decimal(0))
            for l in linhas
        },
    )
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
            proventos_12m=m.proventos_12m,
            yoc_12m=m.yoc_12m,
            tir_aa=m.tir_aa,
            data_inicio=l.posicao.data_inicio,
            book=book.nome if book else None,
            estrategia=book.estrategia.nome if book else None,
            carteira=vinculo.carteira.nome if vinculo else None,
        )
        for l in linhas
        for m in [metricas[(l.investidor_id, l.ativo.id)]]
        for book in [classificacao.book_principal(l.ativo)]
        for vinculo in [classificacao.carteira(l.ativo.id)]
    ]


@router.post("/cotacoes/atualizar", response_model=AtualizacaoCotacoesOut)
def atualizar():
    try:
        r = jobs.executar("cotacoes")
    except jobs.TarefaOcupada as erro:
        raise HTTPException(409, str(erro))
    return AtualizacaoCotacoesOut(atualizados=r.atualizados, sem_cotacao=r.sem_cotacao)


@router.get("/dominio")
def dominio():
    return {
        "eventos_operacao": EVENTOS_OPERACAO,
        "eventos_provento": EVENTOS_PROVENTO,
        "eventos_caixa": EVENTOS_CAIXA,
        "moedas": MOEDAS,
        "indexadores": INDEXADORES,
        "categorias_carteira": CATEGORIAS_CARTEIRA,
    }
