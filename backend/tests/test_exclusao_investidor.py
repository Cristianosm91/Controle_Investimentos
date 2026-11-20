"""Exclusão completa de um investidor, sempre precedida de backup verificado (PRI-001)."""

import json
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from alembic import command
from app.api import cadastros
from app.config import settings
from app.db import Base, get_session
from app.main import app
from app.models import (
    Ativo,
    Corretora,
    DarfPago,
    Grupo,
    HistoricoLancamento,
    Investidor,
    LoteImportacao,
    Meta,
    MovCaixa,
    Operacao,
    PrejuizoInicial,
    Provento,
)
from app.services import backup


@pytest.fixture(scope="module")
def modelo(tmp_path_factory) -> Path:
    caminho = tmp_path_factory.mktemp("modelo") / "modelo.db"
    command.upgrade(backup._alembic(f"sqlite:///{caminho.as_posix()}"), "head")
    return caminho


@pytest.fixture
def banco(tmp_path, modelo, monkeypatch) -> Path:
    """Arquivo SQLite que o backup copia (a API usa outro banco, em memória)."""
    destino = tmp_path / "dados" / "investhub.db"
    destino.parent.mkdir()
    destino.write_bytes(modelo.read_bytes())
    monkeypatch.setattr(settings, "db_path", destino)
    monkeypatch.setattr(settings, "database_url", None)
    monkeypatch.setattr(settings, "backup_copia_dir", "", raising=False)
    return destino


@pytest.fixture
def ambiente(banco):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)

    @event.listens_for(engine, "connect")
    def _fk(conexao, _registro):
        conexao.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    Sessao = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def _sessao():
        with Sessao() as s:
            yield s

    app.dependency_overrides[get_session] = _sessao
    with TestClient(app) as c:
        yield c, Sessao
    app.dependency_overrides.clear()
    engine.dispose()


def _popular(Sessao) -> dict[str, int]:
    with Sessao() as s:
        grupo = Grupo(nome="Família")
        ana = Investidor(nome="Ana", grupo=grupo)
        bia = Investidor(nome="Bia", grupo=grupo)
        ativo = Ativo(ticker="PETR4")
        corretora = Corretora(nome="XP")
        s.add_all([grupo, ana, bia, ativo, corretora])
        s.flush()
        lote = LoteImportacao(tipo="nota", arquivo="nota-ana.pdf", investidor_id=ana.id)
        lote_misto = LoteImportacao(tipo="planilha", arquivo="familia.xlsx", investidor_id=ana.id)
        s.add_all([lote, lote_misto])
        s.flush()
        hoje = date(2024, 1, 2)
        saida = Operacao(investidor_id=ana.id, ativo_id=ativo.id, data=hoje, evento="TRANSF", quantidade=Decimal(-1))
        compra = Operacao(
            investidor_id=ana.id, ativo_id=ativo.id, corretora_id=corretora.id, data=hoje, evento="C",
            quantidade=Decimal(10), lote_id=lote.id,
        )
        s.add_all([saida, compra])
        s.flush()
        entrada = Operacao(
            investidor_id=bia.id, ativo_id=ativo.id, data=hoje, evento="TRANSF", quantidade=Decimal(1),
            transferencia_pareada_id=saida.id, lote_id=lote_misto.id,
        )
        s.add(entrada)
        s.flush()
        saida.transferencia_pareada_id = entrada.id
        s.add_all([
            Provento(investidor_id=ana.id, ativo_id=ativo.id, data_pagamento=hoje, evento="DIV", valor=Decimal(5)),
            MovCaixa(investidor_id=ana.id, data=hoje, evento="APORTE", valor=Decimal(100), lote_id=lote_misto.id),
            MovCaixa(investidor_id=ana.id, data=hoje, evento="APORTE", valor=Decimal(50)),
            DarfPago(investidor_id=ana.id, competencia=hoje, data_pagamento=hoje, valor=Decimal(10)),
            PrejuizoInicial(investidor_id=ana.id, grupo="COMUM", valor=Decimal(3)),
            Meta(nome="Só Ana", tipo="PATRIMONIO", valor_alvo=Decimal(1), data_alvo=hoje, rentabilidade_aa=Decimal(0),
                 investidores=str(ana.id)),
            Meta(nome="Família", tipo="PATRIMONIO", valor_alvo=Decimal(1), data_alvo=hoje, rentabilidade_aa=Decimal(0),
                 investidores=f"{ana.id},{bia.id}"),
            Meta(nome="Todos", tipo="PATRIMONIO", valor_alvo=Decimal(1), data_alvo=hoje, rentabilidade_aa=Decimal(0)),
        ])
        s.commit()
        return {"ana": ana.id, "bia": bia.id, "entrada": entrada.id, "lote_misto": lote_misto.id}


