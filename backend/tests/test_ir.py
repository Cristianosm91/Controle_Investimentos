from datetime import date
from decimal import Decimal as D

import pytest

from app.services import ir
from app.services.ir import Fato, Regra, apurar_exterior, apurar_mensal, categoria_ir, fatos_por_mes, regra_vigente
from app.services.posicao import Movimento

JAN, FEV, MAR = date(2025, 1, 1), date(2025, 2, 1), date(2025, 3, 1)
REGRAS = ir.REGRAS_PADRAO


def _apurar(fatos, inicio=JAN, fim=MAR, **kw):
    return {m.competencia: m for m in apurar_mensal(fatos, REGRAS, inicio, fim, **kw)}


def _cat(mes, categoria):
    return next(c for c in mes.categorias if c.categoria == categoria)


@pytest.mark.parametrize(
    ("classe", "moeda", "daytrade", "bdr_acao", "esperado"),
    [
        ("AÇÃO", "BRL", False, False, "ACAO"),
        ("ação", "BRL", True, False, "DAYTRADE"),
        ("FII", "BRL", True, False, "FII"),
        ("BDR", "BRL", False, False, "BDR"),
        ("BDR", "BRL", False, True, "ACAO"),
        ("STOCK", "USD", False, False, "EXTERIOR"),
        ("ETF_US", "BRL", False, False, "EXTERIOR"),
        ("ETF RF", "BRL", False, False, None),
        ("CDB", "BRL", False, False, None),
    ],
)
def test_categoria_ir(classe, moeda, daytrade, bdr_acao, esperado):
    assert categoria_ir(classe, moeda, daytrade, bdr_acao) == esperado


def test_isencao_de_20_mil_so_para_acoes():
    meses = _apurar({
        (JAN, "ACAO"): Fato(vendas=D(15000), lucro=D(1000)),
        (FEV, "ACAO"): Fato(vendas=D(25000), lucro=D(1000)),
        (MAR, "ETF"): Fato(vendas=D(5000), lucro=D(100)),
    })
    assert _cat(meses[JAN], "ACAO").isento and meses[JAN].imposto == 0
    assert not _cat(meses[FEV], "ACAO").isento and meses[FEV].imposto == D("150.00")
    assert meses[MAR].imposto == D("15.00")


def test_prejuizo_de_mes_isento_e_compensavel():
    meses = _apurar({
        (JAN, "ACAO"): Fato(vendas=D(10000), lucro=D(-500)),
        (FEV, "ACAO"): Fato(vendas=D(30000), lucro=D(1000)),
    })
    assert meses[JAN].prejuizo["COMUM"] == 500
    assert _cat(meses[FEV], "ACAO").base == 500 and meses[FEV].imposto == D("75.00")
    assert meses[FEV].prejuizo["COMUM"] == 0


def test_operacoes_comuns_compensam_entre_si_mas_nao_com_fii_e_daytrade():
    meses = _apurar({
        (JAN, "ACAO"): Fato(vendas=D(30000), lucro=D(-300)),
        (JAN, "BDR"): Fato(vendas=D(5000), lucro=D(500)),
        (JAN, "DAYTRADE"): Fato(vendas=D(1000), lucro=D(-100)),
        (FEV, "FII"): Fato(vendas=D(1000), lucro=D(400)),
        (MAR, "DAYTRADE"): Fato(vendas=D(1000), lucro=D(300)),
    })
    assert _cat(meses[JAN], "BDR").base == 200 and meses[JAN].imposto == D("30.00")
    assert meses[FEV].imposto == D("80.00")  # FII não usa o prejuízo de day trade
    assert _cat(meses[MAR], "DAYTRADE").base == 200 and meses[MAR].imposto == D("40.00")


def test_darf_abaixo_do_minimo_acumula():
    meses = _apurar({(JAN, "FII"): Fato(vendas=D(100), lucro=D(30)), (FEV, "FII"): Fato(vendas=D(100), lucro=D(25))})
    assert meses[JAN].darf == 0 and meses[JAN].darf_transportado == D("6.00")
    assert meses[FEV].darf == D("11.00") and meses[FEV].darf_anterior == D("6.00")
    assert meses[MAR].darf == 0 and meses[MAR].darf_transportado == 0


