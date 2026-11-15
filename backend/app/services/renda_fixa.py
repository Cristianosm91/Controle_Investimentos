"""Ativos personalizados: renda fixa com rendimento estimado por índice e saldo com atualização manual.

Convenção (igual à de um fundo): o ativo tem um valor de cota. Na renda fixa automática a cota vale 1 em
`data_base` e é corrigida por `indexador` x `indexador_pct` + `taxa_aa` (CDI diário, demais mensais).
Cada aplicação é uma compra de `valor aplicado / cota da data` cotas ao preço da cota.
Sem indexador, a cota vem do saldo informado.
"""

import logging
from collections.abc import Iterable, Mapping
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..db import insert_upsert
from ..models import Ativo, Cotacao, IndiceMensal
from .carteira import carregar_posicoes
from .cdi import CdiIndisponivel, CurvaCdi

log = logging.getLogger(__name__)

FONTE_CALCULADA = "Calculado"
FONTE_MANUAL = "Manual"

# Indexador → coluna de `indice_mensal` (variação mensal em fração). PRE = só a taxa a.a.
COLUNAS_INDICE: dict[str, str | None] = {"PRE": None, "CDI": "cdi", "SELIC": "selic", "IPCA": "ipca", "IGPM": "igpm"}


def _proximo_mes(d: date) -> date:
    return (d.replace(day=28) + timedelta(days=4)).replace(day=1)


def fator(
    inicio: date,
    fim: date,
    indice_mensal: Mapping[date, Decimal],
    indexador_pct: Decimal = Decimal(1),
    taxa_aa: Decimal = Decimal(0),
) -> Decimal:
    """Fator de correção entre as datas: índice mensal pró-rata por dias corridos x taxa a.a. (base 365).

    Mês sem índice publicado repete o último conhecido (rendimento estimado, como na planilha).
    """
    if fim <= inicio:
        return Decimal(1)
    total = 1.0
    if indice_mensal:
        anteriores = [c for c in indice_mensal if c < inicio.replace(day=1)]
        ultimo = indice_mensal[max(anteriores)] if anteriores else None
        mes = inicio.replace(day=1)
        while mes <= fim:
            proximo = _proximo_mes(mes)
            a, b = max(inicio, mes), min(fim, proximo)
            ultimo = indice_mensal.get(mes, ultimo)
            if b > a and ultimo is not None:
                total *= (1 + float(ultimo) * float(indexador_pct)) ** ((b - a).days / (proximo - mes).days)
            mes = proximo
    total *= (1 + float(taxa_aa)) ** ((fim - inicio).days / 365)
    return Decimal(str(round(total, 10)))


def _indice(sessao: Session, indexador: str) -> dict[date, Decimal]:
    coluna = COLUNAS_INDICE.get(indexador)
    if coluna is None:
        return {}
    campo = getattr(IndiceMensal, coluna)
    return {d: v for d, v in sessao.execute(select(IndiceMensal.competencia, campo).where(campo.is_not(None)))}


def calculado(ativo: Ativo) -> bool:
    return not ativo.cotacao_automatica and ativo.indexador is not None and ativo.data_base is not None


def _valor_calculado(
    ativo: Ativo, dia: date, indice: Mapping[date, Decimal], curva: CurvaCdi | None,
    manuais: list[tuple[date, Decimal]],
) -> Decimal:
    if ativo.indexador == "CDI" and ativo.data_vencimento:
        dia = min(dia, ativo.data_vencimento)
    inicio, base = ativo.data_base, Decimal(1)
    for data_manual, cota in manuais:
        if data_manual <= dia and (inicio is None or data_manual >= inicio):
            inicio, base = data_manual, cota
    if inicio is None:
        raise ValueError("Ativo automático sem data-base")
    if dia <= inicio:
        return base
    correcao = curva.fator(inicio, dia) if curva is not None else fator(
        inicio, dia, indice, ativo.indexador_pct or Decimal(1), ativo.taxa_aa or Decimal(0),
    )
    return base * correcao


def _manuais(sessao: Session, ativo: Ativo) -> list[tuple[date, Decimal]]:
    return [(dia, preco) for dia, preco in sessao.execute(
        select(Cotacao.data, Cotacao.preco).where(Cotacao.ativo_id == ativo.id, Cotacao.fonte == FONTE_MANUAL)
        .order_by(Cotacao.data)
    )]


def valor_cota(sessao: Session, ativo: Ativo, dia: date, *, projecao: bool = False) -> Decimal:
    """Cota do ativo personalizado na data (1 antes da primeira atualização)."""
    if calculado(ativo):
        curva = (
            CurvaCdi(sessao, ativo.indexador_pct or Decimal(1), ativo.taxa_aa or Decimal(0))
            if ativo.indexador == "CDI" else None
        )
        indice = _indice(sessao, ativo.indexador)
        manuais = _manuais(sessao, ativo)
        if curva is not None and projecao and dia > date.today():
            hoje = date.today()
            if ativo.data_vencimento:
                dia = min(dia, ativo.data_vencimento)
            # Futuro nao tem CDI publicado: conserva a estimativa mensal, separada do saldo efetivo.
            atual = _valor_calculado(ativo, hoje, indice, curva, manuais)
            if not indice:
                raise CdiIndisponivel("CDI mensal ausente para projeção. Atualize os índices.")
            return atual * fator(hoje, dia, indice, ativo.indexador_pct or Decimal(1), ativo.taxa_aa or Decimal(0))
        return _valor_calculado(
            ativo, dia, indice, curva, manuais,
        )
    preco = sessao.scalar(
        select(Cotacao.preco).where(Cotacao.ativo_id == ativo.id, Cotacao.data <= dia).order_by(Cotacao.data.desc())
    )
    return preco if preco is not None else Decimal(1)


