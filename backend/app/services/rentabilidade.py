"""Rentabilidade: série mensal (como a aba `dashboard.` da planilha), TWR, TIR (XIRR) e YoC.

Funções puras recebem movimentos, proventos e séries de preço/câmbio já carregados; o
carregamento do banco fica em `carregar_dados`.

Convenções (iguais às da planilha):
- investido = custo das posições abertas no fim do mês (em BRL);
- fluxo = Δ investido − proventos − lucro de trades − lucro de day trade
  (dinheiro que entrou na carteira; proventos e lucros realizados contam como retirados);
- lucro do mês = mercado_fim − mercado_ini − fluxo;
- TWR do mês = lucro / (mercado_ini + max(fluxo, 0)); acumulado = Π(1 + TWR) − 1.
"""

import bisect
import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from ..db import ano_mes
from ..models import Ativo, Cotacao, CotacaoMoeda, IndiceMensal, Operacao, Provento
from .posicao import ZERO, Carteira, Movimento, Posicao, ordenar

UM = Decimal(1)


# ---------- séries de preço ----------

class Serie:
    """Valores datados com consulta "último valor até a data" (carry-forward)."""

    def __init__(self, pontos: Iterable[tuple[date, Decimal]]):
        ordenados = sorted(pontos)
        self._datas = [d for d, _ in ordenados]
        self._valores = [v for _, v in ordenados]

    def em(self, dia: date) -> Decimal | None:
        i = bisect.bisect_right(self._datas, dia)
        return self._valores[i - 1] if i else None


def fim_do_mes(dia: date) -> date:
    proximo = (dia.replace(day=28) + timedelta(days=4)).replace(day=1)
    return proximo - timedelta(days=1)


def meses(inicio: date, fim: date) -> list[date]:
    """Últimos dias de cada mês de `inicio` até `fim` (inclusive)."""
    resultado, dia = [], fim_do_mes(inicio)
    while dia <= fim_do_mes(fim):
        resultado.append(dia)
        dia = fim_do_mes(dia + timedelta(days=1))
    return resultado


@dataclass
class Precificacao:
    precos: dict[int, Serie]
    cambios: dict[str, Serie]
    moeda_ativo: dict[int, str]

    def valor(self, p: Posicao, dia: date) -> tuple[Decimal, bool]:
        """Valor de mercado em BRL; sem cotação/câmbio, usa o custo (bool indica a falta)."""
        serie = self.precos.get(p.ativo_id)
        preco = serie.em(dia) if serie else None
        moeda = self.moeda_ativo.get(p.ativo_id, "BRL")
        cambio = UM if moeda == "BRL" else (self.cambios[moeda].em(dia) if moeda in self.cambios else None)
        if preco is None or cambio is None:
            return p.custo, False
        return p.quantidade * preco * cambio, True


# ---------- série mensal ----------

@dataclass
class Mes:
    data: date
    investido: Decimal
    mercado: Decimal
    proventos: Decimal
    lucro_trades: Decimal
    lucro_daytrade: Decimal
    fluxo: Decimal
    lucro: Decimal
    twr: Decimal
    twr_acumulado: Decimal
    sem_cotacao: list[int] = field(default_factory=list)


def serie_mensal(
    movimentos: Iterable[Movimento],
    proventos: Iterable[tuple[date, Decimal]],
    precificacao: Precificacao,
    ate: date,
    desde: date | None = None,
) -> list[Mes]:
    movs = ordenar(movimentos)
    if not movs:
        return []
    prov_mes: dict[date, Decimal] = {}
    for dia, valor in proventos:
        chave = fim_do_mes(dia)
        prov_mes[chave] = prov_mes.get(chave, ZERO) + valor

    carteira = Carteira()
    i = 0
    resultado: list[Mes] = []
    investido_ant = mercado_ant = ZERO
    acumulado = UM
    for fim in meses(desde or movs[0].data, ate):
        trades = daytrade = ZERO
        while i < len(movs) and movs[i].data <= fim:
            lucro = carteira.aplicar(movs[i])
            if movs[i].daytrade:
                daytrade += lucro
            else:
                trades += lucro
            i += 1

        investido = mercado = ZERO
        sem_cotacao = []
        for p in carteira.posicoes.values():
            if not p.aberta:
                continue
            investido += p.custo
            valor, cotado = precificacao.valor(p, min(fim, ate))
            mercado += valor
            if not cotado:
                sem_cotacao.append(p.ativo_id)

        prov = prov_mes.get(fim, ZERO)
        fluxo = investido - investido_ant - prov - trades - daytrade
        lucro_mes = mercado - mercado_ant - fluxo
        base = mercado_ant + max(fluxo, ZERO)
        twr = lucro_mes / base if base else ZERO
        acumulado *= UM + twr
        resultado.append(
            Mes(fim, investido, mercado, prov, trades, daytrade, fluxo, lucro_mes, twr, acumulado - UM, sem_cotacao)
        )
        investido_ant, mercado_ant = investido, mercado
    return resultado