def test_irrf_compensa_no_mesmo_ano_e_zera_em_janeiro():
    dez, jan = date(2024, 12, 1), date(2025, 1, 1)
    meses = _apurar(
        {(date(2024, 11, 1), "ACAO"): Fato(vendas=D(10000), lucro=D(10), irrf=D(5)),
         (jan, "FII"): Fato(vendas=D(1000), lucro=D(100))},
        inicio=date(2024, 11, 1), fim=jan,
    )
    assert meses[dez].irrf_saldo == 5
    assert meses[jan].irrf_compensado == 0 and meses[jan].darf == D("20.00")


def test_irrf_abate_imposto_e_pagamento_reduz_saldo():
    meses = _apurar({(JAN, "FII"): Fato(vendas=D(1000), lucro=D(100), irrf=D("0.5"))}, pagos={JAN: D("19.50")})
    assert meses[JAN].darf == D("19.50") and meses[JAN].saldo == 0


def test_prejuizo_inicial_e_limite_com_outras_categorias():
    fatos = {(JAN, "ACAO"): Fato(vendas=D(15000), lucro=D(1000)), (JAN, "DAYTRADE"): Fato(vendas=D(10000), lucro=D(0))}
    assert _apurar(fatos)[JAN].imposto == 0
    m = _apurar(fatos, somar_no_limite={"DAYTRADE"}, prejuizo_inicial={"COMUM": D(400)})[JAN]
    assert _cat(m, "ACAO").base == 600 and m.imposto == D("90.00")
    opcoes = {(JAN, "ACAO"): Fato(vendas=D(15000), lucro=D(1000)), (JAN, "OPCAO"): Fato(vendas=D(6000), lucro=D(0))}
    assert _apurar(opcoes, somar_no_limite={"OPCAO"})[JAN].imposto == D("150.00")
    assert _apurar(opcoes, somar_no_limite={"BDR", "ETF"})[JAN].imposto == 0


def test_subscricao_de_fii_isenta_ate_setembro_de_2021():
    def ops(dia):
        return [ir.OperacaoIR(Movimento(1, 1, dia, "VENDA_SUBSCRICAO", D(-10), D(5)), "XPLG12", "FII", "BRL")]

    assert fatos_por_mes(ops(date(2021, 9, 28)))[0][(date(2021, 9, 1), "FII")].lucro == 50
    assert fatos_por_mes(ops(date(2021, 9, 28)), subscricao_fii_isenta=True)[0] == {}
    assert (date(2021, 10, 1), "FII") in fatos_por_mes(ops(date(2021, 10, 1)), subscricao_fii_isenta=True)[0]


def test_regra_vigente_escolhe_periodo():
    regras = [Regra("FII", date(2000, 1, 1), date(2025, 12, 31), D("0.2")), Regra("FII", date(2026, 1, 1), None, D("0.1"))]
    assert regra_vigente(regras, "FII", date(2025, 6, 1)).aliquota == D("0.2")
    assert regra_vigente(regras, "FII", date(2026, 6, 1)).aliquota == D("0.1")
    assert regra_vigente(regras, "ACAO", date(2026, 6, 1)) is None
    fatos = {(date(2026, 1, 1), "FII"): Fato(vendas=D(1000), lucro=D(1000))}
    meses = apurar_mensal(fatos, regras, date(2026, 1, 1), date(2026, 1, 1))
    assert meses[0].imposto == D("100.00")


def test_exterior_gcap_ate_2023_e_anual_desde_2024():
    fatos = {
        (date(2023, 3, 1), "EXTERIOR"): Fato(vendas=D(40000), lucro=D(1000)),
        (date(2023, 4, 1), "EXTERIOR"): Fato(vendas=D(20000), lucro=D(1000)),  # isento: vendas até R$ 35 mil
        (date(2024, 2, 1), "EXTERIOR"): Fato(vendas=D(5000), lucro=D(-500)),
        (date(2024, 9, 1), "EXTERIOR"): Fato(vendas=D(5000), lucro=D(1500)),
        (date(2025, 1, 1), "EXTERIOR"): Fato(vendas=D(5000), lucro=D(-300)),
    }
    anos = {a.ano: a for a in apurar_exterior(fatos, REGRAS, [2023, 2024, 2025], {2023: (D(50), D(15)), 2024: (D(100), D(20))})}
    assert anos[2023].imposto == D("150.00") and anos[2023].regimes == ["MENSAL"]
    assert anos[2023].dividendos == 50  # informativo (carnê-leão), fora do imposto estimado
    # 2024: lucro líquido 1.000 + dividendos 100 → 165, menos 15 de crédito (limitado ao IR dos dividendos).
    assert anos[2024].base == 1100 and anos[2024].imposto == D("150.00")
    assert anos[2025].imposto == 0 and anos[2025].prejuizo == 300


