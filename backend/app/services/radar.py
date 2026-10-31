"""Composição das métricas do Radar a partir de cotações e fundamentos armazenados."""

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from ..models import Ativo, AtivoRadar, Cotacao, Fundamento, Provento
from .carteira import carregar_posicoes, ultimas_cotacoes
from .posicao import consolidar


@dataclass
class LinhaRadar:
    ativo: Ativo
    tem_posicao: bool
    cotacao: Cotacao | None
    fundamento: Fundamento | None
    variacao_1d_pct: Decimal | None
    variacao_7d_pct: Decimal | None
    variacao_14d_pct: Decimal | None
    drawdown_60d_pct: Decimal | None
    minimo_52s: Decimal | None
    maximo_52s: Decimal | None
    preco_teto_graham: Decimal | None
    upside_graham_pct: Decimal | None
    yoc_12m: Decimal | None
    preco_alvo: Decimal | None = None


def _variacao(historico: list[Cotacao], dias: int, tolerancia: int = 5) -> Decimal | None:
    if len(historico) < 2:
        return None
    ultima = historico[-1]
    alvo = ultima.data - timedelta(days=dias)
    anteriores = [linha for linha in historico[:-1] if linha.data <= alvo]
    if not anteriores:
        return None
    base = anteriores[-1]
    if (alvo - base.data).days > tolerancia or base.preco <= 0:
        return None
    return ultima.preco / base.preco - 1


def _maxima(historico: list[Cotacao], dias: int, hoje: date) -> list[Cotacao] | None:
    if not historico:
        return None
    corte = hoje - timedelta(days=dias)
    dentro = [linha for linha in historico if corte <= linha.data <= hoje]
    if not dentro or historico[0].data > corte + timedelta(days=7):
        return None
    return dentro


def _preco_graham(ativo: Ativo, cotacao: Cotacao | None, fundamento: Fundamento | None) -> Decimal | None:
    if (
        ativo.classe.upper() in {"FII", "FIAGRO"}
        or cotacao is None
        or fundamento is None
        or cotacao.preco <= 0
        or not fundamento.preco_lucro
        or not fundamento.preco_valor_patrimonial
        or fundamento.preco_lucro <= 0
        or fundamento.preco_valor_patrimonial <= 0
    ):
        return None
    return (
        Decimal("22.5") * cotacao.preco**2 / (fundamento.preco_lucro * fundamento.preco_valor_patrimonial)
    ).sqrt()


def _yoc_por_ativo(
    sessao: Session, ativo_ids: set[int], investidores: Sequence[int] | None, hoje: date
) -> tuple[set[int], dict[int, Decimal]]:
    if not ativo_ids:
        return set(), {}
    posicoes = consolidar(p for p in carregar_posicoes(sessao, investidores).values() if p.aberta)
    custos = {ativo_id: p.custo for ativo_id, p in posicoes.items() if ativo_id in ativo_ids and p.custo > 0}
    if not custos:
        return set(), {}

    liquido = func.sum((Provento.valor - Provento.irrf - Provento.taxas) * Provento.cambio)
    consulta = select(Provento.ativo_id, liquido).where(
        Provento.ativo_id.in_(custos),
        Provento.data_pagamento > hoje - timedelta(days=365),
        Provento.data_pagamento <= hoje,
    )
    if investidores:
        consulta = consulta.where(Provento.investidor_id.in_(investidores))
    pagamentos = {ativo_id: valor for ativo_id, valor in sessao.execute(consulta.group_by(Provento.ativo_id))}
    return set(custos), {
        ativo_id: Decimal(str(pagamentos.get(ativo_id) or 0)) / custo
        for ativo_id, custo in custos.items()
        if custo
    }


def listar(
    sessao: Session, investidores: Sequence[int] | None = None, hoje: date | None = None
) -> list[LinhaRadar]:
    hoje = hoje or date.today()
    ativos = list(
        sessao.execute(
            select(AtivoRadar.ativo_id, Ativo, AtivoRadar.preco_alvo)
            .join(Ativo, Ativo.id == AtivoRadar.ativo_id)
            .order_by(Ativo.ticker)
        )
    )
    if not ativos:
        return []

    ativo_ids = {ativo_id for ativo_id, _, _ in ativos}
    cotacoes_atuais = ultimas_cotacoes(sessao, ativo_ids)
    historicos: dict[int, list[Cotacao]] = defaultdict(list)
    for cotacao in sessao.scalars(
        select(Cotacao)
        .where(
            Cotacao.ativo_id.in_(ativo_ids),
            Cotacao.data >= hoje - timedelta(days=380),
            Cotacao.data <= hoje,
        )
        .order_by(Cotacao.ativo_id, Cotacao.data)
    ):
        historicos[cotacao.ativo_id].append(cotacao)

    recentes = (
        select(
            Fundamento.id.label("id"),
            func.row_number()
            .over(
                partition_by=Fundamento.ativo_id,
                order_by=(Fundamento.data_ref.desc(), Fundamento.id.desc()),
            )
            .label("ordem"),
        )
        .where(Fundamento.ativo_id.in_(ativo_ids), Fundamento.data_ref <= hoje)
        .subquery()
    )
    fundamentos = {
        fundamento.ativo_id: fundamento
        for fundamento in sessao.scalars(
            select(Fundamento)
            .join(recentes, and_(recentes.c.id == Fundamento.id, recentes.c.ordem == 1))
        )
    }
    ativos_com_posicao, yoc = _yoc_por_ativo(sessao, ativo_ids, investidores, hoje)

    resultado = []
    for ativo_id, ativo, preco_alvo in ativos:
        cotacao = cotacoes_atuais.get(ativo_id)
        fundamento = fundamentos.get(ativo_id)
        historico = historicos[ativo_id]
        if not cotacao or not historico or historico[-1].id != cotacao.id:
            historico = []
        referencia = cotacao.data if cotacao else hoje
        completo_60d = _maxima(historico, 60, referencia)
        completo_52s = _maxima(historico, 365, referencia)
        graham = _preco_graham(ativo, cotacao, fundamento)
        resultado.append(
            LinhaRadar(
                ativo=ativo,
                tem_posicao=ativo_id in ativos_com_posicao,
                cotacao=cotacao,
                fundamento=fundamento,
                variacao_1d_pct=(
                    cotacao.preco / historico[-2].preco - 1
                    if cotacao and len(historico) >= 2 and historico[-2].preco > 0
                    else None
                ),
                variacao_7d_pct=_variacao(historico, 7),
                variacao_14d_pct=_variacao(historico, 14),
                drawdown_60d_pct=(
                    cotacao.preco / max(linha.preco for linha in completo_60d) - 1
                    if cotacao and completo_60d and max(linha.preco for linha in completo_60d) > 0
                    else None
                ),
                minimo_52s=min((linha.preco for linha in completo_52s), default=None) if completo_52s else None,
                maximo_52s=max((linha.preco for linha in completo_52s), default=None) if completo_52s else None,
                preco_teto_graham=graham,
                upside_graham_pct=graham / cotacao.preco - 1 if graham and cotacao else None,
                yoc_12m=yoc.get(ativo_id),
                preco_alvo=preco_alvo,
            )
        )
    return resultado
