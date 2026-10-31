import sqlite3

from app import config


def test_migra_banco_legado_para_caminho_novo(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    legado = tmp_path / "ControleInv" / "controleinv.db"
    legado.parent.mkdir()
    with sqlite3.connect(legado) as con:
        con.execute("CREATE TABLE t (v INTEGER)")
        con.execute("INSERT INTO t VALUES (42)")
    con.close()

    destino = config.db_padrao()
    config.migrar_banco_legado(destino)

    assert destino == tmp_path / "InvestHub" / "investhub.db"
    con = sqlite3.connect(destino)
    assert con.execute("SELECT v FROM t").fetchone() == (42,)
    con.close()
    assert legado.is_file()


def test_nao_sobrescreve_banco_novo_existente(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    (tmp_path / "ControleInv").mkdir()
    sqlite3.connect(tmp_path / "ControleInv" / "controleinv.db").close()
    destino = config.db_padrao()
    destino.parent.mkdir()
    destino.write_bytes(b"novo")

    config.migrar_banco_legado(destino)

    assert destino.read_bytes() == b"novo"


def test_prefixo_legado_aceito_e_novo_prevalece(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "ARQUIVO_ENV", tmp_path / ".env")
    (tmp_path / ".env").write_text("CONTROLEINV_COTAHIST_HORA=7\nINVESTHUB_PORT=9000\nCONTROLEINV_PORT=1\n")
    monkeypatch.setenv("CONTROLEINV_HOST", "0.0.0.0")
    for chave in ("INVESTHUB_COTAHIST_HORA", "INVESTHUB_PORT", "INVESTHUB_HOST"):
        monkeypatch.setenv(chave, "")  # registra o estado original para o teardown restaurar
        monkeypatch.delenv(chave)

    config._aceitar_prefixo_legado()
    s = config.Settings(_env_file=tmp_path / ".env")

    assert s.cotahist_hora == 7
    assert s.host == "0.0.0.0"
    assert s.port == 9000
