import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from test_extrato_b3 import CAB_NEGOCIACAO, enviar, investidor, xlsx

from app.db import Base
from app.models import Corretora, CorretoraApelido, Investidor
from scripts.importar_planilha import Importador


@pytest.fixture
def sessao():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as sessao:
        sessao.add(Investidor(nome="Teste"))
        sessao.commit()
        yield sessao
    engine.dispose()


def criar(cliente, nome, cnpj=None):
    resposta = cliente.post("/api/corretoras", json={"nome": nome, "cnpj": cnpj})
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def test_uniao_preserva_lancamentos_e_apelidos_em_importacoes(cliente):
    origem = criar(cliente, "XP", "12345678000199")
    destino = criar(cliente, "XP Investimentos")
    inv = investidor(cliente)
    ativo = cliente.post("/api/ativos", json={"ticker": "PETR4"}).json()["id"]
    dados = {"investidor_id": inv, "ativo_id": ativo, "corretora_id": origem["id"]}
    operacao = cliente.post("/api/operacoes", json={
        **dados, "data": "2025-01-01", "evento": "C", "quantidade": 2, "preco": 10,
    })
    provento = cliente.post("/api/proventos", json={
        **dados, "data_pagamento": "2025-01-02", "evento": "DIVIDENDO", "valor": 5,
    })
    caixa = cliente.post("/api/caixa", json={
        "investidor_id": inv, "corretora_id": origem["id"], "data": "2025-01-01", "evento": "APORTE", "valor": 50,
    })
    assert [r.status_code for r in (operacao, provento, caixa)] == [201, 201, 201]

    alerta = [v for v in cliente.get("/api/qualidade-dados").json() if v["codigo"] == "corretoras_duplicadas"]
    assert len(alerta) == 1 and alerta[0]["link"] == "/configuracoes?secao=corretoras"
    resposta = cliente.post(f"/api/corretoras/{origem['id']}/unir", json={"destino_id": destino["id"]})
    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["cnpj"] == "12345678000199"
    assert resposta.json()["apelidos"] == [{"nome": "XP"}]
    assert len(cliente.get("/api/corretoras").json()) == 1
    for recurso in ("operacoes", "proventos", "caixa"):
        itens = cliente.get(f"/api/{recurso}").json()["itens"]
        assert len(itens) == 1 and itens[0]["corretora_id"] == destino["id"]
    assert not [v for v in cliente.get("/api/qualidade-dados").json() if v["codigo"] == "corretoras_duplicadas"]

    conteudo = xlsx(CAB_NEGOCIACAO, [
        ["05/01/2025", "Compra", "Mercado à Vista", "-", "XP INVESTIMENTOS CCTVM S/A", "VALE3", 1, 50, 50],
    ])
    previa = enviar(cliente, "previa", conteudo, investidor_id=inv)
    assert previa.status_code == 200, previa.text
    assert previa.json()["corretoras_novas"] == []
    importacao = enviar(cliente, "importar", conteudo, investidor_id=inv)
    assert importacao.status_code == 200, importacao.text
    assert importacao.json()["corretoras_criadas"] == []
    assert cliente.get("/api/operacoes", params={"ticker": "VALE3"}).json()["itens"][0]["corretora_id"] == destino["id"]
    assert cliente.post("/api/corretoras", json={"nome": "xp"}).status_code == 409


def test_uniao_rejeita_cnpj_divergente_e_destino_invalido_sem_alteracoes(cliente):
    origem = criar(cliente, "XP", "12345678000199")
    destino = criar(cliente, "XP Investimentos", "12345678000270")
    assert cliente.post(f"/api/corretoras/{origem['id']}/unir", json={"destino_id": destino["id"]}).status_code == 409
    assert cliente.post(f"/api/corretoras/{origem['id']}/unir", json={"destino_id": origem["id"]}).status_code == 422
    assert cliente.post(f"/api/corretoras/{origem['id']}/unir", json={"destino_id": 999}).status_code == 404
    assert len(cliente.get("/api/corretoras").json()) == 2
    assert cliente.put(f"/api/corretoras/{origem['id']}", json={"nome": "  "}).status_code == 422
    resposta = cliente.put(f"/api/corretoras/{origem['id']}", json={"nome": " Nova XP ", "cnpj": None})
    assert resposta.status_code == 200 and resposta.json()["nome"] == "Nova XP"
    assert resposta.json()["apelidos"] == [{"nome": "XP"}]


def test_deteccao_conservadora_e_fingerprint_por_par(cliente):
    for nome in ("Ágora", "AGORA", "XP", "XP Investimentos", "XP Investimentos Brasil", "Outra"):
        criar(cliente, nome)
    alertas = [v for v in cliente.get("/api/qualidade-dados").json() if v["codigo"] == "corretoras_duplicadas"]
    assert len(alertas) == 3
    assert len({v["fingerprint"] for v in alertas}) == 3
    assert all(v["severidade"] == "aviso" for v in alertas)


def test_unioes_sucessivas_e_edicao_preservam_apelidos(cliente):
    antiga = criar(cliente, "XP")
    intermediaria = criar(cliente, "XP Investimentos")
    final = criar(cliente, "Corretora Final")
    for origem, destino in ((antiga, intermediaria), (intermediaria, final)):
        resposta = cliente.post(f"/api/corretoras/{origem['id']}/unir", json={"destino_id": destino["id"]})
        assert resposta.status_code == 200, resposta.text
    assert {a["nome"] for a in resposta.json()["apelidos"]} == {"XP", "XP Investimentos"}
    assert cliente.put(f"/api/corretoras/{final['id']}", json={"nome": "Corretora Renomeada"}).status_code == 200
    assert {a["nome"] for a in cliente.get("/api/corretoras").json()[0]["apelidos"]} == {
        "XP", "XP Investimentos", "Corretora Final",
    }


def test_importacao_recusa_corretoras_ambiguas(cliente):
    criar(cliente, "XP")
    criar(cliente, "xp")
    inv = investidor(cliente)
    conteudo = xlsx(CAB_NEGOCIACAO, [
        ["05/01/2025", "Compra", "Mercado à Vista", "-", "XP", "VALE3", 1, 50, 50],
    ])
    resposta = enviar(cliente, "previa", conteudo, investidor_id=inv)
    assert resposta.status_code == 422 and "mais de um cadastro" in resposta.json()["detail"]


def test_importador_planilha_usa_apelidos_e_recusa_ambiguidade(sessao):
    destino = Corretora(nome="XP Investimentos")
    sessao.add(destino)
    sessao.flush()
    sessao.add(CorretoraApelido(nome="XP", corretora_id=destino.id))
    sessao.flush()
    importador = Importador(sessao, sessao.scalar(select(Investidor)))
    assert importador.corretora("xp").id == destino.id
    sessao.add(Corretora(nome="Xp"))
    sessao.flush()
    importador = Importador(sessao, sessao.scalar(select(Investidor)))
    with pytest.raises(ValueError, match="mais de um cadastro"):
        importador.corretora("XP")
