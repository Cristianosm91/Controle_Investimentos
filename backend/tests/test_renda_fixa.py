from datetime import date, timedelta
from decimal import Decimal as D

import pytest

from app.services.renda_fixa import fator


def test_prefixado_um_ano():
    assert fator(date(2025, 1, 1), date(2026, 1, 1), {}, taxa_aa=D("0.10")) == D("1.1")


def test_indice_mensal_pro_rata_e_percentual():
    cdi = {date(2026, 1, 1): D("0.01")}
    assert fator(date(2026, 1, 1), date(2026, 2, 1), cdi) == D("1.01")
    assert fator(date(2026, 1, 1), date(2026, 2, 1), cdi, indexador_pct=D("0.5")) == D("1.005")
    meio = fator(date(2026, 1, 1), date(2026, 1, 16), cdi)
    assert meio == pytest.approx(D("1.01") ** (D(15) / 31), rel=D("1e-9"))


def test_mes_sem_indice_repete_o_ultimo_conhecido():
    cdi = {date(2026, 1, 1): D("0.01")}
    assert fator(date(2026, 1, 1), date(2026, 3, 1), cdi) == D("1.0201")


def test_indice_mais_taxa():
    ipca = {date(2026, 1, 1): D("0.005")}
    esperado = (1.005) * (1.06 ** (31 / 365))
    assert float(fator(date(2026, 1, 1), date(2026, 2, 1), ipca, taxa_aa=D("0.06"))) == pytest.approx(esperado)


def test_fim_antes_do_inicio():
    assert fator(date(2026, 2, 1), date(2026, 1, 1), {}, taxa_aa=D("0.1")) == 1


# ---------- API ----------

@pytest.fixture
def investidor(cliente):
    return cliente.post("/api/investidores", json={"nome": "Ana"}).json()["id"]


def test_ativo_prefixado_gera_cotas_e_valoriza_posicao(cliente, investidor):
    base = date.today() - timedelta(days=365)
    ativo = cliente.post(
        "/api/ativos",
        json={"ticker": "CDB PRE", "classe": "CDB", "cotacao_automatica": False, "indexador": "PRE",
              "taxa_aa": 0.1, "data_base": base.isoformat(), "mercado": None},
    )
    assert ativo.status_code == 201, ativo.text
    ativo_id = ativo.json()["id"]
    cota = cliente.get(f"/api/ativos/{ativo_id}/cota", params={"data": date.today().isoformat()}).json()["cota"]
    assert cota == pytest.approx(1.1)

    cliente.post("/api/operacoes", json={"investidor_id": investidor, "ativo_id": ativo_id, "data": base.isoformat(),
                                         "evento": "C", "quantidade": 1000, "preco": 1})
    pos = cliente.get("/api/posicoes").json()[0]
    assert pos["cotacao_fonte"] == "Calculado" and pos["valor_mercado"] == pytest.approx(1100)


def test_validacoes_do_ativo_personalizado(cliente):
    base = {"ticker": "X", "cotacao_automatica": False, "data_base": "2026-01-01"}
    assert cliente.post("/api/ativos", json={**base, "indexador": "XYZ"}).status_code == 422
    assert cliente.post("/api/ativos", json={**base, "indexador": "PRE"}).status_code == 422  # sem taxa
    assert cliente.post("/api/ativos", json={**base, "indexador": "CDI", "cotacao_automatica": True}).status_code == 422
    cdi = cliente.post("/api/ativos", json={**base, "indexador": "cdi"}).json()
    assert cdi["indexador"] == "CDI" and cdi["indexador_pct"] == 1


def test_saldo_manual_define_a_cota(cliente, investidor):
    ativo_id = cliente.post("/api/ativos", json={"ticker": "PREV1", "classe": "PREV", "cotacao_automatica": False}).json()["id"]
    hoje = date.today().isoformat()
    assert cliente.post(f"/api/ativos/{ativo_id}/saldo", json={"data": hoje, "saldo": 1100}).status_code == 422  # sem posição
    cliente.post("/api/operacoes", json={"investidor_id": investidor, "ativo_id": ativo_id, "data": "2026-01-02",
                                         "evento": "C", "quantidade": 1000, "preco": 1})
    r = cliente.post(f"/api/ativos/{ativo_id}/saldo", json={"data": hoje, "saldo": 1100})
    assert r.status_code == 200 and r.json()["cota"] == pytest.approx(1.1)
    assert cliente.get("/api/posicoes").json()[0]["valor_mercado"] == pytest.approx(1100)
    assert len(cliente.get("/api/ativos", params={"personalizados": True}).json()) == 1
