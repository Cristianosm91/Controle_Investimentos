"""PP-007 (INT-001/OBS-002) e OBS-005: status do job distingue ok/parcial/falha sem expor detalhe técnico."""

import httpx
import pandas as pd
import pytest
from sqlalchemy.exc import IntegrityError

from app.providers import bcb
from app.providers.base import AtivoRef
from app.providers.yahoo import ProvedorYahoo
from app.services import cotacoes, jobs
from app.services.cripto import AtualizacaoCripto
from app.services.fundamentos import ResultadoFundamentos
from app.services.historico import ResultadoHistorico

AAPL = AtivoRef("AAPL", "NASDAQ", "USD")
MSFT = AtivoRef("MSFT", "NASDAQ", "USD")


def _df(simbolos: list[str]) -> pd.DataFrame:
    indice = pd.to_datetime(["2026-11-12", "2026-11-13"])
    colunas = pd.MultiIndex.from_product([simbolos, ["Close"]])
    return pd.DataFrame([[10.0] * len(simbolos), [11.0] * len(simbolos)], index=indice, columns=colunas)


def test_yahoo_registra_falha_quando_download_levanta(monkeypatch):
    def falhar(*_a, **_k):
        raise RuntimeError("boom")

    monkeypatch.setattr("app.providers.yahoo.yf.download", falhar)
    provedor = ProvedorYahoo()
    assert provedor.cotacoes([AAPL]) == {}
    assert provedor.falhas


def test_yahoo_registra_falha_quando_resposta_vazia(monkeypatch):
    monkeypatch.setattr("app.providers.yahoo.yf.download", lambda *_a, **_k: pd.DataFrame())
    provedor = ProvedorYahoo()
    assert provedor.cotacoes([AAPL, MSFT]) == {}
    assert provedor.falhas


def test_yahoo_ticker_sem_dado_nao_e_falha_de_fonte(monkeypatch):
    monkeypatch.setattr("app.providers.yahoo.yf.download", lambda *_a, **_k: _df(["AAPL"]))
    provedor = ProvedorYahoo()
    assert set(provedor.cotacoes([AAPL, MSFT])) == {"AAPL"}
    assert provedor.falhas == []


def test_bcb_registra_falha_de_ptax(monkeypatch):
    def falhar(*_a, **_k):
        raise bcb.ErroPtax("Falha ao consultar PTAX USD no BCB: https://olinda.bcb.gov.br/x?y=1")

    monkeypatch.setattr(bcb, "_consultar", falhar)
    provedor = bcb.ProvedorBcb()
    assert provedor.cambios(["USD"]) == {}
    assert provedor.falhas == ["BCB PTAX (USD)"]


class ProvedorForaDoAr:
    nome = "Fora"

    def __init__(self):
        self.falhas: list[str] = []

    def cotacoes(self, ativos):
        self.falhas.append("Fora indisponível")
        return {}

    def cambios(self, moedas):
        return {}


class ProvedorSemCobertura:
    nome = "Sem"

    def cotacoes(self, ativos):
        return {}

    def cambios(self, moedas):
        return {}


class _Ativo:
    def __init__(self, ticker):
        self.id, self.ticker, self.mercado, self.moeda, self.classe = 1, ticker, "NASDAQ", "BRL", "STOCK"


class _SessaoFalsa:
    def commit(self):
        pass


def test_cotacoes_propaga_falha_de_fonte_e_distingue_de_sem_cotacao():
    falha = cotacoes.atualizar_cotacoes(_SessaoFalsa(), [ProvedorForaDoAr()], [_Ativo("AAPL")])
    assert falha.falhas_fonte == ["Fora indisponível"]
    assert "Fora indisponível" in jobs._resumo_cotacoes(falha)
    sem_dado = cotacoes.atualizar_cotacoes(_SessaoFalsa(), [ProvedorSemCobertura()], [_Ativo("AAPL")])
    assert sem_dado.falhas_fonte == []
    assert sem_dado.sem_cotacao == ["AAPL"]


