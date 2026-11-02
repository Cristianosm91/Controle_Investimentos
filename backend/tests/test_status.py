from datetime import date
from decimal import Decimal as D

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.models import (
    Ativo,
    AtivoBook,
    Book,
    Cotacao,
    Estrategia,
    Investidor,
    Operacao,
    Provento,
)
from app.services import status


def test_status_asset_summarizes_results_and_paginates_timeline():
    engine = create_engine("sqlite://", poolclass=StaticPool)
    Base.metadata.create_all(engine)
    hoje = date(2026, 10, 31)
    with Session(engine) as sessao:
        investidor = Investidor(nome="Ana")
        outro = Investidor(nome="Bia")
        ativo = Ativo(ticker="PETR4", classe="AÇÃO", mercado="BVMF", moeda="BRL")
        sessao.add_all([investidor, outro, ativo])
        sessao.flush()
        sessao.add(Cotacao(ativo_id=ativo.id, data=hoje, preco=D("120"), fonte="B3"))
        sessao.add_all(
            [
                Operacao(
                    investidor_id=investidor.id, ativo_id=ativo.id, data=date(2024, 1, 1), evento="C",
                    quantidade=D("10"), preco=D("100"), taxas=D("10"), moeda="BRL", cambio=D("1"),
                ),
                Operacao(
                    investidor_id=investidor.id, ativo_id=ativo.id, data=date(2024, 2, 1), evento="V",
                    quantidade=D("-2"), preco=D("110"), taxas=D("2"), moeda="BRL", cambio=D("1"),
                ),
                Operacao(
                    investidor_id=investidor.id, ativo_id=ativo.id, data=date(2024, 3, 1), evento="C",
                    quantidade=D("1"), preco=D("10"), moeda="BRL", cambio=D("1"), daytrade=True,
                ),
                Operacao(
                    investidor_id=investidor.id, ativo_id=ativo.id, data=date(2024, 3, 1), evento="V",
                    quantidade=D("-1"), preco=D("12"), moeda="BRL", cambio=D("1"), daytrade=True,
                ),
                Provento(
                    investidor_id=investidor.id, ativo_id=ativo.id, data_pagamento=date(2026, 5, 1),
                    evento="DIVIDENDO", valor=D("60"), irrf=D("10"), taxas=D("5"), moeda="BRL", cambio=D("1"),
                ),
                Provento(
                    investidor_id=investidor.id, ativo_id=ativo.id, data_pagamento=date(2026, 11, 1),
                    evento="DIVIDENDO", valor=D("900"), moeda="BRL", cambio=D("1"),
                ),
                Operacao(
                    investidor_id=outro.id, ativo_id=ativo.id, data=date(2024, 1, 1), evento="C",
                    quantidade=D("2"), preco=D("50"), moeda="BRL", cambio=D("1"),
                ),
            ]
        )
        sessao.flush()

        resultado = status.consultar(sessao, "ativo", ativo.id, [investidor.id], limite=2, deslocamento=1, hoje=hoje)

        assert resultado["nome"] == "PETR4"
        assert resultado["ativos"] == 1
        assert resultado["investido"] == D("808")
        assert resultado["mercado"] == D("960")
        assert resultado["lucro_aberto"] == D("152")
        assert resultado["lucro_swing"] == D("16")
        assert resultado["lucro_daytrade"] == D("2")
        assert resultado["proventos_total"] == D("45")
        assert resultado["proventos_12m"] == D("45")
        assert resultado["yoc_12m"] == D("45") / D("808")
        assert resultado["lucro_total"] == D("215")
        assert resultado["total_eventos"] == 6
        assert [evento["data"] for evento in resultado["eventos"]] == [
            date(2024, 2, 1),
            date(2024, 3, 1),
        ]
        assert resultado["eventos"][0]["valor_brl"] == D("218")
        assert resultado["eventos"][0]["investidor_id"] == investidor.id
    engine.dispose()


