"""Indicadores básicos do Yahoo Finance para ações e fundos listados nos EUA."""

import logging
from collections.abc import Mapping, Sequence
from decimal import Decimal, InvalidOperation

import requests
import yfinance as yf

FONTE = "Yahoo Finance"
MERCADOS = frozenset({"NASDAQ", "NYSE", "NYSEARCA", "NYSEAMERICAN", "BATS"})

log = logging.getLogger(__name__)


def _decimal(valor: object) -> Decimal | None:
    if valor is None or isinstance(valor, bool):
        return None
    try:
        resultado = Decimal(str(valor))
    except (InvalidOperation, ValueError):
        return None
    return resultado if resultado.is_finite() else None


def _percentual(info: Mapping[str, object], campo: str) -> Decimal | None:
    valor = _decimal(info.get(campo))
    return valor * 100 if valor is not None else None


def _indicadores(info: Mapping[str, object]) -> dict[str, Decimal]:
    campos = {
        "preco_lucro": _decimal(info.get("trailingPE")),
        "preco_valor_patrimonial": _decimal(info.get("priceToBook")),
        "dividend_yield": _percentual(info, "dividendYield"),
        "psr": _decimal(info.get("priceToSalesTrailing12Months")),
        "roe": _percentual(info, "returnOnEquity"),
        "margem_bruta": _percentual(info, "grossMargins"),
        "margem_ebit": _percentual(info, "operatingMargins"),
        "margem_liquida": _percentual(info, "profitMargins"),
        "liquidez_corrente": _decimal(info.get("currentRatio")),
        "patrimonio_liquido": _decimal(info.get("totalStockholderEquity")),
        "valor_mercado": _decimal(info.get("marketCap")),
    }
    patrimonio = campos["patrimonio_liquido"]
    divida = _decimal(info.get("totalDebt"))
    caixa = _decimal(info.get("totalCash"))
    if patrimonio and divida is not None and caixa is not None:
        campos["divida_liquida_patrimonio"] = (divida - caixa) / patrimonio
    return {campo: valor for campo, valor in campos.items() if valor is not None}


def buscar(tickers: Sequence[str]) -> tuple[dict[str, dict[str, Decimal]], dict[str, str]]:
    """Busca indicadores disponíveis por ticker, isolando falhas para não perder os demais."""
    encontrados: dict[str, dict[str, Decimal]] = {}
    falhas: dict[str, str] = {}
    for ticker in tickers:
        try:
            info = yf.Ticker(ticker).info
        except (yf.exceptions.YFException, requests.RequestException, ValueError, TypeError) as erro:
            falhas[ticker] = str(erro) or type(erro).__name__
            log.warning("Falha ao buscar fundamentos de %s no Yahoo Finance: %s", ticker, erro)
            continue
        if not isinstance(info, Mapping):
            falhas[ticker] = "A resposta não contém os indicadores esperados"
            log.warning("Resposta inválida de fundamentos do Yahoo Finance para %s", ticker)
            continue
        if not info:
            falhas[ticker] = "Yahoo Finance não retornou indicadores; ticker sem cobertura ou consulta indisponível"
            log.warning("Yahoo Finance não retornou indicadores para %s", ticker)
            continue
        indicadores = _indicadores(info)
        if indicadores:
            encontrados[ticker] = indicadores
    return encontrados, falhas
