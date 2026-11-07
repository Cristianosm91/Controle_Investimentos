from decimal import Decimal as D
from types import SimpleNamespace

import requests
import yfinance as yf

from app.providers import yahoo_fundamentos


def test_buscar_converte_indicadores_para_unidades_do_app(monkeypatch):
    info = {
        "trailingPE": 31.2,
        "priceToBook": 4.1,
        "dividendYield": 0.011,
        "priceToSalesTrailing12Months": 3.2,
        "returnOnEquity": 0.19,
        "grossMargins": 0.44,
        "operatingMargins": 0.12,
        "profitMargins": 0.08,
        "currentRatio": 1.4,
        "totalStockholderEquity": 1000,
        "totalDebt": 500,
        "totalCash": 200,
        "marketCap": 5000,
        "returnOnCapital": 0.14,
        "ffoYield": 0.05,
    }
    monkeypatch.setattr(yf, "Ticker", lambda _ticker: SimpleNamespace(info=info))

    resultado, falhas = yahoo_fundamentos.buscar(["AMZN"])

    assert resultado == {
        "AMZN": {
            "preco_lucro": D("31.2"),
            "preco_valor_patrimonial": D("4.1"),
            "dividend_yield": D("1.1"),
            "psr": D("3.2"),
            "roe": D("19.00"),
            "margem_bruta": D("44.00"),
            "margem_ebit": D("12.00"),
            "margem_liquida": D("8.00"),
            "liquidez_corrente": D("1.4"),
            "patrimonio_liquido": D("1000"),
            "valor_mercado": D("5000"),
            "divida_liquida_patrimonio": D("0.3"),
        }
    }
    assert falhas == {}


def test_buscar_preserva_sucesso_e_reporta_falha_por_ticker(monkeypatch):
    def obter_ticker(ticker):
        if ticker == "VICI":
            raise requests.RequestException("limite de requisições")
        return SimpleNamespace(info={"trailingPE": 12})

    monkeypatch.setattr(yf, "Ticker", obter_ticker)

    resultado, falhas = yahoo_fundamentos.buscar(["VICI", "AMZN"])

    assert resultado == {"AMZN": {"preco_lucro": D("12")}}
    assert falhas == {"VICI": "limite de requisições"}


def test_buscar_nao_emite_indicadores_sem_dados(monkeypatch):
    monkeypatch.setattr(yf, "Ticker", lambda _ticker: SimpleNamespace(info={"marketCap": float("nan")}))

    resultado, falhas = yahoo_fundamentos.buscar(["SGOV"])

    assert resultado == {}
    assert falhas == {}


def test_buscar_trata_resposta_vazia_como_falha_na_fonte(monkeypatch):
    monkeypatch.setattr(yf, "Ticker", lambda _ticker: SimpleNamespace(info={}))

    resultado, falhas = yahoo_fundamentos.buscar(["AMZN"])

    assert resultado == {}
    assert falhas == {
        "AMZN": "Yahoo Finance não retornou indicadores; ticker sem cobertura ou consulta indisponível"
    }