# ---------- TIR (XIRR) ----------

def caixa(m: Movimento) -> Decimal:
    """Dinheiro do ponto de vista do investidor (saída < 0) gerado pelo movimento, em BRL.

    Transferências entram/saem pelo custo informado para que a TIR por ativo continue coerente
    numa troca de ticker; na carteira total elas se anulam.
    """
    ev, q = m.evento, m.quantidade
    if ev == "C" or (ev == "TRANSFERENCIA" and q > 0):
        return -(q * m.preco + m.taxas + m.irrf) * m.cambio
    if ev in ("V", "VENDA_SUBSCRICAO") or ev == "TRANSFERENCIA":
        return (-q * m.preco - m.taxas - m.irrf) * m.cambio
    if ev == "AMORTIZACAO":
        return (-q * m.preco - m.irrf) * m.cambio
    return ZERO


def xirr(fluxos: Sequence[tuple[date, float]]) -> float | None:
    """Taxa anual que zera o VPL dos fluxos (convenção 365 dias). None se não houver solução."""
    fluxos = [(d, v) for d, v in fluxos if v]
    if not fluxos or all(v >= 0 for _, v in fluxos) or all(v <= 0 for _, v in fluxos):
        return None
    inicio = min(d for d, _ in fluxos)
    anos = [((d - inicio).days / 365.0, v) for d, v in fluxos]

    def vpl(taxa: float) -> float:
        return sum(v / (1 + taxa) ** t for t, v in anos)

    def derivada(taxa: float) -> float:
        return sum(-t * v / (1 + taxa) ** (t + 1) for t, v in anos)

    taxa = 0.1
    for _ in range(50):
        try:
            f, df = vpl(taxa), derivada(taxa)
        except (OverflowError, ZeroDivisionError):
            break
        if df == 0:
            break
        nova = taxa - f / df
        if nova <= -0.9999 or not math.isfinite(nova):
            break
        if abs(nova - taxa) < 1e-10:
            return nova
        taxa = nova

    # Newton não convergiu: bissecção num intervalo amplo.
    baixo, alto = -0.9999, 10.0
    try:
        f_baixo, f_alto = vpl(baixo), vpl(alto)
    except OverflowError:
        return None
    if f_baixo * f_alto > 0:
        return None
    for _ in range(200):
        meio = (baixo + alto) / 2
        f_meio = vpl(meio)
        if abs(f_meio) < 1e-7:
            return meio
        if f_baixo * f_meio < 0:
            alto = meio
        else:
            baixo, f_baixo = meio, f_meio
    return (baixo + alto) / 2


def ao_mes(taxa_anual: float | None) -> float | None:
    return None if taxa_anual is None else (1 + taxa_anual) ** (1 / 12) - 1


def tir(
    movimentos: Iterable[Movimento],
    proventos: Iterable[tuple[date, Decimal]],
    valor_final: Decimal,
    data_final: date,
) -> float | None:
    """TIR anual: operações + proventos líquidos + valor de mercado em `data_final` como resgate."""
    fluxos = [(m.data, float(caixa(m))) for m in movimentos]
    fluxos += [(d, float(v)) for d, v in proventos]
    fluxos.append((data_final, float(valor_final)))
    return xirr(fluxos)


# ---------- benchmarks ----------

@dataclass
class Benchmark:
    data: date
    ibov: Decimal | None
    ifix: Decimal | None
    cdi: Decimal | None
    ipca: Decimal | None
    selic: Decimal | None
    igpm: Decimal | None


def _variacao(atual: IndiceMensal | None, anterior: IndiceMensal | None, coluna: str) -> Decimal | None:
    a, b = getattr(atual, coluna, None), getattr(anterior, coluna, None)
    return a / b - 1 if a and b else None


def benchmarks_mensais(indices: Iterable[IndiceMensal], datas: Sequence[date]) -> list[Benchmark]:
    """Variação mensal de cada índice nas datas pedidas (IBOV/IFIX a partir do nível de fechamento)."""
    por_mes = {fim_do_mes(i.competencia): i for i in indices}
    resultado = []
    for fim in datas:
        atual = por_mes.get(fim)
        anterior = por_mes.get(fim_do_mes(fim.replace(day=1) - timedelta(days=1)))
        resultado.append(
            Benchmark(
                fim, _variacao(atual, anterior, "ibov"), _variacao(atual, anterior, "ifix"),
                *(getattr(atual, c, None) for c in ("cdi", "ipca", "selic", "igpm")),
            )
        )
    return resultado


