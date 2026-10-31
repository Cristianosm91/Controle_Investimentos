from datetime import date
from decimal import Decimal as D

import pytest

from app.providers import bcb


def boletim(dia: str, compra: float, venda: float, tipo: str = "Fechamento") -> dict:
    return {"cotacaoCompra": compra, "cotacaoVenda": venda, "dataHoraCotacao": f"{dia} 13:09:28.123", "tipoBoletim": tipo}


VALORES = [
    boletim("2026-10-01", 5.18, 5.19, "Abertura"),
    boletim("2026-10-01", 5.2003, 5.2009),
    boletim("2026-10-02", 5.2232, 5.2238),
    boletim("2026-10-05", 5.30, 5.31, "Intermediário"),
]


def test_considera_so_fechamento_mais_recente_primeiro():
    r = bcb.interpretar_boletins("USD", VALORES)
    assert [p.data for p in r] == [date(2026, 10, 2), date(2026, 10, 1)]
    assert r[0].venda == D("5.2238")
    assert r[0].compra == D("5.2232")


@pytest.fixture
def consulta_falsa(monkeypatch):
    monkeypatch.setattr(bcb, "_consultar", lambda moeda, ini, fim, cliente=None: bcb.interpretar_boletins(moeda, VALORES))
    bcb._ptax_passada.cache_clear()


def test_fim_de_semana_usa_ultimo_dia_util(consulta_falsa):
    assert bcb.ptax("USD", date(2026, 10, 4)).data == date(2026, 10, 2)


def test_defasagem_em_dias_uteis(consulta_falsa):
    assert bcb.ptax("USD", date(2026, 10, 4), dias_uteis_antes=1).data == date(2026, 10, 1)


def test_sem_boletim_suficiente(consulta_falsa):
    with pytest.raises(bcb.ErroPtax):
        bcb.ptax("USD", date(2026, 10, 4), dias_uteis_antes=2)


def test_brl_e_identidade():
    assert bcb.ptax("BRL", date(2026, 10, 4)).venda == 1
