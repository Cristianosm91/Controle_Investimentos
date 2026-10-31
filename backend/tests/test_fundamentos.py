from datetime import date
from decimal import Decimal as D

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.fundamentos import listar_fundamentos
from app.db import Base
from app.models import Ativo, Fundamento
from app.providers import fundamentus
from app.services import fundamentos as servico


def _tabela(cabecalhos: list[str], valores: list[str]) -> str:
    th = "".join(f"<th>{valor}</th>" for valor in cabecalhos)
    td = "".join(f"<td>{valor}</td>" for valor in valores)
    return f'<table id="resultado"><thead><tr>{th}</tr></thead><tbody><tr>{td}</tr></tbody></table>'


def test_interpretar_acoes_preserva_decimais_e_percentuais():
    html = _tabela(
        ["Papel", "P/L", "P/VP", "Div.Yield", "ROE", "Liq.2meses", "Patrim. Líq"],
        ["PETR4", "5,09", "1,41", "6,9%", "27,7%", "2.559.440.000", "480.950.000.000"],
    )

    resultado = fundamentus.interpretar_acoes(html)

    assert resultado == {
        "PETR4": {
            "preco_lucro": D("5.09"),
            "preco_valor_patrimonial": D("1.41"),
            "dividend_yield": D("6.9"),
            "roe": D("27.7"),
            "liquidez_media_2m": D("2559440000"),
            "patrimonio_liquido": D("480950000000"),
        }
    }


def test_interpretar_fiis_extrai_indicadores_especificos():
    html = _tabela(
        ["Papel", "Segmento", "P/VP", "Div Yield", "DY qtd", "Div.Yield 2 anos", "DY 2a qtd", "FFO yield",
         "Patrim Líq", "Valor mercado", "Liquidez", "Área(m2)", "Preço/m2", "Nro de imóveis", "Nro de unidades"],
        ["MXRF11", "Híbrido", "0,95", "14,4%", "12", "0,00%", "0", "9,61%", "5.304.820.000",
         "5.036.790.000", "26.555.800", "474", "576.649", "2", "4"],
    )

    resultado = fundamentus.interpretar_fiis(html)["MXRF11"]

    assert resultado["preco_valor_patrimonial"] == D("0.95")
    assert resultado["dividend_yield"] == D("14.4")
    assert resultado["fii_dividendos_meses_12m"] == 12
    assert resultado["fii_ffo_yield"] == D("9.61")
    assert resultado["fii_area_m2"] == D("474")
    assert resultado["segmento_fii"] == "Híbrido"


def test_interpretar_fundamentus_rejeita_html_sem_tabela():
    with pytest.raises(fundamentus.ErroFundamentus, match="tabela"):
        fundamentus.interpretar_acoes("<html><body>indisponível</body></html>")


def test_investidor10_fica_indisponivel_ate_validar_rota_e_termos():
    fonte = next(f for f in fundamentus.FONTES if f.id == "investidor10")

    assert fonte.disponivel is False
    assert "HTTP 410" in fonte.motivo


def test_endpoint_fontes_informa_disponibilidade(cliente):
    resposta = cliente.get("/api/fundamentos/fontes")
    tarefas = cliente.get("/api/atualizacoes").json()

    assert resposta.status_code == 200
    fontes = {fonte["id"]: fonte for fonte in resposta.json()}
    assert fontes["fundamentus"]["disponivel"] is True
    assert fontes["investidor10"]["disponivel"] is False
    assert "fundamentos" in {tarefa["nome"] for tarefa in tarefas}


def test_atualizar_grava_snapshots_idempotentes_e_expoe_o_mais_recente(monkeypatch):
    engine = create_engine("sqlite://", poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as sessao:
        acao = Ativo(ticker="PETR4", classe="AÇÃO", mercado="BVMF")
        fii = Ativo(ticker="MXRF11", classe="FII", mercado="BVMF")
        sessao.add_all([acao, fii])
        sessao.flush()
        monkeypatch.setattr(
            fundamentus,
            "buscar_acoes",
            lambda _cliente: {"PETR4": {"preco_lucro": D("5.09"), "roe": D("27.7")}},
        )
        monkeypatch.setattr(
            fundamentus,
            "buscar_fiis",
            lambda _cliente: {"MXRF11": {"preco_valor_patrimonial": D("0.95"), "fii_ffo_yield": D("9.61")}},
        )

        resultado = servico.atualizar(sessao, cliente=object(), hoje=date(2026, 10, 31))
        repeticao = servico.atualizar(sessao, cliente=object(), hoje=date(2026, 10, 31))

        assert resultado.atualizados == repeticao.atualizados == 2
        assert sessao.scalar(select(func.count()).select_from(Fundamento)) == 2
        api_resultado = listar_fundamentos(sessao)
        por_ticker = {linha.ticker: linha for linha in api_resultado}
        assert por_ticker["PETR4"].preco_lucro == D("5.09")
        assert por_ticker["MXRF11"].fii_ffo_yield == D("9.61")
        assert por_ticker["PETR4"].model_dump(mode="json")["preco_lucro"] == 5.09

        servico.atualizar(sessao, cliente=object(), hoje=date(2026, 11, 1))
        assert sessao.scalar(select(func.count()).select_from(Fundamento)) == 4
    engine.dispose()


def test_atualizar_preserva_resultados_quando_uma_fonte_falha(monkeypatch):
    engine = create_engine("sqlite://", poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as sessao:
        sessao.add_all(
            [
                Ativo(ticker="PETR4", classe="AÇÃO", mercado="BVMF"),
                Ativo(ticker="MXRF11", classe="FII", mercado="BVMF"),
            ]
        )
        sessao.flush()

        def falhar_acoes(_cliente):
            raise fundamentus.ErroFundamentus("fonte indisponível")

        monkeypatch.setattr(fundamentus, "buscar_acoes", falhar_acoes)
        monkeypatch.setattr(
            fundamentus,
            "buscar_fiis",
            lambda _cliente: {"MXRF11": {"fii_ffo_yield": D("9.61")}},
        )

        resultado = servico.atualizar(sessao, cliente=object(), hoje=date(2026, 10, 31))

        assert resultado.atualizados == 1
        assert resultado.falhas == ["Ações: fonte indisponível"]
        assert sessao.scalar(select(func.count()).select_from(Fundamento)) == 1
    engine.dispose()