def test_fatos_por_mes_usa_lucro_do_preco_medio():
    ops = [
        ir.OperacaoIR(Movimento(1, 1, date(2025, 1, 2), "C", D(100), D(10), D(0), ordem=1), "PETR4", "AÇÃO", "BRL"),
        ir.OperacaoIR(Movimento(1, 1, date(2025, 2, 3), "V", D(-50), D(12), D(1), ordem=2), "PETR4", "AÇÃO", "BRL", D("0.03")),
        ir.OperacaoIR(Movimento(1, 2, date(2025, 2, 3), "C", D(1), D(100), ordem=3), "CDB1", "CDB", "BRL"),
        ir.OperacaoIR(Movimento(1, 2, date(2025, 2, 4), "V", D(-1), D(110), ordem=4), "CDB1", "CDB", "BRL"),
    ]
    fatos, ignorados = fatos_por_mes(ops)
    f = fatos[(FEV, "ACAO")]
    assert (f.vendas, f.lucro, f.irrf) == (600, 99, D("0.03"))
    assert ignorados == {"CDB1"}


# ---------- API ----------

@pytest.fixture
def base(cliente):
    inv = cliente.post("/api/investidores", json={"nome": "Ana"}).json()["id"]
    petr = cliente.post("/api/ativos", json={"ticker": "PETR4", "classe": "AÇÃO", "cnpj": "33.000.167/0001-01"}).json()
    hglg = cliente.post("/api/ativos", json={"ticker": "HGLG11", "classe": "FII"}).json()["id"]

    def op(ativo, data, evento, qtd, preco, irrf=0):
        r = cliente.post("/api/operacoes", json={"investidor_id": inv, "ativo_id": ativo, "data": data, "evento": evento,
                                                 "quantidade": qtd, "preco": preco, "irrf": irrf})
        assert r.status_code == 201, r.text

    op(petr["id"], "2025-01-10", "C", 1000, 30)
    op(petr["id"], "2025-02-10", "V", -1000, 31, irrf=1.55)  # vendas 31 mil: lucro 1.000 tributável
    op(hglg, "2025-01-10", "C", 10, 100)
    op(hglg, "2025-03-10", "V", -10, 105)  # lucro 50 → R$ 10 de IR
    itsa = cliente.post("/api/ativos", json={"ticker": "ITSA4", "classe": "AÇÃO"}).json()["id"]
    op(itsa, "2025-05-10", "C", 100, 10)
    cliente.post("/api/proventos", json={"investidor_id": inv, "ativo_id": petr["id"], "data_pagamento": "2025-01-20",
                                         "evento": "JSCP", "valor": 100, "irrf": 15})
    cliente.post("/api/proventos", json={"investidor_id": inv, "ativo_id": hglg, "data_pagamento": "2025-02-15",
                                         "evento": "RENDIMENTO", "valor": 8})
    cliente.post("/api/proventos", json={"investidor_id": inv, "ativo_id": petr["id"], "data_pagamento": "2025-04-15",
                                         "evento": "ALUGUEL", "valor": 20, "irrf": 3, "taxas": 5})
    return {"inv": inv, "petr": petr, "hglg": hglg}


def test_api_apuracao_e_darf_pago(cliente, base):
    url = f"/api/ir/apuracao?investidor={base['inv']}&ano=2025"
    r = cliente.get(url).json()
    assert 2025 in r["anos"] and len(r["meses"]) == 12
    fev, mar = r["meses"][1], r["meses"][2]
    assert fev["imposto"] == 150 and fev["irrf_compensado"] == 1.55 and fev["darf"] == pytest.approx(148.45)
    assert mar["darf"] == 10

    pago = cliente.post("/api/ir/darfs", json={"investidor_id": base["inv"], "competencia": "2025-02-20",
                                                "data_pagamento": "2025-03-31", "valor": 148.45})
    assert pago.status_code == 201 and pago.json()["competencia"] == "2025-02-01"
    fev = cliente.get(url).json()["meses"][1]
    assert fev["pago"] == pytest.approx(148.45) and fev["saldo"] == pytest.approx(0)
    assert len(cliente.get(f"/api/ir/darfs?investidor={base['inv']}").json()) == 1
    assert cliente.delete(f"/api/ir/darfs/{pago.json()['id']}").status_code == 204
    assert cliente.get("/api/ir/apuracao").status_code == 422  # exige um investidor


