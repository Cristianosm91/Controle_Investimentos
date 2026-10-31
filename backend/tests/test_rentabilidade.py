from datetime import date
from decimal import Decimal as D

import pytest

from app.models import IndiceMensal
from app.services import rentabilidade as r
from app.services.posicao import Movimento


def mov(dia, evento, qtd, preco="0", taxas="0", ativo=1, cambio="1", daytrade=False):
    return Movimento(1, ativo, dia, evento, D(qtd), D(preco), D(taxas), daytrade, 0, D(cambio))


def precificacao(precos: dict[int, list[tuple[date, str]]], cambios=None, moedas=None):
    return r.Precificacao(
        {a: r.Serie((d, D(p)) for d, p in pts) for a, pts in precos.items()},
        {m: r.Serie((d, D(v)) for d, v in pts) for m, pts in (cambios or {}).items()},
        moedas or {},
    )


def test_meses_ate_o_fim_do_mes():
    assert r.meses(date(2024, 1, 15), date(2024, 3, 2)) == [date(2024, 1, 31), date(2024, 2, 29), date(2024, 3, 31)]


def test_serie_carrega_ultimo_valor():
    s = r.Serie([(date(2024, 1, 10), D(1)), (date(2024, 1, 20), D(2))])
    assert s.em(date(2024, 1, 9)) is None
    assert s.em(date(2024, 1, 15)) == 1
    assert s.em(date(2024, 2, 1)) == 2


def test_twr_segue_formula_da_planilha():
    # Linhas de fev-abr/2017 da aba dashboard.: aporte de 560,93; proventos de 3,63 e 3,50.
    movs = [mov(date(2017, 2, 9), "C", "1", "560.93")]
    proventos = [(date(2017, 3, 15), D("3.63")), (date(2017, 4, 15), D("3.50"))]
    precos = precificacao({1: [(date(2017, 2, 28), "579.31"), (date(2017, 3, 31), "630.50"), (date(2017, 4, 28), "624.02")]})
    fev, mar, abr = r.serie_mensal(movs, proventos, precos, date(2017, 4, 30))

    assert fev.fluxo == D("560.93") and fev.lucro == D("18.38")
    assert round(fev.twr, 8) == D("0.03276701")  # 18,38 / (0 + 560,93)
    assert mar.fluxo == D("-3.63") and mar.lucro == D("54.82")
    assert round(mar.twr, 11) == D("0.09462981823")  # fluxo negativo não entra na base
    assert round(abr.twr, 8) == D("-0.00472641")
    assert round(abr.twr_acumulado, 6) == D("0.125154")


def test_fluxo_desconta_lucro_realizado():
    movs = [mov(date(2024, 1, 5), "C", "10", "10"), mov(date(2024, 2, 5), "V", "-10", "12")]
    precos = precificacao({1: [(date(2024, 1, 31), "11"), (date(2024, 2, 29), "12")]})
    jan, fev = r.serie_mensal(movs, [], precos, date(2024, 2, 29))
    assert fev.lucro_trades == 20
    assert fev.investido == 0 and fev.mercado == 0
    assert fev.fluxo == D("-120")  # venda total retira custo + lucro
    assert fev.lucro == 10
    assert round(fev.twr, 6) == round(D(10) / D(110), 6)


def test_mercado_em_moeda_estrangeira_e_falta_de_cotacao():
    movs = [mov(date(2024, 1, 5), "C", "2", "100", cambio="5", ativo=1), mov(date(2024, 1, 5), "C", "1", "50", ativo=2)]
    precos = precificacao({1: [(date(2024, 1, 31), "110")]}, {"USD": [(date(2024, 1, 30), "5.5")]}, {1: "USD", 2: "BRL"})
    (jan,) = r.serie_mensal(movs, [], precos, date(2024, 1, 31))
    assert jan.mercado == D("2") * 110 * D("5.5") + 50  # ativo 2 sem cotação entra pelo custo
    assert jan.sem_cotacao == [2]


def test_xirr_conhecido():
    # 1000 hoje, 1100 em 1 ano -> 10% a.a.
    assert r.xirr([(date(2023, 1, 1), -1000), (date(2024, 1, 1), 1100)]) == pytest.approx(0.1, abs=1e-6)
    assert r.xirr([(date(2023, 1, 1), 1000)]) is None
    assert r.ao_mes(0.1) == pytest.approx(1.1 ** (1 / 12) - 1)


def test_xirr_perda_forte():
    assert r.xirr([(date(2023, 1, 1), -1000), (date(2024, 1, 1), 100)]) == pytest.approx(-0.9, abs=1e-6)


def test_tir_com_proventos_e_valor_final():
    movs = [mov(date(2023, 1, 1), "C", "10", "100")]
    taxa = r.tir(movs, [(date(2023, 7, 2), D(50))], D(1000), date(2024, 1, 1))
    assert 0.04 < taxa < 0.06


def test_caixa_por_evento():
    assert r.caixa(mov(date(2024, 1, 1), "C", "10", "10", "1")) == -101
    assert r.caixa(mov(date(2024, 1, 1), "V", "-10", "12", "1")) == 119
    assert r.caixa(mov(date(2024, 1, 1), "AMORTIZACAO", "10", "-0.5")) == 5
    assert r.caixa(mov(date(2024, 1, 1), "DESDOBRAMENTO", "10")) == 0
    assert r.caixa(mov(date(2024, 1, 1), "C", "2", "10", cambio="5")) == -100


def test_benchmarks_e_acumulado():
    indices = [
        IndiceMensal(competencia=date(2024, 1, 1), ibov=D(100), cdi=D("0.01")),
        IndiceMensal(competencia=date(2024, 2, 1), ibov=D(110), cdi=D("0.01")),
    ]
    jan, fev = r.benchmarks_mensais(indices, [date(2024, 1, 31), date(2024, 2, 29)])
    assert jan.ibov is None and fev.ibov == D("0.1")
    assert r.acumular([jan.cdi, fev.cdi]) == [D("0.01"), D("0.0201")]
    assert r.acumular([None, D("0.1")]) == [None, D("0.1")]
