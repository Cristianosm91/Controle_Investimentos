from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.lancamentos import listar_caixa, listar_operacoes, listar_proventos
from app.api.monitoramento import (
    qualidade_dados,
    reabrir_apontamento,
    tratar_apontamento,
)
from app.db import Base
from app.models import Ativo, Investidor, MovCaixa, Operacao, Provento
from app.services import qualidade


def _banco():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return engine


def _venda(session: Session, investidor: Investidor, ticker: str) -> Operacao:
    ativo = Ativo(ticker=ticker, classe="AÇÃO")
    session.add(ativo)
    session.flush()
    operacao = Operacao(
        investidor_id=investidor.id,
        ativo_id=ativo.id,
        data=date(2026, 1, 5),
        evento="V",
        quantidade=Decimal("-1"),
        preco=Decimal("10"),
        taxas=Decimal("0"),
        irrf=Decimal("0"),
        moeda="BRL",
        cambio=Decimal("1"),
    )
    session.add(operacao)
    session.flush()
    return operacao


def _compra(session: Session, investidor: Investidor, ticker: str) -> Operacao:
    ativo = Ativo(ticker=ticker, classe="AÇÃO")
    session.add(ativo)
    session.flush()
    operacao = Operacao(
        investidor_id=investidor.id,
        ativo_id=ativo.id,
        data=date(2026, 1, 5),
        evento="C",
        quantidade=Decimal("1"),
        preco=Decimal("10"),
        moeda="BRL",
        cambio=Decimal("1"),
    )
    session.add(operacao)
    session.flush()
    return operacao


def test_apontamento_de_posicao_negativa_vincula_e_abre_somente_operacoes_relacionadas():
    engine = _banco()
    with Session(engine) as session:
        investidor = Investidor(nome="Investidor teste")
        session.add(investidor)
        session.flush()
        operacao = _venda(session, investidor, "PETR4")
        segunda_operacao = Operacao(
            investidor_id=investidor.id,
            ativo_id=operacao.ativo_id,
            data=date(2026, 1, 6),
            evento="V",
            quantidade=Decimal("-2"),
            preco=Decimal("11"),
            moeda="BRL",
            cambio=Decimal("1"),
        )
        session.add(segunda_operacao)
        session.flush()
        nao_relacionada = _compra(session, investidor, "VALE3")

        primeira = next(
            v for v in qualidade.verificar(session) if v.codigo == "posicao_negativa"
        )
        segunda = next(
            v for v in qualidade.verificar(session) if v.codigo == "posicao_negativa"
        )

        assert primeira.operacao_ids == [operacao.id, segunda_operacao.id]
        assert primeira.ativo_ids
        assert primeira.investidor_ids == [investidor.id]
        assert primeira.fingerprint == segunda.fingerprint
        pagina = listar_operacoes(
            sessao=session,
            investidores=[investidor.id],
            ticker=None,
            classe=None,
            inicio=None,
            fim=None,
            ids=None,
            apontamento=primeira.fingerprint,
            limite=200,
            deslocamento=0,
        )
        assert pagina.total == 2
        assert {item.id for item in pagina.itens} == {
            operacao.id,
            segunda_operacao.id,
        }
        assert nao_relacionada.id not in {item.id for item in pagina.itens}
    engine.dispose()


def test_tratamento_persiste_sem_alterar_operacao_e_novo_apontamento_nao_herda_status():
    engine = _banco()
    with Session(engine) as session:
        investidor = Investidor(nome="Investidor teste")
        session.add(investidor)
        session.flush()
        operacao = _venda(session, investidor, "PETR4")
        operacao_id = operacao.id
        investidor_id = investidor.id
        fingerprint = next(
            v.fingerprint
            for v in qualidade.verificar(session)
            if v.codigo == "posicao_negativa"
        )

        resposta = tratar_apontamento(fingerprint, session)
        assert resposta.status == "tratado"
        assert session.get(Operacao, operacao_id).quantidade == Decimal("-1")

    with Session(engine) as session:
        dados_atuais = qualidade_dados(session, None)
        assert any(
            v.fingerprint == fingerprint and v.status == "tratado"
            for v in dados_atuais
        ), (fingerprint, [(v.codigo, v.fingerprint, v.status) for v in dados_atuais])
        assert session.get(Operacao, operacao_id).quantidade == Decimal("-1")

        operacao = session.get(Operacao, operacao_id)
        operacao.evento = "C"
        operacao.quantidade = Decimal("1")
        session.commit()
        pagina_antiga = listar_operacoes(
            sessao=session,
            investidores=[investidor_id],
            ticker=None,
            classe=None,
            inicio=None,
            fim=None,
            ids=None,
            apontamento=fingerprint,
            limite=200,
            deslocamento=0,
        )
        assert pagina_antiga.total == 0
        atual = qualidade_dados(session, None, historico=True)
        assert not any(
            v.fingerprint == fingerprint and v.status == "aberto" for v in atual
        )
        assert any(
            v.fingerprint == fingerprint and v.status == "resolvido" for v in atual
        )

        investidor = session.get(Investidor, investidor_id)
        nova_operacao = _venda(session, investidor, "VALE3")
        nova = next(
            v for v in qualidade_dados(session, None)
            if v.codigo == "posicao_negativa"
        )
        assert nova.operacao_ids == [nova_operacao.id]
        assert nova.fingerprint != fingerprint
        assert nova.status == "aberto"

        reabrir_apontamento(fingerprint, session)
        assert session.get(Operacao, nova_operacao.id).quantidade == Decimal("-1")
    engine.dispose()


