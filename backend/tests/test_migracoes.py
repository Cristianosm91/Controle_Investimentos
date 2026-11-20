import sqlite3
from contextlib import closing

import pytest
from alembic.config import Config

from alembic import command
from app.config import RAIZ_PROJETO


def _alembic(url: str) -> Config:
    cfg = Config()
    cfg.set_main_option("script_location", str(RAIZ_PROJETO / "backend" / "alembic"))
    cfg.attributes["url"] = url
    return cfg


def test_upgrade_preserva_dados_referenciados(tmp_path):
    """Migrações que recriam tabelas no SQLite (batch) não podem falhar por chave estrangeira."""
    banco = tmp_path / "antigo.db"
    cfg = _alembic(f"sqlite:///{banco.as_posix()}")
    command.upgrade(cfg, "d2745cfb6a91")
    with closing(sqlite3.connect(banco)) as con:
        con.execute("INSERT INTO investidor (id, nome, cor, ativo) VALUES (1, 'Ana', '#000000', 1)")
        con.execute("INSERT INTO ativo (id, ticker, classe, moeda, cotacao_automatica) VALUES (1, 'PETR4', 'AÇÃO', 'BRL', 1)")
        con.execute("INSERT INTO ativo (id, ticker, classe, moeda, cotacao_automatica) VALUES (2, 'INTR', 'STOCK', 'BRL', 1)")
        con.execute(
            "INSERT INTO operacao (investidor_id, ativo_id, data, evento, quantidade, preco, taxas, irrf, moeda, "
            "cambio, daytrade, origem) VALUES (1, 1, '2024-01-02', 'C', 10, 30, 0, 0, 'BRL', 1, 0, 'manual')"
        )
        con.commit()

    command.upgrade(cfg, "head")

    with closing(sqlite3.connect(banco)) as con:
        assert con.execute("SELECT ticker, coingecko_id FROM ativo WHERE ticker = 'PETR4'").fetchall() == [("PETR4", None)]
        assert con.execute("SELECT moeda FROM ativo WHERE ticker = 'INTR'").fetchone() == ("USD",)
        assert con.execute("SELECT count(*) FROM operacao WHERE ativo_id = 1").fetchone()[0] == 1
        assert con.execute("PRAGMA foreign_key_check").fetchall() == []
        colunas_valor_historico = {linha[1] for linha in con.execute("PRAGMA table_info('valuation_historico')")}
        assert {"premissa_lpa", "premissa_ke", "premissa_fcfe_5"} <= colunas_valor_historico
        colunas_operacao = {linha[1] for linha in con.execute("PRAGMA table_info('operacao')")}
        assert "transferencia_pareada_id" in colunas_operacao
        indices = con.execute("PRAGMA index_list('ativo')").fetchall()
        assert any(i[2] == 1 for i in indices)


def test_migracao_apelidos_preserva_corretoras_e_impede_downgrade_com_perda(tmp_path):
    banco = tmp_path / "corretoras.db"
    cfg = _alembic(f"sqlite:///{banco.as_posix()}")
    command.upgrade(cfg, "c0d3a8b7f1e2")
    with closing(sqlite3.connect(banco)) as con:
        con.execute("INSERT INTO corretora (id, nome, cnpj) VALUES (1, 'XP', NULL)")
        con.commit()
    command.upgrade(cfg, "head")
    with closing(sqlite3.connect(banco)) as con:
        assert con.execute("SELECT id, nome FROM corretora").fetchall() == [(1, "XP")]
        con.execute("INSERT INTO corretora_apelido (nome, corretora_id) VALUES ('XP antigo', 1)")
        con.commit()
        assert con.execute("PRAGMA foreign_key_check").fetchall() == []
    with pytest.raises(RuntimeError, match="Downgrade indisponível"):
        command.downgrade(cfg, "c0d3a8b7f1e2")


def test_migracao_cripto_aditiva_preserva_legado_e_bloqueia_perda(tmp_path):
    banco = tmp_path / "cripto.db"
    cfg = _alembic(f"sqlite:///{banco.as_posix()}")
    command.upgrade(cfg, "c0d3a8b7f1e2")
    with closing(sqlite3.connect(banco)) as con:
        con.execute("INSERT INTO investidor (id, nome, cor, ativo) VALUES (1, 'Teste', '#000000', 1)")
        con.execute(
            "INSERT INTO ativo (id, ticker, classe, moeda, cotacao_automatica) "
            "VALUES (1, 'BTC', 'CRIPTO', 'USD', 1)"
        )
        con.execute(
            "INSERT INTO operacao (id, investidor_id, ativo_id, data, evento, quantidade, preco, taxas, irrf, "
            "moeda, cambio, daytrade, origem) "
            "VALUES (1, 1, 1, '2026-01-02', 'C', 0.01, 50000, 0, 0, 'USD', 5, 0, 'manual')"
        )
        con.commit()

    command.upgrade(cfg, "head")
    with closing(sqlite3.connect(banco)) as con:
        legado = con.execute(
            "SELECT moeda, preco, cambio, cripto_valor_original FROM operacao WHERE id = 1"
        ).fetchone()
        assert legado == ("USD", 50000, 5, None)

    command.downgrade(cfg, "d7e4b2a9c610")
    with closing(sqlite3.connect(banco)) as con:
        assert "cripto_valor_original" not in {
            linha[1] for linha in con.execute("PRAGMA table_info('operacao')")
        }
    command.upgrade(cfg, "head")
    with closing(sqlite3.connect(banco)) as con:
        con.execute("UPDATE operacao SET cripto_valor_original = 500 WHERE id = 1")
        con.commit()

    with pytest.raises(RuntimeError, match="Downgrade indisponível"):
        command.downgrade(cfg, "c0d3a8b7f1e2")
    with closing(sqlite3.connect(banco)) as con:
        assert "cripto_valor_original" in {
            linha[1] for linha in con.execute("PRAGMA table_info('operacao')")
        }
        assert con.execute("SELECT cripto_valor_original FROM operacao WHERE id = 1").fetchone() == (500,)
