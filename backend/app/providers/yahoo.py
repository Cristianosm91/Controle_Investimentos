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

    def historico(self, ativos: Sequence[AtivoRef], inicio: date) -> dict[str, dict[date, Decimal]]:
        """Fechamentos diários (sem ajuste de proventos) desde `inicio`, indexados pelo ticker."""
        por_simbolo = {s: a for a in ativos if (s := simbolo_yahoo(a))}
        if not por_simbolo:
            return {}
        try:
            df = yf.download(
                list(por_simbolo),
                start=inicio.isoformat(),
                interval="1d",
                group_by="ticker",
                auto_adjust=False,
                actions=True,
                progress=False,
                threads=False,
            )
        except Exception:
            log.exception("Falha ao consultar histórico no Yahoo Finance")
            return {}

        resultado: dict[str, dict[date, Decimal]] = {}
        for simbolo, ativo in por_simbolo.items():
            try:
                bloco = df[simbolo] if isinstance(df.columns, pd.MultiIndex) else df
                serie = bloco["Close"].dropna()
            except KeyError:
                continue
            if serie.empty:
                continue
            desdobramentos = bloco["Stock Splits"].fillna(0) if "Stock Splits" in bloco else None
            resultado[ativo.ticker] = {
                dia.date(): Decimal(str(round(float(preco), 6)))
                for dia, preco in desfazer_ajuste_de_splits(serie, desdobramentos).items()
            }
        return resultado


def desfazer_ajuste_de_splits(fechamentos: pd.Series, desdobramentos: pd.Series | None) -> pd.Series:
    """O Yahoo devolve preços já ajustados por splits; as quantidades do app são as históricas.

    Preço bruto em d = preço ajustado × produto dos fatores de split ocorridos depois de d.
    """
    if desdobramentos is None or not (desdobramentos > 0).any():
        return fechamentos
    fatores = desdobramentos.where(desdobramentos > 0, 1.0).reindex(fechamentos.index, fill_value=1.0)
    # Fator acumulado dos splits estritamente posteriores a cada dia.
    posteriores = fatores[::-1].cumprod()[::-1].shift(-1, fill_value=1.0)
    return fechamentos * posteriores
