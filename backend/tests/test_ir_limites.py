"""Bordas exatas dos limites fiscais da apuração de IR (CAL-008 / PP-010).

Fonte dos valores esperados (independente da saída do código):
- README.md, seção "Imposto de renda": ações isentas com vendas de ações <= R$ 20 mil no mês; DARF abaixo
  de R$ 10 acumula para o mês seguinte; exterior até 2023 isento com vendas <= R$ 35 mil no mês (GCAP mensal,
  sem compensação); desde 2024 (Lei 14.754/2023) lucros no ano a 15%, com compensação de prejuízo.
- Seed da tabela `regra_fiscal` (alembic/versions/281775d6ea3d_imposto_de_renda.py, `_REGRAS`), transcrito à mão
  em `SEED_REGRA_FISCAL` abaixo.
Os valores são sintéticos; cada esperado traz a conta feita à mão no comentário.
"""

from datetime import date
from decimal import Decimal as D

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.models import RegraFiscal
from app.services import ir
from app.services.ir import Fato, apurar_exterior, apurar_mensal, fatos_por_mes, regra_vigente
from app.services.posicao import Movimento

# (categoria, início, fim, alíquota, limite de isenção, apuração) — cópia manual do seed da migração.
SEED_REGRA_FISCAL = [
    ("ACAO", "2005-01-01", None, "0.15", "20000", "MENSAL"),
    ("BDR", "2005-01-01", None, "0.15", None, "MENSAL"),
    ("ETF", "2005-01-01", None, "0.15", None, "MENSAL"),
    ("OPCAO", "2005-01-01", None, "0.15", None, "MENSAL"),
    ("DAYTRADE", "2005-01-01", None, "0.20", None, "MENSAL"),
    ("FII", "2005-01-01", None, "0.20", None, "MENSAL"),
    ("EXTERIOR", "2005-01-01", "2023-12-31", "0.15", "35000", "MENSAL"),
    ("EXTERIOR", "2024-01-01", None, "0.15", None, "ANUAL"),
]

JAN, FEV, MAR = date(2025, 1, 1), date(2025, 2, 1), date(2025, 3, 1)
DEZ_2023, JAN_2024 = date(2023, 12, 1), date(2024, 1, 1)


def _regras_do_banco() -> list[ir.Regra]:
    """Grava o seed numa `regra_fiscal` em memória e lê pelo mesmo caminho do serviço."""
    engine = create_engine("sqlite://", poolclass=StaticPool)
    Base.metadata.create_all(engine)
    try:
        with Session(engine) as sessao:
            for categoria, inicio, fim, aliquota, limite, apuracao in SEED_REGRA_FISCAL:
                sessao.add(RegraFiscal(
                    categoria=categoria, vigencia_inicio=date.fromisoformat(inicio),
                    vigencia_fim=date.fromisoformat(fim) if fim else None, aliquota=D(aliquota),
                    limite_isencao=D(limite) if limite else None, apuracao=apuracao,
                ))
            sessao.commit()
            return ir.carregar_regras(sessao)
    finally:
        engine.dispose()


@pytest.fixture(params=["regras_padrao", "regra_fiscal_seed"])
def regras(request):
    """Roda cada borda com as regras padrão (tabela vazia) e com as lidas da tabela `regra_fiscal`."""
    return list(ir.REGRAS_PADRAO) if request.param == "regras_padrao" else _regras_do_banco()


def _apurar(fatos, regras, inicio=JAN, fim=MAR, **kw):
    return {m.competencia: m for m in apurar_mensal(fatos, regras, inicio, fim, **kw)}


def _cat(mes, categoria):
    return next(c for c in mes.categorias if c.categoria == categoria)


def test_regras_padrao_iguais_ao_seed_da_regra_fiscal():
    esperado = {
        (c, date.fromisoformat(i), date.fromisoformat(f) if f else None, D(a), D(lim) if lim else None, ap)
        for c, i, f, a, lim, ap in SEED_REGRA_FISCAL
    }
    obtido = {(r.categoria, r.inicio, r.fim, r.aliquota, r.limite_isencao, r.apuracao) for r in ir.REGRAS_PADRAO}
    assert obtido == esperado
    assert {(r.categoria, r.inicio, r.fim, r.aliquota, r.limite_isencao, r.apuracao) for r in _regras_do_banco()} == esperado


