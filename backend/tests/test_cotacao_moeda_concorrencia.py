"""INT-002: gravação de CotacaoMoeda idempotente quando outro job grava a mesma (moeda, data) ao mesmo tempo."""

from datetime import UTC, date, datetime
from decimal import Decimal as D

import pytest
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import Session

from app.db import Base
from app.models import Ativo, CotacaoMoeda
from app.providers import cripto as fonte_cripto
from app.providers.base import CotacaoAtual
from app.providers.bcb import ProvedorBcb
from app.services import cotacoes, cripto

DIA = date(2026, 11, 13)


@pytest.fixture
def engine(tmp_path):
    engine = create_engine(f"sqlite:///{(tmp_path / 'concorrencia.db').as_posix()}")
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


def simular_job_concorrente(engine, valor: str) -> list[bool]:
    """Antes do 1º INSERT em cotacao_moeda desta sessão, outra conexão grava e confirma a mesma chave."""
    disparado: list[bool] = []

    @event.listens_for(engine, "before_cursor_execute")
    def _antes(conexao, _cursor, sql, *_args):
        if disparado or not sql.lstrip().upper().startswith("INSERT INTO COTACAO_MOEDA"):
            return
        disparado.append(True)
        with Session(engine) as outra:
            outra.add(CotacaoMoeda(moeda="USD", data=DIA, valor=D(valor), fonte="BCB PTAX"))
            outra.commit()

    return disparado


class ProvedorCambio:
    nome = "Fake"

    def cotacoes(self, ativos):
        return {}

    def cambios(self, moedas):
        return {m: CotacaoAtual(m, D("5.10"), None, DIA, "BCB PTAX") for m in moedas}


def test_cotacoes_grava_cambio_sem_integrity_error_com_job_concorrente(engine):
    disparado = simular_job_concorrente(engine, "5.00")
    ativo = Ativo(ticker="AAPL", classe="STOCK", moeda="USD", mercado="NASDAQ")
    with Session(engine) as sessao:
        resultado = cotacoes.atualizar_cotacoes(sessao, [ProvedorCambio()], [ativo])
    assert disparado
    assert resultado.atualizados == {"USD": "BCB PTAX"}
    with Session(engine) as sessao:
        linhas = sessao.scalars(select(CotacaoMoeda)).all()
    assert [(l.moeda, l.data, l.valor) for l in linhas] == [("USD", DIA, D("5.10"))]


def test_cripto_grava_cambio_sem_integrity_error_com_job_concorrente(engine, monkeypatch):
    with Session(engine) as sessao:
        sessao.add(Ativo(ticker="BTC", classe="CRIPTO", moeda="USD", mercado=None, coingecko_id="bitcoin"))
        sessao.commit()
    mercado = fonte_cripto.Mercado(
        id="bitcoin", symbol="btc", name="Bitcoin", current_price=D("100"),
        last_updated=datetime.now(UTC), fonte="CoinGecko",
    )
    monkeypatch.setattr(fonte_cripto, "mercados", lambda ids: ({"bitcoin": mercado}, []))
    monkeypatch.setattr(ProvedorBcb, "cambios", lambda self, moedas: {
        m: CotacaoAtual(m, D("5.10"), None, DIA, "BCB PTAX") for m in moedas
    })
    disparado = simular_job_concorrente(engine, "5.00")
    with Session(engine) as sessao:
        resultado = cripto.atualizar(sessao)
    assert disparado
    assert resultado.atualizados == ["BTC"]
    with Session(engine) as sessao:
        assert sessao.scalar(select(func.count()).select_from(CotacaoMoeda)) == 1
        assert sessao.scalar(select(CotacaoMoeda.valor)) == D("5.10")


def test_cotacoes_atualiza_linha_existente_como_antes(engine):
    with Session(engine) as sessao:
        sessao.add(CotacaoMoeda(moeda="USD", data=DIA, valor=D("4.90"), fonte="Yahoo"))
        sessao.commit()
    ativo = Ativo(ticker="AAPL", classe="STOCK", moeda="USD", mercado="NASDAQ")
    with Session(engine) as sessao:
        cotacoes.atualizar_cotacoes(sessao, [ProvedorCambio()], [ativo])
    with Session(engine) as sessao:
        linha = sessao.scalars(select(CotacaoMoeda)).one()
    assert (linha.valor, linha.fonte) == (D("5.10"), "BCB PTAX")
