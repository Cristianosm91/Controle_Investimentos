from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import delete

from ..models import Investidor, MetaMetodologia
from ..schemas import (
    AlocacaoOut,
    CaixaSaldosOut,
    CategoriaMetaMetodologiaOut,
    CategoriaMetodologiaOut,
    GrupoAlocacaoOut,
    ItemAlocacaoOut,
    MetasMetodologiaIn,
    MetasMetodologiaOut,
    MetodologiaAlocacaoOut,
    SaldoCaixaOut,
)
from ..services import alocacao, caixa
from ..services.carteira import montar_carteira
from .deps import InvestidoresDep, SessaoDep, obter_ou_404

router = APIRouter(tags=["alocação"])


def _metodologias_out(
    metodologias: list[alocacao.MetodologiaAlocacao],
    metas: dict[tuple[str, str], Decimal],
) -> list[MetodologiaAlocacaoOut]:
    return [
        MetodologiaAlocacaoOut(
            nome=m.nome,
            categorias=[
                CategoriaMetodologiaOut(**vars(c), peso_alvo=metas.get((m.nome, c.nome)))
                for c in m.categorias
            ],
            total_atual=m.total_atual,
            peso_total=m.peso_total,
        )
        for m in metodologias
    ]


def _metas_selecionadas(sessao: SessaoDep, investidores: list[int] | None) -> dict[tuple[str, str], Decimal]:
    if investidores is None or len(investidores) != 1:
        return {}
    return alocacao.metas_do_investidor(sessao, investidores[0])


@router.get(
    "/investidores/{investidor_id}/metas-metodologias",
    response_model=list[MetasMetodologiaOut],
    description="Metas individuais; categorias ainda não configuradas são retornadas sem peso-alvo.",
)
def consultar_metas_metodologias(investidor_id: int, sessao: SessaoDep):
    obter_ou_404(sessao, Investidor, investidor_id)
    metas = alocacao.metas_do_investidor(sessao, investidor_id)
    return [
        MetasMetodologiaOut(
            nome=nome,
            categorias=[
                CategoriaMetaMetodologiaOut(nome=categoria, peso_alvo=metas.get((nome, categoria)))
                for categoria in categorias
            ],
        )
        for nome, categorias in alocacao.CATEGORIAS_METODOLOGIAS.items()
    ]


@router.put(
    "/investidores/{investidor_id}/metas-metodologias/{metodologia}",
    response_model=MetasMetodologiaOut,
    description="Substitui todas as metas da metodologia para um investidor; os pesos devem somar 100%.",
)
def salvar_metas_metodologia(investidor_id: int, metodologia: str, dados: MetasMetodologiaIn, sessao: SessaoDep):
    obter_ou_404(sessao, Investidor, investidor_id)
    categorias = alocacao.CATEGORIAS_METODOLOGIAS.get(metodologia)
    if categorias is None:
        raise HTTPException(422, "Metodologia inválida")
    nomes = [categoria.nome for categoria in dados.categorias]
    if len(nomes) != len(categorias) or set(nomes) != set(categorias):
        raise HTTPException(422, "Informe todas as categorias da metodologia, sem duplicatas")
    if sum((categoria.peso_alvo for categoria in dados.categorias), Decimal(0)) != Decimal(1):
        raise HTTPException(422, "As metas da metodologia devem somar 100%")
    sessao.execute(delete(MetaMetodologia).where(
        MetaMetodologia.investidor_id == investidor_id, MetaMetodologia.metodologia == metodologia,
    ))
    sessao.add_all([
        MetaMetodologia(investidor_id=investidor_id, metodologia=metodologia, categoria=c.nome, peso_alvo=c.peso_alvo)
        for c in dados.categorias
    ])
    sessao.commit()
    pesos = {categoria.nome: categoria.peso_alvo for categoria in dados.categorias}
    return MetasMetodologiaOut(
        nome=metodologia,
        categorias=[CategoriaMetaMetodologiaOut(nome=nome, peso_alvo=pesos[nome]) for nome in categorias],
    )


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
        raise HTTPException(422, str(erro)) from erro
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
        metodologias=_metodologias_out(r.metodologias, _metas_selecionadas(sessao, investidores)),
        avisos=r.avisos,
    )


@router.get(
    "/alocacao/metodologias",
    response_model=list[MetodologiaAlocacaoOut],
    description="Exposição ARCA e KRAKEN das posições abertas dos investidores selecionados. "
    "Ao excluir classes, o caixa não é incluído; caso contrário, segue a configuração do Portfólio.",
)
def consultar_metodologias(
    sessao: SessaoDep,
    investidores: InvestidoresDep,
    classes_excluidas: str | None = None,
):
    classes = [classe.strip() for classe in (classes_excluidas or "").split(",") if classe.strip()]
    linhas = montar_carteira(sessao, investidores, consolidado=True)
    return _metodologias_out(
        alocacao.metodologias_da_carteira(sessao, investidores, linhas, classes),
        _metas_selecionadas(sessao, investidores),
    )


@router.get("/caixa/saldos", response_model=CaixaSaldosOut)
def saldos_caixa(sessao: SessaoDep, investidores: InvestidoresDep):
    r = caixa.calcular(sessao, investidores)
    return CaixaSaldosOut(
        integrado_desde=r.integrado_desde,
        total_brl=r.total_brl,
        saldos=[SaldoCaixaOut(**vars(s), saldo=s.saldo, saldo_brl=s.saldo_brl) for s in r.saldos],
    )