# ---------- Isenção de R$ 20 mil (ações, vendas no mês <= 20.000,00) ----------

@pytest.mark.parametrize(
    ("vendas", "isento", "imposto"),
    [
        ("19999.99", True, "0"),  # 19.999,99 <= 20.000,00 → isento
        ("20000.00", True, "0"),  # 20.000,00 <= 20.000,00 → isento (limite inclusivo: "≤ R$ 20 mil")
        ("20000.01", False, "150.00"),  # 20.000,01 > 20.000,00 → tributa: 1.000,00 × 15% = 150,00
    ],
)
def test_isencao_acoes_no_limite_exato(regras, vendas, isento, imposto):
    meses = _apurar({(JAN, "ACAO"): Fato(vendas=D(vendas), lucro=D(1000))}, regras)
    assert _cat(meses[JAN], "ACAO").isento is isento
    assert meses[JAN].imposto == D(imposto)


@pytest.mark.parametrize(
    ("vendas_daytrade", "imposto"),
    [
        ("4999.99", "0"),  # 15.000,00 + 4.999,99 = 19.999,99 → isento
        ("5000.00", "0"),  # 15.000,00 + 5.000,00 = 20.000,00 → isento
        ("5000.01", "150.00"),  # 15.000,00 + 5.000,01 = 20.000,01 → 1.000,00 × 15% = 150,00
    ],
)
def test_limite_de_20_mil_somando_daytrade_no_limite_exato(regras, vendas_daytrade, imposto):
    fatos = {
        (JAN, "ACAO"): Fato(vendas=D(15000), lucro=D(1000)),
        (JAN, "DAYTRADE"): Fato(vendas=D(vendas_daytrade), lucro=D(0)),
    }
    assert _apurar(fatos, regras, somar_no_limite={"DAYTRADE"})[JAN].imposto == D(imposto)


@pytest.mark.parametrize(
    ("preco_venda", "vendas", "imposto"),
    [
        # 1.000 × 19,99999 = 19.999,99 → isento (lucro 19.999,99 − 5,00 − 10.000,00 = 9.994,99 não tributado)
        ("19.99999", "19999.99", "0"),
        # 1.000 × 20,00 = 20.000,00 (taxa de 5,00 não reduz o valor de alienação) → isento
        ("20", "20000.00", "0"),
        # 1.000 × 20,00001 = 20.000,01; lucro 20.000,01 − 5,00 − 10.000,00 = 9.995,01;
        # 9.995,01 × 15% = 1.499,2515 → 1.499,25
        ("20.00001", "20000.01", "1499.25"),
    ],
)
def test_isencao_pelo_valor_bruto_das_vendas_a_partir_das_operacoes(regras, preco_venda, vendas, imposto):
    ops = [
        ir.OperacaoIR(Movimento(1, 1, date(2025, 1, 2), "C", D(1000), D(10), D(0), ordem=1), "AAAA3", "AÇÃO", "BRL"),
        ir.OperacaoIR(
            Movimento(1, 1, date(2025, 1, 20), "V", D(-1000), D(preco_venda), D(5), ordem=2), "AAAA3", "AÇÃO", "BRL"
        ),
    ]
    fatos, _ = fatos_por_mes(ops)
    assert fatos[(JAN, "ACAO")].vendas == D(vendas)
    assert _apurar(fatos, regras, fim=JAN)[JAN].imposto == D(imposto)


# ---------- DARF mínimo de R$ 10,00 (abaixo acumula; 10,00 é devido) ----------
# FII a 20% dá imposto exato em centavos sem depender do modo de arredondamento.

@pytest.mark.parametrize(
    ("lucro_fii", "darf", "transportado"),
    [
        ("49.95", "0", "9.99"),  # 49,95 × 20% = 9,99 < 10,00 → acumula
        ("50.00", "10.00", "0"),  # 50,00 × 20% = 10,00 → devido
        ("50.05", "10.01", "0"),  # 50,05 × 20% = 10,01 → devido
    ],
)
def test_darf_minimo_no_limite_exato(regras, lucro_fii, darf, transportado):
    m = _apurar({(JAN, "FII"): Fato(vendas=D(1000), lucro=D(lucro_fii))}, regras, fim=JAN)[JAN]
    assert m.darf == D(darf) and m.darf_transportado == D(transportado)


