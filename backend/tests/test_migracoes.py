import sqlite3
from contextlib import closing

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
        con.execute(
            "INSERT INTO operacao (investidor_id, ativo_id, data, evento, quantidade, preco, taxas, irrf, moeda, "
            "cambio, daytrade, origem) VALUES (1, 1, '2024-01-02', 'C', 10, 30, 0, 0, 'BRL', 1, 0, 'manual')"
        )
        con.commit()

    command.upgrade(cfg, "head")

    with closing(sqlite3.connect(banco)) as con:
        assert con.execute("SELECT ticker, coingecko_id FROM ativo").fetchall() == [("PETR4", None)]
        assert con.execute("SELECT count(*) FROM operacao WHERE ativo_id = 1").fetchone()[0] == 1
        assert con.execute("PRAGMA foreign_key_check").fetchall() == []
        colunas_valor_historico = {linha[1] for linha in con.execute("PRAGMA table_info('valuation_historico')")}
        assert {"premissa_lpa", "premissa_ke", "premissa_fcfe_5"} <= colunas_valor_historico
        colunas_operacao = {linha[1] for linha in con.execute("PRAGMA table_info('operacao')")}
        assert "transferencia_pareada_id" in colunas_operacao
        indices = con.execute("PRAGMA index_list('ativo')").fetchall()
        assert any(i[2] == 1 for i in indices)
