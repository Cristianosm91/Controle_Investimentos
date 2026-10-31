"""Orquestra a apuração fiscal com dados persistidos e mantém a interface do serviço."""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Ativo, DarfPago, Operacao, PrejuizoInicial, Provento, RegraFiscal
from . import parametros as param
from .ir_calculo import (
    REGRAS_PADRAO,
    ZERO,
    AnoExterior,
    Fato,  # noqa: F401
    MesIR,
    OperacaoIR,
    Regra,
    apurar_exterior,
    apurar_mensal,
    categoria_ir,
    fatos_por_mes,
    mes,
    regra_vigente,  # noqa: F401
)
from .posicao import Movimento


def carregar_regras(sessao: Session) -> list[Regra]:
    linhas = sessao.scalars(select(RegraFiscal)).all()
    if not linhas:
        return list(REGRAS_PADRAO)
    return [
        Regra(r.categoria, r.vigencia_inicio, r.vigencia_fim, r.aliquota, r.limite_isencao, r.apuracao) for r in linhas
    ]


def carregar_operacoes(sessao: Session, investidor_id: int) -> list[OperacaoIR]:
    consulta = (
        select(Operacao, Ativo.ticker, Ativo.classe, Ativo.moeda)
        .join(Ativo, Ativo.id == Operacao.ativo_id)
        .where(Operacao.investidor_id == investidor_id)
    )
    return [
        OperacaoIR(
            Movimento(o.investidor_id, o.ativo_id, o.data, o.evento, o.quantidade, o.preco, o.taxas, o.daytrade, o.id, o.cambio),
            ticker, classe, moeda, o.irrf,
        )
        for o, ticker, classe, moeda in sessao.execute(consulta)
    ]


def _proventos_exterior(sessao: Session, investidor_id: int) -> dict[int, tuple[Decimal, Decimal]]:
    """(rendimento bruto, imposto retido no exterior) em BRL por ano."""
    consulta = (
        select(Provento.data_pagamento, Provento.valor, Provento.irrf, Provento.cambio, Ativo.classe, Ativo.moeda)
        .join(Ativo, Ativo.id == Provento.ativo_id)
        .where(Provento.investidor_id == investidor_id, Provento.evento != "AMORTIZACAO")
    )
    por_ano: dict[int, tuple[Decimal, Decimal]] = {}
    for dia, valor, irrf, cambio, classe, moeda in sessao.execute(consulta):
        if categoria_ir(classe, moeda, False) != "EXTERIOR":
            continue
        bruto, retido = por_ano.get(dia.year, (ZERO, ZERO))
        por_ano[dia.year] = (bruto + valor * cambio, retido + irrf * cambio)
    return por_ano


def carregar_prejuizos(sessao: Session, investidor_id: int) -> dict[str, Decimal]:
    consulta = select(PrejuizoInicial).where(PrejuizoInicial.investidor_id == investidor_id)
    return {p.grupo: p.valor for p in sessao.scalars(consulta)}


def carregar_pagos(sessao: Session, investidor_id: int) -> dict[date, Decimal]:
    pagos: dict[date, Decimal] = defaultdict(lambda: ZERO)
    for darf in sessao.scalars(select(DarfPago).where(DarfPago.investidor_id == investidor_id)):
        pagos[mes(darf.competencia)] += darf.valor
    return dict(pagos)


@dataclass
class ApuracaoIR:
    meses: list[MesIR]
    exterior: list[AnoExterior]
    nao_apurados: list[str]


def apurar(sessao: Session, investidor_id: int, hoje: date | None = None) -> ApuracaoIR:
    p = param.carregar(sessao)
    regras = carregar_regras(sessao)
    fatos, ignorados = fatos_por_mes(
        carregar_operacoes(sessao, investidor_id), p.ir_bdr_como_acao, p.ir_subscricao_fii_isenta
    )
    somar_no_limite = {
        categoria
        for categoria, ativo in (
            ("DAYTRADE", p.ir_daytrade_no_limite), ("OPCAO", p.ir_opcoes_no_limite),
            ("BDR", p.ir_outras_classes_no_limite), ("ETF", p.ir_outras_classes_no_limite),
        )
        if ativo
    }
    prejuizos = carregar_prejuizos(sessao, investidor_id)
    proventos_ext = _proventos_exterior(sessao, investidor_id)
    fim = mes(hoje or date.today())

    meses_bolsa = [competencia for competencia, categoria in fatos if categoria != "EXTERIOR"]
    if p.ir_ano_inicio:
        inicio = date(p.ir_ano_inicio, 1, 1)
    else:
        inicio = date(min(meses_bolsa).year, 1, 1) if meses_bolsa else fim
    meses = apurar_mensal(
        fatos, regras, inicio, max(fim, *meses_bolsa) if meses_bolsa else fim, prejuizos,
        carregar_pagos(sessao, investidor_id), somar_no_limite,
    )

    anos_ext = {competencia.year for competencia, categoria in fatos if categoria == "EXTERIOR"} | set(proventos_ext)
    if p.ir_ano_inicio:
        anos_ext = {ano for ano in anos_ext if ano >= p.ir_ano_inicio}
    anos_ext = set(range(min(anos_ext), fim.year + 1)) if anos_ext else set()
    exterior = apurar_exterior(fatos, regras, anos_ext, proventos_ext, prejuizos.get("EXTERIOR", ZERO))
    return ApuracaoIR(meses, exterior, sorted(ignorados))
