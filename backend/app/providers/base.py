from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Protocol


@dataclass(frozen=True)
class AtivoRef:
    ticker: str
    mercado: str | None
    moeda: str


@dataclass(frozen=True)
class CotacaoAtual:
    ticker: str
    preco: Decimal
    variacao_pct: Decimal | None
    data: date
    fonte: str


class ProvedorCotacao(Protocol):
    nome: str

    def cotacoes(self, ativos: Sequence[AtivoRef]) -> dict[str, CotacaoAtual]:
        """Devolve as cotações encontradas, indexadas pelo ticker. Ausentes ficam de fora."""
        ...

    def cambios(self, moedas: Sequence[str]) -> dict[str, CotacaoAtual]:
        """Valor de 1 unidade de cada moeda em BRL, indexado pela moeda."""
        ...
