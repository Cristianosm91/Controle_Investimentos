"""Lotes de importação: cada arquivo importado vira um lote, que pode ser desfeito sem afetar outros lançamentos."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import LoteImportacao, MovCaixa, Operacao, Provento
from . import auditoria

TIPOS = {
    "EXTRATO_B3": "Extrato B3",
    "PLANILHA_OPERACOES": "Modelo de operações personalizado",
    "PLANILHA_PROVENTOS": "Modelo de proventos personalizado",
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
        itens = list(sessao.scalars(select(modelo).where(modelo.lote_id == lote.id)))
        setattr(lote, campo, len(itens))
        for item in itens:
            auditoria.registrar(sessao, item, "criado")


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
        itens = list(sessao.scalars(select(modelo).where(modelo.lote_id == lote_id)))
        removidos[campo] = len(itens)
        for item in itens:
            anterior = auditoria.snapshot(item)
            sessao.delete(item)
            auditoria.registrar(sessao, item, "excluido", anterior)
    lote.desfeito_em = datetime.now()
    sessao.commit()
    return removidos