def test_darf_de_9_99_sem_novo_imposto_continua_acumulado(regras):
    # Jan: 49,95 × 20% = 9,99 → acumula; Fev/Mar sem imposto: 0 + 9,99 = 9,99 < 10,00 → continua acumulado.
    meses = _apurar({(JAN, "FII"): Fato(vendas=D(1000), lucro=D("49.95"))}, regras)
    assert [(m.darf, m.darf_transportado) for m in meses.values()] == [(0, D("9.99"))] * 3


def test_darf_acumulado_cruza_10_em_dois_meses(regras):
    # Jan: 49,95 × 20% = 9,99 → acumula. Fev: 0,05 × 20% = 0,01; 9,99 + 0,01 = 10,00 → devido.
    meses = _apurar(
        {(JAN, "FII"): Fato(vendas=D(100), lucro=D("49.95")), (FEV, "FII"): Fato(vendas=D(100), lucro=D("0.05"))},
        regras,
    )
    assert meses[JAN].darf == 0 and meses[JAN].darf_transportado == D("9.99")
    assert meses[FEV].darf_anterior == D("9.99") and meses[FEV].darf_mes == D("0.01")
    assert meses[FEV].darf == D("10.00") and meses[FEV].darf_transportado == 0
    assert meses[MAR].darf == 0 and meses[MAR].darf_anterior == 0


def test_darf_acumulado_em_dois_meses_ainda_abaixo_e_pago_no_terceiro(regras):
    # Jan: 25,00 × 20% = 5,00. Fev: 24,95 × 20% = 4,99; 5,00 + 4,99 = 9,99 < 10,00 → acumula.
    # Mar: 0,05 × 20% = 0,01; 9,99 + 0,01 = 10,00 → devido.
    meses = _apurar({
        (JAN, "FII"): Fato(vendas=D(100), lucro=D(25)),
        (FEV, "FII"): Fato(vendas=D(100), lucro=D("24.95")),
        (MAR, "FII"): Fato(vendas=D(100), lucro=D("0.05")),
    }, regras)
    assert meses[FEV].darf == 0 and meses[FEV].darf_transportado == D("9.99")
    assert meses[MAR].darf == D("10.00")


def test_darf_de_10_menos_irrf_fica_abaixo_do_minimo(regras):
    # 50,00 × 20% = 10,00 de imposto; IRRF 0,01 abate → 9,99 < 10,00 → acumula.
    m = _apurar({(JAN, "FII"): Fato(vendas=D(1000), lucro=D(50), irrf=D("0.01"))}, regras, fim=JAN)[JAN]
    assert m.imposto == D("10.00") and m.darf_mes == D("9.99")
    assert m.darf == 0 and m.darf_transportado == D("9.99")


def test_darf_acumulado_atravessa_a_virada_do_ano(regras):
    # Dez/2024: 49,95 × 20% = 9,99 → acumula. Jan/2025: 0,05 × 20% = 0,01; 9,99 + 0,01 = 10,00 → devido.
    # O README só zera em janeiro o saldo de IRRF; o valor abaixo do mínimo segue para o mês seguinte.
    dez = date(2024, 12, 1)
    meses = _apurar(
        {(dez, "FII"): Fato(vendas=D(100), lucro=D("49.95")), (JAN, "FII"): Fato(vendas=D(100), lucro=D("0.05"))},
        regras, inicio=dez, fim=JAN,
    )
    assert meses[dez].darf == 0 and meses[dez].darf_transportado == D("9.99")
    assert meses[JAN].darf_anterior == D("9.99") and meses[JAN].darf == D("10.00")


# ---------- Exterior: R$ 35 mil (GCAP até 2023) e virada para a Lei 14.754/2023 ----------

