from datetime import date
from decimal import Decimal as D

import pandas as pd

from app.providers import indices
from app.providers.yahoo import desfazer_ajuste_de_splits


def test_interpreta_sgs_em_pontos_percentuais():
    r = indices.interpretar_sgs([{"data": "01/07/2026", "valor": "1.22"}, {"data": "01/08/2026", "valor": ""}])
    assert r == {date(2026, 7, 1): D("1.22")}


def test_interpreta_b3_e_fecha_o_mes_no_ultimo_dia_com_valor():
    dados = {
        "results": [
            {"day": 1, "rateValue1": None, "rateValue2": "64.836,12"},
            {"day": 30, "rateValue1": "64.000,00", "rateValue2": None},
            {"day": 31, "rateValue1": "64.670,78", "rateValue2": None},
        ]
    }
    diarios = indices.interpretar_b3_ano(2017, dados)
    assert diarios[date(2017, 1, 31)] == D("64670.78")
    assert indices.fechamentos_mensais(diarios) == {date(2017, 1, 1): D("64670.78"), date(2017, 2, 1): D("64836.12")}


def test_desfaz_ajuste_de_split_do_yahoo():
    dias = pd.to_datetime(["2024-06-06", "2024-06-07", "2024-06-10", "2024-06-11"])
    ajustado = pd.Series([120.99, 120.88, 121.79, 120.91], index=dias)
    splits = pd.Series([0, 0, 10, 0], index=dias)
    bruto = desfazer_ajuste_de_splits(ajustado, splits)
    assert list(bruto.round(2)) == [1209.9, 1208.8, 121.79, 120.91]


def test_sem_split_nao_altera():
    serie = pd.Series([1.0, 2.0], index=pd.to_datetime(["2024-01-01", "2024-01-02"]))
    assert desfazer_ajuste_de_splits(serie, None).equals(serie)