@pytest.fixture
def tarefa(monkeypatch):
    def configurar(nome, funcao):
        monkeypatch.setattr(jobs.TAREFAS[nome], "funcao", funcao)
        return jobs.TAREFAS[nome]

    yield configurar
    for t in jobs.TAREFAS.values():
        t.status = t.sucesso = t.mensagem = None


@pytest.mark.parametrize(
    ("nome", "resultado", "esperado"),
    [
        ("cotacoes", cotacoes.ResultadoAtualizacao(atualizados={"PETR4": "Yahoo"}), "ok"),
        ("cotacoes", cotacoes.ResultadoAtualizacao(sem_cotacao=["XPTO3"]), "ok"),
        ("cotacoes", cotacoes.ResultadoAtualizacao(falhas_fonte=["Yahoo Finance indisponível"]), "parcial"),
        ("indices_diario", ResultadoHistorico(gravados={"meses": 2}), "ok"),
        ("indices_diario", ResultadoHistorico(falhas=["cdi"]), "parcial"),
        ("fundamentos", ResultadoFundamentos(), "ok"),
        ("fundamentos", ResultadoFundamentos(falhas=["Ações: fora do ar"]), "parcial"),
        ("cripto", AtualizacaoCripto(atualizados=["BTC"]), "ok"),
        ("cripto", AtualizacaoCripto(avisos=["Fonte cripto indisponível (HTTP 503)"]), "parcial"),
        (
            "cripto",
            AtualizacaoCripto(
                avisos=["BTC: snapshot recebido é anterior ao cache local"],
                informativos=["BTC: snapshot recebido é anterior ao cache local"],
            ),
            "ok",
        ),
    ],
)
def test_status_do_job(tarefa, nome, resultado, esperado):
    t = tarefa(nome, lambda _s: resultado)
    jobs.executar(nome)
    assert (t.sucesso, t.status) == (True, esperado)


def test_status_falha_quando_job_levanta_sem_expor_sql(tarefa, caplog):
    erro = IntegrityError("INSERT INTO cotacao_moeda (moeda, valor) VALUES (?, ?)", ("USD", 5.1), Exception("UNIQUE"))

    def falhar(_s):
        raise erro

    t = tarefa("cotacoes", falhar)
    with pytest.raises(IntegrityError):
        jobs.executar("cotacoes")
    assert (t.sucesso, t.status) == (False, "falha")
    assert "INSERT" not in t.mensagem and "SQL" not in t.mensagem and "5.1" not in t.mensagem
    assert "INSERT INTO cotacao_moeda" in caplog.text  # detalhe técnico fica no log


def test_status_falha_de_rede_sem_expor_url(tarefa):
    def falhar(_s):
        raise httpx.ConnectError("falhou https://api.exemplo.com/v1?token=abc")

    t = tarefa("cripto", falhar)
    with pytest.raises(httpx.ConnectError):
        jobs.executar("cripto")
    assert t.status == "falha"
    assert "http" not in t.mensagem and "token" not in t.mensagem


def test_mensagem_de_resumo_sem_url(tarefa):
    r = ResultadoFundamentos(falhas=["Ações: Falha ao consultar https://www.fundamentus.com.br/x.php?a=1: 503"])
    t = tarefa("fundamentos", lambda _s: r)
    jobs.executar("fundamentos")
    assert "http" not in t.mensagem and "fundamentus.com.br" not in t.mensagem
    assert t.status == "parcial"


def test_api_expoe_status_mantendo_campos(cliente, tarefa):
    tarefa("indices_diario", lambda _s: ResultadoHistorico(falhas=["ipca"]))
    jobs.executar("indices_diario")
    linhas = {t["nome"]: t for t in cliente.get("/api/atualizacoes").json()}
    item = linhas["indices_diario"]
    assert item["status"] == "parcial"
    assert item["sucesso"] is True and "ipca" in item["mensagem"]
    assert linhas["backup"]["status"] is None