def test_api_prejuizo_inicial_parametros_e_regras(cliente, base):
    url = f"/api/ir/prejuizos-iniciais?investidor={base['inv']}"
    assert cliente.put(url, json=[{"grupo": "COMUM", "valor": 400}, {"grupo": "FII", "valor": 0}]).json() == [
        {"grupo": "COMUM", "valor": 400.0}
    ]
    assert cliente.put(url, json=[{"grupo": "XYZ", "valor": 1}]).status_code == 422
    fev = cliente.get(f"/api/ir/apuracao?investidor={base['inv']}&ano=2025").json()["meses"][1]
    assert fev["imposto"] == 90

    p = cliente.get("/api/parametros").json()
    cliente.put("/api/parametros", json={**p, "ir_ano_inicio": 2026})
    r = cliente.get(f"/api/ir/apuracao?investidor={base['inv']}").json()
    assert all(m["competencia"] >= "2026-01-01" for m in r["meses"])

    assert cliente.get("/api/ir/regras").json() == []  # tabela vazia → regras padrão no cálculo
    regra = {"categoria": "FII", "vigencia_inicio": "2000-01-01", "aliquota": 0.1}
    assert cliente.post("/api/ir/regras", json={**regra, "categoria": "XX"}).status_code == 422
    assert cliente.post("/api/ir/regras", json={**regra, "vigencia_fim": "1999-01-01"}).status_code == 422
    rid = cliente.post("/api/ir/regras", json=regra).json()["id"]
    cliente.put("/api/parametros", json={**p, "ir_ano_inicio": None})
    mar = cliente.get(f"/api/ir/apuracao?investidor={base['inv']}&ano=2025").json()["meses"][2]
    assert mar["imposto"] == 5  # só a regra cadastrada vale (sem regra de ações → sem imposto em fev)
    assert cliente.delete(f"/api/ir/regras/{rid}").status_code == 204


def test_api_dirpf_e_cnpj_preservado(cliente, base):
    petr = base["petr"]
    assert petr["cnpj"] == "33000167000101"
    # Formulários que não enviam o CNPJ (ativos personalizados) não o apagam.
    cliente.put(f"/api/ativos/{petr['id']}", json={"ticker": "PETR4", "classe": "AÇÃO", "nome": "Petrobras"})
    assert next(a for a in cliente.get("/api/ativos").json() if a["ticker"] == "PETR4")["cnpj"] == "33000167000101"

    r = cliente.get(f"/api/ir/dirpf?investidor={base['inv']}&ano=2025").json()
    bens = {b["ticker"]: b for b in r["bens"]}
    assert set(bens) == {"ITSA4"}  # PETR4 e HGLG11 compradas e vendidas no ano não entram
    assert bens["ITSA4"]["custo_atual"] == 1000 and "Custo médio R$ 10,00" in bens["ITSA4"]["discriminacao"]
    assert any("ITSA4" in a for a in r["avisos"])  # sem CNPJ
    tipos = {(x["ficha"], x["ticker"], x["tipo"][:5]): x for x in r["rendimentos"]}
    assert tipos[("EXCLUSIVO", "PETR4", "Juros")]["valor"] == 85
    assert tipos[("EXCLUSIVO", "PETR4", "Alugu")]["valor"] == 17 and tipos[("EXCLUSIVO", "PETR4", "Alugu")]["irrf"] == 3
    assert tipos[("ISENTO", "HGLG11", "Rendi")]["valor"] == 8
    assert r["prejuizo_final"]["COMUM"] == 0 and len(r["meses"]) == 12

    csv = cliente.get(f"/api/ir/dirpf.csv?investidor={base['inv']}&ano=2025")
    assert csv.status_code == 200 and "attachment" in csv.headers["content-disposition"]
    assert "BENS E DIREITOS" in csv.text and "33.000.167/0001-01" in csv.text
