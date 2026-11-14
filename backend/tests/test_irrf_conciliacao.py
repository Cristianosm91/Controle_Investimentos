from datetime import date
from decimal import Decimal as D

import pytest

from app.services.ir import REGRAS_PADRAO, OperacaoIR, apurar_mensal, fatos_por_mes
from app.services.posicao import Movimento, calcular_posicoes


@pytest.mark.parametrize("daytrade", [False, True])
def test_lucro_liquido_igual_carteira_sem_deduzir_irrf_da_base(daytrade):
    compra = Movimento(1, 1, date(2025, 1, 2), "C", D(100), D(10), irrf=D(2), daytrade=daytrade)
    venda = Movimento(1, 1, date(2025, 1, 3), "V", D(-100), D(12), taxas=D(1), irrf=D(3), daytrade=daytrade)
    fatos, _ = fatos_por_mes([
        OperacaoIR(compra, "ETF1", "ETF", "BRL", compra.irrf),
        OperacaoIR(venda, "ETF1", "ETF", "BRL", venda.irrf),
    ])
    mes = apurar_mensal(fatos, REGRAS_PADRAO, date(2025, 1, 1), date(2025, 1, 1))[0]
    categoria = next(c for c in mes.categorias if c.categoria == ("DAYTRADE" if daytrade else "ETF"))
    pos = calcular_posicoes([compra, venda])[(1, 1)]
    assert categoria.lucro == categoria.base == 199
    assert categoria.lucro_liquido == (pos.lucro_daytrade if daytrade else pos.lucro_realizado) == 194
    assert categoria.irrf == mes.irrf == mes.irrf_compensado == 5
    assert mes.imposto == (D("39.80") if daytrade else D("29.85"))
    assert mes.darf == (D("34.80") if daytrade else D("24.85"))
    assert mes.irrf_saldo == 0


def test_compra_com_irrf_venda_parcial_e_saldo_acumulado(cliente):
    inv = cliente.post("/api/investidores", json={"nome": "Teste IRRF"}).json()["id"]
    ativo = cliente.post("/api/ativos", json={"ticker": "ETF1", "classe": "ETF"}).json()["id"]
    for dia, evento, qtd, preco, taxas, irrf in [
        ("2025-01-02", "C", 100, 10, 0, 2),
        ("2025-02-03", "V", -50, 12, 1, 0.03),
    ]:
        r = cliente.post("/api/operacoes", json={
            "investidor_id": inv, "ativo_id": ativo, "data": dia, "evento": evento,
            "quantidade": qtd, "preco": preco, "taxas": taxas, "irrf": irrf,
        })
        assert r.status_code == 201, r.text
    r = cliente.get("/api/ir/apuracao", params={"investidor": inv, "ano": 2025})
    assert r.status_code == 200, r.text
    meses = r.json()["meses"]
    jan = next(m for m in meses if m["competencia"] == "2025-01-01")
    fev = next(m for m in meses if m["competencia"] == "2025-02-01")
    categoria = next(c for c in fev["categorias"] if c["categoria"] == "ETF")
    assert jan["irrf_saldo"] == jan["irrf"] == 2 and jan["irrf_compensado"] == 0
    assert categoria["lucro"] == categoria["base"] == 99
    assert categoria["lucro_liquido"] == pytest.approx(97.97)
    pos = cliente.get("/api/posicoes").json()[0]
    assert pos["lucro_realizado"] == categoria["lucro_liquido"]
    assert fev["irrf"] == 0.03 and fev["irrf_compensado"] == 2.03 and fev["irrf_saldo"] == 0
    assert fev["imposto"] == 14.85 and fev["darf"] == 12.82
