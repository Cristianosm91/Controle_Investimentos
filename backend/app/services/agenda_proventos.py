"""Agenda de proventos (lançados com pagamento futuro) e projeção dos próximos 12 meses.

A projeção repete os pagamentos dos últimos 12 meses no mesmo mês do ano seguinte, ajustados pela quantidade
atual: valor por cota na data-com (ou no pagamento, sem data-com) x quantidade em carteira hoje. É uma
estimativa: empresas mudam valores e calendários. Amortizações e aluguel (BTC) não entram, por não serem
rendimento recorrente por cota.
"""

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import Ativo, Operacao, Provento
from .carteira import carregar_posicoes
from .posicao import ZERO, Movimento, Posicao, aplicar, ordenar

FORA_DA_PROJECAO = frozenset({"AMORTIZACAO", "ALUGUEL"})


def _mes(d: date) -> date:
    return d.replace(day=1)


def _somar_meses(d: date, n: int) -> date:
    total = d.year * 12 + d.month - 1 + n
    return date(total // 12, total % 12 + 1, 1)


@dataclass
class ItemAgenda:
    id: int
    investidor_id: int
    ticker: str
    evento: str
    data_com: date | None
    data_pagamento: date
    liquido: Decimal


@dataclass
class AtivoProjecao:
    ativo_id: int
    ticker: str
    classe: str
    custo: Decimal
    confirmado: Decimal = ZERO
    estimado: Decimal = ZERO

    @property
    def total(self) -> Decimal:
        return self.confirmado + self.estimado

    @property
    def yoc(self) -> Decimal | None:
        return self.total / self.custo if self.custo > 0 else None


@dataclass
class Agenda:
    a_receber: list[ItemAgenda]
    meses: list[tuple[date, Decimal, Decimal]]  # (mês, confirmado, estimado)
    por_ativo: list[AtivoProjecao] = field(default_factory=list)
    total_recebido_12m: Decimal = ZERO
    custo_carteira: Decimal = ZERO

    @property
    def total_a_receber(self) -> Decimal:
        return sum((i.liquido for i in self.a_receber), ZERO)

    @property
    def total_12m(self) -> Decimal:
        return sum((c + e for _, c, e in self.meses), ZERO)


def quantidade_na_data(movimentos: Sequence[Movimento], dia: date) -> Decimal:
    """Quantidade swing ao fim do dia (movimentos já ordenados)."""
    p = Posicao(0, 0)
    for m in movimentos:
        if m.data > dia:
            break
        if not m.daytrade:
            aplicar(p, m)
    return p.quantidade


def calcular(
    sessao: Session, investidor_ids: Sequence[int] | None, hoje: date | None = None, classe: str | None = None
) -> Agenda:
    hoje = hoje or date.today()
    inicio_janela = _somar_meses(_mes(hoje), 1)
    fim_janela = _somar_meses(inicio_janela, 12)
    liquido = (Provento.valor - Provento.irrf - Provento.taxas) * Provento.cambio

    filtro = [Provento.investidor_id.in_(investidor_ids)] if investidor_ids else []
    ativos_da_classe = None
    if classe:
        ativos_da_classe = set(sessao.scalars(select(Ativo.id).where(Ativo.classe == classe)))
        filtro.append(Provento.ativo_id.in_(ativos_da_classe))
    futuros = sessao.execute(
        select(Provento.id, Provento.investidor_id, Provento.ativo_id, Ativo.ticker, Provento.evento,
               Provento.data_com, Provento.data_pagamento, liquido)
        .join(Ativo, Ativo.id == Provento.ativo_id)
        .where(Provento.data_pagamento > hoje, *filtro)
        .order_by(Provento.data_pagamento, Ativo.ticker)
    ).all()
    a_receber = [
        ItemAgenda(i, inv, t, ev, dc, dp, Decimal(str(v or 0))) for i, inv, _, t, ev, dc, dp, v in futuros
    ]

    total_recebido_12m = sessao.scalar(
        select(func.sum(liquido)).where(
            Provento.data_pagamento > hoje - timedelta(days=365),
            Provento.data_pagamento <= hoje,
            *filtro,
        )
    )
    total_recebido_12m = Decimal(str(total_recebido_12m or 0))

    posicoes = {
        k: p
        for k, p in carregar_posicoes(sessao, investidor_ids, ativo_ids=ativos_da_classe).items()
        if p.aberta
    }
    custo_carteira = sum((p.custo for p in posicoes.values()), ZERO)
    ativos = {a.id: a for a in sessao.scalars(select(Ativo).where(Ativo.id.in_({a for _, a in posicoes})))} if posicoes else {}
    por_ativo: dict[int, AtivoProjecao] = {}

    def projecao(ativo_id: int) -> AtivoProjecao:
        if ativo_id not in por_ativo:
            a = ativos.get(ativo_id) or sessao.get(Ativo, ativo_id)
            custo = sum((p.custo for (_, aid), p in posicoes.items() if aid == ativo_id), ZERO)
            por_ativo[ativo_id] = AtivoProjecao(ativo_id, a.ticker, a.classe, custo)
        return por_ativo[ativo_id]

    confirmado: dict[date, Decimal] = defaultdict(lambda: ZERO)
    confirmados_chave: set[tuple[int, int, date]] = set()
    for item, (_, inv, ativo_id, *_resto) in zip(a_receber, futuros, strict=True):
        mes = _mes(item.data_pagamento)
        if inicio_janela <= mes < fim_janela:
            confirmado[mes] += item.liquido
            projecao(ativo_id).confirmado += item.liquido
        confirmados_chave.add((inv, ativo_id, mes))

    estimado: dict[date, Decimal] = defaultdict(lambda: ZERO)
    if posicoes:
        passados = sessao.execute(
            select(Provento.investidor_id, Provento.ativo_id, Provento.data_com, Provento.data_pagamento, liquido)
            .where(
                Provento.data_pagamento > hoje - timedelta(days=365),
                Provento.data_pagamento <= hoje,
                Provento.evento.not_in(FORA_DA_PROJECAO),
                Provento.ativo_id.in_({a for _, a in posicoes}),
                *filtro,
            )
        ).all()
        pares = {(inv, a) for inv, a, *_ in passados if (inv, a) in posicoes}
        movimentos: dict[tuple[int, int], list[Movimento]] = defaultdict(list)
        if pares:
            for r in sessao.execute(
                select(Operacao.id, Operacao.investidor_id, Operacao.ativo_id, Operacao.data, Operacao.evento,
                       Operacao.quantidade, Operacao.preco, Operacao.taxas, Operacao.daytrade, Operacao.cambio)
                .where(Operacao.ativo_id.in_({a for _, a in pares}))
            ):
                if (r.investidor_id, r.ativo_id) in pares:
                    movimentos[(r.investidor_id, r.ativo_id)].append(Movimento(
                        r.investidor_id, r.ativo_id, r.data, r.evento, r.quantidade, r.preco, r.taxas, r.daytrade,
                        r.id, r.cambio,
                    ))
        ordenados = {k: ordenar(v) for k, v in movimentos.items()}
        for inv, ativo_id, data_com, data_pagamento, valor in passados:
            if (inv, ativo_id) not in posicoes:
                continue
            mes = _somar_meses(_mes(data_pagamento), 12)
            if not inicio_janela <= mes < fim_janela or (inv, ativo_id, mes) in confirmados_chave:
                continue
            qtd_ref = quantidade_na_data(ordenados.get((inv, ativo_id), []), data_com or data_pagamento)
            if qtd_ref <= 0:
                continue
            valor_estimado = Decimal(str(valor or 0)) / qtd_ref * posicoes[(inv, ativo_id)].quantidade
            estimado[mes] += valor_estimado
            projecao(ativo_id).estimado += valor_estimado

    meses = [
        (m, confirmado[m], estimado[m]) for m in (_somar_meses(inicio_janela, i) for i in range(12))
    ]
    lista = sorted((p for p in por_ativo.values() if p.total), key=lambda p: -p.total)
    return Agenda(a_receber, meses, lista, total_recebido_12m, custo_carteira)
