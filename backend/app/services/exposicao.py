"""Exposição da carteira por corretora (instituição de custódia)."""

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Ativo, Corretora, Operacao
from .carteira import cambios_atuais, ultimas_cotacoes
from .posicao import ZERO, Movimento, calcular_posicoes

SEM_CORRETORA = "Não informada"


@dataclass
class ExposicaoCorretora:
    corretora: str
    valor: Decimal
    ativos: int


def por_corretora(sessao: Session, investidor_ids: Sequence[int] | None) -> list[ExposicaoCorretora]:
    """Calcula a posição de cada (investidor, corretora, ativo) com as próprias operações daquela corretora.

    Transferências de custódia entre corretoras não são lançadas como operação: um ativo comprado numa
    corretora e vendido em outra pode deixar posições negativas, que são descartadas.
    """
    consulta = select(
        Operacao.id, Operacao.investidor_id, Operacao.corretora_id, Operacao.ativo_id, Operacao.data, Operacao.evento,
        Operacao.quantidade, Operacao.preco, Operacao.taxas, Operacao.daytrade, Operacao.cambio,
    )
    if investidor_ids:
        consulta = consulta.where(Operacao.investidor_id.in_(investidor_ids))
    chaves: dict[tuple[int, int | None], int] = {}
    movimentos = []
    for r in sessao.execute(consulta):
        chave = chaves.setdefault((r.investidor_id, r.corretora_id), len(chaves) + 1)
        movimentos.append(Movimento(
            chave, r.ativo_id, r.data, r.evento, r.quantidade, r.preco, r.taxas, r.daytrade, r.id, r.cambio,
        ))
    if not movimentos:
        return []
    corretora_da_chave = {v: c for (_, c), v in chaves.items()}
    abertas = [p for p in calcular_posicoes(movimentos).values() if p.aberta]

    ativo_ids = {p.ativo_id for p in abertas}
    ativos = {a.id: a for a in sessao.scalars(select(Ativo).where(Ativo.id.in_(ativo_ids)))} if ativo_ids else {}
    cotacoes = ultimas_cotacoes(sessao, ativo_ids)
    cambios = cambios_atuais(sessao)
    nomes = dict(sessao.execute(select(Corretora.id, Corretora.nome)).all())

    valores: dict[str, Decimal] = defaultdict(lambda: ZERO)
    contagem: dict[str, set[int]] = defaultdict(set)
    for p in abertas:
        nome = nomes.get(corretora_da_chave[p.investidor_id], SEM_CORRETORA)
        cotacao = cotacoes.get(p.ativo_id)
        cambio = cambios.get(ativos[p.ativo_id].moeda)
        valor = p.quantidade * cotacao.preco * cambio if cotacao and cambio is not None else p.custo
        valores[nome] += valor
        contagem[nome].add(p.ativo_id)
    return sorted(
        (ExposicaoCorretora(n, v, len(contagem[n])) for n, v in valores.items()), key=lambda e: -e.valor
    )