def acumular(variacoes: Iterable[Decimal | None]) -> list[Decimal | None]:
    """Acumulado composto; meses sem dado repetem o acumulado anterior (None até o primeiro dado)."""
    resultado, acumulado = [], None
    for v in variacoes:
        if v is not None:
            acumulado = (acumulado if acumulado is not None else UM) * (UM + v)
        resultado.append(None if acumulado is None else acumulado - UM)
    return resultado


# ---------- carga do banco ----------

@dataclass
class DadosRentabilidade:
    movimentos: list[Movimento]
    proventos: list[tuple[int, int, date, Decimal]]  # investidor, ativo, data, líquido em BRL
    precificacao: Precificacao


def _ultimos_do_mes(sessao: Session, chave, filtro, modelo):
    """Último registro de cada mês por chave (a série mensal só consulta datas de fim de mês).

    (chave, data) é única em Cotacao e CotacaoMoeda, então o join com o max(data) do mês traz uma linha só.
    """
    valor = modelo.preco if modelo is Cotacao else modelo.valor
    ultimos = (
        select(chave.label("chave"), func.max(modelo.data).label("data"))
        .where(filtro)
        .group_by(chave, ano_mes(sessao, modelo.data))
        .subquery()
    )
    consulta = select(chave, modelo.data, valor).join(
        ultimos, and_(chave == ultimos.c.chave, modelo.data == ultimos.c.data)
    )
    for k, dia, v in sessao.execute(consulta):
        yield k, dia if isinstance(dia, date) else date.fromisoformat(dia), Decimal(str(v))


def carregar_dados(
    sessao: Session,
    investidor_ids: Sequence[int] | None,
    ativo_ids: Sequence[int] | None = None,
) -> DadosRentabilidade:
    filtros_op = []
    filtros_prov = []
    if investidor_ids:
        filtros_op.append(Operacao.investidor_id.in_(investidor_ids))
        filtros_prov.append(Provento.investidor_id.in_(investidor_ids))
    if ativo_ids is not None:
        filtros_op.append(Operacao.ativo_id.in_(ativo_ids))
        filtros_prov.append(Provento.ativo_id.in_(ativo_ids))
    filtros_op.append(Operacao.data <= date.today())
    filtros_prov.append(Provento.data_pagamento <= date.today())

    movimentos = [
        Movimento(
            r.investidor_id, r.ativo_id, r.data, r.evento, r.quantidade, r.preco, r.taxas, r.daytrade, r.id,
            r.cambio, r.irrf,
        )
        for r in sessao.execute(
            select(
                Operacao.investidor_id, Operacao.ativo_id, Operacao.data, Operacao.evento, Operacao.quantidade,
                Operacao.preco, Operacao.taxas, Operacao.daytrade, Operacao.id, Operacao.cambio, Operacao.irrf,
            ).where(*filtros_op)
        )
    ]

    liquido = (Provento.valor - Provento.irrf - Provento.taxas) * Provento.cambio
    proventos = [
        (i, a, d, Decimal(str(v)))
        for i, a, d, v in sessao.execute(
            select(Provento.investidor_id, Provento.ativo_id, Provento.data_pagamento, liquido).where(*filtros_prov)
        )
    ]

    ids_ativos = set(ativo_ids or ()) | {m.ativo_id for m in movimentos}
    moeda_ativo = (
        {a: m for a, m in sessao.execute(select(Ativo.id, Ativo.moeda).where(Ativo.id.in_(ids_ativos)))}
        if ids_ativos
        else {}
    )

    pontos: dict[int, list[tuple[date, Decimal]]] = {}
    if ids_ativos:
        for ativo_id, dia, preco in _ultimos_do_mes(
            sessao, Cotacao.ativo_id, Cotacao.ativo_id.in_(ids_ativos), Cotacao
        ):
            pontos.setdefault(ativo_id, []).append((dia, preco))

    cambios: dict[str, list[tuple[date, Decimal]]] = {}
    moedas = {m for m in moeda_ativo.values() if m != "BRL"}
    if moedas:
        for moeda, dia, valor in _ultimos_do_mes(
            sessao, CotacaoMoeda.moeda, CotacaoMoeda.moeda.in_(moedas), CotacaoMoeda
        ):
            cambios.setdefault(moeda, []).append((dia, valor))

    precificacao = Precificacao(
        {a: Serie(p) for a, p in pontos.items()}, {m: Serie(p) for m, p in cambios.items()}, moeda_ativo
    )
    return DadosRentabilidade(movimentos, proventos, precificacao)


def indices(sessao: Session) -> list[IndiceMensal]:
    return list(sessao.scalars(select(IndiceMensal).order_by(IndiceMensal.competencia)))


def ultima_data_cotacao(sessao: Session) -> date | None:
    return sessao.scalar(select(func.max(Cotacao.data)))
