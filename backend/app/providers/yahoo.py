import logging
from collections.abc import Sequence
from datetime import date
from decimal import Decimal

import pandas as pd
import yfinance as yf

from .base import AtivoRef, CotacaoAtual

log = logging.getLogger(__name__)

_MERCADOS_EUA = {"NASDAQ", "NYSE", "NYSEARCA", "NYSEAMERICAN", "BATS"}


def simbolo_yahoo(ativo: AtivoRef) -> str | None:
    mercado = (ativo.mercado or "").upper()
    if mercado == "BVMF":
        return f"{ativo.ticker}.SA"
    if mercado in _MERCADOS_EUA:
        return ativo.ticker.replace(".", "-")
    return None


class ProvedorYahoo:
    nome = "Yahoo"

    def _fechamentos(self, simbolos: list[str]) -> dict[str, tuple[date, Decimal, Decimal | None]]:
        if not simbolos:
            return {}
        try:
            df = yf.download(
                simbolos,
                period="7d",
                interval="1d",
                group_by="ticker",
                auto_adjust=False,
                progress=False,
                threads=False,
            )
        except Exception:
            log.exception("Falha ao consultar Yahoo Finance")
            return {}

        resultado = {}
        for simbolo in simbolos:
            try:
                serie = df[simbolo]["Close"] if isinstance(df.columns, pd.MultiIndex) else df["Close"]
            except KeyError:
                continue
            serie = serie.dropna()
            if serie.empty:
                continue
            preco = Decimal(str(round(float(serie.iloc[-1]), 6)))
            variacao = None
            if len(serie) > 1 and serie.iloc[-2]:
                variacao = Decimal(str(round(float(serie.iloc[-1] / serie.iloc[-2] - 1), 8)))
            resultado[simbolo] = (serie.index[-1].date(), preco, variacao)
        return resultado

    def cotacoes(self, ativos: Sequence[AtivoRef]) -> dict[str, CotacaoAtual]:
        por_simbolo = {s: a for a in ativos if (s := simbolo_yahoo(a))}
        return {
            por_simbolo[s].ticker: CotacaoAtual(por_simbolo[s].ticker, preco, var, dia, self.nome)
            for s, (dia, preco, var) in self._fechamentos(list(por_simbolo)).items()
        }

    def cambios(self, moedas: Sequence[str]) -> dict[str, CotacaoAtual]:
        por_simbolo = {f"{m}BRL=X": m for m in moedas if m != "BRL"}
        return {
            por_simbolo[s]: CotacaoAtual(por_simbolo[s], preco, var, dia, self.nome)
            for s, (dia, preco, var) in self._fechamentos(list(por_simbolo)).items()
        }
