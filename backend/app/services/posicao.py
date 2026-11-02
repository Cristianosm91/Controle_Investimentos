"""Cálculo de posição, preço médio e lucro realizado (funções puras, sem I/O).

Custo, preço médio e lucro são sempre em BRL: preço e taxas de cada movimento são
convertidos pelo câmbio da data (PTAX), como exige a apuração de IR.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

ZERO = Decimal(0)
_RESIDUO = Decimal("1e-9")


@dataclass(frozen=True)
class Movimento:
    investidor_id: int
    ativo_id: int
    data: date
    evento: str
    quantidade: Decimal
    preco: Decimal = ZERO
    taxas: Decimal = ZERO
    daytrade: bool = False
    ordem: int = 0
    cambio: Decimal = Decimal(1)
    irrf: Decimal = ZERO


@dataclass
class Posicao:
    investidor_id: int
    ativo_id: int
    quantidade: Decimal = ZERO
    custo: Decimal = ZERO
    lucro_realizado: Decimal = ZERO
    lucro_daytrade: Decimal = ZERO
    data_inicio: date | None = None

    @property
    def preco_medio(self) -> Decimal:
        return self.custo / self.quantidade if self.quantidade else ZERO

    @property
    def aberta(self) -> bool:
        return self.quantidade > _RESIDUO


@dataclass(frozen=True)
class ResultadoInvestimento:
    valor_investido: Decimal
    capital_por_posicao: dict[tuple[int, int], Decimal]

    @property
    def valor_investido_posicoes_abertas(self) -> Decimal:
        return self.valor_investido


@dataclass
class PosicaoInvestimento:
    quantidade: Decimal = ZERO
    capital: Decimal = ZERO


@dataclass
class TransferenciaInvestimento:
    data: date
    quantidade: Decimal
    capital: Decimal


def calcular_investimento(movimentos: Iterable[Movimento]) -> ResultadoInvestimento:
    """Calcula o desembolso ainda associado às posições abertas."""
    posicoes: dict[tuple[int, int], PosicaoInvestimento] = {}
    transferencias: dict[int, list[TransferenciaInvestimento]] = {}

    def reduzir(posicao: PosicaoInvestimento, quantidade: Decimal) -> Decimal:
        if quantidade <= 0 or posicao.quantidade <= 0:
            return ZERO
        quantidade = min(quantidade, posicao.quantidade)
        capital = (
            posicao.capital
            if quantidade == posicao.quantidade
            else posicao.capital * quantidade / posicao.quantidade
        )
        posicao.quantidade -= quantidade
        posicao.capital -= capital
        if posicao.quantidade <= _RESIDUO:
            posicao.quantidade = ZERO
            posicao.capital = ZERO
        return capital

    for movimento in ordenar(movimentos):
        chave = (movimento.investidor_id, movimento.ativo_id)
        posicao = posicoes.setdefault(chave, PosicaoInvestimento())
        evento, quantidade = movimento.evento, movimento.quantidade

        if evento == "C":
            desembolso = (quantidade * movimento.preco + movimento.taxas + movimento.irrf) * movimento.cambio
            if not movimento.daytrade:
                posicao.quantidade += quantidade
                posicao.capital += desembolso
        elif evento == "V" and not movimento.daytrade:
            reduzir(posicao, -quantidade)
        elif evento in ("BONIFICACAO", "DESDOBRAMENTO") and not movimento.daytrade:
            posicao.quantidade = max(ZERO, posicao.quantidade + quantidade)
            if posicao.quantidade == ZERO:
                posicao.capital = ZERO
        elif evento == "TRANSFERENCIA" and quantidade < 0:
            capital = reduzir(posicao, -quantidade)
            transferencias.setdefault(movimento.investidor_id, []).append(
                TransferenciaInvestimento(movimento.data, -quantidade, capital)
            )
        elif evento == "TRANSFERENCIA" and quantidade > 0:
            posicao.quantidade += quantidade
            restante = quantidade
            pendentes = transferencias.setdefault(movimento.investidor_id, [])
            for transferencia in sorted(pendentes, key=lambda t: abs((movimento.data - t.data).days)):
                if restante <= 0 or abs((movimento.data - transferencia.data).days) > 7:
                    continue
                movida = min(restante, transferencia.quantidade)
                capital = (
                    transferencia.capital
                    if movida == transferencia.quantidade
                    else transferencia.capital * movida / transferencia.quantidade
                )
                posicao.capital += capital
                transferencia.quantidade -= movida
                transferencia.capital -= capital
                restante -= movida

    capital_por_posicao = {
        chave: posicao.capital
        for chave, posicao in posicoes.items()
        if posicao.quantidade > _RESIDUO
    }
    aberto = sum(capital_por_posicao.values(), ZERO)
    return ResultadoInvestimento(aberto, capital_por_posicao)


def _zerar_residuo(p: Posicao) -> None:
    if abs(p.quantidade) < _RESIDUO:
        p.quantidade = ZERO
        p.custo = ZERO


def _entrada(p: Posicao, m: Movimento) -> Decimal:
    if not p.aberta:
        p.data_inicio = m.data
    p.custo += (m.quantidade * m.preco + m.taxas + m.irrf) * m.cambio
    p.quantidade += m.quantidade
    return ZERO


def _saida(p: Posicao, m: Movimento, realiza_lucro: bool) -> Decimal:
    saida = -m.quantidade
    pm = p.preco_medio
    p.custo -= pm * saida
    p.quantidade -= saida
    _zerar_residuo(p)
    return (saida * m.preco - m.taxas - m.irrf) * m.cambio - pm * saida if realiza_lucro else ZERO


def aplicar(p: Posicao, m: Movimento) -> Decimal:
    """Aplica o movimento à posição e devolve o lucro realizado por ele."""
    ev, q = m.evento, m.quantidade
    if ev in ("C", "BONIFICACAO") or (ev == "TRANSFERENCIA" and q > 0):
        return _entrada(p, m)
    if ev == "V":
        return _saida(p, m, realiza_lucro=True)
    if ev == "TRANSFERENCIA":
        return _saida(p, m, realiza_lucro=False)
    if ev == "VENDA_SUBSCRICAO":
        return (-q * m.preco - m.taxas - m.irrf) * m.cambio
    if ev == "DESDOBRAMENTO":
        p.quantidade += q
        _zerar_residuo(p)
        return ZERO
    if ev in ("AMORTIZACAO", "CISAO"):
        p.custo += q * m.preco * m.cambio
        return ZERO
    raise ValueError(f"Evento de operação desconhecido: {ev}")


class Carteira:
    """Aplica movimentos em ordem cronológica mantendo as posições; permite fotografar entre datas.

    Day trade não altera a posição swing; só acumula lucro em `lucro_daytrade`.
    """

    def __init__(self) -> None:
        self.posicoes: dict[tuple[int, int], Posicao] = {}
        self._daytrade: dict[tuple[int, int], Posicao] = {}

    def aplicar(self, m: Movimento) -> Decimal:
        """Aplica o movimento e devolve o lucro realizado (swing ou day trade, conforme o movimento)."""
        chave = (m.investidor_id, m.ativo_id)
        alvo = self._daytrade if m.daytrade else self.posicoes
        p = alvo.setdefault(chave, Posicao(*chave))
        lucro = aplicar(p, m)
        if m.daytrade:
            self.posicoes.setdefault(chave, Posicao(*chave)).lucro_daytrade += lucro
        else:
            p.lucro_realizado += lucro
        return lucro


def ordenar(movimentos: Iterable[Movimento]) -> list[Movimento]:
    return sorted(movimentos, key=lambda x: (x.data, x.ordem))


def calcular_posicoes(movimentos: Iterable[Movimento]) -> dict[tuple[int, int], Posicao]:
    """Posição por (investidor, ativo). Day trade não altera a posição; só acumula lucro."""
    carteira = Carteira()
    for m in ordenar(movimentos):
        carteira.aplicar(m)
    return carteira.posicoes


def consolidar(posicoes: Iterable[Posicao]) -> dict[int, Posicao]:
    """Soma posições de vários investidores por ativo (investidor_id = 0)."""
    total: dict[int, Posicao] = {}
    for p in posicoes:
        c = total.setdefault(p.ativo_id, Posicao(0, p.ativo_id))
        c.quantidade += p.quantidade
        c.custo += p.custo
        c.lucro_realizado += p.lucro_realizado
        c.lucro_daytrade += p.lucro_daytrade
        if p.aberta and p.data_inicio and (c.data_inicio is None or p.data_inicio < c.data_inicio):
            c.data_inicio = p.data_inicio
    return total
