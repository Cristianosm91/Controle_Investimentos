"""PTAX oficial do Banco Central (API Olinda).

Regra fiscal (Lei 14.754/2023, art. 15): converte-se pela cotação de fechamento, para venda,
divulgada pelo BCB para a data do fato gerador. Sem boletim na data (fim de semana/feriado ou
antes da divulgação), usa-se o último dia útil anterior.
"""

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from functools import lru_cache

import httpx

from .base import AtivoRef, CotacaoAtual

log = logging.getLogger(__name__)

_URL = (
    "https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/"
    "CotacaoMoedaPeriodo(moeda=@moeda,dataInicial=@dataInicial,dataFinalCotacao=@dataFinalCotacao)"
)
_JANELA_DIAS = 15
FONTE = "BCB PTAX"


class ErroPtax(Exception):
    pass


@dataclass(frozen=True)
class Ptax:
    moeda: str
    data: date
    compra: Decimal
    venda: Decimal


def interpretar_boletins(moeda: str, valores: list[dict]) -> list[Ptax]:
    """Só boletins de fechamento, do mais recente para o mais antigo."""
    fechamentos = [
        Ptax(
            moeda,
            datetime.strptime(v["dataHoraCotacao"][:10], "%Y-%m-%d").date(),
            Decimal(str(v["cotacaoCompra"])),
            Decimal(str(v["cotacaoVenda"])),
        )
        for v in valores
        if v.get("tipoBoletim") == "Fechamento"
    ]
    return sorted(fechamentos, key=lambda p: p.data, reverse=True)


def _consultar(moeda: str, inicio: date, fim: date, cliente: httpx.Client | None = None) -> list[Ptax]:
    params = {
        "@moeda": f"'{moeda}'",
        "@dataInicial": f"'{inicio:%m-%d-%Y}'",
        "@dataFinalCotacao": f"'{fim:%m-%d-%Y}'",
        "$format": "json",
        "$select": "cotacaoCompra,cotacaoVenda,dataHoraCotacao,tipoBoletim",
    }
    try:
        resposta = (cliente or httpx).get(_URL, params=params, timeout=20)
        resposta.raise_for_status()
        return interpretar_boletins(moeda, resposta.json()["value"])
    except (httpx.HTTPError, KeyError, ValueError) as erro:
        raise ErroPtax(f"Falha ao consultar PTAX {moeda} no BCB: {erro}") from erro


@lru_cache(maxsize=512)
def _ptax_passada(moeda: str, dia: date, dias_uteis_antes: int) -> Ptax:
    return _escolher(moeda, dia, dias_uteis_antes)


def _escolher(moeda: str, dia: date, dias_uteis_antes: int) -> Ptax:
    janela = _JANELA_DIAS + 2 * dias_uteis_antes
    boletins = [p for p in _consultar(moeda, dia - timedelta(days=janela), dia) if p.data <= dia]
    if len(boletins) <= dias_uteis_antes:
        raise ErroPtax(f"PTAX {moeda} indisponível para {dia:%d/%m/%Y}")
    return boletins[dias_uteis_antes]


def ptax(moeda: str, dia: date, dias_uteis_antes: int = 0) -> Ptax:
    """PTAX de fechamento do último dia útil <= `dia`, recuando `dias_uteis_antes` boletins."""
    moeda = moeda.upper()
    if moeda == "BRL":
        return Ptax("BRL", dia, Decimal(1), Decimal(1))
    # Datas passadas não mudam: cache. Hoje/ontem ainda podem ganhar boletim novo.
    if dia < date.today() - timedelta(days=1):
        return _ptax_passada(moeda, dia, dias_uteis_antes)
    return _escolher(moeda, dia, dias_uteis_antes)


class ProvedorBcb:
    """Câmbio atual pela PTAX de venda; não fornece cotação de ativos."""

    nome = FONTE

    def cotacoes(self, ativos: Sequence[AtivoRef]) -> dict[str, CotacaoAtual]:
        return {}

    def cambios(self, moedas: Sequence[str]) -> dict[str, CotacaoAtual]:
        resultado = {}
        hoje = date.today()
        with httpx.Client() as cliente:
            for moeda in moedas:
                if moeda == "BRL":
                    continue
                try:
                    boletins = _consultar(moeda, hoje - timedelta(days=_JANELA_DIAS), hoje, cliente)
                except ErroPtax:
                    log.exception("PTAX %s indisponível", moeda)
                    continue
                if not boletins:
                    continue
                atual = boletins[0]
                variacao = atual.venda / boletins[1].venda - 1 if len(boletins) > 1 else None
                resultado[moeda] = CotacaoAtual(moeda, atual.venda, variacao, atual.data, self.nome)
        return resultado
