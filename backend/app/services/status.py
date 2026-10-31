"""Resumo e linha do tempo de ativos, carteiras e books."""

from collections.abc import Sequence
from datetime import date, timedelta
from decimal import Decimal
from typing import Literal

from sqlalchemy import Numeric, case, func, literal, select, union_all
from sqlalchemy.orm import Session

from ..dominio import EVENTOS_OPERACAO, EVENTOS_PROVENTO
from ..models import (
    Ativo,
    Book,
    Carteira,
    CarteiraAtivo,
    Operacao,
    Provento,
)
from . import configuracao
from .carteira import montar_carteira

ZERO = Decimal(0)
Escopo = Literal["ativo", "carteira", "book"]


def _ativos_do_escopo(sessao: Session, escopo: Escopo, escopo_id: int) -> tuple[str, dict[int, Decimal]]:
    if escopo == "ativo":
        ativo = sessao.get(Ativo, escopo_id)
        if ativo is None:
            raise LookupError(f"Ativo {escopo_id} não encontrado")
        return ativo.ticker, {ativo.id: Decimal(1)}

    if escopo == "carteira":
        carteira = sessao.get(Carteira, escopo_id)
        if carteira is None:
            raise LookupError(f"Carteira {escopo_id} não encontrada")
        ids = sessao.scalars(select(CarteiraAtivo.ativo_id).where(CarteiraAtivo.carteira_id == escopo_id))
        return carteira.nome, {ativo_id: Decimal(1) for ativo_id in ids}

    book = sessao.get(Book, escopo_id)
    if book is None:
        raise LookupError(f"Book {escopo_id} não encontrado")
    classificacao = configuracao.carregar(sessao)
    pesos = {
        ativo.id: percentual
        for ativo in sessao.scalars(select(Ativo))
        for candidato, percentual in classificacao.books_do_ativo(ativo)
        if candidato.id == escopo_id
    }
    return book.nome, pesos


def _eventos_query(sessao: Session, ativo_ids: set[int], investidores: Sequence[int] | None):
    operacoes = select(
        literal("operacao").label("tipo"),
        Operacao.id.label("id"),
        Operacao.ativo_id.label("ativo_id"),
        Operacao.investidor_id.label("investidor_id"),
        Operacao.data.label("data"),
        Operacao.evento.label("evento"),
        Operacao.quantidade.label("quantidade"),
        Operacao.preco.label("preco"),
        case(
            (Operacao.evento.in_(("C", "V")), (-Operacao.quantidade * Operacao.preco - Operacao.taxas) * Operacao.cambio),
            else_=None,
        ).label("valor_brl"),
        Operacao.moeda.label("moeda"),
        Operacao.daytrade.label("daytrade"),
    ).where(Operacao.ativo_id.in_(ativo_ids))
    proventos = select(
        literal("provento").label("tipo"),
        Provento.id.label("id"),
        Provento.ativo_id.label("ativo_id"),
        Provento.investidor_id.label("investidor_id"),
        Provento.data_pagamento.label("data"),
        Provento.evento.label("evento"),
        literal(None, type_=Numeric(20, 8)).label("quantidade"),
        literal(None, type_=Numeric(20, 8)).label("preco"),
        ((Provento.valor - Provento.irrf - Provento.taxas) * Provento.cambio).label("valor_brl"),
        Provento.moeda.label("moeda"),
        literal(False).label("daytrade"),
    ).where(Provento.ativo_id.in_(ativo_ids))
    if investidores:
        operacoes = operacoes.where(Operacao.investidor_id.in_(investidores))
        proventos = proventos.where(Provento.investidor_id.in_(investidores))
    return union_all(operacoes, proventos).subquery()


