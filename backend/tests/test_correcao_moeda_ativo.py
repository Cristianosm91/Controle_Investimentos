import sqlite3
from datetime import date
from decimal import Decimal as D

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from alembic import command
from app.config import settings
from app.db import get_session
from app.main import app
from app.providers import bcb
from app.services import backup, moeda_ativo


@pytest.fixture
def ambiente(tmp_path, monkeypatch):
    banco = tmp_path / "investhub.db"
    command.upgrade(backup._alembic(f"sqlite:///{banco.as_posix()}"), "head")
    monkeypatch.setattr(settings, "db_path", banco)
    monkeypatch.setattr(settings, "database_url", None)
    monkeypatch.setattr(settings, "backup_copia_dir", "", raising=False)
    engine = create_engine(f"sqlite:///{banco.as_posix()}", connect_args={"check_same_thread": False})
    Sessao = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def sessao():
        with Sessao() as s:
            yield s

    app.dependency_overrides[get_session] = sessao
    with TestClient(app) as cliente:
        yield cliente, banco
    app.dependency_overrides.clear()
    engine.dispose()


def popular(cliente):
    invs = [cliente.post("/api/investidores", json={"nome": n}).json()["id"] for n in ("Pessoa A", "Pessoa B")]
    ativo = cliente.post("/api/ativos", json={"ticker": "ERRADO", "moeda": "BRL"}).json()
    outro = cliente.post("/api/ativos", json={"ticker": "OUTRO", "moeda": "BRL"}).json()
    for inv in invs:
        for a in (ativo, outro):
            r = cliente.post("/api/operacoes", json={
                "investidor_id": inv, "ativo_id": a["id"], "data": "2025-01-04", "evento": "C",
                "quantidade": 10, "preco": 3, "taxas": 0.2, "irrf": 0.01,
            })
            assert r.status_code == 201, r.text
    r = cliente.post("/api/proventos", json={
        "investidor_id": invs[0], "ativo_id": ativo["id"], "data_pagamento": "2025-02-03",
        "evento": "DIVIDENDO", "valor": 2, "taxas": 0.1, "irrf": 0.2,
    })
    assert r.status_code == 201, r.text
    r = cliente.post("/api/caixa", json={
        "investidor_id": invs[0], "data": "2025-01-04", "evento": "APORTE", "valor": 30,
    })
    assert r.status_code == 201, r.text
    return ativo


@pytest.mark.parametrize("metodo", ["patch", "put"])
def test_correcao_explicitamente_confirmada_preserva_numeros_e_backup(ambiente, monkeypatch, metodo):
    cliente, banco = ambiente
    ativo = popular(cliente)
    chamadas = []

    def ptax(moeda, dia):
        chamadas.append((moeda, dia))
        # Sabado usa o boletim de sexta, pelo helper oficial.
        return bcb.Ptax(moeda, dia, D("4.9"), D("5") if dia.month == 1 else D("6"))

    monkeypatch.setattr(bcb, "ptax", ptax)
    corpo = {"moeda": "USD", "confirmar_correcao_moeda": True}
    url = f"/api/ativos/{ativo['id']}/classe"
    if metodo == "put":
        url = f"/api/ativos/{ativo['id']}"
        corpo = {**ativo, **corpo}
    r = getattr(cliente, metodo)(url, json=corpo)
    assert r.status_code == 200, r.text
    assert r.json()["moeda"] == "USD"
    assert chamadas == [("USD", date(2025, 1, 4)), ("USD", date(2025, 2, 3))]
    with sqlite3.connect(banco) as c:
        corrigidas = c.execute("SELECT preco,taxas,irrf,moeda,cambio FROM operacao WHERE ativo_id=?", (ativo["id"],)).fetchall()
        assert corrigidas == [(3, 0.2, 0.01, "USD", 5)] * 2
        assert c.execute("SELECT moeda,cambio FROM operacao WHERE ativo_id!=?", (ativo["id"],)).fetchall() == [("BRL", 1)] * 2
        assert c.execute("SELECT valor,taxas,irrf,moeda,cambio FROM provento").fetchall() == [(2, 0.1, 0.2, "USD", 6)]
        # Caixa nao tem ativo_id; nunca deve ser adivinhado/relabelado por ticker.
        assert c.execute("SELECT moeda,valor FROM mov_caixa").fetchall() == [("BRL", 30)]
    arquivos = list(banco.parent.glob("backups/*-manual.db"))
    assert len(arquivos) == 1
    with sqlite3.connect(arquivos[0]) as c:
        assert c.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert c.execute("SELECT moeda,cambio FROM operacao").fetchall() == [("BRL", 1)] * 4


