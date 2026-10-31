from datetime import date, timedelta
from decimal import Decimal as D

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.models import Ativo, AtivoRadar, Cotacao, Fundamento, Investidor, Operacao, Provento
from app.services import cotacoes, cotahist, radar


def test_watchlist_api_adds_lists_and_removes_assets(cliente):
    ativo = cliente.post("/api/ativos", json={"ticker": "PETR4"}).json()
    resposta = cliente.post(f"/api/radar/{ativo['id']}")

    assert resposta.status_code == 201
    assert resposta.json() == {"ativo_id": ativo["id"], "ticker": "PETR4"}
    assert cliente.post(f"/api/radar/{ativo['id']}").status_code == 409

    lista = cliente.get("/api/radar")
    assert lista.status_code == 200
    assert lista.json()[0]["ticker"] == "PETR4"
    assert lista.json()[0]["tem_posicao"] is False
    assert lista.json()[0]["cotacao"] is None

    assert cliente.delete(f"/api/radar/{ativo['id']}").status_code == 204
    assert cliente.get("/api/radar").json() == []
    assert cliente.delete(f"/api/radar/{ativo['id']}").status_code == 404


def test_watchlist_can_register_new_asset_without_position(cliente):
    resposta = cliente.post("/api/radar", json={"ticker": "mxrf11", "classe": "FII"})

    assert resposta.status_code == 201
    assert resposta.json()["ticker"] == "MXRF11"
    item = cliente.get("/api/radar").json()[0]
    assert item["classe"] == "FII"
    assert item["tem_posicao"] is False
    assert cliente.post("/api/radar", json={"ticker": "MXRF11", "classe": "FII"}).status_code == 409


def test_watchlist_rejects_non_b3_assets(cliente):
    ativo = cliente.post("/api/ativos", json={"ticker": "AAPL", "mercado": "NASDAQ"}).json()

    assert cliente.post(f"/api/radar/{ativo['id']}").status_code == 422


def test_radar_calculates_metrics_and_yoc_from_complete_history():
    engine = create_engine("sqlite://", poolclass=StaticPool)
    Base.metadata.create_all(engine)
    hoje = date(2026, 10, 31)
    with Session(engine) as sessao:
        investidor = Investidor(nome="Ana")
        ativo = Ativo(ticker="PETR4", classe="AÇÃO", mercado="BVMF", moeda="BRL")
        sessao.add_all([investidor, ativo])
        sessao.flush()
        sessao.add(AtivoRadar(ativo_id=ativo.id))
        sessao.add_all(
            [
                Cotacao(ativo_id=ativo.id, data=date(2025, 10, 31), preco=D("90"), fonte="B3"),
                Cotacao(ativo_id=ativo.id, data=date(2026, 9, 1), preco=D("100"), fonte="B3"),
                Cotacao(ativo_id=ativo.id, data=date(2026, 9, 10), preco=D("130"), fonte="B3"),
                Cotacao(ativo_id=ativo.id, data=date(2026, 10, 16), preco=D("110"), fonte="B3"),
                Cotacao(ativo_id=ativo.id, data=date(2026, 10, 23), preco=D("120"), fonte="B3"),
                Cotacao(ativo_id=ativo.id, data=date(2026, 10, 30), preco=D("118"), fonte="B3"),
                Cotacao(ativo_id=ativo.id, data=hoje, preco=D("125"), fonte="B3"),
            ]
        )
        sessao.add(
            Fundamento(
                ativo_id=ativo.id,
                data_ref=hoje,
                fonte="Fundamentus",
                preco_lucro=D("10"),
                preco_valor_patrimonial=D("2"),
                dividend_yield=D("5"),
            )
        )
        sessao.add(
            Operacao(
                investidor_id=investidor.id,
                ativo_id=ativo.id,
                data=date(2025, 10, 1),
                evento="C",
                quantidade=D("10"),
                preco=D("100"),
                moeda="BRL",
                cambio=D("1"),
            )
        )
        sessao.add(
            Provento(
                investidor_id=investidor.id,
                ativo_id=ativo.id,
                data_pagamento=date(2026, 5, 1),
                evento="DIVIDENDO",
                valor=D("30"),
                moeda="BRL",
                cambio=D("1"),
            )
        )
        sessao.add(
            Provento(
                investidor_id=investidor.id,
                ativo_id=ativo.id,
                data_pagamento=date(2026, 11, 1),
                evento="DIVIDENDO",
                valor=D("900"),
                moeda="BRL",
                cambio=D("1"),
            )
        )
        sessao.flush()

        linha = radar.listar(sessao, [investidor.id], hoje)[0]

        assert linha.tem_posicao is True
        assert linha.cotacao.preco == D("125")
        assert linha.variacao_1d_pct == D("125") / D("118") - 1
        assert linha.variacao_7d_pct == D("125") / D("120") - 1
        assert linha.variacao_14d_pct == D("125") / D("110") - 1
        assert linha.drawdown_60d_pct == D("125") / D("130") - 1
        assert linha.minimo_52s == D("90")
        assert linha.maximo_52s == D("130")
        assert linha.preco_teto_graham == (
            D("22.5") * D("125") ** 2 / (D("10") * D("2"))
        ).sqrt()
        assert linha.yoc_12m == D("30") / D("1000")
        assert cotahist._ativos_b3(sessao) == {"PETR4": ativo.id}
        assert cotacoes.ativos_monitorados(sessao) == [ativo]
    engine.dispose()


def test_radar_does_not_report_partial_52_week_range_as_complete():
    engine = create_engine("sqlite://", poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as sessao:
        ativo = Ativo(ticker="MXRF11", classe="FII", mercado="BVMF", moeda="BRL")
        sessao.add(ativo)
        sessao.flush()
        sessao.add(AtivoRadar(ativo_id=ativo.id))
        sessao.add_all(
            [
                Cotacao(ativo_id=ativo.id, data=date(2026, 10, 24), preco=D("10"), fonte="Yahoo"),
                Cotacao(ativo_id=ativo.id, data=date(2026, 10, 31), preco=D("11"), fonte="Yahoo"),
            ]
        )
        sessao.flush()

        linha = radar.listar(sessao, hoje=date(2026, 10, 31))[0]

        assert linha.minimo_52s is None
        assert linha.maximo_52s is None
        assert linha.preco_teto_graham is None
    engine.dispose()


def test_historical_b3_load_includes_one_year_for_watchlist_assets(monkeypatch):
    engine = create_engine("sqlite://", poolclass=StaticPool)
    Base.metadata.create_all(engine)
    monkeypatch.setattr(cotahist, "_carregar", lambda _sessao, nomes: list(nomes))
    ano_atual = date.today().year
    ano_anterior = (date.today() - timedelta(days=370)).year
    with Session(engine) as sessao:
        assert cotahist.carregar_historico(sessao) == [f"COTAHIST_A{ano_atual}"]

        ativo = Ativo(ticker="PETR4", classe="AÇÃO", mercado="BVMF")
        sessao.add(ativo)
        sessao.flush()
        sessao.add(AtivoRadar(ativo_id=ativo.id))
        sessao.flush()

        assert cotahist.carregar_historico(sessao) == [
            f"COTAHIST_A{ano_anterior}",
            f"COTAHIST_A{ano_atual}",
        ]
    engine.dispose()
