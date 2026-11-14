from datetime import date
from decimal import Decimal as D

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db import Base, get_session
from app.main import app
from app.models import CdiDiario, CoberturaCdi
from app.services import renda_fixa
from app.services.cdi import CdiIndisponivel, CurvaCdi, gravar


@pytest.fixture
def sessao():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s
    engine.dispose()


def test_capitaliza_percentual_sobre_cada_taxa_diaria_sem_fim_de_semana(sessao):
    # 110% de 0,01% na sexta e 0,02% na segunda: 1,00011 * 1,00022.
    gravar(sessao, date(2025, 1, 3), date(2025, 1, 6), {
        date(2025, 1, 3): D("0.0001"), date(2025, 1, 6): D("0.0002"),
    })
    curva = CurvaCdi(sessao, D("1.1"))
    assert curva.fator(date(2025, 1, 3), date(2025, 1, 7)) == D("1.0003300242")
    assert curva.fator(date(2025, 1, 4), date(2025, 1, 6)) == 1
    assert curva.fator(date(2025, 1, 6), date(2025, 1, 7)) == D("1.00022")


def test_dias_sem_publicacao_no_intervalo_consultado_nao_recebem_taxa(sessao):
    gravar(sessao, date(2025, 4, 17), date(2025, 4, 22), {
        date(2025, 4, 17): D("0.0001"), date(2025, 4, 22): D("0.0001"),
    })
    assert CurvaCdi(sessao).fator(date(2025, 4, 18), date(2025, 4, 22)) == 1


def test_cobertura_nao_confunde_dados_ausentes_com_feriado(sessao):
    gravar(sessao, date(2025, 1, 2), date(2025, 1, 3), {date(2025, 1, 2): D("0.0001")})
    gravar(sessao, date(2025, 1, 6), date(2025, 1, 7), {date(2025, 1, 6): D("0.0001")})
    with pytest.raises(CdiIndisponivel, match="Atualize"):
        CurvaCdi(sessao).fator(date(2025, 1, 2), date(2025, 1, 8))
    gravar(sessao, date(2025, 1, 3), date(2025, 1, 6), {date(2025, 1, 3): D("0.0001")})
    assert len(list(sessao.scalars(select(CoberturaCdi)))) == 1
    assert CurvaCdi(sessao).fator(date(2025, 1, 2), date(2025, 1, 8)) == D("1.000300030001")


def test_upsert_e_consultas_repetidas_nao_duplicam_taxas(sessao):
    for _ in range(2):
        gravar(sessao, date(2025, 1, 2), date(2025, 1, 3), {date(2025, 1, 2): D("0.0001")})
    assert len(list(sessao.scalars(select(CdiDiario)))) == 1
    assert len(list(sessao.scalars(select(CoberturaCdi)))) == 1


@pytest.mark.parametrize("taxa", [D("-1"), D("NaN"), D("Infinity")])
def test_taxa_invalida_nao_grava_cobertura(sessao, taxa):
    with pytest.raises(ValueError):
        gravar(sessao, date(2025, 1, 2), date(2025, 1, 3), {date(2025, 1, 2): taxa})
    assert list(sessao.scalars(select(CoberturaCdi))) == []


def semear_cdi(cliente):
    gerador = app.dependency_overrides[get_session]()
    s = next(gerador)
    try:
        gravar(s, date(2025, 1, 2), date.today(), {
            date(2025, 1, 2): D("0.0001"),
            date(2025, 1, 3): D("0.0001"),
            date(2025, 1, 6): D("0.0002"),
            date(2025, 1, 7): D("0.0002"),
        })
    finally:
        gerador.close()
    invs = [cliente.post("/api/investidores", json={"nome": nome}).json()["id"] for nome in ("Teste A", "Teste B")]
    ativo = cliente.post("/api/ativos", json={
        "ticker": "CDI TESTE", "classe": "CDB", "cotacao_automatica": False,
        "indexador": "CDI", "indexador_pct": 1.1, "data_base": "2025-01-02",
    }).json()["id"]
    for inv in invs:
        r = cliente.post("/api/operacoes", json={
            "investidor_id": inv, "ativo_id": ativo, "data": "2025-01-02",
            "evento": "C", "quantidade": 500, "preco": 1,
        })
        assert r.status_code == 201, r.text
    return ativo


def test_saldo_corrigido_preserva_historico_e_continua_rendendo(cliente):
    ativo = semear_cdi(cliente)
    url = f"/api/ativos/{ativo}"
    antes = cliente.get(f"{url}/cota", params={"data": "2025-01-03"}).json()["cota"]
    assert antes == pytest.approx(1.00011)
    r = cliente.post(f"{url}/saldo", json={"data": "2025-01-06", "saldo": 1100})
    assert r.status_code == 200 and r.json()["cota"] == 1.1  # Saldo total dos dois investidores.
    assert cliente.get(f"{url}/cota", params={"data": "2025-01-03"}).json()["cota"] == antes
    assert cliente.get(f"{url}/cota", params={"data": "2025-01-07"}).json()["cota"] == pytest.approx(1.100242)
    assert cliente.get(f"{url}/cota", params={"data": "2025-01-08"}).json()["cota"] == pytest.approx(1.10048405324)
    gerador = app.dependency_overrides[get_session]()
    s = next(gerador)
    try:
        renda_fixa.atualizar(s)
        renda_fixa.atualizar(s)
    finally:
        gerador.close()
    assert cliente.get(f"{url}/cota", params={"data": "2025-01-08"}).json()["cota"] == pytest.approx(1.10048405324)
    # Correção posterior não apaga a anterior; editar a mesma data substitui somente aquela âncora.
    r = cliente.post(f"{url}/saldo", json={"data": "2025-01-07", "saldo": 1200})
    assert r.status_code == 200
    r = cliente.post(f"{url}/saldo", json={"data": "2025-01-06", "saldo": 1150})
    assert r.status_code == 200
    assert cliente.get(f"{url}/cota", params={"data": "2025-01-08"}).json()["cota"] == pytest.approx(1.200264)