def _datas(inicio: date, fim: date) -> list[date]:
    """Fim de cada mês (o que a rentabilidade mensal usa) e o próprio dia final."""
    datas, mes = [], inicio.replace(day=1)
    while True:
        fim_mes = _proximo_mes(mes) - timedelta(days=1)
        if fim_mes >= fim:
            break
        if fim_mes >= inicio:
            datas.append(fim_mes)
        mes = _proximo_mes(mes)
    return [*datas, fim]


def _gravar(sessao: Session, ativo_id: int, precos: Iterable[tuple[date, Decimal]], fonte: str) -> int:
    linhas = [
        {"ativo_id": ativo_id, "data": d, "preco": p, "variacao_pct": None, "fonte": fonte} for d, p in precos
    ]
    if linhas:
        lote = insert_upsert(sessao, Cotacao).values(linhas)
        sessao.execute(
            lote.on_conflict_do_update(
                index_elements=["ativo_id", "data"],
                set_={"preco": lote.excluded.preco, "variacao_pct": None, "fonte": lote.excluded.fonte},
            )
        )
    return len(linhas)


def atualizar(
    sessao: Session, ativos: Iterable[Ativo] | None = None, hoje: date | None = None,
    *, falhas: list[str] | None = None,
) -> dict[str, str]:
    """Recalcula as cotas da renda fixa automática (fins de mês desde a data-base e hoje)."""
    hoje = hoje or date.today()
    if ativos is None:
        ativos = sessao.scalars(
            select(Ativo).where(~Ativo.cotacao_automatica, Ativo.indexador.is_not(None), Ativo.data_base.is_not(None))
        )
    atualizados = {}
    for ativo in ativos:
        if not calculado(ativo):
            continue
        indice = _indice(sessao, ativo.indexador)
        curva = (
            CurvaCdi(sessao, ativo.indexador_pct or Decimal(1), ativo.taxa_aa or Decimal(0))
            if ativo.indexador == "CDI" else None
        )
        manuais = _manuais(sessao, ativo)
        datas_manuais = {d for d, _ in manuais}
        if ativo.data_base > hoje:
            continue
        precos = []
        indisponiveis = []
        for d in _datas(ativo.data_base, hoje):
            if d in datas_manuais:
                continue
            try:
                precos.append((d, _valor_calculado(ativo, d, indice, curva, manuais)))
            except CdiIndisponivel as erro:
                indisponiveis.append(d)
                log.warning("%s: %s", ativo.ticker, erro)
        # Uma cota antiga nao pode continuar parecendo recalculada se faltou historico.
        sessao.execute(delete(Cotacao).where(Cotacao.ativo_id == ativo.id, Cotacao.fonte == FONTE_CALCULADA))
        _gravar(sessao, ativo.id, precos, FONTE_CALCULADA)
        if indisponiveis and falhas is not None:
            falhas.append(f"CDI diário de {ativo.ticker}: {len(indisponiveis)} data(s) sem histórico")
        if hoje not in indisponiveis:
            atualizados[ativo.ticker] = FONTE_CALCULADA
    sessao.commit()
    if atualizados:
        log.info("Renda fixa automática recalculada: %s", ", ".join(atualizados))
    return atualizados


def remover_calculadas(sessao: Session, ativo: Ativo) -> None:
    """Ativo deixou de ter rendimento automático: a série estimada não vale mais."""
    sessao.execute(delete(Cotacao).where(Cotacao.ativo_id == ativo.id, Cotacao.fonte == FONTE_CALCULADA))
    sessao.commit()


def informar_saldo(sessao: Session, ativo: Ativo, dia: date, saldo: Decimal) -> Decimal:
    """Saldo manual na moeda do ativo (soma de todos os investidores) → cota = saldo / quantidade aberta."""
    if calculado(ativo) and (dia > date.today() or dia < ativo.data_base):
        raise ValueError("A correção de saldo deve estar entre a data-base e hoje")
    if ativo.indexador == "CDI" and ativo.data_vencimento and dia > ativo.data_vencimento:
        raise ValueError("A correção de saldo deve ser até o vencimento")
    quantidade = sum(
        (p.quantidade for (_, a), p in carregar_posicoes(sessao, None, ate=dia).items() if a == ativo.id),
        Decimal(0),
    )
    if quantidade <= 0:
        raise ValueError(f"{ativo.ticker} não tem posição aberta em {dia:%d/%m/%Y}")
    cota = saldo / quantidade
    _gravar(sessao, ativo.id, [(dia, cota)], FONTE_MANUAL)
    if calculado(ativo):
        atualizar(sessao, [ativo])
    else:
        sessao.commit()
    return cota
