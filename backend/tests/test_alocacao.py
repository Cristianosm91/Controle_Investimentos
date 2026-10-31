from decimal import Decimal as D

import pytest

from app.services.alocacao import BookAlvo, Candidato, calcular_alocacao


def _cand(ativo_id, ticker, valor, book, preco=D(10), **extra):
    return Candidato(ativo_id, ticker, None, "AÇÃO", "BRL", D(valor), [(book, D(1))], preco, preco, **extra)


@pytest.fixture
def books():
    return [BookAlvo(1, "Ações", "RV", D("0.6")), BookAlvo(2, "FII", "RV", D("0.4"))]


def _por_ticker(r):
    return {i.candidato.ticker: i for i in r.ativos}


def test_restante_do_book_dividido_igualmente_e_aporte_cobre_deficits(books):
    cands = [_cand(1, "X", 50, 1), _cand(2, "Y", 10, 1), _cand(3, "Z", 40, 2)]
    r = calcular_alocacao(cands, books, aporte=D(100))
    itens = _por_ticker(r)
    assert itens["X"].valor_alvo == itens["Y"].valor_alvo == D(60)
    assert (itens["X"].ajuste, itens["Y"].ajuste, itens["Z"].ajuste) == (D(10), D(50), D(40))
    assert r.sobra == 0
    assert itens["Y"].quantidade == 5  # R$ 50 / R$ 10


def test_peso_definido_na_carteira(books):
    cands = [_cand(1, "X", 50, 1, peso_no_book=D("0.8")), _cand(2, "Y", 10, 1), _cand(3, "Z", 40, 2)]
    itens = _por_ticker(calcular_alocacao(cands, books))
    assert itens["X"].peso_alvo == D("0.48") and itens["Y"].peso_alvo == D("0.12")


def test_acima_do_teto_nao_recebe_compra(books):
    cands = [_cand(1, "X", 50, 1), _cand(2, "Y", 10, 1, preco_teto=D(8)), _cand(3, "Z", 40, 2)]
    r = calcular_alocacao(cands, books, aporte=D(100))
    itens = _por_ticker(r)
    assert itens["Y"].acima_teto and itens["Y"].ajuste == 0
    assert (itens["X"].ajuste, itens["Z"].ajuste) == (D(10), D(40))
    assert r.sobra == D(50)
    # Sem respeitar o teto, Y volta a receber.
    assert _por_ticker(calcular_alocacao(cands, books, D(100), respeitar_teto=False))["Y"].ajuste == D(50)


def test_aporte_menor_que_deficits_e_proporcional(books):
    cands = [_cand(1, "X", 50, 1), _cand(2, "Y", 10, 1), _cand(3, "Z", 40, 2)]
    r = calcular_alocacao(cands, books, aporte=D(50))
    itens = _por_ticker(r)
    # base 150: alvos X=Y=45, Z=60 → déficits Y=35, Z=20 (X acima do alvo)
    assert itens["X"].ajuste == 0
    assert itens["Y"].ajuste + itens["Z"].ajuste + r.sobra == D(50)
    assert r.sobra < D("0.02")  # só o arredondamento para centavos
    assert itens["Y"].ajuste > itens["Z"].ajuste


def test_rebalancear_vende_o_excesso(books):
    cands = [_cand(1, "X", 80, 1), _cand(2, "Y", 10, 1), _cand(3, "Z", 10, 2)]
    r = calcular_alocacao(cands, books, modo="rebalancear")
    itens = _por_ticker(r)
    assert itens["X"].ajuste == D(-50) and itens["Y"].ajuste == D(20) and itens["Z"].ajuste == D(30)
    assert sum(i.ajuste for i in r.ativos) == 0
    assert {g.nome: g.ajuste for g in r.books} == {"Ações": D(-30), "FII": D(30)}


def test_classe_sem_book_fica_fora_e_gera_aviso(books):
    sem = Candidato(9, "BTC", None, "CRIPTO", "BRL", D(100), [], D(1), D(1))
    r = calcular_alocacao([_cand(1, "X", 100, 1), sem], books)
    assert r.total_atual == D(100) and [i.candidato.ticker for i in r.ativos] == ["X"]
    assert any("CRIPTO" in a for a in r.avisos)
    assert any("FII" in a for a in r.avisos)  # book com peso e sem ativos


def test_ativo_distribuido_entre_books(books):
    misto = Candidato(1, "M", None, "AÇÃO", "BRL", D(100), [(1, D("0.5")), (2, D("0.5"))], D(1), D(1))
    r = calcular_alocacao([misto], books)
    assert {g.nome: g.valor_atual for g in r.books} == {"Ações": D(50), "FII": D(50)}
    assert r.ativos[0].peso_alvo == 1


def test_modo_invalido(books):
    with pytest.raises(ValueError):
        calcular_alocacao([], books, modo="vender")
