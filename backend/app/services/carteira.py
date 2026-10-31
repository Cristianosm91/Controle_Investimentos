"""Monta a carteira a partir do banco: posições + cotação mais recente + proventos (tudo em BRL)."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import Ativo, Cotacao, CotacaoMoeda, Operacao, Provento
from .posicao import ZERO, Movimento, Posicao, calcular_posicoes, consolidar


def carregar_posicoes(
    sessao: Session, investidor_ids: Sequence[int] | None, ate: date | None = None, ativo_ids: set[int] | None = None
) -> dict[tuple[int, int], Posicao]:
    consulta = select(
        Operacao.id, Operacao.investidor_id, Operacao.ativo_id, Operacao.data, Operacao.evento,
        Operacao.quantidade, Operacao.preco, Operacao.taxas, Operacao.daytrade, Operacao.cambio,
    )
    if investidor_ids:
        consulta = consulta.where(Operacao.investidor_id.in_(investidor_ids))
    if ativo_ids is not None:
        consulta = consulta.where(Operacao.ativo_id.in_(ativo_ids))
    if ate:
        consulta = consulta.where(Operacao.data <= ate)
    movimentos = (
        Movimento(
            r.investidor_id, r.ativo_id, r.data, r.evento, r.quantidade, r.preco, r.taxas, r.daytrade, r.id, r.cambio
        )
        for r in sessao.execute(consulta)
    )
    return calcular_posicoes(movimentos)


def _proventos_liquidos(
    sessao: Session, investidor_ids: Sequence[int] | None, ativo_ids: set[int] | None = None
) -> dict[tuple[int, int], Decimal]:
    liquido = func.sum((Provento.valor - Provento.irrf - Provento.taxas) * Provento.cambio)
    consulta = select(Provento.investidor_id, Provento.ativo_id, liquido).group_by(
        Provento.investidor_id, Provento.ativo_id
    )
    if investidor_ids:
        consulta = consulta.where(Provento.investidor_id.in_(investidor_ids))
    if ativo_ids is not None:
        consulta = consulta.where(Provento.ativo_id.in_(ativo_ids))
    return {(i, a): Decimal(str(v or 0)) for i, a, v in sessao.execute(consulta)}


def ultimas_cotacoes(sessao: Session, ativo_ids: set[int]) -> dict[int, Cotacao]:
    if not ativo_ids:
        return {}
    ultima = (
        select(Cotacao.ativo_id, func.max(Cotacao.data).label("data"))
        .where(Cotacao.ativo_id.in_(ativo_ids))
        .group_by(Cotacao.ativo_id)
        .subquery()
    )
    consulta = select(Cotacao).join(ultima, (Cotacao.ativo_id == ultima.c.ativo_id) & (Cotacao.data == ultima.c.data))
    return {c.ativo_id: c for c in sessao.scalars(consulta)}


def cambios_atuais(sessao: Session) -> dict[str, Decimal]:
    """Último valor em BRL de cada moeda; BRL = 1."""
    ultima = (
        select(CotacaoMoeda.moeda, func.max(CotacaoMoeda.data).label("data"))
        .group_by(CotacaoMoeda.moeda)
        .subquery()
    )
    consulta = select(CotacaoMoeda.moeda, CotacaoMoeda.valor).join(
        ultima, (CotacaoMoeda.moeda == ultima.c.moeda) & (CotacaoMoeda.data == ultima.c.data)
    )
    return {"BRL": Decimal(1), **{m: v for m, v in sessao.execute(consulta)}}


@dataclass
class LinhaCarteira:
    investidor_id: int | None
    ativo: Ativo
    posicao: Posicao
    proventos: Decimal
    cotacao: Cotacao | None
    cambio: Decimal | None

    @property
    def valor_mercado(self) -> Decimal | None:
        if not self.cotacao or self.cambio is None:
            return None
        return self.posicao.quantidade * self.cotacao.preco * self.cambio

    @property
    def lucro_aberto(self) -> Decimal | None:
        vm = self.valor_mercado
        return vm - self.posicao.custo if vm is not None else None

    @property
    def lucro_dia(self) -> Decimal | None:
        vm = self.valor_mercado
        if vm is None or self.cotacao.variacao_pct is None:
            return None
        return vm - vm / (1 + self.cotacao.variacao_pct)


def montar_carteira(
    sessao: Session,
    investidor_ids: Sequence[int] | None,
    consolidado: bool,
    somente_abertas: bool = True,
    ativo_ids: set[int] | None = None,
) -> list[LinhaCarteira]:
    posicoes = carregar_posicoes(sessao, investidor_ids, ativo_ids=ativo_ids)
    proventos = _proventos_liquidos(sessao, investidor_ids, ativo_ids)

    if consolidado:
        por_chave: dict[tuple[int | None, int], Posicao] = {
            (None, a): p for a, p in consolidar(posicoes.values()).items()
        }
        prov: dict[tuple[int | None, int], Decimal] = {}
        for (_, a), v in proventos.items():
            prov[(None, a)] = prov.get((None, a), ZERO) + v
    else:
        por_chave = dict(posicoes)
        prov = dict(proventos)

    if somente_abertas:
        por_chave = {k: p for k, p in por_chave.items() if p.aberta}

    ativo_ids = {a for _, a in por_chave}
    ativos = {a.id: a for a in sessao.scalars(select(Ativo).where(Ativo.id.in_(ativo_ids)))} if ativo_ids else {}
    cotacoes = ultimas_cotacoes(sessao, ativo_ids)
    cambios = cambios_atuais(sessao)

    linhas = [
        LinhaCarteira(inv, ativos[a], p, prov.get((inv, a), ZERO), cotacoes.get(a), cambios.get(ativos[a].moeda))
        for (inv, a), p in por_chave.items()
    ]
    linhas.sort(key=lambda l: (l.ativo.classe, l.ativo.ticker, l.investidor_id or 0))
    return linhas