def test_cdi_nao_extrapola_historico_ausente_e_saldo_nao_e_futuro(cliente):
    inv = cliente.post("/api/investidores", json={"nome": "Teste"}).json()["id"]
    ativo = cliente.post("/api/ativos", json={
        "ticker": "SEMCDI", "cotacao_automatica": False, "indexador": "CDI", "data_base": "2025-01-02",
    }).json()["id"]
    r = cliente.get(f"/api/ativos/{ativo}/cota", params={"data": "2025-01-06"})
    assert r.status_code == 422 and "Atualize" in r.json()["detail"]
    cliente.post("/api/operacoes", json={
        "investidor_id": inv, "ativo_id": ativo, "data": "2025-01-02",
        "evento": "C", "quantidade": 1000, "preco": 1,
    })
    assert cliente.get("/api/renda-fixa").status_code == 422
    r = cliente.post(f"/api/ativos/{ativo}/saldo", json={"data": "2099-01-02", "saldo": 1100})
    assert r.status_code == 422
    # Mesmo sem histórico antigo, o saldo informado é uma referência explícita para aquela data.
    r = cliente.post(f"/api/ativos/{ativo}/saldo", json={"data": "2025-01-06", "saldo": 1100})
    assert r.status_code == 200 and r.json()["cota"] == 1.1
    assert cliente.get(f"/api/ativos/{ativo}/cota", params={"data": "2025-01-07"}).status_code == 422


def test_vencimento_interrompe_o_cdi_e_taxa_adicional_usa_252(sessao):
    from app.models import Ativo
    gravar(sessao, date(2025, 1, 2), date(2025, 1, 7), {
        date(2025, 1, 2): D("0.0001"), date(2025, 1, 3): D("0.0001"),
        date(2025, 1, 6): D("0.0002"), date(2025, 1, 7): D("0.0002"),
    })
    ativo = Ativo(
        ticker="CDI VENCE", cotacao_automatica=False, indexador="CDI", data_base=date(2025, 1, 2),
        data_vencimento=date(2025, 1, 6), indexador_pct=D(1), taxa_aa=D(0),
    )
    sessao.add(ativo)
    sessao.commit()
    assert renda_fixa.valor_cota(sessao, ativo, date(2025, 2, 1)) == D("1.00020001")
    curva = CurvaCdi(sessao, taxa_aa=D("0.1"))
    esperado = D("1.00020001") * D("1.1") ** (D(2) / 252)
    assert curva.fator(date(2025, 1, 2), date(2025, 1, 6)) == pytest.approx(esperado, rel=D("1e-25"))


def test_provider_grava_taxas_em_fracao_e_busca_desde_data_base(sessao, monkeypatch):
    from app.models import Ativo
    from app.services import historico

    sessao.add(Ativo(
        ticker="CDI BASE", cotacao_automatica=False, indexador="CDI", data_base=date(2025, 1, 2),
    ))
    sessao.commit()
    consultas = []

    def serie(serie, inicio, fim, cliente):
        if serie == 12:
            consultas.append((inicio, fim))
            # Valores em pontos percentuais, no formato da SGS 12.
            return {date(2025, 1, 2): D("0.045513"), date(2025, 1, 3): D("0.045513")}
        return {}

    monkeypatch.setattr(historico.fontes, "serie_sgs", serie)
    monkeypatch.setattr(historico.fontes, "indice_b3", lambda *args: {})
    resultado = historico.atualizar_indices(sessao, desde=date.today())
    assert resultado.falhas == []
    assert resultado.gravados["CDI diário"] == 2
    assert consultas[0][0] == date(2025, 1, 2)
    assert consultas[0][1] < date.today()
    assert sessao.get(CdiDiario, date(2025, 1, 2)).taxa == D("0.00045513")


def test_falha_provider_nao_inventa_cobertura(sessao, monkeypatch):
    from app.services import historico

    def serie(serie, *args):
        if serie == 12:
            raise historico.fontes.ErroIndice("Falha SGS 12")
        return {}

    monkeypatch.setattr(historico.fontes, "serie_sgs", serie)
    monkeypatch.setattr(historico.fontes, "indice_b3", lambda *args: {})
    resultado = historico.atualizar_indices(sessao)
    assert resultado.falhas == ["CDI diário"]
    assert list(sessao.scalars(select(CoberturaCdi))) == []


def test_migracao_cdi_ida_volta_preserva_ativos(tmp_path):
    from sqlalchemy import text

    from alembic import command
    from app.models import Ativo
    from app.services import backup

    banco = tmp_path / "cdi-migracao.db"
    cfg = backup._alembic(f"sqlite:///{banco.as_posix()}")
    command.upgrade(cfg, "a2e6c19b407d")
    engine = create_engine(f"sqlite:///{banco.as_posix()}")
    with Session(engine) as s:
        s.add(Ativo(ticker="TESTE", moeda="BRL"))
        s.commit()
    command.upgrade(cfg, "d7e4b2a9c610")
    with engine.begin() as c:
        c.execute(text("INSERT INTO cdi_diario (data,taxa) VALUES ('2025-01-02',0.00045513)"))
    command.downgrade(cfg, "a2e6c19b407d")
    command.upgrade(cfg, "d7e4b2a9c610")
    with engine.connect() as c:
        assert c.execute(text("SELECT ticker,moeda FROM ativo")).all() == [("TESTE", "BRL")]
        assert c.execute(text("SELECT count(*) FROM cdi_diario")).scalar() == 0
    engine.dispose()
