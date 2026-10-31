"""Leitura dos quadros públicos de indicadores do Fundamentus."""

import re
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from io import StringIO

import httpx
import pandas as pd

FONTE = "Fundamentus"
_URL_ACOES = "https://www.fundamentus.com.br/resultado.php"
_URL_FIIS = "https://www.fundamentus.com.br/fii.php"
_TICKER = re.compile(r"^[A-Z0-9]{4,16}$")


@dataclass(frozen=True)
class FonteFundamentos:
    id: str
    nome: str
    disponivel: bool
    motivo: str | None = None


FONTES = (
    FonteFundamentos("fundamentus", FONTE, True),
    FonteFundamentos(
        "investidor10",
        "Investidor10",
        False,
        "Conector pendente: rota consultada retornou HTTP 410 e o robots.txt desaconselha /api/.",
    ),
)


class ErroFundamentus(Exception):
    pass


def _cabecalho(valor: object) -> str:
    texto = unicodedata.normalize("NFKD", str(valor)).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Z0-9]", "", texto.upper())


def _numero(valor: object) -> Decimal | None:
    if valor is None or pd.isna(valor):
        return None
    texto = str(valor).strip().replace("\xa0", "").replace("%", "").replace(" ", "")
    if texto in ("", "-", "--"):
        return None
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    try:
        return Decimal(texto)
    except InvalidOperation as erro:
        raise ErroFundamentus(f"Indicador numérico inválido: {valor!r}") from erro


def _tabela(html: str) -> list[dict[str, object]]:
    opcoes = {
        "attrs": {"id": "resultado"},
        "decimal": ",",
        "thousands": ".",
    }
    try:
        tabela = pd.read_html(StringIO(html), **opcoes)[0]
        if tabela.empty:
            raise ErroFundamentus("A página não contém a tabela de indicadores esperada")
        tabelas = pd.read_html(StringIO(html), converters={coluna: str for coluna in tabela.columns}, **opcoes)
    except (ImportError, ValueError, pd.errors.ParserError) as erro:
        raise ErroFundamentus(f"Não foi possível interpretar a tabela de indicadores: {erro}") from erro
    if not tabelas or tabelas[0].empty:
        raise ErroFundamentus("A página não contém a tabela de indicadores esperada")
    return [
        {_cabecalho(chave): valor for chave, valor in linha.items()}
        for linha in tabelas[0].to_dict(orient="records")
    ]


def _valor(linha: Mapping[str, object], *cabecalhos: str) -> object:
    for cabecalho in cabecalhos:
        if (valor := linha.get(_cabecalho(cabecalho))) is not None:
            return valor
    return None


def _texto(linha: Mapping[str, object], cabecalho: str) -> str | None:
    valor = _valor(linha, cabecalho)
    if valor is None or pd.isna(valor):
        return None
    texto = str(valor).strip()
    return texto or None


def _decimal(linha: Mapping[str, object], *cabecalhos: str) -> Decimal | None:
    return _numero(_valor(linha, *cabecalhos))


def interpretar_acoes(html: str) -> dict[str, dict[str, Decimal]]:
    """Interpreta os indicadores da tabela de ações, sem valores em ponto flutuante."""
    resultado = {}
    for linha in _tabela(html):
        ticker = str(_valor(linha, "Papel") or "").strip().upper()
        if not _TICKER.fullmatch(ticker):
            continue
        campos = {
            "preco_lucro": _decimal(linha, "P/L"),
            "preco_valor_patrimonial": _decimal(linha, "P/VP"),
            "dividend_yield": _decimal(linha, "Div.Yield"),
            "psr": _decimal(linha, "PSR"),
            "roe": _decimal(linha, "ROE"),
            "roic": _decimal(linha, "ROIC"),
            "margem_bruta": _decimal(linha, "Mrg Bruta"),
            "margem_ebit": _decimal(linha, "Mrg Ebit"),
            "margem_liquida": _decimal(linha, "Mrg. Líq."),
            "liquidez_corrente": _decimal(linha, "Liq. Corr."),
            "liquidez_media_2m": _decimal(linha, "Liq.2meses"),
            "patrimonio_liquido": _decimal(linha, "Patrim. Líq"),
            "valor_mercado": _decimal(linha, "Valor de mercado"),
            "divida_liquida_patrimonio": _decimal(linha, "Dív.Líq/ Patrim."),
            "crescimento_receita_5a": _decimal(linha, "Cresc. Rec.5a"),
        }
        resultado[ticker] = {chave: valor for chave, valor in campos.items() if valor is not None}
    return resultado


def interpretar_fiis(html: str) -> dict[str, dict[str, Decimal | int | str]]:
    """Interpreta os indicadores de FIIs publicados na tabela de resultados."""
    resultado = {}
    for linha in _tabela(html):
        ticker = str(_valor(linha, "Papel") or "").strip().upper()
        if not _TICKER.fullmatch(ticker):
            continue
        campos: dict[str, Decimal | int | str | None] = {
            "preco_valor_patrimonial": _decimal(linha, "P/VP"),
            "dividend_yield": _decimal(linha, "Div Yield"),
            "fii_dividendos_meses_12m": _inteiro(linha, "DY qtd"),
            "fii_dividend_yield_2a": _decimal(linha, "Div.Yield 2 anos"),
            "fii_dividendos_meses_2a": _inteiro(linha, "DY 2a qtd"),
            "fii_ffo_yield": _decimal(linha, "FFO yield"),
            "patrimonio_liquido": _decimal(linha, "Patrim Líq"),
            "valor_mercado": _decimal(linha, "Valor mercado"),
            "fii_liquidez": _decimal(linha, "Liquidez"),
            "fii_area_m2": _decimal(linha, "Área(m2)"),
            "fii_preco_m2": _decimal(linha, "Preço/m2"),
            "fii_numero_imoveis": _inteiro(linha, "Nro de imóveis"),
            "fii_numero_unidades": _inteiro(linha, "Nro de unidades"),
            "segmento_fii": _texto(linha, "Segmento"),
        }
        resultado[ticker] = {chave: valor for chave, valor in campos.items() if valor is not None}
    return resultado


def _inteiro(linha: Mapping[str, object], cabecalho: str) -> int | None:
    valor = _decimal(linha, cabecalho)
    return int(valor) if valor is not None else None


def _get(cliente: httpx.Client, url: str) -> str:
    try:
        resposta = cliente.get(url)
        resposta.raise_for_status()
    except httpx.HTTPError as erro:
        raise ErroFundamentus(f"Falha ao consultar {url}: {erro}") from erro
    return resposta.text


def buscar_acoes(cliente: httpx.Client) -> dict[str, dict[str, Decimal]]:
    return interpretar_acoes(_get(cliente, _URL_ACOES))


def buscar_fiis(cliente: httpx.Client) -> dict[str, dict[str, Decimal | int | str]]:
    return interpretar_fiis(_get(cliente, _URL_FIIS))


def cliente_http() -> httpx.Client:
    return httpx.Client(
        timeout=httpx.Timeout(30),
        headers={"User-Agent": "ControleInv/0.1 (local investment tracker)"},
    )
