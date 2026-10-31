"""Classificação dos ativos em books e carteiras, conforme a tela de Configurações."""

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from ..models import Ativo, AtivoBook, Book, CarteiraAtivo, ClasseBook


@dataclass(frozen=True)
class Classificacao:
    books: dict[int, Book]
    por_classe: dict[str, int]
    excecoes: dict[int, list[tuple[int, Decimal]]]
    carteiras: dict[int, CarteiraAtivo]  # ativo_id → vínculo (só carteiras ativas)

    def books_do_ativo(self, ativo: Ativo) -> list[tuple[Book, Decimal]]:
        """Books do ativo com a fração de cada um; exceção por ativo prevalece sobre o book da classe."""
        if ativo.id in self.excecoes:
            return [(self.books[b], pct) for b, pct in self.excecoes[ativo.id] if b in self.books]
        book_id = self.por_classe.get(ativo.classe)
        return [(self.books[book_id], Decimal(1))] if book_id in self.books else []

    def book_principal(self, ativo: Ativo) -> Book | None:
        books = self.books_do_ativo(ativo)
        return max(books, key=lambda b: b[1])[0] if books else None

    def carteira(self, ativo_id: int) -> CarteiraAtivo | None:
        return self.carteiras.get(ativo_id)


def carregar(sessao: Session) -> Classificacao:
    books = {b.id: b for b in sessao.scalars(select(Book).options(joinedload(Book.estrategia)))}
    por_classe = {c: b for c, b in sessao.execute(select(ClasseBook.classe, ClasseBook.book_id))}
    excecoes: dict[int, list[tuple[int, Decimal]]] = {}
    for e in sessao.scalars(select(AtivoBook)):
        excecoes.setdefault(e.ativo_id, []).append((e.book_id, e.percentual))
    carteiras = {
        v.ativo_id: v
        for v in sessao.scalars(select(CarteiraAtivo).options(joinedload(CarteiraAtivo.carteira)))
        if v.carteira.ativa
    }
    return Classificacao(books, por_classe, excecoes, carteiras)