@pytest.mark.parametrize(
    ("vendas", "imposto"),
    [
        ("34999.99", "0"),  # <= 35.000,00 → isento
        ("35000.00", "0"),  # <= 35.000,00 → isento (limite inclusivo: "≤ R$ 35 mil")
        ("35000.01", "150.00"),  # > 35.000,00 → 1.000,00 × 15% = 150,00
    ],
)
def test_exterior_isencao_de_35_mil_em_dezembro_de_2023(regras, vendas, imposto):
    fatos = {(DEZ_2023, "EXTERIOR"): Fato(vendas=D(vendas), lucro=D(1000))}
    a = apurar_exterior(fatos, regras, [2023])[0]
    assert a.imposto == D(imposto) and a.regimes == ["MENSAL"]


@pytest.mark.parametrize("vendas", ["34999.99", "35000.00", "35000.01"])
def test_exterior_sem_isencao_de_35_mil_em_janeiro_de_2024(regras, vendas):
    # Desde 2024 não há limite de isenção: 1.000,00 × 15% = 150,00 em qualquer valor de venda.
    fatos = {(JAN_2024, "EXTERIOR"): Fato(vendas=D(vendas), lucro=D(1000))}
    a = apurar_exterior(fatos, regras, [2024])[0]
    assert a.base == D(1000) and a.imposto == D("150.00") and a.regimes == ["ANUAL"]


def test_exterior_regra_vigente_no_ultimo_e_no_primeiro_dia(regras):
    ultimo, primeiro = regra_vigente(regras, "EXTERIOR", date(2023, 12, 31)), regra_vigente(regras, "EXTERIOR", JAN_2024)
    assert (ultimo.apuracao, ultimo.limite_isencao) == ("MENSAL", D(35000))
    assert (primeiro.apuracao, primeiro.limite_isencao) == ("ANUAL", None)


def test_exterior_virada_2023_2024_mesmas_vendas_regimes_diferentes(regras):
    # Dez/2023: vendas 30.000,00 <= 35.000,00 → isento (0). Jan/2024: mesmas vendas, sem isenção → 1.000,00 × 15% = 150,00.
    fatos = {
        (DEZ_2023, "EXTERIOR"): Fato(vendas=D(30000), lucro=D(1000)),
        (JAN_2024, "EXTERIOR"): Fato(vendas=D(30000), lucro=D(1000)),
    }
    anos = {a.ano: a for a in apurar_exterior(fatos, regras, [2023, 2024])}
    assert anos[2023].imposto == 0 and anos[2023].regimes == ["MENSAL"]
    assert anos[2024].base == D(1000) and anos[2024].imposto == D("150.00") and anos[2024].regimes == ["ANUAL"]


def test_exterior_prejuizo_de_dezembro_2023_nao_compensa_em_2024(regras):
    # GCAP até 2023 é "sem compensação de prejuízo" (seed/README): a perda de dez/2023 não vira saldo.
    # 2024: lucro 1.000,00 × 15% = 150,00, sem abater os 500,00 de 2023.
    fatos = {
        (DEZ_2023, "EXTERIOR"): Fato(vendas=D(40000), lucro=D(-500)),
        (JAN_2024, "EXTERIOR"): Fato(vendas=D(40000), lucro=D(1000)),
    }
    anos = {a.ano: a for a in apurar_exterior(fatos, regras, [2023, 2024])}
    assert anos[2023].imposto == 0 and anos[2023].prejuizo == 0
    assert anos[2024].base == D(1000) and anos[2024].imposto == D("150.00")


def test_exterior_prejuizo_anual_compensa_ate_zerar_no_limite(regras):
    # 2024: lucro 1.000,00 − 1.000,00 = 0 → imposto 0, saldo 0.
    # 2025: lucro 1.000,01 contra saldo 0 → 1.000,01 × 15% = 150,0015 → 150,00.
    fatos = {
        (date(2024, 3, 1), "EXTERIOR"): Fato(vendas=D(5000), lucro=D(-1000)),
        (date(2024, 9, 1), "EXTERIOR"): Fato(vendas=D(5000), lucro=D(1000)),
        (date(2025, 2, 1), "EXTERIOR"): Fato(vendas=D(5000), lucro=D("1000.01")),
    }
    anos = {a.ano: a for a in apurar_exterior(fatos, regras, [2024, 2025])}
    assert anos[2024].imposto == 0 and anos[2024].prejuizo == 0
    assert anos[2025].imposto == D("150.00")
