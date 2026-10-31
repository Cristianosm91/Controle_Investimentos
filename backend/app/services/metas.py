"""Metas financeiras: progresso atual e projeção com aportes mensais e rentabilidade real (valores de hoje).

Patrimônio: valor de mercado das posições abertas dos investidores da meta.
Renda: proventos líquidos dos últimos 12 meses ÷ 12; a projeção converte patrimônio em renda pelo
rendimento anual (dividend yield) informado ou, sem ele, pelo rendimento atual da carteira.
Cenários: pessimista e otimista variam a rentabilidade em 2 p.p. a.a. para baixo e para cima.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import Meta, Provento
from .carteira import montar_carteira

VARIACAO_CENARIO = 0.02
HORIZONTE_MAXIMO_MESES = 600


def meses_entre(inicio: date, fim: date) -> int:
    return max(0, (fim.year - inicio.year) * 12 + fim.month - inicio.month)


def somar_meses(d: date, n: int) -> date:
    total = d.year * 12 + d.month - 1 + n
    return date(total // 12, total % 12 + 1, 1)


def taxa_mensal(taxa_aa: float) -> float:
    return (1 + taxa_aa) ** (1 / 12) - 1


def projetar(atual: float, aporte: float, taxa_aa: float, meses: int) -> list[float]:
    """Valor ao fim de cada mês (índice 0 = hoje), com aporte no fim do mês."""
    r = taxa_mensal(taxa_aa)
    valores = [atual]
    for _ in range(meses):
        valores.append(valores[-1] * (1 + r) + aporte)
    return valores


def aporte_necessario(atual: float, alvo: float, taxa_aa: float, meses: int) -> float:
    if meses <= 0:
        return max(0.0, alvo - atual)
    r = taxa_mensal(taxa_aa)
    crescimento = (1 + r) ** meses
    falta = alvo - atual * crescimento
    if falta <= 0:
        return 0.0
    return falta / meses if abs(r) < 1e-12 else falta * r / (crescimento - 1)


def meses_ate_atingir(atual: float, aporte: float, taxa_aa: float, alvo: float) -> int | None:
    if atual >= alvo:
        return 0
    r = taxa_mensal(taxa_aa)
    valor = atual
    for mes in range(1, HORIZONTE_MAXIMO_MESES + 1):
        valor = valor * (1 + r) + aporte
        if valor >= alvo:
            return mes
    return None


def ids(meta: Meta) -> list[int] | None:
    return [int(i) for i in meta.investidores.split(",") if i] if meta.investidores else None


@dataclass
class Situacao:
    patrimonio: float
    renda_mensal: float

    @property
    def rendimento_aa(self) -> float | None:
        return self.renda_mensal * 12 / self.patrimonio if self.patrimonio > 0 else None


def situacao(sessao: Session, investidor_ids: Sequence[int] | None, hoje: date) -> Situacao:
    linhas = montar_carteira(sessao, investidor_ids, consolidado=True)
    patrimonio = sum(float(l.valor_mercado if l.valor_mercado is not None else l.posicao.custo) for l in linhas)
    consulta = select(func.sum((Provento.valor - Provento.irrf - Provento.taxas) * Provento.cambio)).where(
        Provento.data_pagamento > hoje - timedelta(days=365), Provento.data_pagamento <= hoje
    )
    if investidor_ids:
        consulta = consulta.where(Provento.investidor_id.in_(investidor_ids))
    return Situacao(patrimonio, float(sessao.scalar(consulta) or 0) / 12)


@dataclass
class Projecao:
    meta: Meta
    valor_atual: float
    progresso: float
    meses_restantes: int
    projetado: tuple[float, float, float]  # pessimista, base, otimista na data-alvo
    data_estimada: date | None
    aporte_necessario: float
    rendimento_usado: float | None
    serie: list[tuple[date, float, float, float]]

    @property
    def atinge(self) -> bool:
        return self.projetado[1] >= float(self.meta.valor_alvo)


def calcular(meta: Meta, s: Situacao, hoje: date) -> Projecao:
    alvo = float(meta.valor_alvo)
    aporte = float(meta.aporte_mensal)
    taxa = float(meta.rentabilidade_aa)
    meses = meses_entre(hoje, meta.data_alvo)
    renda = meta.tipo == "RENDA"
    rendimento = float(meta.rendimento_aa) if meta.rendimento_aa is not None else s.rendimento_aa

    # Renda: projeta o patrimônio e converte em renda mensal pelo rendimento anual.
    if renda:
        fator = (rendimento or 0) / 12
        atual = s.renda_mensal
        alvo_patrimonio = alvo / fator if fator else float("inf")
    else:
        fator = 1.0
        atual = s.patrimonio
        alvo_patrimonio = alvo

    cenarios = [projetar(s.patrimonio, aporte, taxa + d, meses) for d in (-VARIACAO_CENARIO, 0, VARIACAO_CENARIO)]
    serie = [
        (somar_meses(hoje.replace(day=1), i), cenarios[0][i] * fator, cenarios[1][i] * fator, cenarios[2][i] * fator)
        for i in range(meses + 1)
    ]
    passo = max(1, len(serie) // 120)
    reduzida = serie[::passo]
    serie = reduzida if reduzida[-1] is serie[-1] else [*reduzida, serie[-1]]

    if alvo_patrimonio == float("inf"):
        estimados, necessario = None, 0.0
    else:
        estimados = meses_ate_atingir(s.patrimonio, aporte, taxa, alvo_patrimonio)
        necessario = aporte_necessario(s.patrimonio, alvo_patrimonio, taxa, meses)
    return Projecao(
        meta=meta,
        valor_atual=atual,
        progresso=atual / alvo if alvo else 0.0,
        meses_restantes=meses,
        projetado=(cenarios[0][-1] * fator, cenarios[1][-1] * fator, cenarios[2][-1] * fator),
        data_estimada=somar_meses(hoje.replace(day=1), estimados) if estimados is not None else None,
        aporte_necessario=necessario,
        rendimento_usado=rendimento if renda else None,
        serie=serie,
    )


def listar(sessao: Session, hoje: date | None = None) -> list[Projecao]:
    hoje = hoje or date.today()
    cache: dict[tuple[int, ...] | None, Situacao] = {}
    resultado = []
    for meta in sessao.scalars(select(Meta).order_by(Meta.data_alvo, Meta.id)):
        chave = tuple(sorted(ids(meta))) if ids(meta) else None
        if chave not in cache:
            cache[chave] = situacao(sessao, list(chave) if chave else None, hoje)
        resultado.append(calcular(meta, cache[chave], hoje))
    return resultado
