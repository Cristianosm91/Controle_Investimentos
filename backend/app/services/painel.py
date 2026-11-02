"""Composição das visões de rentabilidade (Resumo, Dashboard, matriz de proventos) para a API."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import extract, func, select
from sqlalchemy.orm import Session

from ..models import Ativo, Provento
from . import rentabilidade as r
from .caixa import calcular_valor_investido
from .posicao import ZERO

_BENCHMARKS = ("ibov", "ifix", "cdi", "ipca")


@dataclass
class LinhaMensal:
    mes: r.Mes
    twr_acumulado: Decimal
    benchmark: r.Benchmark
    acumulados: dict[str, Decimal | None]


def _calcular(sessao: Session, investidor_ids: Sequence[int] | None, ate: date, classe: str | None = None):
    ativo_ids = None
    if classe:
        ativo_ids = list(sessao.scalars(select(Ativo.id).where(Ativo.classe == classe)))
    dados = r.carregar_dados(sessao, investidor_ids, ativo_ids)
    proventos = [(d, v) for _, _, d, v in dados.proventos]
    serie = r.serie_mensal(dados.movimentos, proventos, dados.precificacao, ate)
    bench = r.benchmarks_mensais(r.indices(sessao), [m.data for m in serie])
    return dados, serie, bench


def _janela(serie: list[r.Mes], bench: list[r.Benchmark], inicio: date | None, fim: date | None) -> list[LinhaMensal]:
    """Recorta a série e recalcula os acumulados a partir do início da janela."""
    pares = [
        (m, b) for m, b in zip(serie, bench, strict=True) if (not inicio or m.data >= inicio) and (not fim or m.data <= fim)
    ]
    twr_acc = r.acumular(m.twr for m, _ in pares)
    acumulados = {nome: r.acumular(getattr(b, nome) for _, b in pares) for nome in _BENCHMARKS}
    return [
        LinhaMensal(m, twr_acc[i] or ZERO, b, {nome: acumulados[nome][i] for nome in _BENCHMARKS})
        for i, (m, b) in enumerate(pares)
    ]


def mensal(
    sessao: Session, investidor_ids: Sequence[int] | None, inicio: date | None, fim: date | None,
    classe: str | None = None,
) -> list[LinhaMensal]:
    _, serie, bench = _calcular(sessao, investidor_ids, date.today(), classe)
    return _janela(serie, bench, inicio, fim)


@dataclass
class Janela:
    nome: str
    inicio: date
    twr: Decimal | None
    benchmarks: dict[str, Decimal | None]


@dataclass
class Resumo:
    data_referencia: date | None
    patrimonio: Decimal
    investido: Decimal
    lucro_realizado: Decimal
    proventos_total: Decimal
    aluguel_total: Decimal
    proventos_12m: Decimal
    tir_aa: float | None
    janelas: list[Janela]
    proventos_mensais: list[tuple[date, Decimal]]


def resumo(sessao: Session, investidor_ids: Sequence[int] | None, classe: str | None = None) -> Resumo:
    hoje = date.today()
    dados, serie, bench = _calcular(sessao, investidor_ids, hoje, classe)
    if not serie:
        return Resumo(None, ZERO, ZERO, ZERO, ZERO, ZERO, ZERO, None, [], [])

    atual = serie[-1]
    fim_mes_atual = atual.data
    inicio_ano = date(fim_mes_atual.year, 1, 31)
    um_ano = r.fim_do_mes(fim_mes_atual.replace(day=1) - timedelta(days=330))
    janelas = []
    for nome, inicio in (("Mês", fim_mes_atual), ("Ano", inicio_ano), ("12 meses", um_ano), ("Desde o início", serie[0].data)):
        linhas = _janela(serie, bench, inicio, None)
        if not linhas:
            continue
        ultimo = linhas[-1]
        janelas.append(Janela(nome, linhas[0].mes.data.replace(day=1), ultimo.twr_acumulado, ultimo.acumulados))

    corte_12m = hoje - timedelta(days=365)
    filtros_aluguel = [Provento.evento == "ALUGUEL", Provento.data_pagamento <= hoje]
    if investidor_ids:
        filtros_aluguel.append(Provento.investidor_id.in_(investidor_ids))
    if classe:
        filtros_aluguel.append(Provento.ativo_id.in_(select(Ativo.id).where(Ativo.classe == classe)))
    liquido = (Provento.valor - Provento.irrf - Provento.taxas) * Provento.cambio
    aluguel_total = Decimal(str(sessao.scalar(select(func.sum(liquido)).where(*filtros_aluguel)) or 0))
    aluguel_12m = Decimal(str(
        sessao.scalar(select(func.sum(liquido)).where(*filtros_aluguel, Provento.data_pagamento > corte_12m)) or 0
    ))
    proventos_12m = sum((v for _, _, d, v in dados.proventos if d > corte_12m), ZERO) - aluguel_12m
    lucro_realizado = sum((m.lucro_trades + m.lucro_daytrade for m in serie), ZERO)
    tir = r.tir(dados.movimentos, [(d, v) for _, _, d, v in dados.proventos], atual.mercado, hoje)
    investido = calcular_valor_investido(
        sessao, investidor_ids, classes_incluidas=[classe] if classe else None
    ).valor_investido
    return Resumo(
        data_referencia=r.ultima_data_cotacao(sessao),
        patrimonio=atual.mercado,
        investido=investido,
        lucro_realizado=lucro_realizado,
        proventos_total=sum((v for _, _, _, v in dados.proventos), ZERO) - aluguel_total,
        aluguel_total=aluguel_total,
        proventos_12m=proventos_12m,
        tir_aa=tir,
        janelas=janelas,
        proventos_mensais=[(m.data, m.proventos) for m in serie[-12:]],
    )


# ---------- métricas por posição ----------

@dataclass
class MetricasPosicao:
    proventos_12m: Decimal
    yoc_12m: Decimal | None
    tir_aa: float | None


def metricas_posicoes(
    sessao: Session, investidor_ids: Sequence[int] | None, valores: dict[tuple[int | None, int], tuple[Decimal, Decimal | None]]
) -> dict[tuple[int | None, int], MetricasPosicao]:
    """`valores`: chave (investidor ou None se consolidado, ativo) -> (capital investido, valor de mercado)."""
    dados = r.carregar_dados(sessao, investidor_ids)
    consolidado = any(inv is None for inv, _ in valores)
    chave = (lambda inv, ativo: (None, ativo)) if consolidado else (lambda inv, ativo: (inv, ativo))

    movs: dict[tuple, list] = {}
    for m in dados.movimentos:
        movs.setdefault(chave(m.investidor_id, m.ativo_id), []).append(m)
    provs: dict[tuple, list[tuple[date, Decimal]]] = {}
    for inv, ativo, d, v in dados.proventos:
        provs.setdefault(chave(inv, ativo), []).append((d, v))

    hoje = date.today()
    corte = hoje - timedelta(days=365)
    resultado = {}
    for k, (custo, mercado) in valores.items():
        p12 = sum((v for d, v in provs.get(k, []) if d > corte), ZERO)
        taxa = r.tir(movs.get(k, []), provs.get(k, []), mercado, hoje) if mercado is not None else None
        resultado[k] = MetricasPosicao(p12, p12 / custo if custo else None, taxa)
    return resultado


# ---------- matriz de proventos ----------

@dataclass
class Matriz:
    titulo_linhas: str
    linhas: list[str]
    valores: list[list[Decimal]]


def matriz_proventos(
    sessao: Session, investidor_ids: Sequence[int] | None, ano: int | None, classe: str | None = None
) -> Matriz:
    """Sem ano: linhas = anos. Com ano: linhas = ativos daquele ano. Colunas = meses; valores líquidos em BRL."""
    liquido = func.sum((Provento.valor - Provento.irrf - Provento.taxas) * Provento.cambio)
    mes = extract("month", Provento.data_pagamento)
    if ano:
        rotulo = Ativo.ticker
        consulta = (
            select(rotulo, mes, liquido)
            .join(Ativo, Ativo.id == Provento.ativo_id)
            .where(extract("year", Provento.data_pagamento) == ano)
        )
    else:
        rotulo = extract("year", Provento.data_pagamento)
        consulta = select(rotulo, mes, liquido)
    if classe:
        if not ano:
            consulta = consulta.join(Ativo, Ativo.id == Provento.ativo_id)
        consulta = consulta.where(Ativo.classe == classe)
    if investidor_ids:
        consulta = consulta.where(Provento.investidor_id.in_(investidor_ids))

    tabela: dict[str, list[Decimal]] = {}
    for linha, m, v in sessao.execute(consulta.group_by(rotulo, mes)):
        tabela.setdefault(str(linha), [ZERO] * 12)[int(m) - 1] = Decimal(str(v or 0))
    linhas = sorted(tabela, key=lambda k: -sum(tabela[k])) if ano else sorted(tabela)
    return Matriz("Ativo" if ano else "Ano", linhas, [tabela[k] for k in linhas])