ESPERADO = {
    "Operações": 2,
    "Proventos": 1,
    "Movimentações de caixa": 2,
    "DARFs pagos": 1,
    "Prejuízos a compensar": 1,
    "Metas só deste investidor": 1,
    "Lotes de importação": 1,
}


def _contar(Sessao, modelo) -> int:
    with Sessao() as s:
        return s.scalar(select(func.count()).select_from(modelo))


def test_resumo_da_exclusao(ambiente):
    cliente, Sessao = ambiente
    ids = _popular(Sessao)
    r = cliente.get(f"/api/investidores/{ids['ana']}/exclusao")
    assert r.status_code == 200, r.text
    assert r.json() == {"investidor": {"id": ids["ana"], "nome": "Ana"}, "contagens": ESPERADO, "backup_disponivel": True}
    assert cliente.get("/api/investidores/999/exclusao").status_code == 404


def test_exclusao_completa_gera_backup_e_remove_tudo_do_investidor(ambiente, banco):
    cliente, Sessao = ambiente
    ids = _popular(Sessao)

    r = cliente.delete(f"/api/investidores/{ids['ana']}/completo")

    assert r.status_code == 200, r.text
    corpo = r.json()
    assert corpo["removidos"] == ESPERADO
    assert corpo["backup"].endswith("-antes-exclusao-investidor-manual.db")
    backup.validar(backup.caminho(banco, corpo["backup"]))
    with Sessao() as s:
        assert [i.nome for i in s.scalars(select(Investidor))] == ["Bia"]
        assert s.scalar(select(Operacao.transferencia_pareada_id).where(Operacao.id == ids["entrada"])) is None
        assert s.scalar(select(Operacao.lote_id).where(Operacao.id == ids["entrada"])) == ids["lote_misto"]
        lote_misto = s.get(LoteImportacao, ids["lote_misto"])
        assert lote_misto is not None and lote_misto.investidor_id is None
        assert sorted((m.nome, m.investidores) for m in s.scalars(select(Meta))) == [
            ("Família", str(ids["bia"])), ("Todos", None)
        ]
        historico = s.scalars(select(HistoricoLancamento)).all()
        assert sum(item.acao == "excluido" for item in historico) == 5
        alterado = next(item for item in historico if item.acao == "alterado")
        assert alterado.investidor_id == ids["bia"]
        assert json.loads(alterado.anterior_json)["transferencia_pareada_id"] is not None
        assert json.loads(alterado.novo_json)["transferencia_pareada_id"] is None
    for modelo in (Provento, MovCaixa, DarfPago, PrejuizoInicial):
        assert _contar(Sessao, modelo) == 0
    assert _contar(Sessao, Operacao) == 1
    for compartilhado in (Ativo, Corretora, Grupo):
        assert _contar(Sessao, compartilhado) == 1


def test_falha_no_backup_nao_exclui_nada(ambiente, monkeypatch):
    cliente, Sessao = ambiente
    ids = _popular(Sessao)

    def falhar(*_args, **_kwargs):
        raise backup.BackupInvalido("Backup corrompido: teste")

    monkeypatch.setattr(backup, "gerar", falhar)
    r = cliente.delete(f"/api/investidores/{ids['ana']}/completo")
    assert r.status_code == 409
    assert "backup" in r.json()["detail"].lower()
    assert _contar(Sessao, Investidor) == 2 and _contar(Sessao, Operacao) == 3


def test_sem_backup_disponivel_postgresql_nao_exclui(ambiente, monkeypatch):
    cliente, Sessao = ambiente
    ids = _popular(Sessao)
    monkeypatch.setattr(settings, "database_url", "postgresql://u:p@localhost/db")
    assert cliente.get(f"/api/investidores/{ids['ana']}/exclusao").json()["backup_disponivel"] is False
    r = cliente.delete(f"/api/investidores/{ids['ana']}/completo")
    assert r.status_code == 409
    assert _contar(Sessao, Investidor) == 2


def test_falha_no_meio_desfaz_toda_a_exclusao(ambiente, monkeypatch):
    cliente, Sessao = ambiente
    ids = _popular(Sessao)

    def falhar(*_args, **_kwargs):
        raise RuntimeError("falha simulada")

    monkeypatch.setattr(cadastros, "_ajustar_metas", falhar)
    r = cliente.delete(f"/api/investidores/{ids['ana']}/completo")
    assert r.status_code == 500
    assert "nada foi excluído" in r.json()["detail"]
    assert _contar(Sessao, Investidor) == 2
    assert _contar(Sessao, Operacao) == 3 and _contar(Sessao, Provento) == 1 and _contar(Sessao, Meta) == 3


def test_exclusao_simples_continua_bloqueada_com_lancamentos(ambiente):
    cliente, Sessao = ambiente
    ids = _popular(Sessao)
    assert cliente.delete(f"/api/investidores/{ids['ana']}").status_code == 409
    assert _contar(Sessao, Investidor) == 2