def consultar(
    sessao: Session,
    escopo: Escopo,
    escopo_id: int,
    investidores: Sequence[int] | None,
    limite: int,
    deslocamento: int,
    hoje: date | None = None,
) -> dict:
    hoje = hoje or date.today()
    nome, pesos = _ativos_do_escopo(sessao, escopo, escopo_id)
    ativo_ids = set(pesos)
    linhas = {
        linha.ativo.id: linha
        for linha in montar_carteira(
            sessao, investidores, consolidado=True, somente_abertas=False, ativo_ids=ativo_ids
        )
        if linha.ativo.id in ativo_ids
    }
    posicoes = {ativo_id: linhas[ativo_id].posicao for ativo_id in ativo_ids if ativo_id in linhas}
    investido = sum(
        (posicoes[ativo_id].custo * peso for ativo_id, peso in pesos.items() if ativo_id in posicoes),
        ZERO,
    )
    mercado_parcial = ZERO
    mercado_incompleto = False
    for ativo_id, linha in linhas.items():
        if not linha.posicao.aberta:
            continue
        if linha.valor_mercado is None:
            mercado_incompleto = True
        else:
            mercado_parcial += linha.valor_mercado * pesos[ativo_id]
    mercado = None if mercado_incompleto else mercado_parcial
    lucro_aberto = mercado - investido if mercado is not None else None

    lucro_swing = sum(
        (posicoes[ativo_id].lucro_realizado * peso for ativo_id, peso in pesos.items() if ativo_id in posicoes),
        ZERO,
    )
    lucro_daytrade = sum(
        (posicoes[ativo_id].lucro_daytrade * peso for ativo_id, peso in pesos.items() if ativo_id in posicoes),
        ZERO,
    )
    liquido = (Provento.valor - Provento.irrf - Provento.taxas) * Provento.cambio
    proventos_query = select(Provento.ativo_id, func.sum(liquido)).where(
        Provento.ativo_id.in_(ativo_ids),
        Provento.data_pagamento <= hoje,
    )
    if investidores:
        proventos_query = proventos_query.where(Provento.investidor_id.in_(investidores))
    proventos_por_ativo = {
        ativo_id: Decimal(str(valor or 0))
        for ativo_id, valor in sessao.execute(proventos_query.group_by(Provento.ativo_id))
    }
    proventos_total = sum(
        (proventos_por_ativo.get(ativo_id, ZERO) * peso for ativo_id, peso in pesos.items()),
        ZERO,
    )

    corte_12m = hoje - timedelta(days=365)
    proventos_12m_query = select(Provento.ativo_id, func.sum(liquido)).where(
        Provento.ativo_id.in_(ativo_ids),
        Provento.data_pagamento > corte_12m,
        Provento.data_pagamento <= hoje,
    )
    if investidores:
        proventos_12m_query = proventos_12m_query.where(Provento.investidor_id.in_(investidores))
    proventos_12m_por_ativo = {
        ativo_id: Decimal(str(valor or 0))
        for ativo_id, valor in sessao.execute(proventos_12m_query.group_by(Provento.ativo_id))
    }
    proventos_12m = sum(
        (proventos_12m_por_ativo.get(ativo_id, ZERO) * peso for ativo_id, peso in pesos.items()),
        ZERO,
    )
    yoc_12m = proventos_12m / investido if investido > 0 else None
    lucro_total = (
        lucro_aberto + lucro_swing + lucro_daytrade + proventos_total
        if lucro_aberto is not None
        else None
    )
    distribuicao = [
        {"categoria": "aberto", "rotulo": "Lucro aberto", "valor": lucro_aberto},
        {"categoria": "swing", "rotulo": "Trades swing", "valor": lucro_swing},
        {"categoria": "daytrade", "rotulo": "Day trade", "valor": lucro_daytrade},
        {"categoria": "proventos", "rotulo": "Proventos líquidos", "valor": proventos_total},
    ]

    if not ativo_ids:
        return {
            "escopo": escopo,
            "escopo_id": escopo_id,
            "nome": nome,
            "ativos": 0,
            "investido": ZERO,
            "mercado": ZERO,
            "lucro_aberto": ZERO,
            "lucro_swing": ZERO,
            "lucro_daytrade": ZERO,
            "proventos_total": ZERO,
            "proventos_12m": ZERO,
            "yoc_12m": None,
            "lucro_total": ZERO,
            "distribuicao": distribuicao,
            "total_eventos": 0,
            "eventos": [],
            "limite": limite,
            "deslocamento": deslocamento,
        }

    eventos = _eventos_query(sessao, ativo_ids, investidores)
    total_eventos = sessao.scalar(select(func.count()).select_from(eventos)) or 0
    tickers = dict(sessao.execute(select(Ativo.id, Ativo.ticker).where(Ativo.id.in_(ativo_ids))).all())
    itens_eventos = []
    for evento in sessao.execute(
        select(eventos)
        .order_by(eventos.c.data, eventos.c.id, eventos.c.tipo)
        .limit(limite)
        .offset(deslocamento)
    ):
        peso = pesos[evento.ativo_id]
        rotulo = (
            EVENTOS_OPERACAO.get(evento.evento, evento.evento)
            if evento.tipo == "operacao"
            else EVENTOS_PROVENTO.get(evento.evento, evento.evento)
        )
        itens_eventos.append(
            {
                "id": evento.id,
                "ativo_id": evento.ativo_id,
                "ticker": tickers[evento.ativo_id],
                "data": evento.data,
                "tipo": evento.tipo,
                "evento": evento.evento,
                "rotulo": rotulo,
                "investidor_id": evento.investidor_id,
                "quantidade": evento.quantidade,
                "preco": evento.preco,
                "valor_brl": Decimal(str(evento.valor_brl)) * peso if evento.valor_brl is not None else None,
                "moeda": evento.moeda,
                "daytrade": evento.daytrade,
                "participacao": peso,
            }
        )
    return {
        "escopo": escopo,
        "escopo_id": escopo_id,
        "nome": nome,
        "ativos": len(ativo_ids),
        "investido": investido,
        "mercado": mercado,
        "lucro_aberto": lucro_aberto,
        "lucro_swing": lucro_swing,
        "lucro_daytrade": lucro_daytrade,
        "proventos_total": proventos_total,
        "proventos_12m": proventos_12m,
        "yoc_12m": yoc_12m,
        "lucro_total": lucro_total,
        "distribuicao": distribuicao,
        "total_eventos": total_eventos,
        "eventos": itens_eventos,
        "limite": limite,
        "deslocamento": deslocamento,
    }