def test_apontamento_aberto_com_operacao_excluida_retorna_lista_vazia():
    engine = _banco()
    with Session(engine) as session:
        investidor = Investidor(nome="Investidor teste")
        session.add(investidor)
        session.flush()
        operacao = _venda(session, investidor, "PETR4")
        fingerprint = next(
            v.fingerprint
            for v in qualidade.verificar(session)
            if v.codigo == "posicao_negativa"
        )
        session.delete(operacao)
        session.commit()

        pagina = listar_operacoes(
            sessao=session,
            investidores=[investidor.id],
            ticker=None,
            classe=None,
            inicio=None,
            fim=None,
            ids=None,
            apontamento=fingerprint,
            limite=200,
            deslocamento=0,
        )
        assert pagina.total == 0
        assert pagina.itens == []
    engine.dispose()


def test_apontamento_sem_corretora_abre_lancamentos_dos_tres_tipos_e_expira_ao_alterar():
    engine = _banco()
    with Session(engine) as session:
        investidor = Investidor(nome="Investidor teste")
        session.add(investidor)
        session.flush()
        operacao = _compra(session, investidor, "PETR4")
        provento = Provento(
            investidor_id=investidor.id,
            ativo_id=operacao.ativo_id,
            data_pagamento=date(2026, 1, 10),
            evento="DIVIDENDO",
            valor=Decimal("5"),
            moeda="BRL",
            cambio=Decimal("1"),
        )
        movimento = MovCaixa(
            investidor_id=investidor.id,
            data=date(2026, 1, 11),
            evento="APORTE",
            valor=Decimal("100"),
            moeda="BRL",
        )
        session.add_all((provento, movimento))
        session.flush()

        apontamento = next(
            v for v in qualidade.verificar(session)
            if v.codigo == "sem_corretora"
        )
        assert apontamento.operacao_ids == [operacao.id]
        assert apontamento.provento_ids == [provento.id]
        assert apontamento.caixa_ids == [movimento.id]

        pagina_proventos = listar_proventos(
            sessao=session,
            investidores=[investidor.id],
            ticker=None,
            inicio=None,
            fim=None,
            limite=200,
            deslocamento=0,
            evento=None,
            classe=None,
            apontamento=apontamento.fingerprint,
        )
        pagina_caixa = listar_caixa(
            sessao=session,
            investidores=[investidor.id],
            inicio=None,
            fim=None,
            limite=200,
            deslocamento=0,
            apontamento=apontamento.fingerprint,
        )
        assert [item.id for item in pagina_proventos.itens] == [provento.id]
        assert [item.id for item in pagina_caixa.itens] == [movimento.id]

        tratamento = tratar_apontamento(apontamento.fingerprint, session)
        assert tratamento.provento_ids == [provento.id]
        assert tratamento.caixa_ids == [movimento.id]

        provento.valor = Decimal("6")
        session.commit()
        pagina_antiga = listar_proventos(
            sessao=session,
            investidores=[investidor.id],
            ticker=None,
            inicio=None,
            fim=None,
            limite=200,
            deslocamento=0,
            evento=None,
            classe=None,
            apontamento=apontamento.fingerprint,
        )
        assert pagina_antiga.total == 0
        historico = qualidade_dados(session, None, historico=True)
        resolvido = next(v for v in historico if v.fingerprint == apontamento.fingerprint)
        assert resolvido.status == "resolvido"
        assert resolvido.provento_ids == [provento.id]
        assert resolvido.caixa_ids == [movimento.id]
    engine.dispose()


def test_desfazer_tratamento_retorna_apontamento_ativo_a_pendente():
    engine = _banco()
    with Session(engine) as session:
        investidor = Investidor(nome="Investidor teste")
        session.add(investidor)
        session.flush()
        _venda(session, investidor, "PETR4")
        fingerprint = next(
            v.fingerprint
            for v in qualidade.verificar(session)
            if v.codigo == "posicao_negativa"
        )

        tratar_apontamento(fingerprint, session)
        reabrir_apontamento(fingerprint, session)

        pendente = next(
            v for v in qualidade_dados(session, None)
            if v.fingerprint == fingerprint
        )
        assert pendente.status == "aberto"
    engine.dispose()
