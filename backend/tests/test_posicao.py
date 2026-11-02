from datetime import date
from decimal import Decimal as D

import pytest

from app.services.posicao import Movimento, Posicao, aplicar, calcular_investimento, calcular_posicoes, consolidar


def mov(evento, qtd, preco="0", taxas="0", dia=1, inv=1, ativo=1, daytrade=False, ordem=0):
    return Movimento(inv, ativo, date(2020, 1, dia), evento, D(qtd), D(preco), D(taxas), daytrade, ordem)


def test_compra_inclui_taxas_no_preco_medio():
    # Primeira linha de op.normal: ABCP11 25 @ 13,196 + 22,55 de taxas -> PM 14,098
    p = calcular_posicoes([mov("C", "25", "13.196", "22.55")])[(1, 1)]
    assert p.quantidade == 25
    assert p.preco_medio == D("14.098")


def test_venda_mantem_pm_e_realiza_lucro():
    p = calcular_posicoes([
        mov("C", "10", "10", dia=1),
        mov("C", "10", "20", dia=2),
        mov("V", "-5", "25", "1", dia=3),
    ])[(1, 1)]
    assert p.quantidade == 15
    assert p.preco_medio == 15
    assert p.lucro_realizado == D("49")


def test_venda_total_zera_custo():
    p = calcular_posicoes([mov("C", "3", "10", dia=1), mov("V", "-3", "12", dia=2)])[(1, 1)]
    assert not p.aberta
    assert p.custo == 0
    assert p.lucro_realizado == 6


def test_grupamento_mantem_custo_total():
    p = calcular_posicoes([mov("C", "305", "15"), mov("DESDOBRAMENTO", "-244", dia=2)])[(1, 1)]
    assert p.quantidade == 61
    assert p.custo == D("4575")


def test_bonificacao_entra_pelo_custo_atribuido():
    p = calcular_posicoes([mov("C", "70", "20"), mov("BONIFICACAO", "7", "4.96", dia=2)])[(1, 1)]
    assert p.quantidade == 77
    assert p.custo == D("1434.72")
    assert p.preco_medio == D("1434.72") / 77


def test_preco_da_bonificacao_ajusta_pm_sem_aumentar_capital_investido():
    movimentos = [mov("C", "10", "10"), mov("BONIFICACAO", "2", "5", dia=2)]
    posicao = calcular_posicoes(movimentos)[(1, 1)]
    capital = calcular_investimento(movimentos)
    assert posicao.preco_medio == D("110") / 12
    assert capital.valor_investido == D("100")


def test_amortizacao_e_cisao_reduzem_custo():
    p = calcular_posicoes([
        mov("C", "19", "10"),
        mov("AMORTIZACAO", "19", "-0.5", dia=2),
        mov("CISAO", "19", "-1", dia=3),
    ])[(1, 1)]
    assert p.quantidade == 19
    assert p.custo == D("161.5")


def test_venda_apos_bonificacao_e_cisao_realiza_custo_ajustado():
    p = calcular_posicoes([
        mov("C", "10", "10"),
        mov("BONIFICACAO", "2", "5", dia=2),
        mov("CISAO", "12", "-1", dia=3),
        mov("V", "-6", "12", dia=4),
    ])[(1, 1)]
    assert p.quantidade == 6
    assert p.custo == 49
    assert p.preco_medio == D("49") / 6
    assert p.lucro_realizado == 23


def test_capital_historico_e_aberto_nao_diminuem_com_venda_ou_evento_sem_caixa():
    resultado = calcular_investimento([
        mov("C", "10", "10", "0.2"),
        mov("V", "-4", "15", "0.2", dia=2),
        mov("BONIFICACAO", "2", "5", dia=3),
        mov("CISAO", "8", "-1", dia=4),
        mov("AMORTIZACAO", "8", "-0.5", dia=5),
        mov("C", "1", "20", "0.2", dia=6, daytrade=True),
        mov("V", "-1", "21", dia=6, daytrade=True, ordem=1),
    ])
    assert resultado.valor_investido == D("60.12")
    assert resultado.valor_investido_posicoes_abertas == D("60.12")
    assert resultado.capital_por_posicao[(1, 1)] == D("60.12")


