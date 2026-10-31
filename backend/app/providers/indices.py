"""Índices de referência: séries do SGS/BCB (variação mensal) e índices da B3 (nível de fechamento).

- SGS: CDI 4391, SELIC 4390, IPCA 433, IGP-M 189 (% a.m.); PTAX venda diária USD 1, EUR 21620.
- B3: IBOV e IFIX diários pela API pública de estatísticas de índices.
"""

import base64
import json
from datetime import date, datetime
from decimal import Decimal

import httpx

SERIES_MENSAIS = {"cdi": 4391, "selic": 4390, "ipca": 433, "igpm": 189}
SERIES_PTAX_VENDA = {"USD": 1, "EUR": 21620}
INDICES_B3 = {"ibov": "IBOV", "ifix": "IFIX"}

_SGS = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{serie}/dados"
_B3 = "https://sistemaswebb3-listados.b3.com.br/indexStatisticsProxy/IndexCall/GetPortfolioDay/{parametro}"
# O SGS limita consultas de séries diárias a 10 anos por requisição.
_ANOS_POR_CONSULTA = 5


class ErroIndice(Exception):
    pass


def _numero_br(texto: str) -> Decimal:
    return Decimal(texto.replace(".", "").replace(",", "."))


def interpretar_sgs(valores: list[dict]) -> dict[date, Decimal]:
    return {
        datetime.strptime(v["data"], "%d/%m/%Y").date(): Decimal(str(v["valor"]))
        for v in valores
        if v.get("valor") not in (None, "")
    }


def serie_sgs(serie: int, inicio: date, fim: date, cliente: httpx.Client | None = None) -> dict[date, Decimal]:
    """Valores da série no período (para séries em %, o valor vem em pontos percentuais)."""
    resultado: dict[date, Decimal] = {}
    ano = inicio.year
    while ano <= fim.year:
        de = max(inicio, date(ano, 1, 1))
        ate = min(fim, date(ano + _ANOS_POR_CONSULTA - 1, 12, 31))
        params = {"formato": "json", "dataInicial": f"{de:%d/%m/%Y}", "dataFinal": f"{ate:%d/%m/%Y}"}
        try:
            r = (cliente or httpx).get(_SGS.format(serie=serie), params=params, timeout=60)
            # Período sem dados devolve 404 com corpo de erro.
            if r.status_code != 404:
                r.raise_for_status()
                resultado.update(interpretar_sgs(r.json()))
        except (httpx.HTTPError, ValueError, KeyError) as erro:
            raise ErroIndice(f"Falha ao consultar a série SGS {serie}: {erro}") from erro
        ano += _ANOS_POR_CONSULTA
    return resultado


def interpretar_b3_ano(ano: int, dados: dict) -> dict[date, Decimal]:
    """Resposta GetPortfolioDay: uma linha por dia do mês, colunas rateValue1..12 (meses)."""
    resultado = {}
    for linha in dados.get("results", []):
        for mes in range(1, 13):
            valor = linha.get(f"rateValue{mes}")
            if valor:
                resultado[date(ano, mes, int(linha["day"]))] = _numero_br(valor)
    return resultado


def indice_b3(codigo: str, ano: int, cliente: httpx.Client | None = None) -> dict[date, Decimal]:
    parametro = base64.b64encode(json.dumps({"index": codigo, "language": "pt-br", "year": str(ano)}).encode()).decode()
    try:
        r = (cliente or httpx).get(_B3.format(parametro=parametro), timeout=60)
        r.raise_for_status()
        return interpretar_b3_ano(ano, r.json())
    except (httpx.HTTPError, ValueError, KeyError) as erro:
        raise ErroIndice(f"Falha ao consultar o índice {codigo} na B3 ({ano}): {erro}") from erro


def fechamentos_mensais(diarios: dict[date, Decimal]) -> dict[date, Decimal]:
    """Último valor de cada mês, indexado pelo 1º dia do mês (competência)."""
    resultado: dict[date, tuple[date, Decimal]] = {}
    for dia, valor in diarios.items():
        competencia = dia.replace(day=1)
        if competencia not in resultado or dia > resultado[competencia][0]:
            resultado[competencia] = (dia, valor)
    return {c: v for c, (_, v) in resultado.items()}