def test_sem_confirmacao_nao_altera_cadastro_nem_lancamentos(ambiente):
    cliente, banco = ambiente
    ativo = popular(cliente)
    r = cliente.patch(f"/api/ativos/{ativo['id']}/classe", json={"moeda": "USD"})
    assert r.status_code == 409
    with sqlite3.connect(banco) as c:
        assert c.execute("SELECT moeda FROM ativo WHERE id=?", (ativo["id"],)).fetchone() == ("BRL",)
    assert list(banco.parent.glob("backups/*-manual.db")) == []


@pytest.mark.parametrize("falha", ["ptax", "backup"])
def test_falha_de_ptax_ou_backup_nao_altera_nada(ambiente, monkeypatch, falha):
    cliente, banco = ambiente
    ativo = popular(cliente)

    def ptax(moeda, dia):
        if falha == "ptax":
            raise bcb.ErroPtax("indisponivel")
        return bcb.Ptax(moeda, dia, D(5), D(5))

    monkeypatch.setattr(bcb, "ptax", ptax)
    if falha == "backup":
        def nao_salvar(*args, **kwargs):
            raise OSError("sem espaco")
        monkeypatch.setattr(moeda_ativo.backup, "gerar", nao_salvar)
    r = cliente.patch(f"/api/ativos/{ativo['id']}/classe", json={"moeda": "USD", "confirmar_correcao_moeda": True})
    assert r.status_code == (422 if falha == "ptax" else 409)
    with sqlite3.connect(banco) as c:
        assert c.execute("SELECT DISTINCT moeda,cambio FROM operacao").fetchall() == [("BRL", 1)]
        assert c.execute("SELECT moeda FROM ativo WHERE id=?", (ativo["id"],)).fetchone() == ("BRL",)


def test_correcao_para_brl_redefine_cambio_sem_chamada_externa(cliente):
    ativo = cliente.post("/api/ativos", json={"ticker": "SEMOPS", "moeda": "USD"}).json()
    r = cliente.patch(f"/api/ativos/{ativo['id']}/classe", json={"moeda": "BRL"})
    assert r.status_code == 200 and r.json()["moeda"] == "BRL"


def test_novo_lancamento_durante_ptax_exige_nova_confirmacao(ambiente, monkeypatch):
    cliente, banco = ambiente
    ativo = popular(cliente)
    inserido = False

    def ptax(moeda, dia):
        nonlocal inserido
        if not inserido:
            with sqlite3.connect(banco) as c:
                c.execute(
                    "INSERT INTO operacao (investidor_id,ativo_id,data,evento,quantidade,preco,taxas,irrf,"
                    "moeda,cambio,daytrade,origem) VALUES (1,?,'2025-03-03','C',1,3,0,0,'BRL',1,0,'manual')",
                    (ativo["id"],),
                )
            inserido = True
        return bcb.Ptax(moeda, dia, D(5), D(5))

    monkeypatch.setattr(bcb, "ptax", ptax)
    r = cliente.patch(f"/api/ativos/{ativo['id']}/classe", json={"moeda": "USD", "confirmar_correcao_moeda": True})
    assert r.status_code == 409 and "mudaram" in r.json()["detail"]
    with sqlite3.connect(banco) as c:
        assert c.execute("SELECT DISTINCT moeda,cambio FROM operacao").fetchall() == [("BRL", 1)]
    assert list(banco.parent.glob("backups/*-manual.db")) == []