def test_status_book_uses_configured_asset_allocation():
    engine = create_engine("sqlite://", poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as sessao:
        investidor = Investidor(nome="Ana")
        ativo = Ativo(ticker="PETR4", classe="AÇÃO", mercado="BVMF", moeda="BRL")
        estrategia = Estrategia(nome="RV")
        sessao.add_all([investidor, ativo, estrategia])
        sessao.flush()
        book_a = Book(estrategia_id=estrategia.id, nome="Book A", peso=D("0.5"))
        book_b = Book(estrategia_id=estrategia.id, nome="Book B", peso=D("0.5"))
        sessao.add_all([book_a, book_b])
        sessao.flush()
        sessao.add_all(
            [
                AtivoBook(ativo_id=ativo.id, book_id=book_a.id, percentual=D("0.25")),
                AtivoBook(ativo_id=ativo.id, book_id=book_b.id, percentual=D("0.75")),
                Operacao(
                    investidor_id=investidor.id, ativo_id=ativo.id, data=date(2026, 1, 1), evento="C",
                    quantidade=D("10"), preco=D("100"), moeda="BRL", cambio=D("1"),
                ),
                Cotacao(ativo_id=ativo.id, data=date(2026, 10, 31), preco=D("120"), fonte="B3"),
                Provento(
                    investidor_id=investidor.id, ativo_id=ativo.id, data_pagamento=date(2026, 5, 1),
                    evento="DIVIDENDO", valor=D("45"), moeda="BRL", cambio=D("1"),
                ),
            ]
        )
        sessao.flush()

        resultado = status.consultar(sessao, "book", book_a.id, None, limite=50, deslocamento=0)

        assert resultado["investido"] == D("250")
        assert resultado["mercado"] == D("300")
        assert resultado["lucro_aberto"] == D("50")
        assert resultado["proventos_total"] == D("11.25")
        assert resultado["eventos"][0]["participacao"] == D("0.25")
        assert resultado["eventos"][0]["valor_brl"] == D("-250")
    engine.dispose()


def test_status_open_result_excludes_bonus_from_invested_capital():
    engine = create_engine("sqlite://", poolclass=StaticPool)
    Base.metadata.create_all(engine)
    hoje = date(2026, 10, 31)
    with Session(engine) as sessao:
        investidor = Investidor(nome="Ana")
        ativo = Ativo(ticker="PETR4", classe="AÇÃO", mercado="BVMF", moeda="BRL")
        sessao.add_all([investidor, ativo])
        sessao.flush()
        sessao.add_all(
            [
                Operacao(
                    investidor_id=investidor.id, ativo_id=ativo.id, data=date(2026, 1, 1), evento="C",
                    quantidade=D("10"), preco=D("100"), moeda="BRL", cambio=D("1"),
                ),
                Operacao(
                    investidor_id=investidor.id, ativo_id=ativo.id, data=date(2026, 2, 1), evento="BONIFICACAO",
                    quantidade=D("1"), preco=D("100"), moeda="BRL", cambio=D("1"),
                ),
                Cotacao(ativo_id=ativo.id, data=hoje, preco=D("120"), fonte="B3"),
            ]
        )
        sessao.flush()

        resultado = status.consultar(sessao, "ativo", ativo.id, [investidor.id], limite=10, deslocamento=0, hoje=hoje)

        assert resultado["investido"] == D("1000")
        assert resultado["mercado"] == D("1320")
        assert resultado["lucro_aberto"] == D("320")
        assert resultado["lucro_total"] == D("320")
    engine.dispose()


def test_status_returns_zeroes_for_empty_portfolio(cliente):
    carteira = cliente.post("/api/carteiras", json={"nome": "Vazia", "ativos": []})
    assert carteira.status_code == 201

    resposta = cliente.get(f"/api/status?escopo=carteira&id={carteira.json()['id']}")

    assert resposta.status_code == 200
    assert resposta.json()["ativos"] == 0
    assert resposta.json()["investido"] == 0
    assert resposta.json()["mercado"] == 0
    assert resposta.json()["eventos"] == []


def test_status_rejects_missing_scope_records(cliente):
    assert cliente.get("/api/status?escopo=ativo&id=987").status_code == 404
    assert cliente.get("/api/status?escopo=invalid&id=1").status_code == 422
