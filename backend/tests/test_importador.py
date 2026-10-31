from datetime import datetime
from decimal import Decimal as D

import openpyxl
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db import Base
from app.models import Ativo, DarfPago, Investidor, Operacao, Parametro, PrejuizoInicial, Provento
from scripts.importar_planilha import Importador


@pytest.fixture
def sessao():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        s.add_all([Investidor(nome="Ana", cpf="12345678901"), Ativo(ticker="MGLU3", classe="AÇÃO")])
        s.commit()
        yield s
    engine.dispose()


def _planilha():
    wb = openpyxl.Workbook()
    btc = wb.active
    btc.title = "Página117"
    btc.append(["Movimentação", "Liquidação", "Lançamento", "Ticker", "Valor (R$)"])
    dia = datetime(2026, 8, 5)
    btc.append([dia, dia, "Crédito Ref. Taxa de Remuneração BTC MGLU", "MGLU", "R$ 23,24"])
    btc.append([dia, dia, "DEBITO CBLC IRRF S/ RENDIMENTO DE BTC MGLU", "MGLU", "-R$ 5,22"])
    btc.append([dia, dia, "Taxa de intermediação doador MGLU3 2026072301087022250001-2", "MGLU3", "-R$ 11,99"])
    btc.append([dia, dia, "TED RECEBIDA", "XXXX", "R$ 100,00"])

    darfs = wb.create_sheet("darfs.")
    darfs.append(["Controle de DARFs pagas por investidor"])
    darfs.append([])
    darfs.append(["cpf_investidor", "data_pagamento", "valor_pago"])
    darfs.append(["123.456.789-01", datetime(2026, 3, 31), 148.45])
    darfs.append(["99999999999", datetime(2026, 3, 31), 10])  # outro CPF

    cfg = wb.create_sheet("config.parâmetros")
    cfg.append(["DARF - Configurações de cálculo", None, None, None, None, None, "DARF - Transportar o prejuízo de um exercício"])
    cfg.append(["somar vendas de dayrade no limite 20k", None, None, None, True, None, "cpf", "op.normal", "day trade", "fii"])
    cfg.append(["considerar BDR como Ação (isenções) ", None, None, None, False, None, "ÚNICO INVESTIDOR", -1500, None, 300])
    cfg.append(["ano de início dos calculos DARF (ex. 2024)", None, None, None, 2019.0])
    return wb


def test_importa_aluguel_darfs_e_parametros_sem_duplicar(sessao):
    inv = sessao.scalar(select(Investidor))
    sessao.add(Parametro(chave="ir_bdr_como_acao", valor="1"))  # já definido no app: não sobrescreve
    for _ in range(2):
        imp = Importador(sessao, inv)
        wb = _planilha()
        imp.importar_aluguel(wb)
        imp.importar_darfs(wb)
        imp.importar_parametros_ir(wb)
        sessao.flush()

    (aluguel,) = sessao.scalars(select(Provento)).all()
    assert (aluguel.evento, aluguel.valor, aluguel.irrf, aluguel.taxas) == ("ALUGUEL", D("23.24"), D("5.22"), D("11.99"))
    (darf,) = sessao.scalars(select(DarfPago)).all()
    assert darf.competencia.isoformat() == "2026-02-01" and darf.valor == D("148.45")
    parametros = {p.chave: p.valor for p in sessao.scalars(select(Parametro))}
    assert parametros == {"ir_daytrade_no_limite": "1", "ir_bdr_como_acao": "1", "ir_ano_inicio": "2019"}
    prejuizos = {p.grupo: p.valor for p in sessao.scalars(select(PrejuizoInicial))}
    assert prejuizos == {"COMUM": D(1500), "FII": D(300)}


def _planilha_cripto(qtd_btc=0.5):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Histórico de rendimentos"
    ws["J115"] = 5.4401
    for linha, (ticker, preco, qtd) in enumerate(
        [("BTC", 80681.3, qtd_btc), ("XYZ", 2.5, 10), ("MGLU3", 1, 1), ("ZERO", 1, 0)], start=119,
    ):
        ws[f"J{linha}"], ws[f"K{linha}"], ws[f"L{linha}"] = ticker, preco, qtd
    ws["J124"], ws["K124"] = "Date", "Close"
    ws["J125"], ws["K125"], ws["L125"] = "ETH", 1, 1  # depois do quadro: ignorado
    return wb


def test_importa_criptos_como_abertura_sem_duplicar(sessao):
    inv = sessao.scalar(select(Investidor))
    abertura = datetime(2017, 10, 30).date()
    for qtd in (0.5, 0.7):  # reimportar com quantidade nova não duplica nem altera a abertura
        imp = Importador(sessao, inv)
        imp.importar_cripto(_planilha_cripto(qtd), abertura)
        sessao.flush()

    ops = {o.ativo.ticker: o for o in sessao.scalars(select(Operacao))}
    assert set(ops) == {"BTC", "XYZ"}
    btc = ops["BTC"]
    assert (btc.data, btc.evento, btc.quantidade, btc.preco, btc.moeda, btc.cambio) == (
        abertura, "C", D("0.5"), D("80681.3"), "USD", D("5.4401"),
    )
    assert (btc.ativo.classe, btc.ativo.coingecko_id, btc.ativo.cotacao_automatica) == ("CRIPTO", "bitcoin", True)
    assert ops["XYZ"].ativo.coingecko_id is None
    assert any("MGLU3 já cadastrado" in a for a in imp.avisos)
    assert sessao.scalar(select(Ativo).where(Ativo.ticker == "ETH")) is None
