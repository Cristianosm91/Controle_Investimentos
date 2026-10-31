"""Lotes de importação: cada arquivo importado vira um lote, que pode ser desfeito sem afetar outros lançamentos."""

from datetime import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from ..models import LoteImportacao, MovCaixa, Operacao, Provento

TIPOS = {
    "EXTRATO_B3": "Extrato B3",
    "ALUGUEL": "Extrato de aluguel (BTC)",
}


class LoteInvalido(Exception):
    pass


def novo(sessao: Session, tipo: str, investidor_id: int | None, arquivo: str | None) -> LoteImportacao:
    lote = LoteImportacao(
        tipo=tipo, investidor_id=investidor_id, arquivo=(arquivo or None) and arquivo[:200], criado_em=datetime.now()
    )
    sessao.add(lote)
    sessao.flush()
    return lote


def contar(sessao: Session, lote: LoteImportacao) -> None:
    """Grava no lote quantos lançamentos ele criou (chamar antes do commit, após o flush dos lançamentos)."""
    sessao.flush()
    for modelo, campo in ((Operacao, "operacoes"), (Provento, "proventos"), (MovCaixa, "caixa")):
        setattr(lote, campo, sessao.scalar(select(func.count()).where(modelo.lote_id == lote.id)) or 0)


def listar(sessao: Session, limite: int = 100) -> list[LoteImportacao]:
    return list(sessao.scalars(select(LoteImportacao).order_by(LoteImportacao.id.desc()).limit(limite)))


def desfazer(sessao: Session, lote_id: int) -> dict[str, int]:
    """Apaga os lançamentos gravados pelo lote. Ativos e corretoras criados na importação são mantidos."""
    lote = sessao.get(LoteImportacao, lote_id)
    if lote is None:
        raise LookupError(f"Lote {lote_id} não encontrado")
    if lote.desfeito_em is not None:
        raise LoteInvalido("Este lote já foi desfeito")
    removidos = {}
    for modelo, campo in ((Operacao, "operacoes"), (Provento, "proventos"), (MovCaixa, "caixa")):
        removidos[campo] = sessao.execute(delete(modelo).where(modelo.lote_id == lote_id)).rowcount or 0
    lote.desfeito_em = datetime.now()
    sessao.commit()
    return removidos
