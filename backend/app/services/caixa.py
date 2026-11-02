"""Saldo de caixa por corretora e moeda.

Sempre soma as movimentações lançadas na tela Caixa. A partir de `caixa_data_inicio` (Parâmetros) também
integra os lançamentos de carteira, no valor da moeda original:
compra/venda (inclusive day trade), venda de direito de subscrição, amortização em dinheiro e proventos líquidos.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from ..models import Ativo, Corretora, MovCaixa, Operacao, Provento
from . import parametros
from .carteira import cambios_atuais
from .posicao import Movimento, ResultadoInvestimento, calcular_investimento

ZERO = Decimal(0)


@dataclass
class SaldoCaixa:
    corretora_id: int | None
    moeda: str
    movimentacoes: Decimal = ZERO
    operacoes: Decimal = ZERO
    proventos: Decimal = ZERO
    corretora: str | None = None
    cambio: Decimal | None = None

    @property
    def saldo(self) -> Decimal:
        return self.movimentacoes + self.operacoes + self.proventos

    @property
    def saldo_brl(self) -> Decimal | None:
        return self.saldo * self.cambio if self.cambio is not None else None


@dataclass
class ResultadoCaixa:
    integrado_desde: date | None
    saldos: list[SaldoCaixa] = field(default_factory=list)

    @property
    def total_brl(self) -> Decimal:
        return sum((s.saldo_brl or ZERO for s in self.saldos), ZERO)


def _efeito_operacao(em_brl: bool = False):
    """Entrada (+) / saída (-) de dinheiro de cada operação, na moeda da operação."""
    q, p, t, ir = Operacao.quantidade, Operacao.preco, Operacao.taxas, Operacao.irrf
    efeito = case(
        (Operacao.evento == "C", -(q * p) - t - ir),
        (Operacao.evento.in_(("V", "VENDA_SUBSCRICAO")), -(q * p) - t - ir),
        (Operacao.evento == "AMORTIZACAO", -(q * p) - t - ir),
        else_=0,
    )
    return efeito * Operacao.cambio if em_brl else efeito


def calcular_valor_investido(
    sessao: Session,
    investidor_ids: Sequence[int] | None,
    classes_excluidas: Sequence[str] | None = None,
    ate: date | None = None,
    classes_incluidas: Sequence[str] | None = None,
) -> ResultadoInvestimento:
    """Calcula o capital de aquisição ainda associado às posições abertas."""
    data_referencia = ate or date.today()
    consulta = select(
        Operacao.id, Operacao.investidor_id, Operacao.ativo_id, Operacao.data, Operacao.evento,
        Operacao.quantidade, Operacao.preco, Operacao.taxas, Operacao.daytrade, Operacao.cambio, Operacao.irrf,
    ).where(Operacao.data <= data_referencia)
    if investidor_ids:
        consulta = consulta.where(Operacao.investidor_id.in_(investidor_ids))
    if classes_excluidas:
        consulta = consulta.join(Ativo).where(Ativo.classe.not_in(classes_excluidas))
    if classes_incluidas is not None:
        consulta = consulta.join(Ativo).where(Ativo.classe.in_(classes_incluidas))
    movimentos = [
        Movimento(
            r.investidor_id, r.ativo_id, r.data, r.evento, r.quantidade, r.preco, r.taxas,
            r.daytrade, r.id, r.cambio, r.irrf,
        )
        for r in sessao.execute(consulta)
    ]
    return calcular_investimento(movimentos)


def calcular(sessao: Session, investidor_ids: Sequence[int] | None, data_inicio: date | None = None) -> ResultadoCaixa:
    if data_inicio is None:
        data_inicio = parametros.carregar(sessao).caixa_data_inicio
    saldos: dict[tuple[int | None, str], SaldoCaixa] = {}

    def acumular(consulta, campo: str, modelo) -> None:
        if investidor_ids:
            consulta = consulta.where(modelo.investidor_id.in_(investidor_ids))
        for corretora_id, moeda, valor in sessao.execute(consulta):
            s = saldos.setdefault((corretora_id, moeda), SaldoCaixa(corretora_id, moeda))
            setattr(s, campo, getattr(s, campo) + Decimal(str(valor or 0)))

    acumular(
        select(MovCaixa.corretora_id, MovCaixa.moeda, func.sum(MovCaixa.valor)).group_by(
            MovCaixa.corretora_id, MovCaixa.moeda
        ),
        "movimentacoes",
        MovCaixa,
    )
    if data_inicio is not None:
        acumular(
            select(Operacao.corretora_id, Operacao.moeda, func.sum(_efeito_operacao()))
            .where(Operacao.data >= data_inicio)
            .group_by(Operacao.corretora_id, Operacao.moeda),
            "operacoes",
            Operacao,
        )
        acumular(
            select(
                Provento.corretora_id, Provento.moeda, func.sum(Provento.valor - Provento.irrf - Provento.taxas)
            )
            .where(Provento.data_pagamento >= data_inicio)
            .group_by(Provento.corretora_id, Provento.moeda),
            "proventos",
            Provento,
        )

    nomes = {i: n for i, n in sessao.execute(select(Corretora.id, Corretora.nome))}
    cambios = cambios_atuais(sessao)
    for s in saldos.values():
        s.corretora = nomes.get(s.corretora_id)
        s.cambio = cambios.get(s.moeda)
    lista = sorted(saldos.values(), key=lambda s: (s.corretora is None, s.corretora or "", s.moeda))
    return ResultadoCaixa(data_inicio, lista)