def test_resultado_realizado_desconta_taxas_e_irrf():
    p = calcular_posicoes([
        mov("C", "2", "10", "1"),
        Movimento(1, 1, date(2020, 1, 2), "V", D("-1"), D("12"), D("0.5"), irrf=D("0.1")),
    ])[(1, 1)]
    assert p.custo == D("10.5")
    assert p.lucro_realizado == D("0.9")


def test_capital_aberto_zera_na_venda_total_e_transferencia_nao_novo_desembolso():
    resultado = calcular_investimento([
        mov("C", "10", "10"),
        mov("TRANSFERENCIA", "-10", "10", dia=2, ativo=1),
        mov("TRANSFERENCIA", "10", "10", dia=2, ativo=2, ordem=1),
        mov("V", "-10", "12", dia=3, ativo=2),
    ])
    assert resultado.valor_investido == 0
    assert resultado.valor_investido_posicoes_abertas == 0


def test_transferencia_troca_ticker_sem_lucro():
    movs = [
        mov("C", "100", "10", ativo=1),
        mov("TRANSFERENCIA", "-100", "10", dia=2, ativo=1),
        mov("TRANSFERENCIA", "100", "10", dia=2, ativo=2),
    ]
    pos = calcular_posicoes(movs)
    assert not pos[(1, 1)].aberta
    assert pos[(1, 1)].lucro_realizado == 0
    assert pos[(1, 2)].preco_medio == 10


def test_venda_de_subscricao_e_lucro_integral():
    p = calcular_posicoes([mov("VENDA_SUBSCRICAO", "-20", "0.21")])[(1, 1)]
    assert p.lucro_realizado == D("4.20")
    assert p.quantidade == 0


def test_daytrade_nao_altera_posicao():
    # op.daytrade: PPLA11 +6 @16,46 (0,03) e -6 @16,10 (0,02) -> -2,21
    pos = calcular_posicoes([
        mov("C", "10", "5"),
        mov("C", "6", "16.46", "0.03", dia=2, daytrade=True, ordem=1),
        mov("V", "-6", "16.10", "0.02", dia=2, daytrade=True, ordem=2),
    ])
    p = pos[(1, 1)]
    assert p.quantidade == 10
    assert p.lucro_daytrade == D("-2.21")


def test_cambio_converte_custo_e_lucro_para_brl():
    # INTR: 200 cotas a R$ 37,36616502 + compra de 30 a US$ 5,11 com PTAX 5,1985 -> PM R$ 35,9572 (aba dados.)
    movs = [
        mov("C", "200", "37.36616502"),
        Movimento(1, 1, date(2020, 1, 2), "C", D("30"), D("5.11"), cambio=D("5.1985")),
        Movimento(1, 1, date(2020, 1, 3), "V", D("-30"), D("6"), D("1"), cambio=D("5")),
    ]
    p = calcular_posicoes(movs[:2])[(1, 1)]
    assert round(p.preco_medio, 4) == D("35.9572")
    p = calcular_posicoes(movs)[(1, 1)]
    assert round(p.lucro_realizado, 4) == round((30 * 6 - 1) * 5 - 30 * D("35.95723067"), 4)


def test_consolidar_varios_investidores():
    pos = calcular_posicoes([mov("C", "10", "10", inv=1), mov("C", "30", "20", inv=2)])
    c = consolidar(pos.values())[1]
    assert c.quantidade == 40
    assert c.preco_medio == D("17.5")


def test_evento_desconhecido():
    with pytest.raises(ValueError):
        aplicar(Posicao(1, 1), mov("XYZ", "1"))
